from dotenv import load_dotenv

from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

class Settings(BaseSettings):
    APP_ENV: str = "dev"
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    BERLINHOUSE_EMAIL: str
    BERLINHOUSE_PASSWORD: str
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
    NOTION_API_KEY: str
    PORT: int = 3000
    REASONING_MODEL: str
    RERANKER_MODEL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_URL: str
    WEBHOOK_URL: str

    model_config = SettingsConfigDict(env_file=".env", extra='ignore')

settings = Settings()