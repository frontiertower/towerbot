from enum import Enum

class NodeTypeEnum(str, Enum):
    Event = "Event"
    Floor = "Floor"
    Interest = "Interest"
    Message = "Message"
    Project = "Project"
    Topic = "Topic"
    User = "User"

class EdgeTypeEnum(str, Enum):
    Attends = "ATTENDS"
    InterestedIn = "INTERESTED_IN"
    InReplyTo = "IN_REPLY_TO"
    LocatedOn = "LOCATED_ON"
    RelatedTo = "RELATED_TO"
    Sent = "SENT"
    SentIn = "SENT_IN"
    WorksOn = "WORKS_ON"

EDGE_TYPE_MAP = {
    ("Event", "Floor"): ["LOCATED_ON"],
    ("Event", "Interest"): ["RELATED_TO"],
    ("Message", "Message"): ["IN_REPLY_TO"],
    ("Message", "Topic"): ["SENT_IN"],
    ("Project", "Floor"): ["LOCATED_ON"],
    ("Project", "Interest"): ["RELATED_TO"],
    ("User", "Event"): ["ATTENDS"],
    ("User", "Floor"): ["LOCATED_ON"],
    ("User", "Interest"): ["INTERESTED_IN"],
    ("User", "Message"): ["SENT"],
    ("User", "Project"): ["WORKS_ON"],
}
