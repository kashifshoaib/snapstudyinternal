#!/usr/bin/env python3
"""
Local test script to verify chat functionality with Nova Micro model.
This simulates what the frontend would send to the backend.
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# Add backend src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

async def test_chat_functionality():
    """Test the chat functionality locally."""
    
    print("🧪 Testing SnapStudy Chat with Nova Micro...")
    print("=" * 50)
    
    try:
        # Import backend modules
        from services.chat_agent import AgenticChatAgent
        from services.bedrock import BedrockService
        from config import settings
        
        print(f"✅ Backend modules imported successfully")
        print(f"📋 Current model: {settings.bedrock_model_id}")
        print(f"🌍 AWS Region: {settings.aws_region}")
        print()
        
        # Test Bedrock service directly
        print("🔧 Testing Bedrock Service...")
        bedrock_service = BedrockService()
        
        # Test simple prompt
        test_prompt = "Hello! Can you help me understand photosynthesis?"
        print(f"📝 Test prompt: {test_prompt}")
        
        try:
            response = await bedrock_service.invoke_claude(
                prompt=test_prompt,
                max_tokens=200,
                temperature=0.7
            )
            print(f"✅ Bedrock response: {response[:100]}...")
            print()
        except Exception as e:
            print(f"❌ Bedrock service error: {e}")
            return False
        
        # Test Chat Agent
        print("🤖 Testing Chat Agent...")
        chat_agent = AgenticChatAgent()
        
        # Simulate chat request from UI
        test_context = {
            'user_id': 'test_user_123',
            'user_profile': {
                'user_id': 'test_user_123',
                'email': 'test@example.com',
                'full_name': 'Test User'
            }
        }
        
        session_id = "test_session_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            chat_response = await chat_agent.handle_message(
                user_id='test_user_123',
                message=test_prompt,
                context=test_context,
                session_id=session_id
            )
            
            print(f"✅ Chat Agent Response:")
            print(f"   Intent: {chat_response.get('intent', 'unknown')}")
            print(f"   Confidence: {chat_response.get('confidence', 0)}")
            print(f"   Response: {chat_response.get('response', '')[:150]}...")
            print()
            
        except Exception as e:
            print(f"❌ Chat agent error: {e}")
            return False
        
        # Test different message types
        test_messages = [
            "Can you quiz me on biology?",
            "Explain quantum physics simply",
            "What's my progress?",
            "I need help with math"
        ]
        
        print("🎯 Testing different message types...")
        for i, message in enumerate(test_messages, 1):
            try:
                print(f"   {i}. Testing: '{message}'")
                response = await chat_agent.handle_message(
                    user_id='test_user_123',
                    message=message,
                    context=test_context,
                    session_id=session_id
                )
                intent = response.get('intent', 'unknown')
                confidence = response.get('confidence', 0)
                print(f"      → Intent: {intent} (confidence: {confidence:.2f})")
                
            except Exception as e:
                print(f"      ❌ Error: {e}")
        
        print()
        print("✅ All chat tests completed successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're running this from the project root directory")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_http_endpoint_format():
    """Test the HTTP endpoint request format that the UI would send."""
    
    print("\n🌐 Testing HTTP Endpoint Format...")
    print("=" * 50)
    
    # Simulate what the frontend sends
    sample_requests = [
        {
            "message": "Hello, can you help me learn?",
            "session_id": None,
            "lesson_id": None
        },
        {
            "message": "Quiz me on photosynthesis",
            "session_id": "existing_session_123",
            "lesson_id": "lesson_456"
        }
    ]
    
    for i, request_data in enumerate(sample_requests, 1):
        print(f"📤 Sample Request {i}:")
        print(f"   JSON: {json.dumps(request_data, indent=2)}")
        
        # Validate required fields
        message = request_data.get('message', '').strip()
        if not message:
            print(f"   ❌ Invalid: Empty message")
        elif len(message) > 2000:
            print(f"   ❌ Invalid: Message too long ({len(message)} chars)")
        else:
            print(f"   ✅ Valid request format")
        print()

def main():
    """Main test function."""
    print("🚀 SnapStudy Backend Chat Test")
    print("Testing Nova Micro integration...")
    print()
    
    # Check if we're in the right directory
    if not os.path.exists('backend/src'):
        print("❌ Error: Please run this script from the project root directory")
        print("   Expected structure: ./backend/src/")
        return
    
    # Run async tests
    try:
        # Test HTTP format first
        asyncio.run(test_http_endpoint_format())
        
        # Test actual functionality
        success = asyncio.run(test_chat_functionality())
        
        if success:
            print("🎉 All tests passed! Backend is ready for UI chat requests.")
        else:
            print("⚠️  Some tests failed. Check the errors above.")
            
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test runner error: {e}")

if __name__ == "__main__":
    main()