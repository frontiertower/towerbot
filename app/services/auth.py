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

    def set_database_pool(self, pool: AsyncConnectionPool):
        self._pool = pool
        logger.info("Database pool set for AuthService")

    async def store_pkce_verifier(self, telegram_id: int, code_verifier: str) -> bool:
        """
        Store the PKCE code_verifier for the user's session.

        Args:
            telegram_id (int): The Telegram user ID.
            code_verifier (str): The PKCE code_verifier to store.

        Returns:
            bool: True if stored successfully, False otherwise.
        """
        if self._pool is None:
            logger.error("Database pool not set in AuthService")
            return False
        try:
            async with self._pool.connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        """
                        INSERT INTO sessions (telegram_id, code_verifier)
                        VALUES (%s, %s)
                        ON CONFLICT (telegram_id)
                        DO UPDATE SET code_verifier = EXCLUDED.code_verifier
                        """,
                        (telegram_id, code_verifier),
                    )
            logger.info(f"Stored PKCE verifier for user {telegram_id}")
            return True
        except Exception as e:
            logger.error(
                f"Database error storing PKCE verifier for user {telegram_id}: {e}"
            )
            return False

    async def get_pkce_verifier(self, telegram_id: int) -> Optional[str]:
        """
        Non-destructively retrieves the PKCE verifier for the given Telegram user.

        Args:
            telegram_id (int): The Telegram user ID.

        Returns:
            Optional[str]: The PKCE code_verifier if found, otherwise None.
        """
        if self._pool is None:
            return None
        try:
            async with self._pool.connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "SELECT code_verifier FROM sessions WHERE telegram_id = %s;",
                        (telegram_id,),
                    )
                    result = await cursor.fetchone()
                    if result and result.get("code_verifier"):
                        return result["code_verifier"]
                    return None
        except Exception as e:
            logger.error(
                f"Failed to retrieve PKCE verifier for user {telegram_id}: {e}"
            )
            return None

    async def clear_pkce_verifier(self, telegram_id: int):
        """
        Clears the PKCE verifier after it has been used successfully.

        Args:
            telegram_id (int): The Telegram user ID.
        """
        try:
            async with self._pool.connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "UPDATE sessions SET code_verifier = NULL WHERE telegram_id = %s;",
                        (telegram_id,),
                    )
            logger.info(f"Successfully cleared PKCE verifier for {telegram_id}")
        except Exception as e:
            logger.error(f"Failed to clear PKCE verifier for {telegram_id}: {e}")

    async def check_user_has_session(self, user_id: int) -> bool:
        """
        Check if user has a valid session (returns True/False without raising exceptions).

        Args:
            user_id (int): The Telegram user ID.

        Returns:
            bool: True if the user has a valid session, False otherwise.
        """
        if self._pool is None:
            logger.error("Database pool not available")
            return False

        try:
            async with self._pool.connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        """
                        SELECT 1 FROM sessions
                        WHERE telegram_id = %s
                        AND access_token IS NOT NULL
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

    async def save_user_session(
        self, user_id: int, telegram_id: int, access_token: str
    ) -> bool:
        """
        Update an existing user session with the BerlinHouse user_id and token.

        Args:
            user_id (int): The BerlinHouse user ID.
            telegram_id (int): The Telegram user ID.
            access_token (str): The access token to store.

        Returns:
            bool: True if the session was updated successfully, False otherwise.
        """
        if self._pool is None:
            logger.error("Database pool not available")
            return False
        try:
            async with self._pool.connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        """
                        UPDATE sessions
                        SET user_id = %s, access_token = %s
                        WHERE telegram_id = %s
                        """,
                        (user_id, access_token, telegram_id),
                    )
            logger.info(
                f"Session updated for telegram_id {telegram_id} with user_id {user_id}"
            )
            return True
        except Exception as e:
            logger.error(f"Database error saving user session: {e}")
            return False

    async def get_user_info(self, access_token: str):
        """Get user info from BerlinHouse API using access token"""
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.BERLINHOUSE_BASE_URL}/auth/users/me/", headers=headers
                )
                return response.json()
        except Exception as e:
            logger.error(f"Error fetching user info: {e}")
            return {}


auth_service = AuthService()
