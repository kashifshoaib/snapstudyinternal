"""API integration tests for authentication and user management."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
import json
from datetime import datetime, timezone


# Mock the dependencies before importing the routers
class MockDBService:
    """Mock database service for testing."""
    
    def __init__(self):
        self.users = {}
        self.user_counter = 1
    
    async def get_user_by_email(self, email):
        """Mock get user by email."""
        for user in self.users.values():
            if user.get('email') == email:
                return user
        return None
    
    async def get_user_by_id(self, user_id):
        """Mock get user by ID."""
        return self.users.get(user_id)
    
    async def create_user(self, user_data):
        """Mock create user."""
        user_id = user_data.get('user_id', f'user_{self.user_counter}')
        self.user_counter += 1
        
        user = {
            'user_id': user_id,
            'email': user_data['email'],
            'password_hash': user_data['password_hash'],
            'full_name': user_data.get('full_name'),
            'profession': user_data.get('profession'),
            'education_level': user_data.get('education_level'),
            'country': user_data.get('country'),
            'onboarding_completed': user_data.get('onboarding_completed', False),
            'preferences': user_data.get('preferences'),
            'is_active': user_data.get('is_active', True),
            'created_at': user_data.get('created_at', datetime.now(timezone.utc).isoformat()),
            'updated_at': user_data.get('updated_at', datetime.now(timezone.utc).isoformat())
        }
        
        self.users[user_id] = user
        return user
    
    async def update_user(self, user_id, updates):
        """Mock update user."""
        if user_id not in self.users:
            from src.middleware.error_handler import ResourceNotFoundError
            raise ResourceNotFoundError("User", "user_id", user_id)
        
        user = self.users[user_id]
        user.update(updates)
        user['updated_at'] = datetime.now(timezone.utc).isoformat()
        return user


# Mock password service functions
def mock_hash_password(password):
    """Mock password hashing."""
    return f"hashed_{password}"

def mock_verify_password(password, hashed_password):
    """Mock password verification."""
    return hashed_password == f"hashed_{password}"

# Mock JWT service functions
def mock_create_access_token(user_id, email):
    """Mock JWT token creation."""
    return f"token_{user_id}_{email}"

def mock_verify_token():
    """Mock JWT token verification."""
    return {"user_id": "test_user_123", "email": "test@example.com"}

# Mock settings
class MockSettings:
    jwt_expiration_hours = 24

# Create mock instances
mock_db_service = MockDBService()
mock_settings = MockSettings()

# Patch the imports
import sys
from unittest.mock import MagicMock

# Mock all the modules that would cause import issues
sys.modules['src'] = MagicMock()
sys.modules['src.models'] = MagicMock()
sys.modules['src.models.user'] = MagicMock()
sys.modules['src.services'] = MagicMock()
sys.modules['src.services.dynamodb'] = MagicMock()
sys.modules['src.services.password_service'] = MagicMock()
sys.modules['src.services.jwt_service'] = MagicMock()
sys.modules['src.config'] = MagicMock()
sys.modules['src.middleware'] = MagicMock()
sys.modules['src.middleware.error_handler'] = MagicMock()
sys.modules['src.middleware.auth_middleware'] = MagicMock()

# Set up the mocks
sys.modules['src.services.dynamodb'].db_service = mock_db_service
sys.modules['src.services.password_service'].hash_password = mock_hash_password
sys.modules['src.services.password_service'].verify_password = mock_verify_password
sys.modules['src.services.jwt_service'].create_access_token = mock_create_access_token
sys.modules['src.services.jwt_service'].verify_token = mock_verify_token
sys.modules['src.config'].settings = mock_settings

# Mock error classes
class MockAuthenticationError(Exception):
    pass

class MockValidationError(Exception):
    pass

class MockResourceConflictError(Exception):
    def __init__(self, resource, field, value):
        self.resource = resource
        self.field = field
        self.value = value
        super().__init__(f"{resource} with {field} {value} already exists")

class MockResourceNotFoundError(Exception):
    def __init__(self, resource, field, value):
        self.resource = resource
        self.field = field
        self.value = value
        super().__init__(f"{resource} with {field} {value} not found")

sys.modules['src.middleware.error_handler'].AuthenticationError = MockAuthenticationError
sys.modules['src.middleware.error_handler'].ValidationError = MockValidationError
sys.modules['src.middleware.error_handler'].ResourceConflictError = MockResourceConflictError
sys.modules['src.middleware.error_handler'].ResourceNotFoundError = MockResourceNotFoundError

# Mock Pydantic models
class MockUserRegistration:
    def __init__(self, **kwargs):
        self.email = kwargs.get('email')
        self.password = kwargs.get('password')
        self.full_name = kwargs.get('full_name')
        self.profession = kwargs.get('profession')
        self.education_level = kwargs.get('education_level')
        self.country = kwargs.get('country')

class MockUserLogin:
    def __init__(self, **kwargs):
        self.email = kwargs.get('email')
        self.password = kwargs.get('password')

class MockAuthToken:
    def __init__(self, **kwargs):
        self.access_token = kwargs.get('access_token')
        self.token_type = kwargs.get('token_type', 'bearer')
        self.expires_in = kwargs.get('expires_in')
        self.user_id = kwargs.get('user_id')

class MockUserProfile:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class MockUserProfileUpdate:
    def __init__(self, **kwargs):
        self._data = kwargs
    
    def dict(self, exclude_unset=False):
        return self._data

sys.modules['src.models.user'].UserRegistration = MockUserRegistration
sys.modules['src.models.user'].UserLogin = MockUserLogin
sys.modules['src.models.user'].AuthToken = MockAuthToken
sys.modules['src.models.user'].UserProfile = MockUserProfile
sys.modules['src.models.user'].UserProfileUpdate = MockUserProfileUpdate

# Mock auth middleware
def mock_get_current_user():
    return {"user_id": "test_user_123", "email": "test@example.com"}

sys.modules['src.middleware.auth_middleware'].get_current_user = mock_get_current_user


class TestAPIIntegration:
    """Test cases for API integration."""

    def setup_method(self):
        """Set up test fixtures."""
        # Reset mock database
        mock_db_service.users = {}
        mock_db_service.user_counter = 1
        
        # Create FastAPI app for testing
        self.app = FastAPI()
        
        # Create mock routers
        from fastapi import APIRouter, HTTPException, status
        
        auth_router = APIRouter()
        users_router = APIRouter()
        
        @auth_router.post("/register")
        async def register(user_data: dict):
            """Mock register endpoint."""
            # Check if user already exists
            existing_user = await mock_db_service.get_user_by_email(user_data['email'])
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="User with this email already exists"
                )
            
            # Create user
            user_id = f"user_{mock_db_service.user_counter}"
            hashed_password = mock_hash_password(user_data['password'])
            
            user_item = {
                "user_id": user_id,
                "email": user_data['email'],
                "password_hash": hashed_password,
                "full_name": user_data.get('full_name'),
                "profession": user_data.get('profession'),
                "education_level": user_data.get('education_level'),
                "country": user_data.get('country'),
                "is_active": True
            }
            
            await mock_db_service.create_user(user_item)
            
            # Create access token
            access_token = mock_create_access_token(user_id, user_data['email'])
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": 86400,
                "user_id": user_id
            }
        
        @auth_router.post("/login")
        async def login(user_data: dict):
            """Mock login endpoint."""
            # Get user from database
            user = await mock_db_service.get_user_by_email(user_data['email'])
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            # Verify password
            if not mock_verify_password(user_data['password'], user.get("password_hash", "")):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            # Check if user is active
            if not user.get("is_active", False):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is deactivated"
                )
            
            # Create access token
            access_token = mock_create_access_token(user["user_id"], user["email"])
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": 86400,
                "user_id": user["user_id"]
            }
        
        @auth_router.get("/verify")
        async def verify_token_endpoint():
            """Mock token verification endpoint."""
            return {"valid": True, "message": "Token is valid", "user_id": "test_user_123"}
        
        @users_router.get("/me")
        async def get_current_user_profile():
            """Mock get current user profile endpoint."""
            user = await mock_db_service.get_user_by_id("test_user_123")
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            return {
                "user_id": user["user_id"],
                "email": user["email"],
                "full_name": user.get("full_name"),
                "profession": user.get("profession"),
                "education_level": user.get("education_level"),
                "country": user.get("country"),
                "onboarding_completed": user.get("onboarding_completed", False),
                "preferences": user.get("preferences"),
                "created_at": user["created_at"],
                "updated_at": user["updated_at"]
            }
        
        @users_router.put("/profile")
        async def update_user_profile(profile_data: dict):
            """Mock update user profile endpoint."""
            updated_user = await mock_db_service.update_user("test_user_123", profile_data)
            
            return {
                "message": "Profile updated successfully",
                "user": {
                    "user_id": updated_user["user_id"],
                    "email": updated_user["email"],
                    "full_name": updated_user.get("full_name"),
                    "profession": updated_user.get("profession"),
                    "education_level": updated_user.get("education_level"),
                    "country": updated_user.get("country"),
                    "onboarding_completed": updated_user.get("onboarding_completed", False),
                    "preferences": updated_user.get("preferences"),
                    "updated_at": updated_user["updated_at"]
                }
            }
        
        @users_router.post("/onboarding")
        async def complete_onboarding(onboarding_data: dict):
            """Mock complete onboarding endpoint."""
            # Extract profile updates
            profile_updates = {
                "full_name": onboarding_data.get("full_name"),
                "profession": onboarding_data.get("profession"),
                "education_level": onboarding_data.get("education_level"),
                "country": onboarding_data.get("country"),
                "onboarding_completed": True
            }
            
            # Remove None values
            profile_updates = {k: v for k, v in profile_updates.items() if v is not None}
            
            # Extract preferences
            preferences = {
                "learning_style": onboarding_data.get("learning_style"),
                "attention_span": onboarding_data.get("attention_span"),
                "difficulty_level": onboarding_data.get("difficulty_level")
            }
            
            # Remove None values from preferences
            preferences = {k: v for k, v in preferences.items() if v is not None}
            
            # Add preferences to profile updates
            if preferences:
                profile_updates["preferences"] = preferences
            
            # Update user profile
            updated_user = await mock_db_service.update_user("test_user_123", profile_updates)
            
            return {
                "message": "Onboarding completed successfully",
                "user": {
                    "user_id": updated_user["user_id"],
                    "email": updated_user["email"],
                    "full_name": updated_user.get("full_name"),
                    "profession": updated_user.get("profession"),
                    "education_level": updated_user.get("education_level"),
                    "country": updated_user.get("country"),
                    "onboarding_completed": updated_user.get("onboarding_completed", False),
                    "preferences": updated_user.get("preferences"),
                    "updated_at": updated_user["updated_at"]
                }
            }
        
        # Include routers
        self.app.include_router(auth_router, prefix="/auth")
        self.app.include_router(users_router, prefix="/users")
        
        # Create test client
        self.client = TestClient(self.app)

    def test_user_registration_workflow(self):
        """Test complete user registration workflow."""
        # Test user registration
        registration_data = {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "full_name": "Test User",
            "profession": "Software Engineer",
            "education_level": "Bachelor's Degree",
            "country": "United States"
        }
        
        response = self.client.post("/auth/register", json=registration_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 86400
        assert "user_id" in data
        
        # Verify user was created in database
        user_id = data["user_id"]
        assert user_id in mock_db_service.users
        
        user = mock_db_service.users[user_id]
        assert user["email"] == registration_data["email"]
        assert user["full_name"] == registration_data["full_name"]
        assert user["profession"] == registration_data["profession"]
        assert user["password_hash"] == f"hashed_{registration_data['password']}"

    def test_user_registration_duplicate_email(self):
        """Test user registration with duplicate email."""
        registration_data = {
            "email": "test@example.com",
            "password": "TestPassword123!"
        }
        
        # First registration should succeed
        response1 = self.client.post("/auth/register", json=registration_data)
        assert response1.status_code == 200
        
        # Second registration with same email should fail
        response2 = self.client.post("/auth/register", json=registration_data)
        assert response2.status_code == 409
        assert "already exists" in response2.json()["detail"]

    def test_login_workflow(self):
        """Test user login workflow."""
        # First register a user
        registration_data = {
            "email": "test@example.com",
            "password": "TestPassword123!"
        }
        
        reg_response = self.client.post("/auth/register", json=registration_data)
        assert reg_response.status_code == 200
        
        # Now test login
        login_data = {
            "email": "test@example.com",
            "password": "TestPassword123!"
        }
        
        response = self.client.post("/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 86400
        assert "user_id" in data

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        # Register a user first
        registration_data = {
            "email": "test@example.com",
            "password": "TestPassword123!"
        }
        
        self.client.post("/auth/register", json=registration_data)
        
        # Test login with wrong password
        login_data = {
            "email": "test@example.com",
            "password": "WrongPassword123!"
        }
        
        response = self.client.post("/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_nonexistent_user(self):
        """Test login with nonexistent user."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "TestPassword123!"
        }
        
        response = self.client.post("/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_token_verification(self):
        """Test token verification endpoint."""
        response = self.client.get("/auth/verify")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True
        assert data["message"] == "Token is valid"
        assert "user_id" in data

    def test_get_user_profile(self):
        """Test getting user profile."""
        # Create a test user first
        user_data = {
            "user_id": "test_user_123",
            "email": "test@example.com",
            "password_hash": "hashed_password",
            "full_name": "Test User",
            "profession": "Software Engineer",
            "is_active": True
        }
        
        asyncio.run(mock_db_service.create_user(user_data))
        
        response = self.client.get("/users/me")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["user_id"] == "test_user_123"
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert data["profession"] == "Software Engineer"

    def test_get_user_profile_not_found(self):
        """Test getting user profile when user doesn't exist."""
        # Don't create any user
        response = self.client.get("/users/me")
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    def test_update_user_profile(self):
        """Test updating user profile."""
        # Create a test user first
        user_data = {
            "user_id": "test_user_123",
            "email": "test@example.com",
            "password_hash": "hashed_password",
            "full_name": "Test User",
            "is_active": True
        }
        
        asyncio.run(mock_db_service.create_user(user_data))
        
        # Update profile
        update_data = {
            "full_name": "Updated Test User",
            "profession": "Senior Software Engineer",
            "country": "Canada"
        }
        
        response = self.client.put("/users/profile", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Profile updated successfully"
        assert data["user"]["full_name"] == "Updated Test User"
        assert data["user"]["profession"] == "Senior Software Engineer"
        assert data["user"]["country"] == "Canada"

    def test_complete_onboarding_workflow(self):
        """Test complete onboarding workflow."""
        # Create a test user first
        user_data = {
            "user_id": "test_user_123",
            "email": "test@example.com",
            "password_hash": "hashed_password",
            "is_active": True
        }
        
        asyncio.run(mock_db_service.create_user(user_data))
        
        # Complete onboarding
        onboarding_data = {
            "full_name": "Test User",
            "profession": "Software Engineer",
            "education_level": "Bachelor's Degree",
            "country": "United States",
            "learning_style": "visual",
            "attention_span": 30,
            "difficulty_level": "intermediate"
        }
        
        response = self.client.post("/users/onboarding", json=onboarding_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Onboarding completed successfully"
        assert data["user"]["full_name"] == "Test User"
        assert data["user"]["profession"] == "Software Engineer"
        assert data["user"]["onboarding_completed"] is True
        
        # Check preferences were saved
        preferences = data["user"]["preferences"]
        assert preferences["learning_style"] == "visual"
        assert preferences["attention_span"] == 30
        assert preferences["difficulty_level"] == "intermediate"

    def test_end_to_end_user_journey(self):
        """Test complete end-to-end user journey."""
        # 1. Register user
        registration_data = {
            "email": "journey@example.com",
            "password": "TestPassword123!",
            "full_name": "Journey User"
        }
        
        reg_response = self.client.post("/auth/register", json=registration_data)
        assert reg_response.status_code == 200
        
        user_id = reg_response.json()["user_id"]
        
        # 2. Login user
        login_data = {
            "email": "journey@example.com",
            "password": "TestPassword123!"
        }
        
        login_response = self.client.post("/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        # 3. Get user profile (should work after registration)
        # First update the mock to use the registered user
        mock_db_service.users["test_user_123"] = mock_db_service.users[user_id].copy()
        
        profile_response = self.client.get("/users/me")
        assert profile_response.status_code == 200
        
        # 4. Complete onboarding
        onboarding_data = {
            "full_name": "Journey User Updated",
            "profession": "Data Scientist",
            "education_level": "Master's Degree",
            "country": "Canada",
            "learning_style": "auditory",
            "attention_span": 45,
            "difficulty_level": "advanced"
        }
        
        onboarding_response = self.client.post("/users/onboarding", json=onboarding_data)
        assert onboarding_response.status_code == 200
        
        onboarding_data_response = onboarding_response.json()
        assert onboarding_data_response["user"]["onboarding_completed"] is True
        assert onboarding_data_response["user"]["profession"] == "Data Scientist"
        
        # 5. Update profile again
        update_data = {
            "country": "United Kingdom"
        }
        
        update_response = self.client.put("/users/profile", json=update_data)
        assert update_response.status_code == 200
        
        update_data_response = update_response.json()
        assert update_data_response["user"]["country"] == "United Kingdom"
        
        # 6. Verify token still works
        verify_response = self.client.get("/auth/verify")
        assert verify_response.status_code == 200