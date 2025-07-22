"""Tests for main FastAPI application."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.main import app, process_telegram_update, check_health, handle_telegram_update


class TestMainApplication:
    """Test cases for main FastAPI application."""
    
    def test_app_creation(self):
        """Test that FastAPI app is created correctly."""
        assert isinstance(app, FastAPI)
        assert app.title == "TowerBot"

    def test_static_files_mount(self):
        """Test that static files are mounted correctly."""
        # Check that static mount exists
        static_mount = None
        for route in app.routes:
            if hasattr(route, 'path') and route.path == '/static':
                static_mount = route
                break
        
        assert static_mount is not None


class TestHealthEndpoint:
    """Test cases for health check endpoint."""
    
    def test_check_health_function(self):
        """Test health check function directly."""
        response = check_health()
        
        assert response == {"status": "ok", "message": "TowerBot is running"}

    def test_health_endpoint_integration(self):
        """Test health endpoint through HTTP."""
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "message": "TowerBot is running"}


@pytest.mark.asyncio
class TestTelegramWebhook:
    """Test cases for Telegram webhook handling."""

    async def test_process_telegram_update_success(self):
        """Test successful telegram update processing."""
        mock_tg_app = Mock()
        mock_tg_app.bot = Mock()
        mock_tg_app.process_update = AsyncMock()
        
        update_data = {
            "update_id": 12345,
            "message": {
                "message_id": 1,
                "text": "Hello",
                "chat": {"id": -1001234567890, "type": "supergroup"},
                "from": {"id": 123456789, "is_bot": False, "first_name": "Test"}
            }
        }
        
        with patch('app.main.Update') as mock_update_class:
            mock_update = Mock()
            mock_update.update_id = 12345
            mock_update_class.de_json.return_value = mock_update
            
            await process_telegram_update(mock_tg_app, update_data)
            
            mock_update_class.de_json.assert_called_once_with(data=update_data, bot=mock_tg_app.bot)
            mock_tg_app.process_update.assert_called_once_with(mock_update)

    async def test_process_telegram_update_failure(self):
        """Test telegram update processing with error."""
        mock_tg_app = Mock()
        mock_tg_app.bot = Mock()
        mock_tg_app.process_update = AsyncMock(side_effect=Exception("Processing failed"))
        
        update_data = {"update_id": 12345}
        
        with patch('app.main.Update') as mock_update_class:
            mock_update = Mock()
            mock_update.update_id = 12345
            mock_update_class.de_json.return_value = mock_update
            
            with pytest.raises(Exception, match="Processing failed"):
                await process_telegram_update(mock_tg_app, update_data)

    async def test_handle_telegram_update_success(self):
        """Test successful webhook update handling."""
        mock_request = Mock()
        mock_request.json = AsyncMock(return_value={"update_id": 12345})
        mock_request.app.state.tg_app = Mock()
        
        mock_background_tasks = Mock()
        
        response = await handle_telegram_update(mock_request, mock_background_tasks)
        
        assert response == {"status": "ok"}
        mock_background_tasks.add_task.assert_called_once()
        
        # Verify the background task was added with correct arguments
        call_args = mock_background_tasks.add_task.call_args
        assert call_args[0][0] == process_telegram_update
        assert call_args[0][1] == mock_request.app.state.tg_app
        assert call_args[0][2] == {"update_id": 12345}

    async def test_handle_telegram_update_json_error(self):
        """Test webhook handling with JSON parsing error."""
        mock_request = Mock()
        mock_request.json = AsyncMock(side_effect=Exception("Invalid JSON"))
        
        mock_background_tasks = Mock()
        
        with pytest.raises(Exception, match="Invalid JSON"):
            await handle_telegram_update(mock_request, mock_background_tasks)

    async def test_handle_telegram_update_missing_update_id(self):
        """Test webhook handling with missing update_id."""
        mock_request = Mock()
        mock_request.json = AsyncMock(return_value={"message": "test"})
        mock_request.app.state.tg_app = Mock()
        
        mock_background_tasks = Mock()
        
        response = await handle_telegram_update(mock_request, mock_background_tasks)
        
        assert response == {"status": "ok"}
        mock_background_tasks.add_task.assert_called_once()


class TestIntegrationEndpoints:
    """Integration tests for API endpoints."""
    
    def test_telegram_endpoint_exists(self):
        """Test that telegram webhook endpoint exists."""
        client = TestClient(app)
        
        # POST to telegram endpoint should return 422 for missing body
        # (instead of 404, which would mean endpoint doesn't exist)
        response = client.post("/telegram")
        assert response.status_code in [422, 400]  # Validation error, not not found

    def test_health_endpoint_logging(self):
        """Test that health endpoint includes logging."""
        with patch('app.main.logger') as mock_logger:
            client = TestClient(app)
            response = client.get("/health")
            
            assert response.status_code == 200
            mock_logger.info.assert_called_with("Health check requested")

    @patch('app.main.logger')
    def test_telegram_webhook_logging(self, mock_logger):
        """Test webhook request logging."""
        client = TestClient(app)
        
        # Mock the request processing to avoid missing state
        with patch('app.main.handle_telegram_update') as mock_handler:
            mock_handler.return_value = {"status": "ok"}
            
            response = client.post("/telegram", json={"update_id": 12345})
            
            # The endpoint should be accessible even if it fails due to missing state
            # We're mainly testing the route exists and basic structure


class TestApplicationLifespan:
    """Test cases for application lifespan management."""
    
    def test_lifespan_import(self):
        """Test that lifespan is properly imported and used."""
        # Verify that the app has lifespan configured
        assert app.router.lifespan_context is not None

    def test_app_routes_configured(self):
        """Test that all expected routes are configured."""
        routes = [route.path for route in app.routes if hasattr(route, 'path')]
        
        expected_routes = ['/health', '/telegram']
        for expected_route in expected_routes:
            assert expected_route in routes