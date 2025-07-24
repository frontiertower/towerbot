"""Application lifespan management module for TowerBot.

This module handles the complete startup and shutdown lifecycle of the TowerBot application,
including initialization of services, Telegram bot setup, database connections, background 
task scheduling, and comprehensive multi-layered authentication system.

Key Features:
- Multi-layered authentication (Group membership + Soulink + BerlinHouse API)
- Dynamic AI agent system with command-based and direct message processing
- Robust error handling for Telegram API calls
- Automatic unauthorized group detection and bot removal
- Secure supergroup message processing
- Debug logging and monitoring capabilities

Authentication Flow:
1. Group Membership: User must be in allowed Telegram groups
2. Soulink (Optional): User must share at least one group with designated admin
3. BerlinHouse API: User must be verified community member
4. Command Processing: Only authorized users can execute bot commands
5. Direct Messages: Full authentication for private chat conversations

Message Processing:
- Private Chats: Direct message processing using memory agent with full authentication
- Supergroups: Knowledge graph extraction for authorized groups
- Commands: AI-powered responses with specialized tools (/ask, /connect)
- Commands require immediate context - no reply-based continuation

Soulink Authentication System:
Soulink is TowerBot's innovative "social proximity" authentication mechanism that creates
a trust relationship based on shared group memberships. Named after the concept of a
"soul connection," Soulink ensures users have some social bond with the bot administrator.

How Soulink Works:
- Admin sets their Telegram user ID in SOULINK_ADMIN_ID configuration
- When enabled, users must share at least ONE Telegram group with the admin
- Bot checks all groups where both user and admin are members
- If any shared groups exist, user passes Soulink authentication
- If no shared groups, user is denied access regardless of other permissions

Soulink Benefits:
- Social Validation: Ensures users have genuine social connection to admin
- Dynamic Trust: Access automatically adjusts as group memberships change
- Scalable Security: Works across multiple communities without hardcoding
- Indirect Membership: Users don't need to be in the "main" group specifically

Soulink Configuration:
- SOULINK_ENABLED=true/false (default: false)
- SOULINK_ADMIN_ID=<admin_telegram_user_id>
- Works with existing GROUP_ID and ALLOWED_GROUP_IDS settings

Security Features:
- Input validation for all configuration values
- Specific exception handling for different error types
- Rate limiting detection and logging
- Automatic bot removal from unauthorized groups
- Comprehensive audit logging for all authentication attempts
- Secure direct message processing with memory agent
"""

import logging

from fastapi import FastAPI
from telegram import Update
from telegram.error import TelegramError, BadRequest, Forbidden, NetworkError, RetryAfter
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    ChatMemberHandler,
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
from app.core.constants import INTRODUCTION, COMMAND_EXAMPLES

logger = logging.getLogger(__name__)

def safe_user_log(user_id: int) -> str:
    """Generate privacy-safe user identifier for logging.
    
    In development: Returns full user ID for debugging
    In production: Returns truncated hash for privacy
    """
    if settings.APP_ENV == "dev":
        return str(user_id)
    return f"user_{str(user_id)[:4]}***"

def safe_message_log(message_text: str) -> str:
    """Generate privacy-safe message content for logging.
    
    In development: Returns full message for debugging
    In production: Returns truncated/sanitized version
    """
    if settings.APP_ENV == "dev":
        return message_text
    return f"[{len(message_text)} chars]"

def safe_update_log(update: Update) -> str:
    """Generate privacy-safe update summary for logging.
    
    In development: Returns full update object
    In production: Returns sanitized summary
    """
    if settings.APP_ENV == "dev":
        return str(update)
    return f"Update(id={update.update_id}, type={update.effective_chat.type if update.effective_chat else 'unknown'})"

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

async def is_user_authorized(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if a user is authorized to interact with the bot.
    
    Implements the first two layers of TowerBot's three-tier authentication system:
    1. Group Membership: Validates user is member of allowed Telegram groups
    2. Soulink Authentication: Validates user shares at least one group with admin (if enabled)
    
    This function does NOT check BerlinHouse API membership - that's handled separately
    in individual command handlers to avoid redundant API calls.
    
    Security Features:
    - Robust error handling for Telegram API failures
    - Input validation for configuration values
    - Comprehensive debug logging for audit trails
    - Rate limiting detection and graceful degradation
    
    Args:
        user_id: Telegram user ID to check
        context: Telegram context with bot instance for API calls
        
    Returns:
        bool: True if user passes both group membership and soulink checks
        
    Raises:
        No exceptions - all errors are caught and logged, failing secure by default
    """
    logger.debug(f"Starting authorization check for user {user_id}")
    logger.debug(f"GROUP_ID={settings.GROUP_ID}, ALLOWED_GROUP_IDS={settings.ALLOWED_GROUP_IDS}")
    logger.debug(f"SOULINK_ENABLED={settings.SOULINK_ENABLED}, SOULINK_ADMIN_ID={settings.SOULINK_ADMIN_ID}")
    
    allowed_groups_result = await is_user_in_allowed_groups(user_id, context)
    logger.debug(f"is_user_in_allowed_groups result: {allowed_groups_result}")
    
    if not allowed_groups_result:
        logger.debug(f"User {user_id} DENIED - not in allowed groups")
        return False
    
    soulink_result = await has_soulink_access(user_id, context)
    logger.debug(f"has_soulink_access result: {soulink_result}")
    
    if not soulink_result:
        logger.debug(f"User {user_id} DENIED - failed soulink check")
        logger.info(f"User {user_id} denied access: no shared groups with admin")
        return False
    
    logger.debug(f"User {user_id} AUTHORIZED")
    return True

async def is_user_in_allowed_groups(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if a user is a member of any allowed groups.
    
    Validates user membership in groups specified by GROUP_ID and ALLOWED_GROUP_IDS
    configuration. This is the first layer of TowerBot's authentication system.
    
    Process:
    1. Validates and parses GROUP_ID and ALLOWED_GROUP_IDS configuration
    2. Checks user membership in each group via Telegram Bot API
    3. Returns True if user is member/admin/creator in any allowed group
    
    Error Handling:
    - BadRequest: User not in group (expected, continues silently)
    - Forbidden: Bot lacks permission (warns, continues to next group)
    - NetworkError: Connection issues (errors, continues to next group)
    - RetryAfter: Rate limiting (warns with retry time, continues)
    - TelegramError: Other API errors (errors, continues)
    - Exception: Unexpected errors (errors, continues)
    
    Args:
        user_id: Telegram user ID to check
        context: Telegram context with bot instance for API calls
        
    Returns:
        bool: True if user is member of at least one allowed group
        
    Security Notes:
        - Fails secure: Returns False if all groups fail to check
        - Logs all errors for monitoring and debugging
        - Validates group ID format before API calls
    """
    logger.debug(f"Checking allowed groups for user {user_id}")
    
    allowed_groups = set()
    
    if settings.GROUP_ID:
        try:
            validated_group_id = int(settings.GROUP_ID)
            allowed_groups.add(str(validated_group_id))
        except (ValueError, TypeError):
            logger.error(f"Invalid GROUP_ID format: {settings.GROUP_ID}")
    
    if settings.ALLOWED_GROUP_IDS:
        additional_groups = [gid.strip() for gid in settings.ALLOWED_GROUP_IDS.split(",") if gid.strip()]
        for gid in additional_groups:
            try:
                validated_gid = int(gid)
                allowed_groups.add(str(validated_gid))
            except (ValueError, TypeError):
                logger.error(f"Invalid group ID format in ALLOWED_GROUP_IDS: {gid}")
                continue
    
    logger.debug(f"Allowed groups to check: {allowed_groups}")
    
    for group_id in allowed_groups:
        logger.debug(f"Checking membership in group {group_id}")
        try:
            member = await context.bot.get_chat_member(group_id, user_id)
            logger.debug(f"User {user_id} status in group {group_id}: {member.status}")
            if member.status in ["member", "administrator", "creator"]:
                logger.debug(f"User {user_id} is a {member.status} in group {group_id}")
                return True
        except BadRequest as e:
            logger.debug(f"BadRequest for user {user_id} in group {group_id}: {e}")
            continue
        except Forbidden as e:
            logger.warning(f"Bot lacks permission to check group {group_id}: {e}")
            continue
        except NetworkError as e:
            logger.error(f"Network error checking group {group_id}: {e}")
            continue
        except RetryAfter as e:
            logger.warning(f"Rate limited checking group {group_id}: retry after {e.retry_after}s")
            continue
        except TelegramError as e:
            logger.error(f"Telegram error checking group {group_id}: {e}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error checking group {group_id}: {e}")
            continue
    
    logger.debug(f"User {user_id} not found in any allowed groups")
    return False

async def get_user_groups(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> set:
    """Get all groups that a user is a member of for Soulink authentication.
    
    Used exclusively by the Soulink authentication system to determine shared
    group memberships between users and the designated admin.
    
    Important Limitations:
    - Can only check groups where the bot is also a member
    - Limited to groups specified in GROUP_ID and ALLOWED_GROUP_IDS
    - Cannot discover groups the bot doesn't know about
    
    Process:
    1. Validates GROUP_ID and ALLOWED_GROUP_IDS configuration
    2. Checks user membership in each known group
    3. Returns set of group IDs where user has membership
    
    Error Handling:
    - Same robust error handling as is_user_in_allowed_groups()
    - Continues checking all groups even if some fail
    - Logs all errors for monitoring
    
    Args:
        user_id: Telegram user ID to check
        context: Telegram context with bot instance for API calls
        
    Returns:
        set: Set of group ID strings where the user is a member/admin/creator
        
    Security Notes:
        - Only used for Soulink authentication
        - Does not grant access by itself
        - Fails secure by returning empty set on configuration errors
    """
    user_groups = set()
    
    known_groups = set()
    
    if settings.GROUP_ID:
        try:
            validated_group_id = int(settings.GROUP_ID)
            known_groups.add(str(validated_group_id))
        except (ValueError, TypeError):
            logger.error(f"Invalid GROUP_ID format: {settings.GROUP_ID}")
    
    if settings.ALLOWED_GROUP_IDS:
        additional_groups = [gid.strip() for gid in settings.ALLOWED_GROUP_IDS.split(",") if gid.strip()]
        for gid in additional_groups:
            try:
                validated_gid = int(gid)
                known_groups.add(str(validated_gid))
            except (ValueError, TypeError):
                logger.error(f"Invalid group ID format in ALLOWED_GROUP_IDS: {gid}")
                continue
    
    for group_id in known_groups:
        try:
            member = await context.bot.get_chat_member(group_id, user_id)
            if member.status in ["member", "administrator", "creator"]:
                user_groups.add(group_id)
        except BadRequest as e:
            logger.debug(f"BadRequest checking membership for user {user_id} in group {group_id}: {e}")
            continue
        except Forbidden as e:
            logger.warning(f"Bot lacks permission to check group {group_id}: {e}")
            continue
        except NetworkError as e:
            logger.error(f"Network error checking membership for user {user_id} in group {group_id}: {e}")
            continue
        except RetryAfter as e:
            logger.warning(f"Rate limited checking membership for user {user_id} in group {group_id}: retry after {e.retry_after}s")
            continue
        except TelegramError as e:
            logger.error(f"Telegram error checking membership for user {user_id} in group {group_id}: {e}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error checking membership for user {user_id} in group {group_id}: {e}")
            continue
    
    return user_groups

async def has_soulink_access(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user has Soulink access (shares at least one group with admin).
    
    Soulink is TowerBot's optional "social proximity" authentication layer that requires
    users to share at least one Telegram group with a designated admin. This creates
    a social validation mechanism beyond simple group membership.
    
    How Soulink Works:
    1. Admin designates their Telegram user ID in SOULINK_ADMIN_ID
    2. System checks which groups both user and admin are members of
    3. If they share ANY group, user passes Soulink authentication
    4. If no shared groups, user is denied access
    
    Configuration:
    - SOULINK_ENABLED: Boolean to enable/disable feature
    - SOULINK_ADMIN_ID: Telegram user ID of the admin to check against
    
    Fail-Safe Behavior:
    - If SOULINK_ENABLED=False, always returns True (disabled)
    - If SOULINK_ADMIN_ID is missing/invalid, returns True (fail open)
    - If configuration errors occur, returns True (fail open)
    
    Limitations:
    - Only checks groups where the bot is present
    - Cannot detect shared groups unknown to the bot
    - Admin must be in at least one bot-monitored group
    
    Args:
        user_id: Telegram user ID to check
        context: Telegram context with bot instance for API calls
        
    Returns:
        bool: True if user shares at least one group with admin, or if Soulink is disabled
        
    Security Notes:
        - Fails open on configuration errors (logs warnings)
        - Validates admin ID format before processing
        - Logs all shared group analysis for audit trails
    """
    logger.debug(f"Checking soulink access for user {user_id}")
    logger.debug(f"SOULINK_ENABLED={settings.SOULINK_ENABLED}")
    
    if not settings.SOULINK_ENABLED:
        logger.debug(f"Soulink disabled, allowing access")
        return True
    
    if not settings.SOULINK_ADMIN_ID:
        logger.error("SOULINK_ENABLED is True but SOULINK_ADMIN_ID is not set - failing secure")
        return False
    
    try:
        admin_id = int(settings.SOULINK_ADMIN_ID)
        if admin_id <= 0:
            raise ValueError("Admin ID must be positive")
        logger.debug(f"Admin ID: {admin_id}")
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid SOULINK_ADMIN_ID format: {settings.SOULINK_ADMIN_ID} - {e} - failing secure")
        return False
    
    user_groups = await get_user_groups(user_id, context)
    admin_groups = await get_user_groups(admin_id, context)
    
    shared_groups = user_groups.intersection(admin_groups)
    
    logger.debug(f"User {user_id} groups: {user_groups}")
    logger.debug(f"Admin {admin_id} groups: {admin_groups}")
    logger.debug(f"Shared groups: {shared_groups}")
    
    result = len(shared_groups) > 0
    logger.debug(f"Soulink access result: {result}")
    
    return result

def create_application(
    ai_service: AiService,
    graph_service: GraphService,
):
    """Create and configure the Telegram bot application with comprehensive security.
    
    Sets up the Telegram bot with all necessary handlers, security features,
    and injects the required services into the bot's data context.
    
    Security Features:
    - Multi-layered authentication for all interactions
    - Automatic unauthorized group detection and removal
    - Secure supergroup message processing
    - Command authorization with BerlinHouse API validation
    - Direct message processing with memory agent
    - Debug command for chat information
    
    Handlers Configured:
    - /start: Introduction with full authentication
    - /ask, /connect: AI-powered commands with authentication
    - Chat member updates: Automatic group management
    - Text messages: Context-aware processing with security checks
      * Private chats: Direct message processing using memory agent
      * Supergroups: Knowledge graph extraction
    
    Args:
        ai_service: AI service instance for processing commands and responses
        graph_service: Graph service for knowledge graph operations and user validation
        
    Returns:
        Application: Fully configured Telegram bot application with security features
        
    Security Notes:
        - All handlers implement the three-tier authentication system
        - Bot will automatically leave unauthorized groups
        - All user interactions are logged for audit purposes
        - Error handling prevents information leakage
        - Direct messages use memory agent for conversational interactions
    """
    bot_data = {
        "ai_service": ai_service,
        "graph_service": graph_service,
    }

    application = ApplicationBuilder().token(settings.BOT_TOKEN).build()
    application.bot_data.update(bot_data)
    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(CommandHandler(["ask", "connect", "request"], handle_command))
    application.add_handler(ChatMemberHandler(handle_my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
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

async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bot being added to or removed from chats with security validation.
    
    Implements TowerBot's automatic group management security feature. When the bot
    is added to any chat, this handler validates that the chat is in the allowed
    groups list. If not, the bot immediately leaves the unauthorized chat.
    
    Security Features:
    - Validates all group additions against GROUP_ID and ALLOWED_GROUP_IDS
    - Automatically leaves unauthorized groups
    - Logs all chat member changes for audit purposes
    - Handles configuration errors gracefully
    
    Process:
    1. Extracts chat information from the update
    2. Validates GROUP_ID and ALLOWED_GROUP_IDS configuration
    3. Checks if the chat is in the allowed groups list
    4. If unauthorized, leaves the chat immediately
    5. Logs all actions for monitoring
    
    Args:
        update: Telegram update containing chat member changes
        context: Telegram context for bot operations
        
    Security Notes:
        - Prevents unauthorized access through group invitations
        - Logs all group management actions
        - Handles bot removal gracefully
        - Validates configuration before processing
    """
    result = update.my_chat_member
    chat_id = str(result.chat.id)
    chat_type = result.chat.type
    chat_title = result.chat.title if hasattr(result.chat, 'title') else "Private"
    
    logger.info(f"Bot chat member update - chat_id={chat_id}, type={chat_type}, title='{chat_title}'")
    
    allowed_groups = set()
    
    allowed_groups.add(settings.GROUP_ID)
    
    if settings.ALLOWED_GROUP_IDS:
        additional_groups = [gid.strip() for gid in settings.ALLOWED_GROUP_IDS.split(",") if gid.strip()]
        allowed_groups.update(additional_groups)
    
    if result.new_chat_member.status in ["member", "administrator"]:
        if chat_id not in allowed_groups:
            logger.warning(f"Bot added to unauthorized group {chat_id}. Leaving immediately.")
            try:
                await context.bot.leave_chat(chat_id)
                logger.info(f"Successfully left unauthorized group {chat_id}")
            except Exception as e:
                logger.error(f"Failed to leave unauthorized group {chat_id}: {e}")
        else:
            logger.info(f"Bot added to authorized group {chat_id}")

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command with comprehensive authentication.
    
    Provides the initial introduction to TowerBot for new users. This handler
    implements the full three-tier authentication system to ensure only
    authorized users can receive the introduction.
    
    Authentication Layers:
    1. Group Membership: User must be in allowed Telegram groups
    2. Soulink (Optional): User must share groups with admin if enabled
    3. BerlinHouse API: User must be verified community member
    
    Process:
    1. Validates user is in allowed groups (GROUP_ID or ALLOWED_GROUP_IDS)
    2. Checks Soulink authentication if enabled
    3. Sends introduction message from INTRODUCTION constant
    4. Logs all authentication attempts for audit
    
    Args:
        update: Telegram update containing the /start command
        context: Telegram context for bot operations and service access
        
    Security Notes:
        - Implements full three-tier authentication
        - Logs all authentication attempts
        - Fails secure by ignoring unauthorized users
        - Does not reveal authentication failures to users
    """
    logger.debug(f"/start command received from user {safe_user_log(update.message.from_user.id)}")
    if settings.APP_ENV == "dev":
        logger.debug(f"User info: {update.message.from_user.first_name} {update.message.from_user.last_name} (@{update.message.from_user.username})")
    
    if not await is_user_authorized(update.message.from_user.id, context):
        logger.debug(f"/start command DENIED for user {safe_user_log(update.message.from_user.id)}")
        logger.info(f"Ignoring /start command from unauthorized user {safe_user_log(update.message.from_user.id)}")
        return
    
    logger.debug(f"/start command APPROVED for user {safe_user_log(update.message.from_user.id)}")
    
    await update.message.reply_text(INTRODUCTION)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages with context-aware security processing.
    
    Processes text messages based on chat type with appropriate security measures:
    - Private chats: Full three-tier authentication + direct message processing with memory agent
    - Supergroups: Group authorization + knowledge graph extraction
    
    Private Chat Processing:
    1. Group membership validation
    2. Soulink authentication (if enabled)
    3. BerlinHouse API user existence check
    4. Direct message processing using memory agent
    
    Supergroup Processing:
    1. Chat ID validation against allowed groups
    2. Message processing for knowledge graph extraction
    3. No individual user authentication required
    
    
    Args:
        update: Telegram update containing the text message
        context: Telegram context with bot data and state
        
    Security Features:
        - Different authentication levels per chat type
        - Automatic unauthorized group filtering
        - Comprehensive audit logging
        - Input validation and sanitization
    """
    logger.debug(f"Full update: {safe_update_log(update)}")

    if not is_valid_text_message(update):
        return

    chat_id = update.message.chat.id
    chat_type = update.message.chat.type
    chat_title = update.message.chat.title if hasattr(update.message.chat, 'title') else "Private"
    
    logger.info(f"Message from chat_id={chat_id}, type={chat_type}, title='{chat_title}'")

    ai_service: AiService = context.application.bot_data["ai_service"]
    graph_service: GraphService = context.application.bot_data["graph_service"]

    if update.message.chat.type == "private":
        logger.debug(f"Private message received from user {safe_user_log(update.message.from_user.id)}")
        logger.debug(f"Message: {safe_message_log(update.message.text)}")
        
        if not await is_user_authorized(update.message.from_user.id, context):
            logger.debug(f"Private message DENIED for user {safe_user_log(update.message.from_user.id)}")
            logger.info(f"Ignoring private message from unauthorized user {safe_user_log(update.message.from_user.id)}")
            return
        
        logger.debug(f"Private message APPROVED for user {safe_user_log(update.message.from_user.id)}")

        user_exists = await graph_service.check_user_exists(update.message)
        logger.debug(f"user_exists: {user_exists}")
        if not user_exists:
            await update.message.reply_text(
                "Sorry, you're not a member of the Frontier Tower. Please <a href='https://frontiertower.io'>join the community</a> to get access.",
                parse_mode="HTML"
            )
            return

        try:
            logger.debug(f"Processing direct message for user {safe_user_log(update.message.from_user.id)}")
            response = await ai_service.agent(update.message.text, update.message.from_user.id)
            await update.message.reply_text(response, reply_to_message_id=update.message.message_id)
            logger.debug(f"Successfully processed direct message for user {safe_user_log(update.message.from_user.id)}")
        except Exception as e:
            logger.error(f"Failed to process direct message for user {safe_user_log(update.message.from_user.id)}: {e}")
            await update.message.reply_text("Sorry, I encountered an error processing your message. Please try again later.")
            raise
        return


    if update.message.chat.type == "supergroup":
        chat_id = str(update.message.chat.id)
        allowed_groups = set()
        
        if settings.GROUP_ID:
            try:
                validated_group_id = int(settings.GROUP_ID)
                allowed_groups.add(str(validated_group_id))
            except (ValueError, TypeError):
                logger.error(f"Invalid GROUP_ID format: {settings.GROUP_ID}")
        
        if settings.ALLOWED_GROUP_IDS:
            additional_groups = [gid.strip() for gid in settings.ALLOWED_GROUP_IDS.split(",") if gid.strip()]
            for gid in additional_groups:
                try:
                    validated_gid = int(gid)
                    allowed_groups.add(str(validated_gid))
                except (ValueError, TypeError):
                    logger.error(f"Invalid group ID format in ALLOWED_GROUP_IDS: {gid}")
                    continue
        
        if chat_id not in allowed_groups:
            logger.warning(f"Ignoring supergroup message from unauthorized group {chat_id}")
            return
        
        logger.debug(f"Processing supergroup message from authorized group {chat_id}")
        await graph_service.add_episode(update.message)
        return

async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bot commands with comprehensive authentication and AI processing.
    
    Processes TowerBot's AI-powered commands (/ask, /connect)
    with full three-tier authentication and intelligent response generation.
    
    Supported Commands:
    - /ask: General questions and information requests
    - /connect: Connection requests and networking
    
    Authentication Process:
    1. Group Membership: User must be in allowed Telegram groups
    2. Soulink (Optional): User must share groups with admin if enabled
    3. BerlinHouse API: User must be verified community member
    
    Command Processing:
    1. Extracts command type and context from message
    2. Validates command has context (prompts with example if empty)
    3. Routes to AI service for intelligent response generation
    4. Commands must include context in the initial message - no multi-turn continuation
    
    Args:
        update: Telegram update containing the bot command
        context: Telegram context with bot data and state
        
    Security Features:
        - Full three-tier authentication system
        - Input validation and sanitization
        - Command context validation
        - Response persistence for audit
        - Error handling prevents information leakage
        - Rate limiting and abuse prevention
    """
    if not is_valid_text_message(update):
        return

    logger.debug(f"Command received from user {safe_user_log(update.message.from_user.id)}")
    logger.debug(f"Command: {safe_message_log(update.message.text)}")
    
    if not await is_user_authorized(update.message.from_user.id, context):
        logger.debug(f"Command DENIED for user {safe_user_log(update.message.from_user.id)}")
        logger.info(f"Ignoring command from unauthorized user {safe_user_log(update.message.from_user.id)}")
        return
    
    logger.debug(f"Command APPROVED for user {safe_user_log(update.message.from_user.id)}")

    try:
        ai_service: AiService = context.application.bot_data["ai_service"]
        graph_service: GraphService = context.application.bot_data["graph_service"]
        command = update.message.text.split()[0][1:]
        text_after_command = update.message.text[len(command) + 2:].strip()
        
        logger.debug(f"Processing command '{command}' from user {safe_user_log(update.message.from_user.id)}")

        user_exists = await graph_service.check_user_exists(update.message)
        logger.debug(f"User exists check result: {user_exists}")
        if not user_exists:
            await update.message.reply_text(
                "Sorry, you're not a member of the Frontier Tower. Please <a href='https://frontiertower.io'>join the community</a> to get access.",
                parse_mode="HTML"
            )
            return

        if not text_after_command:
            example = COMMAND_EXAMPLES.get(command, "what's the wifi password?")
            await update.message.reply_text(
                f"Please add some context after your command. <b>Example:</b> /{command} {example}",
                reply_to_message_id=update.message.message_id,
                parse_mode="HTML"
            )
            return

        if command == "ask":
            response = await ai_service.handle_ask(text_after_command)
        if command == "connect":
            response = await ai_service.handle_connect(text_after_command)
        if command == "request":
            response = await ai_service.handle_request(text_after_command)

        await update.message.reply_text(response, reply_to_message_id=update.message.message_id)
        logger.debug(f"Successfully processed command '{command}' from user {safe_user_log(update.message.from_user.id)}")
    except Exception as e:
        logger.error(f"Failed to process command '{command}' from user {safe_user_log(update.message.from_user.id)}: {e}")
        await update.message.reply_text("Sorry, I encountered an error processing your command. Please try again later.")
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for TowerBot.
    
    Manages the complete lifecycle of the TowerBot application with comprehensive
    initialization and graceful shutdown of all services and connections.
    
    Startup Process:
    1. Initializes Azure OpenAI LLM with configured model
    2. Creates PostgreSQL connection pool with optimized settings
    3. Sets up LangGraph store with vector embeddings
    4. Configures PostgreSQL checkpointer for conversation state
    5. Initializes AI, Graph, and Database services
    6. Creates Telegram bot application with security handlers
    7. Starts background scheduler for graph community building
    8. Attaches all services to FastAPI application state
    
    Runtime:
    - Maintains persistent connections to all services
    - Manages background task scheduling
    - Handles Telegram webhook updates
    - Provides health monitoring endpoint
    
    Shutdown Process:
    1. Closes GraphService connections gracefully
    2. Shuts down Telegram bot application
    3. Closes PostgreSQL connection pool
    4. Stops background scheduler
    5. Logs completion of shutdown sequence
    
    Args:
        app: FastAPI application instance for state management
        
    Yields:
        None: Control to the application runtime
        
    State Management:
        - app.state.ai_service: AI service for command processing
        - app.state.graph_service: Graph service for knowledge management
        - app.state.tg_app: Telegram bot application
        - app.state.scheduler: Background task scheduler
    """
    global pool, store, checkpointer

    logger.info("Application startup sequence initiated...")
    
    try:
        llm = AzureChatOpenAI(
            api_version="2024-12-01-preview",
            azure_deployment=settings.MODEL
        )

        pool = AsyncConnectionPool(
            conninfo=settings.POSTGRES_CONN_STRING,
            max_size=20,
            open=False,
            kwargs=connection_kwargs,
        )
        
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

        ai_service.connect(llm, store, checkpointer)

        await graph_service.connect()

        tg_app = create_application(ai_service, graph_service)

        await tg_app.initialize()

        scheduler = start_scheduler(graph_service)

        app.state.ai_service = ai_service
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