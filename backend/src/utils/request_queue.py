"""
Request queue for managing Bedrock API calls.

Implements a queue-based system to serialize requests and prevent burst throttling.
"""

import asyncio
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


@dataclass
class QueuedRequest:
    """Represents a queued request."""
    id: str
    func: Callable
    args: tuple
    kwargs: dict
    priority: int = 0  # Higher number = higher priority
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


class BedrockRequestQueue:
    """Queue manager for Bedrock API requests."""
    
    def __init__(self, max_concurrent: int = 3, processing_delay: float = 0.5):
        self.max_concurrent = max_concurrent
        self.processing_delay = processing_delay  # Delay between requests
        
        # Separate queues for different request types
        self.agent_queue = asyncio.PriorityQueue()
        self.model_queue = asyncio.PriorityQueue()
        
        # Track active requests
        self.active_agent_requests = 0
        self.active_model_requests = 0
        
        # Processing tasks
        self.agent_processor_task = None
        self.model_processor_task = None
        
        # Statistics
        self.stats = {
            'agent_requests_processed': 0,
            'model_requests_processed': 0,
            'agent_queue_size': 0,
            'model_queue_size': 0,
            'total_wait_time': 0.0
        }
        
        self._start_processors()
    
    def _start_processors(self):
        """Start background processors for queues."""
        self.agent_processor_task = asyncio.create_task(self._process_agent_queue())
        self.model_processor_task = asyncio.create_task(self._process_model_queue())
    
    async def queue_agent_request(
        self, 
        func: Callable, 
        *args, 
        priority: int = 0,
        **kwargs
    ) -> Any:
        """Queue a Bedrock Agent request."""
        request_id = f"agent_{datetime.now().timestamp()}"
        request = QueuedRequest(request_id, func, args, kwargs, priority)
        
        # Create future for result
        future = asyncio.Future()
        request.future = future
        
        # Add to queue (negative priority for max-heap behavior)
        await self.agent_queue.put((-priority, request))
        self.stats['agent_queue_size'] = self.agent_queue.qsize()
        
        logger.debug(f"Queued agent request {request_id}, queue size: {self.agent_queue.qsize()}")
        
        # Wait for result
        return await future
    
    async def queue_model_request(
        self, 
        func: Callable, 
        *args, 
        priority: int = 0,
        **kwargs
    ) -> Any:
        """Queue a Bedrock Model request."""
        request_id = f"model_{datetime.now().timestamp()}"
        request = QueuedRequest(request_id, func, args, kwargs, priority)
        
        # Create future for result
        future = asyncio.Future()
        request.future = future
        
        # Add to queue (negative priority for max-heap behavior)
        await self.model_queue.put((-priority, request))
        self.stats['model_queue_size'] = self.model_queue.qsize()
        
        logger.debug(f"Queued model request {request_id}, queue size: {self.model_queue.qsize()}")
        
        # Wait for result
        return await future
    
    async def _process_agent_queue(self):
        """Process agent requests from queue."""
        while True:
            try:
                if self.active_agent_requests >= self.max_concurrent:
                    await asyncio.sleep(0.1)
                    continue
                
                # Get next request
                try:
                    priority, request = await asyncio.wait_for(
                        self.agent_queue.get(), 
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process request
                self.active_agent_requests += 1
                asyncio.create_task(self._execute_agent_request(request))
                
                # Delay between requests to prevent bursts
                await asyncio.sleep(self.processing_delay)
                
            except Exception as e:
                logger.error(f"Error in agent queue processor: {e}")
                await asyncio.sleep(1.0)
    
    async def _process_model_queue(self):
        """Process model requests from queue."""
        while True:
            try:
                if self.active_model_requests >= self.max_concurrent:
                    await asyncio.sleep(0.1)
                    continue
                
                # Get next request
                try:
                    priority, request = await asyncio.wait_for(
                        self.model_queue.get(), 
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process request
                self.active_model_requests += 1
                asyncio.create_task(self._execute_model_request(request))
                
                # Delay between requests to prevent bursts
                await asyncio.sleep(self.processing_delay)
                
            except Exception as e:
                logger.error(f"Error in model queue processor: {e}")
                await asyncio.sleep(1.0)
    
    async def _execute_agent_request(self, request: QueuedRequest):
        """Execute an agent request."""
        try:
            start_time = datetime.now(timezone.utc)
            
            # Execute the function
            result = await request.func(*request.args, **request.kwargs)
            
            # Calculate wait time
            wait_time = (start_time - request.created_at).total_seconds()
            self.stats['total_wait_time'] += wait_time
            self.stats['agent_requests_processed'] += 1
            
            # Set result
            request.future.set_result(result)
            
            logger.debug(f"Completed agent request {request.id}, wait time: {wait_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Agent request {request.id} failed: {e}")
            request.future.set_exception(e)
        finally:
            self.active_agent_requests -= 1
            self.stats['agent_queue_size'] = self.agent_queue.qsize()
    
    async def _execute_model_request(self, request: QueuedRequest):
        """Execute a model request."""
        try:
            start_time = datetime.now(timezone.utc)
            
            # Execute the function
            result = await request.func(*request.args, **request.kwargs)
            
            # Calculate wait time
            wait_time = (start_time - request.created_at).total_seconds()
            self.stats['total_wait_time'] += wait_time
            self.stats['model_requests_processed'] += 1
            
            # Set result
            request.future.set_result(result)
            
            logger.debug(f"Completed model request {request.id}, wait time: {wait_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Model request {request.id} failed: {e}")
            request.future.set_exception(e)
        finally:
            self.active_model_requests -= 1
            self.stats['model_queue_size'] = self.model_queue.qsize()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            **self.stats,
            'active_agent_requests': self.active_agent_requests,
            'active_model_requests': self.active_model_requests,
            'agent_queue_size': self.agent_queue.qsize(),
            'model_queue_size': self.model_queue.qsize()
        }
    
    async def shutdown(self):
        """Shutdown the queue processors."""
        if self.agent_processor_task:
            self.agent_processor_task.cancel()
        if self.model_processor_task:
            self.model_processor_task.cancel()


# Global request queue instance
bedrock_request_queue = BedrockRequestQueue(
    max_concurrent=2,      # Conservative concurrency
    processing_delay=0.8   # 800ms delay between requests
)