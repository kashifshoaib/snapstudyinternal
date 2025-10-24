"""
Security middleware for SnapStudy backend.

Provides JWT validation, security headers, rate limiting, and CORS protection.
"""

import logging
import time
import hashlib
from typing import Dict, Any, Optional, Set
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import jwt
from collections import defaultdict, deque

from ..config import settings
from ..middleware.error_handler import (
    AuthenticationError, 
    AuthorizationError, 
    RateLimitError,
    create_error_response
)

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    def __init__(self, app):
        super().__init__(app)
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https:; "
                "media-src 'self' https:; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            ),
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=(), "
                "speaker=()"
            )
        }
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        for header, value in self.security_headers.items():
            response.headers[header] = value
        
        # Add request ID to response
        if hasattr(request.state, 'request_id'):
            response.headers["X-Request-ID"] = request.state.request_id
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with sliding window algorithm."""
    
    def __init__(
        self, 
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_limit: int = 10
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit
        
        # Storage for rate limiting (in production, use Redis)
        self.minute_windows: Dict[str, deque] = defaultdict(deque)
        self.hour_windows: Dict[str, deque] = defaultdict(deque)
        self.burst_windows: Dict[str, deque] = defaultdict(deque)
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        
        # Try to get user ID from JWT token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                token = auth_header.split(" ")[1]
                payload = jwt.decode(
                    token, 
                    settings.jwt_secret_key, 
                    algorithms=[settings.jwt_algorithm]
                )
                user_id = payload.get("user_id")
                if user_id:
                    return f"user:{user_id}"
            except jwt.InvalidTokenError:
                pass
        
        # Fall back to IP address
        client_ip = request.client.host
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        return f"ip:{client_ip}"
    
    def _is_rate_limited(self, client_id: str, current_time: float) -> Optional[Dict[str, Any]]:
        """Check if client is rate limited."""
        
        # Clean old entries and check burst limit (last 10 seconds)
        burst_window = self.burst_windows[client_id]
        burst_cutoff = current_time - 10  # 10 seconds
        while burst_window and burst_window[0] < burst_cutoff:
            burst_window.popleft()
        
        if len(burst_window) >= self.burst_limit:
            return {
                "limit_type": "burst",
                "retry_after": 10,
                "limit": self.burst_limit,
                "window": "10 seconds"
            }
        
        # Clean old entries and check minute limit
        minute_window = self.minute_windows[client_id]
        minute_cutoff = current_time - 60  # 1 minute
        while minute_window and minute_window[0] < minute_cutoff:
            minute_window.popleft()
        
        if len(minute_window) >= self.requests_per_minute:
            return {
                "limit_type": "minute",
                "retry_after": 60,
                "limit": self.requests_per_minute,
                "window": "1 minute"
            }
        
        # Clean old entries and check hour limit
        hour_window = self.hour_windows[client_id]
        hour_cutoff = current_time - 3600  # 1 hour
        while hour_window and hour_window[0] < hour_cutoff:
            hour_window.popleft()
        
        if len(hour_window) >= self.requests_per_hour:
            return {
                "limit_type": "hour",
                "retry_after": 3600,
                "limit": self.requests_per_hour,
                "window": "1 hour"
            }
        
        return None
    
    def _record_request(self, client_id: str, current_time: float):
        """Record a request for rate limiting."""
        self.burst_windows[client_id].append(current_time)
        self.minute_windows[client_id].append(current_time)
        self.hour_windows[client_id].append(current_time)
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/", "/docs", "/redoc"]:
            return await call_next(request)
        
        client_id = self._get_client_id(request)
        current_time = time.time()
        
        # Check rate limits
        rate_limit_info = self._is_rate_limited(client_id, current_time)
        if rate_limit_info:
            logger.warning(
                f"Rate limit exceeded for {client_id}",
                extra={
                    "client_id": client_id,
                    "limit_type": rate_limit_info["limit_type"],
                    "path": request.url.path,
                    "method": request.method
                }
            )
            
            error_response = create_error_response(
                error_code="RATE_LIMIT_EXCEEDED",
                message=f"Rate limit exceeded: {rate_limit_info['limit']} requests per {rate_limit_info['window']}",
                status_code=429,
                details=rate_limit_info
            )
            
            return JSONResponse(
                status_code=429,
                content=error_response,
                headers={"Retry-After": str(rate_limit_info["retry_after"])}
            )
        
        # Record the request
        self._record_request(client_id, current_time)
        
        # Add rate limit headers to response
        response = await call_next(request)
        
        # Add rate limit info to headers
        minute_remaining = max(0, self.requests_per_minute - len(self.minute_windows[client_id]))
        hour_remaining = max(0, self.requests_per_hour - len(self.hour_windows[client_id]))
        
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(minute_remaining)
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(hour_remaining)
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request logging and tracing."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = hashlib.md5(
            f"{time.time()}{request.client.host}{request.url.path}".encode()
        ).hexdigest()[:16]
        
        request.state.request_id = request_id
        
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": request.client.host,
                "user_agent": request.headers.get("User-Agent", ""),
            }
        )
        
        try:
            response = await call_next(request)
            
            # Log response
            duration = time.time() - start_time
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                }
            )
            
            return response
            
        except Exception as e:
            # Log error
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} - {type(e).__name__}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "duration_ms": round(duration * 1000, 2),
                }
            )
            raise


class JWTValidator:
    """JWT token validation utilities."""
    
    def __init__(self):
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.expiration_hours = settings.jwt_expiration_hours
    
    def create_token(self, user_id: str, additional_claims: Optional[Dict[str, Any]] = None) -> str:
        """Create JWT token for user."""
        
        now = datetime.utcnow()
        payload = {
            "user_id": user_id,
            "iat": now,
            "exp": now + timedelta(hours=self.expiration_hours),
            "iss": "snapstudy-api",
            "aud": "snapstudy-frontend"
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token."""
        
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience="snapstudy-frontend",
                issuer="snapstudy-api"
            )
            
            # Check if token is expired
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
                raise AuthenticationError("Token has expired")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")
        except Exception as e:
            raise AuthenticationError(f"Token validation failed: {str(e)}")
    
    def refresh_token(self, token: str) -> str:
        """Refresh JWT token if it's close to expiration."""
        
        payload = self.verify_token(token)
        
        # Check if token needs refresh (less than 1 hour remaining)
        exp = payload.get("exp")
        if exp:
            time_remaining = datetime.fromtimestamp(exp) - datetime.utcnow()
            if time_remaining < timedelta(hours=1):
                user_id = payload.get("user_id")
                if user_id:
                    return self.create_token(user_id)
        
        return token


class EnhancedHTTPBearer(HTTPBearer):
    """Enhanced HTTP Bearer authentication with better error handling."""
    
    def __init__(self, jwt_validator: JWTValidator):
        super().__init__(auto_error=False)
        self.jwt_validator = jwt_validator
    
    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        credentials = await super().__call__(request)
        
        if not credentials:
            # Check if endpoint requires authentication
            if self._requires_auth(request):
                raise AuthenticationError("Authentication required")
            return None
        
        # Validate token
        try:
            payload = self.jwt_validator.verify_token(credentials.credentials)
            
            # Add user info to request state
            request.state.user_id = payload.get("user_id")
            request.state.token_payload = payload
            
            return credentials
            
        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError(f"Authentication failed: {str(e)}")
    
    def _requires_auth(self, request: Request) -> bool:
        """Check if endpoint requires authentication."""
        
        # Public endpoints that don't require authentication
        public_paths = {
            "/", "/health", "/docs", "/redoc", "/openapi.json",
            "/api/v1/auth/login", "/api/v1/auth/register"
        }
        
        return request.url.path not in public_paths


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """Enhanced CORS middleware with security checks."""
    
    def __init__(self, app, allowed_origins: Optional[Set[str]] = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or set(settings.cors_origins)
        
        # In production, restrict origins
        if settings.cors_origins == ["*"]:
            logger.warning("CORS is configured to allow all origins. This should be restricted in production.")
    
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("Origin")
        
        # Check if origin is allowed
        if origin and self.allowed_origins != {"*"}:
            if origin not in self.allowed_origins:
                logger.warning(
                    f"CORS request from unauthorized origin: {origin}",
                    extra={
                        "origin": origin,
                        "path": request.url.path,
                        "method": request.method
                    }
                )
                
                return JSONResponse(
                    status_code=403,
                    content=create_error_response(
                        error_code="CORS_ERROR",
                        message="Origin not allowed",
                        status_code=403
                    )
                )
        
        response = await call_next(request)
        
        # Add CORS headers for allowed origins
        if origin and (self.allowed_origins == {"*"} or origin in self.allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-Requested-With"
            response.headers["Access-Control-Max-Age"] = "86400"  # 24 hours
        
        return response


# Global instances
jwt_validator = JWTValidator()
enhanced_bearer = EnhancedHTTPBearer(jwt_validator)