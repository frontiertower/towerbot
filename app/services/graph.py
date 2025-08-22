"""Graph service module for TowerBot knowledge graph operations.

This module provides the GraphService class and related functionality for managing
the knowledge graph using Graphiti, including entity extraction, relationship mapping,
and Telegram message processing.
"""

import logging

from datetime import timezone

from graphiti_core import Graphiti
from openai import AsyncOpenAI
from telegram import Message as TelegramMessage
from graphiti_core.nodes import EpisodeType, EpisodicNode
from graphiti_core.llm_client import LLMConfig, OpenAIClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
from graphiti_core.utils.maintenance.graph_data_operations import clear_data

from app.core.config import settings
from app.schemas.generated_enums import EDGE_TYPE_MAP, NodeTypeEnum, EdgeTypeEnum
from app.schemas.ontology import (
    User, Topic, Message, Sent, InReplyTo, SentIn, 
    Event, Interest, Project, WorksOn, LocatedOn, Attends, InterestedIn, Floor, RelatedTo
)

logger = logging.getLogger(__name__)

def get_graphiti_client():
    """Create and configure a Graphiti client instance.
    
    Initializes a Graphiti client with OpenAI services for LLM operations,
    embeddings, and cross-encoding, along with Neo4j database connectivity.
    
    Returns:
        Graphiti: Configured Graphiti client instance
    """
    neo4j_uri = settings.NEO4J_URI
    neo4j_user = settings.NEO4J_USER
    neo4j_password = settings.NEO4J_PASSWORD

    return Graphiti(
        neo4j_uri,
        neo4j_user,
        neo4j_password
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
            NodeTypeEnum.User.value: User,
            NodeTypeEnum.Topic.value: Topic,
            NodeTypeEnum.Message.value: Message,
            NodeTypeEnum.Event.value: Event,
            NodeTypeEnum.Interest.value: Interest,
            NodeTypeEnum.Project.value: Project,
            NodeTypeEnum.Floor.value: Floor
        }
        self.edge_types = {
            EdgeTypeEnum.Sent.value: Sent,
            EdgeTypeEnum.SentIn.value: SentIn,
            EdgeTypeEnum.InReplyTo.value: InReplyTo,
            EdgeTypeEnum.LocatedOn.value: LocatedOn,
            EdgeTypeEnum.WorksOn.value: WorksOn,
            EdgeTypeEnum.Attends.value: Attends,
            EdgeTypeEnum.InterestedIn.value: InterestedIn,
            EdgeTypeEnum.RelatedTo.value: RelatedTo,
        }
        self.edge_type_map = EDGE_TYPE_MAP

    async def connect(self):
        """Initialize the Graphiti client connection.
        
        Sets up the connection to the knowledge graph and optionally
        clears data and rebuilds indices in development environment.
        """
        try:
            self.graphiti = get_graphiti_client()
            logger.info("Graph service connected to Graphiti")
            # Clears the whole database. Only needed for a bug with node, don't clear everytime
            # await clear_data(self.graphiti.driver)
            await self.graphiti.build_indices_and_constraints()
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

    async def add_episode(self, message: TelegramMessage):
        """Add a new episode to the knowledge graph for a Telegram message.

        This method creates an episode in the knowledge graph representing the provided
        Telegram message, extracting and storing relevant entities and relationships
        (excluding Topic and Floor types) using Graphiti's temporal processing.
        Episodes are automatically assigned to the configured group ID for organization.

        Args:
            message: The Telegram message to be represented as an episode in the graph.
        """
        try:
            await self.graphiti.add_episode(
                name=f"telegram_message_{message.message_id}",
                episode_body=message.to_json(),
                source=EpisodeType.json,
                source_description="TowerBot",
                reference_time=message.date.astimezone(timezone.utc),
                group_id=str(settings.GROUP_ID),
                entity_types=self.entity_types,
                excluded_entity_types=["Topic", "Floor"],
                edge_types=self.edge_types,
                edge_type_map=self.edge_type_map,
            )
        except Exception as e:
            logger.error(f"Failed to process message {message.message_id}: {e}")
            raise

    async def reprocess_all_episodes(self):
        """Reprocess all episodes in the knowledge graph.

        This method reprocesses all episodes in the knowledge graph,
        updating the graph with the latest information while handling
        duplicate users by excluding User entities from reprocessing.
        """
        try:
            episodes = await EpisodicNode.get_by_group_ids(
                self.graphiti.driver,
                group_ids=[str(settings.GROUP_ID)]
            )

            await self.graphiti.add_episode_bulk(
                episodes,
                entity_types=self.entity_types,
                excluded_entity_types=["Topic", "Floor"],
                edge_types=self.edge_types,
                edge_type_map=self.edge_type_map,
            )
            logger.info(f"Reprocessed {len(episodes)} episodes")
        except Exception as e:
            logger.error(f"Failed to reprocess episodes: {e}")
            raise

graph_service = GraphService()