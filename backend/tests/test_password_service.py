"""Unit tests for password service."""

import pytest
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.password_service import PasswordService


class TestPasswordService:
    """Test cases for PasswordService."""

    def test_generate_salt(self):
        """Test salt generation."""
        salt1 = PasswordService.generate_salt()
        salt2 = PasswordService.generate_salt()
        
        # Salts should be different
        assert salt1 != salt2
        
        # Salt should be 64 characters (32 bytes as hex)
        assert len(salt1) == 64
        assert len(salt2) == 64
        
        # Salt should be valid hex
        assert all(c in '0123456789abcdef' for c in salt1)
        assert all(c in '0123456789abcdef' for c in salt2)

    def test_hash_password_with_salt(self):
        """Test password hashing with provided salt."""
        password = "TestPassword123!"
        salt = "test_salt_123"
        
        hash1, returned_salt1 = PasswordService.hash_password(password, salt)
        hash2, returned_salt2 = PasswordService.hash_password(password, salt)
        
        # Same password and salt should produce same hash
        assert hash1 == hash2
        assert returned_salt1 == salt
        assert returned_salt2 == salt
        
        # Hash should be 64 characters (SHA-256 hex)
        assert len(hash1) == 64

    def test_hash_password_without_salt(self):
        """Test password hashing with auto-generated salt."""
        password = "TestPassword123!"
        
        hash1, salt1 = PasswordService.hash_password(password)
        hash2, salt2 = PasswordService.hash_password(password)
        
        # Different salts should produce different hashes
        assert hash1 != hash2
        assert salt1 != salt2
        
        # Both should be valid lengths
        assert len(hash1) == 64
        assert len(hash2) == 64
        assert len(salt1) == 64
        assert len(salt2) == 64

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "TestPassword123!"
        hash_value, salt = PasswordService.hash_password(password)
        
        # Correct password should verify
        assert PasswordService.verify_password(password, hash_value, salt) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hash_value, salt = PasswordService.hash_password(password)
        
        # Wrong password should not verify
        assert PasswordService.verify_password(wrong_password, hash_value, salt) is False

    def test_validate_password_strength_valid(self):
        """Test password strength validation with valid password."""
        valid_password = "TestPassword123!"
        result = PasswordService.validate_password_strength(valid_password)
        
        assert result['is_valid'] is True
        assert len(result['errors']) == 0
        assert result['requirements_met']['min_length'] is True
        assert result['requirements_met']['has_uppercase'] is True
        assert result['requirements_met']['has_lowercase'] is True
        assert result['requirements_met']['has_digit'] is True
        assert result['requirements_met']['has_special'] is True

    def test_validate_password_strength_too_short(self):
        """Test password strength validation with short password."""
        short_password = "Test1!"
        result = PasswordService.validate_password_strength(short_password)
        
        assert result['is_valid'] is False
        assert "Password must be at least 8 characters long" in result['errors']
        assert result['requirements_met']['min_length'] is False

    def test_validate_password_strength_no_uppercase(self):
        """Test password strength validation without uppercase."""
        password = "testpassword123!"
        result = PasswordService.validate_password_strength(password)
        
        assert result['is_valid'] is False
        assert "Password must contain at least one uppercase letter" in result['errors']
        assert result['requirements_met']['has_uppercase'] is False

    def test_validate_password_strength_no_lowercase(self):
        """Test password strength validation without lowercase."""
        password = "TESTPASSWORD123!"
        result = PasswordService.validate_password_strength(password)
        
        assert result['is_valid'] is False
        assert "Password must contain at least one lowercase letter" in result['errors']
        assert result['requirements_met']['has_lowercase'] is False

    def test_validate_password_strength_no_digit(self):
        """Test password strength validation without digit."""
        password = "TestPassword!"
        result = PasswordService.validate_password_strength(password)
        
        assert result['is_valid'] is False
        assert "Password must contain at least one digit" in result['errors']
        assert result['requirements_met']['has_digit'] is False

    def test_validate_password_strength_no_special(self):
        """Test password strength validation without special character."""
        password = "TestPassword123"
        result = PasswordService.validate_password_strength(password)
        
        assert result['is_valid'] is False
        assert "Password must contain at least one special character" in result['errors']
        assert result['requirements_met']['has_special'] is False

    def test_validate_password_strength_multiple_failures(self):
        """Test password strength validation with multiple failures."""
        weak_password = "test"
        result = PasswordService.validate_password_strength(weak_password)
        
        assert result['is_valid'] is False
        assert len(result['errors']) == 4  # Missing uppercase, digit, special, and too short
        assert result['requirements_met']['min_length'] is False
        assert result['requirements_met']['has_uppercase'] is False
        assert result['requirements_met']['has_digit'] is False
        assert result['requirements_met']['has_special'] is False
        assert result['requirements_met']['has_lowercase'] is True  # Only lowercase present