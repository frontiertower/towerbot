import uuid
import logging

from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from langsmith import Client
from langchain_openai import AzureChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.store.postgres.base import BasePostgresStore
from langgraph.checkpoint.postgres.base import BasePostgresSaver
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langmem import create_manage_memory_tool, create_search_memory_tool

from app.core.constants import SYSTEM_PROMPT
from app.core.tools import get_qa_agent_tools, get_connect_agent_tools

logger = logging.getLogger(__name__)

class AiService:
    """AI service for managing conversational agents and LLM interactions.
    
    This service provides AI-powered capabilities for TowerBot including:
    - Memory-enabled conversation agents for direct messages
    - Specialized command handlers for /ask and /connect commands
    - Session management for conversation continuity
    - Integration with LangChain tools and agents
    """
    def __init__(self):
        self.bot = None
        self.client = Client()
        self.llm: Optional[AzureChatOpenAI] = None
        self.user_sessions: Dict[str, Dict[str, Any]] = {}

    def connect(self, llm: AzureChatOpenAI, store: BasePostgresStore, checkpointer: BasePostgresSaver):
        """Initialize the AI service with required components.
        
        Args:
            llm: Azure OpenAI language model instance
            store: PostgreSQL store for vector embeddings and memory
            checkpointer: PostgreSQL checkpointer for conversation state
        """
        self.llm = llm
        self.bot = create_react_agent(
            name="TowerBot",
            model=self.llm,
            tools=[
                *get_connect_agent_tools(),
                *get_qa_agent_tools(self.llm),
                create_manage_memory_tool(namespace=("memories", "{user_id}"), store=store),
                create_search_memory_tool(namespace=("memories", "{user_id}"), store=store),
            ],
            store=store,
            checkpointer=checkpointer,
        )

    def _get_or_create_session(self, user_id: int, command: str):
        """Get existing session or create a new one for user conversations.
        
        Sessions are maintained for 24 hours to provide conversation continuity.
        Each session is identified by user_id and command type.
        
        Args:
            user_id: Telegram user ID
            command: Command type or 'direct' for direct messages
            
        Returns:
            str: Thread ID for the conversation session
        """
        session_key = f"{user_id}_{command}"
        
        if session_key in self.user_sessions:
            session_time = self.user_sessions[session_key]['created_at']
            if datetime.now() - session_time < timedelta(hours=24):
                return self.user_sessions[session_key]['thread_id']
        
        thread_id = f"{user_id}_{command}_{uuid.uuid4().hex[:8]}"
        self.user_sessions[session_key] = {
            'thread_id': thread_id,
            'created_at': datetime.now()
        }
        return thread_id
    
    async def handle_ask(self, message: str):
        """Handle /ask command using QA agent with specialized tools.
        
        Args:
            message: User's question or query
            
        Returns:
            str: AI-generated response to the user's question
        """
        tools = get_qa_agent_tools(self.llm)
        prompt = self.client.pull_prompt("towerbot-ask")

        agent = create_tool_calling_agent(self.llm, tools, prompt)
        agent_executor = AgentExecutor(name="Ask", agent=agent, tools=tools)

        response = await agent_executor.ainvoke({
                "input": message,
                "chat_history": []
            })

        return response.get("output")
    
    async def handle_connect(self, message: str):
        """Handle /connect command using connection agent with graph search tools.
        
        Args:
            message: User's connection request or interest
            
        Returns:
            str: AI-generated response with connection suggestions
        """
        tools = get_connect_agent_tools()
        prompt = self.client.pull_prompt("towerbot-connect")

        agent = create_tool_calling_agent(self.llm, tools, prompt)
        agent_executor = AgentExecutor(name="Connect", agent=agent, tools=tools)

        response = await agent_executor.ainvoke({
                "input": message,
                "chat_history": []
            })

        return response.get("output")

    async def agent(self, message: str, user_id: int):
        """Process direct messages using memory-enabled conversational agent.
        
        This method handles private chat interactions with full memory capabilities,
        allowing for context-aware conversations that remember previous interactions.
        
        Args:
            message: User's message content
            user_id: Telegram user ID for session management
            
        Returns:
            str: AI-generated conversational response
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.format(system_time="now")},
            {"role": "user", "content": message}
        ]

        thread_id = self._get_or_create_session(user_id, "direct")

        config = {
            'recursion_limit': 50,
            "configurable": {
                "user_id": str(user_id),
                "thread_id": thread_id
            }
        }

        response = await self.bot.ainvoke(
            {"messages": messages},
            config=config
        )

        return response["messages"][-1].content