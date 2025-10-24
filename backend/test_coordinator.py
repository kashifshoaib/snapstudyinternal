#!/usr/bin/env python3
"""
Test the coordinator directly to ensure it's working.
"""

import asyncio
import sys
import os
import time
import logging

# Add the backend src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.bedrock_coordinator import bedrock_coordinator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def mock_bedrock_call(call_type: str, delay: float = 0.1):
    """Mock a Bedrock call that takes some time."""
    logger.info(f"🔄 Starting mock {call_type} call...")
    await asyncio.sleep(delay)
    logger.info(f"✅ Mock {call_type} call completed")
    return f"Mock {call_type} response"


async def test_coordinator():
    """Test the coordinator with multiple calls."""
    logger.info("🧪 Testing Bedrock Coordinator...")
    
    # Get initial stats
    initial_stats = bedrock_coordinator.get_stats()
    logger.info(f"📊 Initial stats: {initial_stats}")
    
    # Test multiple calls
    tasks = []
    
    # Create 3 agent calls and 2 model calls
    for i in range(3):
        task = bedrock_coordinator.execute_bedrock_request(
            'agent', 
            mock_bedrock_call, 
            f'agent_{i}', 
            0.1
        )
        tasks.append(task)
    
    for i in range(2):
        task = bedrock_coordinator.execute_bedrock_request(
            'model', 
            mock_bedrock_call, 
            f'model_{i}', 
            0.1
        )
        tasks.append(task)
    
    # Execute all calls
    start_time = time.time()
    results = await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    # Get final stats
    final_stats = bedrock_coordinator.get_stats()
    
    logger.info(f"⏱️  Total execution time: {total_time:.2f}s")
    logger.info(f"📊 Final stats: {final_stats}")
    
    # Analyze results
    expected_min_time = (len(tasks) - 1) * final_stats['current_min_interval']
    
    logger.info("\n🔍 ANALYSIS:")
    logger.info(f"   Expected minimum time: {expected_min_time:.2f}s")
    logger.info(f"   Actual time: {total_time:.2f}s")
    logger.info(f"   Requests processed: {final_stats['total_requests'] - initial_stats['total_requests']}")
    
    if total_time >= expected_min_time * 0.9:  # Allow 10% tolerance
        logger.info("✅ Coordinator is working correctly - requests were properly spaced")
    else:
        logger.warning("⚠️  Coordinator may not be working - requests completed too quickly")
    
    return results


async def test_throttling_simulation():
    """Test coordinator with simulated throttling."""
    logger.info("\n🚫 Testing throttling simulation...")
    
    async def mock_throttled_call():
        """Mock a call that throws throttling exception."""
        raise Exception("throttlingException: Your request rate is too high")
    
    try:
        await bedrock_coordinator.execute_bedrock_request('agent', mock_throttled_call)
    except Exception as e:
        logger.info(f"✅ Caught expected throttling error: {e}")
    
    # Check if interval was increased
    stats = bedrock_coordinator.get_stats()
    logger.info(f"📊 Stats after throttling: {stats}")
    
    if stats['current_min_interval'] > 6.0:
        logger.info("✅ Coordinator increased interval after throttling")
    else:
        logger.warning("⚠️  Coordinator did not increase interval after throttling")


async def main():
    """Main test function."""
    logger.info("🚀 BEDROCK COORDINATOR TEST")
    logger.info("="*50)
    
    try:
        # Test normal operation
        await test_coordinator()
        
        # Test throttling response
        await test_throttling_simulation()
        
        logger.info("\n🎯 CONCLUSION:")
        logger.info("If you see proper spacing and interval increases, the coordinator is working.")
        logger.info("If throttling still occurs in your app, check that all Bedrock calls use the coordinator.")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())