"""
Enhanced Agentic Chat System with Amazon Q Integration and Educational Guardrails.

This enhanced chat agent provides:
- Amazon Q Business integration for educational knowledge
- Amazon Q Developer integration for coding assistance
- Content guardrails and safety filters
- Educational context validation
- Multi-AI orchestration with intelligent fallbacks
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import uuid

from .amazon_q_service import amazon_q_service, QServiceType, ContentCategory, SafetyLevel
from .chat_agent import AgenticChatAgent, ChatIntent
from .bedrock import bedrock_service
from .dynamodb import db_service
from .adaptive_agent import BedrockAgentCore
from ..config import settings

logger = logging.getLogger(__name__)


class EnhancedChatIntent(str, Enum):
    """Enhanced chat intents with Amazon Q capabilities."""
    # Original intents
    SUMMARIZATION = "summarization"
    EXPLANATION = "explanation"
    QUIZ_REQUEST = "quiz_request"
    PROGRESS_INQUIRY = "progress_inquiry"
    HELP_REQUEST = "help_request"
    GENERAL_CHAT = "general_chat"
    ENCOURAGEMENT = "encouragement"
    
    # New Q-powered intents
    RESEARCH_REQUEST = "research_request"
    RESOURCE_SEARCH = "resource_search"
    CODING_HELP = "coding_help"
    ACADEMIC_ASSISTANCE = "academic_assistance"
    STUDY_GUIDANCE = "study_guidance"


class ResponseSource(str, Enum):
    """Sources of chat responses."""
    BEDROCK_CLAUDE = "bedrock_claude"
    AMAZON_Q_BUSINESS = "amazon_q_business"
    AMAZON_Q_DEVELOPER = "amazon_q_developer"
    AGENT_CORE = "agent_core"
    FALLBACK = "fallback"


class EnhancedAgenticChatAgent:
    """
    Enhanced chat agent with Amazon Q integration and educational guardrails.
    
    Provides intelligent routing between different AI services based on query type,
    with comprehensive safety filters and educational content validation.
    """
    
    def __init__(self):
        # Initialize base services
        self.agent_core = BedrockAgentCore()
        self.bedrock = bedrock_service
        self.db = db_service
        self.amazon_q = amazon_q_service
        
        # Initialize original chat agent for fallback
        self.base_chat_agent = AgenticChatAgent()
        
        # Enhanced intent recognition thresholds
        self.HIGH_CONFIDENCE_THRESHOLD = 0.85
        self.MEDIUM_CONFIDENCE_THRESHOLD = 0.65
        
        # Service routing configuration
        self.service_routing = {
            EnhancedChatIntent.RESEARCH_REQUEST: [QServiceType.BUSINESS, ResponseSource.BEDROCK_CLAUDE],
            EnhancedChatIntent.RESOURCE_SEARCH: [QServiceType.BUSINESS],
            EnhancedChatIntent.CODING_HELP: [QServiceType.DEVELOPER, QServiceType.BUSINESS, ResponseSource.BEDROCK_CLAUDE],
            EnhancedChatIntent.ACADEMIC_ASSISTANCE: [QServiceType.BUSINESS, ResponseSource.BEDROCK_CLAUDE],
            EnhancedChatIntent.STUDY_GUIDANCE: [QServiceType.BUSINESS, ResponseSource.AGENT_CORE],
            EnhancedChatIntent.EXPLANATION: [QServiceType.BUSINESS, ResponseSource.BEDROCK_CLAUDE],
            EnhancedChatIntent.SUMMARIZATION: [ResponseSource.AGENT_CORE, ResponseSource.BEDROCK_CLAUDE]
        }
        
        # Educational keywords for enhanced intent recognition
        self.educational_intent_keywords = {
            'research_request': [
                'research', 'papers', 'studies', 'findings', 'literature review',
                'academic sources', 'scholarly articles', 'peer reviewed'
            ],
            'resource_search': [
                'resources', 'materials', 'references', 'books', 'articles',
                'tutorials', 'guides', 'documentation', 'examples'
            ],
            'coding_help': [
                'code', 'programming', 'algorithm', 'debug', 'syntax',
                'function', 'class', 'method', 'variable', 'loop'
            ],
            'academic_assistance': [
                'homework', 'assignment', 'project', 'essay', 'report',
                'analysis', 'calculation', 'problem solving'
            ],
            'study_guidance': [
                'study plan', 'learning strategy', 'study tips', 'preparation',
                'exam prep', 'review', 'practice', 'memorization'
            ]
        }
    
    async def handle_enhanced_message(
        self,
        user_id: str,
        message: str,
        context: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle chat messages with enhanced Amazon Q integration and guardrails.
        
        Args:
            user_id: ID of the user sending the message
            message: The user's message
            context: Current learning context
            session_id: Optional chat session ID
            
        Returns:
            Dict containing enhanced response with source attribution
        """
        try:
            logger.info(f"Processing enhanced chat message from user {user_id}: {message[:100]}...")
            
            # Get or create session ID
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # Build comprehensive context
            enhanced_context = await self._build_comprehensive_context(
                user_id, session_id, message, context
            )
            
            # Enhanced intent recognition with Q capabilities
            intent_analysis = await self._enhanced_intent_recognition(
                message, enhanced_context
            )
            
            # Validate content safety and educational appropriateness
            safety_validation = await self._validate_educational_safety(
                message, intent_analysis, enhanced_context
            )
            
            if safety_validation['blocked']:
                return await self._create_safety_response(safety_validation, session_id)
            
            # Route to appropriate AI service based on intent
            response_data = await self._route_to_optimal_service(
                intent_analysis, enhanced_context, user_id, session_id
            )
            
            # Post-process response for educational appropriateness
            processed_response = await self._post_process_educational_response(
                response_data, intent_analysis, enhanced_context
            )
            
            # Store enhanced conversation
            await self._store_enhanced_chat_message(
                session_id, user_id, message, processed_response, intent_analysis
            )
            
            # Update agent memory with enhanced interaction data
            await self._update_enhanced_memory(
                user_id, message, processed_response, intent_analysis, enhanced_context
            )
            
            return {
                'session_id': session_id,
                'response': processed_response['response'],
                'response_type': processed_response.get('response_type', 'enhanced_chat'),
                'intent': intent_analysis.get('intent'),
                'confidence': intent_analysis.get('confidence'),
                'source': processed_response.get('source', ResponseSource.FALLBACK),
                'educational_category': processed_response.get('educational_category'),
                'safety_level': safety_validation.get('level', SafetyLevel.SAFE),
                'resources': processed_response.get('resources', []),
                'metadata': {
                    'enhanced_features_used': True,
                    'q_services_available': await self._check_q_services_availability(),
                    'processing_time': processed_response.get('processing_time'),
                    'fallback_used': processed_response.get('fallback_used', False)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced chat processing: {e}")
            
            # Fallback to base chat agent
            try:
                fallback_response = await self.base_chat_agent.handle_message(
                    user_id, message, context, session_id
                )
                fallback_response['metadata'] = {
                    'enhanced_features_used': False,
                    'fallback_reason': str(e),
                    'fallback_to_base_agent': True
                }
                return fallback_response
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                return self._create_emergency_response(session_id, str(e))
    
    async def _enhanced_intent_recognition(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhanced intent recognition with Amazon Q capabilities.
        
        Recognizes educational intents that can benefit from Q services.
        """
        try:
            # First, try enhanced intent recognition
            enhanced_intent = await self._recognize_enhanced_intents(message, context)
            
            if enhanced_intent['confidence'] >= self.MEDIUM_CONFIDENCE_THRESHOLD:
                return enhanced_intent
            
            # Use TRUE agent intent recognition (no prompts)
            base_intent = await self.agent_core._agent_intent_recognition({
                **context,
                'user_message': message,
                'enhanced_mode': True
            })
            
            return {
                'intent': base_intent.get('intent', EnhancedChatIntent.GENERAL_CHAT),
                'confidence': base_intent.get('confidence', 0.5),
                'reasoning': base_intent.get('reasoning', 'Base intent recognition'),
                'enhanced_features': enhanced_intent.get('enhanced_features', []),
                'educational_indicators': enhanced_intent.get('educational_indicators', [])
            }
            
        except Exception as e:
            logger.error(f"Enhanced intent recognition failed: {e}")
            return {
                'intent': EnhancedChatIntent.GENERAL_CHAT,
                'confidence': 0.3,
                'reasoning': f'Intent recognition failed: {str(e)}',
                'error': True
            }
    
    async def _recognize_enhanced_intents(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recognize intents specific to Amazon Q capabilities."""
        message_lower = message.lower()
        
        # Check for enhanced intent keywords
        for intent_name, keywords in self.educational_intent_keywords.items():
            keyword_matches = sum(1 for keyword in keywords if keyword in message_lower)
            
            if keyword_matches > 0:
                confidence = min(0.9, 0.6 + (keyword_matches * 0.1))
                
                return {
                    'intent': EnhancedChatIntent(intent_name),
                    'confidence': confidence,
                    'reasoning': f'Detected {keyword_matches} keywords for {intent_name}',
                    'enhanced_features': [intent_name],
                    'educational_indicators': [kw for kw in keywords if kw in message_lower]
                }
        
        # Check for general educational patterns
        educational_patterns = [
            ('research', 'find', 'search'), # Research request
            ('help', 'code', 'programming'), # Coding help
            ('explain', 'what is', 'how does'), # Academic assistance
            ('resources', 'materials', 'references'), # Resource search
            ('study', 'learn', 'practice') # Study guidance
        ]
        
        for i, patterns in enumerate(educational_patterns):
            if any(pattern in message_lower for pattern in patterns):
                intent_mapping = [
                    EnhancedChatIntent.RESEARCH_REQUEST,
                    EnhancedChatIntent.CODING_HELP,
                    EnhancedChatIntent.ACADEMIC_ASSISTANCE,
                    EnhancedChatIntent.RESOURCE_SEARCH,
                    EnhancedChatIntent.STUDY_GUIDANCE
                ]
                
                return {
                    'intent': intent_mapping[i],
                    'confidence': 0.7,
                    'reasoning': f'Matched educational pattern: {patterns}',
                    'enhanced_features': ['pattern_matching'],
                    'educational_indicators': list(patterns)
                }
        
        return {
            'intent': EnhancedChatIntent.GENERAL_CHAT,
            'confidence': 0.4,
            'reasoning': 'No enhanced intents detected',
            'enhanced_features': [],
            'educational_indicators': []
        }
    
    async def _validate_educational_safety(
        self,
        message: str,
        intent_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate message safety and educational appropriateness using Amazon Q guardrails.
        """
        try:
            # Use Amazon Q service for content validation
            safety_check = await self.amazon_q._validate_content_safety(message)
            
            # Additional educational context validation
            educational_check = await self._validate_educational_context(
                message, intent_analysis, context
            )
            
            # Combine safety and educational validation
            if safety_check['level'] == SafetyLevel.BLOCKED:
                return {
                    'blocked': True,
                    'level': SafetyLevel.BLOCKED,
                    'reason': safety_check['reason'],
                    'type': 'safety_violation'
                }
            
            if not educational_check['appropriate']:
                return {
                    'blocked': True,
                    'level': SafetyLevel.BLOCKED,
                    'reason': educational_check['reason'],
                    'type': 'non_educational'
                }
            
            return {
                'blocked': False,
                'level': SafetyLevel.SAFE,
                'reason': 'Content passed all validation checks',
                'educational_score': educational_check.get('score', 0.8)
            }
            
        except Exception as e:
            logger.error(f"Safety validation failed: {e}")
            # Err on the side of caution
            return {
                'blocked': False,
                'level': SafetyLevel.NEEDS_REVIEW,
                'reason': f'Validation error: {str(e)}',
                'type': 'validation_error'
            }
    
    async def _validate_educational_context(
        self,
        message: str,
        intent_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate that the message is appropriate for educational context."""
        
        # Check if message has educational indicators
        educational_indicators = intent_analysis.get('educational_indicators', [])
        
        # Check current learning context
        has_learning_context = bool(
            context.get('current_lesson') or 
            context.get('learning_progress') or
            context.get('user_profile', {}).get('learning_style')
        )
        
        # Educational appropriateness score
        score = 0.0
        
        if educational_indicators:
            score += 0.4
        
        if has_learning_context:
            score += 0.3
        
        # Check for learning-related words
        learning_words = [
            'learn', 'study', 'understand', 'explain', 'help', 'teach',
            'practice', 'example', 'tutorial', 'homework', 'assignment'
        ]
        
        message_lower = message.lower()
        learning_word_count = sum(1 for word in learning_words if word in message_lower)
        score += min(0.3, learning_word_count * 0.1)
        
        return {
            'appropriate': score >= 0.5,
            'score': score,
            'reason': f'Educational appropriateness score: {score:.2f}' if score >= 0.5 
                     else 'Message does not appear to be educational in nature'
        }
    
    async def _route_to_optimal_service(
        self,
        intent_analysis: Dict[str, Any],
        context: Dict[str, Any],
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Route the request to the optimal AI service based on intent and availability.
        """
        intent = intent_analysis.get('intent', EnhancedChatIntent.GENERAL_CHAT)
        message = context.get('user_message', '')
        
        # Get preferred services for this intent
        preferred_services = self.service_routing.get(intent, [ResponseSource.BEDROCK_CLAUDE])
        
        # Try each service in order of preference
        for service in preferred_services:
            try:
                if service == QServiceType.BUSINESS:
                    return await self._handle_q_business_request(
                        user_id, message, intent, context, session_id
                    )
                elif service == QServiceType.DEVELOPER:
                    return await self._handle_q_developer_request(
                        user_id, message, intent, context, session_id
                    )
                elif service == ResponseSource.AGENT_CORE:
                    return await self._handle_agent_core_request(
                        intent_analysis, context, session_id
                    )
                elif service == ResponseSource.BEDROCK_CLAUDE:
                    return await self._handle_bedrock_request(
                        intent_analysis, context, session_id
                    )
                    
            except Exception as e:
                logger.warning(f"Service {service} failed: {e}, trying next service")
                continue
        
        # All services failed, use fallback
        return await self._handle_fallback_request(intent_analysis, context, session_id)
    
    async def _handle_q_business_request(
        self,
        user_id: str,
        message: str,
        intent: EnhancedChatIntent,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle request using Amazon Q Business."""
        
        if intent == EnhancedChatIntent.RESEARCH_REQUEST:
            # Extract research topic
            topic = await self._extract_research_topic(message)
            resources_response = await self.amazon_q.get_educational_resources(
                user_id=user_id,
                topic=topic,
                resource_type="research",
                difficulty_level=context.get('user_profile', {}).get('difficulty_level', 'intermediate')
            )
            
            if resources_response['success']:
                return {
                    'response': f"I found several research resources about {topic}:\n\n" + 
                              self._format_research_resources(resources_response['resources']),
                    'response_type': 'research_results',
                    'source': ResponseSource.AMAZON_Q_BUSINESS,
                    'resources': resources_response['resources'],
                    'educational_category': ContentCategory.RESEARCH
                }
        
        elif intent == EnhancedChatIntent.RESOURCE_SEARCH:
            # Extract resource search parameters
            topic = await self._extract_topic_from_message(message)
            resource_type = await self._extract_resource_type(message)
            
            resources_response = await self.amazon_q.get_educational_resources(
                user_id=user_id,
                topic=topic,
                resource_type=resource_type,
                difficulty_level=context.get('user_profile', {}).get('difficulty_level', 'intermediate')
            )
            
            if resources_response['success']:
                return {
                    'response': f"Here are educational resources for {topic}:\n\n" + 
                              self._format_educational_resources(resources_response['resources']),
                    'response_type': 'resource_list',
                    'source': ResponseSource.AMAZON_Q_BUSINESS,
                    'resources': resources_response['resources'],
                    'educational_category': ContentCategory.GENERAL_EDUCATION
                }
        
        # For other intents, use general Q Business chat
        q_response = await self.amazon_q.chat_with_q_business(
            user_id=user_id,
            message=message,
            conversation_id=session_id,
            educational_context=context
        )
        
        if q_response['success']:
            return {
                'response': q_response['response'],
                'response_type': 'q_business_chat',
                'source': ResponseSource.AMAZON_Q_BUSINESS,
                'resources': q_response.get('source_attributions', []),
                'educational_category': q_response.get('educational_category', ContentCategory.GENERAL_EDUCATION)
            }
        
        # Q Business failed, raise exception to try next service
        raise Exception(f"Q Business failed: {q_response.get('reason', 'Unknown error')}")
    
    async def _handle_q_developer_request(
        self,
        user_id: str,
        message: str,
        intent: EnhancedChatIntent,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle request using Amazon Q Developer."""
        
        if intent == EnhancedChatIntent.CODING_HELP:
            # Extract programming language and context
            programming_language = await self._extract_programming_language(message, context)
            
            coding_response = await self.amazon_q.get_coding_assistance(
                user_id=user_id,
                code_question=message,
                programming_language=programming_language,
                context={
                    'skill_level': context.get('user_profile', {}).get('difficulty_level', 'intermediate'),
                    'learning_context': context.get('current_lesson', {}).get('title', 'General Programming')
                }
            )
            
            if coding_response['success']:
                return {
                    'response': coding_response['response'],
                    'response_type': 'coding_assistance',
                    'source': ResponseSource.AMAZON_Q_DEVELOPER,
                    'code_examples': coding_response.get('code_examples', []),
                    'educational_category': ContentCategory.PROGRAMMING
                }
        
        # Q Developer failed or not applicable, raise exception to try next service
        raise Exception("Q Developer not available or not applicable for this request")
    
    async def _handle_agent_core_request(
        self,
        intent_analysis: Dict[str, Any],
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle request using TRUE Bedrock Agents for autonomous reasoning."""
        
        try:
            # Use actual Bedrock Agents instead of prompt-based reasoning
            agent_context = {
                **context,
                'intent_analysis': intent_analysis,
                'session_id': session_id,
                'user_message': context.get('user_message', ''),
                'autonomous_mode': True
            }
            
            # Determine the appropriate goal based on intent
            intent = intent_analysis.get('intent', EnhancedChatIntent.GENERAL_CHAT)
            goal = self._map_intent_to_agent_goal(intent)
            
            # Invoke Bedrock Agent for autonomous reasoning
            agent_response = await self.agent_core.reason_over_context(agent_context, goal)
            
            if agent_response.get('autonomous_decision'):
                return {
                    'response': agent_response.get('agent_response', 'I analyzed your request and here\'s my autonomous recommendation.'),
                    'response_type': 'autonomous_agent_response',
                    'source': ResponseSource.AGENT_CORE,
                    'autonomous': True,
                    'confidence': agent_response.get('confidence', 0.8),
                    'reasoning': agent_response.get('reasoning', 'Autonomous decision by Bedrock Agent'),
                    'recommendations': agent_response.get('recommendations', []),
                    'session_id': agent_response.get('session_id', session_id),
                    'agent_trace': agent_response.get('trace_data', [])
                }
            else:
                # Fallback if agent is unavailable
                return await self._handle_bedrock_request(intent_analysis, context, session_id)
                
        except Exception as e:
            logger.error(f"Agent Core request failed: {e}")
            # Fallback to Bedrock Claude
            return await self._handle_bedrock_request(intent_analysis, context, session_id)
    
    def _map_intent_to_agent_goal(self, intent: EnhancedChatIntent) -> str:
        """Map chat intent to agent goal for autonomous processing."""
        intent_goal_mapping = {
            EnhancedChatIntent.EXPLANATION: "provide_educational_explanation",
            EnhancedChatIntent.SUMMARIZATION: "create_learning_summary", 
            EnhancedChatIntent.QUIZ_REQUEST: "generate_assessment_quiz",
            EnhancedChatIntent.PROGRESS_INQUIRY: "analyze_learning_progress",
            EnhancedChatIntent.HELP_REQUEST: "provide_learning_assistance",
            EnhancedChatIntent.RESEARCH_REQUEST: "conduct_educational_research",
            EnhancedChatIntent.RESOURCE_SEARCH: "find_learning_resources",
            EnhancedChatIntent.CODING_HELP: "provide_programming_assistance",
            EnhancedChatIntent.ACADEMIC_ASSISTANCE: "provide_academic_support",
            EnhancedChatIntent.STUDY_GUIDANCE: "create_study_plan",
            EnhancedChatIntent.GENERAL_CHAT: "engage_educational_conversation"
        }
        
        return intent_goal_mapping.get(intent, "provide_general_educational_assistance")
    
    async def _handle_bedrock_request(
        self,
        intent_analysis: Dict[str, Any],
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle request using Bedrock Claude directly."""
        
        # Use the original chat agent's Bedrock functionality
        response = await self.base_chat_agent._execute_intent_based_response(
            intent_analysis, context
        )
        
        response['source'] = ResponseSource.BEDROCK_CLAUDE
        return response
    
    async def _handle_fallback_request(
        self,
        intent_analysis: Dict[str, Any],
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Handle request using fallback mechanisms."""
        
        return {
            'response': "I'm here to help with your learning! While some of my advanced features are temporarily unavailable, I can still assist with explanations, summaries, and general educational questions. What would you like to learn about?",
            'response_type': 'fallback',
            'source': ResponseSource.FALLBACK,
            'fallback_used': True,
            'educational_category': ContentCategory.GENERAL_EDUCATION
        }
    
    async def _post_process_educational_response(
        self,
        response_data: Dict[str, Any],
        intent_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Post-process response to ensure educational appropriateness."""
        
        # Validate response content
        response_content = response_data.get('response', '')
        
        # Check if response is educational
        if not await self.amazon_q._is_educational_content(response_content):
            # Enhance with educational context
            enhanced_response = await self._enhance_with_educational_context(
                response_content, intent_analysis, context
            )
            response_data['response'] = enhanced_response
            response_data['enhanced'] = True
        
        # Add educational suggestions if appropriate
        if intent_analysis.get('intent') in [
            EnhancedChatIntent.GENERAL_CHAT,
            EnhancedChatIntent.HELP_REQUEST
        ]:
            response_data['educational_suggestions'] = await self._generate_educational_suggestions(context)
        
        return response_data
    
    async def _enhance_with_educational_context(
        self,
        response: str,
        intent_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Enhance response with educational context and learning connections."""
        
        current_lesson = context.get('current_lesson', {})
        user_profile = context.get('user_profile', {})
        
        enhancements = []
        
        if current_lesson.get('title'):
            enhancements.append(f"This relates to your current lesson: {current_lesson['title']}")
        
        if user_profile.get('learning_style'):
            learning_style = user_profile['learning_style']
            if learning_style == 'visual':
                enhancements.append("💡 Tip: Try creating diagrams or mind maps to visualize these concepts!")
            elif learning_style == 'auditory':
                enhancements.append("🎧 Tip: Consider discussing this topic aloud or finding audio resources!")
            elif learning_style == 'kinesthetic':
                enhancements.append("✋ Tip: Look for hands-on activities or practical exercises related to this topic!")
        
        if enhancements:
            return f"{response}\n\n{' '.join(enhancements)}"
        
        return response
    
    async def _generate_educational_suggestions(self, context: Dict[str, Any]) -> List[str]:
        """Generate educational suggestions based on context."""
        
        suggestions = [
            "Ask me to explain any concept you're studying",
            "Request research resources on topics you're learning",
            "Get help with coding or programming questions",
            "Ask for study strategies and learning tips"
        ]
        
        current_lesson = context.get('current_lesson', {})
        if current_lesson.get('key_concepts'):
            concepts = current_lesson['key_concepts'][:2]  # First 2 concepts
            suggestions.insert(0, f"Ask me about: {', '.join(concepts)}")
        
        return suggestions
    
    # Helper methods for content extraction
    async def _extract_research_topic(self, message: str) -> str:
        """Extract research topic from message."""
        # Simple extraction - in production, use more sophisticated NLP
        message_lower = message.lower()
        
        # Remove common research request words
        research_words = ['research', 'find', 'search', 'about', 'on', 'papers', 'studies']
        words = message_lower.split()
        topic_words = [word for word in words if word not in research_words and len(word) > 2]
        
        return ' '.join(topic_words[:5])  # First 5 meaningful words
    
    async def _extract_topic_from_message(self, message: str) -> str:
        """Extract main topic from message."""
        # Simple topic extraction
        words = message.lower().split()
        
        # Remove common words
        stop_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
        meaningful_words = [word for word in words if word not in stop_words and len(word) > 2]
        
        return ' '.join(meaningful_words[:3])  # First 3 meaningful words
    
    async def _extract_resource_type(self, message: str) -> str:
        """Extract resource type from message."""
        message_lower = message.lower()
        
        resource_types = {
            'tutorial': ['tutorial', 'guide', 'how-to'],
            'research': ['paper', 'study', 'research', 'article'],
            'example': ['example', 'sample', 'demo'],
            'reference': ['reference', 'documentation', 'manual']
        }
        
        for resource_type, keywords in resource_types.items():
            if any(keyword in message_lower for keyword in keywords):
                return resource_type
        
        return 'all'
    
    async def _extract_programming_language(self, message: str, context: Dict[str, Any]) -> str:
        """Extract programming language from message or context."""
        message_lower = message.lower()
        
        languages = ['python', 'javascript', 'java', 'c++', 'c#', 'go', 'rust', 'php', 'ruby']
        
        for language in languages:
            if language in message_lower:
                return language
        
        # Check context for language hints
        current_lesson = context.get('current_lesson', {})
        if current_lesson.get('key_concepts'):
            for concept in current_lesson['key_concepts']:
                if any(lang in concept.lower() for lang in languages):
                    return next(lang for lang in languages if lang in concept.lower())
        
        return 'python'  # Default
    
    def _format_research_resources(self, resources: List[Dict[str, Any]]) -> str:
        """Format research resources for display."""
        if not resources:
            return "No specific resources found, but I can help you understand the topic better."
        
        formatted = []
        for i, resource in enumerate(resources[:5], 1):  # Limit to 5 resources
            title = resource.get('title', f'Resource {i}')
            description = resource.get('description', 'Educational resource')
            url = resource.get('url', '')
            
            resource_text = f"{i}. **{title}**\n   {description}"
            if url:
                resource_text += f"\n   Link: {url}"
            
            formatted.append(resource_text)
        
        return '\n\n'.join(formatted)
    
    def _format_educational_resources(self, resources: List[Dict[str, Any]]) -> str:
        """Format educational resources for display."""
        return self._format_research_resources(resources)  # Same formatting for now
    
    async def _build_comprehensive_context(
        self,
        user_id: str,
        session_id: str,
        message: str,
        base_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build comprehensive context including Q service availability."""
        
        # Start with base context from original chat agent
        context = await self.base_chat_agent._build_enhanced_context(
            user_id, session_id, message, base_context
        )
        
        # Add Q service availability
        q_health = await self.amazon_q.get_service_health()
        context['q_services_health'] = q_health
        
        # Add enhanced educational context
        context['enhanced_mode'] = True
        context['available_services'] = await self._get_available_services()
        
        return context
    
    async def _get_available_services(self) -> List[str]:
        """Get list of available AI services."""
        services = [ResponseSource.BEDROCK_CLAUDE, ResponseSource.AGENT_CORE]
        
        # Check Q services availability
        q_health = await self.amazon_q.get_service_health()
        
        if q_health['services']['q_business']['available']:
            services.append(ResponseSource.AMAZON_Q_BUSINESS)
        
        if q_health['services']['q_developer']['available']:
            services.append(ResponseSource.AMAZON_Q_DEVELOPER)
        
        return services
    
    async def _check_q_services_availability(self) -> Dict[str, bool]:
        """Check availability of Q services."""
        q_health = await self.amazon_q.get_service_health()
        
        return {
            'q_business': q_health['services']['q_business']['available'],
            'q_developer': q_health['services']['q_developer']['available'],
            'guardrails': q_health['services']['guardrails']['available']
        }
    
    async def _store_enhanced_chat_message(
        self,
        session_id: str,
        user_id: str,
        user_message: str,
        ai_response: Dict[str, Any],
        intent_analysis: Dict[str, Any]
    ) -> None:
        """Store enhanced chat message with additional metadata."""
        
        # Use base chat agent storage with enhanced metadata
        await self.base_chat_agent._store_chat_message(
            session_id=session_id,
            user_id=user_id,
            user_message=user_message,
            ai_response=ai_response['response'],
            intent_analysis={
                **intent_analysis,
                'enhanced_features': True,
                'source': ai_response.get('source'),
                'educational_category': ai_response.get('educational_category')
            }
        )
    
    async def _update_enhanced_memory(
        self,
        user_id: str,
        message: str,
        response: Dict[str, Any],
        intent_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> None:
        """Update agent memory with enhanced interaction data."""
        
        await self.agent_core.update_memory(user_id, {
            'enhanced_chat_interaction': {
                'user_message': message,
                'recognized_intent': intent_analysis.get('intent'),
                'confidence': intent_analysis.get('confidence'),
                'response_source': response.get('source'),
                'educational_category': response.get('educational_category'),
                'q_services_used': response.get('source') in [
                    ResponseSource.AMAZON_Q_BUSINESS,
                    ResponseSource.AMAZON_Q_DEVELOPER
                ],
                'resources_provided': len(response.get('resources', [])),
                'enhanced_features_used': True
            }
        })
    
    async def _create_safety_response(
        self,
        safety_validation: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Create response for blocked content."""
        
        return {
            'session_id': session_id,
            'response': "I'm designed to help with educational and learning-related questions. Please ask about academic topics, study materials, research, or learning strategies. I'm here to support your educational journey!",
            'response_type': 'safety_block',
            'intent': EnhancedChatIntent.HELP_REQUEST,
            'confidence': 1.0,
            'source': ResponseSource.FALLBACK,
            'safety_level': safety_validation['level'],
            'blocked_reason': safety_validation['reason'],
            'educational_suggestions': [
                "Ask for help with homework or assignments",
                "Request explanations of academic concepts",
                "Search for educational resources and materials",
                "Get study tips and learning strategies",
                "Ask for coding help with programming courses"
            ]
        }
    
    def _create_emergency_response(self, session_id: str, error: str) -> Dict[str, Any]:
        """Create emergency fallback response."""
        
        return {
            'session_id': session_id,
            'response': "I'm experiencing some technical difficulties, but I'm still here to help with your learning! Please try rephrasing your question, and I'll do my best to assist you with your studies.",
            'response_type': 'emergency_fallback',
            'intent': EnhancedChatIntent.GENERAL_CHAT,
            'confidence': 0.5,
            'source': ResponseSource.FALLBACK,
            'error': error,
            'metadata': {
                'emergency_fallback': True,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        }


# Global enhanced chat agent instance
enhanced_chat_agent = EnhancedAgenticChatAgent()