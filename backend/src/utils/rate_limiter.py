"""
Rate limiting utilities for AWS Bedrock API calls.

Implements token bucket algorithm to prevent burst requests that exceed AWS limits.
"""

import asyncio
import time
from typing import Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 80  # Conservative limit (80% of 100 RPM quota)
    burst_capacity: int = 10       # Allow small bursts
    refill_rate: float = 1.33      # requests per second (80/60)


class TokenBucket:
    """Token bucket rate limiter implementation."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.tokens = config.burst_capacity
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from the bucket. Returns True if successful."""
        async with self._lock:
            now = time.time()
            
            # Refill tokens based on time elapsed
            time_elapsed = now - self.last_refill
            tokens_to_add = time_elapsed * self.config.refill_rate
            
            self.tokens = min(
                self.config.burst_capacity,
                self.tokens + tokens_to_add
            )
            self.last_refill = now
            
            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    async def wait_for_tokens(self, tokens: int = 1) -> None:
        """Wait until tokens are available."""
        while not await self.acquire(tokens):
            # Calculate wait time for next token
            wait_time = tokens / self.config.refill_rate
            await asyncio.sleep(min(wait_time, 1.0))  # Max 1 second wait


class BedrockRateLimiter:
    """Rate limiter specifically for Bedrock services."""
    
    def __init__(self):
        # Separate rate limiters for different services
        self.agent_limiter = TokenBucket(RateLimitConfig(
            requests_per_minute=40,  # Conservative for agents
            burst_capacity=5,
            refill_rate=0.67
        ))
        
        self.model_limiter = TokenBucket(RateLimitConfig(
            requests_per_minute=60,  # Conservative for direct model calls
            burst_capacity=8,
            refill_rate=1.0
        ))
    
    async def acquire_agent_token(self) -> None:
        """Acquire token for Bedrock Agent call."""
        await self.agent_limiter.wait_for_tokens(1)
        logger.debug("Acquired token for Bedrock Agent call")
    
    async def acquire_model_token(self) -> None:
        """Acquire token for Bedrock Model call."""
        await self.model_limiter.wait_for_tokens(1)
        logger.debug("Acquired token for Bedrock Model call")


# Global rate limiter instance
bedrock_rate_limiter = BedrockRateLimiter()