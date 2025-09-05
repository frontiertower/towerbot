from typing import Optional
from dotenv import load_dotenv

from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    APP_ENV: str = "dev"
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_API_VERSION: Optional[str] = None
    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    BERLINHOUSE_API_KEY: Optional[str] = None
    BERLINHOUSE_BASE_URL: Optional[str] = None
    BOT_TOKEN: str
    DEFAULT_DATABASE: str
    EMBEDDING_MODEL: str
    GROUP_ID: str
    LANGSMITH_API_KEY: str
    LANGSMITH_PROJECT: str
    LANGSMITH_TRACING: bool = True
    MODEL: str
    NEO4J_PASSWORD: str
    NEO4J_URI: str
    NEO4J_USER: str
    NOTION_API_KEY: Optional[str] = None
    OAUTH_CLIENT_ID: Optional[str] = None
    OAUTH_CLIENT_SECRET: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    PORT: int = 8000
    POSTGRES_CONN_STRING: Optional[str] = None
    REASONING_MODEL: str
    RERANKER_MODEL: str
    SENTRY_DNS: Optional[str] = None
    WEBHOOK_URL: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
