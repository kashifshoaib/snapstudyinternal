#!/usr/bin/env python3
"""
Test the chat endpoint with authentication.
"""

import requests
import json
import time

def test_chat_with_auth():
    """Test chat endpoint with proper authentication."""
    
    base_url = "https://1w0yyb3an4.execute-api.us-east-1.amazonaws.com/prod"
    
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://d334lncig0w4ow.cloudfront.net"
    }
    
    print("🧪 Testing Chat with Authentication")
    print("=" * 50)
    
    # Step 1: Login to get auth token
    print("🔐 Step 1: Logging in...")
    login_data = {
        "email": "m1@gmail.com",
        "password": "m1@gmail.com"
    }
    
    try:
        login_response = requests.post(
            f"{base_url}/api/v1/auth/login",
            json=login_data,
            headers=headers,
            timeout=30
        )
        
        print(f"   Login Status: {login_response.status_code}")
        
        if login_response.status_code == 200:
            login_result = login_response.json()
            access_token = login_result.get('access_token')
            print(f"   ✅ Login successful, got token: {access_token[:20]}...")
            
            # Step 2: Test chat with auth token
            print("\n💬 Step 2: Testing chat with auth token...")
            
            chat_headers = {
                **headers,
                "Authorization": f"Bearer {access_token}"
            }
            
            chat_data = {
                "message": "hi",
                "session_id": None,
                "lesson_id": None
            }
            
            print(f"   📤 Sending: {json.dumps(chat_data, indent=2)}")
            
            start_time = time.time()
            
            chat_response = requests.post(
                f"{base_url}/api/v1/chat/message",
                json=chat_data,
                headers=chat_headers,
                timeout=60
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            print(f"   ⏱️ Response time: {response_time:.2f}s")
            print(f"   📊 Status Code: {chat_response.status_code}")
            
            if chat_response.status_code == 200:
                try:
                    chat_result = chat_response.json()
                    print(f"   ✅ Chat Response: {json.dumps(chat_result, indent=2)}")
                except json.JSONDecodeError:
                    print(f"   ❌ Invalid JSON: {chat_response.text}")
            else:
                print(f"   ❌ Chat Error: {chat_response.text}")
                
        else:
            print(f"   ❌ Login failed: {login_response.text}")
            
    except requests.exceptions.Timeout:
        print("   ⏰ Request timed out")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def test_chat_without_auth():
    """Test chat endpoint without authentication (should work for anonymous)."""
    
    base_url = "https://1w0yyb3an4.execute-api.us-east-1.amazonaws.com/prod"
    
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://d334lncig0w4ow.cloudfront.net"
    }
    
    print("\n🔓 Testing Chat without Authentication")
    print("=" * 50)
    
    chat_data = {
        "message": "hello",
        "session_id": None,
        "lesson_id": None
    }
    
    try:
        print(f"📤 Sending: {json.dumps(chat_data, indent=2)}")
        
        start_time = time.time()
        
        response = requests.post(
            f"{base_url}/api/v1/chat/message",
            json=chat_data,
            headers=headers,
            timeout=60
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        print(f"⏱️ Response time: {response_time:.2f}s")
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"✅ Response: {json.dumps(result, indent=2)}")
            except json.JSONDecodeError:
                print(f"❌ Invalid JSON: {response.text}")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_cors_preflight():
    """Test CORS preflight for chat endpoint."""
    
    base_url = "https://1w0yyb3an4.execute-api.us-east-1.amazonaws.com/prod"
    
    print("\n🌐 Testing CORS Preflight")
    print("=" * 50)
    
    headers = {
        "Origin": "https://d334lncig0w4ow.cloudfront.net",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type,authorization"
    }
    
    try:
        response = requests.options(
            f"{base_url}/api/v1/chat/message",
            headers=headers,
            timeout=10
        )
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📋 Response Headers:")
        for key, value in response.headers.items():
            if 'access-control' in key.lower() or 'cors' in key.lower():
                print(f"   {key}: {value}")
                
    except Exception as e:
        print(f"❌ CORS Error: {e}")

if __name__ == "__main__":
    test_cors_preflight()
    test_chat_without_auth()
    test_chat_with_auth()