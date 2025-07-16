from datetime import timezone

from telegram import Message
from openai import AsyncAzureOpenAI
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from graphiti_core.llm_client import LLMConfig, OpenAIClient
from graphiti_core.utils.maintenance.graph_data_operations import clear_data
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient

from app.core.config import settings
from app.models.ontology import User, Floor, Event, Interest, WorksOn, LocatedOn, Attends, InterestedIn, Project

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
        self.entity_types = {"User": User, "Floor": Floor, "Event": Event, "Interest": Interest, "Project": Project}
        self.edge_types = {
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
        await self.graphiti.close()

    async def build_communities(self):
        if settings.APP_ENV == "prod":
            await self.graphiti.build_communities()

    async def save_episode(self, message: Message):
        await self.graphiti.add_episode(
            name=f"telegram_message_{message.message_id}",
            episode_body=message.to_json(),
            source=EpisodeType.json,
            source_description="TowerBot",
            reference_time=message.date.astimezone(timezone.utc),
            group_id=settings.GROUP_ID,
            entity_types=self.entity_types,
            edge_types=self.edge_types,
            edge_type_map=self.edge_type_map,
            update_communities=True,
        )