import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from telegram import Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings

from app.core.config import settings
from app.core.constants import INTRODUCTION, COMMAND_EXAMPLES
from app.services.ai import AiService
from app.services.graph import GraphService
from app.services.database import DatabaseService

logger = logging.getLogger(__name__)

def is_valid_text_message(update: Update) -> bool:
    return bool(update.message and update.message.text and update.message.text.strip())

def create_telegram_application(
    ai_service: AiService,
    db_service: DatabaseService,
    graph_service: GraphService,
) -> Application:
    bot_data = {
        "ai_service": ai_service,
        "db_service": db_service,
        "graph_service": graph_service,
    }
    application = ApplicationBuilder().token(settings.BOT_TOKEN).build()
    application.bot_data.update(bot_data)
    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(CommandHandler(["ask", "help", "connect"], handle_command))
    message_handler = MessageHandler(
        filters.TEXT & (~filters.COMMAND) & (
            filters.ChatType.GROUP | filters.ChatType.SUPERGROUP | filters.ChatType.PRIVATE
        ),
        handle_message
    )
    application.add_handler(message_handler)
    return application

def start_scheduler(graph_service: GraphService) -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(graph_service.build_communities, CronTrigger(hour=0, minute=0))
    scheduler.start()
    logger.info("APScheduler started.")
    return scheduler

async def handle_start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(INTRODUCTION)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_valid_text_message(update):
        return
    db_service: DatabaseService = context.application.bot_data["db_service"]
    graph_service: GraphService = context.application.bot_data["graph_service"]
    ai_service: AiService = context.application.bot_data["ai_service"]
    if update.message.chat.type == "private":
        await update.message.reply_text("Direct conversations are coming soon. In the meantime, you can use commands (e.g. /ask, /help, /connect).")
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
    if settings.APP_ENV == "prod":
        await db_service.save_message(update.message)
        if update.message.chat.type == "supergroup":
            await graph_service.process_telegram_message(update.message)

async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_valid_text_message(update):
        return
    ai_service: AiService = context.application.bot_data["ai_service"]
    db_service: DatabaseService = context.application.bot_data["db_service"]
    command = update.message.text.split()[0][1:]
    text_after_command = update.message.text[len(command) + 2:].strip()
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
    if settings.APP_ENV == "prod":
        await db_service.save_command(update.message, response, command)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup sequence initiated...")

    llm = AzureChatOpenAI(
        api_version="2024-12-01-preview",
        azure_deployment=settings.MODEL
    )

    embeddings = AzureOpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        openai_api_version="2024-12-01-preview"
    )

    store = InMemoryStore(
        index={
            "dims": 1536,
            "embed": f"azure_openai:{settings.EMBEDDING_MODEL}"
        }
    )

    checkpointer = MemorySaver()

    ai_service = AiService()
    db_service = DatabaseService()
    graph_service = GraphService()

    ai_service.connect(llm, embeddings, store, checkpointer)
    db_service.connect()
    await graph_service.connect()

    tg_app = create_telegram_application(ai_service, db_service, graph_service)
    await tg_app.initialize()

    scheduler = start_scheduler(graph_service)

    app.state.ai_service = ai_service
    app.state.db_service = db_service
    app.state.graph_service = graph_service
    app.state.tg_app = tg_app
    app.state.scheduler = scheduler

    logger.info("Application startup complete. Bot is initialized and ready.")

    try:
        yield

    finally:
        logger.info("Application shutdown sequence initiated...")

        await graph_service.close()
        logger.info("Graphiti client closed.")

        if app.state.tg_app:
            await app.state.tg_app.shutdown()
            logger.info("Telegram application shut down.")

        if app.state.scheduler:
            app.state.scheduler.shutdown()
            logger.info("APScheduler shut down.")

        logger.info("Application shutdown complete.")