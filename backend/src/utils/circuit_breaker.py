"""
Circuit breaker pattern for AWS Bedrock services.

Prevents cascading failures by temporarily disabling calls to failing services.
"""

import asyncio
import time
from enum import Enum
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Service is failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5      # Failures before opening circuit
    recovery_timeout: int = 60      # Seconds before trying half-open
    success_threshold: int = 3      # Successes needed to close circuit
    timeout: int = 30               # Request timeout in seconds


class CircuitBreaker:
    """Circuit breaker implementation for service calls."""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    logger.info(f"Circuit breaker {self.name} entering HALF_OPEN state")
                else:
                    raise Exception(f"Circuit breaker {self.name} is OPEN - service unavailable")
        
        try:
            # Execute the function with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )
            
            await self._on_success()
            return result
            
        except Exception as e:
            await self._on_failure(e)
            raise
    
    async def _on_success(self):
        """Handle successful call."""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    logger.info(f"Circuit breaker {self.name} CLOSED - service recovered")
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0  # Reset failure count on success
    
    async def _on_failure(self, exception: Exception):
        """Handle failed call."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker {self.name} OPEN - service still failing")
            elif (self.state == CircuitState.CLOSED and 
                  self.failure_count >= self.config.failure_threshold):
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker {self.name} OPEN - failure threshold reached")
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (time.time() - self.last_failure_time) >= self.config.recovery_timeout
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time
        }


class BedrockCircuitBreakers:
    """Circuit breakers for Bedrock services."""
    
    def __init__(self):
        # Circuit breaker for Bedrock Agents
        self.agent_breaker = CircuitBreaker(
            "bedrock_agents",
            CircuitBreakerConfig(
                failure_threshold=3,    # Lower threshold for agents
                recovery_timeout=120,   # Longer recovery time
                success_threshold=2,
                timeout=45
            )
        )
        
        # Circuit breaker for Bedrock Models
        self.model_breaker = CircuitBreaker(
            "bedrock_models",
            CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=60,
                success_threshold=3,
                timeout=30
            )
        )
    
    async def call_agent(self, func: Callable, *args, **kwargs) -> Any:
        """Call Bedrock Agent with circuit breaker protection."""
        return await self.agent_breaker.call(func, *args, **kwargs)
    
    async def call_model(self, func: Callable, *args, **kwargs) -> Any:
        """Call Bedrock Model with circuit breaker protection."""
        return await self.model_breaker.call(func, *args, **kwargs)
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all circuit breakers."""
        return {
            'agent_breaker': self.agent_breaker.get_state(),
            'model_breaker': self.model_breaker.get_state()
        }


# Global circuit breaker instance
bedrock_circuit_breakers = BedrockCircuitBreakers()