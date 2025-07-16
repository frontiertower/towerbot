from datetime import timezone
from telegram import Message
from openai import AsyncAzureOpenAI
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.llm_client import LLMConfig, OpenAIClient
# from graphiti_core.utils.maintenance.graph_data_operations import clear_data
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
            "LocatedOn": LocatedOn,
            "WorksOn": WorksOn,
            "Attends": Attends,
            "InterestedIn": InterestedIn,
        }
        self.edge_type_map = {
            ("User", "Event"): ["Attends"],
            ("User", "Floor"): ["LocatedOn"],
            ("Event", "Floor"): ["LocatedOn"],
            ("Project", "Floor"): ["LocatedOn"],
            ("User", "Interest"): ["InterestedIn"],
            ("User", "Project"): ["WorksOn"],
            ("Event", "Interest"): ["InterestedIn"],
            ("Entity", "Entity"): ["RelatesTo"],
        }

    async def connect(self):
        self.graphiti = get_graphiti_client()
        # if settings.APP_ENV == "dev":
        #     await clear_data(self.graphiti.driver)
        #     await self.graphiti.build_indices_and_constraints()

    async def close(self):
        if self.graphiti:
            await self.graphiti.close()

    async def build_communities(self):
        if settings.APP_ENV == "prod" and self.graphiti:
            await self.graphiti.build_communities()

    async def process_telegram_message(self, message: Message):
        await self.add_structured_message(message)
        await self.extract_entities_from_message(message)

    async def add_structured_message(self, message: Message):
        if not self.graphiti:
            raise ConnectionError("Graphiti client not connected. Call `connect()` first.")

        user_info = message.from_user
        user_node = await self.graphiti.nodes.get(User, user_id=user_info.id)
        if not user_node:
            user_node = User(
                user_id=user_info.id,
                username=user_info.username,
                first_name=user_info.first_name
            )
            await self.graphiti.nodes.add(user_node)

        topic_id = message.message_thread_id
        topic_name = "General"
        if message.forum_topic_created:
            topic_name = message.forum_topic_created.name
        if not topic_id:
            topic_id = message.chat.id

        topic_node = await self.graphiti.nodes.get(Topic, topic_id=topic_id)
        if not topic_node:
            topic_node = Topic(topic_id=topic_id, title=topic_name)
            await self.graphiti.nodes.add(topic_node)

        iso_timestamp = message.date.astimezone(timezone.utc).isoformat()
        message_node = Message(
            message_id=message.message_id,
            text=message.text,
            timestamp=iso_timestamp
        )
        await self.graphiti.nodes.add(message_node)

        await self.graphiti.edges.add(user_node, Sent(), message_node)
        await self.graphiti.edges.add(message_node, BelongsTo(), topic_node)

        if message.reply_to_message:
            parent_message_id = message.reply_to_message.message_id
            parent_message_node = await self.graphiti.nodes.get(Message, message_id=parent_message_id)
            if parent_message_node:
                await self.graphiti.edges.add(message_node, InReplyTo(), parent_message_node)

    async def extract_entities_from_message(self, message: Message):
        if not self.graphiti:
            raise ConnectionError("Graphiti client not connected. Call `connect()` first.")

        conversational_body = self._create_conversational_body(message)
        if not message.text:
            return

        await self.graphiti.add_episode(
            name=f"telegram_message_extraction_{message.message_id}",
            episode_body=conversational_body,
            source=EpisodeType.message,
            source_description="TowerBot",
            reference_time=message.date.astimezone(timezone.utc),
            group_id=settings.GROUP_ID,
            entity_types=self.entity_types,
            excluded_entity_types=["User", "Topic", "Message"],
            edge_types=self.edge_types,
            edge_type_map=self.edge_type_map,
            update_communities=True,
        )

    def _get_message_description(self, message: Message) -> str:
        if message.text:
            return message.text
        if hasattr(message, 'forum_topic_created') and message.forum_topic_created:
            return f"[Created Forum Topic: '{message.forum_topic_created.name}']"
        if hasattr(message, 'photo') and message.photo:
            return "[Shared a photo]"
        if hasattr(message, 'sticker') and message.sticker:
            return "[Sent a sticker]"
        return "[Message with no text]"

    def _create_conversational_body(self, message: Message) -> str:
        sender_name = message.from_user.first_name or message.from_user.username or "Unknown"
        message_text = self._get_message_description(message)

        is_meaningful_reply = (
            message.reply_to_message and
            (message.reply_to_message.text or message.reply_to_message.photo)
        )

        if is_meaningful_reply:
            original_msg = message.reply_to_message
            original_sender = original_msg.from_user.first_name or original_msg.from_user.username or "Unknown"
            original_text = self._get_message_description(original_msg)
            return (
                f"{original_sender}: {original_text}\n"
                f"{sender_name}: {message_text}"
            )
        return f"{sender_name}: {message_text}"