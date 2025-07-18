"""AI service module for TowerBot intelligent agent operations.

This module provides the AiService class for managing AI agents that handle
user queries and connection requests using LangChain and LangGraph frameworks.
"""
import uuid
import logging

from datetime import datetime

from langchain_openai import AzureChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.store.postgres.base import BasePostgresStore
from langgraph.checkpoint.postgres.base import BasePostgresSaver
from langmem import create_manage_memory_tool, create_search_memory_tool

from app.core.constants import SYSTEM_PROMPT
from app.schemas.responses import QuestionResponse, ConnectionResponse
from app.core.tools import get_qa_agent_tools, get_connect_agent_tools

logger = logging.getLogger(__name__)

class AiService:
    """Service class for managing AI agents and processing user requests.
    
    This class handles the creation and management of two specialized AI agents:
    - QA Agent: Handles general questions and information retrieval
    - Connect Agent: Handles connection requests and network searches
    
    Both agents use memory storage and checkpointing for conversation continuity.
    
    Attributes:
        qa_agent: Question-answering agent for general queries
        connect_agent: Connection agent for network and relationship queries
    """
    def __init__(self):
        """Initialize the AiService with empty agent references."""
        self.qa_agent = None
        self.connect_agent = None
        self.user_sessions = {}  # Track active sessions per user

    def connect(self, llm: AzureChatOpenAI, store: BasePostgresStore, checkpointer: BasePostgresSaver):
        """Initialize and configure the AI agents.
        
        Creates both QA and Connect agents with their respective tools,
        memory management, and checkpointing capabilities.
        
        Args:
            llm: Azure OpenAI language model instance
            store: PostgreSQL store for agent memory
            checkpointer: PostgreSQL checkpointer for conversation state
        """
        try:
            self.qa_agent = create_react_agent(
                name="Ask",
                model=llm,
                response_format=QuestionResponse,
                tools=[
                    *get_qa_agent_tools(llm),
                    create_manage_memory_tool(namespace=("memories", "{user_id}"), store=store),
                    create_search_memory_tool(namespace=("memories", "{user_id}"), store=store),
                ],
                store=store,
                checkpointer=checkpointer,
            )
            self.connect_agent = create_react_agent(
                name="Connect",
                model=llm,
                response_format=ConnectionResponse,
                tools=[
                    *get_connect_agent_tools(),
                    create_manage_memory_tool(namespace=("memories", "{user_id}"), store=store),
                    create_search_memory_tool(namespace=("memories", "{user_id}"), store=store),
                ],
                store=store,
                checkpointer=checkpointer,
            )
            logger.info("AI agents initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AI agents: {e}")
            raise

    def _get_or_create_session(self, user_id: int, command: str) -> str:
        """Get existing session or create new one for user+command combination."""
        session_key = f"{user_id}_{command}"
        
        # Check if user has an active session for this command type
        if session_key in self.user_sessions:
            # Check if session is recent (within last hour)
            session_time = self.user_sessions[session_key]['created_at']
            if (datetime.now() - session_time).seconds < 3600:
                return self.user_sessions[session_key]['thread_id']
        
        # Create new session
        thread_id = f"{user_id}_{command}_{uuid.uuid4().hex[:8]}"
        self.user_sessions[session_key] = {
            'thread_id': thread_id,
            'created_at': datetime.now()
        }
        return thread_id

    async def run(self, command: str, message: str, user_id: int):
        """Execute a command using the appropriate AI agent.
        
        Routes the command to either the QA or Connect agent based on
        the command type and processes the user's message.
        
        Args:
            command: The command type ('ask', 'report', 'propose', or 'connect')
            message: User's message content
            user_id: Unique identifier for the user
            
        Returns:
            The structured response from the appropriate agent
            
        Raises:
            RuntimeError: If agents are not initialized
        """
        agent = self.qa_agent if command in ["ask", "report", "propose"] else self.connect_agent

        if not agent:
            logger.error(f"Agent for command '{command}' not initialized")
            raise RuntimeError("Agent not initialized. Call connect() on startup.")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.format(system_time="now")},
            {"role": "user", "content": message}
        ]

        thread_id = self._get_or_create_session(user_id, command)
        
        config = {
            'recursion_limit': 50,
            "configurable": {
                "user_id": str(user_id),
                "thread_id": thread_id
            }
        }

        try:
            logger.debug(f"Processing {command} command for user {user_id}")
            response = await agent.ainvoke(
                {"messages": messages},
                config=config
            )
            logger.debug(f"Successfully processed {command} command for user {user_id}")
            return response["structured_response"]
        except Exception as e:
            logger.error(f"Failed to process {command} command for user {user_id}: {e}")
            raise