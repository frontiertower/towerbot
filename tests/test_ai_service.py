"""Tests for AI service functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from app.services.ai import AiService


class TestAiService:
    """Test cases for AiService class."""

    def test_init(self, ai_service):
        """Test AiService initialization."""
        assert ai_service.bot is None
        assert ai_service.llm is None
        assert isinstance(ai_service.user_sessions, dict)
        assert len(ai_service.user_sessions) == 0

    def test_connect(self, ai_service, mock_llm, mock_store, mock_checkpointer):
        """Test connecting the AI service."""
        with patch('app.services.ai.create_react_agent') as mock_create_agent:
            mock_bot = Mock()
            mock_create_agent.return_value = mock_bot
            
            ai_service.connect(mock_llm, mock_store, mock_checkpointer)
            
            assert ai_service.llm == mock_llm
            assert ai_service.bot == mock_bot
            mock_create_agent.assert_called_once()

    def test_get_or_create_session_new(self, ai_service):
        """Test creating a new session."""
        user_id = 123456789
        command = "direct"
        
        thread_id = ai_service._get_or_create_session(user_id, command)
        
        assert thread_id.startswith(f"{user_id}_{command}_")
        assert f"{user_id}_{command}" in ai_service.user_sessions
        session = ai_service.user_sessions[f"{user_id}_{command}"]
        assert session['thread_id'] == thread_id
        assert isinstance(session['created_at'], datetime)

    def test_get_or_create_session_existing_valid(self, ai_service):
        """Test retrieving an existing valid session."""
        user_id = 123456789
        command = "direct"
        session_key = f"{user_id}_{command}"
        thread_id = f"{user_id}_{command}_test123"
        
        # Create an existing session that's less than 24 hours old
        ai_service.user_sessions[session_key] = {
            'thread_id': thread_id,
            'created_at': datetime.now() - timedelta(hours=12)
        }
        
        result_thread_id = ai_service._get_or_create_session(user_id, command)
        
        assert result_thread_id == thread_id

    def test_get_or_create_session_existing_expired(self, ai_service):
        """Test creating a new session when the existing one is expired."""
        user_id = 123456789
        command = "direct"
        session_key = f"{user_id}_{command}"
        old_thread_id = f"{user_id}_{command}_old123"
        
        # Create an existing session that's more than 24 hours old
        ai_service.user_sessions[session_key] = {
            'thread_id': old_thread_id,
            'created_at': datetime.now() - timedelta(hours=25)
        }
        
        new_thread_id = ai_service._get_or_create_session(user_id, command)
        
        assert new_thread_id != old_thread_id
        assert new_thread_id.startswith(f"{user_id}_{command}_")

    @pytest.mark.asyncio
    @patch('app.services.ai.create_tool_calling_agent')
    @patch('app.services.ai.AgentExecutor')
    async def test_handle_ask(self, mock_executor_class, mock_create_agent, ai_service, mock_llm):
        """Test handling /ask command."""
        ai_service.llm = mock_llm
        ai_service.client = Mock()
        ai_service.client.pull_prompt.return_value = Mock()
        
        mock_agent = Mock()
        mock_create_agent.return_value = mock_agent
        
        mock_executor = Mock()
        mock_executor.ainvoke = AsyncMock(return_value={"output": "Test response"})
        mock_executor_class.return_value = mock_executor
        
        with patch('app.services.ai.get_qa_agent_tools', return_value=[]):
            result = await ai_service.handle_ask("What is the weather?")
            
            assert result == "Test response"
            mock_executor.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.ai.create_tool_calling_agent')
    @patch('app.services.ai.AgentExecutor')
    async def test_handle_connect(self, mock_executor_class, mock_create_agent, ai_service, mock_llm):
        """Test handling /connect command."""
        ai_service.llm = mock_llm
        ai_service.client = Mock()
        ai_service.client.pull_prompt.return_value = Mock()
        
        mock_agent = Mock()
        mock_create_agent.return_value = mock_agent
        
        mock_executor = Mock()
        mock_executor.ainvoke = AsyncMock(return_value={"output": "Connection response"})
        mock_executor_class.return_value = mock_executor
        
        with patch('app.services.ai.get_connect_agent_tools', return_value=[]):
            result = await ai_service.handle_connect("I'm interested in AI")
            
            assert result == "Connection response"
            mock_executor.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.ai.create_tool_calling_agent')
    @patch('app.services.ai.AgentExecutor')
    async def test_handle_request(self, mock_executor_class, mock_create_agent, ai_service, mock_llm):
        """Test handling /request command."""
        ai_service.llm = mock_llm
        ai_service.client = Mock()
        ai_service.client.pull_prompt.return_value = Mock()
        
        mock_agent = Mock()
        mock_create_agent.return_value = mock_agent
        
        mock_executor = Mock()
        mock_executor.ainvoke = AsyncMock(return_value={"output": "Supply request created"})
        mock_executor_class.return_value = mock_executor
        
        with patch('app.services.ai.get_request_agent_tools', return_value=[]):
            result = await ai_service.handle_request("I need office supplies")
            
            assert result == "Supply request created"
            mock_executor.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_agent(self, ai_service):
        """Test the conversational agent."""
        user_id = 123456789
        message = "Hello, how are you?"
        
        mock_bot = AsyncMock()
        mock_bot.ainvoke.return_value = {
            "messages": [Mock(content="I'm doing well, thank you!")]
        }
        ai_service.bot = mock_bot
        
        # Mock the client and prompt
        ai_service.client = Mock()
        mock_prompt = Mock()
        mock_prompt.messages = [Mock()]
        mock_prompt.messages[0].prompt.template = "Test system prompt {system_time}"
        ai_service.client.pull_prompt.return_value = mock_prompt
        
        result = await ai_service.agent(message, user_id)
        
        assert result == "I'm doing well, thank you!"
        mock_bot.ainvoke.assert_called_once()
        
        # Verify session was created
        session_key = f"{user_id}_direct"
        assert session_key in ai_service.user_sessions

    @pytest.mark.asyncio
    async def test_agent_no_bot(self, ai_service):
        """Test agent method when bot is not connected."""
        user_id = 123456789
        message = "Hello"
        
        # Bot is None by default
        with pytest.raises(AttributeError):
            await ai_service.agent(message, user_id)

    def test_session_cleanup_logic(self, ai_service):
        """Test session cleanup logic with different time scenarios."""
        user_id = 123456789
        command = "test"
        session_key = f"{user_id}_{command}"
        
        # Test session exactly at 24 hour boundary
        ai_service.user_sessions[session_key] = {
            'thread_id': 'old_thread',
            'created_at': datetime.now() - timedelta(hours=24, seconds=1)
        }
        
        new_thread = ai_service._get_or_create_session(user_id, command)
        assert new_thread != 'old_thread'