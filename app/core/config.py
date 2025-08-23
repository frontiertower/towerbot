
from dotenv import load_dotenv

from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

class Settings(BaseSettings):
    ALLOWED_GROUP_IDS: str = ""
    APP_ENV: str = "dev"
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    BERLINHOUSE_API_KEY: str = ""
    BERLINHOUSE_BASE_URL: str = ""
    BOT_TOKEN: str
    DEFAULT_DATABASE: str = "neo4j"
    EMBEDDING_MODEL: str
    GROUP_ID: str
    LANGSMITH_API_KEY: str
    LANGSMITH_PROJECT: str
    LANGSMITH_TRACING: bool = True
    MODEL: str
    NEO4J_PASSWORD: str
    NEO4J_URI: str
    NEO4J_USER: str
    NOTION_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    PORT: int = 3000
    POSTGRES_CONN_STRING: str
    REASONING_MODEL: str
    RERANKER_MODEL: str
    SOULINK_ADMIN_ID: str = ""
    SOULINK_ENABLED: bool = False
    WEBHOOK_URL: str

    model_config = SettingsConfigDict(env_file=".env", extra='ignore')

settings = Settings()