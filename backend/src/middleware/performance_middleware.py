"""
Performance optimization middleware for FastAPI.

This middleware provides response compression, caching headers,
and performance monitoring for API endpoints.
"""

import time
import gzip
import json
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

from ..utils.performance_monitor import performance_metrics, cache_manager

logger = logging.getLogger(__name__)


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware for performance optimization and monitoring."""
    
    def __init__(
        self,
        app: ASGIApp,
        enable_compression: bool = True,
        enable_caching: bool = True,
        compression_threshold: int = 1024,  # Compress responses > 1KB
        cache_control_max_age: int = 300,   # 5 minutes default cache
    ):
        super().__init__(app)
        self.enable_compression = enable_compression
        self.enable_caching = enable_caching
        self.compression_threshold = compression_threshold
        self.cache_control_max_age = cache_control_max_age
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with performance optimizations."""
        start_time = time.time()
        
        # Generate request ID for tracking
        request_id = f"req_{int(start_time * 1000)}_{id(request)}"
        request.state.request_id = request_id
        
        # Check for cached response
        if self.enable_caching and request.method == "GET":
            cached_response = await self._get_cached_response(request)
            if cached_response:
                # Add performance headers
                cached_response.headers["X-Cache"] = "HIT"
                cached_response.headers["X-Request-ID"] = request_id
                
                # Record cache hit metric
                duration = time.time() - start_time
                performance_metrics.record_operation(
                    f"{request.method} {request.url.path}",
                    duration,
                    True,
                    {"cache": "hit", "request_id": request_id}
                )
                
                return cached_response
        
        # Process request
        try:
            response = await call_next(request)
            success = 200 <= response.status_code < 400
        except Exception as e:
            logger.error(f"Request {request_id} failed: {str(e)}")
            success = False
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "request_id": request_id}
            )
        
        # Calculate response time
        duration = time.time() - start_time
        
        # Add performance headers
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        response.headers["X-Request-ID"] = request_id
        
        # Add cache headers for GET requests
        if self.enable_caching and request.method == "GET" and success:
            await self._add_cache_headers(request, response)
            
            # Cache successful responses
            if response.status_code == 200:
                await self._cache_response(request, response)
        
        # Compress response if enabled and beneficial
        if self.enable_compression and success:
            response = await self._compress_response(request, response)
        
        # Record performance metrics
        performance_metrics.record_operation(
            f"{request.method} {request.url.path}",
            duration,
            success,
            {
                "status_code": response.status_code,
                "request_id": request_id,
                "cache": "miss" if self.enable_caching and request.method == "GET" else "n/a"
            }
        )
        
        # Log slow requests
        if duration > 2.0:
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path} "
                f"took {duration:.3f}s (Request ID: {request_id})"
            )
        
        return response
    
    async def _get_cached_response(self, request: Request) -> Optional[Response]:
        """Get cached response if available."""
        cache_key = self._generate_cache_key(request)
        cached_data = cache_manager.get(cache_key)
        
        if cached_data:
            return JSONResponse(
                content=cached_data["content"],
                status_code=cached_data["status_code"],
                headers=cached_data.get("headers", {})
            )
        
        return None
    
    async def _cache_response(self, request: Request, response: Response) -> None:
        """Cache response for future requests."""
        if not isinstance(response, JSONResponse):
            return
        
        # Don't cache responses with authentication or user-specific data
        if "authorization" in request.headers or "user" in str(request.url.path).lower():
            return
        
        cache_key = self._generate_cache_key(request)
        
        # Extract response content
        if hasattr(response, 'body'):
            try:
                content = json.loads(response.body.decode())
                cache_data = {
                    "content": content,
                    "status_code": response.status_code,
                    "headers": dict(response.headers)
                }
                
                # Cache for default TTL
                cache_manager.set(cache_key, cache_data, self.cache_control_max_age)
            except (json.JSONDecodeError, AttributeError):
                # Skip caching if we can't decode the response
                pass
    
    async def _add_cache_headers(self, request: Request, response: Response) -> None:
        """Add appropriate cache headers to response."""
        # Determine cache strategy based on endpoint
        path = request.url.path
        
        if "/auth/" in path:
            # Don't cache auth endpoints
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        elif "/users/" in path:
            # Short cache for user data
            response.headers["Cache-Control"] = f"private, max-age=60"
        elif "/lessons/" in path or "/analytics/" in path:
            # Medium cache for lesson and analytics data
            response.headers["Cache-Control"] = f"private, max-age={self.cache_control_max_age}"
        else:
            # Default cache
            response.headers["Cache-Control"] = f"public, max-age={self.cache_control_max_age}"
        
        # Add ETag for cache validation
        if hasattr(response, 'body') and response.body:
            import hashlib
            etag = hashlib.md5(response.body).hexdigest()
            response.headers["ETag"] = f'"{etag}"'
            
            # Check if client has current version
            if request.headers.get("If-None-Match") == f'"{etag}"':
                response.status_code = 304
                response.body = b""
    
    async def _compress_response(self, request: Request, response: Response) -> Response:
        """Compress response if beneficial."""
        # Check if client accepts gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            return response
        
        # Check if response is large enough to benefit from compression
        if not hasattr(response, 'body') or len(response.body) < self.compression_threshold:
            return response
        
        # Check content type
        content_type = response.headers.get("content-type", "")
        compressible_types = [
            "application/json",
            "text/html",
            "text/css",
            "text/javascript",
            "application/javascript"
        ]
        
        if not any(ct in content_type for ct in compressible_types):
            return response
        
        # Compress the response
        try:
            compressed_body = gzip.compress(response.body)
            
            # Only use compression if it actually reduces size
            if len(compressed_body) < len(response.body):
                response.body = compressed_body
                response.headers["Content-Encoding"] = "gzip"
                response.headers["Content-Length"] = str(len(compressed_body))
                response.headers["Vary"] = "Accept-Encoding"
        except Exception as e:
            logger.warning(f"Failed to compress response: {e}")
        
        return response
    
    def _generate_cache_key(self, request: Request) -> str:
        """Generate cache key for request."""
        import hashlib
        
        # Include method, path, and query parameters
        key_parts = [
            request.method,
            str(request.url.path),
            str(request.url.query)
        ]
        
        # Include relevant headers that affect response
        relevant_headers = ["accept", "accept-language"]
        for header in relevant_headers:
            if header in request.headers:
                key_parts.append(f"{header}:{request.headers[header]}")
        
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()


class ResponseOptimizationMiddleware(BaseHTTPMiddleware):
    """Middleware for response optimization and minification."""
    
    def __init__(self, app: ASGIApp, minify_json: bool = True):
        super().__init__(app)
        self.minify_json = minify_json
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Optimize response content."""
        response = await call_next(request)
        
        # Optimize JSON responses
        if (self.minify_json and 
            isinstance(response, JSONResponse) and 
            hasattr(response, 'body')):
            
            try:
                # Parse and re-serialize JSON without whitespace
                content = json.loads(response.body.decode())
                optimized_body = json.dumps(content, separators=(',', ':')).encode()
                
                # Update response if optimization reduces size
                if len(optimized_body) < len(response.body):
                    response.body = optimized_body
                    response.headers["Content-Length"] = str(len(optimized_body))
                    
            except (json.JSONDecodeError, AttributeError):
                # Skip optimization if JSON parsing fails
                pass
        
        return response


# Database query optimization middleware
class DatabaseOptimizationMiddleware(BaseHTTPMiddleware):
    """Middleware for database query optimization."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.query_cache: Dict[str, Any] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add database optimization context."""
        # Add query optimization hints to request state
        request.state.db_optimization = {
            "enable_query_cache": True,
            "batch_queries": True,
            "use_read_replicas": request.method == "GET"
        }
        
        return await call_next(request)


# Rate limiting middleware for performance protection
class PerformanceRateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware to protect performance."""
    
    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 60,
        burst_limit: int = 10
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.request_counts: Dict[str, Dict[str, Any]] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting based on client IP."""
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Clean old entries
        self._cleanup_old_entries(current_time)
        
        # Check rate limits
        if self._is_rate_limited(client_ip, current_time):
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please slow down.",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Record request
        self._record_request(client_ip, current_time)
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check for forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """Check if client is rate limited."""
        if client_ip not in self.request_counts:
            return False
        
        client_data = self.request_counts[client_ip]
        
        # Check burst limit (requests in last 10 seconds)
        recent_requests = [
            t for t in client_data["timestamps"] 
            if current_time - t < 10
        ]
        
        if len(recent_requests) >= self.burst_limit:
            return True
        
        # Check per-minute limit
        minute_requests = [
            t for t in client_data["timestamps"] 
            if current_time - t < 60
        ]
        
        return len(minute_requests) >= self.requests_per_minute
    
    def _record_request(self, client_ip: str, current_time: float) -> None:
        """Record a request for rate limiting."""
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = {"timestamps": []}
        
        self.request_counts[client_ip]["timestamps"].append(current_time)
        
        # Keep only last 100 timestamps per client
        timestamps = self.request_counts[client_ip]["timestamps"]
        if len(timestamps) > 100:
            self.request_counts[client_ip]["timestamps"] = timestamps[-100:]
    
    def _cleanup_old_entries(self, current_time: float) -> None:
        """Clean up old rate limiting entries."""
        cutoff_time = current_time - 3600  # 1 hour ago
        
        for client_ip in list(self.request_counts.keys()):
            timestamps = self.request_counts[client_ip]["timestamps"]
            recent_timestamps = [t for t in timestamps if t > cutoff_time]
            
            if recent_timestamps:
                self.request_counts[client_ip]["timestamps"] = recent_timestamps
            else:
                del self.request_counts[client_ip]