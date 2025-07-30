import httpx

from typing import Any

from mcp.server.fastmcp import FastMCP

from app.services.graph import get_graphiti_client

mcp = FastMCP("tower")

@mcp.tool()
async def query_graph(query: str) -> list[dict[str, Any]]:
    """Query the graph database using Graphiti.

    Args:
        query: Search query string to find relevant nodes in the graph

    Returns:
        List of dictionaries containing graph search results with attributes filtered out
    """
    try:
        graphiti = get_graphiti_client()
        results = await graphiti.search(query=query)

        filtered_results = []
        for result in results:
            filtered_result = {k: v for k, v in result.items() if k != "attributes"}
            filtered_results.append(filtered_result)
        
        return filtered_results
    except Exception as e:
        raise Exception(f"Graph query failed: {e}") from e

@mcp.tool()
async def get_calendar_events() -> list[dict[str, Any]]:
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
            return response.json()
    except httpx.HTTPStatusError as e:
        raise Exception(f"API Error: {e.response.status_code} - {e.response.text}") from e
    except httpx.RequestError as e:
        raise Exception(f"API Request Error: {e}") from e


if __name__ == "__main__":
    mcp.run(transport='stdio')