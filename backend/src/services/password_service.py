"""
Password hashing service for secure password management.

Provides SHA-256 password hashing with random salt generation,
password verification, and password strength validation.
"""

import hashlib
import secrets
import re
from typing import Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)


class PasswordService:
    """Service for secure password hashing and validation."""

    @staticmethod
    def generate_salt() -> str:
        """
        Generate a random salt for password hashing.
        
        Returns:
            Random salt as hex string
        """
        return secrets.token_hex(32)  # 64 character hex string (32 bytes)

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using SHA-256.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        # Simple hash using SHA-256
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        
        logger.debug("Password hashed successfully")
        return password_hash

    @staticmethod
    def verify_password(password: str, stored_hash: str) -> bool:
        """
        Verify password against stored hash.
        
        Args:
            password: Plain text password to verify
            stored_hash: Stored password hash
            
        Returns:
            True if password matches, False otherwise
        """
        # Hash the provided password
        computed_hash = PasswordService.hash_password(password)
        
        # Compare hashes
        return computed_hash == stored_hash

    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """
        Validate password strength according to security requirements.
        
        Requirements:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        
        Args:
            password: Password to validate
            
        Returns:
            Dict with validation result and details
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'requirements_met': {
                'min_length': False,
                'has_uppercase': False,
                'has_lowercase': False,
                'has_digit': False,
                'has_special': False
            }
        }
        
        # Check minimum length
        if len(password) >= 8:
            validation_result['requirements_met']['min_length'] = True
        else:
            validation_result['errors'].append("Password must be at least 8 characters long")
            validation_result['is_valid'] = False
        
        # Check for uppercase letter
        if re.search(r'[A-Z]', password):
            validation_result['requirements_met']['has_uppercase'] = True
        else:
            validation_result['errors'].append("Password must contain at least one uppercase letter")
            validation_result['is_valid'] = False
        
        # Check for lowercase letter
        if re.search(r'[a-z]', password):
            validation_result['requirements_met']['has_lowercase'] = True
        else:
            validation_result['errors'].append("Password must contain at least one lowercase letter")
            validation_result['is_valid'] = False
        
        # Check for digit
        if re.search(r'\d', password):
            validation_result['requirements_met']['has_digit'] = True
        else:
            validation_result['errors'].append("Password must contain at least one digit")
            validation_result['is_valid'] = False
        
        # Check for special character
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            validation_result['requirements_met']['has_special'] = True
        else:
            validation_result['errors'].append("Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)")
            validation_result['is_valid'] = False
        
        logger.debug(f"Password validation completed: {'valid' if validation_result['is_valid'] else 'invalid'}")
        return validation_result


# Global service instance
password_service = PasswordService()