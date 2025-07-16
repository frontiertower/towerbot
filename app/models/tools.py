from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class NodeTypeEnum(str, Enum):
    User = "User"
    Floor = "Floor"
    Event = "Event"
    Interest = "Interest"
    Project = "Project"
    
class EdgeTypeEnum(str, Enum):
    WorksOn = "WorksOn"
    Attends = "Attends"
    LocatedOn = "LocatedOn"
    InterestedIn = "InterestedIn"

class ConnectInputSchema(BaseModel):
    """
    Schema for connecting two nodes in the graph.

    Attributes:
        message (str): The user's message to search the graph.
        edge_types (Optional[List[EdgeTypeEnum]]): Array of edge types, e.g. ['WorksOn', 'Attends'].
        node_labels (Optional[List[NodeTypeEnum]]): Array of node types, e.g. ['User', 'Floor'].
    """
    message: str = Field(
        ...,
        description="The user's message to search the graph"
    )
    edge_types: Optional[List[EdgeTypeEnum]] = Field(
        default=None,
        description="Array of edge types, e.g. ['WorksOn', 'Attends']"
    )
    node_labels: Optional[List[NodeTypeEnum]] = Field(
        default=None,
        description="Array of node types, e.g. ['User', 'Floor']"
    )