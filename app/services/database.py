"""Database service module for TowerBot data persistence.

This module defines the DatabaseService class, which manages asynchronous
database operations for TowerBot using a PostgreSQL connection pool for optimal
performance and resource management. It provides methods for saving Telegram 
messages and tracking command executions with efficient connection pooling.
"""

import json
import logging

from telegram import Message
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)

class DatabaseService:
    """
    Service class for managing asynchronous database operations for TowerBot.

    This class provides asynchronous methods to interact with the PostgreSQL database,
    including saving Telegram messages and command execution records. It uses an
    AsyncConnectionPool for efficient, concurrent database access and optimal
    resource management.

    Attributes:
        pool (AsyncConnectionPool): The asynchronous connection pool for database operations.
    """
    def __init__(self, pool: AsyncConnectionPool):
        """
        Initialize the DatabaseService with an async connection pool.

        Args:
            pool (AsyncConnectionPool): The asynchronous connection pool to use for database operations.
        """
        self.pool: AsyncConnectionPool = pool

    async def save_message(self, message: Message):
        """
        Persist a Telegram message to the database using connection pooling.

        Args:
            message (Message): The Telegram message object to be saved.

        Raises:
            Exception: If an error occurs during the database operation.
        """
        try:
            message_json = json.loads(message.to_json())
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "INSERT INTO public.messages (message) VALUES (%s)",
                        (json.dumps(message_json),)
                    )
            logger.debug(f"Message {message.message_id} saved to database")
        except Exception as e:
            logger.error(f"Failed to save message {message.message_id}: {e}")
            raise

    async def save_command(self, message: Message, response: dict, command: str):
        """
        Save a command execution record to the database using connection pooling.

        Args:
            message (Message): The Telegram message object associated with the command.
            response (dict): The response object returned by the command execution.
            command (str): The command string that was executed.

        Raises:
            Exception: If an error occurs during the database operation.
        """
        try:
            message_json = json.loads(message.to_json())
            response_json = response.model_dump()
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "INSERT INTO public.commands (category, command, response) VALUES (%s, %s, %s)",
                        (command, json.dumps(message_json), json.dumps(response_json))
                    )
            logger.debug(f"Command '{command}' from message {message.message_id} saved to database")
        except Exception as e:
            logger.error(f"Failed to save command '{command}' from message {message.message_id}: {e}")
            raise