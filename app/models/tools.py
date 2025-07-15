from enum import Enum
from typing import List
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
    """Connect two nodes"""
    node_labels: List[NodeTypeEnum] = Field(description="Array of node types, e.g. ['User', 'Floor']")
    edge_types: List[EdgeTypeEnum] = Field(description="Array of edge types, e.g. ['WorksOn', 'Attends']")