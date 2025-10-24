"""
Enhanced authentication middleware for JWT token management.

Provides JWT token extraction from Authorization header, user context injection
for protected routes, and comprehensive error handling for authentication failures.
"""

import logging
from typing import Optional, Dict, Any, Set
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..services.jwt_service import jwt_service

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT authentication and user context injection."""

    def __init__(self, app):
        super().__init__(app)
        self.public_paths = {
            "/",
            "/health",
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/auth/verify",
            "/api/v1/auth/refresh"
        }

    async def dispatch(self, request: Request, call_next):
        """Process request with authentication checks."""
        
        # Skip authentication for public endpoints
        if self._is_public_path(request.url.path):
            return await call_next(request)

        # Extract and validate JWT token
        try:
            token = self._extract_token(request)
            if token:
                user_context = await self._validate_and_inject_user_context(request, token)
                if user_context:
                    logger.debug(f"User context injected for user {user_context.get('email')}")
                else:
                    return self._create_auth_error_response("Invalid or expired token")
            else:
                return self._create_auth_error_response("Authentication required")

        except HTTPException as e:
            return self._create_auth_error_response(e.detail, e.status_code)
        except Exception as e:
            logger.error(f"Authentication middleware error: {str(e)}")
            return self._create_auth_error_response("Authentication failed")

        # Continue with request processing
        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        """Check if path is public and doesn't require authentication."""
        return path in self.public_paths or path.startswith("/static/")

    def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract JWT token from Authorization header.
        
        Args:
            request: FastAPI request object
            
        Returns:
            JWT token string if found, None otherwise
        """
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return None
        
        # Check for Bearer token format
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format. Expected 'Bearer <token>'"
            )
        
        # Extract token
        token = auth_header.split(" ", 1)[1] if len(auth_header.split(" ")) > 1 else None
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing token in authorization header"
            )
        
        return token

    async def _validate_and_inject_user_context(
        self, 
        request: Request, 
        token: str
    ) -> Optional[Dict[str, Any]]:
        """
        Validate JWT token and inject user context into request.
        
        Args:
            request: FastAPI request object
            token: JWT token to validate
            
        Returns:
            User context dict if valid, None if invalid
        """
        # Validate JWT token
        token_payload = jwt_service.validate_token(token)
        if not token_payload:
            return None

        # Extract user information from token
        user_id = token_payload.get('user_id')
        email = token_payload.get('email')
        
        if not user_id or not email:
            logger.warning("Token missing required user information")
            return None

        # Get additional user data from database
        try:
            # Lazy import to avoid circular dependency
            from ..services.dynamodb import db_service
            user_data = await db_service.get_user_by_id(user_id)
            if not user_data:
                logger.warning(f"User {user_id} not found in database")
                return None

            # Create comprehensive user context
            user_context = {
                'user_id': user_id,
                'email': email,
                'full_name': token_payload.get('full_name', user_data.get('full_name', '')),
                'is_active': user_data.get('is_active', True),
                'onboarding_completed': user_data.get('onboarding_completed', False),
                'preferences': user_data.get('preferences', {}),
                'token_payload': token_payload
            }

            # Inject user context into request state
            request.state.user = user_context
            request.state.user_id = user_id
            request.state.user_email = email
            request.state.authenticated = True

            return user_context

        except Exception as e:
            logger.error(f"Error fetching user data for {user_id}: {str(e)}")
            return None

    def _create_auth_error_response(
        self, 
        message: str, 
        status_code: int = status.HTTP_401_UNAUTHORIZED
    ) -> JSONResponse:
        """
        Create standardized authentication error response.
        
        Args:
            message: Error message
            status_code: HTTP status code
            
        Returns:
            JSONResponse with error details
        """
        error_response = {
            "detail": message,
            "error_code": "AUTHENTICATION_FAILED",
            "status_code": status_code,
            "type": "authentication_error"
        }

        return JSONResponse(
            status_code=status_code,
            content=error_response,
            headers={
                "WWW-Authenticate": "Bearer",
                "Content-Type": "application/json"
            }
        )


class EnhancedHTTPBearer(HTTPBearer):
    """Enhanced HTTP Bearer authentication with comprehensive error handling."""

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        """
        Extract and validate Bearer token from request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            HTTPAuthorizationCredentials if valid
            
        Raises:
            HTTPException: On authentication failure
        """
        try:
            credentials = await super().__call__(request)
            
            if not credentials:
                if self.auto_error:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication credentials required",
                        headers={"WWW-Authenticate": "Bearer"}
                    )
                return None

            # Validate token format
            if credentials.scheme.lower() != "bearer":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication scheme. Expected 'Bearer'",
                    headers={"WWW-Authenticate": "Bearer"}
                )

            # Validate JWT token
            token_payload = jwt_service.validate_token(credentials.credentials)
            if not token_payload:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"}
                )

            # Inject user context into request
            request.state.user_id = token_payload.get('user_id')
            request.state.user_email = token_payload.get('email')
            request.state.token_payload = token_payload
            request.state.authenticated = True

            return credentials

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Bearer token validation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Bearer"}
            )


async def simple_require_auth(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> Dict[str, Any]:
    """
    Simple authentication dependency that validates JWT token.
    
    Returns:
        User context from JWT token
        
    Raises:
        HTTPException: On authentication failure
    """
    from ..services.jwt_service import jwt_service
    
    token = credentials.credentials
    payload = jwt_service.validate_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        'user_id': payload.get('user_id'),
        'email': payload.get('email'),
        'full_name': payload.get('full_name', '')
    }


# Global instances for dependency injection
require_auth = simple_require_auth
enhanced_bearer = EnhancedHTTPBearer()