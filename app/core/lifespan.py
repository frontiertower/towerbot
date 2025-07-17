"""Application lifespan management module for TowerBot.

This module handles the startup and shutdown lifecycle of the TowerBot application,
including initialization of services, Telegram bot setup, database connections,
and background task scheduling.
"""

import logging

from fastapi import FastAPI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from psycopg.rows import dict_row
from contextlib import asynccontextmanager
from langchain_openai import AzureChatOpenAI
from psycopg_pool import AsyncConnectionPool
from apscheduler.triggers.cron import CronTrigger
from langgraph.store.postgres.aio import AsyncPostgresStore
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.services.ai import AiService
from app.services.graph import GraphService
from app.services.database import DatabaseService
from app.core.constants import INTRODUCTION, COMMAND_EXAMPLES

logger = logging.getLogger(__name__)

pool: AsyncConnectionPool | None = None
store: AsyncPostgresStore | None = None
checkpointer: AsyncPostgresSaver | None = None

connection_kwargs = {
    "autocommit": True,
    "row_factory": dict_row,
    "prepare_threshold": None,
}

def is_valid_text_message(update: Update):
    """Check if an update contains a valid text message.
    
    Args:
        update: Telegram update object
        
    Returns:
        bool: True if the update contains a non-empty text message
    """
    return bool(update.message and update.message.text and update.message.text.strip())

def create_application(
    ai_service: AiService,
    db_service: DatabaseService,
    graph_service: GraphService,
):
    """Create and configure the Telegram bot application.
    
    Sets up the Telegram bot with all necessary handlers and injects
    the required services into the bot's data context.
    
    Args:
        ai_service: AI service instance for processing commands
        db_service: Database service for data persistence
        graph_service: Graph service for knowledge graph operations
        
    Returns:
        Application: Configured Telegram bot application
    """
    bot_data = {
        "ai_service": ai_service,
        "db_service": db_service,
        "graph_service": graph_service,
    }

    application = ApplicationBuilder().token(settings.BOT_TOKEN).build()
    application.bot_data.update(bot_data)
    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(CommandHandler(["ask", "report", "propose", "connect"], handle_command))
    message_handler = MessageHandler(
        filters.TEXT & (~filters.COMMAND) & (
            filters.ChatType.GROUP | filters.ChatType.SUPERGROUP | filters.ChatType.PRIVATE
        ),
        handle_message
    )

    application.add_handler(message_handler)
    return application

def start_scheduler(graph_service: GraphService):
    """Start the background task scheduler.
    
    Configures and starts a background scheduler for periodic tasks
    like building graph communities.
    
    Args:
        graph_service: Graph service instance for scheduled operations
        
    Returns:
        BackgroundScheduler: Started scheduler instance
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(graph_service.build_communities, CronTrigger(hour=0, minute=0))
    scheduler.start()
    logger.info("APScheduler started.")

    return scheduler

async def handle_start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command.
    
    Sends an introduction message to users who send the /start command.
    
    Args:
        update: Telegram update containing the command
        _: Telegram context (unused)
    """
    await update.message.reply_text(INTRODUCTION)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages.
    
    Processes text messages based on chat type and context:
    - Private chats: Validates user membership and provides guidance
    - Group chats: Processes messages for graph extraction and storage
    - Handles reply-based command continuation
    
    Args:
        update: Telegram update containing the message
        context: Telegram context with bot data and state
    """
    if not is_valid_text_message(update):
        return

    db_service: DatabaseService = context.application.bot_data["db_service"]
    graph_service: GraphService = context.application.bot_data["graph_service"]
    ai_service: AiService = context.application.bot_data["ai_service"]

    if update.message.chat.type == "private":
        # TODO: Confirm via BerlinHouse API if user is a citizen
        user_exists = await graph_service.check_user_exists(update.message)
        if not user_exists:
            await update.message.reply_text(
                "Sorry, you're not a member of the Frontier Tower. Please <a href='https://frontiertower.io'>join the community</a> to get access.",
                parse_mode="HTML"
            )
            return

        await update.message.reply_text("Direct conversations are coming soon. In the meantime, you can use commands (e.g. /ask, /report, /propose, /connect).")
        return

    if update.message.reply_to_message:
        pending_commands = context.application.bot_data.setdefault("pending_commands", {})
        replied_id = update.message.reply_to_message.message_id
        pending = pending_commands.get(replied_id)
        if pending and pending["user_id"] == update.message.from_user.id:
            command = pending["command"]
            text_after_command = update.message.text.strip()
            response = await ai_service.run(command, text_after_command, update.message.from_user.id)
            await update.message.reply_text(response.answer, reply_to_message_id=update.message.message_id)
            await db_service.save_command(update.message, response, command)
            del pending_commands[replied_id]
            return

    if update.message.chat.type == "supergroup":
        await graph_service.process_telegram_message(update.message)
        await db_service.save_message(update.message)
        return

async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bot commands like /ask, /report, /propose, and /connect.
    
    Processes bot commands by extracting the command and context,
    validating input, and routing to the appropriate AI service.
    
    Args:
        update: Telegram update containing the command
        context: Telegram context with bot data and state
    """
    if not is_valid_text_message(update):
        return

    try:
        ai_service: AiService = context.application.bot_data["ai_service"]
        db_service: DatabaseService = context.application.bot_data["db_service"]
        command = update.message.text.split()[0][1:]
        text_after_command = update.message.text[len(command) + 2:].strip()
        
        logger.debug(f"Processing command '{command}' from user {update.message.from_user.id}")

        if not text_after_command:
            example = COMMAND_EXAMPLES.get(command, "what's the wifi password?")
            sent_message = await update.message.reply_text(
                f"Please add some context after your command. <b>Example:</b> /{command} {example}",
                reply_to_message_id=update.message.message_id,
                parse_mode="HTML"
            )
            context.application.bot_data.setdefault("pending_commands", {})[sent_message.message_id] = {
                "command": command,
                "user_id": update.message.from_user.id,
            }
            return

        response = await ai_service.run(command, text_after_command, update.message.from_user.id)
        await update.message.reply_text(response.answer, reply_to_message_id=update.message.message_id)
        await db_service.save_command(update.message, response, command)
        logger.debug(f"Successfully processed command '{command}' from user {update.message.from_user.id}")
    except Exception as e:
        logger.error(f"Failed to process command '{command}' from user {update.message.from_user.id}: {e}")
        await update.message.reply_text("Sorry, I encountered an error processing your command. Please try again later.")
        raise 

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager.
    
    Manages the complete lifecycle of the TowerBot application:
    - Startup: Initializes services, connections, and background tasks
    - Runtime: Maintains application state
    - Shutdown: Cleanly closes connections and stops services
    
    Args:
        app: FastAPI application instance
        
    Yields:
        None: Control to the application runtime
    """
    global pool, store, checkpointer

    logger.info("Application startup sequence initiated...")
    
    try:
        llm = AzureChatOpenAI(
            api_version="2024-12-01-preview",
            azure_deployment=settings.MODEL
        )

        # Create connection pool with proper configuration
        pool = AsyncConnectionPool(
            conninfo=settings.SUPABASE_CONN_STRING,
            max_size=20,
            kwargs=connection_kwargs,
        )
        
        # Open the pool explicitly as recommended
        await pool.open()

        store = AsyncPostgresStore(
            pool,
            index={
                "dims": 1536,
                "embed": f"azure_openai:{settings.EMBEDDING_MODEL}",
            },
        )

        checkpointer = AsyncPostgresSaver(pool)

        await store.setup()
        await checkpointer.setup()

        ai_service = AiService()
        graph_service = GraphService()
        db_service = DatabaseService(pool)

        ai_service.connect(llm, store, checkpointer)

        await graph_service.connect()

        tg_app = create_application(ai_service, db_service, graph_service)

        await tg_app.initialize()

        scheduler = start_scheduler(graph_service)

        app.state.ai_service = ai_service
        app.state.db_service = db_service
        app.state.graph_service = graph_service
        app.state.tg_app = tg_app
        app.state.scheduler = scheduler

        logger.info("Application startup complete. Bot is initialized and ready.")
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise

    try:
        yield
    finally:
        logger.info("Application shutdown sequence initiated...")
        try:
            await graph_service.close()
            logger.info("Graphiti client closed.")
        except Exception as e:
            logger.error(f"Error closing Graphiti client: {e}")

        try:
            if app.state.tg_app:
                await app.state.tg_app.shutdown()
                logger.info("Telegram application shut down.")
        except Exception as e:
            logger.error(f"Error shutting down Telegram application: {e}")

        try:
            if pool:
                await pool.close()
                logger.info("Postgres connection pool closed.")
        except Exception as e:
            logger.error(f"Error closing Postgres connection pool: {e}")

        try:
            if app.state.scheduler:
                app.state.scheduler.shutdown()
                logger.info("APScheduler shut down.")
        except Exception as e:
            logger.error(f"Error shutting down APScheduler: {e}")

        logger.info("Application shutdown complete.")