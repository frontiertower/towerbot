import json

from telegram import Message
from supabase import create_client, Client

from app.core.config import settings

def get_supabase_client():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

class DatabaseService:
    def __init__(self):
        self.supabase: Client | None = None

    def connect(self):
        self.supabase = get_supabase_client()

    async def save_message(self, message: Message):
        if self.supabase is None:
            self.connect()

        message_json_string = message.to_json()
        message_json = json.loads(message_json_string)

        self.supabase.table("messages").insert({
            "message": message_json,
        }).execute()

    async def save_command(self, message: Message, response: dict, command: str):
        if self.supabase is None:
            self.connect()

        message_json_string = message.to_json()
        message_json = json.loads(message_json_string)

        self.supabase.table("commands").insert({
            "category": command,
            "command": message_json,
            "response": response.model_dump(),
        }).execute()