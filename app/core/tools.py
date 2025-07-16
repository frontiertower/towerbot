import json
import httpx

from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Callable, List, Optional

from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI
from langchain_openai import AzureOpenAIEmbeddings
from langchain.tools.retriever import create_retriever_tool
from graphiti_core.search.search_filters import SearchFilters
from langchain_community.vectorstores import SupabaseVectorStore

from app.core.config import settings
from app.services.graph import get_graphiti_client
from app.services.database import get_supabase_client
from app.models.tools import ConnectInputSchema, NodeTypeEnum, EdgeTypeEnum

async def get_jwt_token() -> str:
    """
    Obtain a JWT access token from the BerlinHouse API using credentials from settings.

    Returns:
        str: The JWT access token as a string.

    Raises:
        Exception: If the API returns an error or the request fails.
    """
    url = "https://api.berlinhouse.com/auth/login/"
    email = settings.BERLINHOUSE_EMAIL
    password = settings.BERLINHOUSE_PASSWORD
    payload = {"email": email, "password": password}

    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("access")
    except httpx.HTTPStatusError as e:
        raise Exception(f"API Error: {e.response.status_code} - {e.response.text}") from e
    except httpx.RequestError as e:
        raise Exception(f"API Request Error: {e}") from e

async def summarize_calendar_events(events: dict[str, Any], llm: AzureChatOpenAI) -> str:
    """
    Summarize a dictionary of events using an LLM, highlighting those relevant for today (US Pacific time).

    Args:
        events (dict[str, Any]): The events data in JSON/dict format.

    Returns:
        str: The LLM-generated summary of the events, focusing on today's important or relevant events.
    """
    pacific_tz = ZoneInfo("America/Los_Angeles")
    pacific_date = datetime.now(pacific_tz).strftime('%Y-%m-%d')

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful assistant. "
                "Given a list of calendar events in JSON format, summarize the events for the user. "
                "Highlight any events that are relevant or important for today ({date}) in the US Pacific timezone. "
                "If there are no relevant events, say so. "
                "Be concise and clear."
            ).format(date=pacific_date),
        },
        {
            "role": "user",
            "content": f"Here are the events in JSON:\n{events}",
        },
    ]

    ai_msg = await llm.ainvoke(messages)
    return ai_msg.content


def get_calendar_events_tool(llm: AzureChatOpenAI):
    @tool
    async def get_calendar_events() -> str:
        """
        Retrieve all future events from the Luma calendar API and summarize them using an LLM.

        Returns:
            str: A summary of future events, with emphasis on those relevant for today (US Pacific time).

        Raises:
            Exception: If the Luma API is unavailable or returns an error.
        """
        url = "https://api.lu.ma/calendar/get-items?calendar_api_id=cal-Sl7q1nHTRXQzjP2&period=future"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                events = response.json()
                return await summarize_calendar_events(events, llm)
        except httpx.HTTPStatusError as e:
            raise Exception(f"API Error: {e.response.status_code} - {e.response.text}") from e
        except httpx.RequestError as e:
            raise Exception(f"API Request Error: {e}") from e
    return get_calendar_events

def get_notion_database_tool(embeddings):
    @tool
    async def get_notion_database(query: str) -> Optional[dict[str, Any]]:
        """
        Search the Notion database for information relevant to the provided query using vector search.
        Args:
            query (str): The search query string.
        Returns:
            Optional[dict[str, Any]]: The most relevant information as a JSON object, or None if nothing is found.
        """
        vectorstore = SupabaseVectorStore(
            embedding=embeddings,
            client=get_supabase_client(),
            table_name="documents",
            query_name="match_documents",
        )
        retriever = vectorstore.as_retriever()
        retriever_tool = create_retriever_tool(
            retriever,
            "retrieve_notion_database",
            "Search and return information about Frontier Towner's Notion database.",
        )
        return retriever_tool.invoke({"query": query})
    return get_notion_database


@tool
async def get_tower_communities() -> Optional[dict[str, Any]]:
    """
    Fetch and summarize all BerlinHouse communities using the BerlinHouse API and LLM summarization.

    Returns:
        Optional[dict[str, Any]]: A summary of BerlinHouse communities, or raises an exception if unavailable.

    Raises:
        Exception: If the BerlinHouse API is unavailable or returns an error.
    """
    url = "https://api.berlinhouse.com/communities/"
    headers = {
        "Authorization": f"Bearer {await get_jwt_token()}"
    }
    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            communities = response.json()
            return communities
    except httpx.HTTPStatusError as e:
        raise Exception(f"API Error: {e.response.status_code} - {e.response.text}") from e
    except httpx.RequestError as e:
        raise Exception(f"API Request Error: {e}") from e

@tool
def get_tower_info() -> dict[str, Any]:
    """
    Retrieve detailed information about the Frontier Towner building.

    This tool loads and returns the contents of 'tower.json', which contains comprehensive data about the building,
    including amenities, facilities, floor plans, and other relevant details. Use this tool to answer questions
    about the building's features, resources, or layout.

    Returns:
        dict[str, Any]: A dictionary containing all available information about the Frontier Towner.
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    json_file_path = project_root / "static" / "json" / "tower.json"

    with open(json_file_path, 'r', encoding='utf-8') as f:
        tower_data = json.load(f)
    return tower_data


@tool("get_connections", args_schema=ConnectInputSchema)
async def get_connections(
    message: str,
    edge_types: List[EdgeTypeEnum],
    node_labels: List[NodeTypeEnum],
) -> Any:
    graphiti = get_graphiti_client()

    if edge_types and node_labels:
        search_filter = SearchFilters(
            node_labels=node_labels,
            edge_types=edge_types,
        )
        return await graphiti.search_(
            query=message,
            search_filter=search_filter
        )
    else:
        return await graphiti.search_(
            query=message
        )


def get_ask_tools(llm: AzureChatOpenAI, embeddings: AzureOpenAIEmbeddings) -> List[Callable[..., Any]]:
    return [
        get_tower_info,
        get_calendar_events_tool(llm),
    ]

def get_connect_tools() -> List[Callable[..., Any]]:
    return [
        get_connections,
    ]