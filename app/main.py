"""Main FastAPI application module for TowerBot.

This module contains the core FastAPI application setup and request handlers for the TowerBot
system, which processes Telegram updates and provides health monitoring endpoints.
"""

import logging

from telegram import Update
from starlette.routing import Mount
from fastapi.staticfiles import StaticFiles
from mcp.server.sse import SseServerTransport
from fastapi import FastAPI, Request, BackgroundTasks, Depends

from app.core.lifespan import lifespan
from app.services.auth import auth_service
from app.mcp.tower import mcp as tower_mcp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
    ]
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

app = FastAPI(lifespan=lifespan)

sse = SseServerTransport("/messages")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.router.routes.append(Mount("/messages", app=sse.handle_post_message))

async def process_telegram_update(tg_app, update_data):
    """Process a Telegram update in the background.
    
    Args:
        tg_app: The Telegram application instance
        update_data: Raw update data from Telegram webhook
    """
    try:
        update = Update.de_json(data=update_data, bot=tg_app.bot)
        logger.debug(f"Processing Telegram update {update.update_id}")
        await tg_app.process_update(update)
        logger.info(f"Finished processing Telegram update {update.update_id}")
    except Exception as e:
        logger.error(f"Failed to process Telegram update: {e}")
        raise

@app.get("/health")
def check_health():
    """Health check endpoint for monitoring service status.
    
    Returns:
        dict: Status information indicating service health
    """
    logger.info("Health check requested")
    return {"status": "ok", "message": "TowerBot is running"}

@app.post("/telegram")
async def handle_telegram_update(request: Request, background_tasks: BackgroundTasks):
    """Handle incoming Telegram webhook updates.
    
    Receives webhook updates from Telegram and queues them for background processing
    to ensure fast response times and prevent webhook timeouts.
    
    Args:
        request: The incoming HTTP request containing update data
        background_tasks: FastAPI background tasks manager
        
    Returns:
        dict: Status confirmation message
    """
    try:
        update_data = await request.json()
        update_id = update_data.get('update_id', 'unknown')
        logger.info(f"Telegram update {update_id} received, queueing for background processing")
        
        tg_app = request.app.state.tg_app
        background_tasks.add_task(process_telegram_update, tg_app, update_data)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Failed to handle Telegram update: {e}")
        raise


@app.api_route("/sse", methods=["GET", "POST"], tags=["MCP"], dependencies=[Depends(auth_service.require_api_key)])
async def handle_sse(request: Request):
    """
    SSE endpoint for MCP server.

    This endpoint establishes a Server-Sent Events (SSE) connection for the MCP (Multi-Channel Processor)
    server, allowing real-time bidirectional communication with authenticated clients. Requires a valid API key.

    Args:
        request (Request): The incoming HTTP request.

    Returns:
        Streaming response for SSE communication.
    """
    async with sse.connect_sse(request.scope, request.receive, request._send) as (
        read_stream,
        write_stream,
    ):
        init_options = tower_mcp._mcp_server.create_initialization_options()
        await tower_mcp._mcp_server.run(
            read_stream,
            write_stream,
            init_options,
        )