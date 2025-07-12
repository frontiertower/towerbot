from supabase import create_client, Client

from app.core.config import settings

def get_supabase_client():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

class DatabaseService:
    def __init__(self):
        self.supabase: Client | None = None

    def connect(self):
        self.supabase = get_supabase_client()