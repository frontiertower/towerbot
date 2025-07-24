"""Test configuration and fixtures for TowerBot."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime
from telegram import User as TelegramUser, Message as TelegramMessage, Chat

from app.services.ai import AiService
from app.services.graph import GraphService
from app.core.config import Settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock(spec=Settings)
    settings.APP_ENV = "test"
    settings.AZURE_OPENAI_API_KEY = "test-key"
    settings.AZURE_OPENAI_ENDPOINT = "https://test.openai.azure.com"
    settings.BOT_TOKEN = "test-bot-token"
    settings.GROUP_ID = "-1001234567890"
    settings.ALLOWED_GROUP_IDS = ""
    settings.SOULINK_ENABLED = False
    settings.SOULINK_ADMIN_ID = ""
    settings.WEBHOOK_URL = "https://test.webhook.com"
    settings.NEO4J_URI = "neo4j://localhost:7687"
    settings.NEO4J_USER = "neo4j"
    settings.NEO4J_PASSWORD = "password"
    settings.POSTGRES_CONN_STRING = "postgresql://test@localhost/test"
    settings.MODEL = "gpt-4"
    settings.EMBEDDING_MODEL = "text-embedding-ada-002"
    settings.RERANKER_MODEL = "gpt-3.5-turbo"
    settings.BERLINHOUSE_API_KEY = "test-api-key"
    settings.BERLINHOUSE_BASE_URL = "https://api.berlinhouse.com"
    settings.LANGSMITH_API_KEY = "test-key"
    settings.LANGSMITH_PROJECT = "test-project"
    settings.NOTION_API_KEY = "test-notion-key"
    return settings


@pytest.fixture
def mock_telegram_user():
    """Mock Telegram user for testing."""
    return TelegramUser(
        id=123456789,
        is_bot=False,
        first_name="Test",
        last_name="User",
        username="testuser"
    )


@pytest.fixture
def mock_telegram_message(mock_telegram_user):
    """Mock Telegram message for testing."""
    chat = Chat(id=-1001234567890, type="supergroup")
    message = Mock(spec=TelegramMessage)
    message.message_id = 12345
    message.from_user = mock_telegram_user
    message.chat = chat
    message.text = "Test message"
    message.date = datetime.now()
    message.to_json.return_value = '{"message_id": 12345, "text": "Test message"}'
    return message


@pytest.fixture
def mock_llm():
    """Mock Azure OpenAI LLM for testing."""
    llm = AsyncMock()
    llm.ainvoke.return_value = Mock(content="Test AI response")
    return llm


@pytest.fixture
def mock_store():
    """Mock PostgreSQL store for testing."""
    return Mock()


@pytest.fixture
def mock_checkpointer():
    """Mock PostgreSQL checkpointer for testing."""
    return Mock()


@pytest.fixture
def mock_graphiti():
    """Mock Graphiti client for testing."""
    graphiti = AsyncMock()
    graphiti.driver = Mock()
    graphiti.driver.execute_query.return_value = Mock(records=[])
    graphiti.add_episode = AsyncMock()
    graphiti.add_episode_bulk = AsyncMock()
    graphiti.build_indices_and_constraints = AsyncMock()
    graphiti.build_communities = AsyncMock()
    graphiti.close = AsyncMock()
    graphiti.search_ = AsyncMock(return_value=[])
    return graphiti


@pytest.fixture
def ai_service():
    """Create AiService instance for testing."""
    return AiService()


@pytest.fixture
def graph_service():
    """Create GraphService instance for testing."""
    return GraphService()