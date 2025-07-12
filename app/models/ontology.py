from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

# Entities
class User(BaseModel):
    """A registered individual in the Frontier Tower ecosystem."""
    user_id: str = Field(description="Unique identifier for the user.")
    first_name: str = Field(description="Full name of the user.")
    last_name: str = Field(description="Last name of the user.")
    username: str = Field(description="Username of the user.")
    affiliation: Optional[str] = Field(None, description="Organization or group the user is affiliated with.")
    joined_at: datetime = Field(default_factory=datetime.now, description="Timestamp when the user joined.")

class Floor(BaseModel):
    """A specific floor within the Frontier Tower, with its attributes."""
    floor_id: str = Field(description="Unique identifier for the floor.")
    level: int = Field(description="Numeric floor level, e.g., 1 for first floor.")
    description: Optional[str] = Field(None, description="Description of the floor, e.g., 'Innovation Lab'.")
    facilities: Optional[List[str]] = Field(None, description="List of facilities available on this floor.")
    capacity: Optional[int] = Field(None, description="Maximum occupancy of the floor.")

class Event(BaseModel):
    """An event, meeting, or activity scheduled within the Frontier Tower."""
    event_id: str = Field(description="Unique identifier for the event.")
    title: str = Field(description="Title or name of the event.")
    description: Optional[str] = Field(None, description="Detailed description of the event.")
    start_time: datetime = Field(description="Start time of the event.")
    end_time: Optional[datetime] = Field(None, description="End time of the event.")
    organizer_id: str = Field(description="User ID of the event organizer.")
    floor_id: Optional[str] = Field(None, description="Floor where the event is held.")
    status: Optional[str] = Field("Scheduled", description="Current status, e.g., 'Scheduled', 'Completed', 'Cancelled'.")

class Interest(BaseModel):
    """A topic, field, or area of interest relevant to users or events."""
    interest_id: str = Field(description="Unique identifier for the interest.")
    description: Optional[str] = Field(None, description="Brief description of the interest area.")

class Project(BaseModel):
    """A specific project being worked on by users or communities."""
    project_id: str = Field(description="A unique identifier for the project.")
    status: Optional[str] = Field("Active", description="The current status, e.g., 'Active', 'Archived'.")

# Edges
class LocatedOn(BaseModel):
    """Indicates that an event or user is located on a specific floor."""
    floor_id: str = Field(description="ID of the floor where the entity is located.")
    since: Optional[datetime] = Field(None, description="Timestamp since the entity has been located here.")
    details: Optional[str] = Field(None, description="Additional location details, e.g., room number.")

class WorksOn(BaseModel):
    """Represents a user's involvement in organizing or supporting an event."""
    user_id: str = Field(description="ID of the user involved.")
    event_id: str = Field(description="ID of the event.")
    role: Optional[str] = Field(None, description="Role of the user in the event, e.g., 'Speaker', 'Volunteer'.")
    assigned_at: datetime = Field(default_factory=datetime.now, description="When the user was assigned to the event.")

class Attends(BaseModel):
    """Represents a user's attendance at an event."""
    user_id: str = Field(description="ID of the attending user.")
    event_id: str = Field(description="ID of the attended event.")
    rsvp_status: Optional[str] = Field(None, description="RSVP status, e.g., 'Attending', 'Interested', 'Declined'.")
    checked_in_at: Optional[datetime] = Field(None, description="Timestamp when the user checked in.")

class InterestedIn(BaseModel):
    """Links a user or event to an area of interest."""
    user_id: Optional[str] = Field(None, description="ID of the user expressing interest.")
    event_id: Optional[str] = Field(None, description="ID of the event related to the interest.")
    interest_id: str = Field(description="ID of the interest area.")
    expressed_at: datetime = Field(default_factory=datetime.now, description="When the interest was expressed.")