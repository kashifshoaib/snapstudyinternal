"""Unit tests for DynamoDB service."""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timezone
import uuid

from src.services.dynamodb import DynamoDBService
from src.middleware.error_handler import (
    ResourceNotFoundError, 
    ValidationError,
    ResourceConflictError
)


class TestDynamoDBService:
    """Test cases for DynamoDBService."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch('src.services.dynamodb.boto3'), \
             patch('src.services.dynamodb.settings') as mock_settings:
            
            mock_settings.aws_region = 'us-east-1'
            mock_settings.users_table = 'test-users'
            mock_settings.lessons_table = 'test-lessons'
            mock_settings.micro_lessons_table = 'test-micro-lessons'
            mock_settings.quizzes_table = 'test-quizzes'
            mock_settings.user_engagement_table = 'test-engagement'
            mock_settings.chat_history_table = 'test-chat'
            
            self.db_service = DynamoDBService()
            
            # Mock tables
            self.mock_users_table = Mock()
            self.mock_lessons_table = Mock()
            self.mock_micro_lessons_table = Mock()
            self.mock_quizzes_table = Mock()
            self.mock_user_engagement_table = Mock()
            self.mock_chat_history_table = Mock()
            
            self.db_service.users_table = self.mock_users_table
            self.db_service.lessons_table = self.mock_lessons_table
            self.db_service.micro_lessons_table = self.mock_micro_lessons_table
            self.db_service.quizzes_table = self.mock_quizzes_table
            self.db_service.user_engagement_table = self.mock_user_engagement_table
            self.db_service.chat_history_table = self.mock_chat_history_table

    def test_serialize_item_basic_types(self):
        """Test serialization of basic data types."""
        item = {
            'string_field': 'test',
            'int_field': 123,
            'float_field': 123.45,
            'bool_field': True,
            'none_field': None
        }
        
        serialized = self.db_service._serialize_item(item)
        
        assert serialized['string_field'] == 'test'
        assert serialized['int_field'] == 123
        assert str(serialized['float_field']) == '123.45'  # Decimal conversion
        assert serialized['bool_field'] is True
        assert serialized['none_field'] is None

    def test_serialize_item_datetime(self):
        """Test serialization of datetime objects."""
        now = datetime.now(timezone.utc)
        item = {'timestamp': now}
        
        serialized = self.db_service._serialize_item(item)
        
        assert serialized['timestamp'] == now.isoformat()

    def test_serialize_item_nested(self):
        """Test serialization of nested structures."""
        item = {
            'nested_dict': {
                'inner_string': 'test',
                'inner_float': 123.45
            },
            'nested_list': [1, 2.5, 'test']
        }
        
        serialized = self.db_service._serialize_item(item)
        
        assert serialized['nested_dict']['inner_string'] == 'test'
        assert str(serialized['nested_dict']['inner_float']) == '123.45'
        assert serialized['nested_list'][0] == 1
        assert str(serialized['nested_list'][1]) == '2.5'
        assert serialized['nested_list'][2] == 'test'

    def test_deserialize_item_basic_types(self):
        """Test deserialization of basic data types."""
        from decimal import Decimal
        
        item = {
            'string_field': 'test',
            'int_field': 123,
            'decimal_field': Decimal('123.45'),
            'bool_field': True
        }
        
        deserialized = self.db_service._deserialize_item(item)
        
        assert deserialized['string_field'] == 'test'
        assert deserialized['int_field'] == 123
        assert deserialized['decimal_field'] == 123.45  # Decimal to float
        assert deserialized['bool_field'] is True

    @pytest.mark.asyncio
    async def test_create_user_valid(self):
        """Test user creation with valid data."""
        user_data = {
            'email': 'test@example.com',
            'password_hash': 'hashed_password',
            'full_name': 'Test User',
            'age': 25
        }
        
        # Mock successful put_item
        self.mock_users_table.put_item.return_value = None
        
        # Mock get_user_by_email to return None (user doesn't exist)
        with patch.object(self.db_service, 'get_user_by_email', return_value=None):
            result = await self.db_service.create_user(user_data)
        
        # Verify put_item was called
        self.mock_users_table.put_item.assert_called_once()
        
        # Verify result structure
        assert result['email'] == 'test@example.com'
        assert result['full_name'] == 'Test User'
        assert result['age'] == 25
        assert 'user_id' in result
        assert 'created_at' in result
        assert 'updated_at' in result
        assert result['is_active'] is True
        assert result['onboarding_completed'] is False

    @pytest.mark.asyncio
    async def test_create_user_missing_email(self):
        """Test user creation with missing email."""
        user_data = {
            'password_hash': 'hashed_password'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            await self.db_service.create_user(user_data)
        
        assert "Email is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_user_missing_password_hash(self):
        """Test user creation with missing password hash."""
        user_data = {
            'email': 'test@example.com'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            await self.db_service.create_user(user_data)
        
        assert "Password hash is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self):
        """Test user creation with duplicate email."""
        user_data = {
            'email': 'test@example.com',
            'password_hash': 'hashed_password'
        }
        
        # Mock get_user_by_email to return existing user
        existing_user = {'user_id': 'existing_123', 'email': 'test@example.com'}
        with patch.object(self.db_service, 'get_user_by_email', return_value=existing_user):
            with pytest.raises(ResourceConflictError) as exc_info:
                await self.db_service.create_user(user_data)
        
        assert "email" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_user_by_id_found(self):
        """Test getting user by ID when user exists."""
        user_id = 'test_user_123'
        mock_user = {
            'user_id': user_id,
            'email': 'test@example.com',
            'full_name': 'Test User'
        }
        
        # Mock successful get_item
        self.mock_users_table.get_item.return_value = {'Item': mock_user}
        
        result = await self.db_service.get_user_by_id(user_id)
        
        # Verify get_item was called with correct key
        self.mock_users_table.get_item.assert_called_once_with(Key={'user_id': user_id})
        
        # Verify result
        assert result['user_id'] == user_id
        assert result['email'] == 'test@example.com'
        assert result['full_name'] == 'Test User'

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self):
        """Test getting user by ID when user doesn't exist."""
        user_id = 'nonexistent_user'
        
        # Mock get_item returning no item
        self.mock_users_table.get_item.return_value = {}
        
        result = await self.db_service.get_user_by_id(user_id)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_by_id_empty_id(self):
        """Test getting user by ID with empty ID."""
        with pytest.raises(ValidationError) as exc_info:
            await self.db_service.get_user_by_id('')
        
        assert "User ID is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_user_by_email_found(self):
        """Test getting user by email when user exists."""
        email = 'test@example.com'
        mock_user = {
            'user_id': 'test_user_123',
            'email': email,
            'full_name': 'Test User'
        }
        
        # Mock successful query
        self.mock_users_table.query.return_value = {'Items': [mock_user]}
        
        result = await self.db_service.get_user_by_email(email)
        
        # Verify query was called with correct parameters
        self.mock_users_table.query.assert_called_once()
        call_args = self.mock_users_table.query.call_args
        assert call_args[1]['IndexName'] == 'email-index'
        
        # Verify result
        assert result['user_id'] == 'test_user_123'
        assert result['email'] == email
        assert result['full_name'] == 'Test User'

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self):
        """Test getting user by email when user doesn't exist."""
        email = 'nonexistent@example.com'
        
        # Mock query returning no items
        self.mock_users_table.query.return_value = {'Items': []}
        
        result = await self.db_service.get_user_by_email(email)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_by_email_empty_email(self):
        """Test getting user by email with empty email."""
        with pytest.raises(ValidationError) as exc_info:
            await self.db_service.get_user_by_email('')
        
        assert "Email is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_user_valid(self):
        """Test user update with valid data."""
        user_id = 'test_user_123'
        updates = {
            'full_name': 'Updated Name',
            'age': 30,
            'profession': 'Senior Engineer'
        }
        
        # Mock existing user
        existing_user = {'user_id': user_id, 'email': 'test@example.com'}
        
        # Mock updated user response
        updated_user = {
            'user_id': user_id,
            'email': 'test@example.com',
            'full_name': 'Updated Name',
            'age': 30,
            'profession': 'Senior Engineer'
        }
        
        with patch.object(self.db_service, 'get_user_by_id', return_value=existing_user):
            # Mock successful update_item
            self.mock_users_table.update_item.return_value = {'Attributes': updated_user}
            
            result = await self.db_service.update_user(user_id, updates)
        
        # Verify update_item was called
        self.mock_users_table.update_item.assert_called_once()
        
        # Verify result
        assert result['user_id'] == user_id
        assert result['full_name'] == 'Updated Name'
        assert result['age'] == 30
        assert result['profession'] == 'Senior Engineer'

    @pytest.mark.asyncio
    async def test_update_user_not_found(self):
        """Test user update when user doesn't exist."""
        user_id = 'nonexistent_user'
        updates = {'full_name': 'Updated Name'}
        
        # Mock get_user_by_id to return None
        with patch.object(self.db_service, 'get_user_by_id', return_value=None):
            with pytest.raises(ResourceNotFoundError) as exc_info:
                await self.db_service.update_user(user_id, updates)
        
        assert "User" in str(exc_info.value)
        assert user_id in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_user_empty_updates(self):
        """Test user update with empty updates."""
        user_id = 'test_user_123'
        updates = {}
        
        with pytest.raises(ValidationError) as exc_info:
            await self.db_service.update_user(user_id, updates)
        
        assert "No updates provided" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_user_empty_id(self):
        """Test user update with empty user ID."""
        updates = {'full_name': 'Updated Name'}
        
        with pytest.raises(ValidationError) as exc_info:
            await self.db_service.update_user('', updates)
        
        assert "User ID is required" in str(exc_info.value)

    def test_health_check_success(self):
        """Test successful health check."""
        # Mock successful table load
        self.mock_users_table.load.return_value = None
        
        result = self.db_service.health_check()
        
        assert result['status'] == 'healthy'
        assert result['service'] == 'dynamodb'

    def test_health_check_failure(self):
        """Test health check failure."""
        from src.middleware.error_handler import ServiceUnavailableError
        
        # Mock table load failure
        self.mock_users_table.load.side_effect = Exception('Connection failed')
        
        with pytest.raises(ServiceUnavailableError) as exc_info:
            self.db_service.health_check()
        
        assert "DynamoDB" in str(exc_info.value)
        assert "Health check failed" in str(exc_info.value)

    def test_get_item_sync_found(self):
        """Test synchronous get_item when item exists."""
        table_name = 'users'
        key = {'user_id': 'test_user_123'}
        mock_item = {'user_id': 'test_user_123', 'email': 'test@example.com'}
        
        # Mock successful get_item
        self.mock_users_table.get_item.return_value = {'Item': mock_item}
        
        result = self.db_service.get_item_sync(table_name, key)
        
        # Verify get_item was called with correct key
        self.mock_users_table.get_item.assert_called_once_with(Key=key)
        
        # Verify result
        assert result['user_id'] == 'test_user_123'
        assert result['email'] == 'test@example.com'

    def test_get_item_sync_not_found(self):
        """Test synchronous get_item when item doesn't exist."""
        table_name = 'users'
        key = {'user_id': 'nonexistent_user'}
        
        # Mock get_item returning no item
        self.mock_users_table.get_item.return_value = {}
        
        result = self.db_service.get_item_sync(table_name, key)
        
        assert result is None

    def test_put_item_sync_success(self):
        """Test synchronous put_item success."""
        table_name = 'users'
        item = {'user_id': 'test_user_123', 'email': 'test@example.com'}
        
        # Mock successful put_item
        self.mock_users_table.put_item.return_value = None
        
        result = self.db_service.put_item_sync(table_name, item)
        
        # Verify put_item was called
        self.mock_users_table.put_item.assert_called_once()
        
        # Verify result is the original item
        assert result == item