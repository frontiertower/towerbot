from langgraph.store.base import BaseStore
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langmem import create_manage_memory_tool, create_search_memory_tool

from app.core.config import settings
from app.core.constants import SYSTEM_PROMPT
from app.models.responses import QuestionResponse
from app.core.tools import get_qa_tools, get_connect_tools

def get_model(model_type: str):
    if model_type == "model":
        deployment = settings.MODEL
    elif model_type == "reasoning":
        deployment = settings.REASONING_MODEL
    else:
        raise ValueError(f"Unknown model_type: {model_type}")
    
    return AzureChatOpenAI(
        api_version="2024-12-01-preview",
        azure_deployment=deployment,
    )

class AiService:
    def __init__(self):
        self.qa_agent = None
        self.connect_agent = None

    def connect(self, llm: AzureChatOpenAI, embeddings: AzureOpenAIEmbeddings, store: BaseStore, checkpointer: BaseCheckpointSaver):
        self.qa_agent = create_react_agent(
            name="Ask",
            model=llm,
            response_format=QuestionResponse,
            tools=[
                *get_qa_tools(llm, embeddings),
                create_manage_memory_tool(namespace=("memories", "{user_id}")),
                create_search_memory_tool(namespace=("memories", "{user_id}")),
            ],
            store=store,
            checkpointer=checkpointer,
        )
        self.connect_agent = create_react_agent(
            name="Connect",
            model=llm,
            response_format=QuestionResponse,
            tools=[
                *get_connect_tools(),
                create_manage_memory_tool(namespace=("memories", "{user_id}")),
                create_search_memory_tool(namespace=("memories", "{user_id}")),
            ],
            store=store,
            checkpointer=checkpointer,
        )

    async def run(self, command: str, message: str, user_id: int):
        agent = self.qa_agent if command == "ask" else self.connect_agent

        if not agent:
            raise RuntimeError("Agent not initialized. Call connect() on startup.")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.format(system_time="now")},
            {"role": "user", "content": message}
        ]

        config = {
            'recursion_limit': 50,
            "configurable": {
                "user_id": str(user_id),
                "thread_id": str(user_id)
            }
        }

        response = await agent.ainvoke(
            {"messages": messages},
            config=config
        )

        return response["structured_response"]