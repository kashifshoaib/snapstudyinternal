#!/usr/bin/env python3
"""
Test script to verify the throttling fix is working.

This script sends the same request that was causing throttling and monitors
the response to ensure the coordinator is working properly.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_chat_request(session: aiohttp.ClientSession, api_url: str) -> dict:
    """Test the chat request that was causing throttling."""
    try:
        start_time = time.time()
        
        payload = {
            "message": "What are AI Agents?",
            "session_id": f"test_{int(time.time())}"
        }
        
        async with session.post(
            f"{api_url}/api/v1/chat/message",
            json=payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            response_time = time.time() - start_time
            
            if response.status == 200:
                data = await response.json()
                return {
                    'status': 'success',
                    'response_time': response_time,
                    'response_length': len(str(data))
                }
            else:
                text = await response.text()
                return {
                    'status': 'failed',
                    'status_code': response.status,
                    'response_time': response_time,
                    'error': text
                }
                
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'response_time': time.time() - start_time
        }


async def check_throttling_status(session: aiohttp.ClientSession, api_url: str) -> dict:
    """Check the current throttling status."""
    try:
        async with session.get(f"{api_url}/api/v1/health/throttling-status") as response:
            if response.status == 200:
                return await response.json()
            else:
                return {'error': f'Status check failed: {response.status}'}
    except Exception as e:
        return {'error': str(e)}


async def main():
    """Main test function."""
    api_url = "http://localhost:8000"
    
    logger.info("🧪 Starting throttling fix test...")
    
    async with aiohttp.ClientSession() as session:
        # First, check initial status
        logger.info("📊 Checking initial throttling status...")
        initial_status = await check_throttling_status(session, api_url)
        
        if 'coordinator' in initial_status:
            coordinator_stats = initial_status['coordinator']
            logger.info(f"📈 Coordinator stats: {coordinator_stats}")
        else:
            logger.warning("⚠️  Could not get coordinator status")
        
        # Test multiple requests to see if throttling is prevented
        logger.info("🚀 Testing multiple chat requests...")
        
        results = []
        for i in range(5):
            logger.info(f"📤 Sending request {i+1}/5...")
            
            result = await test_chat_request(session, api_url)
            results.append(result)
            
            logger.info(f"📥 Request {i+1} result: {result['status']} "
                       f"({result.get('response_time', 0):.2f}s)")
            
            # Check status after each request
            if i % 2 == 0:  # Check every other request
                status = await check_throttling_status(session, api_url)
                if 'coordinator' in status:
                    stats = status['coordinator']
                    logger.info(f"📊 Coordinator: {stats['total_requests']} requests, "
                               f"{stats['throttled_requests']} throttled, "
                               f"interval: {stats['current_min_interval']:.2f}s")
        
        # Final status check
        logger.info("📊 Checking final throttling status...")
        final_status = await check_throttling_status(session, api_url)
        
        # Analyze results
        logger.info("\n" + "="*60)
        logger.info("🔍 TEST RESULTS ANALYSIS")
        logger.info("="*60)
        
        successful_requests = sum(1 for r in results if r['status'] == 'success')
        failed_requests = sum(1 for r in results if r['status'] == 'failed')
        error_requests = sum(1 for r in results if r['status'] == 'error')
        
        avg_response_time = sum(r.get('response_time', 0) for r in results) / len(results)
        
        logger.info(f"✅ Successful requests: {successful_requests}/5")
        logger.info(f"❌ Failed requests: {failed_requests}/5")
        logger.info(f"🚫 Error requests: {error_requests}/5")
        logger.info(f"⏱️  Average response time: {avg_response_time:.2f}s")
        
        if 'coordinator' in final_status:
            final_stats = final_status['coordinator']
            logger.info(f"📈 Total coordinator requests: {final_stats['total_requests']}")
            logger.info(f"🚫 Throttled requests: {final_stats['throttled_requests']}")
            logger.info(f"📊 Throttle rate: {final_stats['throttle_rate']:.1f}%")
            logger.info(f"⏰ Current interval: {final_stats['current_min_interval']:.2f}s")
        
        # Recommendations
        logger.info("\n🎯 RECOMMENDATIONS:")
        
        if successful_requests == 5 and final_status.get('coordinator', {}).get('throttled_requests', 0) == 0:
            logger.info("🎉 EXCELLENT! No throttling detected. The fix is working!")
        elif successful_requests >= 4:
            logger.info("✅ GOOD! Most requests succeeded. Minor throttling may still occur.")
        elif successful_requests >= 2:
            logger.info("⚠️  PARTIAL SUCCESS. Some throttling still occurring.")
            logger.info("   Consider increasing the minimum request interval.")
        else:
            logger.info("❌ POOR RESULTS. Throttling fix may not be working properly.")
            logger.info("   Check logs for errors and consider manual interval adjustment.")
        
        # Show how to adjust if needed
        if final_status.get('coordinator', {}).get('throttled_requests', 0) > 0:
            logger.info("\n🔧 To manually adjust the request interval:")
            logger.info(f"   curl -X POST {api_url}/api/v1/health/adjust-throttling?interval_seconds=3.0")


if __name__ == "__main__":
    asyncio.run(main())