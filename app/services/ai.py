import uuid
import logging

from datetime import datetime
from typing import Dict, Any, Optional

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
    def __init__(self):
        self.agent = None
        self.client = Client()
        self.llm: Optional[AzureChatOpenAI] = None
        self.user_sessions: Dict[str, Dict[str, Any]] = {}

    def connect(self, llm: AzureChatOpenAI, store: BasePostgresStore, checkpointer: BasePostgresSaver):
        self.llm = llm
        self.agent = create_react_agent(
            name="TowerBot",
            model=self.llm,
            tools=[
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
            if (datetime.now() - session_time).seconds < 3600:
                return self.user_sessions[session_key]['thread_id']
        
        thread_id = f"{user_id}_{command}_{uuid.uuid4().hex[:8]}"
        self.user_sessions[session_key] = {
            'thread_id': thread_id,
            'created_at': datetime.now()
        }
        return thread_id
    
    async def _handle_ask_command(self, message: str):
        tools = get_qa_agent_tools(self.llm)
        prompt = self.client.pull_prompt("hwchase17/openai-tools-agent")

        agent = create_tool_calling_agent(self.llm, tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        response = await agent_executor.ainvoke({
                "input": message
            })
        return response.get("output")

    async def run(self, command: str, message: str, user_id: int):
        if command == "ask":
            return await self._handle_ask_command(message)

        if not command or command.strip() == "":
            command = "direct"

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

            response = await self.agent.ainvoke(
                {"messages": messages},
                config=config
            )

            return response["messages"][-1].content