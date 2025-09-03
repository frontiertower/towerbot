import logging
from typing import Optional

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


class AuthService:
    def __init__(self):
        self._pool: Optional[AsyncConnectionPool] = None

    def set_database_pool(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool
        logger.info("Database pool set for AuthService")

    async def require_user_session(self, user_id: int) -> dict:
        """Check if user has a valid session in the sessions table"""
        if self._pool is None:
            logger.error("Database pool not available for authentication")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database connection not available",
            )

        try:
            async with self._pool.connection() as conn:
                conn.row_factory = dict_row
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        """
                        SELECT * FROM sessions 
                        WHERE user_id = %s 
                        AND (expires_at IS NULL OR expires_at > NOW())
                        ORDER BY created_at DESC 
                        LIMIT 1
                        """,
                        (user_id,)
                    )
                    session_row = await cursor.fetchone()

            if not session_row:
                logger.warning(f"No valid session for user {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No valid session found. Please authenticate first.",
                )

            logger.debug(f"Valid session found for user {user_id}")
            return session_row

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Database error during session validation: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error during authentication",
            )

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
                        (user_id,)
                    )
                    result = await cursor.fetchone()
                    return result is not None

        except Exception as e:
            logger.error(f"Database error checking user session: {e}")
            return False


auth_service = AuthService()
