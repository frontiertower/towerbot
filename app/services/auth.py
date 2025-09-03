import logging
from typing import Optional
import httpx

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


class AuthService:
    def __init__(self):
        self._pool: Optional[AsyncConnectionPool] = None

    def set_database_pool(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool
        logger.info("Database pool set for AuthService")

    async def check_user_has_session(self, user_id: int) -> bool:
        """Check if user has a valid session (returns True/False without raising exceptions)"""
        if self._pool is None:
            logger.error("Database pool not available")
            return False

        try:
            async with self._pool.connection() as conn:
                conn.row_factory = dict_row
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        """
                        SELECT 1 FROM sessions 
                        WHERE user_id = %s 
                        AND (expires_at IS NULL OR expires_at > NOW())
                        LIMIT 1
                        """,
                        (user_id,),
                    )
                    result = await cursor.fetchone()
                    return result is not None

        except Exception as e:
            logger.error(f"Database error checking user session: {e}")
            return False

    async def save_user_session(self, user_id: int, access_token: str) -> bool:
        """Save user session to the sessions table"""
        if self._pool is None:
            logger.error("Database pool not available")
            return False

        try:
            async with self._pool.connection() as conn:
                conn.row_factory = dict_row
                async with conn.cursor() as cursor:     
                    await cursor.execute(
                        """
                        INSERT INTO sessions (user_id, access_token)
                        VALUES (%s, %s)
                        ON CONFLICT (user_id) 
                        DO UPDATE SET 
                            access_token = EXCLUDED.access_token
                        """,
                        (user_id, access_token)
                    )
                    
            logger.info(f"Session saved for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Database error saving user session: {e}")
            return False

    async def get_user_info(self, access_token: str) -> dict:
        """Get user info from BerlinHouse API using access token"""
        headers = {'Authorization': f'Bearer {access_token}'}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{settings.BERLINHOUSE_BASE_URL}/auth/users/me/', headers=headers)
                return response.json()
        except Exception as e:
            logger.error(f"Error fetching user info: {e}")
            return {}


auth_service = AuthService()
