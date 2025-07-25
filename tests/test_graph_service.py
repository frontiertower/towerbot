"""Tests for Graph service functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from app.services.graph import GraphService, get_graphiti_client
from app.schemas.generated_enums import NodeTypeEnum, EdgeTypeEnum


class TestGraphService:
    """Test cases for GraphService class."""

    def test_init(self, graph_service):
        """Test GraphService initialization."""
        assert graph_service.graphiti is None
        assert isinstance(graph_service.entity_types, dict)
        assert isinstance(graph_service.edge_types, dict)
        assert isinstance(graph_service.edge_type_map, dict)
        
        # Verify entity types are properly mapped
        assert NodeTypeEnum.User.value in graph_service.entity_types
        assert NodeTypeEnum.Topic.value in graph_service.entity_types
        assert NodeTypeEnum.Message.value in graph_service.entity_types
        
        # Verify edge types are properly mapped
        assert EdgeTypeEnum.Sent.value in graph_service.edge_types
        assert EdgeTypeEnum.SentIn.value in graph_service.edge_types

    @pytest.mark.asyncio
    @patch('app.services.graph.get_graphiti_client')
    async def test_connect_success(self, mock_get_client, graph_service, mock_graphiti, mock_settings):
        """Test successful GraphService connection."""
        mock_get_client.return_value = mock_graphiti
        
        with patch('app.services.graph.settings', mock_settings):
            mock_settings.APP_ENV = "prod"
            await graph_service.connect()
            
            assert graph_service.graphiti == mock_graphiti
            mock_graphiti.build_indices_and_constraints.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.graph.get_graphiti_client')
    async def test_connect_dev_environment(self, mock_get_client, graph_service, mock_graphiti, mock_settings):
        """Test GraphService connection in development environment."""
        mock_get_client.return_value = mock_graphiti
        
        with patch('app.services.graph.settings', mock_settings):
            mock_settings.APP_ENV = "dev"
            await graph_service.connect()
            
            assert graph_service.graphiti == mock_graphiti
            mock_graphiti.build_indices_and_constraints.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.graph.get_graphiti_client')
    async def test_connect_failure(self, mock_get_client, graph_service):
        """Test GraphService connection failure."""
        mock_get_client.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            await graph_service.connect()

    @pytest.mark.asyncio
    async def test_close_success(self, graph_service, mock_graphiti):
        """Test successful GraphService close."""
        graph_service.graphiti = mock_graphiti
        
        await graph_service.close()
        
        mock_graphiti.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_no_client(self, graph_service):
        """Test closing when no graphiti client exists."""
        # Should not raise any exception
        await graph_service.close()

    @pytest.mark.asyncio
    async def test_close_with_error(self, graph_service, mock_graphiti):
        """Test closing with error."""
        graph_service.graphiti = mock_graphiti
        mock_graphiti.close.side_effect = Exception("Close error")
        
        # Should not raise exception, just log it
        await graph_service.close()

    @pytest.mark.asyncio
    async def test_build_communities_prod(self, graph_service, mock_graphiti, mock_settings):
        """Test building communities in production environment."""
        graph_service.graphiti = mock_graphiti
        
        with patch('app.services.graph.settings', mock_settings):
            mock_settings.APP_ENV = "prod"
            
            await graph_service.build_communities()
            
            mock_graphiti.build_communities.assert_called_once()

    @pytest.mark.asyncio
    async def test_build_communities_dev(self, graph_service, mock_graphiti, mock_settings):
        """Test build_communities does nothing in dev environment."""
        graph_service.graphiti = mock_graphiti
        
        with patch('app.services.graph.settings', mock_settings):
            mock_settings.APP_ENV = "dev"
            
            await graph_service.build_communities()
            
            mock_graphiti.build_communities.assert_not_called()

    @pytest.mark.asyncio
    async def test_build_communities_no_client(self, graph_service, mock_settings):
        """Test build_communities with no graphiti client."""
        with patch('app.services.graph.settings', mock_settings):
            mock_settings.APP_ENV = "prod"
            
            # Should not raise exception
            await graph_service.build_communities()

    @pytest.mark.asyncio
    async def test_check_user_exists_true(self, graph_service, mock_graphiti, mock_telegram_message):
        """Test checking if user exists - user found."""
        graph_service.graphiti = mock_graphiti
        mock_result = Mock()
        mock_result.records = [Mock()]
        mock_graphiti.driver.execute_query = AsyncMock(return_value=mock_result)
        
        result = await graph_service.check_user_exists(mock_telegram_message)
        
        assert result is True
        mock_graphiti.driver.execute_query.assert_called_once_with(
            "\n        MATCH (n:User {user_id: $user_id})\n        RETURN n.user_id\n        LIMIT 1\n        ",
            user_id=mock_telegram_message.from_user.id
        )

    @pytest.mark.asyncio
    async def test_check_user_exists_false(self, graph_service, mock_graphiti, mock_telegram_message):
        """Test checking if user exists - user not found."""
        graph_service.graphiti = mock_graphiti
        mock_result = Mock()
        mock_result.records = []
        mock_graphiti.driver.execute_query = AsyncMock(return_value=mock_result)
        
        result = await graph_service.check_user_exists(mock_telegram_message)
        
        assert result is False
        mock_graphiti.driver.execute_query.assert_called_once_with(
            "\n        MATCH (n:User {user_id: $user_id})\n        RETURN n.user_id\n        LIMIT 1\n        ",
            user_id=mock_telegram_message.from_user.id
        )

    @pytest.mark.asyncio
    async def test_check_user_exists_no_records_attr(self, graph_service, mock_graphiti, mock_telegram_message):
        """Test checking if user exists with no records attribute."""
        graph_service.graphiti = mock_graphiti
        mock_result = True  # Boolean result instead of object with records
        mock_graphiti.driver.execute_query = AsyncMock(return_value=mock_result)
        
        result = await graph_service.check_user_exists(mock_telegram_message)
        
        assert result is True
        mock_graphiti.driver.execute_query.assert_called_once_with(
            "\n        MATCH (n:User {user_id: $user_id})\n        RETURN n.user_id\n        LIMIT 1\n        ",
            user_id=mock_telegram_message.from_user.id
        )

    @pytest.mark.asyncio
    async def test_process_message_success(self, graph_service, mock_graphiti, mock_telegram_message, mock_settings):
        """Test successful message processing."""
        graph_service.graphiti = mock_graphiti
        
        with patch('app.services.graph.settings', mock_settings):
            mock_settings.GROUP_ID = "123"
            
            await graph_service.add_episode(mock_telegram_message)
            
            mock_graphiti.add_episode.assert_called_once()
            call_args = mock_graphiti.add_episode.call_args
            assert call_args.kwargs['name'] == f"telegram_message_{mock_telegram_message.message_id}"
            assert call_args.kwargs['group_id'] == "123"
            assert "Topic" in call_args.kwargs['excluded_entity_types']
            assert "Floor" in call_args.kwargs['excluded_entity_types']

    @pytest.mark.asyncio
    async def test_process_message_failure(self, graph_service, mock_graphiti, mock_telegram_message, mock_settings):
        """Test message processing failure."""
        graph_service.graphiti = mock_graphiti
        mock_graphiti.add_episode.side_effect = Exception("Processing failed")
        
        with patch('app.services.graph.settings', mock_settings):
            mock_settings.GROUP_ID = "123"
            
            with pytest.raises(Exception, match="Processing failed"):
                await graph_service.add_episode(mock_telegram_message)

    @pytest.mark.asyncio
    @patch('app.services.graph.EpisodicNode')
    async def test_reprocess_all_episodes_success(self, mock_episodic_node, graph_service, mock_graphiti, mock_settings):
        """Test successful episode reprocessing."""
        graph_service.graphiti = mock_graphiti
        mock_episodes = [Mock(), Mock(), Mock()]
        mock_episodic_node.get_by_group_ids = AsyncMock(return_value=mock_episodes)
        
        with patch('app.services.graph.settings', mock_settings):
            mock_settings.GROUP_ID = "123"
            
            await graph_service.reprocess_all_episodes()
            
            mock_episodic_node.get_by_group_ids.assert_called_once_with(
                mock_graphiti.driver, group_ids=["123"]
            )
            mock_graphiti.add_episode_bulk.assert_called_once_with(
                mock_episodes,
                entity_types=graph_service.entity_types,
                excluded_entity_types=["Topic", "Floor"],
                edge_types=graph_service.edge_types,
                edge_type_map=graph_service.edge_type_map,
            )

    @pytest.mark.asyncio
    @patch('app.services.graph.EpisodicNode')
    async def test_reprocess_all_episodes_failure(self, mock_episodic_node, graph_service, mock_graphiti, mock_settings):
        """Test episode reprocessing failure."""
        graph_service.graphiti = mock_graphiti
        mock_episodic_node.get_by_group_ids.side_effect = Exception("Reprocessing failed")
        
        with patch('app.services.graph.settings', mock_settings):
            mock_settings.GROUP_ID = "123"
            
            with pytest.raises(Exception, match="Reprocessing failed"):
                await graph_service.reprocess_all_episodes()


class TestGetGraphitiClient:
    """Test cases for get_graphiti_client function."""
    
    @patch('app.services.graph.AsyncAzureOpenAI')
    @patch('app.services.graph.Graphiti')
    @patch('app.services.graph.OpenAIClient')
    @patch('app.services.graph.OpenAIEmbedder')
    @patch('app.services.graph.OpenAIRerankerClient')
    def test_get_graphiti_client(self, mock_reranker, mock_embedder, mock_llm_client, 
                                mock_graphiti_class, mock_azure_openai, mock_settings):
        """Test Graphiti client creation."""
        mock_azure_instance = Mock()
        mock_azure_openai.return_value = mock_azure_instance
        mock_graphiti_instance = Mock()
        mock_graphiti_class.return_value = mock_graphiti_instance
        
        with patch('app.services.graph.settings', mock_settings):
            result = get_graphiti_client()
            
            assert result == mock_graphiti_instance
            mock_graphiti_class.assert_called_once()
            mock_azure_openai.assert_called()  # Called twice for LLM and embedding clients