import os
import asyncio
import logging
import hashlib
import base64

from fastapi import FastAPI
from contextlib import asynccontextmanager
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.memory import InMemoryStore
from langgraph.store.postgres.aio import AsyncPostgresStore
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.config import settings
from app.core.constants import COMMAND_EXAMPLES, INTRODUCTION
from app.services.ai import ai_service
from app.services.auth import auth_service
from app.services.graph import graph_service

logger = logging.getLogger(__name__)


def safe_user_log(user_id: int):
    if settings.APP_ENV == "dev":
        return str(user_id)
    return f"user_{str(user_id)[:4]}***"


def safe_message_log(message_text: str):
    if settings.APP_ENV == "dev":
        return message_text
    return f"[{len(message_text)} chars]"


def safe_update_log(update: Update):
    if settings.APP_ENV == "dev":
        return str(update)
    return (
        f"Update(id={update.update_id}, "
        f"type={update.effective_chat.type if update.effective_chat else 'unknown'})"
    )


pool: AsyncConnectionPool | None = None
store: AsyncPostgresStore | InMemoryStore | None = None
checkpointer: AsyncPostgresSaver | MemorySaver | None = None

connection_kwargs = {
    "autocommit": True,
    "row_factory": dict_row,
    "prepare_threshold": None,
}


def is_valid_text_message(update: Update):
    return bool(update.message and update.message.text and update.message.text.strip())


def create_application():
    bot_data = {
        "ai_service": ai_service,
        "graph_service": graph_service,
    }
    application = ApplicationBuilder().token(settings.BOT_TOKEN).build()
    application.bot_data.update(bot_data)

    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(CommandHandler("login", handle_login))
    application.add_handler(
        CommandHandler(["ask", "connect", "request"], handle_command)
    )
    application.add_handler(
        ChatMemberHandler(handle_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER)
    )
    application.add_handler(
        MessageHandler(
            filters.TEXT
            & (~filters.COMMAND)
            & (
                filters.ChatType.GROUP
                | filters.ChatType.SUPERGROUP
                | filters.ChatType.PRIVATE
            ),
            handle_message,
        )
    )

    return application


async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    chat_id = str(result.chat.id)

    if result.new_chat_member.status in ["member", "administrator"]:
        logger.info(f"Bot added to group {chat_id}")


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if context.args:
        param = context.args[0]
        if param == "auth_success":
            await update.message.reply_text(
                "🎉 <b>Welcome back!</b>\n\n"
                "Your OAuth authorization was completed successfully. "
                "You can now use all bot features that require authentication.",
                parse_mode="HTML",
            )
            return

    if settings.OAUTH_CLIENT_ID and settings.OAUTH_CLIENT_SECRET:
        if not await auth_service.check_user_has_session(user_id):
            await handle_login(update, context)
            return

    await update.message.reply_text(INTRODUCTION)


async def handle_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /login command to initiate PKCE OAuth flow"""
    user_id = update.message.from_user.id

    if not settings.BERLINHOUSE_BASE_URL or not settings.OAUTH_CLIENT_ID:
        await update.message.reply_text("OAuth is not configured.")
        return

    try:
        # 1. Generate a secure random verifier
        code_verifier = (
            base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode("utf-8")
        )

        # 2. Store the verifier so the callback can use it later
        if not await auth_service.store_pkce_verifier(user_id, code_verifier):
            raise Exception("Failed to store PKCE verifier in the database.")

        # 3. Create the SHA256 challenge
        code_challenge = (
            base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode("utf-8")).digest()
            )
            .rstrip(b"=")
            .decode("utf-8")
        )

        # 4. Build the URL with the new PKCE parameters
        oauth_url = (
            f"{settings.BERLINHOUSE_BASE_URL}/o/authorize/?response_type=code&"
            f"client_id={settings.OAUTH_CLIENT_ID}&"
            f"redirect_uri={settings.WEBHOOK_URL}/auth/callback&"
            f"scope=read&"
            f"state={user_id}&"
            f"code_challenge={code_challenge}&"
            f"code_challenge_method=S256"  # Always S256 for this method
        )

        keyboard = [
            [InlineKeyboardButton("🏢 Sign in with Frontier Tower", url=oauth_url)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🔐 <b>Sign In Required</b>\n\n"
            "Click the button below to sign in with your Frontier Tower account.",
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
        logger.info(f"PKCE OAuth flow initiated for user {safe_user_log(user_id)}")

    except Exception as e:
        logger.error(
            f"Failed to generate OAuth flow for user {safe_user_log(user_id)}: {e}",
            exc_info=True,
        )
        await update.message.reply_text(
            "❌ Sorry, there was an error. Please try again later."
        )


async def handle_login_direct_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int
):
    """Handle login requirement by sending direct message to user"""
    if not settings.BERLINHOUSE_BASE_URL or not settings.OAUTH_CLIENT_ID:
        await context.bot.send_message(chat_id=user_id, text="OAuth is not configured.")
        return

    try:
        # 1. Generate a secure random verifier
        code_verifier = (
            base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode("utf-8")
        )

        # 2. Store the verifier so the callback can use it later
        if not await auth_service.store_pkce_verifier(user_id, code_verifier):
            raise Exception("Failed to store PKCE verifier in the database.")

        # 3. Create the SHA256 challenge
        code_challenge = (
            base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode("utf-8")).digest()
            )
            .rstrip(b"=")
            .decode("utf-8")
        )

        # 4. Build the URL with the new PKCE parameters
        oauth_url = (
            f"{settings.BERLINHOUSE_BASE_URL}/o/authorize/?response_type=code&"
            f"client_id={settings.OAUTH_CLIENT_ID}&"
            f"redirect_uri={settings.WEBHOOK_URL}/auth/callback&"
            f"scope=read&"
            f"state={user_id}&"
            f"code_challenge={code_challenge}&"
            f"code_challenge_method=S256"  # Always S256 for this method
        )

        keyboard = [
            [InlineKeyboardButton("🏢 Sign in with Frontier Tower", url=oauth_url)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text="🔐 <b>Sign In Required</b>\n\n"
            "Click the button below to sign in with your Frontier Tower account.",
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
        logger.info(
            f"PKCE OAuth flow initiated for user {safe_user_log(user_id)} via direct message"
        )

    except Exception as e:
        logger.error(
            f"Failed to generate OAuth flow for user {safe_user_log(user_id)}: {e}",
            exc_info=True,
        )
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Sorry, there was an error. Please try again later.",
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_valid_text_message(update):
        return

    if update.message.chat.type == "private":
        user_id = update.message.from_user.id

        if settings.OAUTH_CLIENT_ID and settings.OAUTH_CLIENT_SECRET:
            if not await auth_service.check_user_has_session(user_id):
                await handle_login(update, context)
                return

        if not await graph_service.check_user_exists(update.message):
            await update.message.reply_text(
                "Sorry, you're not a member of the Frontier Tower. "
                "Please <a href='https://frontiertower.io'>join the "
                "community</a> to get access.",
                parse_mode="HTML",
            )
            return

        try:
            response = await ai_service.agent(update.message.text, user_id)
            await update.message.reply_text(
                response, reply_to_message_id=update.message.message_id
            )
        except Exception as e:
            logger.error(
                f"Failed to process direct message for user "
                f"{safe_user_log(user_id)}: {e}"
            )
            await update.message.reply_text(
                "Sorry, I encountered an error. Please try again later."
            )
            raise
    elif update.message.chat.type == "supergroup":
        await graph_service.add_episode(update.message)


async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_valid_text_message(update):
        return

    user_id = update.message.from_user.id

    if settings.OAUTH_CLIENT_ID and settings.OAUTH_CLIENT_SECRET:
        if not await auth_service.check_user_has_session(user_id):
            await handle_login_direct_message(update, context, user_id)
            return

    full_command = update.message.text.split()[0][1:]
    command = full_command.split("@")[0]
    text_after_command = update.message.text[len(full_command) + 2 :].strip()

    if not await graph_service.check_user_exists(update.message):
        await update.message.reply_text(
            "Sorry, you're not a member of the Frontier Tower. "
            "Please <a href='https://frontiertower.io'>join the community</a> "
            "to get access.",
            parse_mode="HTML",
        )
        return

    if not text_after_command:
        example = COMMAND_EXAMPLES.get(command, "what's the wifi password?")
        await update.message.reply_text(
            f"Please add some context. <b>Example:</b> /{command} {example}",
            parse_mode="HTML",
        )
        return

    try:
        response = ""
        if command == "ask":
            response = await ai_service.handle_ask(text_after_command)
        elif command == "connect":
            response = await ai_service.handle_connect(text_after_command)
        elif command == "request":
            response = await ai_service.handle_request(text_after_command)

        if response:
            await update.message.reply_text(
                response, reply_to_message_id=update.message.message_id
            )
    except Exception as e:
        logger.error(
            f"Failed to process command '{command}' from user "
            f"{safe_user_log(user_id)}: {e}"
        )
        await update.message.reply_text(
            "Sorry, I encountered an error processing your command."
        )
        raise


async def initialize_services(app: FastAPI):
    global pool, store, checkpointer
    logger.info("Background service initialization started...")
    try:
        logger.info("Initializing LLM...")
        if settings.OPENAI_API_KEY:
            llm = ChatOpenAI(model=settings.MODEL)
        else:
            llm = AzureChatOpenAI(
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_deployment=settings.MODEL,
            )

        if settings.POSTGRES_CONN_STRING:
            logger.info("Opening Postgres connection pool...")
            pool = AsyncConnectionPool(
                conninfo=settings.POSTGRES_CONN_STRING,
                max_size=20,
                open=False,
                kwargs=connection_kwargs,
            )
            await pool.open()
            auth_service.set_database_pool(pool)

            logger.info("Setting up store and checkpointer...")
            if settings.OPENAI_API_KEY:
                embed_config = f"openai:{settings.EMBEDDING_MODEL}"
            else:
                embed_config = f"azure_openai:{settings.EMBEDDING_MODEL}"

            store = AsyncPostgresStore(
                pool,
                index={"dims": 1536, "embed": embed_config},
            )
            checkpointer = AsyncPostgresSaver(pool)

            logger.info("Setting up store...")
            await store.setup()
            logger.info("Setting up checkpointer...")
            await checkpointer.setup()
        else:
            logger.info("Using in-memory stores (no POSTGRES_CONN_STRING provided)...")
            store = InMemoryStore()
            checkpointer = MemorySaver()
        logger.info("Connecting AI service...")
        ai_service.connect(llm, store, checkpointer)
        logger.info("Connecting graph service...")
        await graph_service.connect()

        logger.info("Initializing Telegram app...")
        tg_app = create_application()
        await tg_app.initialize()

        logger.info("Setting app state...")
        app.state.ai_service = ai_service
        app.state.graph_service = graph_service
        app.state.auth_service = auth_service
        app.state.tg_app = tg_app
        logger.info("Background service initialization complete.")
    except Exception as e:
        logger.error(f"Background service initialization failed: {e}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup sequence initiated...")
    initialization_task = asyncio.create_task(initialize_services(app))

    try:
        yield
    finally:
        logger.info("Application shutdown sequence initiated...")
        if not initialization_task.done():
            initialization_task.cancel()
        try:
            if app.state.graph_service:
                await app.state.graph_service.close()
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
