
import logging

from datetime import timezone

from graphiti_core import Graphiti
from openai import AsyncAzureOpenAI
from telegram import Message as TelegramMessage
from graphiti_core.nodes import EpisodeType, EpisodicNode
from graphiti_core.llm_client import LLMConfig, OpenAIClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient

from app.core.config import settings
from app.schemas.generated_enums import EDGE_TYPE_MAP, NodeTypeEnum, EdgeTypeEnum
from app.schemas.ontology import (
    User, Topic, Message, Sent, InReplyTo, SentIn, 
    Event, Interest, Project, WorksOn, LocatedOn, Attends, InterestedIn, Floor, RelatedTo
)

logger = logging.getLogger(__name__)

def get_graphiti_client():
    neo4j_uri = settings.NEO4J_URI
    neo4j_user = settings.NEO4J_USER
    neo4j_password = settings.NEO4J_PASSWORD

    if settings.OPENAI_API_KEY:
        return Graphiti(
            neo4j_uri,
            neo4j_user,
            neo4j_password
        )
    else:
        api_key = settings.AZURE_OPENAI_API_KEY
        api_version = settings.AZURE_OPENAI_API_VERSION
        llm_endpoint = settings.AZURE_OPENAI_ENDPOINT
        embedding_endpoint = settings.AZURE_OPENAI_ENDPOINT

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
        try:
            self.graphiti = get_graphiti_client()
            logger.info("Graph service connected to Graphiti")
            await self.graphiti.build_indices_and_constraints()
        except Exception as e:
            logger.error(f"Failed to connect to graph service: {e}")
            raise

    async def close(self):
        if self.graphiti:
            try:
                await self.graphiti.close()
                logger.info("Graph service connection closed")
            except Exception as e:
                logger.error(f"Error closing graph service connection: {e}")

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

    async def add_episode(self, message: TelegramMessage):
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