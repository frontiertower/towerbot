"""Tests for configuration settings."""

import pytest
from unittest.mock import patch, Mock
import os

from app.core.config import Settings, settings


class TestSettings:
    """Test cases for Settings class."""
    
    @patch.dict(os.environ, {}, clear=True)
    def test_settings_defaults(self):
        """Test default values in settings."""
        test_settings = Settings(
            AZURE_OPENAI_API_KEY="test-key",
            AZURE_OPENAI_ENDPOINT="https://test.openai.azure.com",
            BERLINHOUSE_EMAIL="test@example.com",
            BERLINHOUSE_PASSWORD="password",
            BOT_TOKEN="test-bot-token",
            DEFAULT_DATABASE="test-db",
            EMBEDDING_MODEL="text-embedding-ada-002",
            GROUP_ID="-1001234567890",
            LANGSMITH_API_KEY="test-langsmith-key",
            LANGSMITH_PROJECT="test-project",
            MODEL="gpt-4",
            NEO4J_PASSWORD="neo4j-password",
            NEO4J_URI="neo4j://localhost:7687",
            NEO4J_USER="neo4j",
            NOTION_API_KEY="test-notion-key",
            POSTGRES_CONN_STRING="postgresql://test@localhost/test",
            RERANKER_MODEL="gpt-3.5-turbo",
            WEBHOOK_URL="https://test.webhook.com"
        )
        
        # Test default values
        assert test_settings.APP_ENV == "dev"
        assert test_settings.PORT == 3000
        assert test_settings.ALLOWED_GROUP_IDS == ""
        assert test_settings.SOULINK_ENABLED is False
        assert test_settings.SOULINK_ADMIN_ID == ""
        assert test_settings.LANGSMITH_TRACING is True

    def test_settings_custom_values(self):
        """Test settings with custom values."""
        test_settings = Settings(
            APP_ENV="prod",
            AZURE_OPENAI_API_KEY="custom-key",
            AZURE_OPENAI_ENDPOINT="https://custom.openai.azure.com",
            BERLINHOUSE_EMAIL="custom@example.com",
            BERLINHOUSE_PASSWORD="custom-password",
            BOT_TOKEN="custom-bot-token",
            DEFAULT_DATABASE="custom-db",
            EMBEDDING_MODEL="custom-embedding-model",
            GROUP_ID="-1009876543210",
            ALLOWED_GROUP_IDS="-1001111111111,-1002222222222",
            SOULINK_ENABLED=True,
            SOULINK_ADMIN_ID="987654321",
            LANGSMITH_API_KEY="custom-langsmith-key",
            LANGSMITH_PROJECT="custom-project",
            LANGSMITH_TRACING=False,
            MODEL="gpt-3.5-turbo",
            NEO4J_PASSWORD="custom-neo4j-password",
            NEO4J_URI="neo4j://custom.neo4j.com:7687",
            NEO4J_USER="custom-neo4j-user",
            NOTION_API_KEY="custom-notion-key",
            PORT=8080,
            POSTGRES_CONN_STRING="postgresql://custom@custom.postgres.com/custom",
            RERANKER_MODEL="custom-reranker",
            WEBHOOK_URL="https://custom.webhook.com"
        )
        
        assert test_settings.APP_ENV == "prod"
        assert test_settings.PORT == 8080
        assert test_settings.ALLOWED_GROUP_IDS == "-1001111111111,-1002222222222"
        assert test_settings.SOULINK_ENABLED is True
        assert test_settings.SOULINK_ADMIN_ID == "987654321"
        assert test_settings.LANGSMITH_TRACING is False
        assert test_settings.AZURE_OPENAI_API_KEY == "custom-key"
        assert test_settings.BOT_TOKEN == "custom-bot-token"

    @patch.dict(os.environ, {}, clear=True)
    def test_required_fields(self):
        """Test that required fields raise ValidationError when missing."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Settings()

    def test_required_fields_individual(self):
        """Test individual required fields."""
        base_settings = {
            "AZURE_OPENAI_API_KEY": "test",
            "AZURE_OPENAI_ENDPOINT": "https://test.com",
            "BERLINHOUSE_EMAIL": "test@test.com",
            "BERLINHOUSE_PASSWORD": "test",
            "BOT_TOKEN": "test",
            "DEFAULT_DATABASE": "test",
            "EMBEDDING_MODEL": "test",
            "GROUP_ID": "test",
            "LANGSMITH_API_KEY": "test",
            "LANGSMITH_PROJECT": "test",
            "MODEL": "test",
            "NEO4J_PASSWORD": "test",
            "NEO4J_URI": "test",
            "NEO4J_USER": "test",
            "NOTION_API_KEY": "test",
            "POSTGRES_CONN_STRING": "test",
            "RERANKER_MODEL": "test",
            "WEBHOOK_URL": "test",
        }
        
        # Test that all required fields are present
        settings_instance = Settings(**base_settings)
        assert settings_instance.BOT_TOKEN == "test"
        
        # Test missing required field
        incomplete_settings = base_settings.copy()
        del incomplete_settings["BOT_TOKEN"]
        
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            Settings(**incomplete_settings)

    @patch.dict(os.environ, {
        'AZURE_OPENAI_API_KEY': 'env-key',
        'BOT_TOKEN': 'env-bot-token',
        'APP_ENV': 'env-prod'
    }, clear=False)
    def test_environment_variable_loading(self):
        """Test that environment variables are properly loaded."""
        # Create minimal required settings, letting env vars fill in some values
        base_required = {
            "AZURE_OPENAI_ENDPOINT": "https://test.com",
            "BERLINHOUSE_EMAIL": "test@test.com", 
            "BERLINHOUSE_PASSWORD": "test",
            "DEFAULT_DATABASE": "test",
            "EMBEDDING_MODEL": "test",
            "GROUP_ID": "test",
            "LANGSMITH_API_KEY": "test",
            "LANGSMITH_PROJECT": "test", 
            "MODEL": "test",
            "NEO4J_PASSWORD": "test",
            "NEO4J_URI": "test",
            "NEO4J_USER": "test",
            "NOTION_API_KEY": "test",
            "POSTGRES_CONN_STRING": "test",
            "RERANKER_MODEL": "test",
            "WEBHOOK_URL": "test",
        }
        
        test_settings = Settings(**base_required)
        
        # These should come from environment variables
        assert test_settings.AZURE_OPENAI_API_KEY == 'env-key'
        assert test_settings.BOT_TOKEN == 'env-bot-token'
        assert test_settings.APP_ENV == 'env-prod'

    def test_global_settings_instance(self):
        """Test that the global settings instance exists."""
        # The global settings instance should be importable and valid
        assert settings is not None
        assert isinstance(settings, Settings)

    def test_settings_model_config(self):
        """Test settings model configuration."""
        test_settings = Settings(
            AZURE_OPENAI_API_KEY="test",
            AZURE_OPENAI_ENDPOINT="https://test.com",
            BERLINHOUSE_EMAIL="test@test.com",
            BERLINHOUSE_PASSWORD="test",
            BOT_TOKEN="test",
            DEFAULT_DATABASE="test",
            EMBEDDING_MODEL="test",
            GROUP_ID="test",
            LANGSMITH_API_KEY="test",
            LANGSMITH_PROJECT="test",
            MODEL="test",
            NEO4J_PASSWORD="test",
            NEO4J_URI="test",
            NEO4J_USER="test",
            NOTION_API_KEY="test",
            POSTGRES_CONN_STRING="test",
            RERANKER_MODEL="test",
            WEBHOOK_URL="test",
        )
        
        # Verify model config attributes
        config = test_settings.model_config
        assert config.get('env_file') == '.env'
        assert config.get('extra') == 'ignore'

    @patch.dict(os.environ, {}, clear=True)
    def test_soulink_configuration(self):
        """Test Soulink authentication configuration options."""
        # Test disabled Soulink
        test_settings = Settings(
            AZURE_OPENAI_API_KEY="test",
            AZURE_OPENAI_ENDPOINT="https://test.com",
            BERLINHOUSE_EMAIL="test@test.com",
            BERLINHOUSE_PASSWORD="test",
            BOT_TOKEN="test",
            DEFAULT_DATABASE="test",
            EMBEDDING_MODEL="test",
            GROUP_ID="test",
            LANGSMITH_API_KEY="test",
            LANGSMITH_PROJECT="test",
            MODEL="test",
            NEO4J_PASSWORD="test",
            NEO4J_URI="test",
            NEO4J_USER="test",
            NOTION_API_KEY="test",
            POSTGRES_CONN_STRING="test",
            RERANKER_MODEL="test",
            WEBHOOK_URL="test",
            SOULINK_ENABLED=False
        )
        
        assert test_settings.SOULINK_ENABLED is False
        assert test_settings.SOULINK_ADMIN_ID == ""
        
        # Test enabled Soulink
        test_settings_enabled = Settings(
            AZURE_OPENAI_API_KEY="test",
            AZURE_OPENAI_ENDPOINT="https://test.com",
            BERLINHOUSE_EMAIL="test@test.com",
            BERLINHOUSE_PASSWORD="test",
            BOT_TOKEN="test",
            DEFAULT_DATABASE="test",
            EMBEDDING_MODEL="test",
            GROUP_ID="test",
            LANGSMITH_API_KEY="test",
            LANGSMITH_PROJECT="test",
            MODEL="test",
            NEO4J_PASSWORD="test",
            NEO4J_URI="test",
            NEO4J_USER="test",
            NOTION_API_KEY="test",
            POSTGRES_CONN_STRING="test",
            RERANKER_MODEL="test",
            WEBHOOK_URL="test",
            SOULINK_ENABLED=True,
            SOULINK_ADMIN_ID="123456789"
        )
        
        assert test_settings_enabled.SOULINK_ENABLED is True
        assert test_settings_enabled.SOULINK_ADMIN_ID == "123456789"