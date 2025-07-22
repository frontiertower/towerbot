"""Webhook configuration script for TowerBot.

This module provides functionality to set up the Telegram webhook URL
for receiving updates from the Telegram Bot API.
"""

import logging
import asyncio

from telegram import Update
from telegram.ext import Application, ApplicationBuilder

from app.core.config import settings

logger = logging.getLogger(__name__)

async def main():
    """Configure and set the Telegram webhook URL.
    
    Creates a Telegram application instance and sets the webhook URL
    to receive updates from the Telegram Bot API.
    """
    webhook_url = f"{settings.WEBHOOK_URL}/telegram"
    
    tg_app: Application = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    logger.info("Setting Telegram webhook...")
    
    await tg_app.bot.set_webhook(
        url=webhook_url, 
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True 
    )

    logger.info(f"Webhook set to {webhook_url}")

if __name__ == "__main__":
    asyncio.run(main())