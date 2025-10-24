"""
Amazon Q Integration Service for SnapStudy Educational Chatbot.

This service integrates Amazon Q Business and Q Developer to provide:
- Educational knowledge base access
- Research assistance and resources
- Technical/coding help for programming courses
- Content guardrails and safety filters
"""

import boto3
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from botocore.exceptions import ClientError
import asyncio
from datetime import datetime, timezone
from enum import Enum

from ..config import settings

logger = logging.getLogger(__name__)


class QServiceType(str, Enum):
    """Types of Amazon Q services available."""
    BUSINESS = "business"
    DEVELOPER = "developer"


class ContentCategory(str, Enum):
    """Educational content categories."""
    ACADEMIC = "academic"
    TECHNICAL = "technical"
    RESEARCH = "research"
    GENERAL_EDUCATION = "general_education"
    PROGRAMMING = "programming"
    SCIENCE = "science"
    MATHEMATICS = "mathematics"
    LANGUAGE = "language"


class SafetyLevel(str, Enum):
    """Content safety levels."""
    SAFE = "safe"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


class AmazonQService:
    """
    Amazon Q integration service with educational focus and content guardrails.
    
    Provides access to Q Business for educational knowledge and Q Developer
    for technical assistance, with built-in safety and content filtering.
    """
    
    def __init__(self):
        # Initialize Q Business client
        self.q_business_client = boto3.client(
            'qbusiness', 
            region_name=settings.aws_region
        )
        
        # Initialize Q Developer client (if available)
        try:
            self.q_developer_client = boto3.client(
                'q-developer',
                region_name=settings.aws_region
            )
            self.q_developer_available = True
        except Exception as e:
            logger.warning(f"Q Developer not available: {e}")
            self.q_developer_client = None
            self.q_developer_available = False
        
        # Initialize Bedrock for guardrails
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name=settings.aws_region
        )
        
        # Configuration
        self.application_id = getattr(settings, 'q_business_application_id', None)
        self.user_id_prefix = "snapstudy-user-"
        
        # Educational content keywords for filtering
        self.educational_keywords = {
            'academic': ['study', 'learn', 'education', 'course', 'lesson', 'tutorial', 'academic'],
            'research': ['research', 'paper', 'study', 'analysis', 'investigation', 'findings'],
            'technical': ['programming', 'code', 'algorithm', 'software', 'development', 'technical'],
            'science': ['science', 'physics', 'chemistry', 'biology', 'experiment', 'theory'],
            'mathematics': ['math', 'mathematics', 'equation', 'formula', 'calculation', 'statistics']
        }
        
        # Blocked content patterns
        self.blocked_patterns = [
            'violence', 'hate', 'harassment', 'illegal', 'harmful', 'inappropriate',
            'adult content', 'explicit', 'offensive', 'discrimination', 'bullying'
        ]
    
    async def chat_with_q_business(
        self, 
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None,
        educational_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Chat with Amazon Q Business for educational knowledge and resources.
        
        Args:
            user_id: SnapStudy user ID
            message: User's question/message
            conversation_id: Optional conversation ID for context
            educational_context: Current learning context (lesson, subject, etc.)
            
        Returns:
            Dict containing Q Business response with safety validation
        """
        try:
            # Validate application is configured
            if not self.application_id:
                raise ValueError("Amazon Q Business application not configured")
            
            # Pre-filter content for safety
            safety_check = await self._validate_content_safety(message)
            if safety_check['level'] == SafetyLevel.BLOCKED:
                return self._create_blocked_response(safety_check['reason'])
            
            # Enhance message with educational context
            enhanced_message = await self._enhance_educational_context(
                message, educational_context
            )
            
            # Prepare Q Business request
            q_user_id = f"{self.user_id_prefix}{user_id}"
            
            request_params = {
                'applicationId': self.application_id,
                'userId': q_user_id,
                'userMessage': enhanced_message
            }
            
            # Add conversation context if available
            if conversation_id:
                request_params['conversationId'] = conversation_id
            
            # Call Q Business
            response = self.q_business_client.chat_sync(**request_params)
            
            # Process and validate response
            processed_response = await self._process_q_business_response(
                response, educational_context
            )
            
            # Apply educational content filtering
            filtered_response = await self._apply_educational_filters(processed_response)
            
            return {
                'success': True,
                'response': filtered_response['content'],
                'conversation_id': response.get('conversationId'),
                'source_attributions': filtered_response.get('sources', []),
                'educational_category': filtered_response.get('category'),
                'safety_level': SafetyLevel.SAFE,
                'service_type': QServiceType.BUSINESS,
                'metadata': {
                    'response_id': response.get('systemMessageId'),
                    'user_message_id': response.get('userMessageId'),
                    'enhanced_query': enhanced_message != message
                }
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Q Business API error: {error_code} - {e}")
            
            if error_code == 'AccessDeniedException':
                return self._create_error_response(
                    "Access denied to Q Business. Please check permissions.",
                    "access_denied"
                )
            elif error_code == 'ResourceNotFoundException':
                return self._create_error_response(
                    "Q Business application not found. Please check configuration.",
                    "not_configured"
                )
            else:
                return self._create_error_response(
                    f"Q Business service error: {error_code}",
                    "service_error"
                )
                
        except Exception as e:
            logger.error(f"Unexpected error in Q Business chat: {e}")
            return self._create_error_response(
                "Sorry, I'm having trouble accessing educational resources right now.",
                "unexpected_error"
            )
    
    async def get_educational_resources(
        self,
        user_id: str,
        topic: str,
        resource_type: str = "all",
        difficulty_level: str = "intermediate"
    ) -> Dict[str, Any]:
        """
        Get educational resources and research materials using Q Business.
        
        Args:
            user_id: SnapStudy user ID
            topic: Educational topic to search for
            resource_type: Type of resources (papers, tutorials, examples, etc.)
            difficulty_level: Difficulty level (beginner, intermediate, advanced)
            
        Returns:
            Dict containing educational resources and materials
        """
        try:
            # Construct educational resource query
            resource_query = await self._build_educational_query(
                topic, resource_type, difficulty_level
            )
            
            # Use Q Business to find resources
            response = await self.chat_with_q_business(
                user_id=user_id,
                message=resource_query,
                educational_context={
                    'type': 'resource_search',
                    'topic': topic,
                    'resource_type': resource_type,
                    'difficulty': difficulty_level
                }
            )
            
            if response['success']:
                # Parse and categorize resources
                resources = await self._parse_educational_resources(
                    response['response'], topic, resource_type
                )
                
                return {
                    'success': True,
                    'topic': topic,
                    'resources': resources,
                    'total_found': len(resources),
                    'difficulty_level': difficulty_level,
                    'conversation_id': response.get('conversation_id')
                }
            else:
                return response
                
        except Exception as e:
            logger.error(f"Error getting educational resources: {e}")
            return self._create_error_response(
                "Unable to retrieve educational resources at this time.",
                "resource_error"
            )
    
    async def get_coding_assistance(
        self,
        user_id: str,
        code_question: str,
        programming_language: str = "python",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get coding assistance using Q Developer (if available) or Q Business.
        
        Args:
            user_id: SnapStudy user ID
            code_question: Programming question or code to analyze
            programming_language: Programming language context
            context: Additional context (project type, learning level, etc.)
            
        Returns:
            Dict containing coding assistance and examples
        """
        try:
            # Validate this is educational coding content
            if not await self._is_educational_coding_query(code_question):
                return self._create_blocked_response(
                    "Please ask educational programming questions related to learning."
                )
            
            # Try Q Developer first if available
            if self.q_developer_available:
                try:
                    return await self._get_q_developer_assistance(
                        user_id, code_question, programming_language, context
                    )
                except Exception as e:
                    logger.warning(f"Q Developer failed, falling back to Q Business: {e}")
            
            # Fallback to Q Business with coding context
            coding_query = await self._build_coding_query(
                code_question, programming_language, context
            )
            
            response = await self.chat_with_q_business(
                user_id=user_id,
                message=coding_query,
                educational_context={
                    'type': 'coding_assistance',
                    'language': programming_language,
                    'context': context
                }
            )
            
            if response['success']:
                # Process coding response
                coding_response = await self._process_coding_response(
                    response['response'], programming_language
                )
                
                return {
                    'success': True,
                    'response': coding_response['content'],
                    'code_examples': coding_response.get('examples', []),
                    'explanations': coding_response.get('explanations', []),
                    'programming_language': programming_language,
                    'service_used': 'q_business',
                    'conversation_id': response.get('conversation_id')
                }
            else:
                return response
                
        except Exception as e:
            logger.error(f"Error getting coding assistance: {e}")
            return self._create_error_response(
                "Unable to provide coding assistance at this time.",
                "coding_error"
            )
    
    async def _validate_content_safety(self, content: str) -> Dict[str, Any]:
        """
        Validate content safety using Bedrock Guardrails and custom filters.
        
        Args:
            content: Content to validate
            
        Returns:
            Dict with safety level and reasoning
        """
        try:
            # Check for blocked patterns
            content_lower = content.lower()
            for pattern in self.blocked_patterns:
                if pattern in content_lower:
                    return {
                        'level': SafetyLevel.BLOCKED,
                        'reason': f"Content contains inappropriate material: {pattern}",
                        'confidence': 0.9
                    }
            
            # Use Bedrock Guardrails if configured
            if hasattr(settings, 'bedrock_guardrail_id'):
                try:
                    guardrail_response = self.bedrock_client.apply_guardrail(
                        guardrailIdentifier=settings.bedrock_guardrail_id,
                        guardrailVersion=getattr(settings, 'bedrock_guardrail_version', 'DRAFT'),
                        source='INPUT',
                        content=[{
                            'text': {
                                'text': content
                            }
                        }]
                    )
                    
                    # Check guardrail results
                    if guardrail_response.get('action') == 'BLOCKED':
                        return {
                            'level': SafetyLevel.BLOCKED,
                            'reason': 'Content blocked by safety guardrails',
                            'confidence': 0.95,
                            'guardrail_response': guardrail_response
                        }
                        
                except Exception as e:
                    logger.warning(f"Guardrail check failed: {e}")
            
            # Check if content is educational
            is_educational = await self._is_educational_content(content)
            if not is_educational:
                return {
                    'level': SafetyLevel.NEEDS_REVIEW,
                    'reason': 'Content may not be educational',
                    'confidence': 0.7
                }
            
            return {
                'level': SafetyLevel.SAFE,
                'reason': 'Content passed safety checks',
                'confidence': 0.9
            }
            
        except Exception as e:
            logger.error(f"Error in content safety validation: {e}")
            return {
                'level': SafetyLevel.NEEDS_REVIEW,
                'reason': 'Unable to validate content safety',
                'confidence': 0.5
            }
    
    async def _is_educational_content(self, content: str) -> bool:
        """Check if content is educational in nature."""
        content_lower = content.lower()
        
        # Check for educational keywords
        educational_score = 0
        total_categories = len(self.educational_keywords)
        
        for category, keywords in self.educational_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                educational_score += 1
        
        # Consider educational if matches at least 1 category or contains learning indicators
        learning_indicators = [
            'how to', 'what is', 'explain', 'learn', 'understand', 'help me',
            'tutorial', 'example', 'practice', 'study', 'homework', 'assignment'
        ]
        
        has_learning_indicators = any(indicator in content_lower for indicator in learning_indicators)
        
        return educational_score > 0 or has_learning_indicators
    
    async def _enhance_educational_context(
        self, 
        message: str, 
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Enhance message with educational context for better Q responses."""
        if not context:
            return f"Educational Question: {message}"
        
        context_parts = ["Educational Question"]
        
        if context.get('current_lesson'):
            lesson_title = context['current_lesson'].get('title', 'Current Lesson')
            context_parts.append(f"Current Lesson: {lesson_title}")
        
        if context.get('subject'):
            context_parts.append(f"Subject: {context['subject']}")
        
        if context.get('difficulty_level'):
            context_parts.append(f"Level: {context['difficulty_level']}")
        
        if context.get('learning_objective'):
            context_parts.append(f"Learning Goal: {context['learning_objective']}")
        
        enhanced_context = " | ".join(context_parts)
        return f"{enhanced_context}\n\nQuestion: {message}"
    
    async def _process_q_business_response(
        self, 
        response: Dict[str, Any], 
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process and validate Q Business response."""
        try:
            # Extract main response content
            system_message = response.get('systemMessage', '')
            
            # Extract source attributions if available
            source_attributions = []
            if 'sourceAttributions' in response:
                for attribution in response['sourceAttributions']:
                    source_attributions.append({
                        'title': attribution.get('title', ''),
                        'url': attribution.get('url', ''),
                        'snippet': attribution.get('snippet', ''),
                        'updated_at': attribution.get('updatedAt', '')
                    })
            
            return {
                'content': system_message,
                'sources': source_attributions,
                'raw_response': response
            }
            
        except Exception as e:
            logger.error(f"Error processing Q Business response: {e}")
            return {
                'content': "I received a response but had trouble processing it. Please try rephrasing your question.",
                'sources': [],
                'error': str(e)
            }
    
    async def _apply_educational_filters(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Apply educational content filters to ensure appropriate responses."""
        content = response.get('content', '')
        
        # Categorize content
        category = await self._categorize_educational_content(content)
        
        # Validate educational appropriateness
        if not await self._is_appropriate_educational_content(content):
            content = "I can only provide educational content. Please ask questions related to learning, studying, or academic topics."
            category = ContentCategory.GENERAL_EDUCATION
        
        return {
            'content': content,
            'sources': response.get('sources', []),
            'category': category,
            'filtered': content != response.get('content', '')
        }
    
    async def _categorize_educational_content(self, content: str) -> ContentCategory:
        """Categorize educational content by type."""
        content_lower = content.lower()
        
        # Check each category
        for category_name, keywords in self.educational_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                return ContentCategory(category_name.upper())
        
        return ContentCategory.GENERAL_EDUCATION
    
    async def _is_appropriate_educational_content(self, content: str) -> bool:
        """Validate content is appropriate for educational context."""
        # Check for inappropriate content indicators
        inappropriate_indicators = [
            'violence', 'illegal', 'harmful', 'inappropriate', 'adult',
            'explicit', 'offensive', 'hate', 'discrimination'
        ]
        
        content_lower = content.lower()
        return not any(indicator in content_lower for indicator in inappropriate_indicators)
    
    async def _build_educational_query(
        self, 
        topic: str, 
        resource_type: str, 
        difficulty_level: str
    ) -> str:
        """Build optimized query for educational resource search."""
        query_parts = [
            f"Find educational resources about {topic}",
            f"Difficulty level: {difficulty_level}"
        ]
        
        if resource_type != "all":
            query_parts.append(f"Resource type: {resource_type}")
        
        query_parts.extend([
            "Include research papers, tutorials, examples, and learning materials",
            "Focus on academic and educational sources",
            "Provide explanations suitable for students"
        ])
        
        return ". ".join(query_parts)
    
    async def _parse_educational_resources(
        self, 
        response_content: str, 
        topic: str, 
        resource_type: str
    ) -> List[Dict[str, Any]]:
        """Parse educational resources from Q Business response."""
        # This is a simplified parser - in production, you'd want more sophisticated parsing
        resources = []
        
        # Look for common resource patterns
        lines = response_content.split('\n')
        current_resource = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_resource:
                    resources.append(current_resource)
                    current_resource = {}
                continue
            
            # Simple pattern matching for resources
            if line.startswith('Title:') or line.startswith('**'):
                current_resource['title'] = line.replace('Title:', '').replace('**', '').strip()
            elif line.startswith('URL:') or line.startswith('Link:'):
                current_resource['url'] = line.replace('URL:', '').replace('Link:', '').strip()
            elif line.startswith('Description:'):
                current_resource['description'] = line.replace('Description:', '').strip()
            elif current_resource and not current_resource.get('description'):
                current_resource['description'] = line
        
        # Add final resource if exists
        if current_resource:
            resources.append(current_resource)
        
        # Ensure all resources have required fields
        for resource in resources:
            resource.setdefault('title', f"Resource about {topic}")
            resource.setdefault('description', "Educational resource")
            resource.setdefault('type', resource_type)
            resource.setdefault('topic', topic)
        
        return resources
    
    async def _is_educational_coding_query(self, query: str) -> bool:
        """Validate that coding query is educational in nature."""
        educational_coding_indicators = [
            'learn', 'tutorial', 'example', 'how to', 'explain', 'understand',
            'practice', 'exercise', 'homework', 'assignment', 'study', 'beginner',
            'help me', 'teach me', 'show me', 'algorithm', 'concept'
        ]
        
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in educational_coding_indicators)
    
    async def _build_coding_query(
        self, 
        question: str, 
        language: str, 
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build optimized coding query for educational assistance."""
        query_parts = [
            f"Programming help in {language}:",
            question,
            "Please provide educational explanations and examples suitable for learning.",
            "Include step-by-step explanations and best practices."
        ]
        
        if context:
            if context.get('skill_level'):
                query_parts.append(f"Skill level: {context['skill_level']}")
            if context.get('project_type'):
                query_parts.append(f"Project context: {context['project_type']}")
        
        return " ".join(query_parts)
    
    async def _process_coding_response(
        self, 
        response: str, 
        language: str
    ) -> Dict[str, Any]:
        """Process coding assistance response to extract examples and explanations."""
        # Simple parsing - in production, use more sophisticated code extraction
        lines = response.split('\n')
        
        code_examples = []
        explanations = []
        current_code = []
        in_code_block = False
        
        for line in lines:
            if line.strip().startswith('```'):
                if in_code_block:
                    # End of code block
                    if current_code:
                        code_examples.append('\n'.join(current_code))
                        current_code = []
                    in_code_block = False
                else:
                    # Start of code block
                    in_code_block = True
            elif in_code_block:
                current_code.append(line)
            else:
                # Regular explanation text
                if line.strip():
                    explanations.append(line.strip())
        
        return {
            'content': response,
            'examples': code_examples,
            'explanations': explanations,
            'language': language
        }
    
    async def _get_q_developer_assistance(
        self,
        user_id: str,
        question: str,
        language: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get assistance from Q Developer (placeholder - implement when Q Developer API is available)."""
        # This is a placeholder for Q Developer integration
        # The actual implementation would depend on the Q Developer API when it becomes available
        
        logger.info("Q Developer integration placeholder - using Q Business fallback")
        raise NotImplementedError("Q Developer API not yet available")
    
    def _create_blocked_response(self, reason: str) -> Dict[str, Any]:
        """Create response for blocked content."""
        return {
            'success': False,
            'response': "I can only help with educational and learning-related questions. Please ask about academic topics, studying, or learning materials.",
            'blocked': True,
            'reason': reason,
            'safety_level': SafetyLevel.BLOCKED,
            'suggestions': [
                "Ask about study techniques or learning strategies",
                "Request help with academic subjects",
                "Look for educational resources or research materials",
                "Get assistance with homework or assignments"
            ]
        }
    
    def _create_error_response(self, message: str, error_type: str) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            'success': False,
            'response': message,
            'error_type': error_type,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    async def get_service_health(self) -> Dict[str, Any]:
        """Check health status of Amazon Q services."""
        health_status = {
            'q_business': {'available': False, 'configured': False},
            'q_developer': {'available': False, 'configured': False},
            'guardrails': {'available': False, 'configured': False}
        }
        
        # Check Q Business
        try:
            if self.application_id:
                # Try a simple operation to check availability
                test_response = self.q_business_client.list_conversations(
                    applicationId=self.application_id,
                    userId=f"{self.user_id_prefix}health-check",
                    maxResults=1
                )
                health_status['q_business'] = {'available': True, 'configured': True}
            else:
                health_status['q_business'] = {'available': False, 'configured': False}
        except Exception as e:
            logger.warning(f"Q Business health check failed: {e}")
            health_status['q_business'] = {'available': False, 'configured': bool(self.application_id)}
        
        # Check Q Developer
        health_status['q_developer'] = {
            'available': self.q_developer_available,
            'configured': self.q_developer_available
        }
        
        # Check Guardrails
        try:
            if hasattr(settings, 'bedrock_guardrail_id') and settings.bedrock_guardrail_id:
                # Test guardrail availability using bedrock client (not bedrock-runtime)
                bedrock_control_client = boto3.client('bedrock', region_name=settings.aws_region)
                bedrock_control_client.get_guardrail(
                    guardrailIdentifier=settings.bedrock_guardrail_id
                )
                health_status['guardrails'] = {'available': True, 'configured': True}
            else:
                health_status['guardrails'] = {'available': False, 'configured': False}
        except Exception as e:
            logger.warning(f"Guardrails health check failed: {e}")
            health_status['guardrails'] = {'available': False, 'configured': bool(getattr(settings, 'bedrock_guardrail_id', None))}
        
        return {
            'overall_health': all(
                service['available'] for service in health_status.values()
                if service['configured']
            ),
            'services': health_status,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


# Global service instance
amazon_q_service = AmazonQService()