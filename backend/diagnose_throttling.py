#!/usr/bin/env python3
"""
Diagnose throttling issues by checking AWS quotas and testing requests.
"""

import boto3
import asyncio
import time
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_aws_quotas():
    """Check actual AWS Bedrock quotas."""
    try:
        # Check Service Quotas
        quotas_client = boto3.client('service-quotas', region_name='us-east-1')
        
        logger.info("🔍 Checking AWS Bedrock quotas...")
        
        # List Bedrock quotas
        try:
            response = quotas_client.list_service_quotas(ServiceCode='bedrock')
            
            for quota in response.get('Quotas', []):
                quota_name = quota.get('QuotaName', '')
                if 'request' in quota_name.lower() or 'token' in quota_name.lower():
                    logger.info(f"📊 {quota_name}: {quota.get('Value', 'N/A')}")
                    
        except Exception as e:
            logger.warning(f"⚠️  Could not retrieve quotas: {e}")
            
    except Exception as e:
        logger.error(f"❌ Error checking quotas: {e}")


def check_bedrock_models():
    """Check available Bedrock models."""
    try:
        bedrock_client = boto3.client('bedrock', region_name='us-east-1')
        
        logger.info("🤖 Checking available Bedrock models...")
        
        response = bedrock_client.list_foundation_models()
        
        claude_models = [
            model for model in response.get('modelSummaries', [])
            if 'claude' in model.get('modelId', '').lower()
        ]
        
        logger.info(f"📋 Found {len(claude_models)} Claude models:")
        for model in claude_models[:5]:  # Show first 5
            logger.info(f"   - {model.get('modelId')}")
            
    except Exception as e:
        logger.error(f"❌ Error checking models: {e}")


def test_direct_bedrock_call():
    """Test a direct Bedrock call to see raw throttling behavior."""
    try:
        bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        logger.info("🧪 Testing direct Bedrock model call...")
        
        body = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": "Hello"}]
                }
            ]
        }
        
        start_time = time.time()
        
        response = bedrock_client.invoke_model(
            modelId="amazon.nova-micro-v1:0",
            body=json.dumps(body),
            contentType='application/json'
        )
        
        response_time = time.time() - start_time
        
        response_body = json.loads(response['body'].read())
        
        logger.info(f"✅ Direct call succeeded in {response_time:.2f}s")
        logger.info(f"📝 Response: {response_body.get('content', [{}])[0].get('text', '')[:50]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Direct call failed: {e}")
        return False


def test_bedrock_agent_call():
    """Test a direct Bedrock agent call."""
    try:
        agent_client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')
        
        logger.info("🤖 Testing direct Bedrock agent call...")
        
        # Use the learning agent ID from environment
        import os
        agent_id = os.getenv('LEARNING_AGENT_ID', 'YSEVVJCGLP')
        
        if not agent_id or agent_id == 'YSEVVJCGLP':
            logger.warning("⚠️  Using default agent ID - may not work")
        
        start_time = time.time()
        
        response = agent_client.invoke_agent(
            agentId=agent_id,
            agentAliasId='TSTALIASID',
            sessionId=f'test_{int(time.time())}',
            inputText='Hello, what are AI agents?'
        )
        
        response_time = time.time() - start_time
        
        # Process streaming response
        completion = ""
        for event in response.get('completion', []):
            if 'chunk' in event:
                chunk_bytes = event['chunk'].get('bytes', b'')
                completion += chunk_bytes.decode('utf-8')
        
        logger.info(f"✅ Agent call succeeded in {response_time:.2f}s")
        logger.info(f"📝 Response: {completion[:100]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Agent call failed: {e}")
        return False


async def test_rapid_calls():
    """Test rapid calls to see throttling behavior."""
    logger.info("⚡ Testing rapid calls to trigger throttling...")
    
    success_count = 0
    throttle_count = 0
    
    for i in range(3):
        logger.info(f"📤 Rapid call {i+1}/3...")
        
        try:
            if test_direct_bedrock_call():
                success_count += 1
            else:
                throttle_count += 1
        except Exception as e:
            if 'throttl' in str(e).lower():
                throttle_count += 1
                logger.warning(f"🚫 Call {i+1} throttled: {e}")
            else:
                logger.error(f"❌ Call {i+1} failed: {e}")
        
        # Very short delay to trigger throttling
        await asyncio.sleep(0.1)
    
    logger.info(f"📊 Rapid test results: {success_count} success, {throttle_count} throttled")
    
    if throttle_count > 0:
        logger.warning("⚠️  Throttling detected with rapid calls - this confirms the issue")
    else:
        logger.info("✅ No throttling with rapid calls - quotas may be higher than expected")


def main():
    """Main diagnostic function."""
    logger.info("🔍 BEDROCK THROTTLING DIAGNOSTICS")
    logger.info("="*50)
    
    # Check AWS credentials
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        logger.info(f"🔐 AWS Account: {identity.get('Account')}")
        logger.info(f"👤 User/Role: {identity.get('Arn', '').split('/')[-1]}")
    except Exception as e:
        logger.error(f"❌ AWS credentials issue: {e}")
        return
    
    print()
    
    # Check quotas
    check_aws_quotas()
    print()
    
    # Check models
    check_bedrock_models()
    print()
    
    # Test single calls
    logger.info("🧪 Testing single Bedrock calls...")
    model_works = test_direct_bedrock_call()
    print()
    
    agent_works = test_bedrock_agent_call()
    print()
    
    # Test rapid calls if single calls work
    if model_works:
        asyncio.run(test_rapid_calls())
    
    print()
    logger.info("🎯 RECOMMENDATIONS:")
    
    if not model_works and not agent_works:
        logger.error("❌ Both model and agent calls failed - check AWS permissions and region")
    elif not model_works:
        logger.warning("⚠️  Model calls failed but agent works - check model permissions")
    elif not agent_works:
        logger.warning("⚠️  Agent calls failed but model works - check agent configuration")
    else:
        logger.info("✅ Both model and agent calls work individually")
        logger.info("💡 The issue is likely rapid sequential calls in your application")
        logger.info("🔧 The coordinator should fix this by spacing requests 6+ seconds apart")


if __name__ == "__main__":
    main()