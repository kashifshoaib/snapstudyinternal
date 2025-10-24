"""
Bedrock Request Coordinator

Coordinates all Bedrock requests (Agents + Models) to prevent throttling by
ensuring proper spacing between all types of requests.
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class BedrockRequestCoordinator:
    """
    Global coordinator for all Bedrock requests to prevent throttling.
    
    This ensures that ALL Bedrock requests (agents, models, etc.) are properly
    spaced out to prevent burst throttling, regardless of which service makes the call.
    """
    
    def __init__(self):
        # Global lock for all Bedrock requests
        self._request_lock = asyncio.Lock()
        
        # Track last request time for spacing
        self._last_request_time = 0.0
        
        # Minimum delay between ANY Bedrock requests (very aggressive spacing)
        self._min_request_interval = 6.0  # 6 seconds between requests (very aggressive)
        
        # Track request statistics
        self._stats = {
            'total_requests': 0,
            'agent_requests': 0,
            'model_requests': 0,
            'total_wait_time': 0.0,
            'throttled_requests': 0
        }
    
    async def execute_bedrock_request(
        self, 
        request_type: str,  # 'agent' or 'model'
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a Bedrock request with global coordination.
        
        This method ensures that ALL Bedrock requests are properly spaced
        to prevent throttling, regardless of the calling service.
        """
        async with self._request_lock:
            # Calculate required wait time
            current_time = time.time()
            time_since_last_request = current_time - self._last_request_time
            
            if time_since_last_request < self._min_request_interval:
                wait_time = self._min_request_interval - time_since_last_request
                
                logger.info(
                    f"🕐 Bedrock {request_type} request delayed {wait_time:.2f}s "
                    f"to prevent throttling (last request {time_since_last_request:.2f}s ago)"
                )
                
                await asyncio.sleep(wait_time)
                self._stats['total_wait_time'] += wait_time
            
            # Update last request time
            self._last_request_time = time.time()
            
            # Update statistics
            self._stats['total_requests'] += 1
            if request_type == 'agent':
                self._stats['agent_requests'] += 1
            else:
                self._stats['model_requests'] += 1
            
            logger.info(f"🚀 Executing Bedrock {request_type} request (interval: {self._min_request_interval}s)")
        
        # Execute the actual request (outside the lock to allow other coordination)
        try:
            start_time = time.time()
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            logger.info(f"✅ Bedrock {request_type} request completed in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            # Check if it's a throttling error
            error_str = str(e).lower()
            if 'throttl' in error_str or 'rate' in error_str or 'too many' in error_str:
                self._stats['throttled_requests'] += 1
                logger.error(f"🚫 Bedrock {request_type} request throttled despite coordination: {e}")
                
                # Increase minimum interval aggressively if we're still getting throttled
                async with self._request_lock:
                    old_interval = self._min_request_interval
                    self._min_request_interval = min(self._min_request_interval * 2.0, 30.0)  # Double it, max 30s
                    logger.error(f"📈 AGGRESSIVELY increased minimum request interval from {old_interval:.2f}s to {self._min_request_interval:.2f}s")
                    logger.error(f"🛑 This indicates your AWS quotas may be lower than expected or there's high concurrent usage")
            
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get coordinator statistics."""
        return {
            **self._stats,
            'current_min_interval': self._min_request_interval,
            'time_since_last_request': time.time() - self._last_request_time,
            'throttle_rate': (self._stats['throttled_requests'] / max(1, self._stats['total_requests'])) * 100
        }
    
    def adjust_interval(self, new_interval: float):
        """Manually adjust the minimum request interval."""
        self._min_request_interval = max(0.5, min(new_interval, 30.0))  # Clamp between 0.5s and 30s
        logger.info(f"🔧 Manually adjusted minimum request interval to {self._min_request_interval:.2f}s")


# Global coordinator instance
bedrock_coordinator = BedrockRequestCoordinator()