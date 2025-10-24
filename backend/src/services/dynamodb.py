"""DynamoDB service for data operations."""

from dotenv import load_dotenv
load_dotenv()

import boto3
from boto3.dynamodb.conditions import Key, Attr
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import uuid
import json
from decimal import Decimal

from ..config import settings
from ..utils.retry import dynamodb_retry, DYNAMODB_RETRY_CONFIG
from ..middleware.error_handler import (
    ResourceNotFoundError, 
    ServiceUnavailableError,
    ValidationError,
    handle_aws_error
)

import logging

logger = logging.getLogger(__name__)


class DynamoDBService:
    """Service for DynamoDB operations."""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name=settings.aws_region)
        self.users_table = self.dynamodb.Table(settings.users_table)
        self.lessons_table = self.dynamodb.Table(settings.lessons_table)
        self.micro_lessons_table = self.dynamodb.Table(settings.micro_lessons_table)
        self.quizzes_table = self.dynamodb.Table(settings.quizzes_table)
        self.user_engagement_table = self.dynamodb.Table(settings.user_engagement_table)
        self.chat_history_table = self.dynamodb.Table(settings.chat_history_table)
    
    def _serialize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Python types to DynamoDB compatible types."""
        if isinstance(item, dict):
            return {k: self._serialize_item(v) for k, v in item.items()}
        elif isinstance(item, list):
            return [self._serialize_item(i) for i in item]
        elif isinstance(item, datetime):
            return item.isoformat()
        elif isinstance(item, float):
            return Decimal(str(item))
        else:
            return item
    
    def _deserialize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DynamoDB types to Python types."""
        if isinstance(item, dict):
            return {k: self._deserialize_item(v) for k, v in item.items()}
        elif isinstance(item, list):
            return [self._deserialize_item(i) for i in item]
        elif isinstance(item, Decimal):
            return float(item)
        else:
            return item
    
    def initialize(self):
        """Initialize the DynamoDB service and verify table access."""
        try:
            # Test connectivity to all tables
            tables_to_check = [
                (self.users_table, "Users"),
                (self.lessons_table, "Lessons"),
                (self.micro_lessons_table, "MicroLessons"),
                (self.quizzes_table, "Quizzes"),
                (self.user_engagement_table, "UserEngagement"),
                (self.chat_history_table, "ChatHistory")
            ]
            
            for table, name in tables_to_check:
                try:
                    table.load()
                    logger.info(f"Successfully connected to {name} table")
                except Exception as e:
                    logger.error(f"Failed to connect to {name} table: {str(e)}")
                    raise ServiceUnavailableError(f"DynamoDB {name} table", str(e))
            
            logger.info("DynamoDB service initialized successfully")
            
        except Exception as e:
            logger.error(f"DynamoDB initialization failed: {str(e)}")
            raise ServiceUnavailableError("DynamoDB", f"Initialization failed: {str(e)}")
    
    def health_check(self):
        """Perform health check on DynamoDB service."""
        try:
            # Simple health check - describe one table
            self.users_table.load()
            return {"status": "healthy", "service": "dynamodb"}
        except Exception as e:
            logger.error(f"DynamoDB health check failed: {str(e)}")
            raise ServiceUnavailableError("DynamoDB", f"Health check failed: {str(e)}")
    
    def cleanup(self):
        """Cleanup DynamoDB resources."""
        try:
            # Close any open connections if needed
            logger.info("DynamoDB service cleanup completed")
        except Exception as e:
            logger.error(f"DynamoDB cleanup error: {str(e)}")
    
    def get_item_sync(self, table_name: str, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get item from DynamoDB table with retry logic (synchronous)."""
        try:
            table = getattr(self, f"{table_name.lower()}_table")
            response = table.get_item(Key=key)
            
            if 'Item' in response:
                return self._deserialize_item(response['Item'])
            return None
            
        except Exception as e:
            logger.error(f"Error getting item from {table_name}: {str(e)}")
            aws_exception = handle_aws_error(e)
            raise aws_exception
    
    async def get_item(self, table_name: str, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get item from DynamoDB table with retry logic (async wrapper)."""
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(
            None, self.get_item_sync, table_name, key
        )
    
    def put_item_sync(self, table_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
        """Put item to DynamoDB table with retry logic (synchronous)."""
        try:
            table = getattr(self, f"{table_name.lower()}_table")
            serialized_item = self._serialize_item(item)
            
            table.put_item(Item=serialized_item)
            return item
            
        except Exception as e:
            logger.error(f"Error putting item to {table_name}: {str(e)}")
            aws_exception = handle_aws_error(e)
            raise aws_exception
    
    async def put_item(self, table_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
        """Put item to DynamoDB table with retry logic (async wrapper)."""
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(
            None, self.put_item_sync, table_name, item
        )
    
    @dynamodb_retry
    async def update_item(
        self, 
        table_name: str, 
        key: Dict[str, Any], 
        update_expression: str,
        expression_attribute_values: Dict[str, Any],
        expression_attribute_names: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Update item in DynamoDB table with retry logic."""
        try:
            table = getattr(self, f"{table_name.lower()}_table")
            
            update_params = {
                'Key': key,
                'UpdateExpression': update_expression,
                'ExpressionAttributeValues': self._serialize_item(expression_attribute_values),
                'ReturnValues': 'ALL_NEW'
            }
            
            if expression_attribute_names:
                update_params['ExpressionAttributeNames'] = expression_attribute_names
            
            response = table.update_item(**update_params)
            
            if 'Attributes' in response:
                return self._deserialize_item(response['Attributes'])
            return {}
            
        except Exception as e:
            logger.error(f"Error updating item in {table_name}: {str(e)}")
            aws_exception = handle_aws_error(e)
            raise aws_exception
    
    @dynamodb_retry
    async def delete_item(self, table_name: str, key: Dict[str, Any]) -> bool:
        """Delete item from DynamoDB table with retry logic."""
        try:
            table = getattr(self, f"{table_name.lower()}_table")
            table.delete_item(Key=key)
            return True
            
        except Exception as e:
            logger.error(f"Error deleting item from {table_name}: {str(e)}")
            aws_exception = handle_aws_error(e)
            raise aws_exception
    
    @dynamodb_retry
    async def query_items(
        self, 
        table_name: str, 
        key_condition: Any,
        index_name: Optional[str] = None,
        filter_expression: Optional[Any] = None,
        limit: Optional[int] = None,
        scan_index_forward: bool = True
    ) -> List[Dict[str, Any]]:
        """Query items from DynamoDB table with retry logic."""
        try:
            # Map table names to actual table attributes
            table_mapping = {
                'users': self.users_table,
                'lessons': self.lessons_table,
                'microlessons': self.micro_lessons_table,
                'quizzes': self.quizzes_table,
                'userengagement': self.user_engagement_table,
                'chathistory': self.chat_history_table
            }
            
            table_key = table_name.lower()
            if table_key not in table_mapping:
                raise ValueError(f"Unknown table: {table_name}")
            
            table = table_mapping[table_key]
            
            # Handle key_condition - if it's a dict, convert to proper expression
            if isinstance(key_condition, dict):
                from boto3.dynamodb.conditions import Key
                key_conditions = []
                for key, value in key_condition.items():
                    key_conditions.append(Key(key).eq(value))
                
                if len(key_conditions) == 1:
                    key_condition_expr = key_conditions[0]
                else:
                    key_condition_expr = key_conditions[0]
                    for condition in key_conditions[1:]:
                        key_condition_expr = key_condition_expr & condition
            else:
                key_condition_expr = key_condition
            
            query_params = {
                'KeyConditionExpression': key_condition_expr,
                'ScanIndexForward': scan_index_forward
            }
            
            if index_name:
                query_params['IndexName'] = index_name
            
            if filter_expression:
                query_params['FilterExpression'] = filter_expression
            
            if limit:
                query_params['Limit'] = limit
            
            response = table.query(**query_params)
            
            items = []
            if 'Items' in response:
                items = [self._deserialize_item(item) for item in response['Items']]
            
            return items
            
        except Exception as e:
            logger.error(f"Error querying items from {table_name}: {str(e)}")
            aws_exception = handle_aws_error(e)
            raise aws_exception

    # User operations
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user with proper data validation."""
        try:
            # Validate required fields
            if not user_data.get('email'):
                raise ValidationError("Email is required")
            
            if not user_data.get('password_hash'):
                raise ValidationError("Password hash is required")
            
            # Check if user already exists
            existing_user = await self.get_user_by_email(user_data['email'])
            if existing_user:
                from ..middleware.error_handler import ResourceConflictError
                raise ResourceConflictError("User", "email", user_data['email'])
            
            # Generate user ID if not provided
            user_id = user_data.get('user_id', str(uuid.uuid4()))
            now = datetime.now(timezone.utc)
            
            # Set default values
            item = {
                'user_id': user_id,
                'email': user_data['email'],
                'password_hash': user_data['password_hash'],
                'full_name': user_data.get('full_name'),
                'age': user_data.get('age'),
                'profession': user_data.get('profession'),
                'education_level': user_data.get('education_level'),
                'country': user_data.get('country'),
                'onboarding_completed': user_data.get('onboarding_completed', False),
                'preferences': user_data.get('preferences'),
                'is_active': user_data.get('is_active', True),
                'created_at': now.isoformat(),
                'updated_at': now.isoformat()
            }
            
            # Remove None values
            item = {k: v for k, v in item.items() if v is not None}
            
            serialized_item = self._serialize_item(item)
            self.users_table.put_item(Item=serialized_item)
            
            logger.info(f"User created successfully: {user_data['email']}")
            return self._deserialize_item(serialized_item)
            
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            if isinstance(e, (ValidationError, ResourceConflictError)):
                raise
            aws_exception = handle_aws_error(e)
            raise aws_exception
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID with proper error handling."""
        try:
            if not user_id:
                raise ValidationError("User ID is required")
            
            response = self.users_table.get_item(Key={'user_id': user_id})
            
            if 'Item' in response:
                user = self._deserialize_item(response['Item'])
                logger.debug(f"User retrieved by ID: {user_id}")
                return user
            
            logger.debug(f"User not found by ID: {user_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {str(e)}")
            if isinstance(e, ValidationError):
                raise
            aws_exception = handle_aws_error(e)
            raise aws_exception
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email using GSI with proper error handling."""
        try:
            if not email:
                raise ValidationError("Email is required")
            
            # Use scan operation for development (less efficient but works without GSI)
            response = self.users_table.scan(
                FilterExpression=Attr('email').eq(email)
            )
            
            items = response.get('Items', [])
            if items:
                user = self._deserialize_item(items[0])
                logger.debug(f"User retrieved by email: {email}")
                return user
            
            logger.debug(f"User not found by email: {email}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {str(e)}")
            if isinstance(e, ValidationError):
                raise
            aws_exception = handle_aws_error(e)
            raise aws_exception
    
    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update user profile with proper validation."""
        try:
            if not user_id:
                raise ValidationError("User ID is required")
            
            if not updates:
                raise ValidationError("No updates provided")
            
            # Check if user exists
            existing_user = await self.get_user_by_id(user_id)
            if not existing_user:
                raise ResourceNotFoundError("User", "user_id", user_id)
            
            # Add updated timestamp
            updates['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            # Build update expression
            update_expression = "SET "
            expression_values = {}
            expression_names = {}
            
            for key, value in updates.items():
                # Handle reserved keywords by using expression attribute names
                attr_name = f"#{key}"
                attr_value = f":{key}"
                
                update_expression += f"{attr_name} = {attr_value}, "
                expression_values[attr_value] = self._serialize_item(value)
                expression_names[attr_name] = key
            
            update_expression = update_expression.rstrip(", ")
            
            response = self.users_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values,
                ReturnValues='ALL_NEW'
            )
            
            updated_user = self._deserialize_item(response['Attributes'])
            logger.info(f"User updated successfully: {user_id}")
            return updated_user
            
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {str(e)}")
            if isinstance(e, (ValidationError, ResourceNotFoundError)):
                raise
            aws_exception = handle_aws_error(e)
            raise aws_exception
    
    # Lesson operations
    async def create_lesson(self, lesson_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new lesson."""
        lesson_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        item = {
            'lesson_id': lesson_id,
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
            **lesson_data
        }
        
        serialized_item = self._serialize_item(item)
        self.lessons_table.put_item(Item=serialized_item)
        return self._deserialize_item(serialized_item)
    
    async def get_lesson(self, lesson_id: str) -> Optional[Dict[str, Any]]:
        """Get lesson by ID."""
        response = self.lessons_table.get_item(Key={'lesson_id': lesson_id})
        return self._deserialize_item(response.get('Item')) if 'Item' in response else None
    
    async def get_user_lessons(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all lessons for a user."""
        response = self.lessons_table.query(
            IndexName='UserLessonsIndex',
            KeyConditionExpression=Key('user_id').eq(user_id)
        )
        return [self._deserialize_item(item) for item in response.get('Items', [])]
    
    async def update_lesson(self, lesson_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update lesson data."""
        updates['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        update_expression = "SET "
        expression_values = {}
        
        for key, value in updates.items():
            update_expression += f"#{key} = :{key}, "
            expression_values[f":{key}"] = self._serialize_item(value)
        
        update_expression = update_expression.rstrip(", ")
        expression_names = {f"#{key}": key for key in updates.keys()}
        
        response = self.lessons_table.update_item(
            Key={'lesson_id': lesson_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )
        
        return self._deserialize_item(response['Attributes'])
    
    # Micro-lesson operations
    async def create_micro_lesson(self, micro_lesson_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new micro-lesson."""
        micro_lesson_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        item = {
            'micro_lesson_id': micro_lesson_id,
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
            **micro_lesson_data
        }
        
        serialized_item = self._serialize_item(item)
        self.micro_lessons_table.put_item(Item=serialized_item)
        return self._deserialize_item(serialized_item)
    
    async def get_lesson_micro_lessons(self, lesson_id: str) -> List[Dict[str, Any]]:
        """Get all micro-lessons for a lesson, ordered by sequence."""
        response = self.micro_lessons_table.query(
            IndexName='LessonMicroLessonsIndex',
            KeyConditionExpression=Key('lesson_id').eq(lesson_id)
        )
        items = [self._deserialize_item(item) for item in response.get('Items', [])]
        return sorted(items, key=lambda x: x.get('sequence_number', 0))
    
    # Quiz operations
    async def create_quiz(self, quiz_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new quiz."""
        quiz_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        item = {
            'quiz_id': quiz_id,
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
            **quiz_data
        }
        
        serialized_item = self._serialize_item(item)
        self.quizzes_table.put_item(Item=serialized_item)
        return self._deserialize_item(serialized_item)
    
    async def get_micro_lesson_quiz(self, micro_lesson_id: str) -> Optional[Dict[str, Any]]:
        """Get quiz for a micro-lesson."""
        response = self.quizzes_table.query(
            IndexName='MicroLessonQuizzesIndex',
            KeyConditionExpression=Key('micro_lesson_id').eq(micro_lesson_id)
        )
        items = response.get('Items', [])
        return self._deserialize_item(items[0]) if items else None
    
    # Engagement tracking
    async def track_engagement(self, engagement_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track user engagement event."""
        engagement_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        item = {
            'engagement_id': engagement_id,
            'timestamp': now.isoformat(),
            **engagement_data
        }
        
        serialized_item = self._serialize_item(item)
        self.user_engagement_table.put_item(Item=serialized_item)
        return self._deserialize_item(serialized_item)
    
    async def get_user_engagement(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get user engagement history."""
        response = self.user_engagement_table.query(
            IndexName='UserEngagementIndex',
            KeyConditionExpression=Key('user_id').eq(user_id),
            Limit=limit,
            ScanIndexForward=False  # Most recent first
        )
        return [self._deserialize_item(item) for item in response.get('Items', [])]
    
    async def get_quiz_by_id(self, quiz_id: str) -> Optional[Dict[str, Any]]:
        """Get quiz by ID."""
        response = self.quizzes_table.get_item(Key={'quiz_id': quiz_id})
        return self._deserialize_item(response.get('Item')) if 'Item' in response else None
    
    async def update_quiz(self, quiz_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update quiz data."""
        updates['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        update_expression = "SET "
        expression_values = {}
        
        for key, value in updates.items():
            update_expression += f"#{key} = :{key}, "
            expression_values[f":{key}"] = self._serialize_item(value)
        
        update_expression = update_expression.rstrip(", ")
        expression_names = {f"#{key}": key for key in updates.keys()}
        
        response = self.quizzes_table.update_item(
            Key={'quiz_id': quiz_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )
        
        return self._deserialize_item(response['Attributes'])
    
    # Chat history operations
    async def create_chat_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new chat session."""
        session_id = session_data.get('session_id', str(uuid.uuid4()))
        now = datetime.now(timezone.utc)
        
        # Calculate TTL (30 days from now)
        ttl = int((now.timestamp() + (30 * 24 * 60 * 60)))
        
        item = {
            'session_id': session_id,
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
            'messages': [],
            'ttl': ttl,
            **session_data
        }
        
        serialized_item = self._serialize_item(item)
        self.chat_history_table.put_item(Item=serialized_item)
        return self._deserialize_item(serialized_item)
    
    async def get_chat_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get chat session by ID."""
        response = self.chat_history_table.get_item(Key={'session_id': session_id})
        return self._deserialize_item(response.get('Item')) if 'Item' in response else None
    
    async def update_chat_session(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update chat session data."""
        updates['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        update_expression = "SET "
        expression_values = {}
        
        for key, value in updates.items():
            update_expression += f"#{key} = :{key}, "
            expression_values[f":{key}"] = self._serialize_item(value)
        
        update_expression = update_expression.rstrip(", ")
        expression_names = {f"#{key}": key for key in updates.keys()}
        
        response = self.chat_history_table.update_item(
            Key={'session_id': session_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )
        
        return self._deserialize_item(response['Attributes'])
    
    async def add_chat_message(
        self, 
        session_id: str, 
        user_id: str, 
        user_message: str, 
        ai_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a message to chat session."""
        now = datetime.now(timezone.utc)
        
        # Get existing session or create new one
        session = await self.get_chat_session(session_id)
        
        if session:
            messages = session.get('messages', [])
        else:
            # Create new session
            await self.create_chat_session({
                'session_id': session_id,
                'user_id': user_id
            })
            messages = []
        
        # Add new messages
        messages.extend([
            {
                'role': 'user',
                'content': user_message,
                'timestamp': now.isoformat()
            },
            {
                'role': 'assistant',
                'content': ai_response,
                'timestamp': now.isoformat(),
                'metadata': metadata or {}
            }
        ])
        
        # Keep only recent messages (last 50)
        if len(messages) > 50:
            messages = messages[-50:]
        
        # Update session with new messages
        await self.update_chat_session(session_id, {
            'messages': messages,
            'user_id': user_id
        })
    
    async def get_user_chat_sessions(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent chat sessions for a user."""
        # Note: This would require a GSI on user_id in a real implementation
        # For now, we'll return an empty list as this is not critical for the core functionality
        return []


# Global service instance - initialized lazily to avoid circular imports
dynamodb_service = DynamoDBService()
# Alias for backward compatibility
db_service = dynamodb_service