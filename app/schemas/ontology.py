from typing import Optional, List
from pydantic import BaseModel, Field


class User(BaseModel):
    user_id: int = Field(..., description="Unique integer ID for the user.")
    username: Optional[str] = Field(
        None, description="The user's username, if available."
    )
    first_name: str = Field(..., description="The user's first name, if available.")
    last_name: Optional[str] = Field(
        None, description="The user's last name, if available."
    )

    class Config:
        label = "User"


class Topic(BaseModel):
    topic_id: int = Field(..., description="Unique integer ID for the topic.")
    title: str = Field(..., description="Title of the topic or thread.")

    class Config:
        label = "Topic"


class Message(BaseModel):
    message_id: int = Field(..., description="Unique integer ID for the message.")
    text: Optional[str] = Field(None, description="Text content of the message.")
    timestamp: str = Field(
        ..., description="ISO 8601 timestamp when the message was sent."
    )

    class Config:
        label = "Message"


class Floor(BaseModel):
    level: int = Field(..., description="Numeric floor level, e.g., 9 for ninth floor.")
    description: Optional[str] = Field(
        None, description="Description of the floor, e.g., 'Artificial Intelligence'."
    )
    facilities: Optional[List[str]] = Field(
        None, description="List of facilities available on this floor."
    )

    class Config:
        label = "Floor"


class Event(BaseModel):
    luma_id: Optional[str] = Field(None, description="Luma ID of the event.")
    url: Optional[str] = Field(None, description="URL of the event.")
    start_at: Optional[str] = Field(
        None,
        description="Start time of the event as an ISO 8601 string, e.g., '2024-06-01T10:00:00Z'.",
    )
    end_at: Optional[str] = Field(
        None,
        description="End time of the event as an ISO 8601 string, e.g., '2024-06-01T12:00:00Z'.",
    )
    status: Optional[str] = Field(
        "Scheduled",
        description="Current status, e.g., 'Scheduled', 'Completed', 'Cancelled'.",
    )

    class Config:
        label = "Event"


class Interest(BaseModel):
    title: str = Field(..., description="Title of the interest.")

    class Config:
        label = "Interest"


class Project(BaseModel):
    status: Optional[str] = Field(
        "Active", description="The current status, e.g., 'Active', 'Archived'."
    )

    class Config:
        label = "Project"


class Sent(BaseModel):
    class Config:
        label = "SENT"
        source_types = ["User"]
        target_types = ["Message"]


class SentIn(BaseModel):
    class Config:
        label = "SENT_IN"
        source_types = ["Message"]
        target_types = ["Topic"]


class InReplyTo(BaseModel):
    class Config:
        label = "IN_REPLY_TO"
        source_types = ["Message"]
        target_types = ["Message"]


class LocatedOn(BaseModel):
    since: Optional[str] = Field(
        None, description="ISO 8601 timestamp since the entity has been located here."
    )
    details: Optional[str] = Field(
        None, description="Additional location details, e.g., room number."
    )

    class Config:
        label = "LOCATED_ON"
        source_types = ["User", "Event", "Project"]
        target_types = ["Floor"]


class WorksOn(BaseModel):
    role: Optional[str] = Field(
        None,
        description="Role of the user in the event or project, e.g., 'Speaker', 'Volunteer'.",
    )
    assigned_at: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp when the user was assigned to the event or project.",
    )

    class Config:
        label = "WORKS_ON"
        source_types = ["User"]
        target_types = ["Project"]


class Attends(BaseModel):
    rsvp_status: Optional[str] = Field(
        None, description="RSVP status, e.g., 'Attending', 'Interested', 'Declined'."
    )
    checked_in_at: Optional[str] = Field(
        None, description="ISO 8601 timestamp when the user checked in."
    )

    class Config:
        label = "ATTENDS"
        source_types = ["User"]
        target_types = ["Event"]


class InterestedIn(BaseModel):
    expressed_at: Optional[str] = Field(
        None, description="ISO 8601 timestamp when the interest was expressed."
    )

    class Config:
        label = "INTERESTED_IN"
        source_types = ["User"]
        target_types = ["Interest"]


class RelatedTo(BaseModel):
    relationship_type: Optional[str] = Field(
        None, description="Type of relationship, e.g., 'technology', 'domain', 'topic'"
    )

    class Config:
        label = "RELATED_TO"
        source_types = ["Project", "Event"]
        target_types = ["Interest"]
