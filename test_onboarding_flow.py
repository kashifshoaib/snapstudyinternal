#!/usr/bin/env python3
"""
Test script for the complete onboarding flow.
"""

import requests
import base64
import json

def test_onboarding_flow():
    """Test the complete onboarding flow."""
    print("🧪 Testing Onboarding Flow")
    print("=" * 30)
    
    # Test data
    test_email = "onboarding-test@example.com"
    test_password = "testpass123"
    
    # Step 1: Register new user
    print("1️⃣  Registering new user...")
    reg_response = requests.post(
        'http://localhost:8000/api/v1/auth/register',
        json={
            'email': test_email,
            'password': test_password,
            'full_name': 'Test User',
            'profession': 'Developer',
            'education_level': 'Bachelor',
            'country': 'US'
        }
    )
    
    if reg_response.status_code != 200:
        print(f"❌ Registration failed: {reg_response.text}")
        return
    
    print("✅ Registration successful")
    
    # Step 2: Login and check onboarding status
    print("\n2️⃣  Logging in...")
    login_response = requests.post(
        'http://localhost:8000/api/v1/auth/login',
        json={'email': test_email, 'password': test_password}
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.text}")
        return
    
    token = login_response.json()['access_token']
    payload = json.loads(base64.b64decode(token.split('.')[1] + '=='))
    
    print("✅ Login successful")
    print(f"🎯 Onboarding needed: {not payload.get('onboarding_completed', True)}")
    
    # Step 3: Complete onboarding
    print("\n3️⃣  Completing onboarding...")
    onboarding_data = {
        "full_name": "Test User Updated",
        "age": 25,
        "profession": "Software Developer",
        "education_level": "Bachelor's Degree",
        "country": "United States",
        "learning_style": "visual",
        "attention_span": 30,
        "difficulty_level": "intermediate"
    }
    
    onboarding_response = requests.post(
        'http://localhost:8000/api/v1/users/onboarding',
        json=onboarding_data,
        headers={'Authorization': f'Bearer {token}'}
    )
    
    if onboarding_response.status_code == 200:
        print("✅ Onboarding completed successfully")
        print("📊 Response:", onboarding_response.json())
    else:
        print(f"❌ Onboarding failed: {onboarding_response.text}")
    
    # Step 4: Login again to verify onboarding status
    print("\n4️⃣  Verifying onboarding status...")
    login2_response = requests.post(
        'http://localhost:8000/api/v1/auth/login',
        json={'email': test_email, 'password': test_password}
    )
    
    if login2_response.status_code == 200:
        token2 = login2_response.json()['access_token']
        payload2 = json.loads(base64.b64decode(token2.split('.')[1] + '=='))
        
        onboarding_completed = payload2.get('onboarding_completed', False)
        print(f"🎯 Onboarding completed: {onboarding_completed}")
        
        if onboarding_completed:
            print("✅ Onboarding flow working correctly!")
        else:
            print("⚠️  Onboarding status not updated in token")
    else:
        print(f"❌ Second login failed: {login2_response.text}")
    
    print("\n🏁 Test completed!")

if __name__ == "__main__":
    test_onboarding_flow()