"""Core tools and utilities for TowerBot AI agents.

This module provides tools for external API integrations, graph search functionality,
and agent utilities used by the QA, Connect, and Request agents. Includes BerlinHouse
API integration for community data and supply request management.
"""

import json
import httpx
import logging

from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, List, Optional, Union

from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI
from graphiti_core.search.search_filters import SearchFilters
from graphiti_core.search.search_config_recipes import (
    COMBINED_HYBRID_SEARCH_MMR,
    COMBINED_HYBRID_SEARCH_CROSS_ENCODER,
    EDGE_HYBRID_SEARCH_RRF,
    EDGE_HYBRID_SEARCH_MMR,
    EDGE_HYBRID_SEARCH_NODE_DISTANCE,
    EDGE_HYBRID_SEARCH_EPISODE_MENTIONS,
    EDGE_HYBRID_SEARCH_CROSS_ENCODER,
    NODE_HYBRID_SEARCH_RRF,
    NODE_HYBRID_SEARCH_MMR,
    NODE_HYBRID_SEARCH_NODE_DISTANCE,
    NODE_HYBRID_SEARCH_EPISODE_MENTIONS,
    NODE_HYBRID_SEARCH_CROSS_ENCODER,
    COMMUNITY_HYBRID_SEARCH_RRF,
    COMMUNITY_HYBRID_SEARCH_MMR,
)

from app.core.config import settings
from app.services.graph import get_graphiti_client
from app.schemas.tools import SearchInputSchema, NodeTypeEnum, EdgeTypeEnum, SearchRecipeEnum

logger = logging.getLogger(__name__)

SEARCH_RECIPE_MAP = {
    SearchRecipeEnum.COMBINED_HYBRID_SEARCH_MMR: COMBINED_HYBRID_SEARCH_MMR,
    SearchRecipeEnum.COMBINED_HYBRID_SEARCH_CROSS_ENCODER: COMBINED_HYBRID_SEARCH_CROSS_ENCODER,
    SearchRecipeEnum.EDGE_HYBRID_SEARCH_RRF: EDGE_HYBRID_SEARCH_RRF,
    SearchRecipeEnum.EDGE_HYBRID_SEARCH_MMR: EDGE_HYBRID_SEARCH_MMR,
    SearchRecipeEnum.EDGE_HYBRID_SEARCH_NODE_DISTANCE: EDGE_HYBRID_SEARCH_NODE_DISTANCE,
    SearchRecipeEnum.EDGE_HYBRID_SEARCH_EPISODE_MENTIONS: EDGE_HYBRID_SEARCH_EPISODE_MENTIONS,
    SearchRecipeEnum.EDGE_HYBRID_SEARCH_CROSS_ENCODER: EDGE_HYBRID_SEARCH_CROSS_ENCODER,
    SearchRecipeEnum.NODE_HYBRID_SEARCH_RRF: NODE_HYBRID_SEARCH_RRF,
    SearchRecipeEnum.NODE_HYBRID_SEARCH_MMR: NODE_HYBRID_SEARCH_MMR,
    SearchRecipeEnum.NODE_HYBRID_SEARCH_NODE_DISTANCE: NODE_HYBRID_SEARCH_NODE_DISTANCE,
    SearchRecipeEnum.NODE_HYBRID_SEARCH_EPISODE_MENTIONS: NODE_HYBRID_SEARCH_EPISODE_MENTIONS,
    SearchRecipeEnum.NODE_HYBRID_SEARCH_CROSS_ENCODER: NODE_HYBRID_SEARCH_CROSS_ENCODER,
    SearchRecipeEnum.COMMUNITY_HYBRID_SEARCH_RRF: COMMUNITY_HYBRID_SEARCH_RRF,
    SearchRecipeEnum.COMMUNITY_HYBRID_SEARCH_MMR: COMMUNITY_HYBRID_SEARCH_MMR,
}
"""Mapping of search recipe enums to their corresponding configuration objects.

This dictionary maps the SearchRecipeEnum values to their actual Graphiti search
configuration objects for use in graph search operations.
"""

async def summarize_calendar_events(events: dict[str, Any], llm: AzureChatOpenAI):
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
    @tool("get_calendar_events", parse_docstring=True)
    async def get_calendar_events():
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
            logger.error(f"Luma API HTTP error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"API Error: {e.response.status_code} - {e.response.text}") from e
        except httpx.RequestError as e:
            logger.error(f"Luma API request error: {e}")
            raise Exception(f"API Request Error: {e}") from e
    return get_calendar_events

@tool("get_tower_communities", parse_docstring=True)
async def get_tower_communities(search: Optional[str] = None):
    """
    Fetch and summarize BerlinHouse communities using the BerlinHouse API, with optional search functionality.

    Args:
        search: Optional search keywords to filter communities

    Returns:
        Optional[dict[str, Any]]: A summary of BerlinHouse communities, or raises an exception if unavailable.

    Raises:
        Exception: If the BerlinHouse API is unavailable or returns an error.
    """
    headers = {
        "X-API-Key": settings.BERLINHOUSE_API_KEY,
        "Content-Type": "application/json"
    }
    try:
        async with httpx.AsyncClient(verify=False) as client:
            endpoint = settings.BERLINHOUSE_BASE_URL + "/communities/"
            params = {}
            if search:
                params["search"] = search
            response = await client.get(endpoint, headers=headers, params=params)
            response.raise_for_status()
            communities = response.json()
            return communities
    except httpx.HTTPStatusError as e:
        logger.error(f"BerlinHouse communities API HTTP error: {e.response.status_code} - {e.response.text}")
        raise Exception(f"API Error: {e.response.status_code} - {e.response.text}") from e
    except httpx.RequestError as e:
        logger.error(f"BerlinHouse communities API request error: {e}")
        raise Exception(f"API Request Error: {e}") from e
    

@tool("create_supply_request", parse_docstring=True)
async def create_supply_request(item: str, additional_info: Optional[str] = None):
    """
    Create a new supply request in the BerlinHouse system.

    This tool sends a POST request to the BerlinHouse API to create a supply request for a specific item and amount,
    along with any additional information provided by the user. It is used to request supplies or resources needed
    within the BerlinHouse community.

    Args:
        item (str): The name or description of the item being requested.
        additional_info (Optional[str]): Any extra details or context about the supply request.

    Returns:
        dict[str, Any]: The response from the BerlinHouse API containing details of the created supply request.

    Raises:
        Exception: If the BerlinHouse API is unavailable or returns an error.
    """
    headers = {
        "X-API-Key": settings.BERLINHOUSE_API_KEY,
        "Content-Type": "application/json"
    }
    try:
        async with httpx.AsyncClient(verify=False) as client:
            endpoint = settings.BERLINHOUSE_BASE_URL + "/supply-requests/"
            data = {
                "item": item,
                "amount": 0,
            }
            if additional_info is not None:
                data["additional_info"] = additional_info
            response = await client.post(endpoint, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"BerlinHouse communities API HTTP error: {e.response.status_code} - {e.response.text}")
        raise Exception(f"API Error: {e.response.status_code} - {e.response.text}") from e
    except httpx.RequestError as e:
        logger.error(f"BerlinHouse communities API request error: {e}")
        raise Exception(f"API Request Error: {e}") from e

@tool("get_tower_info", parse_docstring=True)
def get_tower_info():
    """
    Retrieve detailed information about the Frontier Towner building.

    This tool loads and returns the contents of 'tower.json', which contains comprehensive data about the building,
    including amenities, facilities, floor plans, and other relevant details. Use this tool to answer questions
    about the building's features, resources, or layout.

    Returns:
        dict[str, Any]: A dictionary containing all available information about the Frontier Towner.
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    json_file_path = project_root / "static" / "data" / "tower.json"

    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            tower_data = json.load(f)
        logger.debug(f"Tower data loaded from {json_file_path}")
        return tower_data
    except FileNotFoundError:
        logger.error(f"Tower data file not found: {json_file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in tower data file: {e}")
        raise


@tool("get_connections", args_schema=SearchInputSchema)
async def get_connections(
    query: str,
    recipe: Optional[SearchRecipeEnum] = None,
    edge_types: Optional[List[Union[str, EdgeTypeEnum]]] = None,
    node_labels: Optional[List[Union[str, NodeTypeEnum]]] = None,
):
    """
    Searches the graph for connection opportunities based on a query, leveraging message context.
    
    Uses combined hybrid search with cross-encoder by default to capture context from messages
    and episodes, providing better hit rates for finding relevant connections between people.
    """
    graphiti = get_graphiti_client()
    
    if recipe and recipe in SEARCH_RECIPE_MAP:
        search_config = SEARCH_RECIPE_MAP[recipe].model_copy(deep=True)
    else:
        search_config = COMBINED_HYBRID_SEARCH_CROSS_ENCODER.model_copy(deep=True)

    search_config.limit = 10
    search_filter = None

    if node_labels or edge_types:
        search_filter = SearchFilters(
            node_labels=node_labels or [],
            edge_types=edge_types or [],
        )

    return await graphiti.search_(
        query=query,
        config=search_config,
        search_filter=search_filter
    )


def get_qa_agent_tools(llm: AzureChatOpenAI):
    """Get the list of tools available to the QA agent.
    
    Args:
        llm: Azure OpenAI language model instance
        
    Returns:
        list: List of tools for the QA agent
    """
    return [
        get_tower_info,
        get_tower_communities,
        get_calendar_events_tool(llm),
    ]

def get_connect_agent_tools():
    """Get the list of tools available to the Connect agent.
    
    Returns:
        list: List of tools for the Connect agent
    """
    return [
        get_connections,
    ]

def get_request_agent_tools():
    """Get the list of tools available to the Request agent.
    
    Returns:
        list: List of tools for the Request agent
    """
    return [
        create_supply_request,
    ]