#!/usr/bin/env python3
"""
Test different API routes to see which ones work.
"""

import requests
import json

def test_routes():
    """Test various API routes."""
    
    base_url = "https://1w0yyb3an4.execute-api.us-east-1.amazonaws.com/prod"
    
    routes_to_test = [
        "/",
        "/health", 
        "/api/v1/health",
        "/api/v1/auth/login",
        "/api/v1/chat/message"
    ]
    
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://d334lncig0w4ow.cloudfront.net"
    }
    
    print("🧪 Testing API Routes")
    print("=" * 50)
    
    for route in routes_to_test:
        url = f"{base_url}{route}"
        print(f"\n🔍 Testing: {route}")
        
        try:
            # Test GET first
            response = requests.get(url, headers=headers, timeout=10)
            print(f"   GET {response.status_code}: {response.text[:100]}...")
            
            # Test OPTIONS for CORS
            response = requests.options(url, headers=headers, timeout=10)
            print(f"   OPTIONS {response.status_code}: {dict(response.headers)}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_routes()