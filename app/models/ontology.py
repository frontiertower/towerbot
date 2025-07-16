from typing import Optional, List
from pydantic import BaseModel, Field

# Entities
class User(BaseModel):
    """A registered individual in the Frontier Tower ecosystem."""
    first_name: str = Field(description="Full name of the user.")
    last_name: str = Field(description="Last name of the user.")
    username: str = Field(description="Username of the user.")
    affiliation: Optional[str] = Field(None, description="Organization or group the user is affiliated with.")

class Floor(BaseModel):
    """A specific floor within the Frontier Tower, with its attributes."""
    level: int = Field(description="Numeric floor level, e.g., 1 for first floor.")
    description: Optional[str] = Field(None, description="Description of the floor, e.g., 'Innovation Lab'.")
    facilities: Optional[List[str]] = Field(None, description="List of facilities available on this floor.")
    capacity: Optional[int] = Field(None, description="Maximum occupancy of the floor.")

class Event(BaseModel):
    """An event, meeting, or activity scheduled within the Frontier Tower."""
    title: str = Field(description="Title or name of the event.")
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

class Interest(BaseModel):
    """A topic, field, or area of interest relevant to users or events."""
    description: Optional[str] = Field(None, description="Brief description of the interest area.")

class Project(BaseModel):
    """A specific project being worked on by users or communities."""
    status: Optional[str] = Field("Active", description="The current status, e.g., 'Active', 'Archived'.")

# Edges
class LocatedOn(BaseModel):
    """Indicates that an event, project, or user is located on a specific floor."""
    since: Optional[str] = Field(
        None,
        description="Timestamp since the entity has been located here, as an ISO 8601 string."
    )
    details: Optional[str] = Field(None, description="Additional location details, e.g., room number.")

class WorksOn(BaseModel):
    """Represents a user's involvement in organizing or supporting a project or event."""
    role: Optional[str] = Field(None, description="Role of the user in the event, e.g., 'Speaker', 'Volunteer'.")
    assigned_at: Optional[str] = Field(
        None,
        description="When the user was assigned to the event, as an ISO 8601 string."
    )

class Attends(BaseModel):
    """Represents a user's attendance at an event."""
    rsvp_status: Optional[str] = Field(None, description="RSVP status, e.g., 'Attending', 'Interested', 'Declined'.")
    checked_in_at: Optional[str] = Field(
        None,
        description="Timestamp when the user checked in, as an ISO 8601 string."
    )

class InterestedIn(BaseModel):
    """Links a user or event to an area of interest."""
    expressed_at: Optional[str] = Field(
        None,
        description="When the interest was expressed, as an ISO 8601 string."
    )