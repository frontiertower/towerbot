"""AI service module for TowerBot intelligent agent operations.

This module provides the AiService class for managing AI agents that handle
user queries, connection requests, and direct messages using LangChain and LangGraph frameworks.

The AiService implements a dynamic agent configuration system that supports:
- Command-based agents: /ask, /report, /propose, /connect with specialized tools
- Direct message agent: Memory-only agent for conversational interactions
- Dynamic agent creation: Easy addition of new agent types via AgentConfig
- Session management: Conversation continuity across interactions
- Memory integration: All agents have access to memory tools for context retention

Agent Types:
- Ask Agent: General questions and information retrieval with QA tools
- Report Agent: Community reports and observations with QA tools  
- Propose Agent: Suggestions and proposals with QA tools
- Connect Agent: Connection requests and network searches with graph tools
- Memory Agent: Direct message processing with memory operations only

All agents share common memory and checkpointing capabilities for conversation continuity.
"""
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Type

from langchain_openai import AzureChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.store.postgres.base import BasePostgresStore
from langgraph.checkpoint.postgres.base import BasePostgresSaver
from langmem import create_manage_memory_tool, create_search_memory_tool
from pydantic import BaseModel

from app.core.constants import SYSTEM_PROMPT
from app.schemas.responses import QuestionResponse, ConnectionResponse
from app.core.tools import get_qa_agent_tools, get_connect_agent_tools

logger = logging.getLogger(__name__)

class AgentConfig:
    """Configuration class for AI agent creation.
    
    This class encapsulates all the parameters needed to create an AI agent,
    making it easy to define different agent types with their specific tools,
    response formats, and names.
    """
    def __init__(
        self,
        name: str,
        response_format: Type[BaseModel],
        tools: List[Any],
        description: Optional[str] = None
    ):
        self.name = name
        self.response_format = response_format
        self.tools = tools
        self.description = description or f"Agent for {name} operations"

class AiService:
    """Service class for managing AI agents and processing user requests.
    
    This class handles the creation and management of multiple specialized AI agents
    using a dynamic configuration system. Each agent can have different tools,
    response formats, and names while sharing common memory and checkpointing capabilities.
    
    Attributes:
        agents: Dictionary mapping command types to their corresponding agents
        user_sessions: Dictionary tracking active sessions per user
    """
    def __init__(self):
        """Initialize the AiService with empty agent references."""
        self.agents: Dict[str, Any] = {}
        self.user_sessions: Dict[str, Dict[str, Any]] = {}

    def _create_agent_configs(self, llm: AzureChatOpenAI, store: BasePostgresStore) -> Dict[str, AgentConfig]:
        """Create agent configurations for all supported agent types.
        
        Args:
            llm: Azure OpenAI language model instance
            store: PostgreSQL store for agent memory
            
        Returns:
            Dictionary mapping command types to their agent configurations
        """
        # Common memory tools for all agents
        memory_tools = [
            create_manage_memory_tool(namespace=("memories", "{user_id}"), store=store),
            create_search_memory_tool(namespace=("memories", "{user_id}"), store=store),
        ]
        
        return {
            "ask": AgentConfig(
                name="Ask",
                response_format=QuestionResponse,
                tools=[*get_qa_agent_tools(llm), *memory_tools],
                description="Handles general questions and information retrieval"
            ),
            "report": AgentConfig(
                name="Report", 
                response_format=QuestionResponse,
                tools=[*get_qa_agent_tools(llm), *memory_tools],
                description="Handles reporting and information requests"
            ),
            "propose": AgentConfig(
                name="Propose",
                response_format=QuestionResponse, 
                tools=[*get_qa_agent_tools(llm), *memory_tools],
                description="Handles proposal and suggestion requests"
            ),
            "connect": AgentConfig(
                name="Connect",
                response_format=ConnectionResponse,
                tools=[*get_connect_agent_tools(), *memory_tools],
                description="Handles connection requests and network searches"
            ),
            # Memory-only Agent for direct messages (no command)
            "direct": AgentConfig(
                name="Memory",
                response_format=QuestionResponse,
                tools=memory_tools,
                description="Handles direct messages with memory operations only"
            ),
        }

    def connect(self, llm: AzureChatOpenAI, store: BasePostgresStore, checkpointer: BasePostgresSaver):
        """Initialize and configure all AI agents.
        
        Creates agents dynamically based on their configurations, with their respective tools,
        memory management, and checkpointing capabilities.
        
        Args:
            llm: Azure OpenAI language model instance
            store: PostgreSQL store for agent memory
            checkpointer: PostgreSQL checkpointer for conversation state
        """
        try:
            agent_configs = self._create_agent_configs(llm, store)
            
            for command, config in agent_configs.items():
                self.agents[command] = create_react_agent(
                    name=config.name,
                    model=llm,
                    response_format=config.response_format,
                    tools=config.tools,
                    store=store,
                    checkpointer=checkpointer,
                )
                logger.info(f"Initialized {config.name} agent for '{command}' command")
                
            logger.info(f"Successfully initialized {len(self.agents)} AI agents")
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

    def get_agent(self, command: str):
        """Get the appropriate agent for a given command.
        
        Args:
            command: The command type to get an agent for (or None for direct messages)
            
        Returns:
            The agent instance for the command
            
        Raises:
            RuntimeError: If no agent is found for the command
        """
        # For direct messages (no command), use the memory agent
        if not command or command.strip() == "":
            command = "direct"
            
        agent = self.agents.get(command)
        if not agent:
            available_commands = list(self.agents.keys())
            raise RuntimeError(
                f"No agent found for command '{command}'. "
                f"Available commands: {available_commands}"
            )
        return agent

    async def run(self, command: str, message: str, user_id: int):
        """Execute a command using the appropriate AI agent.
        
        Routes the command to the appropriate agent based on the command type.
        For direct messages (no command), uses the memory agent.
        
        Args:
            command: The command type (e.g., 'ask', 'report', 'propose', 'connect') or None/empty for direct messages
            message: User's message content
            user_id: Unique identifier for the user
            
        Returns:
            The structured response from the appropriate agent
            
        Raises:
            RuntimeError: If agents are not initialized or command is not supported
        """
        # Determine the actual command to use for session management
        session_command = command if command and command.strip() else "direct"
        agent = self.get_agent(command)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.format(system_time="now")},
            {"role": "user", "content": message}
        ]

        thread_id = self._get_or_create_session(user_id, session_command)
        
        config = {
            'recursion_limit': 50,
            "configurable": {
                "user_id": str(user_id),
                "thread_id": thread_id
            }
        }

        try:
            if command and command.strip():
                logger.debug(f"Processing {command} command for user {user_id}")
            else:
                logger.debug(f"Processing direct message for user {user_id}")
                
            response = await agent.ainvoke(
                {"messages": messages},
                config=config
            )
            
            if command and command.strip():
                logger.debug(f"Successfully processed {command} command for user {user_id}")
            else:
                logger.debug(f"Successfully processed direct message for user {user_id}")
                
            return response["structured_response"]
        except Exception as e:
            if command and command.strip():
                logger.error(f"Failed to process {command} command for user {user_id}: {e}")
            else:
                logger.error(f"Failed to process direct message for user {user_id}: {e}")
            raise

    def add_agent(self, command: str, config: AgentConfig, llm: AzureChatOpenAI, 
                  store: BasePostgresStore, checkpointer: BasePostgresSaver):
        """Dynamically add a new agent configuration.
        
        This method allows runtime addition of new agent types without
        modifying the core _create_agent_configs method.
        
        Args:
            command: The command type for the new agent
            config: AgentConfig instance defining the agent's properties
            llm: Azure OpenAI language model instance
            store: PostgreSQL store for agent memory
            checkpointer: PostgreSQL checkpointer for conversation state
        """
        try:
            self.agents[command] = create_react_agent(
                name=config.name,
                model=llm,
                response_format=config.response_format,
                tools=config.tools,
                store=store,
                checkpointer=checkpointer,
            )
            logger.info(f"Successfully added new agent '{config.name}' for '{command}' command")
        except Exception as e:
            logger.error(f"Failed to add agent for command '{command}': {e}")
            raise