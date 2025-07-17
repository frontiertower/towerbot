"""Database service module for TowerBot data persistence.

This module provides the DatabaseService class for managing data storage
operations using Supabase, including message logging and command tracking.
"""

import json

from telegram import Message
from supabase import create_client, Client

from app.core.config import settings

def get_supabase_client():
    """Create and return a Supabase client instance.
    
    Returns:
        Client: Configured Supabase client for database operations
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

class DatabaseService:
    """Service class for managing database operations.
    
    This class handles all database-related operations including:
    - Connection management to Supabase
    - Message storage and logging
    - Command execution tracking
    
    Attributes:
        supabase: Supabase client instance for database operations
    """
    def __init__(self):
        """Initialize the DatabaseService with empty client reference."""
        self.supabase: Client | None = None

    def connect(self):
        """Initialize the Supabase client connection."""
        self.supabase = get_supabase_client()

    async def save_message(self, message: Message):
        """Save a Telegram message to the database.
        
        Stores the complete message object as JSON in the messages table.
        
        Args:
            message: Telegram message object to store
        """
        if self.supabase is None:
            self.connect()

        message_json_string = message.to_json()
        message_json = json.loads(message_json_string)

        self.supabase.table("messages").insert({
            "message": message_json,
        }).execute()

    async def save_command(self, message: Message, response: dict, command: str):
        """Save a command execution record to the database.
        
        Stores the command message, AI response, and command type
        in the commands table for tracking and analytics.
        
        Args:
            message: Original Telegram message containing the command
            response: AI agent response object
            command: Command type (e.g., 'ask', 'connect')
        """
        if self.supabase is None:
            self.connect()

        message_json_string = message.to_json()
        message_json = json.loads(message_json_string)

        self.supabase.table("commands").insert({
            "category": command,
            "command": message_json,
            "response": response.model_dump(),
        }).execute()