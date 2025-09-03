import uuid
import logging

from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)

class AuthService:
    
    def __init__(self):
        self._pool: Optional[AsyncConnectionPool] = None
        # In-memory storage for OAuth tokens (use Redis in production)
        self._oauth_tokens: Dict[str, Dict[str, Any]] = {}
    
    def set_database_pool(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool
        logger.info("Database pool set for AuthService")
    
    async def require_api_key(
        self,
        cred: HTTPAuthorizationCredentials = Security(bearer_scheme),
    ) -> dict:
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
            raise
        except Exception as e:
            logger.error(f"Database error during API key validation: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error during authentication",
            )
    
    def generate_oauth_token(self, user_id: int, expires_minutes: int = 30) -> str:
        """Generate a unique OAuth token for a Telegram user"""
        oauth_token = str(uuid.uuid4())
        expiry = datetime.now() + timedelta(minutes=expires_minutes)
        
        self._oauth_tokens[oauth_token] = {
            'user_id': user_id,
            'created_at': datetime.now(),
            'expires_at': expiry,
            'used': False
        }
        
        logger.info(f"Generated OAuth token for user {user_id}")
        return oauth_token
    
    def get_oauth_token_data(self, oauth_token: str) -> Optional[Dict[str, Any]]:
        """Get OAuth token data if valid and not expired"""
        token_data = self._oauth_tokens.get(oauth_token)
        if not token_data:
            logger.warning(f"OAuth token not found: {oauth_token[:8]}...")
            return None
        
        if datetime.now() > token_data['expires_at']:
            logger.warning(f"OAuth token expired: {oauth_token[:8]}...")
            # Clean up expired token
            del self._oauth_tokens[oauth_token]
            return None
        
        return token_data
    
    def mark_oauth_token_used(self, oauth_token: str) -> bool:
        """Mark an OAuth token as used"""
        token_data = self._oauth_tokens.get(oauth_token)
        if token_data and not token_data['used']:
            token_data['used'] = True
            logger.info(f"OAuth token marked as used: {oauth_token[:8]}...")
            return True
        return False
    
    def cleanup_expired_tokens(self):
        """Remove expired OAuth tokens from memory"""
        now = datetime.now()
        expired_tokens = [
            token for token, data in self._oauth_tokens.items()
            if now > data['expires_at']
        ]
        
        for token in expired_tokens:
            del self._oauth_tokens[token]
        
        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired OAuth tokens")

auth_service = AuthService()