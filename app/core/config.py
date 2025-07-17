"""Configuration settings module for TowerBot.

This module defines the application configuration using Pydantic settings,
loading environment variables and providing type-safe access to configuration values.
"""

from dotenv import load_dotenv

from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

class Settings(BaseSettings):
    """Application settings configuration.
    
    This class defines all configuration parameters for the TowerBot application,
    including API keys, database connections, and service endpoints. Settings are
    loaded from environment variables with optional .env file support.
    
    Attributes:
        APP_ENV: Application environment (dev/prod)
        AZURE_OPENAI_API_KEY: Azure OpenAI service API key
        AZURE_OPENAI_ENDPOINT: Azure OpenAI service endpoint URL
        BERLINHOUSE_EMAIL: Email for BerlinHouse API authentication
        BERLINHOUSE_PASSWORD: Password for BerlinHouse API authentication
        BOT_TOKEN: Telegram bot token
        DEFAULT_DATABASE: Default database name
        EMBEDDING_MODEL: Name of the embedding model to use
        GROUP_ID: Telegram group ID for bot operations
        LANGSMITH_API_KEY: LangSmith tracing API key
        LANGSMITH_PROJECT: LangSmith project name
        LANGSMITH_TRACING: Enable/disable LangSmith tracing
        MODEL: Name of the main AI model to use
        NEO4J_PASSWORD: Neo4j database password
        NEO4J_URI: Neo4j database URI
        NEO4J_USER: Neo4j database username
        NOTION_API_KEY: Notion API key
        PORT: Server port number
        RERANKER_MODEL: Name of the reranker model to use
        SUPABASE_ANON_KEY: Supabase anonymous key
        SUPABASE_CONN_STRING: Supabase database connection string
        SUPABASE_SERVICE_ROLE_KEY: Supabase service role key
        SUPABASE_URL: Supabase project URL
        WEBHOOK_URL: Webhook URL for external integrations
    """
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
    RERANKER_MODEL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_CONN_STRING: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_URL: str
    WEBHOOK_URL: str

    model_config = SettingsConfigDict(env_file=".env", extra='ignore')

settings = Settings()
"""Global settings instance for the application.

This is the main configuration object used throughout the application.
It automatically loads values from environment variables and .env files.
"""