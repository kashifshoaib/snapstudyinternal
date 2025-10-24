#!/usr/bin/env python3
"""
Bedrock Throttling Monitor

Monitor and analyze Bedrock API throttling patterns to optimize request rates.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ThrottlingMonitor:
    """Monitor Bedrock API throttling and performance."""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.session = None
        self.metrics = {
            'requests_sent': 0,
            'successful_requests': 0,
            'throttled_requests': 0,
            'failed_requests': 0,
            'average_response_time': 0.0,
            'response_times': []
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def check_health_status(self) -> Dict[str, Any]:
        """Check current health and throttling status."""
        try:
            start_time = time.time()
            
            async with self.session.get(f"{self.api_base_url}/api/v1/health/throttling-status") as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    self.metrics['successful_requests'] += 1
                    self.metrics['response_times'].append(response_time)
                    return data
                else:
                    self.metrics['failed_requests'] += 1
                    logger.error(f"Health check failed with status {response.status}")
                    return {}
                    
        except Exception as e:
            self.metrics['failed_requests'] += 1
            logger.error(f"Health check error: {e}")
            return {}
        finally:
            self.metrics['requests_sent'] += 1
    
    async def test_chat_endpoint(self, message: str = "What are AI Agents?") -> Dict[str, Any]:
        """Test the chat endpoint that was experiencing throttling."""
        try:
            start_time = time.time()
            
            payload = {
                "message": message,
                "session_id": f"monitor_{int(time.time())}"
            }
            
            async with self.session.post(
                f"{self.api_base_url}/api/v1/chat/message",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    self.metrics['successful_requests'] += 1
                    self.metrics['response_times'].append(response_time)
                    return {
                        'status': 'success',
                        'response_time': response_time,
                        'data': data
                    }
                elif response.status == 429:  # Too Many Requests
                    self.metrics['throttled_requests'] += 1
                    logger.warning(f"Chat request throttled (429) - response time: {response_time:.2f}s")
                    return {
                        'status': 'throttled',
                        'response_time': response_time,
                        'status_code': 429
                    }
                else:
                    self.metrics['failed_requests'] += 1
                    logger.error(f"Chat request failed with status {response.status}")
                    return {
                        'status': 'failed',
                        'response_time': response_time,
                        'status_code': response.status
                    }
                    
        except Exception as e:
            self.metrics['failed_requests'] += 1
            logger.error(f"Chat request error: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
        finally:
            self.metrics['requests_sent'] += 1
    
    async def run_load_test(self, duration_seconds: int = 300, requests_per_minute: int = 20):
        """Run a load test to identify throttling patterns."""
        logger.info(f"Starting load test: {duration_seconds}s duration, {requests_per_minute} req/min")
        
        request_interval = 60.0 / requests_per_minute  # seconds between requests
        end_time = time.time() + duration_seconds
        
        test_messages = [
            "What are AI Agents?",
            "Explain machine learning",
            "How does adaptive learning work?",
            "What is natural language processing?",
            "Tell me about neural networks"
        ]
        
        message_index = 0
        
        while time.time() < end_time:
            # Test chat endpoint
            message = test_messages[message_index % len(test_messages)]
            result = await self.test_chat_endpoint(message)
            
            # Log result
            logger.info(f"Request {self.metrics['requests_sent']}: {result.get('status')} "
                       f"({result.get('response_time', 0):.2f}s)")
            
            # Check health status every 10 requests
            if self.metrics['requests_sent'] % 10 == 0:
                health_status = await self.check_health_status()
                if health_status:
                    logger.info(f"Health check: {health_status.get('services', {})}")
            
            message_index += 1
            
            # Wait for next request
            await asyncio.sleep(request_interval)
        
        # Calculate final metrics
        self._calculate_final_metrics()
        
        logger.info("Load test completed")
        self.print_summary()
    
    def _calculate_final_metrics(self):
        """Calculate final performance metrics."""
        if self.metrics['response_times']:
            self.metrics['average_response_time'] = sum(self.metrics['response_times']) / len(self.metrics['response_times'])
            self.metrics['min_response_time'] = min(self.metrics['response_times'])
            self.metrics['max_response_time'] = max(self.metrics['response_times'])
        
        if self.metrics['requests_sent'] > 0:
            self.metrics['success_rate'] = (self.metrics['successful_requests'] / self.metrics['requests_sent']) * 100
            self.metrics['throttle_rate'] = (self.metrics['throttled_requests'] / self.metrics['requests_sent']) * 100
            self.metrics['failure_rate'] = (self.metrics['failed_requests'] / self.metrics['requests_sent']) * 100
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("BEDROCK THROTTLING MONITOR - TEST SUMMARY")
        print("="*60)
        print(f"Total Requests Sent:     {self.metrics['requests_sent']}")
        print(f"Successful Requests:     {self.metrics['successful_requests']}")
        print(f"Throttled Requests:      {self.metrics['throttled_requests']}")
        print(f"Failed Requests:         {self.metrics['failed_requests']}")
        print(f"Success Rate:            {self.metrics.get('success_rate', 0):.1f}%")
        print(f"Throttle Rate:           {self.metrics.get('throttle_rate', 0):.1f}%")
        print(f"Failure Rate:            {self.metrics.get('failure_rate', 0):.1f}%")
        print(f"Average Response Time:   {self.metrics.get('average_response_time', 0):.2f}s")
        print(f"Min Response Time:       {self.metrics.get('min_response_time', 0):.2f}s")
        print(f"Max Response Time:       {self.metrics.get('max_response_time', 0):.2f}s")
        print("="*60)
        
        # Recommendations
        print("\nRECOMMENDATIONS:")
        if self.metrics.get('throttle_rate', 0) > 10:
            print("⚠️  High throttling rate detected!")
            print("   - Reduce request rate in production")
            print("   - Implement longer delays between requests")
            print("   - Consider request queuing")
        
        if self.metrics.get('average_response_time', 0) > 10:
            print("⚠️  High average response time!")
            print("   - Check circuit breaker status")
            print("   - Monitor AWS service health")
            print("   - Consider timeout adjustments")
        
        if self.metrics.get('success_rate', 0) < 90:
            print("⚠️  Low success rate!")
            print("   - Check error logs for patterns")
            print("   - Verify AWS credentials and permissions")
            print("   - Monitor service quotas")
        
        if (self.metrics.get('throttle_rate', 0) < 5 and 
            self.metrics.get('success_rate', 0) > 95):
            print("✅ System performing well!")
            print("   - Current rate limits are appropriate")
            print("   - Consider gradual rate increase if needed")


async def main():
    """Main monitoring function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor Bedrock API throttling")
    parser.add_argument("--duration", type=int, default=300, help="Test duration in seconds")
    parser.add_argument("--rate", type=int, default=20, help="Requests per minute")
    parser.add_argument("--url", type=str, default="http://localhost:8000", help="API base URL")
    
    args = parser.parse_args()
    
    async with ThrottlingMonitor(args.url) as monitor:
        # First, check current status
        logger.info("Checking current system status...")
        health_status = await monitor.check_health_status()
        
        if health_status:
            print("\nCurrent System Status:")
            print(json.dumps(health_status, indent=2))
        
        # Run load test
        await monitor.run_load_test(args.duration, args.rate)


if __name__ == "__main__":
    asyncio.run(main())