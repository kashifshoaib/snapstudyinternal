"""API dependencies for authentication and authorization."""

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from ..middleware.security import enhanced_bearer

logger = logging.getLogger(__name__)

# Enhanced security with JWT validation
security = enhanced_bearer


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Enhanced dependency to get current authenticated user with proper error handling."""
    from ..middleware.error_handler import AuthenticationError, ResourceNotFoundError
    from ..services.dynamodb import db_service

    if not credentials:
        raise AuthenticationError("Authentication required")

    try:
        # Get user ID from request state (set by enhanced_bearer)
        user_id = getattr(credentials, 'user_id', None)
        if hasattr(credentials, 'request') and hasattr(credentials.request.state, 'user_id'):
            user_id = credentials.request.state.user_id

        if not user_id:
            # Fallback to token parsing
            from ..middleware.security import jwt_validator
            payload = jwt_validator.verify_token(credentials.credentials)
            user_id = payload.get('user_id')

        if not user_id:
            raise AuthenticationError("Invalid token: user ID not found")

        # Get user from database
        user = await db_service.get_user_by_id(user_id)
        if not user:
            raise ResourceNotFoundError("User", user_id)

        return user

    except (AuthenticationError, ResourceNotFoundError):
        raise
    except Exception as e:
        logger.error(f"Error in get_current_user: {str(e)}")
        raise AuthenticationError(f"Authentication failed: {str(e)}")
