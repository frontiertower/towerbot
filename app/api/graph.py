from typing import Any, List, Dict
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.services.graph import get_graphiti_client

graph_router = APIRouter(prefix="/api/v1/graph", tags=["graph"])

class GraphQueryRequest(BaseModel):
    query: str = Field(..., description="Natural language query to search the knowledge graph", min_length=1, max_length=1000)

class GraphQueryResponse(BaseModel):
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