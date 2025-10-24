"""
Retry utilities with exponential backoff for AWS services.

Provides robust retry mechanisms for API calls with intelligent backoff strategies.
"""

import asyncio
import logging
import random
from typing import Callable, Any, Optional, Type, Tuple, Dict
from functools import wraps
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or (
            ClientError,
            BotoCoreError,
            ConnectionError,
            TimeoutError
        )


# Predefined retry configurations
BEDROCK_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True
)

DYNAMODB_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=0.5,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=True
)

S3_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=15.0,
    exponential_base=2.0,
    jitter=True
)

POLLY_RETRY_CONFIG = RetryConfig(
    max_attempts=4,
    base_delay=1.0,
    max_delay=20.0,
    exponential_base=2.0,
    jitter=True
)


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay for retry attempt with exponential backoff and jitter."""
    
    # Exponential backoff
    delay = config.base_delay * (config.exponential_base ** (attempt - 1))
    
    # Cap at max delay
    delay = min(delay, config.max_delay)
    
    # Add jitter to prevent thundering herd
    if config.jitter:
        jitter_range = delay * 0.1  # 10% jitter
        delay += random.uniform(-jitter_range, jitter_range)
    
    return max(0, delay)


def is_retryable_error(exception: Exception, config: RetryConfig) -> bool:
    """Determine if an exception should trigger a retry."""
    
    # Check if exception type is retryable
    if not isinstance(exception, config.retryable_exceptions):
        return False
    
    # For AWS ClientError, check specific error codes
    if isinstance(exception, ClientError):
        error_code = exception.response.get('Error', {}).get('Code', '')
        
        # Non-retryable AWS errors
        non_retryable_codes = {
            'AccessDenied',
            'InvalidParameterValue',
            'ValidationException',
            'ResourceNotFoundException',
            'InvalidRequestException',
            'UnauthorizedOperation'
        }
        
        if error_code in non_retryable_codes:
            return False
        
        # Retryable AWS errors
        retryable_codes = {
            'ThrottlingException',
            'TooManyRequestsException',
            'ServiceUnavailable',
            'InternalFailure',
            'RequestTimeout',
            'ServiceQuotaExceededException'
        }
        
        return error_code in retryable_codes or error_code.endswith('Exception')
    
    return True


async def retry_async(
    func: Callable,
    config: RetryConfig,
    *args,
    **kwargs
) -> Any:
    """Execute async function with retry logic."""
    
    last_exception = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            start_time = datetime.utcnow()
            result = await func(*args, **kwargs)
            
            # Log successful retry if not first attempt
            if attempt > 1:
                logger.info(
                    f"Function {func.__name__} succeeded on attempt {attempt}",
                    extra={
                        "function": func.__name__,
                        "attempt": attempt,
                        "total_attempts": config.max_attempts
                    }
                )
            
            return result
            
        except Exception as e:
            last_exception = e
            
            # Check if we should retry
            if not is_retryable_error(e, config):
                logger.warning(
                    f"Non-retryable error in {func.__name__}: {type(e).__name__} - {str(e)}",
                    extra={
                        "function": func.__name__,
                        "attempt": attempt,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    }
                )
                raise e
            
            # Don't retry on last attempt
            if attempt == config.max_attempts:
                logger.error(
                    f"Function {func.__name__} failed after {config.max_attempts} attempts",
                    extra={
                        "function": func.__name__,
                        "total_attempts": config.max_attempts,
                        "final_error_type": type(e).__name__,
                        "final_error_message": str(e)
                    }
                )
                break
            
            # Calculate delay and wait
            delay = calculate_delay(attempt, config)
            
            logger.warning(
                f"Function {func.__name__} failed on attempt {attempt}, retrying in {delay:.2f}s",
                extra={
                    "function": func.__name__,
                    "attempt": attempt,
                    "total_attempts": config.max_attempts,
                    "delay_seconds": delay,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            
            await asyncio.sleep(delay)
    
    # All attempts failed
    raise last_exception


def retry_sync(
    func: Callable,
    config: RetryConfig,
    *args,
    **kwargs
) -> Any:
    """Execute sync function with retry logic."""
    
    last_exception = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            result = func(*args, **kwargs)
            
            # Log successful retry if not first attempt
            if attempt > 1:
                logger.info(
                    f"Function {func.__name__} succeeded on attempt {attempt}",
                    extra={
                        "function": func.__name__,
                        "attempt": attempt,
                        "total_attempts": config.max_attempts
                    }
                )
            
            return result
            
        except Exception as e:
            last_exception = e
            
            # Check if we should retry
            if not is_retryable_error(e, config):
                logger.warning(
                    f"Non-retryable error in {func.__name__}: {type(e).__name__} - {str(e)}",
                    extra={
                        "function": func.__name__,
                        "attempt": attempt,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    }
                )
                raise e
            
            # Don't retry on last attempt
            if attempt == config.max_attempts:
                logger.error(
                    f"Function {func.__name__} failed after {config.max_attempts} attempts",
                    extra={
                        "function": func.__name__,
                        "total_attempts": config.max_attempts,
                        "final_error_type": type(e).__name__,
                        "final_error_message": str(e)
                    }
                )
                break
            
            # Calculate delay and wait
            delay = calculate_delay(attempt, config)
            
            logger.warning(
                f"Function {func.__name__} failed on attempt {attempt}, retrying in {delay:.2f}s",
                extra={
                    "function": func.__name__,
                    "attempt": attempt,
                    "total_attempts": config.max_attempts,
                    "delay_seconds": delay,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            
            import time
            time.sleep(delay)
    
    # All attempts failed
    raise last_exception


def with_retry(config: RetryConfig = BEDROCK_RETRY_CONFIG):
    """Decorator for adding retry logic to async functions."""
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_async(func, config, *args, **kwargs)
        return wrapper
    
    return decorator


def with_sync_retry(config: RetryConfig = BEDROCK_RETRY_CONFIG):
    """Decorator for adding retry logic to sync functions."""
    
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return retry_sync(func, config, *args, **kwargs)
        return wrapper
    
    return decorator


# Convenience decorators for specific services
bedrock_retry = with_retry(BEDROCK_RETRY_CONFIG)
dynamodb_retry = with_retry(DYNAMODB_RETRY_CONFIG)
s3_retry = with_retry(S3_RETRY_CONFIG)
polly_retry = with_retry(POLLY_RETRY_CONFIG)

bedrock_sync_retry = with_sync_retry(BEDROCK_RETRY_CONFIG)
dynamodb_sync_retry = with_sync_retry(DYNAMODB_RETRY_CONFIG)
s3_sync_retry = with_sync_retry(S3_RETRY_CONFIG)
polly_sync_retry = with_sync_retry(POLLY_RETRY_CONFIG)


class CircuitBreaker:
    """Circuit breaker pattern for service protection."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def __call__(self, func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == 'OPEN':
                if self._should_attempt_reset():
                    self.state = 'HALF_OPEN'
                else:
                    raise ServiceUnavailableError(
                        func.__name__,
                        "Circuit breaker is OPEN"
                    )
            
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
                
            except self.expected_exception as e:
                self._on_failure()
                raise e
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        
        return (
            datetime.utcnow() - self.last_failure_time
        ).total_seconds() >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures",
                extra={
                    "failure_count": self.failure_count,
                    "failure_threshold": self.failure_threshold
                }
            )


# Define ServiceUnavailableError locally to avoid circular imports
class ServiceUnavailableError(Exception):
    """Local ServiceUnavailableError to avoid circular imports."""
    def __init__(self, service: str, message: str = ""):
        full_message = f"{service} service unavailable"
        if message:
            full_message += f": {message}"
        super().__init__(full_message)