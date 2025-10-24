#!/usr/bin/env python3
"""
Test script to verify frontend onboarding sends all fields to backend.
"""

import requests
import json
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.src.services.dynamodb import db_service
import asyncio

def test_frontend_onboarding_flow():
    """Test that frontend properly sends all onboarding fields to backend."""
    print("🧪 Testing Frontend → Backend Onboarding Flow")
    print("=" * 50)
    
    # Test data - this simulates what the frontend form should send
    test_email = "frontend-test@example.com"
    test_password = "testpass123"
    
    # Step 1: Register new user
    print("1️⃣  Registering new user...")
    reg_response = requests.post(
        'http://localhost:8000/api/v1/auth/register',
        json={
            'email': test_email,
            'password': test_password,
            'full_name': 'Frontend Test User',
            'profession': 'Tester',
            'education_level': 'Bachelor',
            'country': 'US'
        }
    )
    
    if reg_response.status_code != 200:
        print(f"❌ Registration failed: {reg_response.text}")
        return False
    
    print("✅ Registration successful")
    
    # Step 2: Login
    print("\n2️⃣  Logging in...")
    login_response = requests.post(
        'http://localhost:8000/api/v1/auth/login',
        json={'email': test_email, 'password': test_password}
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.text}")
        return False
    
    token = login_response.json()['access_token']
    print("✅ Login successful")
    
    # Step 3: Complete onboarding with ALL fields (simulating frontend form)
    print("\n3️⃣  Completing onboarding with ALL fields...")
    
    # This is exactly what the frontend OnboardingFlow should send
    complete_onboarding_data = {
        "full_name": "Frontend Test User Updated",
        "age": 28,
        "profession": "Senior Frontend Developer", 
        "education_level": "Master's Degree",
        "country": "United States",
        "learning_style": "visual",
        "attention_span": 30,
        "difficulty_level": "advanced"
    }
    
    print("📤 Sending onboarding data:")
    for key, value in complete_onboarding_data.items():
        print(f"   {key}: {value}")
    
    onboarding_response = requests.post(
        'http://localhost:8000/api/v1/users/onboarding',
        json=complete_onboarding_data,
        headers={'Authorization': f'Bearer {token}'}
    )
    
    print(f"\n📥 Backend Response Status: {onboarding_response.status_code}")
    
    if onboarding_response.status_code != 200:
        print(f"❌ Onboarding failed: {onboarding_response.text}")
        return False
    
    print("✅ Onboarding API call successful")
    
    # Step 4: Verify ALL fields are in database
    print("\n4️⃣  Verifying database contains ALL fields...")
    
    async def verify_database():
        try:
            user = await db_service.get_user_by_email(test_email)
            if not user:
                print("❌ User not found in database")
                return False
            
            # Check all expected fields
            expected_fields = {
                'full_name': 'Frontend Test User Updated',
                'age': 28.0,  # DynamoDB returns numbers as float
                'profession': 'Senior Frontend Developer',
                'education_level': "Master's Degree", 
                'country': 'United States',
                'learning_style': 'visual',
                'attention_span': 30.0,
                'difficulty_level': 'advanced',
                'onboarding_completed': True
            }
            
            all_fields_correct = True
            
            print("📊 Database verification:")
            for field, expected_value in expected_fields.items():
                actual_value = user.get(field)
                if actual_value == expected_value:
                    print(f"   ✅ {field}: {actual_value}")
                else:
                    print(f"   ❌ {field}: Expected '{expected_value}', Got '{actual_value}'")
                    all_fields_correct = False
            
            # Also check preferences object
            preferences = user.get('preferences', {})
            expected_preferences = {
                'learning_style': 'visual',
                'attention_span': 30.0,
                'difficulty_level': 'advanced'
            }
            
            print("\n📋 Preferences object:")
            for field, expected_value in expected_preferences.items():
                actual_value = preferences.get(field)
                if actual_value == expected_value:
                    print(f"   ✅ preferences.{field}: {actual_value}")
                else:
                    print(f"   ❌ preferences.{field}: Expected '{expected_value}', Got '{actual_value}'")
                    all_fields_correct = False
            
            return all_fields_correct
            
        except Exception as e:
            print(f"❌ Database verification error: {e}")
            return False
    
    # Run database verification
    verification_result = asyncio.run(verify_database())
    
    if verification_result:
        print("\n🎉 SUCCESS: All onboarding fields properly saved to database!")
        print("✅ Frontend → Backend → Database flow is working correctly")
        return True
    else:
        print("\n❌ FAILURE: Some fields missing or incorrect in database")
        return False

if __name__ == "__main__":
    success = test_frontend_onboarding_flow()
    if success:
        print("\n🏆 Frontend onboarding integration test PASSED")
    else:
        print("\n💥 Frontend onboarding integration test FAILED")
        sys.exit(1)