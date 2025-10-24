"""
Comprehensive error messages for authentication system.

This module provides standardized error messages for all authentication
and user management scenarios with proper internationalization support.
"""

from typing import Dict, Any, Optional
from enum import Enum


class ErrorCode(Enum):
    """Standardized error codes for the authentication system."""
    
    # Authentication errors
    INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    TOKEN_MISSING = "AUTH_TOKEN_MISSING"
    AUTHENTICATION_REQUIRED = "AUTH_REQUIRED"
    INSUFFICIENT_PERMISSIONS = "AUTH_INSUFFICIENT_PERMISSIONS"
    
    # Registration errors
    EMAIL_ALREADY_EXISTS = "REG_EMAIL_EXISTS"
    INVALID_EMAIL_FORMAT = "REG_INVALID_EMAIL"
    WEAK_PASSWORD = "REG_WEAK_PASSWORD"
    REGISTRATION_FAILED = "REG_FAILED"
    
    # User profile errors
    USER_NOT_FOUND = "USER_NOT_FOUND"
    PROFILE_UPDATE_FAILED = "USER_UPDATE_FAILED"
    INVALID_USER_DATA = "USER_INVALID_DATA"
    ONBOARDING_INCOMPLETE = "USER_ONBOARDING_INCOMPLETE"
    
    # Validation errors
    VALIDATION_FAILED = "VALIDATION_FAILED"
    REQUIRED_FIELD_MISSING = "VALIDATION_REQUIRED_FIELD"
    INVALID_FIELD_VALUE = "VALIDATION_INVALID_VALUE"
    FIELD_TOO_LONG = "VALIDATION_FIELD_TOO_LONG"
    FIELD_TOO_SHORT = "VALIDATION_FIELD_TOO_SHORT"
    INVALID_AGE_RANGE = "VALIDATION_INVALID_AGE"
    INVALID_ATTENTION_SPAN = "VALIDATION_INVALID_ATTENTION_SPAN"
    
    # System errors
    DATABASE_ERROR = "SYS_DATABASE_ERROR"
    NETWORK_ERROR = "SYS_NETWORK_ERROR"
    SERVICE_UNAVAILABLE = "SYS_SERVICE_UNAVAILABLE"
    INTERNAL_ERROR = "SYS_INTERNAL_ERROR"
    RATE_LIMIT_EXCEEDED = "SYS_RATE_LIMIT"


class ErrorMessages:
    """Centralized error message management with user-friendly messages."""
    
    # Error message templates
    MESSAGES = {
        # Authentication errors
        ErrorCode.INVALID_CREDENTIALS: {
            "message": "Invalid email or password. Please check your credentials and try again.",
            "user_message": "The email or password you entered is incorrect.",
            "action": "Please verify your email and password, then try again."
        },
        ErrorCode.TOKEN_EXPIRED: {
            "message": "Your session has expired. Please log in again.",
            "user_message": "Your session has expired for security reasons.",
            "action": "Please log in again to continue."
        },
        ErrorCode.TOKEN_INVALID: {
            "message": "Invalid authentication token. Please log in again.",
            "user_message": "There was an issue with your session.",
            "action": "Please log in again to continue."
        },
        ErrorCode.TOKEN_MISSING: {
            "message": "Authentication required. Please log in to access this resource.",
            "user_message": "You need to be logged in to access this feature.",
            "action": "Please log in to continue."
        },
        ErrorCode.AUTHENTICATION_REQUIRED: {
            "message": "Authentication required to access this resource.",
            "user_message": "You need to be logged in to access this feature.",
            "action": "Please log in to continue."
        },
        ErrorCode.INSUFFICIENT_PERMISSIONS: {
            "message": "You don't have permission to perform this action.",
            "user_message": "You don't have permission to access this feature.",
            "action": "Contact support if you believe this is an error."
        },
        
        # Registration errors
        ErrorCode.EMAIL_ALREADY_EXISTS: {
            "message": "An account with this email address already exists.",
            "user_message": "This email is already registered.",
            "action": "Try logging in instead, or use a different email address."
        },
        ErrorCode.INVALID_EMAIL_FORMAT: {
            "message": "Please enter a valid email address.",
            "user_message": "The email format is not valid.",
            "action": "Please enter a valid email address (e.g., user@example.com)."
        },
        ErrorCode.WEAK_PASSWORD: {
            "message": "Password does not meet security requirements.",
            "user_message": "Your password is not strong enough.",
            "action": "Use at least 8 characters with uppercase, lowercase, numbers, and special characters."
        },
        ErrorCode.REGISTRATION_FAILED: {
            "message": "Registration failed. Please try again.",
            "user_message": "We couldn't create your account right now.",
            "action": "Please check your information and try again."
        },
        
        # User profile errors
        ErrorCode.USER_NOT_FOUND: {
            "message": "User account not found.",
            "user_message": "We couldn't find your account.",
            "action": "Please check your login credentials or contact support."
        },
        ErrorCode.PROFILE_UPDATE_FAILED: {
            "message": "Failed to update profile. Please try again.",
            "user_message": "We couldn't save your profile changes.",
            "action": "Please check your information and try again."
        },
        ErrorCode.INVALID_USER_DATA: {
            "message": "Invalid user data provided.",
            "user_message": "Some of the information you provided is not valid.",
            "action": "Please check your information and try again."
        },
        ErrorCode.ONBOARDING_INCOMPLETE: {
            "message": "Please complete your profile setup.",
            "user_message": "Your profile setup is incomplete.",
            "action": "Please complete the onboarding process to continue."
        },
        
        # Validation errors
        ErrorCode.VALIDATION_FAILED: {
            "message": "Validation failed for the provided data.",
            "user_message": "Some of the information you provided is not valid.",
            "action": "Please check the highlighted fields and try again."
        },
        ErrorCode.REQUIRED_FIELD_MISSING: {
            "message": "Required field is missing.",
            "user_message": "Please fill in all required fields.",
            "action": "Complete all required fields marked with an asterisk (*)."
        },
        ErrorCode.INVALID_FIELD_VALUE: {
            "message": "Invalid value provided for field.",
            "user_message": "One or more fields contain invalid values.",
            "action": "Please check the highlighted fields and correct any errors."
        },
        ErrorCode.FIELD_TOO_LONG: {
            "message": "Field value is too long.",
            "user_message": "One or more fields are too long.",
            "action": "Please shorten the text in the highlighted fields."
        },
        ErrorCode.FIELD_TOO_SHORT: {
            "message": "Field value is too short.",
            "user_message": "One or more fields are too short.",
            "action": "Please provide more information in the highlighted fields."
        },
        ErrorCode.INVALID_AGE_RANGE: {
            "message": "Age must be between 13 and 100 years.",
            "user_message": "Please enter a valid age.",
            "action": "Age must be between 13 and 100 years."
        },
        ErrorCode.INVALID_ATTENTION_SPAN: {
            "message": "Attention span must be between 5 and 60 minutes.",
            "user_message": "Please enter a valid attention span.",
            "action": "Attention span must be between 5 and 60 minutes."
        },
        
        # System errors
        ErrorCode.DATABASE_ERROR: {
            "message": "Database error occurred. Please try again later.",
            "user_message": "We're experiencing technical difficulties.",
            "action": "Please try again in a few moments. If the problem persists, contact support."
        },
        ErrorCode.NETWORK_ERROR: {
            "message": "Network error occurred. Please check your connection.",
            "user_message": "There seems to be a connection issue.",
            "action": "Please check your internet connection and try again."
        },
        ErrorCode.SERVICE_UNAVAILABLE: {
            "message": "Service is temporarily unavailable.",
            "user_message": "The service is temporarily unavailable.",
            "action": "Please try again in a few minutes."
        },
        ErrorCode.INTERNAL_ERROR: {
            "message": "An internal error occurred. Please try again later.",
            "user_message": "Something went wrong on our end.",
            "action": "Please try again later. If the problem persists, contact support."
        },
        ErrorCode.RATE_LIMIT_EXCEEDED: {
            "message": "Too many requests. Please wait before trying again.",
            "user_message": "You're making requests too quickly.",
            "action": "Please wait a moment before trying again."
        }
    }
    
    @classmethod
    def get_error_response(
        cls, 
        error_code: ErrorCode, 
        field_name: Optional[str] = None,
        custom_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get a standardized error response.
        
        Args:
            error_code: The error code enum
            field_name: Optional field name for validation errors
            custom_message: Optional custom message to override default
            details: Optional additional details
            
        Returns:
            Standardized error response dictionary
        """
        error_info = cls.MESSAGES.get(error_code, {
            "message": "An unknown error occurred.",
            "user_message": "Something went wrong.",
            "action": "Please try again or contact support."
        })
        
        response = {
            "error_code": error_code.value,
            "message": custom_message or error_info["message"],
            "user_message": error_info["user_message"],
            "action": error_info["action"],
            "timestamp": cls._get_timestamp()
        }
        
        if field_name:
            response["field"] = field_name
            
        if details:
            response["details"] = details
            
        return response
    
    @classmethod
    def get_validation_error_response(
        cls,
        field_errors: Dict[str, str],
        general_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a validation error response with field-specific errors.
        
        Args:
            field_errors: Dictionary of field names to error messages
            general_message: Optional general error message
            
        Returns:
            Standardized validation error response
        """
        return {
            "error_code": ErrorCode.VALIDATION_FAILED.value,
            "message": general_message or "Validation failed for one or more fields.",
            "user_message": "Please correct the errors below and try again.",
            "action": "Check the highlighted fields and correct any errors.",
            "field_errors": field_errors,
            "timestamp": cls._get_timestamp()
        }
    
    @classmethod
    def get_success_response(
        cls,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get a standardized success response.
        
        Args:
            message: Success message
            data: Optional data to include
            
        Returns:
            Standardized success response
        """
        response = {
            "success": True,
            "message": message,
            "timestamp": cls._get_timestamp()
        }
        
        if data:
            response["data"] = data
            
        return response
    
    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"


# Convenience functions for common error scenarios
def authentication_error(message: Optional[str] = None) -> Dict[str, Any]:
    """Get authentication error response."""
    return ErrorMessages.get_error_response(
        ErrorCode.INVALID_CREDENTIALS,
        custom_message=message
    )

def validation_error(field_errors: Dict[str, str]) -> Dict[str, Any]:
    """Get validation error response."""
    return ErrorMessages.get_validation_error_response(field_errors)

def user_not_found_error() -> Dict[str, Any]:
    """Get user not found error response."""
    return ErrorMessages.get_error_response(ErrorCode.USER_NOT_FOUND)

def email_exists_error() -> Dict[str, Any]:
    """Get email already exists error response."""
    return ErrorMessages.get_error_response(ErrorCode.EMAIL_ALREADY_EXISTS)

def weak_password_error() -> Dict[str, Any]:
    """Get weak password error response."""
    return ErrorMessages.get_error_response(ErrorCode.WEAK_PASSWORD)

def token_expired_error() -> Dict[str, Any]:
    """Get token expired error response."""
    return ErrorMessages.get_error_response(ErrorCode.TOKEN_EXPIRED)

def internal_error() -> Dict[str, Any]:
    """Get internal error response."""
    return ErrorMessages.get_error_response(ErrorCode.INTERNAL_ERROR)

def success_response(message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get success response."""
    return ErrorMessages.get_success_response(message, data)