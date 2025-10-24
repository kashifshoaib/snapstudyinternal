"""
Health check endpoints for monitoring Bedrock service status.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

from ...utils.rate_limiter import bedrock_rate_limiter
from ...utils.circuit_breaker import bedrock_circuit_breakers
from ...utils.request_queue import get_bedrock_request_queue
from ...utils.bedrock_coordinator import bedrock_coordinator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """Basic health check."""
    return {
        "status": "healthy",
        "service": "snapstudy-backend",
        "timestamp": "2024-10-23T03:20:00Z"
    }


@router.get("/bedrock")
async def bedrock_health() -> Dict[str, Any]:
    """Detailed Bedrock service health check."""
    try:
        # Get circuit breaker status
        circuit_status = bedrock_circuit_breakers.get_status()
        
        # Get queue statistics
        queue_stats = get_bedrock_request_queue().get_stats()
        
        # Determine overall health
        agent_healthy = circuit_status['agent_breaker']['state'] != 'open'
        model_healthy = circuit_status['model_breaker']['state'] != 'open'
        queue_healthy = (queue_stats['agent_queue_size'] < 10 and 
                        queue_stats['model_queue_size'] < 10)
        
        overall_healthy = agent_healthy and model_healthy and queue_healthy
        
        return {
            "status": "healthy" if overall_healthy else "degraded",
            "timestamp": "2024-10-23T03:20:00Z",
            "services": {
                "bedrock_agents": {
                    "status": "healthy" if agent_healthy else "unhealthy",
                    "circuit_breaker": circuit_status['agent_breaker']
                },
                "bedrock_models": {
                    "status": "healthy" if model_healthy else "unhealthy",
                    "circuit_breaker": circuit_status['model_breaker']
                },
                "request_queue": {
                    "status": "healthy" if queue_healthy else "overloaded",
                    "statistics": queue_stats
                }
            },
            "recommendations": _get_health_recommendations(
                circuit_status, queue_stats
            )
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


def _get_health_recommendations(
    circuit_status: Dict[str, Any], 
    queue_stats: Dict[str, Any]
) -> list:
    """Generate health recommendations based on current status."""
    recommendations = []
    
    # Circuit breaker recommendations
    if circuit_status['agent_breaker']['state'] == 'open':
        recommendations.append(
            "Bedrock Agents circuit breaker is OPEN - reduce agent request rate"
        )
    
    if circuit_status['model_breaker']['state'] == 'open':
        recommendations.append(
            "Bedrock Models circuit breaker is OPEN - reduce model request rate"
        )
    
    # Queue recommendations
    if queue_stats['agent_queue_size'] > 5:
        recommendations.append(
            f"Agent queue is backed up ({queue_stats['agent_queue_size']} requests) - "
            "consider increasing processing delay"
        )
    
    if queue_stats['model_queue_size'] > 5:
        recommendations.append(
            f"Model queue is backed up ({queue_stats['model_queue_size']} requests) - "
            "consider increasing processing delay"
        )
    
    # Performance recommendations
    avg_wait_time = (queue_stats['total_wait_time'] / 
                    max(1, queue_stats['agent_requests_processed'] + 
                        queue_stats['model_requests_processed']))
    
    if avg_wait_time > 5.0:
        recommendations.append(
            f"High average wait time ({avg_wait_time:.1f}s) - "
            "consider optimizing request patterns"
        )
    
    if not recommendations:
        recommendations.append("All systems operating normally")
    
    return recommendations


@router.get("/throttling-status")
async def throttling_status() -> Dict[str, Any]:
    """Get current throttling and rate limiting status."""
    return {
        "coordinator": bedrock_coordinator.get_stats(),
        "rate_limiting": {
            "agent_limiter": {
                "tokens_available": bedrock_rate_limiter.agent_limiter.tokens,
                "capacity": bedrock_rate_limiter.agent_limiter.config.burst_capacity,
                "refill_rate": bedrock_rate_limiter.agent_limiter.config.refill_rate
            },
            "model_limiter": {
                "tokens_available": bedrock_rate_limiter.model_limiter.tokens,
                "capacity": bedrock_rate_limiter.model_limiter.config.burst_capacity,
                "refill_rate": bedrock_rate_limiter.model_limiter.config.refill_rate
            }
        },
        "circuit_breakers": bedrock_circuit_breakers.get_status(),
        "request_queue": get_bedrock_request_queue().get_stats()
    }


@router.post("/adjust-throttling")
async def adjust_throttling(interval_seconds: float) -> Dict[str, Any]:
    """Manually adjust the Bedrock request interval."""
    try:
        bedrock_coordinator.adjust_interval(interval_seconds)
        return {
            "status": "success",
            "message": f"Adjusted minimum request interval to {interval_seconds}s",
            "current_stats": bedrock_coordinator.get_stats()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))