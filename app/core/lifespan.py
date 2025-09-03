
import asyncio
import logging

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
from telegram.error import (BadRequest, Forbidden, NetworkError, RetryAfter,
                            TelegramError)
from telegram.ext import (ApplicationBuilder, ChatMemberHandler,
                          CommandHandler, ContextTypes, MessageHandler,
                          filters)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.config import settings
from app.core.constants import COMMAND_EXAMPLES, INTRODUCTION
from app.services.ai import ai_service
from app.services.auth import auth_service
from app.services.graph import graph_service

logger = logging.getLogger(__name__)


def safe_user_log(user_id: int) -> str:
    if settings.APP_ENV == "dev":
        return str(user_id)
    return f"user_{str(user_id)[:4]}***"


def safe_message_log(message_text: str) -> str:
    if settings.APP_ENV == "dev":
        return message_text
    return f"[{len(message_text)} chars]"


def safe_update_log(update: Update) -> str:
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
    return bool(update.message and update.message.text and
                update.message.text.strip())


async def is_user_authorized(user_id: int,
                             context: ContextTypes.DEFAULT_TYPE) -> bool:
    logger.debug(f"Starting authorization check for user {user_id}")
    if not await is_user_in_allowed_groups(user_id, context):
        logger.debug(f"User {user_id} DENIED - not in allowed groups")
        return False

    if not await has_soulink_access(user_id, context):
        logger.debug(f"User {user_id} DENIED - failed soulink check")
        return False

    logger.debug(f"User {user_id} AUTHORIZED")
    return True


async def is_user_in_allowed_groups(user_id: int,
                                    context: ContextTypes.DEFAULT_TYPE) -> bool:
    logger.debug(f"Checking allowed groups for user {user_id}")
    allowed_groups = set()
    if settings.GROUP_ID:
        try:
            allowed_groups.add(str(int(settings.GROUP_ID)))
        except (ValueError, TypeError):
            logger.error(f"Invalid GROUP_ID format: {settings.GROUP_ID}")

    if settings.ALLOWED_GROUP_IDS:
        for gid in settings.ALLOWED_GROUP_IDS.split(","):
            if gid.strip():
                try:
                    allowed_groups.add(str(int(gid.strip())))
                except (ValueError, TypeError):
                    logger.error(
                        "Invalid group ID format in ALLOWED_GROUP_IDS: "
                        f"{gid}"
                    )

    for group_id in allowed_groups:
        try:
            member = await context.bot.get_chat_member(group_id, user_id)
            if member.status in ["member", "administrator", "creator"]:
                return True
        except (BadRequest, Forbidden, NetworkError, RetryAfter,
                TelegramError) as e:
            logger.warning(
                f"Could not check membership for user {user_id} in "
                f"group {group_id}: {e}"
            )
            continue
    return False


async def get_user_groups(user_id: int,
                          context: ContextTypes.DEFAULT_TYPE) -> set:
    user_groups = set()
    known_groups = set()

    if settings.GROUP_ID:
        try:
            known_groups.add(str(int(settings.GROUP_ID)))
        except (ValueError, TypeError):
            logger.error(f"Invalid GROUP_ID format: {settings.GROUP_ID}")

    if settings.ALLOWED_GROUP_IDS:
        for gid in settings.ALLOWED_GROUP_IDS.split(","):
            if gid.strip():
                try:
                    known_groups.add(str(int(gid.strip())))
                except (ValueError, TypeError):
                    logger.error(
                        "Invalid group ID format in ALLOWED_GROUP_IDS: "
                        f"{gid}"
                    )
    for group_id in known_groups:
        try:
            member = await context.bot.get_chat_member(group_id, user_id)
            if member.status in ["member", "administrator", "creator"]:
                user_groups.add(group_id)
        except (BadRequest, Forbidden, NetworkError, RetryAfter,
                TelegramError) as e:
            logger.warning(
                f"Could not check membership for user {user_id} in "
                f"group {group_id}: {e}"
            )
    return user_groups


async def has_soulink_access(user_id: int,
                             context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not settings.SOULINK_ENABLED:
        return True

    try:
        admin_id = int(settings.SOULINK_ADMIN_ID)
        if admin_id <= 0:
            raise ValueError("Admin ID must be positive")
    except (ValueError, TypeError, AttributeError):
        logger.error("Soulink is enabled but SOULINK_ADMIN_ID is invalid.")
        return False

    user_groups = await get_user_groups(user_id, context)
    admin_groups = await get_user_groups(admin_id, context)
    return bool(user_groups.intersection(admin_groups))


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
        CommandHandler(["ask", "connect", "request"], handle_command))
    application.add_handler(
        ChatMemberHandler(handle_my_chat_member,
                          ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(
        MessageHandler(
            filters.TEXT & (~filters.COMMAND) &
            (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP
             | filters.ChatType.PRIVATE), handle_message))

    return application


async def handle_my_chat_member(update: Update,
                                context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    chat_id = str(result.chat.id)
    allowed_groups = {settings.GROUP_ID}
    if settings.ALLOWED_GROUP_IDS:
        allowed_groups.update(
            gid.strip() for gid in settings.ALLOWED_GROUP_IDS.split(",")
            if gid.strip())

    if result.new_chat_member.status in ["member", "administrator"]:
        if chat_id not in allowed_groups:
            logger.warning(
                f"Bot added to unauthorized group {chat_id}. Leaving.")
            try:
                await context.bot.leave_chat(chat_id)
            except TelegramError as e:
                logger.error(f"Failed to leave unauthorized group {chat_id}: {e}")
        else:
            logger.info(f"Bot added to authorized group {chat_id}")


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_authorized(update.message.from_user.id, context):
        logger.info("Ignoring /start from unauthorized user "
                    f"{safe_user_log(update.message.from_user.id)}")
        return
    await update.message.reply_text(INTRODUCTION)


async def handle_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /login command to initiate OAuth flow"""
    user_id = update.message.from_user.id
    
    # Check if OAuth is configured
    if not settings.OAUTH_BASE_URL or not settings.OAUTH_CLIENT_ID:
        await update.message.reply_text(
            "OAuth is not configured on this bot. Please contact the administrator."
        )
        return
    
    # Check if user is authorized to use the bot
    if not await is_user_authorized(user_id, context):
        logger.info(f"Ignoring /login from unauthorized user {safe_user_log(user_id)}")
        return
    
    try:
        # Generate OAuth token
        oauth_token = auth_service.generate_oauth_token(user_id, expires_minutes=30)
        
        # Build OAuth URL
        oauth_url = (
            f"{settings.OAUTH_BASE_URL}/o/authorize/?response_type=code&"
            f"client_id={settings.OAUTH_CLIENT_ID}&"
            f"redirect_uri={settings.WEBHOOK_URL}&"
            f"scope=read"
        )
        
        # Create inline keyboard
        keyboard = [[InlineKeyboardButton("🔗 Authorize with OAuth", url=oauth_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔐 <b>OAuth Authorization</b>\n\n"
            "Click the button below to authorize your account with OAuth.\n"
            "This will allow you to access additional features.\n\n"
            "<i>⏰ This link will expire in 30 minutes.</i>",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
        
        logger.info(f"OAuth flow initiated for user {safe_user_log(user_id)}")
        
    except Exception as e:
        logger.error(f"Failed to generate OAuth flow for user {safe_user_log(user_id)}: {e}")
        await update.message.reply_text(
            "❌ Sorry, there was an error generating the authorization link. "
            "Please try again later."
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_valid_text_message(update):
        return

    if update.message.chat.type == "private":
        user_id = update.message.from_user.id
        if not await is_user_authorized(user_id, context):
            logger.info("Ignoring private message from unauthorized user "
                        f"{safe_user_log(user_id)}")
            return

        if not await graph_service.check_user_exists(update.message):
            await update.message.reply_text(
                "Sorry, you're not a member of the Frontier Tower. "
                "Please <a href='https://frontiertower.io'>join the "
                "community</a> to get access.",
                parse_mode="HTML")
            return

        try:
            response = await ai_service.agent(update.message.text, user_id)
            await update.message.reply_text(
                response, reply_to_message_id=update.message.message_id)
        except Exception as e:
            logger.error(f"Failed to process direct message for user "
                         f"{safe_user_log(user_id)}: {e}")
            await update.message.reply_text(
                "Sorry, I encountered an error. Please try again later.")
            raise
    elif update.message.chat.type == "supergroup":
        await graph_service.add_episode(update.message)


async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_valid_text_message(update):
        return

    user_id = update.message.from_user.id
    if not await is_user_authorized(user_id, context):
        logger.info(f"Ignoring command from unauthorized user "
                    f"{safe_user_log(user_id)}")
        return

    full_command = update.message.text.split()[0][1:]
    command = full_command.split('@')[0]
    text_after_command = update.message.text[len(full_command) + 2:].strip()

    if not await graph_service.check_user_exists(update.message):
        await update.message.reply_text(
            "Sorry, you're not a member of the Frontier Tower. "
            "Please <a href='https://frontiertower.io'>join the community</a> "
            "to get access.",
            parse_mode="HTML")
        return

    if not text_after_command:
        example = COMMAND_EXAMPLES.get(command, "what's the wifi password?")
        await update.message.reply_text(
            f"Please add some context. <b>Example:</b> /{command} {example}",
            parse_mode="HTML")
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
                response, reply_to_message_id=update.message.message_id)
    except Exception as e:
        logger.error(
            f"Failed to process command '{command}' from user "
            f"{safe_user_log(user_id)}: {e}"
        )
        await update.message.reply_text(
            "Sorry, I encountered an error processing your command.")
        raise


async def initialize_services(app: FastAPI):
    global pool, store, checkpointer
    logger.info("Background service initialization started...")
    try:
        logger.info("Initializing LLM...")
        if settings.OPENAI_API_KEY:
            llm = ChatOpenAI(model=settings.MODEL)
        else:
            llm = AzureChatOpenAI(api_version=settings.AZURE_OPENAI_API_VERSION,
                                  azure_deployment=settings.MODEL)

        if settings.POSTGRES_CONN_STRING:
            logger.info("Opening Postgres connection pool...")
            pool = AsyncConnectionPool(conninfo=settings.POSTGRES_CONN_STRING,
                                     max_size=20,
                                     open=False,
                                     kwargs=connection_kwargs)
            await pool.open()
            auth_service.set_database_pool(pool)

            logger.info("Setting up store and checkpointer...")
            if settings.OPENAI_API_KEY:
                embed_config = f"openai:{settings.EMBEDDING_MODEL}"
            else:
                embed_config = f"azure_openai:{settings.EMBEDDING_MODEL}"
                
            store = AsyncPostgresStore(
                pool,
                index={
                    "dims": 1536,
                    "embed": embed_config
                },
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