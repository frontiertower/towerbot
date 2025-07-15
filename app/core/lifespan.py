import logging

from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from fastapi import FastAPI
from telegram import Update
from contextlib import asynccontextmanager
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings

from app.core.config import settings
from app.services.ai import AiService
from app.services.graph import GraphService
from app.core.constants import COMMAND_EXAMPLES
from app.services.database import DatabaseService
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

def is_valid_text_message(update: Update) -> bool:
    return bool(update.message and update.message.text and update.message.text.strip())


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_service = context.application.bot_data["db_service"]
    graph_service = context.application.bot_data["graph_service"]

    if not is_valid_text_message(update):
        return

    if update.message.reply_to_message:
        pending_commands = context.application.bot_data.get("pending_commands", {})
        replied_id = update.message.reply_to_message.message_id
        pending = pending_commands.get(replied_id)
        if pending and pending["user_id"] == update.message.from_user.id:
            command = pending["command"]
            text_after_command = update.message.text.strip()
            ai_service = context.application.bot_data["ai_service"]
            response = await ai_service.run(command, text_after_command, update.message.from_user.id)
            await update.message.reply_text(
                response.answer,
                reply_to_message_id=update.message.message_id
            )
            await db_service.save_command(update.message, response, command)
            del pending_commands[replied_id]
            return

    await db_service.save_message(update.message)
    if update.message.chat.type == "supergroup":
        await graph_service.save_episode(update.message)

async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ai_service = context.application.bot_data["ai_service"]
    db_service = context.application.bot_data["db_service"]

    if not is_valid_text_message(update):
        return

    command = update.message.text.split()[0][1:] if update.message and update.message.text else None
    message_text = update.message.text if update.message and update.message.text else ""
    text_after_command = message_text[len(command) + 2:].strip() if command else ""

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

    await update.message.reply_text(
        response.answer,
        reply_to_message_id=update.message.message_id
    )

    await db_service.save_command(update.message, response, command)

@asynccontextmanager
async def lifespan(app: FastAPI):
    llm = AzureChatOpenAI(
        api_version="2024-12-01-preview",
        azure_deployment=settings.MODEL,
    )

    embeddings = AzureOpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        openai_api_version="2024-12-01-preview",
    )

    store = InMemoryStore(
        index={
            "dims": 1536,
            "embed": f"azure_openai:{settings.EMBEDDING_MODEL}",
        }
    )

    checkpointer = MemorySaver()

    ai_service = AiService()
    db_service = DatabaseService()
    graph_service = GraphService()

    ai_service.connect(llm, embeddings, store, checkpointer)
    db_service.connect()
    
    await graph_service.connect()

    app.state.ai_service = ai_service
    app.state.db_service = db_service
    app.state.graph_service = graph_service

    tg_app: Application = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    tg_app.bot_data["ai_service"] = ai_service
    tg_app.bot_data["db_service"] = db_service
    tg_app.bot_data["graph_service"] = graph_service

    tg_app.add_handler(CommandHandler("ask", handle_command))
    tg_app.add_handler(CommandHandler("help", handle_command))
    tg_app.add_handler(CommandHandler("connect", handle_command))

    message_handler = MessageHandler(
        filters.TEXT & (~filters.COMMAND) & (
            filters.ChatType.GROUP | filters.ChatType.SUPERGROUP | filters.ChatType.PRIVATE
        ),
        handle_message
    )
    
    tg_app.add_handler(message_handler)

    await tg_app.initialize()

    app.state.tg_app = tg_app
    logger.info("Application startup complete. Bot is initialized and ready for webhooks.")

    scheduler = BackgroundScheduler()
    scheduler.add_job(graph_service.build_communities, CronTrigger(hour=0, minute=0))
    scheduler.start()
    app.state.scheduler = scheduler

    try:
        yield
    finally:
        await graph_service.close()
        await app.state.tg_app.shutdown()
        logger.info("Shutting down Telegram...")
        scheduler.shutdown()
        logger.info("Shutting down APScheduler...")