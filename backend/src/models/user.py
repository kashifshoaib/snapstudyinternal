"""User data models."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum
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


class UserProfile(BaseModel):
    """Complete user profile data model with comprehensive validation."""
    user_id: str
    email: EmailStr
    full_name: Optional[str] = None
    age: Optional[int] = Field(None, ge=13, le=100, description="User age between 13 and 100")
    profession: Optional[str] = None
    education_level: Optional[str] = None
    country: Optional[str] = None
    learning_style: Optional[LearningStyle] = None
    attention_span: Optional[int] = Field(None, ge=5, le=60, description="Attention span in minutes (5-60)")
    difficulty_level: Optional[DifficultyLevel] = None
    onboarding_completed: bool = False
    preferences: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool = True


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


class UserLogin(BaseModel):
    """User login request model."""
    email: EmailStr
    password: str


class UserProfileUpdate(BaseModel):
    """User profile update model with comprehensive validation."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    age: Optional[int] = Field(None, ge=13, le=100)
    profession: Optional[str] = Field(None, max_length=100)
    education_level: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    learning_style: Optional[LearningStyle] = None
    attention_span: Optional[int] = Field(None, ge=5, le=60, description="Attention span in minutes")
    difficulty_level: Optional[DifficultyLevel] = None
    onboarding_completed: Optional[bool] = None
    preferences: Optional[Dict[str, Any]] = None


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


class UserResponse(BaseModel):
    """User response model for API responses."""
    user_id: str
    email: str
    full_name: Optional[str] = None
    age: Optional[int] = None
    profession: Optional[str] = None
    education_level: Optional[str] = None
    country: Optional[str] = None
    learning_style: Optional[LearningStyle] = None
    attention_span: Optional[int] = None
    difficulty_level: Optional[DifficultyLevel] = None
    onboarding_completed: bool = False
    preferences: Optional[Dict[str, Any]] = None
    created_at: datetime
    is_active: bool = True

    class Config:
        """Pydantic configuration."""
        use_enum_values = True