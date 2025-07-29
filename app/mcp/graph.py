from typing import Any

from mcp.server.fastmcp import FastMCP

from app.services.graph import get_graphiti_client

mcp = FastMCP("graph")

@mcp.tool()
async def query_graph(query: str) -> list[dict[str, Any]]:
    """Query the graph database using Graphiti.

    Args:
        query: Search query string to find relevant nodes in the graph

    Returns:
        List of dictionaries containing graph search results with attributes filtered out
    """
    graphiti = get_graphiti_client()
    results = await graphiti.search(query=query)

    filtered_results = []
    for result in results:
        filtered_result = {k: v for k, v in result if k != "attributes"}
        filtered_results.append(filtered_result)
    
    return filtered_results


if __name__ == "__main__":
    mcp.run(transport='stdio')