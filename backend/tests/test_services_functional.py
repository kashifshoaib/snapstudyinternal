#!/usr/bin/env python3
"""
Functional Tests for Backend Services

Tests all backend services including DynamoDB, Auth, AWS integrations, etc.
"""

import pytest
import asyncio
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.dynamodb import DynamoDBService
from src.services.auth import AuthService
from src.middleware.error_handler import handle_aws_error, ServiceUnavailableError
from src.utils.retry import retry_async, RetryConfig
from botocore.exceptions import ClientError, NoCredentialsError


class TestDynamoDBServiceDetailed:
    """Detailed tests for DynamoDB service operations."""
    
    @pytest.fixture
    def db_service(self):
        """Create DynamoDB service instance."""
        return DynamoDBService()
    
    @pytest.fixture
    def sample_user(self):
        """Sample user data."""
        return {
            'user_id': str(uuid.uuid4()),
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'learning_style': 'visual',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
    
    def test_initialization_success(self, db_service):
        """Test successful DynamoDB service initialization."""
        with patch.object(db_service, 'users_table') as mock_users_table:
            with patch.object(db_service, 'lessons_table') as mock_lessons_table:
                with patch.object(db_service, 'micro_lessons_table') as mock_micro_lessons_table:
                    with patch.object(db_service, 'quizzes_table') as mock_quizzes_table:
                        with patch.object(db_service, 'user_engagement_table') as mock_engagement_table:
                            with patch.object(db_service, 'chat_history_table') as mock_chat_table:
                                # Mock all table loads to succeed
                                mock_users_table.load.return_value = None
                                mock_lessons_table.load.return_value = None
                                mock_micro_lessons_table.load.return_value = None
                                mock_quizzes_table.load.return_value = None
                                mock_engagement_table.load.return_value = None
                                mock_chat_table.load.return_value = None
                                
                                # Should not raise exception
                                db_service.initialize()
                                
                                # Verify all tables were checked
                                assert mock_users_table.load.called
                                assert mock_lessons_table.load.called
    
    def test_initialization_failure(self, db_service):
        """Test DynamoDB service initialization failure."""
        with patch.object(db_service, 'users_table') as mock_table:
            mock_table.load.side_effect = Exception("Table not found")
            
            with pytest.raises(ServiceUnavailableError):
                db_service.initialize()
    
    def test_health_check_success(self, db_service):
        """Test successful health check."""
        with patch.object(db_service, 'users_table') as mock_table:
            mock_table.load.return_value = None
            
            result = db_service.health_check()
            
            assert result['status'] == 'healthy'
            assert result['service'] == 'dynamodb'
    
    def test_health_check_failure(self, db_service):
        """Test health check failure."""
        with patch.object(db_service, 'users_table') as mock_table:
            mock_table.load.side_effect = Exception("Connection failed")
            
            with pytest.raises(ServiceUnavailableError):
                db_service.health_check()
    
    def test_serialize_complex_data(self, db_service):
        """Test serialization of complex data structures."""
        complex_data = {
            'nested_dict': {
                'inner_dict': {
                    'float_value': 123.456,
                    'datetime_value': datetime.now(timezone.utc),
                    'list_value': [1.1, 2.2, 3.3]
                }
            },
            'list_of_dicts': [
                {'id': 1, 'value': 10.5},
                {'id': 2, 'value': 20.7}
            ]
        }
        
        serialized = db_service._serialize_item(complex_data)
        
        # Check nested serialization
        inner_dict = serialized['nested_dict']['inner_dict']
        assert isinstance(inner_dict['float_value'], Decimal)
        assert isinstance(inner_dict['datetime_value'], str)
        assert all(isinstance(x, Decimal) for x in inner_dict['list_value'])
        
        # Check list of dicts
        for item in serialized['list_of_dicts']:
            assert isinstance(item['value'], Decimal)
    
    @pytest.mark.asyncio
    async def test_get_item_async_wrapper(self, db_service):
        """Test async wrapper for get_item."""
        with patch.object(db_service, 'get_item_sync') as mock_sync:
            mock_sync.return_value = {'user_id': '123', 'email': 'test@example.com'}
            
            result = await db_service.get_item('users', {'user_id': '123'})
            
            assert result['user_id'] == '123'
            mock_sync.assert_called_once_with('users', {'user_id': '123'})
    
    @pytest.mark.asyncio
    async def test_put_item_async_wrapper(self, db_service):
        """Test async wrapper for put_item."""
        with patch.object(db_service, 'put_item_sync') as mock_sync:
            test_item = {'user_id': '123', 'email': 'test@example.com'}
            mock_sync.return_value = test_item
            
            result = await db_service.put_item('users', test_item)
            
            assert result == test_item
            mock_sync.assert_called_once_with('users', test_item)
    
    @pytest.mark.asyncio
    async def test_user_operations_flow(self, db_service, sample_user):
        """Test complete user operations flow."""
        with patch.object(db_service, 'users_table') as mock_table:
            # Test user creation
            mock_table.put_item.return_value = None
            
            created_user = await db_service.create_user({
                'email': sample_user['email'],
                'first_name': sample_user['first_name'],
                'last_name': sample_user['last_name']
            })
            
            assert 'user_id' in created_user
            assert created_user['email'] == sample_user['email']
            
            # Test user retrieval
            mock_table.get_item.return_value = {'Item': created_user}
            
            retrieved_user = await db_service.get_user_by_id(created_user['user_id'])
            
            assert retrieved_user['user_id'] == created_user['user_id']
            assert retrieved_user['email'] == sample_user['email']
            
            # Test user update
            mock_table.update_item.return_value = {
                'Attributes': {**created_user, 'first_name': 'Updated'}
            }
            
            updated_user = await db_service.update_user(
                created_user['user_id'],
                {'first_name': 'Updated'}
            )
            
            assert updated_user['first_name'] == 'Updated'
    
    @pytest.mark.asyncio
    async def test_lesson_operations_flow(self, db_service):
        """Test complete lesson operations flow."""
        user_id = str(uuid.uuid4())
        
        with patch.object(db_service, 'lessons_table') as mock_table:
            # Test lesson creation
            mock_table.put_item.return_value = None
            
            lesson_data = {
                'user_id': user_id,
                'title': 'Python Basics',
                'content_type': 'pdf',
                'status': 'processing'
            }
            
            created_lesson = await db_service.create_lesson(lesson_data)
            
            assert 'lesson_id' in created_lesson
            assert created_lesson['title'] == 'Python Basics'
            assert created_lesson['user_id'] == user_id
            
            # Test lesson retrieval
            mock_table.get_item.return_value = {'Item': created_lesson}
            
            retrieved_lesson = await db_service.get_lesson(created_lesson['lesson_id'])
            
            assert retrieved_lesson['lesson_id'] == created_lesson['lesson_id']
            
            # Test user lessons query
            mock_table.query.return_value = {'Items': [created_lesson]}
            
            user_lessons = await db_service.get_user_lessons(user_id)
            
            assert len(user_lessons) == 1
            assert user_lessons[0]['lesson_id'] == created_lesson['lesson_id']
    
    @pytest.mark.asyncio
    async def test_engagement_tracking(self, db_service):
        """Test engagement tracking functionality."""
        with patch.object(db_service, 'user_engagement_table') as mock_table:
            mock_table.put_item.return_value = None
            
            engagement_data = {
                'user_id': str(uuid.uuid4()),
                'event_type': 'lesson_started',
                'lesson_id': str(uuid.uuid4()),
                'session_id': str(uuid.uuid4())
            }
            
            result = await db_service.track_engagement(engagement_data)
            
            assert 'engagement_id' in result
            assert 'timestamp' in result
            assert result['user_id'] == engagement_data['user_id']
            assert result['event_type'] == engagement_data['event_type']
    
    @pytest.mark.asyncio
    async def test_chat_session_operations(self, db_service):
        """Test chat session operations."""
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        
        with patch.object(db_service, 'chat_history_table') as mock_table:
            # Test session creation
            mock_table.put_item.return_value = None
            
            session_data = {
                'session_id': session_id,
                'user_id': user_id
            }
            
            created_session = await db_service.create_chat_session(session_data)
            
            assert created_session['session_id'] == session_id
            assert created_session['user_id'] == user_id
            assert 'ttl' in created_session
            assert created_session['messages'] == []
            
            # Test adding messages
            mock_table.get_item.return_value = {'Item': created_session}
            mock_table.update_item.return_value = {
                'Attributes': {
                    **created_session,
                    'messages': [
                        {'role': 'user', 'content': 'Hello'},
                        {'role': 'assistant', 'content': 'Hi there!'}
                    ]
                }
            }
            
            await db_service.add_chat_message(
                session_id, user_id, 'Hello', 'Hi there!'
            )
            
            # Verify update was called
            mock_table.update_item.assert_called()


class TestAuthServiceDetailed:
    """Detailed tests for authentication service."""
    
    @pytest.fixture
    def auth_service(self):
        """Create auth service instance."""
        return AuthService()
    
    @pytest.mark.asyncio
    async def test_authenticate_user_placeholder(self, auth_service):
        """Test user authentication (placeholder implementation)."""
        result = await auth_service.authenticate_user('test@example.com', 'password')
        
        # Placeholder implementation returns mock data
        assert 'user_id' in result
        assert result['email'] == 'test@example.com'
        assert 'access_token' in result
    
    @pytest.mark.asyncio
    async def test_register_user_placeholder(self, auth_service):
        """Test user registration (placeholder implementation)."""
        user_data = {
            'email': 'newuser@example.com',
            'password': 'password123',
            'first_name': 'New',
            'last_name': 'User'
        }
        
        result = await auth_service.register_user(user_data)
        
        # Placeholder implementation returns mock data
        assert 'user_id' in result
        assert result['email'] == user_data['email']
        assert 'access_token' in result
    
    @pytest.mark.asyncio
    async def test_verify_token_placeholder(self, auth_service):
        """Test token verification (placeholder implementation)."""
        result = await auth_service.verify_token('valid-token')
        
        # Placeholder implementation returns mock data
        assert result is not None
        assert 'user_id' in result
        assert 'email' in result


class TestErrorHandlingDetailed:
    """Detailed tests for error handling functionality."""
    
    def test_handle_aws_no_credentials_error(self):
        """Test handling of AWS no credentials error."""
        error = NoCredentialsError()
        
        result = handle_aws_error(error)
        
        assert isinstance(result, ServiceUnavailableError)
        assert "AWS credentials not configured" in str(result)
        assert result.details['aws_error'] == 'NoCredentialsError'
    
    def test_handle_aws_client_error_access_denied(self):
        """Test handling of AWS access denied error."""
        error = ClientError(
            error_response={
                'Error': {
                    'Code': 'AccessDenied',
                    'Message': 'Access denied to resource'
                }
            },
            operation_name='GetItem'
        )
        
        result = handle_aws_error(error)
        
        assert result.status_code == 403
        assert result.error_code == 'AUTHORIZATION_ERROR'
        assert 'Access denied to resource' in str(result)
    
    def test_handle_aws_client_error_resource_not_found(self):
        """Test handling of AWS resource not found error."""
        error = ClientError(
            error_response={
                'Error': {
                    'Code': 'ResourceNotFoundException',
                    'Message': 'Table not found'
                }
            },
            operation_name='DescribeTable'
        )
        
        result = handle_aws_error(error)
        
        assert result.status_code == 404
        assert result.error_code == 'RESOURCE_NOT_FOUND'
        assert 'Table not found' in str(result)
    
    def test_handle_aws_client_error_throttling(self):
        """Test handling of AWS throttling error."""
        error = ClientError(
            error_response={
                'Error': {
                    'Code': 'ThrottlingException',
                    'Message': 'Rate exceeded'
                }
            },
            operation_name='PutItem'
        )
        
        result = handle_aws_error(error)
        
        assert result.status_code == 429
        assert result.error_code == 'RATE_LIMIT_EXCEEDED'
        assert result.details['retry_after'] == 30


class TestRetryMechanisms:
    """Test retry mechanisms and reliability features."""
    
    @pytest.mark.asyncio
    async def test_retry_success_after_failure(self):
        """Test retry mechanism with eventual success."""
        call_count = 0
        
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                # Use a retryable exception type
                raise ConnectionError("Temporary connection failure")
            return "success"
        
        config = RetryConfig(max_attempts=3, base_delay=0.01)
        result = await retry_async(failing_function, config)
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_max_attempts_exceeded(self):
        """Test retry mechanism when max attempts exceeded."""
        async def always_failing_function():
            raise Exception("Permanent failure")
        
        config = RetryConfig(max_attempts=2, base_delay=0.01)
        
        with pytest.raises(Exception, match="Permanent failure"):
            await retry_async(always_failing_function, config)
    
    @pytest.mark.asyncio
    async def test_retry_non_retryable_error(self):
        """Test retry mechanism with non-retryable error."""
        async def function_with_validation_error():
            raise ValueError("Invalid input")
        
        config = RetryConfig(
            max_attempts=3,
            base_delay=0.01,
            retryable_exceptions=(ConnectionError,)  # Only retry connection errors
        )
        
        with pytest.raises(ValueError, match="Invalid input"):
            await retry_async(function_with_validation_error, config)


class TestDataConsistency:
    """Test data consistency and integrity."""
    
    @pytest.fixture
    def db_service(self):
        """Create DynamoDB service instance."""
        return DynamoDBService()
    
    def test_datetime_serialization_consistency(self, db_service):
        """Test datetime serialization produces consistent results."""
        test_datetime = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        
        serialized1 = db_service._serialize_item({'timestamp': test_datetime})
        serialized2 = db_service._serialize_item({'timestamp': test_datetime})
        
        assert serialized1['timestamp'] == serialized2['timestamp']
        assert serialized1['timestamp'] == test_datetime.isoformat()
    
    def test_decimal_precision_preservation(self, db_service):
        """Test that decimal precision is preserved during serialization."""
        test_values = [123.456789, 0.000001, 999999.999999]
        
        for value in test_values:
            serialized = db_service._serialize_item({'value': value})
            deserialized = db_service._deserialize_item(serialized)
            
            # Should preserve precision within reasonable bounds
            assert abs(deserialized['value'] - value) < 1e-10
    
    def test_nested_data_integrity(self, db_service):
        """Test integrity of nested data structures."""
        complex_data = {
            'level1': {
                'level2': {
                    'level3': {
                        'values': [1.1, 2.2, 3.3],
                        'timestamp': datetime.now(timezone.utc),
                        'metadata': {'key': 'value'}
                    }
                }
            }
        }
        
        serialized = db_service._serialize_item(complex_data)
        deserialized = db_service._deserialize_item(serialized)
        
        # Check deep nested structure is preserved
        level3 = deserialized['level1']['level2']['level3']
        assert len(level3['values']) == 3
        assert level3['metadata']['key'] == 'value'
        assert isinstance(level3['timestamp'], str)


if __name__ == "__main__":
    """Run the services functional tests."""
    print("🔧 SnapStudy Backend Services Functional Test Suite")
    print("=" * 60)
    
    # Run pytest with verbose output
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--color=yes"
    ])