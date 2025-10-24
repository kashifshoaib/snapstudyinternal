"""
Comprehensive error handling middleware for SnapStudy backend.

Provides centralized error handling, logging, and user-friendly error responses.
"""

import logging
import traceback
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import boto3
from botocore.exceptions import ClientError, BotoCoreError, NoCredentialsError

logger = logging.getLogger(__name__)


class SnapStudyException(Exception):
    """Base exception class for SnapStudy application."""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = 500, 
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(SnapStudyException):
    """Exception for validation errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            details=details
        )


class AuthenticationError(SnapStudyException):
    """Exception for authentication errors."""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_ERROR",
            details=details
        )


class AuthorizationError(SnapStudyException):
    """Exception for authorization errors."""
    
    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHORIZATION_ERROR",
            details=details
        )


class ResourceNotFoundError(SnapStudyException):
    """Exception for resource not found errors."""

    def __init__(self, resource: str, resource_id: str = "", details: Optional[Dict[str, Any]] = None):
        message = f"{resource} not found"
        if resource_id:
            message += f" (ID: {resource_id})"

        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
            details=details or {"resource": resource, "resource_id": resource_id}
        )


class ResourceConflictError(SnapStudyException):
    """Exception for resource conflict errors (e.g., duplicate resources)."""

    def __init__(self, resource: str, field: str = "", value: str = "", details: Optional[Dict[str, Any]] = None):
        message = f"{resource} already exists"
        if field and value:
            message += f" with {field}: {value}"

        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="RESOURCE_CONFLICT",
            details=details or {"resource": resource, "field": field, "value": value}
        )


class ServiceUnavailableError(SnapStudyException):
    """Exception for service unavailable errors."""
    
    def __init__(self, service: str, message: str = "", details: Optional[Dict[str, Any]] = None):
        full_message = f"{service} service unavailable"
        if message:
            full_message += f": {message}"
        
        super().__init__(
            message=full_message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="SERVICE_UNAVAILABLE",
            details=details or {"service": service}
        )


class RateLimitError(SnapStudyException):
    """Exception for rate limit errors."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after}
        )


def create_error_response(
    error_code: str,
    message: str,
    status_code: int = 500,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create standardized error response."""
    
    response = {
        "error": {
            "code": error_code,
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    }
    
    if details:
        response["error"]["details"] = details
    
    if request_id:
        response["error"]["request_id"] = request_id
    
    # Add user-friendly message based on error type
    user_messages = {
        "AUTHENTICATION_ERROR": "Please log in to continue.",
        "AUTHORIZATION_ERROR": "You don't have permission to access this resource.",
        "VALIDATION_ERROR": "Please check your input and try again.",
        "RESOURCE_NOT_FOUND": "The requested resource was not found.",
        "SERVICE_UNAVAILABLE": "This service is temporarily unavailable. Please try again later.",
        "RATE_LIMIT_EXCEEDED": "Too many requests. Please wait before trying again.",
        "INTERNAL_ERROR": "An unexpected error occurred. Please try again later."
    }
    
    if error_code in user_messages:
        response["error"]["user_message"] = user_messages[error_code]
    
    return response


def handle_aws_error(error: Exception) -> SnapStudyException:
    """Convert AWS errors to SnapStudy exceptions."""
    
    if isinstance(error, NoCredentialsError):
        return ServiceUnavailableError(
            "AWS",
            "AWS credentials not configured",
            {"aws_error": "NoCredentialsError"}
        )
    
    if isinstance(error, ClientError):
        error_code = error.response.get('Error', {}).get('Code', 'Unknown')
        error_message = error.response.get('Error', {}).get('Message', str(error))
        
        # Map common AWS errors
        if error_code in ['AccessDenied', 'UnauthorizedOperation']:
            return AuthorizationError(
                f"AWS access denied: {error_message}",
                {"aws_error_code": error_code}
            )
        
        if error_code in ['ResourceNotFoundException', 'NoSuchKey']:
            return ResourceNotFoundError(
                "AWS Resource",
                error_message,
                {"aws_error_code": error_code}
            )
        
        if error_code in ['ThrottlingException', 'TooManyRequestsException']:
            return RateLimitError(
                f"AWS rate limit: {error_message}",
                retry_after=30
            )
        
        if error_code in ['ServiceUnavailable', 'InternalFailure']:
            return ServiceUnavailableError(
                "AWS",
                error_message,
                {"aws_error_code": error_code}
            )
        
        # Generic AWS error
        return SnapStudyException(
            f"AWS error: {error_message}",
            status_code=500,
            error_code="AWS_ERROR",
            details={"aws_error_code": error_code}
        )
    
    if isinstance(error, BotoCoreError):
        return ServiceUnavailableError(
            "AWS",
            f"AWS connection error: {str(error)}",
            {"aws_error": "BotoCoreError"}
        )
    
    # Unknown AWS error
    return SnapStudyException(
        f"Unknown AWS error: {str(error)}",
        status_code=500,
        error_code="AWS_ERROR_UNKNOWN"
    )


async def snapstudy_exception_handler(request: Request, exc: SnapStudyException) -> JSONResponse:
    """Handle SnapStudy custom exceptions."""
    
    request_id = getattr(request.state, 'request_id', None)
    
    # Log the error
    logger.error(
        f"SnapStudy error: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    response_data = create_error_response(
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    
    request_id = getattr(request.state, 'request_id', None)
    
    # Map HTTP status codes to error codes
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        422: "UNPROCESSABLE_ENTITY",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT"
    }
    
    error_code = error_code_map.get(exc.status_code, "HTTP_ERROR")
    
    logger.warning(
        f"HTTP error: {exc.status_code} - {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    response_data = create_error_response(
        error_code=error_code,
        message=str(exc.detail),
        status_code=exc.status_code,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors."""
    
    request_id = getattr(request.state, 'request_id', None)
    
    # Extract validation error details
    validation_errors = []
    for error in exc.errors():
        validation_errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        f"Validation error: {len(validation_errors)} field(s)",
        extra={
            "validation_errors": validation_errors,
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    response_data = create_error_response(
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        status_code=422,
        details={"validation_errors": validation_errors},
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=422,
        content=response_data
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    
    request_id = getattr(request.state, 'request_id', None)
    
    # Log the full traceback for debugging
    logger.error(
        f"Unexpected error: {type(exc).__name__} - {str(exc)}",
        extra={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": traceback.format_exc(),
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    # Check if it's an AWS error
    if isinstance(exc, (ClientError, BotoCoreError, NoCredentialsError)):
        aws_exception = handle_aws_error(exc)
        return await snapstudy_exception_handler(request, aws_exception)
    
    # Generic error response (don't expose internal details)
    response_data = create_error_response(
        error_code="INTERNAL_ERROR",
        message="An unexpected error occurred",
        status_code=500,
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=500,
        content=response_data
    )