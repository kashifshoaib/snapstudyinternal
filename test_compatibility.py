#!/usr/bin/env python3
"""
Simple compatibility test script for the authentication system.
"""

import sys
import os
import traceback

# Add the backend src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        # Test model imports
        from models.user import UserProfile, UserRegistration, UserLogin, UserProfileUpdate, UserPreferences, AuthToken
        print("✓ User models imported successfully")
        
        # Test service imports
        from services.jwt_service import jwt_service
        from services.password_service import password_service
        from services.dynamodb import db_service
        print("✓ Services imported successfully")
        
        # Test router imports
        from api.routers.auth import router as auth_router
        from api.routers.users import router as users_router
        print("✓ Routers imported successfully")
        
        # Test middleware imports
        from middleware.auth_middleware import auth_middleware
        print("✓ Middleware imported successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        traceback.print_exc()
        return False

def test_user_models():
    """Test user model creation and validation."""
    print("\nTesting user models...")
    
    try:
        from models.user import UserProfile, UserRegistration, UserLogin, UserPreferences
        from datetime import datetime
        
        # Test UserRegistration
        user_reg = UserRegistration(
            email="test@example.com",
            password="TestPassword123!",
            full_name="Test User"
        )
        print("✓ UserRegistration model works")
        
        # Test UserLogin
        user_login = UserLogin(
            email="test@example.com",
            password="TestPassword123!"
        )
        print("✓ UserLogin model works")
        
        # Test UserProfile
        user_profile = UserProfile(
            user_id="test-123",
            email="test@example.com",
            full_name="Test User",
            age=25,
            profession="Developer",
            education_level="Bachelor's",
            country="US",
            onboarding_completed=True,
            created_at=datetime.utcnow().isoformat() + "Z",
            updated_at=datetime.utcnow().isoformat() + "Z",
            is_active=True
        )
        print("✓ UserProfile model works")
        
        # Test UserPreferences
        preferences = UserPreferences(
            learning_style="visual",
            attention_span=30,
            difficulty_level="intermediate"
        )
        print("✓ UserPreferences model works")
        
        return True
        
    except Exception as e:
        print(f"✗ User model test failed: {e}")
        traceback.print_exc()
        return False

def test_services():
    """Test service functionality."""
    print("\nTesting services...")
    
    try:
        from services.jwt_service import jwt_service
        from services.password_service import password_service
        
        # Test password service
        password = "TestPassword123!"
        hashed = password_service.hash_password(password)
        is_valid = password_service.verify_password(password, hashed)
        
        if not is_valid:
            print("✗ Password service verification failed")
            return False
        print("✓ Password service works")
        
        # Test JWT service
        test_payload = {"user_id": "test-123", "email": "test@example.com"}
        token = jwt_service.create_token(test_payload)
        decoded = jwt_service.verify_token(token)
        
        if decoded.get("user_id") != test_payload["user_id"]:
            print("✗ JWT service verification failed")
            return False
        print("✓ JWT service works")
        
        return True
        
    except Exception as e:
        print(f"✗ Service test failed: {e}")
        traceback.print_exc()
        return False

def test_api_structure():
    """Test API router structure."""
    print("\nTesting API structure...")
    
    try:
        from api.routers.auth import router as auth_router
        from api.routers.users import router as users_router
        
        # Check auth router endpoints
        auth_paths = [route.path for route in auth_router.routes]
        required_auth_endpoints = ["/register", "/login", "/verify"]
        
        missing_auth = [ep for ep in required_auth_endpoints if ep not in auth_paths]
        if missing_auth:
            print(f"⚠ Missing auth endpoints: {missing_auth}")
        else:
            print("✓ Auth endpoints present")
        
        # Check users router endpoints
        users_paths = [route.path for route in users_router.routes]
        required_user_endpoints = ["/me", "/profile", "/onboarding"]
        
        missing_users = [ep for ep in required_user_endpoints if ep not in users_paths]
        if missing_users:
            print(f"⚠ Missing user endpoints: {missing_users}")
        else:
            print("✓ User endpoints present")
        
        return True
        
    except Exception as e:
        print(f"✗ API structure test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all compatibility tests."""
    print("=== Authentication System Compatibility Test ===\n")
    
    tests = [
        ("Import Test", test_imports),
        ("User Models Test", test_user_models),
        ("Services Test", test_services),
        ("API Structure Test", test_api_structure)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
            print(f"✓ {test_name} PASSED")
        else:
            print(f"✗ {test_name} FAILED")
    
    print(f"\n=== Results ===")
    print(f"Passed: {passed}/{total}")
    print(f"Status: {'PASSED' if passed == total else 'FAILED'}")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)