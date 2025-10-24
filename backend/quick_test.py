#!/usr/bin/env python3
"""
Quick test to verify the throttling fix is working.
"""

import asyncio
import aiohttp
import json
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_chat_endpoint():
    """Test the chat endpoint that was experiencing throttling."""
    
    async with aiohttp.ClientSession() as session:
        logger.info("🧪 Testing chat endpoint...")
        
        payload = {
            "message": "What are AI Agents?",
            "session_id": f"test_{int(time.time())}"
        }
        
        try:
            start_time = time.time()
            
            async with session.post(
                "http://localhost:8000/api/v1/chat/message",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Success! Response time: {response_time:.2f}s")
                    logger.info(f"📝 Response: {data.get('response', '')[:100]}...")
                    return True
                else:
                    text = await response.text()
                    logger.error(f"❌ Failed with status {response.status}: {text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return False


async def check_coordinator_status():
    """Check the coordinator status."""
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:8000/api/v1/health/throttling-status") as response:
                if response.status == 200:
                    data = await response.json()
                    coordinator = data.get('coordinator', {})
                    
                    logger.info("📊 Coordinator Status:")
                    logger.info(f"   Total requests: {coordinator.get('total_requests', 0)}")
                    logger.info(f"   Throttled requests: {coordinator.get('throttled_requests', 0)}")
                    logger.info(f"   Throttle rate: {coordinator.get('throttle_rate', 0):.1f}%")
                    logger.info(f"   Current interval: {coordinator.get('current_min_interval', 0):.2f}s")
                    
                    return coordinator.get('throttled_requests', 0) == 0
                else:
                    logger.error(f"❌ Status check failed: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Status check error: {e}")
            return False


async def main():
    """Main test function."""
    logger.info("🚀 Starting quick throttling test...")
    
    # Test multiple requests
    success_count = 0
    total_tests = 3
    
    for i in range(total_tests):
        logger.info(f"📤 Test {i+1}/{total_tests}")
        
        if await test_chat_endpoint():
            success_count += 1
        
        # Check status after each test
        await check_coordinator_status()
        
        # Wait between tests
        if i < total_tests - 1:
            logger.info("⏳ Waiting 3 seconds...")
            await asyncio.sleep(3)
    
    # Final results
    logger.info("\n" + "="*50)
    logger.info("🔍 QUICK TEST RESULTS")
    logger.info("="*50)
    logger.info(f"✅ Successful tests: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        logger.info("🎉 All tests passed! Throttling fix appears to be working.")
    elif success_count > 0:
        logger.info("⚠️  Partial success. Some throttling may still occur.")
    else:
        logger.info("❌ All tests failed. Check server logs for errors.")
    
    # Final status check
    await check_coordinator_status()


if __name__ == "__main__":
    asyncio.run(main())