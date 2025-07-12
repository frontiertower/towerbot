from langchain_openai import AzureChatOpenAI
from langgraph.prebuilt import create_react_agent

from app.core.config import settings
from app.models.qa import QuestionResponse
from app.core.prompts import SYSTEM_PROMPT
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
        self.model: AzureChatOpenAI | None = None
        self.reasoning_model: AzureChatOpenAI | None = None
        self.qa_agent = None
        self.connect_agent = None

    def connect(self, llm: AzureChatOpenAI, embeddings):
        self.model = llm
        self.reasoning_model = get_model("reasoning")
        self.qa_agent = create_react_agent(name="QA", model=self.model, tools=get_qa_tools(self.model, embeddings), response_format=QuestionResponse)
        self.connect_agent = create_react_agent(name="CONNECT", model=self.reasoning_model, tools=get_connect_tools())

    async def agent(self, message: str, command: str):
        agent = self.qa_agent if command == "ask" else self.connect_agent

        if not agent:
            raise RuntimeError("AI agent not initialized. Call connect() on startup.")

        response = await agent.ainvoke(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT.format(system_time="now")},
                    {"role": "user", "content": message}
                ]
            }
        )

        return response["structured_response"]