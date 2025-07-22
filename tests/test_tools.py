"""Tests for core tools and utilities."""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, mock_open
from datetime import datetime
from pathlib import Path

import httpx

from app.core.tools import (
    get_jwt_token, summarize_calendar_events, get_calendar_events_tool,
    get_tower_communities, get_tower_info, get_connections,
    get_qa_agent_tools, get_connect_agent_tools, SEARCH_RECIPE_MAP
)
from app.schemas.tools import SearchRecipeEnum, NodeTypeEnum, EdgeTypeEnum


@pytest.mark.asyncio
class TestExternalAPITools:
    """Test cases for external API integration tools."""

    @patch('app.core.tools.httpx.AsyncClient')
    async def test_get_jwt_token_success(self, mock_client_class, mock_settings):
        """Test successful JWT token retrieval."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.json.return_value = {"access": "test-token"}
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        with patch('app.core.tools.settings', mock_settings):
            token = await get_jwt_token()
            
            assert token == "test-token"
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "https://api.berlinhouse.com/auth/login/"
            assert call_args[1]["json"]["email"] == mock_settings.BERLINHOUSE_EMAIL
            assert call_args[1]["json"]["password"] == mock_settings.BERLINHOUSE_PASSWORD

    @patch('app.core.tools.httpx.AsyncClient')
    async def test_get_jwt_token_http_error(self, mock_client_class, mock_settings):
        """Test JWT token retrieval with HTTP error."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=Mock(), response=mock_response
        )
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        with patch('app.core.tools.settings', mock_settings):
            with pytest.raises(Exception, match="API Error: 401"):
                await get_jwt_token()

    @patch('app.core.tools.httpx.AsyncClient')
    async def test_get_jwt_token_request_error(self, mock_client_class, mock_settings):
        """Test JWT token retrieval with request error."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.RequestError("Connection failed")
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        with patch('app.core.tools.settings', mock_settings):
            with pytest.raises(Exception, match="API Request Error"):
                await get_jwt_token()

    async def test_summarize_calendar_events(self, mock_llm):
        """Test calendar events summarization."""
        test_events = {
            "events": [
                {"title": "Test Event", "date": "2023-07-20"},
                {"title": "Another Event", "date": "2023-07-21"}
            ]
        }
        
        mock_llm.ainvoke.return_value = Mock(content="Summary of events")
        
        result = await summarize_calendar_events(test_events, mock_llm)
        
        assert result == "Summary of events"
        mock_llm.ainvoke.assert_called_once()
        call_args = mock_llm.ainvoke.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0]["role"] == "system"
        assert call_args[1]["role"] == "user"

    @patch('app.core.tools.httpx.AsyncClient')
    async def test_get_calendar_events_tool_success(self, mock_client_class, mock_llm):
        """Test successful calendar events retrieval."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.json.return_value = {"events": ["event1", "event2"]}
        mock_response.raise_for_status = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        mock_llm.ainvoke.return_value = Mock(content="Events summary")
        
        calendar_tool = get_calendar_events_tool(mock_llm)
        result = await calendar_tool()
        
        assert result == "Events summary"
        mock_client.get.assert_called_once()

    @patch('app.core.tools.httpx.AsyncClient')
    async def test_get_calendar_events_tool_http_error(self, mock_client_class, mock_llm):
        """Test calendar events retrieval with HTTP error."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Internal Server Error", request=Mock(), response=mock_response
        )
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        calendar_tool = get_calendar_events_tool(mock_llm)
        
        with pytest.raises(Exception, match="API Error: 500"):
            await calendar_tool()

    @patch('app.core.tools.get_jwt_token')
    @patch('app.core.tools.httpx.AsyncClient')
    async def test_get_tower_communities_success(self, mock_client_class, mock_jwt):
        """Test successful tower communities retrieval."""
        mock_jwt.return_value = "test-token"
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.json.return_value = {"communities": ["community1", "community2"]}
        mock_response.raise_for_status = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        result = await get_tower_communities()
        
        assert result == {"communities": ["community1", "community2"]}
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-token"

    @patch('app.core.tools.get_jwt_token')
    @patch('app.core.tools.httpx.AsyncClient')
    async def test_get_tower_communities_http_error(self, mock_client_class, mock_jwt):
        """Test tower communities retrieval with HTTP error."""
        mock_jwt.return_value = "test-token"
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "403 Forbidden", request=Mock(), response=mock_response
        )
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        with pytest.raises(Exception, match="API Error: 403"):
            await get_tower_communities()


class TestLocalDataTools:
    """Test cases for local data access tools."""

    @patch('builtins.open', new_callable=mock_open, read_data='{"building": "test"}')
    def test_get_tower_info_success(self, mock_file):
        """Test successful tower info retrieval."""
        result = get_tower_info()
        
        assert result == {"building": "test"}
        mock_file.assert_called_once()

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_get_tower_info_file_not_found(self, mock_file):
        """Test tower info retrieval with missing file."""
        with pytest.raises(FileNotFoundError):
            get_tower_info()

    @patch('builtins.open', new_callable=mock_open, read_data='invalid json')
    def test_get_tower_info_invalid_json(self, mock_file):
        """Test tower info retrieval with invalid JSON."""
        with pytest.raises(json.JSONDecodeError):
            get_tower_info()


@pytest.mark.asyncio
class TestGraphSearchTools:
    """Test cases for graph search tools."""

    @patch('app.core.tools.get_graphiti_client')
    async def test_get_connections_default_recipe(self, mock_get_client):
        """Test get_connections with default recipe."""
        mock_graphiti = AsyncMock()
        mock_graphiti.search_.return_value = ["connection1", "connection2"]
        mock_get_client.return_value = mock_graphiti
        
        result = await get_connections("test query")
        
        assert result == ["connection1", "connection2"]
        mock_graphiti.search_.assert_called_once()
        call_args = mock_graphiti.search_.call_args
        assert call_args[1]["query"] == "test query"

    @patch('app.core.tools.get_graphiti_client')
    async def test_get_connections_custom_recipe(self, mock_get_client):
        """Test get_connections with custom recipe."""
        mock_graphiti = AsyncMock()
        mock_graphiti.search_.return_value = ["connection1"]
        mock_get_client.return_value = mock_graphiti
        
        result = await get_connections(
            "test query", 
            recipe=SearchRecipeEnum.NODE_HYBRID_SEARCH_MMR
        )
        
        assert result == ["connection1"]
        mock_graphiti.search_.assert_called_once()

    @patch('app.core.tools.get_graphiti_client')
    async def test_get_connections_with_filters(self, mock_get_client):
        """Test get_connections with node and edge filters."""
        mock_graphiti = AsyncMock()
        mock_graphiti.search_.return_value = ["filtered_connection"]
        mock_get_client.return_value = mock_graphiti
        
        result = await get_connections(
            "test query",
            node_labels=[NodeTypeEnum.User, NodeTypeEnum.Project],
            edge_types=[EdgeTypeEnum.WorksOn]
        )
        
        assert result == ["filtered_connection"]
        mock_graphiti.search_.assert_called_once()
        call_args = mock_graphiti.search_.call_args
        assert call_args[1]["search_filter"] is not None


class TestToolConfiguration:
    """Test cases for tool configuration and mappings."""

    def test_search_recipe_map_completeness(self):
        """Test that all search recipes are mapped."""
        # All enum values should be in the map
        for recipe in SearchRecipeEnum:
            assert recipe in SEARCH_RECIPE_MAP
        
        # All map values should be valid
        for recipe_config in SEARCH_RECIPE_MAP.values():
            assert recipe_config is not None

    def test_get_qa_agent_tools(self, mock_llm):
        """Test QA agent tools configuration."""
        tools = get_qa_agent_tools(mock_llm)
        
        assert len(tools) > 0
        # Should include tower info tool and calendar events tool
        tool_names = [tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in tools]
        assert any('get_tower_info' in str(tool) or 'tower' in str(tool).lower() for tool in tool_names)

    def test_get_connect_agent_tools(self):
        """Test Connect agent tools configuration."""
        tools = get_connect_agent_tools()
        
        assert len(tools) > 0
        # Should include connections tool
        tool_names = [tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in tools]
        assert any('get_connections' in str(tool) or 'connection' in str(tool).lower() for tool in tool_names)

    def test_search_recipe_enum_values(self):
        """Test that SearchRecipeEnum has expected values."""
        expected_recipes = [
            "COMBINED_HYBRID_SEARCH_MMR",
            "COMBINED_HYBRID_SEARCH_CROSS_ENCODER", 
            "EDGE_HYBRID_SEARCH_RRF",
            "NODE_HYBRID_SEARCH_MMR",
            "COMMUNITY_HYBRID_SEARCH_RRF"
        ]
        
        recipe_values = [recipe.value for recipe in SearchRecipeEnum]
        
        for expected in expected_recipes:
            assert expected in recipe_values