"""
Performance monitoring system for authentication flows.

This module provides comprehensive performance monitoring, caching strategies,
and optimization utilities for the authentication system.
"""

import time
import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from functools import wraps
from contextlib import asynccontextmanager
import json
import hashlib

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Collects and manages performance metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, List[Dict[str, Any]]] = {}
        self.cache_stats: Dict[str, Dict[str, int]] = {}
        self.slow_operations: List[Dict[str, Any]] = []
        
    def record_operation(
        self, 
        operation: str, 
        duration: float, 
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a performance metric for an operation."""
        if operation not in self.metrics:
            self.metrics[operation] = []
            
        metric = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "duration": duration,
            "success": success,
            "metadata": metadata or {}
        }
        
        self.metrics[operation].append(metric)
        
        # Track slow operations (> 2 seconds)
        if duration > 2.0:
            self.slow_operations.append({
                "operation": operation,
                "duration": duration,
                "timestamp": metric["timestamp"],
                "metadata": metadata
            })
            logger.warning(f"Slow operation detected: {operation} took {duration:.2f}s")
        
        # Keep only last 1000 metrics per operation
        if len(self.metrics[operation]) > 1000:
            self.metrics[operation] = self.metrics[operation][-1000:]
    
    def record_cache_hit(self, cache_key: str):
        """Record a cache hit."""
        if cache_key not in self.cache_stats:
            self.cache_stats[cache_key] = {"hits": 0, "misses": 0}
        self.cache_stats[cache_key]["hits"] += 1
    
    def record_cache_miss(self, cache_key: str):
        """Record a cache miss."""
        if cache_key not in self.cache_stats:
            self.cache_stats[cache_key] = {"hits": 0, "misses": 0}
        self.cache_stats[cache_key]["misses"] += 1
    
    def get_operation_stats(self, operation: str) -> Dict[str, Any]:
        """Get statistics for a specific operation."""
        if operation not in self.metrics:
            return {"error": "Operation not found"}
        
        durations = [m["duration"] for m in self.metrics[operation]]
        successes = [m["success"] for m in self.metrics[operation]]
        
        if not durations:
            return {"error": "No data available"}
        
        return {
            "operation": operation,
            "total_calls": len(durations),
            "success_rate": sum(successes) / len(successes) * 100,
            "avg_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "p95_duration": self._percentile(durations, 95),
            "p99_duration": self._percentile(durations, 99),
            "recent_calls": self.metrics[operation][-10:]  # Last 10 calls
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_hits = sum(stats["hits"] for stats in self.cache_stats.values())
        total_misses = sum(stats["misses"] for stats in self.cache_stats.values())
        total_requests = total_hits + total_misses
        
        return {
            "total_requests": total_requests,
            "total_hits": total_hits,
            "total_misses": total_misses,
            "hit_rate": (total_hits / total_requests * 100) if total_requests > 0 else 0,
            "cache_details": self.cache_stats
        }
    
    def get_slow_operations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent slow operations."""
        return sorted(
            self.slow_operations[-limit:], 
            key=lambda x: x["duration"], 
            reverse=True
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all performance metrics."""
        summary = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "operations": {},
            "cache_stats": self.get_cache_stats(),
            "slow_operations_count": len(self.slow_operations),
            "total_operations": sum(len(metrics) for metrics in self.metrics.values())
        }
        
        for operation in self.metrics.keys():
            summary["operations"][operation] = self.get_operation_stats(operation)
        
        return summary
    
    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile of a list of numbers."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


class CacheManager:
    """In-memory cache manager with TTL support."""
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self.cache:
            entry = self.cache[key]
            if datetime.utcnow() < entry["expires"]:
                performance_metrics.record_cache_hit(key)
                return entry["value"]
            else:
                # Expired, remove from cache
                del self.cache[key]
        
        performance_metrics.record_cache_miss(key)
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl or self.default_ttl
        expires = datetime.utcnow() + timedelta(seconds=ttl)
        
        self.cache[key] = {
            "value": value,
            "expires": expires,
            "created": datetime.utcnow()
        }
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count of removed items."""
        now = datetime.utcnow()
        expired_keys = [
            key for key, entry in self.cache.items() 
            if now >= entry["expires"]
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.utcnow()
        active_entries = sum(
            1 for entry in self.cache.values() 
            if now < entry["expires"]
        )
        
        return {
            "total_entries": len(self.cache),
            "active_entries": active_entries,
            "expired_entries": len(self.cache) - active_entries,
            "memory_usage_estimate": len(str(self.cache))  # Rough estimate
        }


# Global instances
performance_metrics = PerformanceMetrics()
cache_manager = CacheManager()


def monitor_performance(operation_name: str):
    """Decorator to monitor function performance."""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                error = None
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    error = str(e)
                    raise
                finally:
                    duration = time.time() - start_time
                    performance_metrics.record_operation(
                        operation_name, 
                        duration, 
                        success,
                        {"error": error} if error else None
                    )
            
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                error = None
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    error = str(e)
                    raise
                finally:
                    duration = time.time() - start_time
                    performance_metrics.record_operation(
                        operation_name, 
                        duration, 
                        success,
                        {"error": error} if error else None
                    )
            
            return sync_wrapper
    
    return decorator


@asynccontextmanager
async def performance_context(operation_name: str, metadata: Optional[Dict[str, Any]] = None):
    """Context manager for monitoring performance."""
    start_time = time.time()
    success = True
    error = None
    
    try:
        yield
    except Exception as e:
        success = False
        error = str(e)
        raise
    finally:
        duration = time.time() - start_time
        final_metadata = metadata or {}
        if error:
            final_metadata["error"] = error
        
        performance_metrics.record_operation(
            operation_name, 
            duration, 
            success,
            final_metadata
        )


def cached(key_func: Callable = None, ttl: int = 300):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = hashlib.md5("|".join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


class AuthPerformanceOptimizer:
    """Authentication-specific performance optimizations."""
    
    @staticmethod
    @monitor_performance("password_hash")
    def optimize_password_hashing(password: str) -> str:
        """Optimized password hashing with performance monitoring."""
        from ..services.password_service import password_service
        return password_service.hash_password(password)
    
    @staticmethod
    @monitor_performance("jwt_create")
    def optimize_jwt_creation(payload: Dict[str, Any]) -> str:
        """Optimized JWT creation with performance monitoring."""
        from ..services.jwt_service import jwt_service
        return jwt_service.create_token(payload)
    
    @staticmethod
    @monitor_performance("jwt_verify")
    def optimize_jwt_verification(token: str) -> Dict[str, Any]:
        """Optimized JWT verification with performance monitoring."""
        from ..services.jwt_service import jwt_service
        return jwt_service.verify_token(token)
    
    @staticmethod
    @cached(ttl=300)  # Cache user data for 5 minutes
    @monitor_performance("user_lookup")
    async def optimize_user_lookup(user_id: str) -> Optional[Dict[str, Any]]:
        """Optimized user lookup with caching."""
        from ..services.dynamodb import db_service
        return await db_service.get_user_by_id(user_id)
    
    @staticmethod
    @cached(ttl=600)  # Cache user by email for 10 minutes
    @monitor_performance("user_email_lookup")
    async def optimize_user_email_lookup(email: str) -> Optional[Dict[str, Any]]:
        """Optimized user email lookup with caching."""
        from ..services.dynamodb import db_service
        return await db_service.get_user_by_email(email)


# Background task to cleanup expired cache entries
async def cache_cleanup_task():
    """Background task to cleanup expired cache entries."""
    while True:
        try:
            removed_count = cache_manager.cleanup_expired()
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} expired cache entries")
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
        
        # Run cleanup every 5 minutes
        await asyncio.sleep(300)


# Performance monitoring endpoints
def get_performance_report() -> Dict[str, Any]:
    """Get comprehensive performance report."""
    return {
        "performance_metrics": performance_metrics.get_summary(),
        "cache_stats": cache_manager.get_stats(),
        "slow_operations": performance_metrics.get_slow_operations(20),
        "recommendations": generate_performance_recommendations()
    }


def generate_performance_recommendations() -> List[Dict[str, str]]:
    """Generate performance optimization recommendations."""
    recommendations = []
    
    # Check for slow operations
    slow_ops = performance_metrics.get_slow_operations(10)
    if slow_ops:
        recommendations.append({
            "type": "slow_operations",
            "message": f"Found {len(slow_ops)} slow operations. Consider optimizing these endpoints.",
            "action": "Review slow operations and implement caching or optimization"
        })
    
    # Check cache hit rate
    cache_stats = cache_manager.get_stats()
    if cache_stats["total_entries"] > 0:
        cache_perf_stats = performance_metrics.get_cache_stats()
        if cache_perf_stats["hit_rate"] < 70:
            recommendations.append({
                "type": "low_cache_hit_rate",
                "message": f"Cache hit rate is {cache_perf_stats['hit_rate']:.1f}%. Consider increasing TTL or improving cache keys.",
                "action": "Analyze cache usage patterns and optimize caching strategy"
            })
    
    # Check for high error rates
    for operation, stats in performance_metrics.get_summary()["operations"].items():
        if stats.get("success_rate", 100) < 95:
            recommendations.append({
                "type": "high_error_rate",
                "message": f"Operation '{operation}' has {stats['success_rate']:.1f}% success rate.",
                "action": "Investigate and fix errors in this operation"
            })
    
    return recommendations


# Startup function to initialize performance monitoring
def initialize_performance_monitoring():
    """Initialize performance monitoring system."""
    logger.info("Initializing performance monitoring system...")
    
    # Start cache cleanup task
    asyncio.create_task(cache_cleanup_task())
    
    logger.info("Performance monitoring system initialized")


# Export optimized functions for use in authentication flows
auth_optimizer = AuthPerformanceOptimizer()