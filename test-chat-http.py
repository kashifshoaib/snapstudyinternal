#!/usr/bin/env python3
"""
Test the chat HTTP endpoint directly to see if it's working.
"""

import requests
import json
import time

def test_chat_endpoint():
    """Test the chat HTTP endpoint."""
    
    # Your API Gateway URL
    api_url = "https://1w0yyb3an4.execute-api.us-east-1.amazonaws.com/prod"
    chat_endpoint = f"{api_url}/api/v1/chat/message"
    
    print("🧪 Testing Chat HTTP Endpoint")
    print(f"🌐 URL: {chat_endpoint}")
    print("=" * 50)
    
    # Test message
    test_data = {
        "message": "hi",
        "session_id": None,
        "lesson_id": None
    }
    
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://d334lncig0w4ow.cloudfront.net"
    }
    
    try:
        print(f"📤 Sending: {json.dumps(test_data, indent=2)}")
        print("⏳ Waiting for response...")
        
        start_time = time.time()
        
        response = requests.post(
            chat_endpoint,
            json=test_data,
            headers=headers,
            timeout=60  # 60 second timeout
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        print(f"⏱️ Response time: {response_time:.2f}s")
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                print(f"✅ Response: {json.dumps(response_data, indent=2)}")
            except json.JSONDecodeError:
                print(f"❌ Invalid JSON response: {response.text}")
        else:
            print(f"❌ Error response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out after 60 seconds")
    except requests.exceptions.ConnectionError as e:
        print(f"🔌 Connection error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_chat_endpoint()