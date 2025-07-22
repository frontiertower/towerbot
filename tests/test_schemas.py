"""Tests for schema definitions and data models."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from app.schemas.tools import SearchInputSchema, SearchRecipeEnum, NodeTypeEnum, EdgeTypeEnum
from app.schemas.responses import *
from app.schemas.ontology import *
from app.schemas.generated_enums import EDGE_TYPE_MAP


class TestToolSchemas:
    """Test cases for tool-related schemas."""
    
    def test_search_input_schema_validation(self):
        """Test SearchInputSchema validation."""
        # Valid schema
        valid_data = {
            "query": "test query",
            "recipe": SearchRecipeEnum.COMBINED_HYBRID_SEARCH_MMR,
            "edge_types": [EdgeTypeEnum.Sent],
            "node_labels": [NodeTypeEnum.User]
        }
        
        schema = SearchInputSchema(**valid_data)
        assert schema.query == "test query"
        assert schema.recipe == SearchRecipeEnum.COMBINED_HYBRID_SEARCH_MMR
        assert EdgeTypeEnum.Sent in schema.edge_types
        assert NodeTypeEnum.User in schema.node_labels

    def test_search_input_schema_minimal(self):
        """Test SearchInputSchema with minimal required fields."""
        minimal_data = {"query": "minimal test"}
        
        schema = SearchInputSchema(**minimal_data)
        assert schema.query == "minimal test"
        assert schema.recipe is None
        assert schema.edge_types is None
        assert schema.node_labels is None

    def test_search_recipe_enum_values(self):
        """Test SearchRecipeEnum contains expected values."""
        expected_values = [
            "COMBINED_HYBRID_SEARCH_MMR",
            "COMBINED_HYBRID_SEARCH_CROSS_ENCODER",
            "EDGE_HYBRID_SEARCH_RRF",
            "EDGE_HYBRID_SEARCH_MMR",
            "NODE_HYBRID_SEARCH_RRF",
            "COMMUNITY_HYBRID_SEARCH_MMR"
        ]
        
        actual_values = [recipe.value for recipe in SearchRecipeEnum]
        
        for expected in expected_values:
            assert expected in actual_values

    def test_node_type_enum_values(self):
        """Test NodeTypeEnum contains expected values."""
        expected_values = ["User", "Topic", "Message", "Event", "Interest", "Project", "Floor"]
        
        actual_values = [node_type.value for node_type in NodeTypeEnum]
        
        for expected in expected_values:
            assert expected in actual_values

    def test_edge_type_enum_values(self):
        """Test EdgeTypeEnum contains expected values."""
        expected_values = [
            "Sent", "SentIn", "InReplyTo", "LocatedOn", 
            "WorksOn", "Attends", "InterestedIn", "RelatedTo"
        ]
        
        actual_values = [edge_type.value for edge_type in EdgeTypeEnum]
        
        for expected in expected_values:
            assert expected in actual_values


class TestOntologySchemas:
    """Test cases for ontology-related schemas."""
    
    def test_user_node_creation(self):
        """Test User node schema creation."""
        user_data = {
            "user_id": 123456789,
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User"
        }
        
        user = User(**user_data)
        assert user.user_id == 123456789
        assert user.username == "testuser"
        assert user.first_name == "Test"
        assert user.last_name == "User"

    def test_message_node_creation(self):
        """Test Message node schema creation."""
        message_data = {
            "message_id": 12345,
            "text": "Test message content",
            "timestamp": "2023-07-20T10:00:00Z"
        }
        
        message = Message(**message_data)
        assert message.message_id == 12345
        assert message.text == "Test message content"
        assert message.timestamp == "2023-07-20T10:00:00Z"

    def test_topic_node_creation(self):
        """Test Topic node schema creation."""
        topic_data = {
            "topic_id": 123,
            "title": "Artificial Intelligence"
        }
        
        topic = Topic(**topic_data)
        assert topic.topic_id == 123
        assert topic.title == "Artificial Intelligence"

    def test_event_node_creation(self):
        """Test Event node schema creation."""
        event_data = {
            "title": "TowerBot Meetup",
            "description": "Monthly community meetup",
            "start_at": "2023-07-20T18:00:00Z",
            "end_at": "2023-07-20T20:00:00Z"
        }
        
        event = Event(**event_data)
        assert event.title == "TowerBot Meetup"
        assert event.description == "Monthly community meetup"
        assert event.start_at == "2023-07-20T18:00:00Z"
        assert event.end_at == "2023-07-20T20:00:00Z"

    def test_project_node_creation(self):
        """Test Project node schema creation."""
        project_data = {
            "title": "TowerBot Development",
            "description": "AI-powered Telegram bot for community management",
            "status": "Active"
        }
        
        project = Project(**project_data)
        assert project.title == "TowerBot Development"
        assert project.description == "AI-powered Telegram bot for community management"
        assert project.status == "Active"

    def test_interest_node_creation(self):
        """Test Interest node schema creation."""
        interest_data = {
            "title": "Machine Learning"
        }
        
        interest = Interest(**interest_data)
        assert interest.title == "Machine Learning"

    def test_floor_node_creation(self):
        """Test Floor node schema creation."""
        floor_data = {
            "level": 5,
            "description": "Creative workspace and collaboration area",
            "facilities": ["WiFi", "Conference Room", "Kitchen"]
        }
        
        floor = Floor(**floor_data)
        assert floor.level == 5
        assert floor.description == "Creative workspace and collaboration area"
        assert "WiFi" in floor.facilities


class TestRelationshipSchemas:
    """Test cases for relationship/edge schemas."""
    
    def test_sent_edge_creation(self):
        """Test Sent relationship schema creation."""
        sent = Sent()
        # Sent edge has no properties in the actual schema
        assert sent is not None

    def test_sent_in_edge_creation(self):
        """Test SentIn relationship schema creation."""
        sent_in = SentIn()
        # SentIn edge has no properties in the actual schema
        assert sent_in is not None

    def test_in_reply_to_edge_creation(self):
        """Test InReplyTo relationship schema creation."""
        in_reply_to = InReplyTo()
        # InReplyTo edge has no properties in the actual schema
        assert in_reply_to is not None

    def test_works_on_edge_creation(self):
        """Test WorksOn relationship schema creation."""
        works_on_data = {
            "role": "Developer",
            "assigned_at": "2023-07-20T10:00:00Z"
        }
        
        works_on = WorksOn(**works_on_data)
        assert works_on.role == "Developer"
        assert works_on.assigned_at == "2023-07-20T10:00:00Z"

    def test_attends_edge_creation(self):
        """Test Attends relationship schema creation."""
        attends_data = {
            "rsvp_status": "Attending",
            "checked_in_at": "2023-07-20T18:00:00Z"
        }
        
        attends = Attends(**attends_data)
        assert attends.rsvp_status == "Attending"
        assert attends.checked_in_at == "2023-07-20T18:00:00Z"

    def test_interested_in_edge_creation(self):
        """Test InterestedIn relationship schema creation."""
        interested_in_data = {
            "expressed_at": "2023-07-20T10:00:00Z"
        }
        
        interested_in = InterestedIn(**interested_in_data)
        assert interested_in.expressed_at == "2023-07-20T10:00:00Z"

    def test_located_on_edge_creation(self):
        """Test LocatedOn relationship schema creation."""
        located_on_data = {
            "since": "2023-07-20T10:00:00Z",
            "details": "Room 5A"
        }
        
        located_on = LocatedOn(**located_on_data)
        assert located_on.since == "2023-07-20T10:00:00Z"
        assert located_on.details == "Room 5A"

    def test_related_to_edge_creation(self):
        """Test RelatedTo relationship schema creation."""
        related_to_data = {
            "relationship_type": "technology"
        }
        
        related_to = RelatedTo(**related_to_data)
        assert related_to.relationship_type == "technology"


class TestGeneratedEnums:
    """Test cases for generated enums and mappings."""
    
    def test_edge_type_map_structure(self):
        """Test that EDGE_TYPE_MAP has expected structure."""
        assert isinstance(EDGE_TYPE_MAP, dict)
        assert len(EDGE_TYPE_MAP) > 0
        
        # Each key should be a tuple of node types
        for key in EDGE_TYPE_MAP.keys():
            assert isinstance(key, tuple)
            assert len(key) == 2
            
        # Each value should be a list of edge types
        for value in EDGE_TYPE_MAP.values():
            assert isinstance(value, list)
            for edge_type in value:
                assert isinstance(edge_type, str)

    def test_edge_type_map_contains_expected_mappings(self):
        """Test that EDGE_TYPE_MAP contains some expected mappings."""
        # Test some logical mappings that should exist
        user_message_key = None
        for key in EDGE_TYPE_MAP.keys():
            if "User" in key and "Message" in key:
                user_message_key = key
                break
        
        assert user_message_key is not None
        assert "Sent" in EDGE_TYPE_MAP[user_message_key]

    def test_enum_consistency(self):
        """Test consistency between enums and schemas."""
        # All NodeTypeEnum values should correspond to actual node classes
        node_type_values = [node_type.value for node_type in NodeTypeEnum]
        expected_nodes = ["User", "Topic", "Message", "Event", "Interest", "Project", "Floor"]
        
        for expected in expected_nodes:
            assert expected in node_type_values
        
        # All EdgeTypeEnum values should correspond to actual edge classes  
        edge_type_values = [edge_type.value for edge_type in EdgeTypeEnum]
        expected_edges = ["Sent", "SentIn", "InReplyTo", "LocatedOn", "WorksOn", "Attends", "InterestedIn", "RelatedTo"]
        
        for expected in expected_edges:
            assert expected in edge_type_values