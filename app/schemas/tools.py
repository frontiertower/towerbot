
from enum import Enum
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from app.schemas.generated_enums import NodeTypeEnum, EdgeTypeEnum

class SearchRecipeEnum(str, Enum):
    COMBINED_HYBRID_SEARCH_MMR = "COMBINED_HYBRID_SEARCH_MMR"
    COMBINED_HYBRID_SEARCH_CROSS_ENCODER = "COMBINED_HYBRID_SEARCH_CROSS_ENCODER"
    EDGE_HYBRID_SEARCH_RRF = "EDGE_HYBRID_SEARCH_RRF"
    EDGE_HYBRID_SEARCH_MMR = "EDGE_HYBRID_SEARCH_MMR"
    EDGE_HYBRID_SEARCH_NODE_DISTANCE = "EDGE_HYBRID_SEARCH_NODE_DISTANCE"
    EDGE_HYBRID_SEARCH_EPISODE_MENTIONS = "EDGE_HYBRID_SEARCH_EPISODE_MENTIONS"
    EDGE_HYBRID_SEARCH_CROSS_ENCODER = "EDGE_HYBRID_SEARCH_CROSS_ENCODER"
    NODE_HYBRID_SEARCH_RRF = "NODE_HYBRID_SEARCH_RRF"
    NODE_HYBRID_SEARCH_MMR = "NODE_HYBRID_SEARCH_MMR"
    NODE_HYBRID_SEARCH_NODE_DISTANCE = "NODE_HYBRID_SEARCH_NODE_DISTANCE"
    NODE_HYBRID_SEARCH_EPISODE_MENTIONS = "NODE_HYBRID_SEARCH_EPISODE_MENTIONS"
    NODE_HYBRID_SEARCH_CROSS_ENCODER = "NODE_HYBRID_SEARCH_CROSS_ENCODER"
    COMMUNITY_HYBRID_SEARCH_RRF = "COMMUNITY_HYBRID_SEARCH_RRF"
    COMMUNITY_HYBRID_SEARCH_MMR = "COMMUNITY_HYBRID_SEARCH_MMR"
    COMMUNITY_HYBRID_SEARCH_CROSS_ENCODER = "COMMUNITY_HYBRID_SEARCH_CROSS_ENCODER"

class SearchInputSchema(BaseModel):
    query: str = Field(..., description="The full message to search the graph")
    recipe: Optional[SearchRecipeEnum] = Field(
        default=None,
        description=(
            "The search recipe to use. Choose based on the query's intent. "
            "If the user asks a general question, use RRF. If they need diverse results, use MMR. "
            "If they ask about a specific entity (like a person), use NODE_DISTANCE. "
            "For the highest accuracy, use CROSS_ENCODER.\n\n"
            "---GUIDE TO RECIPES---\n"
            "**Reranking by Highest Relevance (RRF):**\n"
            "Benefit: Blends keyword and semantic results for robust, accurate retrieval. Ideal for general-purpose queries.\n"
            "- EDGE_HYBRID_SEARCH_RRF: For general questions about relationships or facts.\n"
            "- NODE_HYBRID_SEARCH_RRF: For general questions about entities or concepts.\n"
            "- COMMUNITY_HYBRID_SEARCH_RRF: For general questions about broad themes or communities.\n\n"
            "**Reranking for Diversity (MMR):**\n"
            "Benefit: Balances relevance and diversity to reduce redundant results and cover more aspects of a query.\n"
            "- COMBINED_HYBRID_SEARCH_MMR: Get diverse nodes, edges, and communities for a broad overview.\n"
            "- EDGE_HYBRID_SEARCH_MMR: Find a diverse set of facts/relationships.\n"
            "- NODE_HYBRID_SEARCH_MMR: Find a diverse set of entities/concepts.\n"
            "- COMMUNITY_HYBRID_SEARCH_MMR: Find a diverse set of themes.\n\n"
            "**Reranking by Contextual Focus (Node Distance):**\n"
            "Benefit: Prioritizes results based on proximity to a specific 'focal' node.\n"
            "- EDGE_HYBRID_SEARCH_NODE_DISTANCE: Finds facts most relevant to a specific starting entity.\n"
            "- NODE_HYBRID_SEARCH_NODE_DISTANCE: Finds entities most relevant to a specific starting entity.\n\n"
            "**Reranking by Highest Accuracy (Cross-Encoder):**\n"
            "Benefit: Scores relevance with higher accuracy by considering the query and result together.\n"
            "- COMBINED_HYBRID_SEARCH_CROSS_ENCODER: Highest accuracy search across the entire graph.\n"
            "- EDGE_HYBRID_SEARCH_CROSS_ENCODER: Highest accuracy search for relationships/facts.\n"
            "- NODE_HYBRID_SEARCH_CROSS_ENCODER: Highest accuracy search for entities/concepts.\n\n"
            "**Reranking by Mentions (Episode Mentions):**\n"
            "Benefit: Prioritizes information based on recent mentions in a sequence or 'episode.'\n"
            "- EDGE_HYBRID_SEARCH_EPISODE_MENTIONS: Find relationships relevant to a specific moment or conversation.\n"
            "- NODE_HYBRID_SEARCH_EPISODE_MENTIONS: Find entities relevant to a specific moment or conversation."
        )
    )
    edge_types: Optional[List[Union[str, EdgeTypeEnum]]] = Field(
        default=None,
        description="Array of edge types to filter by, e.g. ['WORKS_ON', 'ATTENDS']. Accepts both enum values and string literals."
    )
    node_labels: Optional[List[Union[str, NodeTypeEnum]]] = Field(
        default=None,
        description="Array of node types to filter by, e.g. ['User', 'Floor']. Accepts both enum values and string literals."
    )