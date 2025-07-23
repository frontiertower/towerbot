from typing import Any
from fastapi import APIRouter, HTTPException

from app.services.graph import get_graphiti_client

graph_router = APIRouter(prefix="/api/v1/graph", tags=["graph"])

@graph_router.post("/search", summary="Search the knowledge graph")
async def connections_search(request: dict[str, Any]):
    try:
        graphiti = get_graphiti_client()
        results = await graphiti.search_(query=request.query)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 