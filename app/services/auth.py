"""Authentication service for TowerBot.

This service handles API key authentication for graph endpoints and provides
a centralized authentication layer for the application.
"""

import logging
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)

class AuthService:
    """Authentication service for API key validation and management.
    
    This service provides centralized authentication functionality for TowerBot,
    including API key validation against the PostgreSQL database.
    
    Features:
    - API key validation for graph endpoints
    - Database connection management
    - Secure token validation
    - Comprehensive error handling
    """
    
    def __init__(self):
        self._pool: Optional[AsyncConnectionPool] = None
    
    def set_database_pool(self, pool: AsyncConnectionPool) -> None:
        """Set the database pool for authentication operations.
        
        Args:
            pool: AsyncConnectionPool instance for database connections
        """
        self._pool = pool
        logger.info("Database pool set for AuthService")
    
    async def require_api_key(
        self,
        cred: HTTPAuthorizationCredentials = Security(bearer_scheme),
    ) -> dict:
        """
        Validates API key authentication for graph endpoints.
        
        This method extracts the bearer token from the Authorization header,
        validates it against the 'keys' table in the PostgreSQL database, and
        returns the key record if valid.
        
        Args:
            cred: HTTP authorization credentials containing the bearer token
            
        Returns:
            dict: The API key record from the database
            
        Raises:
            HTTPException: 
                - 401 if authorization header is missing or malformed
                - 403 if API key is invalid or not found in database
                - 500 if database connection is unavailable
                
        Example:
            Used as a FastAPI dependency:
            ```python
            @router.get("/endpoint", dependencies=[Depends(auth_service.require_api_key)])
            async def protected_endpoint():
                return {"message": "Access granted"}
            ```
        """
        if cred is None or cred.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = cred.credentials

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
                        "SELECT * FROM keys WHERE key = %s",
                        (token,)
                    )
                    key_row = await cursor.fetchone()
            
            if not key_row:
                logger.warning(f"Invalid API key attempted: {token[:8]}...")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid API key",
                )
            
            logger.debug(f"Valid API key used: {token[:8]}...")
            return key_row
            
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Database error during API key validation: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error during authentication",
            )

auth_service = AuthService() 