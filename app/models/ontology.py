from typing import Optional, List
from pydantic import BaseModel, Field

# =========================
# Graphiti Entity Definitions
# =========================

class User(BaseModel):
    """
    @Graphiti Entity: User
    Represents a unique user in the chat system.
    """
    user_id: int = Field(..., description="Unique integer ID for the user.")
    username: Optional[str] = Field(None, description="The user's username, if available.")
    first_name: Optional[str] = Field(None, description="The user's first name, if available.")

    class Config:
        label = "User"

class Topic(BaseModel):
    """
    @Graphiti Entity: Topic
    Represents a conversation thread or topic.
    """
    topic_id: int = Field(..., description="Unique integer ID for the topic.")
    title: str = Field(..., description="Title of the topic or thread.")

    class Config:
        label = "Topic"

class Message(BaseModel):
    """
    @Graphiti Entity: Message
    Represents a single message sent in the chat.
    """
    message_id: int = Field(..., description="Unique integer ID for the message.")
    text: Optional[str] = Field(None, description="Text content of the message.")
    timestamp: str = Field(..., description="ISO 8601 timestamp when the message was sent.")

    class Config:
        label = "Message"

class Floor(BaseModel):
    """
    @Graphiti Entity: Floor
    Represents a specific floor within the Frontier Tower.
    """
    level: int = Field(..., description="Numeric floor level, e.g., 1 for first floor.")
    description: Optional[str] = Field(None, description="Description of the floor, e.g., 'Innovation Lab'.")
    facilities: Optional[List[str]] = Field(None, description="List of facilities available on this floor.")
    capacity: Optional[int] = Field(None, description="Maximum occupancy of the floor.")

    class Config:
        label = "Floor"

class Event(BaseModel):
    """
    @Graphiti Entity: Event
    Represents an event, meeting, or activity scheduled within the Frontier Tower.
    """
    title: str = Field(..., description="Title or name of the event.")
    description: Optional[str] = Field(None, description="Detailed description of the event.")
    start_time: Optional[str] = Field(
        None,
        description="Start time of the event as an ISO 8601 string, e.g., '2024-06-01T10:00:00Z'."
    )
    end_time: Optional[str] = Field(
        None,
        description="End time of the event as an ISO 8601 string, e.g., '2024-06-01T12:00:00Z'."
    )
    status: Optional[str] = Field(
        "Scheduled",
        description="Current status, e.g., 'Scheduled', 'Completed', 'Cancelled'."
    )

    class Config:
        label = "Event"

class Interest(BaseModel):
    """
    @Graphiti Entity: Interest
    Represents a topic, field, or area of interest relevant to users or events.
    """
    description: Optional[str] = Field(None, description="Brief description of the interest area.")

    class Config:
        label = "Interest"

class Project(BaseModel):
    """
    @Graphiti Entity: Project
    Represents a specific project being worked on by users or communities.
    """
    status: Optional[str] = Field("Active", description="The current status, e.g., 'Active', 'Archived'.")

    class Config:
        label = "Project"

# =========================
# Graphiti Edge Definitions
# =========================

class Sent(BaseModel):
    """
    @Graphiti Edge: SENT
    Relationship: (User)-[:SENT]->(Message)
    Indicates that a user sent a message.
    """
    class Config:
        label = "SENT"

class BelongsTo(BaseModel):
    """
    @Graphiti Edge: BELONGS_TO
    Relationship: (Message)-[:BELONGS_TO]->(Topic)
    Indicates that a message belongs to a topic/thread.
    """
    class Config:
        label = "BELONGS_TO"

class InReplyTo(BaseModel):
    """
    @Graphiti Edge: IN_REPLY_TO
    Relationship: (Message)-[:IN_REPLY_TO]->(Message)
    Indicates that a message is a reply to another message.
    """
    class Config:
        label = "IN_REPLY_TO"

class LocatedOn(BaseModel):
    """
    @Graphiti Edge: LOCATED_ON
    Indicates that an event, project, or user is located on a specific floor.
    """
    since: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp since the entity has been located here."
    )
    details: Optional[str] = Field(None, description="Additional location details, e.g., room number.")

    class Config:
        label = "LOCATED_ON"

class WorksOn(BaseModel):
    """
    @Graphiti Edge: WORKS_ON
    Represents a user's involvement in organizing or supporting a project or event.
    """
    role: Optional[str] = Field(None, description="Role of the user in the event or project, e.g., 'Speaker', 'Volunteer'.")
    assigned_at: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp when the user was assigned to the event or project."
    )

    class Config:
        label = "WORKS_ON"

class Attends(BaseModel):
    """
    @Graphiti Edge: ATTENDS
    Represents a user's attendance at an event.
    """
    rsvp_status: Optional[str] = Field(None, description="RSVP status, e.g., 'Attending', 'Interested', 'Declined'.")
    checked_in_at: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp when the user checked in."
    )

    class Config:
        label = "ATTENDS"

class InterestedIn(BaseModel):
    """
    @Graphiti Edge: INTERESTED_IN
    Links a user or event to an area of interest.
    """
    expressed_at: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp when the interest was expressed."
    )

    class Config:
        label = "INTERESTED_IN"