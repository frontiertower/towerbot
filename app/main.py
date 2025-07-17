"""Main FastAPI application module for TowerBot.

This module contains the core FastAPI application setup and request handlers for the TowerBot
system, which processes Telegram updates and provides health monitoring endpoints.
"""

import logging

from telegram import Update
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Request, BackgroundTasks

from app.core.lifespan import lifespan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

app = FastAPI(title="TowerBot", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

async def process_telegram_update(tg_app, update_data):
    """Process a Telegram update in the background.
    
    Args:
        tg_app: The Telegram application instance
        update_data: Raw update data from Telegram webhook
    """
    update = Update.de_json(data=update_data, bot=tg_app.bot)
    await tg_app.process_update(update)
    logger.info("Finished processing Telegram update in the background.")

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
    logger.info("Telegram update received, queueing for background processing.")
    tg_app = request.app.state.tg_app
    update_data = await request.json()

    background_tasks.add_task(process_telegram_update, tg_app, update_data)
    return {"status": "ok"}