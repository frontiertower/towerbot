"""Configuration settings module for TowerBot.

This module defines the comprehensive application configuration using Pydantic settings,
loading environment variables and providing type-safe access to configuration values.

The configuration supports TowerBot's multi-layered authentication system including:
- Basic Telegram group membership validation
- Soulink social proximity authentication
- BerlinHouse API integration
- Comprehensive security and monitoring settings

All settings are validated at startup and provide clear error messages for
misconfiguration issues.
"""

from dotenv import load_dotenv

from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

class Settings(BaseSettings):
    """Application settings configuration for TowerBot.
    
    This class defines all configuration parameters for the TowerBot application,
    including API keys, database connections, service endpoints, and the comprehensive
    multi-layered authentication system.
    
    Authentication Configuration:
        GROUP_ID: Primary Telegram group ID (required, must be numeric)
        ALLOWED_GROUP_IDS: Comma-separated additional group IDs (optional)
        SOULINK_ENABLED: Enable Soulink social proximity authentication (default: False)
        SOULINK_ADMIN_ID: Admin user ID for Soulink validation (required if SOULINK_ENABLED=True)
        
    Soulink Authentication System:
        Soulink is TowerBot's "social proximity" authentication layer that requires users
        to share at least one Telegram group with a designated admin. This creates a
        trust relationship based on social connections rather than just group membership.
        
        Soulink Mechanism:
        1. Admin configures their Telegram user ID in SOULINK_ADMIN_ID
        2. Bot discovers all groups where both user and admin are members
        3. If any shared groups exist, user passes Soulink authentication
        4. If no shared groups, user is denied access
        
        Soulink Use Cases:
        - Community gatekeeping: Ensure users are "vouched for" by shared membership
        - Multi-community access: Allow users across different communities you manage
        - Dynamic trust: Automatically grant/revoke access as relationships change
        - Social validation: Verify users have genuine connection to admin
        
        Soulink Configuration Examples:
        - SOULINK_ENABLED=false (default): Soulink disabled, only group membership checked
        - SOULINK_ENABLED=true + SOULINK_ADMIN_ID=123456789: Enables social proximity check
        - Works with GROUP_ID and ALLOWED_GROUP_IDS for comprehensive access control
    
    Service Configuration:
        BOT_TOKEN: Telegram bot token (required)
        WEBHOOK_URL: Webhook URL for Telegram updates (required)
        AZURE_OPENAI_API_KEY: Azure OpenAI service API key (required)
        AZURE_OPENAI_ENDPOINT: Azure OpenAI service endpoint URL (required)
        
    Database Configuration:
        POSTGRES_CONN_STRING: PostgreSQL connection string (required)
        NEO4J_URI: Neo4j database URI (required)
        NEO4J_USER: Neo4j database username (required)
        NEO4J_PASSWORD: Neo4j database password (required)
        DEFAULT_DATABASE: Default database name (required)
    
    BerlinHouse API Configuration:
        BERLINHOUSE_EMAIL: Email for BerlinHouse API authentication (required)
        BERLINHOUSE_PASSWORD: Password for BerlinHouse API authentication (required)
        
    AI Model Configuration:
        MODEL: Name of the main AI model to use (required)
        EMBEDDING_MODEL: Name of the embedding model to use (required)
        RERANKER_MODEL: Name of the reranker model to use (required)
    
    Monitoring & Analytics:
        LANGSMITH_API_KEY: LangSmith tracing API key (required)
        LANGSMITH_PROJECT: LangSmith project name (required)
        LANGSMITH_TRACING: Enable/disable LangSmith tracing (default: True)
    
    Other Configuration:
        APP_ENV: Application environment (default: "dev")
        PORT: Server port number (default: 3000)
        NOTION_API_KEY: Notion API key (required)
        
    Security Notes:
        - All group IDs must be numeric Telegram group IDs (negative numbers)
        - SOULINK_ADMIN_ID must be a positive integer if Soulink is enabled
        - Invalid configurations will be logged and handled gracefully
        - Bot will automatically leave unauthorized groups
    """
    APP_ENV: str = "dev"
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    BERLINHOUSE_API_KEY: str
    BOT_TOKEN: str
    DEFAULT_DATABASE: str
    EMBEDDING_MODEL: str
    GROUP_ID: str
    ALLOWED_GROUP_IDS: str = ""
    SOULINK_ENABLED: bool = False
    SOULINK_ADMIN_ID: str = ""
    LANGSMITH_API_KEY: str
    LANGSMITH_PROJECT: str
    LANGSMITH_TRACING: bool = True
    MODEL: str
    NEO4J_PASSWORD: str
    NEO4J_URI: str
    NEO4J_USER: str
    NOTION_API_KEY: str
    PORT: int = 3000
    POSTGRES_CONN_STRING: str
    REASONING_MODEL: str
    RERANKER_MODEL: str
    WEBHOOK_URL: str

    model_config = SettingsConfigDict(env_file=".env", extra='ignore')

settings = Settings()
"""Global settings instance for the TowerBot application.

This is the main configuration object used throughout the application.
It automatically loads values from environment variables and .env files.

The settings instance provides:
- Type-safe access to all configuration parameters
- Automatic validation of required fields
- Default values for optional parameters
- Integration with TowerBot's multi-layered authentication system

Usage:
    from app.core.config import settings
    
    if settings.SOULINK_ENABLED:
        admin_id = settings.SOULINK_ADMIN_ID
    
    bot_token = settings.BOT_TOKEN
    webhook_url = settings.WEBHOOK_URL
    
Configuration files are loaded in this order:
1. .env file (if present)
2. Environment variables (override .env values)
3. Default values (for optional parameters)
"""