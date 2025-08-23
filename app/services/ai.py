import uuid
import logging

from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from langsmith import Client
from langgraph.prebuilt import create_react_agent
from langchain_core.language_models import BaseChatModel
from langgraph.store.postgres.base import BasePostgresStore
from langgraph.checkpoint.postgres.base import BasePostgresSaver
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langmem import create_manage_memory_tool, create_search_memory_tool

from app.core.tools import get_qa_agent_tools, get_connect_agent_tools, get_request_agent_tools

logger = logging.getLogger(__name__)

class AiService:
    def __init__(self):
        self.bot = None
        self.client = Client()
        self.llm: Optional[BaseChatModel] = None
        self.user_sessions: Dict[str, Dict[str, Any]] = {}

    def connect(self, llm: BaseChatModel, store: BasePostgresStore, checkpointer: BasePostgresSaver):
        self.llm = llm
        self.bot = create_react_agent(
            name="General",
            model=self.llm,
            tools=[
                *get_qa_agent_tools(),
                *get_connect_agent_tools(),
                create_manage_memory_tool(namespace=("memories", "{user_id}"), store=store),
                create_search_memory_tool(namespace=("memories", "{user_id}"), store=store),
            ],
            store=store,
            checkpointer=checkpointer,
        )

    def _get_or_create_session(self, user_id: int, command: str):
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
        tools = get_qa_agent_tools()
        prompt = self.client.pull_prompt("totaylor/towerbot-ask")

        agent = create_tool_calling_agent(self.llm, tools, prompt)
        agent_executor = AgentExecutor(name="Ask", agent=agent, tools=tools)

        response = await agent_executor.ainvoke({
                "input": message,
                "chat_history": [],
                "system_time": datetime.now()
            })

        return response.get("output")
    
    async def handle_connect(self, message: str):
        tools = get_connect_agent_tools()
        prompt = self.client.pull_prompt("totaylor/towerbot-connect")

        agent = create_tool_calling_agent(self.llm, tools, prompt)
        agent_executor = AgentExecutor(name="Connect", agent=agent, tools=tools)

        response = await agent_executor.ainvoke({
                "input": message,
                "chat_history": [],
                "system_time": datetime.now()
            })

        return response.get("output")
    
    async def handle_request(self, message: str):
        tools = get_request_agent_tools()
        prompt = self.client.pull_prompt("totaylor/towerbot-request")

        agent = create_tool_calling_agent(self.llm, tools, prompt)
        agent_executor = AgentExecutor(name="Request", agent=agent, tools=tools)

        response = await agent_executor.ainvoke({
                "input": message,
                "chat_history": [],
                "system_time": datetime.now()
            })

        return response.get("output")

    async def agent(self, message: str, user_id: int):
        prompt = self.client.pull_prompt("totaylor/towerbot-general")

        messages = [
            {"role": "system", "content": prompt.messages[0].prompt.template.format(system_time=datetime.now())},
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

ai_service = AiService()