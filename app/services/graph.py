from datetime import timezone
from openai import AsyncAzureOpenAI
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from telegram import Message as TelegramMessage
from graphiti_core.llm_client import LLMConfig, OpenAIClient
from graphiti_core.utils.maintenance.graph_data_operations import clear_data
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient

from app.core.config import settings
from app.models.ontology import (
    User, Topic, Message, Sent, InReplyTo, BelongsTo, 
    Event, Interest, Project, WorksOn, LocatedOn, Attends, InterestedIn
)

def get_graphiti_client():
    api_key = settings.AZURE_OPENAI_API_KEY
    api_version = "2024-12-01-preview"
    llm_endpoint = settings.AZURE_OPENAI_ENDPOINT
    embedding_endpoint = settings.AZURE_OPENAI_ENDPOINT

    neo4j_uri = settings.NEO4J_URI
    neo4j_user = settings.NEO4J_USER
    neo4j_password = settings.NEO4J_PASSWORD

    llm_small_model = settings.RERANKER_MODEL
    llm_model = settings.MODEL
    embedding_model = settings.EMBEDDING_MODEL

    llm_client_azure = AsyncAzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        azure_endpoint=llm_endpoint
    )

    embedding_client_azure = AsyncAzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        azure_endpoint=embedding_endpoint
    )

    azure_llm_config = LLMConfig(
        small_model=llm_small_model,
        model=llm_model,
    )

    return Graphiti(
        neo4j_uri,
        neo4j_user,
        neo4j_password,
        llm_client=OpenAIClient(
            config=azure_llm_config,
            client=llm_client_azure
        ),
        embedder=OpenAIEmbedder(
            config=OpenAIEmbedderConfig(
                embedding_model=embedding_model
            ),
            client=embedding_client_azure
        ),
        cross_encoder=OpenAIRerankerClient(
            config=LLMConfig(
                model=azure_llm_config.small_model
            ),
            client=llm_client_azure
        )
    )

class GraphService:
    def __init__(self):
        self.graphiti: Graphiti | None = None
        self.entity_types = {
            "User": User, 
            "Topic": Topic,
            "Message": Message,
            "Event": Event, 
            "Interest": Interest, 
            "Project": Project
        }
        self.edge_types = {
            "SENT": Sent,
            "BELONGS_TO": BelongsTo,
            "IN_REPLY_TO": InReplyTo,
            "LOCATED_ON": LocatedOn,
            "WORKS_ON": WorksOn,
            "ATTENDS": Attends,
            "INTERESTED_IN": InterestedIn,
        }
        self.edge_type_map = {
            ("User", "Event"): ["ATTENDS"],
            ("User", "Floor"): ["LOCATED_ON"],
            ("Event", "Floor"): ["LOCATED_ON"],
            ("Project", "Floor"): ["LOCATED_ON"],
            ("User", "Interest"): ["INTERESTED_IN"],
            ("User", "Project"): ["WORKS_ON"],
            ("Event", "Interest"): ["INTERESTED_IN"],
            ("Entity", "Entity"): ["RELATES_TO"],
        }

    async def connect(self):
        self.graphiti = get_graphiti_client()
        if settings.APP_ENV == "dev":
            await clear_data(self.graphiti.driver)
            await self.graphiti.build_indices_and_constraints()

    async def close(self):
        if self.graphiti:
            await self.graphiti.close()

    async def build_communities(self):
        if settings.APP_ENV == "prod" and self.graphiti:
            await self.graphiti.build_communities()

    async def process_telegram_message(self, message: TelegramMessage):
        await self._add_structured_message(message)
        await self._extract_entities_from_message(message)

    async def check_user_exists(self, message: TelegramMessage):
        user_id = message.from_user.id
        cypher = """
        MATCH (n:User {user_id: $user_id})
        RETURN n.user_id
        LIMIT 1
        """
        result = await self.graphiti.driver.execute_query(
            cypher,
            user_id=user_id
        )

        records = getattr(result, "records", None)
        if records is not None:
            return len(records) > 0
        return bool(result)

    async def _add_structured_message(self, message: TelegramMessage):
        user_info = message.from_user
        user_id = user_info.id
        user_node = None

        cypher = "MATCH (n:User {user_id: $user_id}) RETURN n"
        result = await self.graphiti.driver.execute_query(cypher, user_id=user_id)

        if result and isinstance(result[0], dict) and 'n' in result[0]:
            user_node = User(**result[0]['n'])
        else:
            user_node = User(
                user_id=user_id,
                username=getattr(user_info, "username", None),
                first_name=user_info.first_name,
                last_name=getattr(user_info, "last_name", None)
            )
            cypher = """
            MERGE (n:User {user_id: $user_id})
            SET n += $props
            RETURN n
            """
            await self.graphiti.driver.execute_query(
                cypher,
                user_id=user_node.user_id,
                props=user_node.model_dump()
            )

        topic_id = message.message_thread_id
        topic_name = "General"

        if message.reply_to_message and message.reply_to_message.forum_topic_created:
            topic_name = message.reply_to_message.forum_topic_created.name
        if not topic_id:
            topic_id = message.chat.id
        
        topic_node = None
        cypher = "MATCH (n:Topic {topic_id: $topic_id}) RETURN n"
        result = await self.graphiti.driver.execute_query(cypher, topic_id=topic_id)

        if result and isinstance(result[0], dict) and 'n' in result[0]:
            topic_node = Topic(**result[0]['n'])
        else:
            topic_node = Topic(topic_id=topic_id, title=topic_name)
            cypher = """
            MERGE (n:Topic {topic_id: $topic_id})
            SET n += $props
            RETURN n
            """
            await self.graphiti.driver.execute_query(
                cypher,
                topic_id=topic_node.topic_id,
                props=topic_node.model_dump()
            )

        iso_timestamp = message.date.astimezone(timezone.utc).isoformat()
        message_node = Message(
            message_id=message.message_id,
            text=message.text,
            timestamp=iso_timestamp
        )
        cypher = """
        MERGE (n:Message {message_id: $message_id})
        SET n += $props
        RETURN n
        """
        await self.graphiti.driver.execute_query(
            cypher,
            message_id=message_node.message_id,
            props=message_node.model_dump()
        )

        await self._add_edge("SENT", user_node.user_id, message_node.message_id, "User", "Message")
        await self._add_edge("BELONGS_TO", message_node.message_id, topic_node.topic_id, "Message", "Topic")

        if message.reply_to_message:
            parent_message_id = message.reply_to_message.message_id
            cypher = "MATCH (n:Message {message_id: $message_id}) RETURN n"
            result = await self.graphiti.driver.execute_query(cypher, message_id=parent_message_id)

            if result and isinstance(result[0], dict) and 'n' in result[0]:
                await self._add_edge("IN_REPLY_TO", message_node.message_id, parent_message_id, "Message", "Message")

    async def _add_edge(self, edge_type: str, from_id: int, to_id: int, from_label: str, to_label: str):
        from_id_field = "user_id" if from_label == "User" else "message_id" if from_label == "Message" else "topic_id"
        to_id_field = "user_id" if to_label == "User" else "message_id" if to_label == "Message" else "topic_id"
        
        cypher = f"""
        MATCH (a:{from_label} {{{from_id_field}: $from_id}}), (b:{to_label} {{{to_id_field}: $to_id}})
        MERGE (a)-[r:{edge_type}]->(b)
        RETURN r
        """
        await self.graphiti.driver.execute_query(
            cypher,
            from_id=from_id,
            to_id=to_id
        )

    async def _extract_entities_from_message(self, message: TelegramMessage):
        await self.graphiti.add_episode(
            name=f"telegram_message_{message.message_id}",
            episode_body=message.to_json(),
            source=EpisodeType.json,
            source_description="TowerBot",
            reference_time=message.date.astimezone(timezone.utc),
            group_id=settings.GROUP_ID,
            entity_types=self.entity_types,
            excluded_entity_types=["User", "Topic", "Message"],
            edge_types=self.edge_types,
            edge_type_map=self.edge_type_map,
            update_communities=True,
        )