"""
Agentic Chat and Tutoring System for SnapStudy.

This module implements natural language intent recognition using AgentCore primitives
for autonomous conversation without requiring special command syntax.
The agent intelligently decides between summarize/explain/quiz/progress functions
based on conversational context.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from decimal import Decimal
import uuid

from .bedrock import bedrock_service
from .dynamodb import db_service
from .adaptive_agent import BedrockAgentCore
from ..config import settings

logger = logging.getLogger(__name__)


class ChatIntent(str, Enum):
    """Possible intents the agent can recognize from natural conversation."""
    SUMMARIZATION = "summarization"      # User wants a summary of current lesson
    EXPLANATION = "explanation"          # User wants concept explained
    QUIZ_REQUEST = "quiz_request"        # User wants to be quizzed
    PROGRESS_INQUIRY = "progress_inquiry" # User wants to know their progress
    HELP_REQUEST = "help_request"        # User needs general help
    GENERAL_CHAT = "general_chat"        # General conversational response
    ENCOURAGEMENT = "encouragement"      # User needs motivation/support


class AgenticChatAgent:
    """
    Natural Agentic Chat Agent that uses AgentCore primitives for intelligent
    conversation without requiring special command syntax.
    
    The agent autonomously recognizes user intent and decides what type of
    response is needed based on conversational context.
    """
    
    def __init__(self):
        self.agent_core = BedrockAgentCore()
        self.bedrock = bedrock_service
        self.db = db_service
        
        # Intent recognition confidence thresholds
        self.HIGH_CONFIDENCE_THRESHOLD = 0.8
        self.MEDIUM_CONFIDENCE_THRESHOLD = 0.6
        
        # Response templates for different intents
        self.intent_functions = {
            ChatIntent.SUMMARIZATION: self._handle_summarization,
            ChatIntent.EXPLANATION: self._handle_explanation,
            ChatIntent.QUIZ_REQUEST: self._handle_quiz_request,
            ChatIntent.PROGRESS_INQUIRY: self._handle_progress_inquiry,
            ChatIntent.HELP_REQUEST: self._handle_help_request,
            ChatIntent.GENERAL_CHAT: self._handle_general_chat,
            ChatIntent.ENCOURAGEMENT: self._handle_encouragement
        }
    
    async def handle_message(
        self, 
        user_id: str,
        message: str, 
        context: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle real-time chat messages with agentic intent recognition.
        
        Args:
            user_id: ID of the user sending the message
            message: The user's message
            context: Current learning context (lesson, progress, etc.)
            session_id: Optional chat session ID
            
        Returns:
            Dict containing the response and metadata
        """
        try:
            logger.info(f"Processing chat message from user {user_id}: {message[:100]}...")
            
            # Get or create session ID
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # Handle anonymous users
            if not user_id or user_id == 'anonymous':
                user_id = 'anonymous'
                # Skip user profile lookup for anonymous users
                enhanced_context = {
                    'user_id': user_id,
                    'message': message,
                    'session_id': session_id,
                    'user_profile': None,
                    **context
                }
            else:
                # Retrieve conversation history and user context for authenticated users
                enhanced_context = await self._build_enhanced_context(
                    user_id, session_id, message, context
                )
            
            # Use AgentCore to analyze intent and context
            intent_analysis = await self.agent_core.reason_over_context(
                context=enhanced_context,
                goal="understand_user_intent_and_provide_appropriate_response"
            )
            
            # Execute appropriate response based on recognized intent
            response_data = await self._execute_intent_based_response(
                intent_analysis, enhanced_context
            )
            
            # Store conversation in chat history
            await self._store_chat_message(
                session_id, user_id, message, response_data['response'], intent_analysis
            )
            
            # Update agent memory with this interaction
            await self.agent_core.update_memory(user_id, {
                'chat_interaction': {
                    'user_message': message,
                    'recognized_intent': intent_analysis.get('intent'),
                    'confidence': Decimal(str(intent_analysis.get('confidence', 0.0))),
                    'response_type': response_data.get('response_type'),
                    'context_summary': enhanced_context.get('context_summary', {})
                }
            })
            
            return {
                'session_id': session_id,
                'response': response_data['response'],
                'response_type': response_data.get('response_type', 'text'),
                'intent': intent_analysis.get('intent'),
                'confidence': Decimal(str(intent_analysis.get('confidence', 0.0))),
                'metadata': response_data.get('metadata', {})
            }
            
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
            return {
                'session_id': session_id or str(uuid.uuid4()),
                'response': "I'm sorry, I'm having trouble understanding right now. Could you try rephrasing your question?",
                'response_type': 'text',
                'intent': ChatIntent.GENERAL_CHAT,
                'confidence': Decimal('0.0'),
                'error': str(e)
            }
    
    async def _build_enhanced_context(
        self, 
        user_id: str, 
        session_id: str, 
        current_message: str,
        base_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build comprehensive context for intent recognition including conversation history,
        user profile, current lesson context, and learning progress.
        """
        # Get conversation history
        chat_history = await self._get_chat_history(session_id, limit=10)
        
        # Get user profile and learning preferences
        user_profile = await self.db.get_user_by_id(user_id)
        
        # Get recent learning activity
        recent_engagement = await self.db.get_user_engagement(user_id, limit=5)
        
        # Get agent memory for this user
        agent_memory = await self.agent_core.retrieve_memory(user_id)
        
        # Build enhanced context
        enhanced_context = {
            'user_message': current_message,
            'conversation_history': chat_history,
            'user_profile': user_profile or {},
            'current_lesson': base_context.get('current_lesson', {}),
            'learning_progress': base_context.get('learning_progress', {}),
            'recent_engagement': recent_engagement,
            'agent_memory': agent_memory,
            'session_id': session_id,
            'context_summary': {
                'has_active_lesson': bool(base_context.get('current_lesson')),
                'recent_quiz_performance': self._extract_recent_quiz_performance(recent_engagement),
                'conversation_length': len(chat_history),
                'user_learning_style': user_profile.get('learning_style') if user_profile else None
            }
        }
        
        return enhanced_context
    
    async def _execute_intent_based_response(
        self, 
        intent_analysis: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute appropriate response based on recognized intent with confidence scoring.
        """
        intent = intent_analysis.get('intent', ChatIntent.GENERAL_CHAT)
        confidence = Decimal(str(intent_analysis.get('confidence', 0.5)))
        
        # Map string intent to enum if needed
        if isinstance(intent, str):
            try:
                intent = ChatIntent(intent.lower())
            except ValueError:
                intent = ChatIntent.GENERAL_CHAT
        
        # Execute intent-specific handler if confidence is high enough
        if confidence >= Decimal(str(self.MEDIUM_CONFIDENCE_THRESHOLD)) and intent in self.intent_functions:
            handler = self.intent_functions[intent]
            return await handler(intent_analysis, context)
        else:
            # Fall back to general chat for low confidence
            return await self._handle_general_chat(intent_analysis, context)
    
    async def _handle_summarization(
        self, 
        intent_analysis: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle summarization requests using AgentCore function invocation."""
        current_lesson = context.get('current_lesson', {})
        
        if not current_lesson:
            return {
                'response': "I don't see any active lesson to summarize. Would you like me to help you start a new lesson?",
                'response_type': 'text'
            }
        
        try:
            # Use AgentCore function invocation for summarization
            summary = await self.agent_core.invoke_function(
                function_name="summarize_lesson",
                parameters={
                    'lesson_content': current_lesson.get('content', ''),
                    'key_concepts': current_lesson.get('key_concepts', []),
                    'user_profile': context.get('user_profile', {}),
                    'learning_progress': context.get('learning_progress', {})
                }
            )
            
            return {
                'response': summary,
                'response_type': 'summary',
                'metadata': {
                    'lesson_id': current_lesson.get('lesson_id'),
                    'lesson_title': current_lesson.get('title')
                }
            }
            
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            # Fallback to simple summary
            key_concepts = current_lesson.get('key_concepts', [])
            if key_concepts:
                concepts_text = ", ".join(key_concepts[:3])
                return {
                    'response': f"Here's a quick summary: We've been covering {concepts_text}. The main focus has been on understanding these core concepts and how they apply to your learning goals.",
                    'response_type': 'summary'
                }
            else:
                return {
                    'response': "We're currently working through your lesson content. The key focus is building understanding step by step.",
                    'response_type': 'summary'
                }
    
    async def _handle_explanation(
        self, 
        intent_analysis: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle explanation requests using AgentCore function invocation."""
        concept_to_explain = intent_analysis.get('concept_to_explain', '')
        user_message = context.get('user_message', '')
        
        # Extract concept from user message if not provided
        if not concept_to_explain:
            concept_to_explain = await self._extract_concept_from_message(user_message)
        
        try:
            # Use AgentCore function invocation for explanation
            explanation = await self.agent_core.invoke_function(
                function_name="explain_concept",
                parameters={
                    'concept': concept_to_explain,
                    'lesson_context': context.get('current_lesson', {}),
                    'user_learning_style': context.get('user_profile', {}).get('learning_style', 'visual'),
                    'user_background': {
                        'profession': context.get('user_profile', {}).get('profession', ''),
                        'education_level': context.get('user_profile', {}).get('education_level', ''),
                        'difficulty_preference': context.get('user_profile', {}).get('difficulty_level', 'intermediate')
                    }
                }
            )
            
            return {
                'response': explanation,
                'response_type': 'explanation',
                'metadata': {
                    'concept': concept_to_explain,
                    'learning_style': context.get('user_profile', {}).get('learning_style')
                }
            }
            
        except Exception as e:
            logger.error(f"Explanation failed: {e}")
            return {
                'response': f"I'd be happy to explain {concept_to_explain or 'that concept'}! Let me break it down in simple terms based on what we've been learning. Could you be more specific about which part you'd like me to focus on?",
                'response_type': 'explanation'
            }
    
    async def _handle_quiz_request(
        self, 
        intent_analysis: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle quiz requests using AgentCore function invocation."""
        current_lesson = context.get('current_lesson', {})
        
        if not current_lesson:
            return {
                'response': "I'd love to quiz you! However, I don't see an active lesson. Would you like to start a lesson first, or shall I ask you some general questions about a topic you're interested in?",
                'response_type': 'text'
            }
        
        try:
            # Use AgentCore function invocation for practice quiz generation
            quiz = await self.agent_core.invoke_function(
                function_name="generate_practice_quiz",
                parameters={
                    'lesson_content': current_lesson.get('content', ''),
                    'key_concepts': current_lesson.get('key_concepts', []),
                    'difficulty': context.get('user_profile', {}).get('difficulty_level', 'intermediate'),
                    'num_questions': 2,  # Shorter quiz for chat context
                    'question_types': ['multiple_choice', 'true_false']  # Simpler types for chat
                }
            )
            
            return {
                'response': "Great! I've prepared a quick quiz for you. Let's see how you're doing with the current material.",
                'response_type': 'quiz',
                'metadata': {
                    'quiz_data': quiz,
                    'lesson_id': current_lesson.get('lesson_id')
                }
            }
            
        except Exception as e:
            logger.error(f"Quiz generation failed: {e}")
            return {
                'response': "I'd love to quiz you on what we've been learning! How about this: Can you tell me the main concept we've been focusing on in this lesson?",
                'response_type': 'quiz'
            }
    
    async def _handle_progress_inquiry(
        self, 
        intent_analysis: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle progress inquiries using AgentCore function invocation."""
        user_id = context.get('user_profile', {}).get('user_id')
        
        if not user_id:
            return {
                'response': "I'm having trouble accessing your progress information right now. Please try again in a moment.",
                'response_type': 'text'
            }
        
        try:
            # Use AgentCore function invocation for progress analysis
            progress_summary = await self.agent_core.invoke_function(
                function_name="show_progress",
                parameters={
                    'user_id': user_id,
                    'current_lesson': context.get('current_lesson', {}),
                    'learning_progress': context.get('learning_progress', {}),
                    'recent_engagement': context.get('recent_engagement', [])
                }
            )
            
            return {
                'response': progress_summary,
                'response_type': 'progress',
                'metadata': {
                    'user_id': user_id,
                    'progress_data': context.get('learning_progress', {})
                }
            }
            
        except Exception as e:
            logger.error(f"Progress inquiry failed: {e}")
            # Fallback to simple progress response
            progress = context.get('learning_progress', {})
            if progress:
                completion = progress.get('completion_percentage', 0)
                return {
                    'response': f"You're making great progress! You've completed {completion:.1f}% of your current lesson. Keep up the excellent work!",
                    'response_type': 'progress'
                }
            else:
                return {
                    'response': "You're just getting started on your learning journey! Every step forward is progress. Would you like to begin a new lesson?",
                    'response_type': 'progress'
                }
    
    async def _handle_help_request(
        self, 
        intent_analysis: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle general help requests."""
        help_text = """I'm here to help you learn! Here's what I can do:

🎯 **Ask me anything** - I'll understand what you need naturally
📚 **Get summaries** - "Can you summarize what we've covered?"
💡 **Explain concepts** - "I don't understand X" or "Can you explain Y?"
🧠 **Practice with quizzes** - "Test my knowledge" or "Quiz me"
📊 **Check progress** - "How am I doing?" or "What's my progress?"

I adapt to your learning style and provide personalized help. Just ask me anything in your own words!"""
        
        return {
            'response': help_text,
            'response_type': 'help',
            'metadata': {
                'help_type': 'general'
            }
        }
    
    async def _handle_encouragement(
        self, 
        intent_analysis: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle encouragement and motivation requests."""
        user_profile = context.get('user_profile', {})
        recent_performance = self._extract_recent_quiz_performance(
            context.get('recent_engagement', [])
        )
        
        # Personalized encouragement based on recent performance
        if recent_performance and recent_performance.get('avg_score', 0) > 0.8:
            encouragement = f"You're doing fantastic! Your recent performance shows you're really mastering this material. Your dedication to learning is impressive - keep up the excellent work!"
        elif recent_performance and recent_performance.get('avg_score', 0) > 0.6:
            encouragement = f"You're making solid progress! Learning takes time, and you're building understanding step by step. Every question you ask and every concept you work through is moving you forward."
        else:
            encouragement = f"Remember, every expert was once a beginner! Learning is a journey, and you're taking all the right steps. Don't be discouraged - I'm here to help you succeed."
        
        return {
            'response': encouragement,
            'response_type': 'encouragement',
            'metadata': {
                'performance_context': recent_performance
            }
        }
    
    async def _handle_general_chat(
        self, 
        intent_analysis: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle general conversational responses."""
        user_message = context.get('user_message', '')
        current_lesson = context.get('current_lesson', {})
        
        # Generate contextual response using Bedrock
        chat_prompt = f"""
        You are an AI tutor having a natural conversation with a student. 
        
        Student message: {user_message}
        
        Current lesson context: {current_lesson.get('title', 'No active lesson')}
        
        Provide a helpful, encouraging response that:
        1. Acknowledges their message naturally
        2. Relates to their learning context when appropriate
        3. Offers gentle guidance toward learning activities
        4. Maintains a supportive, friendly tone
        
        Keep the response conversational and under 100 words.
        """
        
        try:
            response = await self.bedrock.invoke_claude(
                prompt=chat_prompt,
                max_tokens=4096,
                temperature=0.7
            )
            
            return {
                'response': response.strip(),
                'response_type': 'chat',
                'metadata': {
                    'conversation_type': 'general'
                }
            }
            
        except Exception as e:
            logger.error(f"General chat response failed: {e}")
            return {
                'response': "I'm here to help with your learning! Is there anything specific you'd like to know or work on?",
                'response_type': 'chat'
            }
    
    async def _extract_concept_from_message(self, message: str) -> str:
        """Extract the concept the user wants explained from their message."""
        # Simple extraction - in a real implementation, this could be more sophisticated
        explain_keywords = ['explain', 'what is', 'what are', 'how does', 'how do', 'tell me about']
        
        message_lower = message.lower()
        for keyword in explain_keywords:
            if keyword in message_lower:
                # Extract text after the keyword
                parts = message_lower.split(keyword, 1)
                if len(parts) > 1:
                    concept = parts[1].strip().rstrip('?').strip()
                    return concept[:50]  # Limit length
        
        # Fallback: return the whole message if no specific pattern found
        return message[:50]
    
    def _extract_recent_quiz_performance(self, engagement_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Extract recent quiz performance from engagement data."""
        quiz_events = [
            event for event in engagement_data 
            if event.get('event_type') == 'quiz_completed'
        ]
        
        if not quiz_events:
            return None
        
        scores = []
        for event in quiz_events[-5:]:  # Last 5 quizzes
            event_data = event.get('event_data', {})
            if 'score' in event_data:
                scores.append(event_data['score'])
        
        if scores:
            return {
                'avg_score': sum(scores) / len(scores),
                'recent_scores': scores,
                'quiz_count': len(scores)
            }
        
        return None
    
    async def _get_chat_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve conversation history for the session."""
        try:
            response = self.db.chat_history_table.get_item(
                Key={'session_id': session_id}
            )
            
            if 'Item' in response:
                messages = response['Item'].get('messages', [])
                return messages[-limit:] if messages else []
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to retrieve chat history: {e}")
            return []
    
    async def _store_chat_message(
        self, 
        session_id: str, 
        user_id: str, 
        user_message: str, 
        ai_response: str,
        intent_analysis: Dict[str, Any]
    ) -> None:
        """Store chat message in conversation history."""
        try:
            now = datetime.now(timezone.utc)
            
            # Get existing conversation or create new one
            response = self.db.chat_history_table.get_item(
                Key={'session_id': session_id}
            )
            
            if 'Item' in response:
                # Update existing conversation
                messages = response['Item'].get('messages', [])
            else:
                # Create new conversation
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
                    'intent': intent_analysis.get('intent'),
                    'confidence': Decimal(str(intent_analysis.get('confidence', 0.0)))
                }
            ])
            
            # Keep only recent messages (last 50)
            if len(messages) > 50:
                messages = messages[-50:]
            
            # Calculate TTL (30 days from now)
            ttl = int((now.timestamp() + (30 * 24 * 60 * 60)))
            
            # Store updated conversation
            self.db.chat_history_table.put_item(
                Item={
                    'session_id': session_id,
                    'user_id': user_id,
                    'messages': messages,
                    'updated_at': now.isoformat(),
                    'ttl': ttl
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to store chat message: {e}")
    
    async def get_chat_history(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """Get complete chat history for a session."""
        try:
            response = self.db.chat_history_table.get_item(
                Key={'session_id': session_id}
            )
            
            if 'Item' in response:
                item = response['Item']
                # Verify user owns this session
                if item.get('user_id') == user_id:
                    return {
                        'session_id': session_id,
                        'messages': item.get('messages', []),
                        'updated_at': item.get('updated_at')
                    }
            
            return {
                'session_id': session_id,
                'messages': [],
                'updated_at': None
            }
            
        except Exception as e:
            logger.error(f"Failed to get chat history: {e}")
            return {
                'session_id': session_id,
                'messages': [],
                'error': str(e)
            }


# Global service instance
chat_agent = AgenticChatAgent()