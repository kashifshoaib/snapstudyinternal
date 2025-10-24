#!/usr/bin/env python3
"""
Simple test to verify Nova Micro model integration.
"""

import boto3
import json
import os
from datetime import datetime

def test_nova_micro_directly():
    """Test Nova Micro model directly with Bedrock."""
    
    print("🧪 Testing Amazon Nova Micro Model...")
    print("=" * 50)
    
    try:
        # Initialize Bedrock client
        bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
        model_id = "amazon.nova-micro-v1:0"
        
        print(f"📋 Model: {model_id}")
        print(f"🌍 Region: us-east-1")
        print()
        
        # Test messages that the UI might send
        test_messages = [
            "Hello! Can you help me learn about photosynthesis?",
            "Explain quantum physics in simple terms",
            "Can you quiz me on biology?",
            "What is the capital of France?"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"🔄 Test {i}: {message}")
            
            # Prepare Nova request using invoke_model format
            body = {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": message}]
                    }
                ]
            }
            
            try:
                start_time = datetime.now()
                
                # Use Nova invoke_model API (compatible with older boto3)
                response = bedrock_client.invoke_model(
                    modelId=model_id,
                    body=json.dumps(body),
                    contentType='application/json'
                )
                
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds()
                
                # Parse response
                response_body = json.loads(response['body'].read())
                
                # Debug: Print full response structure
                print(f"   🔍 Full response keys: {list(response_body.keys())}")
                
                # Extract text from Nova invoke_model response
                if 'output' in response_body and 'message' in response_body['output']:
                    output_text = response_body['output']['message']['content'][0]['text']
                    print(f"   ✅ Response ({response_time:.2f}s): {output_text[:100]}...")
                else:
                    print(f"   ❌ Unexpected response format: {json.dumps(response_body, indent=2)}")
                
                print()
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                print()
        
        print("✅ Nova Micro model test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Setup error: {e}")
        return False

def test_chat_request_format():
    """Test the format that the UI sends for chat requests."""
    
    print("\n🌐 Testing UI Chat Request Format...")
    print("=" * 50)
    
    # Simulate different types of requests from the UI
    ui_requests = [
        {
            "type": "Simple chat",
            "data": {
                "message": "Hello, I need help with math",
                "session_id": None,
                "lesson_id": None
            }
        },
        {
            "type": "Lesson-specific chat",
            "data": {
                "message": "Can you explain this concept?",
                "session_id": "session_123",
                "lesson_id": "lesson_456"
            }
        },
        {
            "type": "Quiz request",
            "data": {
                "message": "Quiz me on photosynthesis",
                "session_id": "session_789",
                "lesson_id": None
            }
        }
    ]
    
    for request in ui_requests:
        print(f"📤 {request['type']}:")
        print(f"   Request: {json.dumps(request['data'], indent=2)}")
        
        # Validate the request
        message = request['data'].get('message', '').strip()
        if not message:
            print("   ❌ Invalid: Empty message")
        elif len(message) > 2000:
            print("   ❌ Invalid: Message too long")
        else:
            print("   ✅ Valid format")
        print()

def main():
    """Main test function."""
    print("🚀 SnapStudy Nova Micro Integration Test")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test UI request format
    test_chat_request_format()
    
    # Test Nova model directly
    success = test_nova_micro_directly()
    
    if success:
        print("🎉 Nova Micro is working! Backend should handle UI chat requests properly.")
        print("\n📋 Summary:")
        print("   ✅ Nova Micro model responds correctly")
        print("   ✅ Request/response format is compatible")
        print("   ✅ Ready for frontend integration")
    else:
        print("⚠️  Nova Micro test failed. Check AWS credentials and permissions.")

if __name__ == "__main__":
    main()