
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Literal

from app.schemas.generated_enums import NodeTypeEnum

class SourceType(str, Enum):
    NOTION_KNOWLEDGE_BASE = "Notion Knowledge Base"
    VECTOR_DATABASE = "Vector Database"

class ToolUsed(str, Enum):
    NOTION_SEARCH = "Notion Search"
    VECTOR_SEARCH = "Vector Search"

class ConnectionCandidate(BaseModel):
    node_id: str = Field(
        ...,
        description="Unique identifier of the graph node to connect with.",
    )
    display_name: str = Field(
        ...,
        description="Human‑readable name or title of the node.",
    )
    node_label: NodeTypeEnum = Field(
        ...,
        description="The node’s label/type in the knowledge graph (e.g., 'User', 'Community').",
    )
    match_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Similarity/confidence score for this particular candidate.",
    )

class QuestionResponse(BaseModel):
    answer: str = Field(
        ...,
        description="The final, synthesized answer to the user's query.",
    )
    source_type: SourceType = Field(
        ...,
        description="The type of data source used to generate the answer, as determined by the system.",
    )
    source_document: str = Field(
        ...,
        description=(
            "The specific source document, page, or identifier from which the information "
            "was retrieved (e.g., 'FAQ Page', 'Document ID: 12345', 'Guide to X')."
        ),
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "The model's overall confidence in the accuracy of the final answer, "
            "ranging from 0.0 (low) to 1.0 (high)."
        ),
    )
    retrieval_score: Optional[float] = Field(
        None,
        description=(
            "The similarity score (e.g., cosine similarity) from the vector database search. "
            "This will be null if the Notion knowledge base was used directly."
        ),
    )
    tool_used: ToolUsed = Field(
        ...,
        description="The specific tool used to fetch the information.",
    )
    model_config = {
        "use_enum_values": True,
        "validate_by_name": True,
    }

class ConnectionResponse(BaseModel):
    answer: str = Field(
        ...,
        description="Short, synthesized explanation of who the user should connect with and why.",
    )
    candidates: List[ConnectionCandidate] = Field(
        ...,
        description="Ordered list of the best connection matches, highest‑scoring first.",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall confidence in the quality of the candidate list.",
    )
    retrieval_score: Optional[float] = Field(
        None,
        description=(
            "The top similarity score from the underlying vector search (or None if "
            "Graphiti search didn’t supply one)."
        ),
    )
    tool_used: Literal["get_connections"] = Field(
        "get_connections",
        description="Tool invoked to produce this response.",
    )

    model_config = {
        "validate_by_name": True,
        "use_enum_values": True,
    }