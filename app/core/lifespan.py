import logging

from typing import Dict

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
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings

from app.core.config import settings
from app.services.ai import AiService
from app.services.graph import GraphService
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

pending_commands: Dict[int, str] = {}

def is_valid_text_message(update: Update) -> bool:
    return bool(update.message and update.message.text and update.message.text.strip())


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ai_service = context.application.bot_data["ai_service"]
    graph_service = context.application.bot_data["graph_service"]

    if not is_valid_text_message(update):
        return

    if update.message.reply_to_message and update.message.reply_to_message.message_id in pending_commands:
        command = pending_commands.pop(update.message.reply_to_message.message_id)
        question = update.message.text
        response = await ai_service.agent(question, command)
        await update.message.reply_text(
            response.answer, reply_to_message_id=update.message.message_id
        )
        return

    if update.message.chat.type == "supergroup":
        await graph_service.save_episode(update.message)


async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ai_service = context.application.bot_data["ai_service"]

    if not is_valid_text_message(update):
        if update.message:
            sent = await update.message.reply_text("How can I help?", reply_to_message_id=update.message.message_id)
            command = update.message.text.split()[0][1:] if update.message and update.message.text else None
            if sent and hasattr(sent, 'message_id') and command:
                pending_commands[sent.message_id] = command
        return

    command = update.message.text.split()[0][1:] if update.message and update.message.text else None
    message_text = update.message.text if update.message and update.message.text else ""
    text_after_command = message_text[len(command) + 2:].strip() if command else ""

    if not text_after_command:
        sent = await update.message.reply_text("How can I help?", reply_to_message_id=update.message.message_id)
        if sent and hasattr(sent, 'message_id') and command:
            pending_commands[sent.message_id] = command
        return

    response = await ai_service.agent(text_after_command, command)

    await update.message.reply_text(
        response.answer, reply_to_message_id=update.message.message_id
    )


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

    ai_service = AiService()
    graph_service = GraphService()

    ai_service.connect(llm, embeddings)
    
    await graph_service.connect()

    app.state.ai_service = ai_service
    app.state.graph_service = graph_service

    tg_app: Application = ApplicationBuilder().token(settings.BOT_TOKEN).build()

    tg_app.bot_data["ai_service"] = ai_service
    tg_app.bot_data["graph_service"] = graph_service

    tg_app.add_handler(CommandHandler("ask", handle_command))
    tg_app.add_handler(CommandHandler("help", handle_command))
    tg_app.add_handler(CommandHandler("connect", handle_command))

    message_handler = MessageHandler(
        filters.TEXT
        & (~filters.COMMAND)
        & (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP | filters.ChatType.PRIVATE),
        handle_message,
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
        await app.state.tg_app.shutdown()
        logger.info("Shutting down Telegram...")
        scheduler.shutdown()
        logger.info("Shutting down APScheduler...")