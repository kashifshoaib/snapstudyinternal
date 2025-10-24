"""Unit tests for JWT service."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import jwt
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock settings before importing
class MockSettings:
    jwt_secret_key = "test_secret_key_for_testing"
    jwt_algorithm = "HS256"
    jwt_expiration_hours = 24

# Mock the config module
sys.modules['config'] = MagicMock()
sys.modules['config'].settings = MockSettings()

from services.jwt_service import JWTService


class TestJWTService:
    """Test cases for JWTService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.jwt_service = JWTService()

    def test_generate_token_default_expiration(self):
        """Test token generation with default expiration."""
        user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com',
            'full_name': 'Test User'
        }
        
        token = self.jwt_service.generate_token(user_data)
        
        # Token should be a string
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode token to verify contents
        payload = jwt.decode(
            token, 
            self.jwt_service.secret_key, 
            algorithms=[self.jwt_service.algorithm]
        )
        
        assert payload['user_id'] == user_data['user_id']
        assert payload['email'] == user_data['email']
        assert payload['full_name'] == user_data['full_name']
        assert payload['type'] == 'access'
        assert 'exp' in payload
        assert 'iat' in payload

    def test_generate_token_custom_expiration(self):
        """Test token generation with custom expiration."""
        user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com'
        }
        custom_expiration = timedelta(hours=1)
        
        token = self.jwt_service.generate_token(user_data, custom_expiration)
        
        # Decode token to verify expiration
        payload = jwt.decode(
            token, 
            self.jwt_service.secret_key, 
            algorithms=[self.jwt_service.algorithm]
        )
        
        # Check that expiration is approximately 1 hour from now
        exp_time = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
        expected_exp = datetime.now(timezone.utc) + custom_expiration
        
        # Allow 1 minute tolerance
        assert abs((exp_time - expected_exp).total_seconds()) < 60

    def test_generate_refresh_token(self):
        """Test refresh token generation."""
        user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com',
            'full_name': 'Test User'
        }
        
        refresh_token = self.jwt_service.generate_refresh_token(user_data)
        
        # Token should be a string
        assert isinstance(refresh_token, str)
        assert len(refresh_token) > 0
        
        # Decode token to verify contents
        payload = jwt.decode(
            refresh_token, 
            self.jwt_service.secret_key, 
            algorithms=[self.jwt_service.algorithm]
        )
        
        assert payload['user_id'] == user_data['user_id']
        assert payload['email'] == user_data['email']
        assert payload['type'] == 'refresh'
        assert 'exp' in payload
        assert 'iat' in payload
        
        # Refresh token should have longer expiration (7 days)
        exp_time = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
        expected_exp = datetime.now(timezone.utc) + timedelta(days=7)
        
        # Allow 1 minute tolerance
        assert abs((exp_time - expected_exp).total_seconds()) < 60

    def test_validate_token_valid(self):
        """Test token validation with valid token."""
        user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com',
            'full_name': 'Test User'
        }
        
        token = self.jwt_service.generate_token(user_data)
        payload = self.jwt_service.validate_token(token)
        
        assert payload is not None
        assert payload['user_id'] == user_data['user_id']
        assert payload['email'] == user_data['email']
        assert payload['full_name'] == user_data['full_name']
        assert payload['type'] == 'access'

    def test_validate_token_invalid_signature(self):
        """Test token validation with invalid signature."""
        user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com'
        }
        
        # Generate token with different secret
        invalid_token = jwt.encode(
            user_data, 
            'wrong_secret', 
            algorithm='HS256'
        )
        
        payload = self.jwt_service.validate_token(invalid_token)
        assert payload is None

    def test_validate_token_expired(self):
        """Test token validation with expired token."""
        user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com',
            'exp': datetime.now(timezone.utc) - timedelta(hours=1),  # Expired 1 hour ago
            'type': 'access'
        }
        
        expired_token = jwt.encode(
            user_data, 
            self.jwt_service.secret_key, 
            algorithm=self.jwt_service.algorithm
        )
        
        payload = self.jwt_service.validate_token(expired_token)
        assert payload is None

    def test_validate_token_wrong_type(self):
        """Test token validation with wrong token type."""
        user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com',
            'exp': datetime.now(timezone.utc) + timedelta(hours=1),
            'type': 'refresh'  # Wrong type for access token validation
        }
        
        token = jwt.encode(
            user_data, 
            self.jwt_service.secret_key, 
            algorithm=self.jwt_service.algorithm
        )
        
        payload = self.jwt_service.validate_token(token)
        assert payload is None

    def test_validate_refresh_token_valid(self):
        """Test refresh token validation with valid token."""
        user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com'
        }
        
        refresh_token = self.jwt_service.generate_refresh_token(user_data)
        payload = self.jwt_service.validate_refresh_token(refresh_token)
        
        assert payload is not None
        assert payload['user_id'] == user_data['user_id']
        assert payload['email'] == user_data['email']
        assert payload['type'] == 'refresh'

    def test_validate_refresh_token_wrong_type(self):
        """Test refresh token validation with wrong token type."""
        user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com'
        }
        
        # Generate access token instead of refresh token
        access_token = self.jwt_service.generate_token(user_data)
        payload = self.jwt_service.validate_refresh_token(access_token)
        
        assert payload is None

    def test_refresh_access_token_valid(self):
        """Test access token refresh with valid refresh token."""
        user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com',
            'full_name': 'Test User'
        }
        
        refresh_token = self.jwt_service.generate_refresh_token(user_data)
        result = self.jwt_service.refresh_access_token(refresh_token, user_data)
        
        assert 'access_token' in result
        assert result['token_type'] == 'bearer'
        assert result['expires_in'] == 24 * 3600  # 24 hours in seconds
        assert 'refreshed_at' in result
        
        # Verify new access token is valid
        new_payload = self.jwt_service.validate_token(result['access_token'])
        assert new_payload is not None
        assert new_payload['user_id'] == user_data['user_id']

    def test_refresh_access_token_invalid_refresh_token(self):
        """Test access token refresh with invalid refresh token."""
        user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com'
        }
        
        invalid_refresh_token = "invalid.token.here"
        
        with pytest.raises(HTTPException) as exc_info:
            self.jwt_service.refresh_access_token(invalid_refresh_token, user_data)
        
        assert exc_info.value.status_code == 401
        assert "Invalid or expired refresh token" in str(exc_info.value.detail)

    def test_refresh_access_token_user_mismatch(self):
        """Test access token refresh with user mismatch."""
        user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com'
        }
        
        different_user_data = {
            'user_id': 'different_user_456',
            'email': 'different@example.com'
        }
        
        refresh_token = self.jwt_service.generate_refresh_token(user_data)
        
        with pytest.raises(HTTPException) as exc_info:
            self.jwt_service.refresh_access_token(refresh_token, different_user_data)
        
        assert exc_info.value.status_code == 401
        assert "Refresh token user mismatch" in str(exc_info.value.detail)

    def test_decode_token_without_verification(self):
        """Test token decoding without verification."""
        user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com',
            'exp': datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
            'type': 'access'
        }
        
        token = jwt.encode(
            user_data, 
            self.jwt_service.secret_key, 
            algorithm=self.jwt_service.algorithm
        )
        
        payload = self.jwt_service.decode_token_without_verification(token)
        
        assert payload is not None
        assert payload['user_id'] == user_data['user_id']
        assert payload['email'] == user_data['email']

    def test_get_token_expiration(self):
        """Test getting token expiration time."""
        user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com'
        }
        
        token = self.jwt_service.generate_token(user_data)
        expiration = self.jwt_service.get_token_expiration(token)
        
        assert expiration is not None
        assert isinstance(expiration, datetime)
        
        # Should be approximately 24 hours from now
        expected_exp = datetime.now(timezone.utc) + timedelta(hours=24)
        assert abs((expiration - expected_exp).total_seconds()) < 60

    def test_is_token_expired_valid(self):
        """Test token expiration check with valid token."""
        user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com'
        }
        
        token = self.jwt_service.generate_token(user_data)
        is_expired = self.jwt_service.is_token_expired(token)
        
        assert is_expired is False

    def test_is_token_expired_expired(self):
        """Test token expiration check with expired token."""
        user_data = {
            'user_id': 'test_user_123',
            'email': 'test@example.com',
            'exp': datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
            'type': 'access'
        }
        
        expired_token = jwt.encode(
            user_data, 
            self.jwt_service.secret_key, 
            algorithm=self.jwt_service.algorithm
        )
        
        is_expired = self.jwt_service.is_token_expired(expired_token)
        assert is_expired is True