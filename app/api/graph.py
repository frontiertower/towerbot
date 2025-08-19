from typing import Any, List, Dict
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.services.graph import get_graphiti_client

graph_router = APIRouter(prefix="/api/v1/graph", tags=["graph"])

class GraphQueryRequest(BaseModel):
    """Request model for graph queries."""
    query: str = Field(..., description="Natural language query to search the knowledge graph", min_length=1, max_length=1000)

class GraphQueryResponse(BaseModel):
    """Response model for graph queries."""
    results: List[Dict[str, Any]] = Field(..., description="List of matching nodes/edges from the knowledge graph")

@graph_router.post(
    "/query", 
    summary="Query the temporal knowledge graph",
    description="Query TowerBot's temporal knowledge graph using natural language to find community interactions, relationships, and events.",
    response_model=GraphQueryResponse,
    responses={
        200: {
            "description": "Successful query response",
            "content": {
                "application/json": {
                    "example": {
                        "results": [
                            {
                                "uuid": "abc-123",
                                "name": "MENTIONED",
                                "fact": "John mentioned the tower project in group chat",
                                "created_at": "2025-07-25T10:30:00Z"
                            }
                        ]
                    }
                }
            }
        },
        401: {"description": "API key authentication failed"},
        403: {"description": "Invalid API key"},
        500: {"description": "Graph search failed or internal error"}
    }
)
async def query_graph(request: GraphQueryRequest):
    """
    Query the temporal knowledge graph using natural language.
    
    This endpoint provides access to TowerBot's knowledge graph, which contains
    temporal information about community interactions, relationships, and events.
    The graph is powered by Graphiti and processes Telegram messages into
    structured knowledge representations.
    
    Authentication:
        Requires a valid API key in the Authorization header as a Bearer token.
        API keys are validated against the 'keys' table in the PostgreSQL database.
    
    Args:
        request: Dictionary containing the query parameters
            - query (str): Natural language query to search the knowledge graph
    
    Returns:
        dict: Search results from the knowledge graph with attributes filtered out
            - results (list): List of matching nodes/edges from the graph
            
    Raises:
        HTTPException:
            - 401 if API key authentication fails
            - 403 if API key is invalid
            - 500 if graph search fails or internal error occurs
            
    Example:
        ```python
        # Request
        {
            "query": "What did John say about the tower project?"
        }
        
        # Response
        {
            "results": [
                {
                    "uuid": "abc-123",
                    "name": "MENTIONED",
                    "fact": "John mentioned the tower project in group chat",
                    "created_at": "2025-07-25T10:30:00Z",
                    ...
                }
            ]
        }
        ```
    
    Note:
        The 'attributes' field (containing embeddings) is filtered from results
        to reduce response size and avoid exposing internal representations.
    """
    try:
        graphiti = get_graphiti_client()
        results = await graphiti.search(query=request.query)
        
        filtered_results = []
        for result in results:
            filtered_result = {k: v for k, v in result if k != "attributes"}
            filtered_results.append(filtered_result)
        
        return GraphQueryResponse(results=filtered_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))