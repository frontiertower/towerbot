from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class SourceType(str, Enum):
    NOTION_KNOWLEDGE_BASE = "Notion Knowledge Base"
    VECTOR_DATABASE = "Vector Database"

class ToolUsed(str, Enum):
    NOTION_SEARCH = "Notion Search"
    VECTOR_SEARCH = "Vector Search"

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

class AnswerResponse(BaseModel):
    answer: str = Field(
        ...,
        description="The final, synthesized answer to the user's query.",
    )
    source_type: str = Field(
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
    confident_score: float = Field(
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
    tool_used: str = Field(
        ...,
        description="The specific tool used to fetch the information.",
    )