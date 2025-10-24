"""Unit tests for user models."""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.user import (
    UserProfile, UserRegistration, UserLogin, UserProfileUpdate,
    UserPreferences, OnboardingData, AuthToken, UserResponse,
    LearningStyle, DifficultyLevel
)


class TestUserModels:
    """Test cases for user data models."""

    def test_learning_style_enum(self):
        """Test LearningStyle enum values."""
        assert LearningStyle.VISUAL == "visual"
        assert LearningStyle.AUDITORY == "auditory"
        assert LearningStyle.READING == "reading"

    def test_difficulty_level_enum(self):
        """Test DifficultyLevel enum values."""
        assert DifficultyLevel.BEGINNER == "beginner"
        assert DifficultyLevel.INTERMEDIATE == "intermediate"
        assert DifficultyLevel.ADVANCED == "advanced"

    def test_user_profile_valid(self):
        """Test UserProfile with valid data."""
        now = datetime.now(timezone.utc)
        profile_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com',
            'full_name': 'Test User',
            'age': 25,
            'profession': 'Software Engineer',
            'education_level': 'Bachelor\'s Degree',
            'country': 'United States',
            'learning_style': LearningStyle.VISUAL,
            'attention_span': 30,
            'difficulty_level': DifficultyLevel.INTERMEDIATE,
            'onboarding_completed': True,
            'preferences': {'theme': 'dark'},
            'created_at': now,
            'updated_at': now,
            'is_active': True
        }
        
        profile = UserProfile(**profile_data)
        
        assert profile.user_id == 'test_user_123'
        assert profile.email == 'test@example.com'
        assert profile.full_name == 'Test User'
        assert profile.age == 25
        assert profile.learning_style == LearningStyle.VISUAL
        assert profile.attention_span == 30
        assert profile.difficulty_level == DifficultyLevel.INTERMEDIATE

    def test_user_profile_age_validation(self):
        """Test UserProfile age validation."""
        now = datetime.now(timezone.utc)
        base_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com',
            'created_at': now,
            'updated_at': now
        }
        
        # Valid age
        profile = UserProfile(**{**base_data, 'age': 25})
        assert profile.age == 25
        
        # Age too young
        with pytest.raises(ValidationError) as exc_info:
            UserProfile(**{**base_data, 'age': 12})
        assert "ensure this value is greater than or equal to 13" in str(exc_info.value)
        
        # Age too old
        with pytest.raises(ValidationError) as exc_info:
            UserProfile(**{**base_data, 'age': 101})
        assert "ensure this value is less than or equal to 100" in str(exc_info.value)

    def test_user_profile_attention_span_validation(self):
        """Test UserProfile attention span validation."""
        now = datetime.now(timezone.utc)
        base_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com',
            'created_at': now,
            'updated_at': now
        }
        
        # Valid attention span
        profile = UserProfile(**{**base_data, 'attention_span': 30})
        assert profile.attention_span == 30
        
        # Attention span too short
        with pytest.raises(ValidationError) as exc_info:
            UserProfile(**{**base_data, 'attention_span': 4})
        assert "ensure this value is greater than or equal to 5" in str(exc_info.value)
        
        # Attention span too long
        with pytest.raises(ValidationError) as exc_info:
            UserProfile(**{**base_data, 'attention_span': 61})
        assert "ensure this value is less than or equal to 60" in str(exc_info.value)

    def test_user_registration_valid(self):
        """Test UserRegistration with valid data."""
        registration_data = {
            'email': 'test@example.com',
            'password': 'TestPassword123!',
            'full_name': 'Test User',
            'age': 25,
            'profession': 'Software Engineer',
            'education_level': 'Bachelor\'s Degree',
            'country': 'United States'
        }
        
        registration = UserRegistration(**registration_data)
        
        assert registration.email == 'test@example.com'
        assert registration.password == 'TestPassword123!'
        assert registration.full_name == 'Test User'
        assert registration.age == 25

    def test_user_registration_email_validation(self):
        """Test UserRegistration email validation."""
        base_data = {
            'password': 'TestPassword123!'
        }
        
        # Valid email
        registration = UserRegistration(**{**base_data, 'email': 'test@example.com'})
        assert registration.email == 'test@example.com'
        
        # Invalid email format
        with pytest.raises(ValidationError) as exc_info:
            UserRegistration(**{**base_data, 'email': 'invalid-email'})
        assert "value is not a valid email address" in str(exc_info.value)

    def test_user_registration_password_validation(self):
        """Test UserRegistration password validation."""
        base_data = {
            'email': 'test@example.com'
        }
        
        # Valid password
        registration = UserRegistration(**{**base_data, 'password': 'TestPassword123!'})
        assert registration.password == 'TestPassword123!'
        
        # Password too short
        with pytest.raises(ValidationError) as exc_info:
            UserRegistration(**{**base_data, 'password': 'Test1!'})
        assert "Password must be at least 8 characters long" in str(exc_info.value)
        
        # Password without letter
        with pytest.raises(ValidationError) as exc_info:
            UserRegistration(**{**base_data, 'password': '12345678!'})
        assert "Password must contain at least one letter" in str(exc_info.value)
        
        # Password without number
        with pytest.raises(ValidationError) as exc_info:
            UserRegistration(**{**base_data, 'password': 'TestPassword!'})
        assert "Password must contain at least one number" in str(exc_info.value)

    def test_user_registration_email_lowercase(self):
        """Test UserRegistration email conversion to lowercase."""
        registration_data = {
            'email': 'TEST@EXAMPLE.COM',
            'password': 'TestPassword123!'
        }
        
        registration = UserRegistration(**registration_data)
        assert registration.email == 'test@example.com'

    def test_user_login_valid(self):
        """Test UserLogin with valid data."""
        login_data = {
            'email': 'test@example.com',
            'password': 'TestPassword123!'
        }
        
        login = UserLogin(**login_data)
        
        assert login.email == 'test@example.com'
        assert login.password == 'TestPassword123!'

    def test_user_profile_update_valid(self):
        """Test UserProfileUpdate with valid data."""
        update_data = {
            'full_name': 'Updated Name',
            'age': 30,
            'profession': 'Senior Engineer',
            'learning_style': LearningStyle.AUDITORY,
            'attention_span': 45,
            'difficulty_level': DifficultyLevel.ADVANCED,
            'onboarding_completed': True,
            'preferences': {'theme': 'light'}
        }
        
        update = UserProfileUpdate(**update_data)
        
        assert update.full_name == 'Updated Name'
        assert update.age == 30
        assert update.learning_style == LearningStyle.AUDITORY
        assert update.attention_span == 45
        assert update.difficulty_level == DifficultyLevel.ADVANCED

    def test_user_profile_update_field_validation(self):
        """Test UserProfileUpdate field validation."""
        # Valid data
        update = UserProfileUpdate(full_name='Test User', age=25)
        assert update.full_name == 'Test User'
        assert update.age == 25
        
        # Invalid age
        with pytest.raises(ValidationError) as exc_info:
            UserProfileUpdate(age=12)
        assert "ensure this value is greater than or equal to 13" in str(exc_info.value)
        
        # Invalid attention span
        with pytest.raises(ValidationError) as exc_info:
            UserProfileUpdate(attention_span=4)
        assert "ensure this value is greater than or equal to 5" in str(exc_info.value)

    def test_user_preferences_valid(self):
        """Test UserPreferences with valid data."""
        preferences_data = {
            'learning_style': LearningStyle.VISUAL,
            'attention_span': 30,
            'difficulty_level': DifficultyLevel.INTERMEDIATE
        }
        
        preferences = UserPreferences(**preferences_data)
        
        assert preferences.learning_style == LearningStyle.VISUAL
        assert preferences.attention_span == 30
        assert preferences.difficulty_level == DifficultyLevel.INTERMEDIATE

    def test_user_preferences_validation(self):
        """Test UserPreferences validation."""
        base_data = {
            'learning_style': LearningStyle.VISUAL,
            'difficulty_level': DifficultyLevel.INTERMEDIATE
        }
        
        # Valid attention span
        preferences = UserPreferences(**{**base_data, 'attention_span': 30})
        assert preferences.attention_span == 30
        
        # Invalid attention span
        with pytest.raises(ValidationError) as exc_info:
            UserPreferences(**{**base_data, 'attention_span': 4})
        assert "ensure this value is greater than or equal to 5" in str(exc_info.value)

    def test_onboarding_data_valid(self):
        """Test OnboardingData with valid data."""
        onboarding_data = {
            'full_name': 'Test User',
            'age': 25,
            'profession': 'Software Engineer',
            'education_level': 'Bachelor\'s Degree',
            'country': 'United States',
            'learning_style': LearningStyle.VISUAL,
            'attention_span': 30,
            'difficulty_level': DifficultyLevel.INTERMEDIATE
        }
        
        onboarding = OnboardingData(**onboarding_data)
        
        assert onboarding.full_name == 'Test User'
        assert onboarding.age == 25
        assert onboarding.learning_style == LearningStyle.VISUAL
        assert onboarding.attention_span == 30
        assert onboarding.difficulty_level == DifficultyLevel.INTERMEDIATE

    def test_onboarding_data_validation(self):
        """Test OnboardingData validation."""
        base_data = {
            'full_name': 'Test User',
            'learning_style': LearningStyle.VISUAL,
            'attention_span': 30,
            'difficulty_level': DifficultyLevel.INTERMEDIATE
        }
        
        # Valid age
        onboarding = OnboardingData(**{**base_data, 'age': 25})
        assert onboarding.age == 25
        
        # Invalid age
        with pytest.raises(ValidationError) as exc_info:
            OnboardingData(**{**base_data, 'age': 12})
        assert "ensure this value is greater than or equal to 13" in str(exc_info.value)

    def test_auth_token_valid(self):
        """Test AuthToken with valid data."""
        token_data = {
            'access_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
            'token_type': 'bearer',
            'expires_in': 3600,
            'user_id': 'test_user_123'
        }
        
        token = AuthToken(**token_data)
        
        assert token.access_token == 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
        assert token.token_type == 'bearer'
        assert token.expires_in == 3600
        assert token.user_id == 'test_user_123'

    def test_auth_token_default_type(self):
        """Test AuthToken with default token type."""
        token_data = {
            'access_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
            'expires_in': 3600,
            'user_id': 'test_user_123'
        }
        
        token = AuthToken(**token_data)
        assert token.token_type == 'bearer'  # Default value

    def test_user_response_valid(self):
        """Test UserResponse with valid data."""
        now = datetime.now(timezone.utc)
        response_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com',
            'full_name': 'Test User',
            'age': 25,
            'profession': 'Software Engineer',
            'education_level': 'Bachelor\'s Degree',
            'country': 'United States',
            'learning_style': LearningStyle.VISUAL,
            'attention_span': 30,
            'difficulty_level': DifficultyLevel.INTERMEDIATE,
            'onboarding_completed': True,
            'preferences': {'theme': 'dark'},
            'created_at': now,
            'is_active': True
        }
        
        response = UserResponse(**response_data)
        
        assert response.user_id == 'test_user_123'
        assert response.email == 'test@example.com'
        assert response.full_name == 'Test User'
        assert response.learning_style == LearningStyle.VISUAL
        assert response.onboarding_completed is True
        assert response.is_active is True

    def test_user_response_defaults(self):
        """Test UserResponse with default values."""
        now = datetime.now(timezone.utc)
        minimal_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com',
            'created_at': now
        }
        
        response = UserResponse(**minimal_data)
        
        assert response.user_id == 'test_user_123'
        assert response.email == 'test@example.com'
        assert response.onboarding_completed is False  # Default
        assert response.is_active is True  # Default
        assert response.full_name is None  # Optional field