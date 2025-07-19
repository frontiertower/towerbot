"""Graph service module for TowerBot knowledge graph operations.

This module provides the GraphService class and related functionality for managing
the knowledge graph using Graphiti, including entity extraction, relationship mapping,
and Telegram message processing.
"""

import logging
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
from app.schemas.ontology import (
    User, Topic, Message, Sent, InReplyTo, SentIn, 
    Event, Interest, Project, WorksOn, LocatedOn, Attends, InterestedIn, Floor, RelatedTo
)

logger = logging.getLogger(__name__)

def get_graphiti_client():
    """Create and configure a Graphiti client instance.
    
    Initializes a Graphiti client with Azure OpenAI services for LLM operations,
    embeddings, and cross-encoding, along with Neo4j database connectivity.
    
    Returns:
        Graphiti: Configured Graphiti client instance
    """
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
    """Service class for managing knowledge graph operations.
    
    This class handles all graph-related operations including:
    - Connection management to the Graphiti knowledge graph
    - Processing Telegram messages for entity extraction
    - Managing structured data storage and relationships
    - Building and maintaining graph communities
    
    Attributes:
        graphiti: The Graphiti client instance
        entity_types: Mapping of entity type names to their classes
        edge_types: Mapping of edge type names to their classes
        edge_type_map: Mapping of entity type pairs to allowed edge types
    """
    def __init__(self):
        """Initialize the GraphService with entity and edge type mappings."""
        self.graphiti: Graphiti | None = None
        self.entity_types = {
            "User": User, 
            "Topic": Topic,
            "Message": Message,
            "Event": Event, 
            "Interest": Interest, 
            "Project": Project,
            "Floor": Floor
        }
        self.edge_types = {
            "SENT": Sent,
            "SENT_IN": SentIn,
            "IN_REPLY_TO": InReplyTo,
            "LOCATED_ON": LocatedOn,
            "WORKS_ON": WorksOn,
            "ATTENDS": Attends,
            "INTERESTED_IN": InterestedIn,
            "RELATED_TO": RelatedTo,
        }
        self.edge_type_map = {
            ("User", "Event"): ["ATTENDS"],
            ("User", "Floor"): ["LOCATED_ON"],
            ("User", "Interest"): ["INTERESTED_IN"],
            ("User", "Project"): ["WORKS_ON"],
            
            ("User", "Message"): ["SENT"],
            ("Message", "Topic"): ["SENT_IN"],
            ("Message", "Message"): ["IN_REPLY_TO"],
            
            ("Event", "Floor"): ["LOCATED_ON"],
            ("Project", "Floor"): ["LOCATED_ON"],
            
            ("Project", "Interest"): ["RELATED_TO"],
            
            ("Event", "Interest"): ["RELATED_TO"],
        }

    async def connect(self):
        """Initialize the Graphiti client connection.
        
        Sets up the connection to the knowledge graph and optionally
        clears data and rebuilds indices in development environment.
        """
        try:
            self.graphiti = get_graphiti_client()
            logger.info("Graph service connected to Graphiti")
            if settings.APP_ENV == "dev":
                await clear_data(self.graphiti.driver)
                await self.graphiti.build_indices_and_constraints()
                logger.info("Development environment: Graph data cleared and indices rebuilt")
        except Exception as e:
            logger.error(f"Failed to connect to graph service: {e}")
            raise

    async def close(self):
        """Close the Graphiti client connection."""
        if self.graphiti:
            try:
                await self.graphiti.close()
                logger.info("Graph service connection closed")
            except Exception as e:
                logger.error(f"Error closing graph service connection: {e}")

    async def build_communities(self):
        """Build graph communities in production environment.
        
        Creates community structures within the knowledge graph
        to improve search and retrieval performance.
        """
        if settings.APP_ENV == "prod" and self.graphiti:
            try:
                await self.graphiti.build_communities()
                logger.info("Graph communities built successfully")
            except Exception as e:
                logger.error(f"Failed to build graph communities: {e}")

    async def process_telegram_message(self, message: TelegramMessage):
        """Process a Telegram message for knowledge graph integration.
        
        Handles both structured message storage and entity extraction
        from the message content.
        
        Args:
            message: Telegram message object to process
        """
        try:
            logger.debug(f"Processing message {message.message_id} for graph integration")
            await self._store_message_context(message)
            await self._add_episode(message)
            logger.debug(f"Successfully processed message {message.message_id}")
        except Exception as e:
            logger.error(f"Failed to process message {message.message_id}: {e}")
            raise

    async def check_user_exists(self, message: TelegramMessage):
        """Check if a user exists in the knowledge graph.
        
        Args:
            message: Telegram message containing user information
            
        Returns:
            bool: True if user exists in the graph, False otherwise
        """
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

    async def _store_message_context(self, message: TelegramMessage):
        """Add structured message data to the knowledge graph.
        
        Creates or updates User, Topic, and Message nodes and establishes
        relationships between them based on the Telegram message structure.
        
        Args:
            message: Telegram message to process and store
        """
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
            text=message.text or "",
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
        await self._add_edge("SENT_IN", message_node.message_id, topic_node.topic_id, "Message", "Topic")

        if message.reply_to_message and not message.reply_to_message.forum_topic_created:
            parent_message_id = message.reply_to_message.message_id
            await self._add_edge("IN_REPLY_TO", message_node.message_id, parent_message_id, "Message", "Message")

    async def _add_edge(
        self,
        edge_type: str,
        from_id: int,
        to_id: int,
        from_label: str,
        to_label: str
    ):
        """Add an edge relationship between two nodes in the graph.

        This method uses MERGE to idempotently create the nodes and the relationship,
        preventing errors if a node does not yet exist.

        Args:
            edge_type: Type of edge to create (e.g., 'SENT', 'IN_REPLY_TO')
            from_id: ID of the source node
            to_id: ID of the target node
            from_label: Label of the source node type
            to_label: Label of the target node type
        """
        id_fields = {
            "User": "user_id",
            "Message": "message_id",
            "Topic": "topic_id"
        }
        from_id_field = id_fields.get(from_label, "id")
        to_id_field = id_fields.get(to_label, "id")

        cypher = f"""
        MERGE (a:{from_label} {{{from_id_field}: $from_id}})
        MERGE (b:{to_label} {{{to_id_field}: $to_id}})
        MERGE (a)-[r:{edge_type}]->(b)
        RETURN r
        """
        await self.graphiti.driver.execute_query(
            cypher,
            from_id=from_id,
            to_id=to_id
        )

    async def _add_episode(self, message: TelegramMessage):
        """Add a new episode to the knowledge graph for a Telegram message.

        This method creates an episode in the knowledge graph representing the provided
        Telegram message, extracting and storing relevant entities and relationships
        (excluding User, Topic, and Message types) using Graphiti's processing.

        Args:
            message: The Telegram message to be represented as an episode in the graph.
        """
        await self.graphiti.add_episode(
            name=f"telegram_message_{message.message_id}",
            episode_body=message.to_json(),
            source=EpisodeType.json,
            source_description="TowerBot",
            reference_time=message.date.astimezone(timezone.utc),
            group_id=settings.GROUP_ID,
            entity_types=self.entity_types,
            excluded_entity_types=["User", "Topic", "Message", "Floor"],
            edge_types=self.edge_types,
            edge_type_map=self.edge_type_map,
            update_communities=True,
        )