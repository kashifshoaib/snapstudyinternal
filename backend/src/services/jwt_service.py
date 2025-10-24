"""
JWT token management service for authentication.

Provides JWT token generation, validation, decoding, and refresh mechanisms
with configurable expiration times.
"""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import logging
from fastapi import HTTPException, status

from ..config import settings

logger = logging.getLogger(__name__)


class JWTService:
    """Service for JWT token management."""

    def __init__(self):
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.expiration_hours = settings.jwt_expiration_hours

    def generate_token(self, user_data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Generate JWT access token for user.
        
        Args:
            user_data: User information to encode in token
            expires_delta: Optional custom expiration time
            
        Returns:
            JWT token string
        """
        # Set expiration time
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(hours=self.expiration_hours)
        
        # Prepare token payload (keep it simple and compatible)
        payload = {
            'user_id': user_data.get('user_id'),
            'email': user_data.get('email'),
            'full_name': user_data.get('full_name', ''),
            'onboarding_completed': user_data.get('onboarding_completed', False),
            'exp': expire,
            'iat': datetime.now(timezone.utc),
            'type': 'access'
        }
        
        # Generate token
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        logger.debug(f"JWT token generated for user {user_data.get('email')}")
        return token

    def generate_refresh_token(self, user_data: Dict[str, Any]) -> str:
        """
        Generate JWT refresh token for user.
        
        Args:
            user_data: User information to encode in token
            
        Returns:
            JWT refresh token string
        """
        # Refresh tokens have longer expiration (7 days)
        expire = datetime.now(timezone.utc) + timedelta(days=7)
        
        # Prepare refresh token payload (minimal data)
        payload = {
            'user_id': user_data.get('user_id'),
            'email': user_data.get('email'),
            'exp': expire,
            'iat': datetime.now(timezone.utc),
            'type': 'refresh'
        }
        
        # Generate refresh token
        refresh_token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        logger.debug(f"JWT refresh token generated for user {user_data.get('email')}")
        return refresh_token

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate and decode JWT token.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Decoded token payload if valid, None if invalid
        """
        try:
            # Decode and validate token (simple approach)
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": True}
            )
            
            # Verify token type
            if payload.get('type') != 'access':
                logger.warning("Invalid token type")
                return None
            
            logger.debug(f"JWT token validated for user {payload.get('email')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected JWT validation error: {str(e)}")
            return None

    def validate_refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Validate and decode JWT refresh token.
        
        Args:
            refresh_token: JWT refresh token to validate
            
        Returns:
            Decoded token payload if valid, None if invalid
        """
        try:
            # Decode and validate refresh token (simple approach)
            payload = jwt.decode(
                refresh_token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": True}
            )
            
            # Verify token type
            if payload.get('type') != 'refresh':
                logger.warning("Invalid refresh token type")
                return None
            
            logger.debug(f"JWT refresh token validated for user {payload.get('email')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT refresh token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT refresh token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected JWT refresh token validation error: {str(e)}")
            return None

    def refresh_access_token(self, refresh_token: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate new access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            user_data: Updated user data for new token
            
        Returns:
            Dict containing new access token and metadata
            
        Raises:
            HTTPException: If refresh token is invalid
        """
        # Validate refresh token
        refresh_payload = self.validate_refresh_token(refresh_token)
        if not refresh_payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        # Verify user matches
        if refresh_payload.get('user_id') != user_data.get('user_id'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token user mismatch"
            )
        
        # Generate new access token
        new_access_token = self.generate_token(user_data)
        
        logger.info(f"Access token refreshed for user {user_data.get('email')}")
        
        return {
            'access_token': new_access_token,
            'token_type': 'bearer',
            'expires_in': self.expiration_hours * 3600,  # Convert to seconds
            'refreshed_at': datetime.now(timezone.utc).isoformat()
        }

    def decode_token_without_verification(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode JWT token without signature verification (for debugging/inspection).
        
        Args:
            token: JWT token to decode
            
        Returns:
            Decoded payload if decodable, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False}
            )
            return payload
        except Exception as e:
            logger.error(f"Failed to decode token: {str(e)}")
            return None

    def get_token_expiration(self, token: str) -> Optional[datetime]:
        """
        Get expiration time from JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            Expiration datetime if valid, None otherwise
        """
        payload = self.decode_token_without_verification(token)
        if payload and 'exp' in payload:
            return datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
        return None

    def is_token_expired(self, token: str) -> bool:
        """
        Check if JWT token is expired.
        
        Args:
            token: JWT token to check
            
        Returns:
            True if expired, False if valid or unable to determine
        """
        expiration = self.get_token_expiration(token)
        if expiration:
            return datetime.now(timezone.utc) > expiration
        return True  # Assume expired if can't determine


# Global service instance
jwt_service = JWTService()