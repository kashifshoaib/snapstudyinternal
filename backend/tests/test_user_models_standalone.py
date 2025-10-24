"""Standalone unit tests for user models functionality."""

import pytest
from datetime import datetime, timezone
from pydantic import BaseModel, EmailStr, Field, ValidationError, validator
from enum import Enum
from typing import Optional, Dict, Any
import re


class LearningStyle(str, Enum):
    """Learning style preferences for users."""
    VISUAL = "visual"
    AUDITORY = "auditory"
    READING = "reading"


class DifficultyLevel(str, Enum):
    """Difficulty level preferences for learning content."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class UserRegistration(BaseModel):
    """User registration request model with comprehensive validation."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    age: Optional[int] = Field(None, ge=13, le=100)
    profession: Optional[str] = Field(None, max_length=100)
    education_level: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)

    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password strength requirements."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        return v

    @validator('email')
    def validate_email_format(cls, v):
        """Additional email validation."""
        if not v or '@' not in v:
            raise ValueError('Valid email address is required')
        return v.lower()


class UserPreferences(BaseModel):
    """User learning preferences model with validation."""
    learning_style: LearningStyle
    attention_span: int = Field(..., ge=5, le=60, description="Attention span in minutes (5-60)")
    difficulty_level: DifficultyLevel

    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class OnboardingData(BaseModel):
    """Onboarding data collection model."""
    full_name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=13, le=100)
    profession: Optional[str] = Field(None, max_length=100)
    education_level: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    learning_style: LearningStyle
    attention_span: int = Field(..., ge=5, le=60)
    difficulty_level: DifficultyLevel


class AuthToken(BaseModel):
    """Authentication token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str


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
        assert "String should have at least 8 characters" in str(exc_info.value)
        
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

    def test_user_registration_age_validation(self):
        """Test UserRegistration age validation."""
        base_data = {
            'email': 'test@example.com',
            'password': 'TestPassword123!'
        }
        
        # Valid age
        registration = UserRegistration(**{**base_data, 'age': 25})
        assert registration.age == 25
        
        # Age too young
        with pytest.raises(ValidationError) as exc_info:
            UserRegistration(**{**base_data, 'age': 12})
        assert "Input should be greater than or equal to 13" in str(exc_info.value)
        
        # Age too old
        with pytest.raises(ValidationError) as exc_info:
            UserRegistration(**{**base_data, 'age': 101})
        assert "Input should be less than or equal to 100" in str(exc_info.value)

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

    def test_user_preferences_attention_span_validation(self):
        """Test UserPreferences attention span validation."""
        base_data = {
            'learning_style': LearningStyle.VISUAL,
            'difficulty_level': DifficultyLevel.INTERMEDIATE
        }
        
        # Valid attention span
        preferences = UserPreferences(**{**base_data, 'attention_span': 30})
        assert preferences.attention_span == 30
        
        # Attention span too short
        with pytest.raises(ValidationError) as exc_info:
            UserPreferences(**{**base_data, 'attention_span': 4})
        assert "Input should be greater than or equal to 5" in str(exc_info.value)
        
        # Attention span too long
        with pytest.raises(ValidationError) as exc_info:
            UserPreferences(**{**base_data, 'attention_span': 61})
        assert "Input should be less than or equal to 60" in str(exc_info.value)

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
        assert "Input should be greater than or equal to 13" in str(exc_info.value)

    def test_onboarding_data_required_fields(self):
        """Test OnboardingData required field validation."""
        # Missing full_name
        with pytest.raises(ValidationError) as exc_info:
            OnboardingData(
                age=25,
                learning_style=LearningStyle.VISUAL,
                attention_span=30,
                difficulty_level=DifficultyLevel.INTERMEDIATE
            )
        assert "Field required" in str(exc_info.value)

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

    def test_auth_token_required_fields(self):
        """Test AuthToken required field validation."""
        # Missing access_token
        with pytest.raises(ValidationError) as exc_info:
            AuthToken(
                expires_in=3600,
                user_id='test_user_123'
            )
        assert "Field required" in str(exc_info.value)