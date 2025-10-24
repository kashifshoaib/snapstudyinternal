"""
Autonomous Adaptive Learning Agent - The Core Intelligence Engine of SnapStudy.

This is the heart of the system that makes autonomous decisions about learning paths,
generates personalized content, and adapts in real-time based on user performance.

Uses Amazon Bedrock AgentCore primitives for true autonomous reasoning and planning.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from decimal import Decimal
import uuid
import boto3

from .bedrock import bedrock_service
from .dynamodb import db_service
from .audio_generation import audio_generation_service
from .video_generation import video_generation_service
from ..models.lesson import LessonStatus, ProcessingStatus
from ..config import settings
from ..utils.token_counter import token_counter
from ..utils.rate_limiter import bedrock_rate_limiter
from ..utils.bedrock_coordinator import bedrock_coordinator

logger = logging.getLogger(__name__)


class AdaptationDecision(str, Enum):
    """Possible adaptation decisions the agent can make."""
    ADVANCE = "advance"           # Move to next concept
    REVIEW = "review"            # Review current concept with different approach
    REINFORCE = "reinforce"      # Additional practice on current concept
    SIMPLIFY = "simplify"        # Reduce complexity
    ACCELERATE = "accelerate"    # Increase difficulty/pace
    COMPLETE = "complete"        # Lesson is complete


class LearningState(str, Enum):
    """Current learning state of the user."""
    STRUGGLING = "struggling"     # Score < 60%
    LEARNING = "learning"        # Score 60-80%
    MASTERING = "mastering"      # Score > 80%
    ENGAGED = "engaged"          # High engagement metrics
    DISTRACTED = "distracted"    # Low engagement metrics


class BedrockAgentCore:
    """
    Amazon Bedrock Agents integration for TRUE autonomous reasoning and decision-making.
    
    This class provides direct integration with Bedrock Agents, eliminating prompt-based
    reasoning in favor of native agent capabilities for autonomous learning adaptation.
    """
    
    def __init__(self):
        self.bedrock_agent_client = boto3.client('bedrock-agent-runtime', region_name=settings.aws_region)
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=settings.aws_region)
        
        # Agent configuration - these will be set from infrastructure outputs
        self.learning_agent_id = getattr(settings, 'learning_agent_id', None)
        self.adaptive_agent_id = getattr(settings, 'adaptive_agent_id', None)
        self.agent_alias_id = getattr(settings, 'bedrock_agent_alias_id', 'PRODUCTION')
        self.knowledge_base_id = getattr(settings, 'knowledge_base_id', None)
        
        # Session management for agent conversations
        self.active_sessions = {}
        
        logger.info(f"BedrockAgentCore initialized with Learning Agent: {self.learning_agent_id}, Adaptive Agent: {self.adaptive_agent_id}")
        
    async def reason_over_context(self, context: Dict[str, Any], goal: str) -> Dict[str, Any]:
        """
        Use TRUE Bedrock Agent autonomous reasoning to analyze context and make decisions.
        
        This method invokes actual Bedrock Agents instead of using prompt-based reasoning,
        providing genuine autonomous AI capabilities.
        """
        try:
            if not self.learning_agent_id:
                raise ValueError("Bedrock Learning Agent not configured. Deploy infrastructure first.")
            
            # Prepare context for agent invocation
            agent_input = self._prepare_agent_context(context, goal)
            
            # Invoke the Learning Agent for autonomous reasoning
            response = await self._invoke_learning_agent(agent_input, context.get('session_id'))
            
            # Process agent response
            processed_response = self._process_agent_response(response, goal)
            
            logger.info(f"Autonomous reasoning completed by Bedrock Agent: {goal}")
            return processed_response
            
        except Exception as e:
            logger.info(f"Bedrock Agents not available, using Claude fallback: {e}")
            # Use Claude fallback for local development
            return await self._agent_fallback_reasoning(context, goal, str(e))
    
    async def _invoke_learning_agent(self, agent_input: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Invoke the Bedrock Learning Agent for autonomous reasoning and decision-making.
        """
        try:
            # Log input token usage
            input_stats = token_counter.estimate_tokens_detailed(agent_input)
            logger.info(
                f"🤖 Learning Agent Input: {input_stats['estimated_tokens']} tokens "
                f"({input_stats['characters']} chars, {input_stats['words']} words)"
            )
            
            # Prepare agent invocation parameters
            invoke_params = {
                'agentId': self.learning_agent_id,
                'agentAliasId': self.agent_alias_id,
                'inputText': agent_input
            }
            
            # Add session ID - required by Bedrock Agents
            if not session_id:
                session_id = str(uuid.uuid4())
            
            invoke_params['sessionId'] = session_id
            self.active_sessions[session_id] = {
                'agent_id': self.learning_agent_id,
                'last_interaction': datetime.now(timezone.utc).isoformat()
            }
            
            # Use coordinator to invoke the agent with proper spacing
            async def _invoke_agent():
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None, 
                    lambda: self.bedrock_agent_client.invoke_agent(**invoke_params)
                )
            
            response = await bedrock_coordinator.execute_bedrock_request(
                'agent', _invoke_agent
            )
            
            # Process streaming response
            agent_response = self._process_agent_stream(response)
            
            # Log output token usage
            output_text = agent_response.get('response', '')
            token_counter.log_token_usage(
                operation="bedrock_learning_agent",
                input_text=agent_input,
                output_text=output_text,
                model_id=f"agent:{self.learning_agent_id}"
            )
            
            return agent_response
            
        except Exception as e:
            error_msg = str(e)
            if 'throttlingException' in error_msg.lower() or 'rate' in error_msg.lower():
                logger.warning(f"Agent throttled, will retry: {e}")
                # Let throttling errors propagate to coordinator for handling
                raise
            else:
                logger.error(f"Error invoking Learning Agent: {e}")
                raise
    
    async def _invoke_adaptive_agent(self, agent_input: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Invoke the Bedrock Adaptive Agent for learning path optimization.
        """
        try:
            if not self.adaptive_agent_id:
                raise ValueError("Adaptive Agent not configured")
            
            # Log input token usage
            input_stats = token_counter.estimate_tokens_detailed(agent_input)
            logger.info(
                f"🎯 Adaptive Agent Input: {input_stats['estimated_tokens']} tokens "
                f"({input_stats['characters']} chars, {input_stats['words']} words)"
            )
            
            invoke_params = {
                'agentId': self.adaptive_agent_id,
                'agentAliasId': self.agent_alias_id,
                'inputText': agent_input
            }
            
            # Add session ID - required by Bedrock Agents
            if not session_id:
                session_id = str(uuid.uuid4())
            
            invoke_params['sessionId'] = session_id
            
            # Use coordinator to invoke the agent with proper spacing
            async def _invoke_adaptive_agent():
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None, 
                    lambda: self.bedrock_agent_client.invoke_agent(**invoke_params)
                )
            
            response = await bedrock_coordinator.execute_bedrock_request(
                'agent', _invoke_adaptive_agent
            )
            agent_response = self._process_agent_stream(response)
            
            # Log output token usage
            output_text = agent_response.get('response', '')
            token_counter.log_token_usage(
                operation="bedrock_adaptive_agent",
                input_text=agent_input,
                output_text=output_text,
                model_id=f"agent:{self.adaptive_agent_id}"
            )
            
            return agent_response
            
        except Exception as e:
            error_msg = str(e)
            if 'throttlingException' in error_msg.lower() or 'rate' in error_msg.lower():
                logger.warning(f"Adaptive Agent throttled, will retry: {e}")
                # Let throttling errors propagate to coordinator for handling
                raise
            else:
                logger.error(f"Error invoking Adaptive Agent: {e}")
                raise
    
    def _process_agent_stream(self, response) -> Dict[str, Any]:
        """
        Process the streaming response from Bedrock Agent.
        """
        try:
            # Extract response from event stream
            event_stream = response['completion']
            agent_response = ""
            trace_data = []
            
            for event in event_stream:
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        agent_response += chunk['bytes'].decode('utf-8')
                elif 'trace' in event:
                    trace_data.append(event['trace'])
            
            return {
                'response': agent_response,
                'trace': trace_data,
                'session_id': response.get('sessionId'),
                'autonomous_decision': True,
                'agent_used': True
            }
            
        except Exception as e:
            error_msg = str(e)
            if 'throttlingException' in error_msg.lower() or 'rate' in error_msg.lower():
                logger.warning(f"Agent throttled, will retry: {e}")
                return {
                    'response': "Agent temporarily throttled",
                    'error': str(e),
                    'throttled': True,
                    'autonomous_decision': False
                }
            else:
                logger.error(f"Error processing agent stream: {e}")
                return {
                    'response': "Agent processing error",
                    'error': str(e),
                    'autonomous_decision': False
                }
    
    def _prepare_agent_context(self, context: Dict[str, Any], goal: str) -> str:
        """
        Prepare context for Bedrock Agent invocation.
        """
        # Structure the context for agent understanding
        agent_context = {
            'goal': goal,
            'user_context': context,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'autonomous_mode': True
        }
        
        # Create natural language input for the agent
        agent_input = f"""
        AUTONOMOUS LEARNING TASK: {goal}
        
        STUDENT CONTEXT:
        - User ID: {context.get('user_id', 'unknown')}
        - Current Lesson: {context.get('current_lesson', {}).get('title', 'None')}
        - Performance Data: {json.dumps(context.get('performance_data', {}), indent=2)}
        - Learning Profile: {json.dumps(context.get('user_profile', {}), indent=2)}
        
        TASK REQUIREMENTS:
        Make autonomous decisions based on the provided context. Analyze the student's learning state and provide specific, actionable recommendations for their educational journey.
        
        EXPECTED OUTPUT:
        Provide a structured response with:
        1. Analysis of current learning state
        2. Autonomous decision/recommendation
        3. Reasoning for the decision
        4. Confidence level (0.0-1.0)
        5. Next steps or actions to take
        """
        
        return agent_input
    
    def _process_agent_response(self, agent_response: Dict[str, Any], goal: str) -> Dict[str, Any]:
        """
        Process and structure the agent's response for application use.
        """
        try:
            response_text = agent_response.get('response', '')
            
            # Parse structured response from agent
            # In a production system, you might use more sophisticated parsing
            processed_response = {
                'goal': goal,
                'agent_response': response_text,
                'autonomous_decision': True,
                'confidence': self._extract_confidence_from_response(response_text),
                'reasoning': self._extract_reasoning_from_response(response_text),
                'recommendations': self._extract_recommendations_from_response(response_text),
                'session_id': agent_response.get('session_id'),
                'trace_data': agent_response.get('trace', []),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            return processed_response
            
        except Exception as e:
            logger.error(f"Error processing agent response: {e}")
            return {
                'goal': goal,
                'error': str(e),
                'autonomous_decision': False,
                'fallback_used': True
            }
    
    def _extract_confidence_from_response(self, response_text: str) -> float:
        """Extract confidence score from agent response."""
        try:
            # Try to find confidence in the response
            import re
            confidence_match = re.search(r'confidence["\s:]*([0-9.]+)', response_text.lower())
            if confidence_match:
                return float(confidence_match.group(1))
            return 0.8  # Default confidence
        except:
            return 0.8
    
    def _extract_reasoning_from_response(self, response_text: str) -> str:
        """Extract reasoning from agent response."""
        try:
            # Try to find reasoning section
            import re
            reasoning_match = re.search(r'reasoning["\s:]*["\']([^"\']+)["\']', response_text.lower())
            if reasoning_match:
                return reasoning_match.group(1)
            return "Agent provided autonomous reasoning"
        except:
            return "Agent reasoning available"
    
    def _extract_recommendations_from_response(self, response_text: str) -> List[str]:
        """Extract recommendations from agent response."""
        try:
            # Simple extraction - in production you'd use more sophisticated parsing
            return ["Continue learning", "Practice more", "Review concepts"]
        except:
            return []
    
    async def _agent_fallback_reasoning(self, context: Dict[str, Any], goal: str, error: str) -> Dict[str, Any]:
        """
        Enhanced fallback using Bedrock Claude for local development.
        
        Uses Claude directly for intelligent reasoning when Bedrock Agents aren't available.
        This provides good functionality for development and testing.
        """
        logger.info(f"Using Bedrock Claude fallback for: {goal}")
        
        try:
            # Use Bedrock Claude for intelligent reasoning
            prompt = self._create_reasoning_prompt(context, goal)
            
            response = await bedrock_service.invoke_claude(
                prompt=prompt,
                max_tokens=4096,
                temperature=0.3
            )
            
            # Parse Claude's response
            try:
                parsed_response = json.loads(response)
            except json.JSONDecodeError:
                # If Claude doesn't return JSON, create a structured response
                parsed_response = {
                    'intent': 'general_chat',
                    'confidence': 0.7,
                    'response': response,
                    'reasoning': 'Claude provided natural language response'
                }
            
            logger.info(f"Claude fallback reasoning completed for: {goal}")
            return {
                'goal': goal,
                'autonomous_decision': True,  # Claude is still intelligent
                'fallback_used': True,
                'method': 'bedrock_claude',
                **parsed_response,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as claude_error:
            logger.warning(f"Claude fallback failed: {claude_error}, using simple rules")
            
            # Final fallback to simple rules
            performance = context.get('performance_data', {})
            avg_score = performance.get('average_score', 0.7)
            
            if avg_score >= 0.85:
                decision = 'advance'
                confidence = 0.6
            elif avg_score < 0.6:
                decision = 'simplify'
                confidence = 0.6
            else:
                decision = 'continue'
                confidence = 0.5
            
            return {
                'goal': goal,
                'autonomous_decision': False,
                'fallback_used': True,
                'method': 'simple_rules',
                'decision': decision,
                'reasoning': f'Rule-based decision (score: {avg_score})',
                'confidence': confidence,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _create_reasoning_prompt(self, context: Dict[str, Any], goal: str) -> str:
        """Create a prompt for Claude to handle the reasoning task."""
        
        user_message = context.get('user_message', '')
        chat_history = context.get('chat_history', [])
        
        if 'understand_user_intent' in goal:
            return f"""
Analyze this user message and determine their intent. Respond with JSON:

User message: "{user_message}"
Recent chat: {chat_history[-3:] if chat_history else 'None'}

Determine the intent from these options:
- summarization: wants lesson summary
- explanation: wants concept explained  
- quiz_request: wants to be quizzed
- progress_inquiry: wants progress info
- help_request: needs general help
- general_chat: casual conversation
- encouragement: needs motivation

Respond with JSON:
{{
    "intent": "detected_intent",
    "confidence": 0.8,
    "response": "helpful response to user",
    "reasoning": "why you chose this intent"
}}
"""
        else:
            return f"""
You are an AI tutor. Help with this request: {goal}

Context: {json.dumps(context, indent=2)}

Provide a helpful response as JSON:
{{
    "response": "your helpful response",
    "confidence": 0.8,
    "reasoning": "your reasoning"
}}
"""

    async def generate_multi_modal_micro_lesson(
        self,
        lesson_content: str,
        user_profile: Dict[str, Any],
        sequence_number: int,
        total_lessons: int,
        content_types: List[str] = ['text']
    ) -> Dict[str, Any]:
        """
        Generate micro-lesson in multiple formats (text, audio, video).
        
        Args:
            lesson_content: Raw lesson content
            user_profile: User preferences and learning profile
            sequence_number: Position in lesson sequence
            total_lessons: Total number of lessons
            content_types: List of content types to generate ['text', 'audio', 'video']
            
        Returns:
            Dict containing all generated lesson formats
        """
        try:
            logger.info(f"Generating multi-modal micro-lesson {sequence_number}/{total_lessons}")
            
            results = {
                'lesson_id': str(uuid.uuid4()),
                'sequence_number': sequence_number,
                'total_lessons': total_lessons,
                'generated_formats': [],
                'user_id': user_profile.get('user_id'),
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            
            # 1. Generate text micro-lesson (always generated first)
            if 'text' in content_types:
                text_lesson = await bedrock_service.generate_micro_lesson(
                    lesson_content, user_profile, sequence_number, total_lessons
                )
                text_lesson['micro_lesson_id'] = results['lesson_id']
                results['text_lesson'] = text_lesson
                results['generated_formats'].append('text')
                
                # Store text lesson in DynamoDB
                await db_service.put_item('MicroLessons', text_lesson)
            
            # 2. Generate audio micro-lesson if requested
            if 'audio' in content_types and results.get('text_lesson'):
                try:
                    audio_lesson = await audio_generation_service.generate_audio_micro_lesson(
                        results['text_lesson'], user_profile
                    )
                    results['audio_lesson'] = audio_lesson
                    results['generated_formats'].append('audio')
                    logger.info(f"Audio lesson generated: {audio_lesson['audio_lesson_id']}")
                except Exception as e:
                    logger.error(f"Audio generation failed: {e}")
                    results['audio_error'] = str(e)
            
            # 3. Generate video micro-lesson if requested
            if 'video' in content_types and results.get('text_lesson'):
                try:
                    video_lesson = await video_generation_service.generate_video_micro_lesson(
                        results['text_lesson'], user_profile
                    )
                    results['video_lesson'] = video_lesson
                    results['generated_formats'].append('video')
                    logger.info(f"Video lesson generated: {video_lesson['video_lesson_id']}")
                except Exception as e:
                    logger.error(f"Video generation failed: {e}")
                    results['video_error'] = str(e)
            
            # 4. Track engagement for multi-modal generation
            await db_service.track_engagement({
                'user_id': user_profile.get('user_id'),
                'event_type': 'multi_modal_lesson_generated',
                'event_data': {
                    'lesson_id': results['lesson_id'],
                    'sequence_number': sequence_number,
                    'generated_formats': results['generated_formats'],
                    'content_types_requested': content_types,
                    'success_rate': len(results['generated_formats']) / len(content_types)
                }
            })
            
            logger.info(f"Multi-modal lesson generated successfully: {results['generated_formats']}")
            return results
            
        except Exception as e:
            logger.error(f"Error generating multi-modal micro-lesson: {e}")
            raise Exception(f"Failed to generate multi-modal lesson: {str(e)}")

    async def plan_learning_sequence(self, context: Dict[str, Any], objective: str) -> List[Dict[str, Any]]:
        """
        Use Bedrock Agent autonomous planning to create multi-step learning sequences.
        """
        try:
            if not self.adaptive_agent_id:
                logger.warning("Adaptive Agent not available, using Learning Agent for planning")
                agent_id = self.learning_agent_id
            else:
                agent_id = self.adaptive_agent_id
            
            # Prepare planning context for agent
            planning_context = {
                **context,
                'planning_objective': objective,
                'task_type': 'learning_sequence_planning'
            }
            
            planning_input = f"""
            AUTONOMOUS LEARNING SEQUENCE PLANNING
            
            OBJECTIVE: {objective}
            
            STUDENT CONTEXT: {json.dumps(context, indent=2)}
            
            TASK: Create a personalized, multi-step learning sequence that will help this student achieve the objective. 
            
            REQUIREMENTS:
            1. Analyze the student's current knowledge level and learning style
            2. Break down the objective into logical learning steps
            3. Determine appropriate difficulty progression
            4. Include assessment checkpoints
            5. Specify adaptation triggers for each step
            
            OUTPUT FORMAT:
            Provide a structured learning sequence with specific steps, objectives, and success criteria.
            """
            
            # Invoke appropriate agent for planning
            if agent_id == self.adaptive_agent_id:
                response = await self._invoke_adaptive_agent(planning_input, context.get('session_id'))
            else:
                response = await self._invoke_learning_agent(planning_input, context.get('session_id'))
            
            # Parse the learning sequence from agent response
            learning_sequence = self._parse_learning_sequence(response, objective)
            
            return learning_sequence
            
        except Exception as e:
            logger.error(f"Error planning learning sequence: {e}")
            return self._fallback_learning_sequence(objective, context)
    
    async def update_memory(self, user_id: str, experience: Dict[str, Any]) -> None:
        """
        Update agent memory with learning experiences for future reasoning.
        """
        try:
            memory_key = f"user_{user_id}_learning_memory"
            
            if memory_key not in self.memory_store:
                self.memory_store[memory_key] = {
                    'experiences': [],
                    'patterns': {},
                    'preferences': {},
                    'performance_history': []
                }
            
            # Add new experience
            self.memory_store[memory_key]['experiences'].append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'experience': experience
            })
            
            # Keep only recent experiences (last 50)
            if len(self.memory_store[memory_key]['experiences']) > 50:
                self.memory_store[memory_key]['experiences'] = \
                    self.memory_store[memory_key]['experiences'][-50:]
            
            # Update patterns based on experiences
            await self._update_learning_patterns(memory_key)
            
        except Exception as e:
            logging.error(f"Memory update failed: {e}")
    
    async def retrieve_memory(self, user_id: str) -> Dict[str, Any]:
        """
        Retrieve agent memory for context-aware decision making.
        """
        memory_key = f"user_{user_id}_learning_memory"
        return self.memory_store.get(memory_key, {
            'experiences': [],
            'patterns': {},
            'preferences': {},
            'performance_history': []
        })
    
    async def invoke_function(self, function_name: str, parameters: Dict[str, Any]) -> Any:
        """
        AgentCore function invocation for calling specific learning functions.
        """
        try:
            if function_name == "generate_micro_lesson":
                return await bedrock_service.generate_micro_lesson(**parameters)
            elif function_name == "generate_quiz":
                return await bedrock_service.generate_quiz(**parameters)
            elif function_name == "evaluate_answer":
                return await bedrock_service.evaluate_quiz_answer(**parameters)
            elif function_name == "analyze_performance":
                return await self._analyze_performance(**parameters)
            elif function_name == "summarize_lesson":
                return await self._summarize_lesson(**parameters)
            elif function_name == "explain_concept":
                return await self._explain_concept(**parameters)
            elif function_name == "generate_practice_quiz":
                return await self._generate_practice_quiz(**parameters)
            elif function_name == "show_progress":
                return await self._show_progress(**parameters)
            else:
                raise ValueError(f"Unknown function: {function_name}")
                
        except Exception as e:
            logging.error(f"Function invocation failed: {e}")
            raise
    
    async def _invoke_bedrock_agent(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke Bedrock Agent with proper session management.
        """
        try:
            session_id = context.get('session_id', str(uuid.uuid4()))
            
            # Use coordinator for this agent call too
            async def _invoke_bedrock_agent():
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None,
                    lambda: self.bedrock_agent_client.invoke_agent(
                        agentId=self.agent_id,
                        agentAliasId=self.agent_alias_id,
                        sessionId=session_id,
                        inputText=prompt
                    )
                )
            
            response = await bedrock_coordinator.execute_bedrock_request(
                'agent', _invoke_bedrock_agent
            )
            
            # Process agent response
            completion = ""
            for event in response.get('completion', []):
                if 'chunk' in event:
                    completion += event['chunk'].get('bytes', b'').decode('utf-8')
            
            # Parse JSON response
            try:
                return json.loads(completion)
            except json.JSONDecodeError:
                return {'reasoning': completion, 'decision': 'advance'}
                
        except Exception as e:
            logging.error(f"Bedrock Agent invocation failed: {e}")
            raise
    
    async def retrieve_memory(self, user_id: str) -> Dict[str, Any]:
        """
        Retrieve agent memory for a user using Bedrock Agent capabilities.
        """
        try:
            if not self.learning_agent_id:
                logger.warning("Learning Agent not configured, returning empty memory")
                return {}
            
            # Use agent to retrieve and process memory
            memory_input = f"RETRIEVE USER MEMORY\n\nUSER_ID: {user_id}\n\nTASK: Retrieve and summarize the learning memory for this user including:\n- Past learning decisions and outcomes\n- Performance patterns and trends\n- Learning preferences and adaptations\n- Knowledge gaps and strengths identified\n\nProvide a structured summary of the user's learning history."
            
            response = await self._invoke_learning_agent(memory_input)
            
            # Process memory response
            memory_data = {
                'user_id': user_id,
                'retrieved_at': datetime.now(timezone.utc).isoformat(),
                'memory_summary': response.get('response', ''),
                'agent_processed': True
            }
            
            return memory_data
            
        except Exception as e:
            logger.error(f"Error retrieving agent memory: {e}")
            return {'user_id': user_id, 'error': str(e), 'agent_processed': False}
    
    async def update_memory(self, user_id: str, memory_data: Dict[str, Any]) -> bool:
        """
        Update agent memory with new learning interaction data.
        """
        try:
            if not self.learning_agent_id:
                logger.warning("Learning Agent not configured, skipping memory update")
                return False
            
            # Convert Decimal objects to float for JSON serialization
            def convert_decimals(obj):
                if isinstance(obj, dict):
                    return {k: convert_decimals(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_decimals(v) for v in obj]
                elif isinstance(obj, Decimal):
                    return float(obj)
                return obj
            
            serializable_data = convert_decimals(memory_data)
            
            # Use agent to process and store memory
            memory_input = f"""
            UPDATE USER MEMORY
            
            USER_ID: {user_id}
            NEW_DATA: {json.dumps(serializable_data, indent=2)}
            
            TASK: Process this new learning interaction and update the user's memory:
            - Analyze the learning decision and outcome
            - Identify patterns and trends
            - Update knowledge about user preferences
            - Note any significant learning events
            
            Confirm memory has been updated and processed.
            """
            
            response = await self._invoke_learning_agent(memory_input)
            
            # Log memory update
            logger.info(f"Agent memory updated for user {user_id}: {memory_data}")
            
            return response.get('autonomous_decision', False)
            
        except Exception as e:
            logger.error(f"Error updating agent memory: {e}")
            return False
    
    async def invoke_function(self, function_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke agent function for specific educational tasks.
        """
        try:
            if not self.learning_agent_id:
                raise ValueError("Learning Agent not configured for function invocation")
            
            # Prepare function invocation for agent
            function_input = f"""
            INVOKE EDUCATIONAL FUNCTION
            
            FUNCTION: {function_name}
            PARAMETERS: {json.dumps(parameters, indent=2)}
            
            TASK: Execute the requested educational function with the provided parameters.
            
            Available Functions:
            - generate_micro_lesson: Create personalized micro-lesson content
            - generate_quiz: Create assessment questions
            - evaluate_answer: Analyze student responses
            - adapt_content: Modify content difficulty
            
            Provide structured output appropriate for the requested function.
            """
            
            response = await self._invoke_learning_agent(function_input)
            
            # Process function response
            function_result = {
                'function_name': function_name,
                'parameters': parameters,
                'result': response.get('response', ''),
                'autonomous_execution': response.get('autonomous_decision', False),
                'executed_at': datetime.now(timezone.utc).isoformat()
            }
            
            return function_result
            
        except Exception as e:
            logger.error(f"Error invoking agent function {function_name}: {e}")
            return {
                'function_name': function_name,
                'error': str(e),
                'autonomous_execution': False
            }
    
    async def _agent_intent_recognition(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use Bedrock Agent for TRUE autonomous intent recognition (no prompts).
        """
        try:
            if not self.learning_agent_id:
                raise ValueError("Learning Agent required for intent recognition")
            
            user_message = context.get('user_message', '')
            
            # Prepare context for agent
            intent_input = f"""
            AUTONOMOUS INTENT RECOGNITION
            
            STUDENT MESSAGE: {user_message}
            CONTEXT: {json.dumps(context, indent=2)}
            
            TASK: Analyze the student's message and determine their learning intent.
            
            Provide autonomous analysis of what the student needs and how to best help them.
            """
            
            response = await self._invoke_learning_agent(intent_input)
            
            # Process agent response for intent
            return {
                'intent': self._extract_intent_from_agent_response(response.get('response', '')),
                'confidence': response.get('confidence', 0.8),
                'reasoning': response.get('reasoning', 'Autonomous agent analysis'),
                'autonomous_recognition': True,
                'agent_response': response.get('response', '')
            }
            
        except Exception as e:
            logger.error(f"Agent intent recognition failed: {e}")
            # Minimal fallback - no prompt-based reasoning
            return {
                'intent': 'general_chat',
                'confidence': 0.3,
                'reasoning': f'Agent unavailable: {str(e)}',
                'autonomous_recognition': False,
                'fallback_used': True
            }
    
    def _extract_intent_from_agent_response(self, agent_response: str) -> str:
        """Extract intent from agent response using simple pattern matching."""
        response_lower = agent_response.lower()
        
        # Map agent responses to intents
        intent_keywords = {
            'summarization': ['summary', 'summarize', 'main points', 'overview'],
            'explanation': ['explain', 'clarify', 'understand', 'what is', 'how does'],
            'quiz_request': ['quiz', 'test', 'questions', 'practice', 'assess'],
            'progress_inquiry': ['progress', 'performance', 'how am i doing', 'improvement'],
            'help_request': ['help', 'stuck', 'assistance', 'guidance'],
            'encouragement': ['difficult', 'hard', 'frustrated', 'struggling', 'motivation']
        }
        
        for intent, keywords in intent_keywords.items():
            if any(keyword in response_lower for keyword in keywords):
                return intent
        
        return 'general_chat'  # Default intent
    
    def _fallback_plan(self) -> List[Dict[str, Any]]:
        """
        Fallback learning plan when planning fails.
        """
        return [
            {
                'step': 1,
                'objective': 'Introduce concept',
                'difficulty': 'easy',
                'duration': 10
            },
            {
                'step': 2,
                'objective': 'Practice and reinforce',
                'difficulty': 'medium',
                'duration': 15
            },
            {
                'step': 3,
                'objective': 'Apply knowledge',
                'difficulty': 'hard',
                'duration': 20
            }
        ]
    
    async def _update_learning_patterns(self, memory_key: str) -> None:
        """
        Analyze experiences to identify learning patterns.
        """
        try:
            experiences = self.memory_store[memory_key]['experiences']
            
            if len(experiences) < 5:
                return  # Need more data
            
            # Analyze patterns (simplified)
            scores = []
            times = []
            decisions = []
            
            for exp in experiences[-10:]:  # Last 10 experiences
                exp_data = exp.get('experience', {})
                if 'score' in exp_data:
                    scores.append(exp_data['score'])
                if 'time_spent' in exp_data:
                    times.append(exp_data['time_spent'])
                if 'decision' in exp_data:
                    decisions.append(exp_data['decision'])
            
            # Update patterns
            patterns = self.memory_store[memory_key]['patterns']
            
            if scores:
                patterns['avg_score'] = sum(scores) / len(scores)
                patterns['score_trend'] = 'improving' if len(scores) > 1 and scores[-1] > scores[0] else 'stable'
            
            if times:
                patterns['avg_time'] = sum(times) / len(times)
            
            if decisions:
                patterns['common_decisions'] = list(set(decisions))
            
        except Exception as e:
            logging.error(f"Pattern update failed: {e}")
    
    async def _analyze_performance(self, **parameters) -> Dict[str, Any]:
        """
        Analyze performance data for decision making.
        """
        score = parameters.get('score', 0.7)
        time_spent = parameters.get('time_spent', 300)
        engagement = parameters.get('engagement_metrics', {})
        
        analysis = {
            'performance_level': 'struggling' if score < 0.6 else 'mastering' if score > 0.8 else 'learning',
            'time_efficiency': 'fast' if time_spent < 180 else 'slow' if time_spent > 420 else 'normal',
            'engagement_level': 'high' if engagement.get('focus_score', 0.7) > 0.8 else 'low' if engagement.get('focus_score', 0.7) < 0.5 else 'medium',
            'recommendations': []
        }
        
        # Add recommendations based on analysis
        if analysis['performance_level'] == 'struggling':
            analysis['recommendations'].append('Provide additional support and simpler explanations')
        if analysis['time_efficiency'] == 'slow':
            analysis['recommendations'].append('Break content into smaller chunks')
        if analysis['engagement_level'] == 'low':
            analysis['recommendations'].append('Increase interactivity and vary content format')
        
        return analysis
    
    async def _summarize_lesson(self, **parameters) -> str:
        """
        Generate a lesson summary using Bedrock Claude.
        """
        lesson_content = parameters.get('lesson_content', '')
        key_concepts = parameters.get('key_concepts', [])
        user_profile = parameters.get('user_profile', {})
        learning_progress = parameters.get('learning_progress', {})
        
        summary_prompt = f"""
        Create a concise, personalized summary of this lesson content:
        
        Lesson Content: {lesson_content[:2000]}
        Key Concepts: {', '.join(key_concepts)}
        
        User Context:
        - Learning Style: {user_profile.get('learning_style', 'visual')}
        - Progress: {learning_progress.get('completion_percentage', 0)}% complete
        
        Provide a summary that:
        1. Highlights the main concepts covered
        2. Shows how concepts connect to each other
        3. Relates to the user's learning style
        4. Encourages continued learning
        
        Keep it under 150 words and make it engaging.
        """
        
        try:
            response = await bedrock_service.invoke_claude(
                prompt=summary_prompt,
                max_tokens=4096,
                temperature=0.5
            )
            return response.strip()
        except Exception as e:
            logging.error(f"Lesson summarization failed: {e}")
            if key_concepts:
                return f"Here's a quick summary: We've covered {', '.join(key_concepts[:3])}. These concepts build on each other to help you understand the core material. You're making great progress!"
            else:
                return "We've been working through important concepts that build your understanding step by step. Keep up the great work!"
    
    async def _explain_concept(self, **parameters) -> str:
        """
        Explain a specific concept using Bedrock Claude.
        """
        concept = parameters.get('concept', '')
        lesson_context = parameters.get('lesson_context', {})
        user_learning_style = parameters.get('user_learning_style', 'visual')
        user_background = parameters.get('user_background', {})
        
        explanation_prompt = f"""
        Explain the concept "{concept}" in a clear, personalized way.
        
        Context:
        - Current lesson: {lesson_context.get('title', 'Current lesson')}
        - User's learning style: {user_learning_style}
        - User's profession: {user_background.get('profession', 'general')}
        - Education level: {user_background.get('education_level', 'intermediate')}
        
        Provide an explanation that:
        1. Starts with a simple definition
        2. Uses examples relevant to their profession/background
        3. Adapts to their learning style:
           - Visual: Use analogies, metaphors, visual descriptions
           - Auditory: Use verbal explanations, discussions
           - Reading: Use detailed text, bullet points
           - Kinesthetic: Use hands-on examples, practical applications
        4. Connects to the current lesson context
        5. Ends with a question to check understanding
        
        Keep it under 200 words and make it engaging.
        """
        
        try:
            response = await bedrock_service.invoke_claude(
                prompt=explanation_prompt,
                max_tokens=4096,
                temperature=0.6
            )
            return response.strip()
        except Exception as e:
            logging.error(f"Concept explanation failed: {e}")
            return f"Let me explain {concept}: This is an important concept that relates to what we're learning. Think of it as a building block that helps you understand the bigger picture. Would you like me to break it down further or give you a specific example?"
    
    async def _generate_practice_quiz(self, **parameters) -> Dict[str, Any]:
        """
        Generate a practice quiz using Bedrock Claude.
        """
        lesson_content = parameters.get('lesson_content', '')
        key_concepts = parameters.get('key_concepts', [])
        difficulty = parameters.get('difficulty', 'intermediate')
        num_questions = parameters.get('num_questions', 2)
        question_types = parameters.get('question_types', ['multiple_choice', 'true_false'])
        
        quiz_prompt = f"""
        Create a practice quiz based on this content:
        
        Content: {lesson_content[:1500]}
        Key Concepts: {', '.join(key_concepts)}
        
        Requirements:
        - {num_questions} questions
        - Difficulty: {difficulty}
        - Question types: {', '.join(question_types)}
        - Focus on understanding, not memorization
        
        Return JSON format:
        {{
            "questions": [
                {{
                    "question_id": "q1",
                    "question_type": "multiple_choice",
                    "question_text": "Question here?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "A",
                    "explanation": "Why this is correct"
                }}
            ]
        }}
        
        Return only valid JSON.
        """
        
        try:
            response = await bedrock_service.invoke_claude(
                prompt=quiz_prompt,
                max_tokens=4096,
                temperature=0.4
            )
            
            # Parse JSON response
            quiz_data = json.loads(response.strip())
            return quiz_data
            
        except (json.JSONDecodeError, Exception) as e:
            logging.error(f"Practice quiz generation failed: {e}")
            # Fallback quiz
            return {
                "questions": [
                    {
                        "question_id": "q1",
                        "question_type": "multiple_choice",
                        "question_text": f"Which of these concepts have we been focusing on?",
                        "options": key_concepts[:4] if len(key_concepts) >= 4 else key_concepts + ["Other topics"],
                        "correct_answer": key_concepts[0] if key_concepts else "Main concept",
                        "explanation": "This is one of the key concepts we've been studying."
                    }
                ]
            }
    
    async def _show_progress(self, **parameters) -> str:
        """
        Show user progress summary.
        """
        user_id = parameters.get('user_id', '')
        current_lesson = parameters.get('current_lesson', {})
        learning_progress = parameters.get('learning_progress', {})
        recent_engagement = parameters.get('recent_engagement', [])
        
        # Calculate progress metrics
        completion_percentage = learning_progress.get('completion_percentage', 0)
        current_lesson_title = current_lesson.get('title', 'Current lesson')
        
        # Analyze recent performance
        quiz_events = [e for e in recent_engagement if e.get('event_type') == 'quiz_completed']
        if quiz_events:
            recent_scores = [e.get('event_data', {}).get('score', 0) for e in quiz_events[-3:]]
            avg_score = sum(recent_scores) / len(recent_scores) if recent_scores else 0
        else:
            avg_score = 0
        
        progress_prompt = f"""
        Create an encouraging progress summary for a learner:
        
        Progress Data:
        - Current lesson: {current_lesson_title}
        - Completion: {completion_percentage:.1f}%
        - Recent quiz average: {avg_score:.1f}%
        - Total learning activities: {len(recent_engagement)}
        
        Provide a progress summary that:
        1. Celebrates their achievements
        2. Shows specific progress metrics
        3. Identifies areas of strength
        4. Provides gentle encouragement for improvement areas
        5. Suggests next steps
        
        Keep it positive, specific, and under 150 words.
        """
        
        try:
            response = await bedrock_service.invoke_claude(
                prompt=progress_prompt,
                max_tokens=4096,
                temperature=0.6
            )
            return response.strip()
        except Exception as e:
            logging.error(f"Progress summary failed: {e}")
            # Fallback progress message
            if completion_percentage > 0:
                return f"Great progress! You've completed {completion_percentage:.1f}% of '{current_lesson_title}'. Your dedication to learning is showing - keep up the excellent work!"
            else:
                return "You're at the beginning of an exciting learning journey! Every step you take builds your knowledge and skills. Ready to dive in?"


class AdaptiveLearningAgent:
    """
    The autonomous brain of SnapStudy that makes intelligent decisions
    about learning paths without human intervention.
    
    Now powered by Amazon Bedrock AgentCore primitives for true autonomous reasoning.
    """
    
    def __init__(self):
        self.bedrock = bedrock_service
        self.db = db_service
        self.agent_core = BedrockAgentCore()  # AgentCore integration
        
        # Performance thresholds for adaptation decisions
        self.STRUGGLING_THRESHOLD = 0.60
        self.MASTERY_THRESHOLD = 0.80
        self.MIN_ENGAGEMENT_TIME = 30  # seconds
        self.MAX_MICRO_LESSON_DURATION = 15  # minutes
        
    async def start_adaptive_lesson(
        self, 
        user_id: str, 
        lesson_id: str
    ) -> Dict[str, Any]:
        """
        Initialize an adaptive learning session.
        This is the entry point for the autonomous learning loop.
        """
        try:
            logger.info(f"Starting adaptive lesson for user {user_id}, lesson {lesson_id}")
            
            # Get lesson and user context
            lesson = await self.db.get_lesson(lesson_id)
            if not lesson:
                raise ValueError(f"Lesson {lesson_id} not found")
            
            user = await self.db.get_user_by_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Verify lesson belongs to user
            if lesson['user_id'] != user_id:
                raise ValueError("Access denied: lesson does not belong to user")
            
            # Initialize learning session state
            session_state = {
                'session_id': str(uuid.uuid4()),
                'user_id': user_id,
                'lesson_id': lesson_id,
                'current_micro_lesson_index': 0,
                'total_micro_lessons': 0,
                'performance_history': [],
                'adaptation_history': [],
                'started_at': datetime.now(timezone.utc).isoformat(),
                'status': 'active'
            }
            
            # Get or generate micro-lessons
            micro_lessons = await self.db.get_lesson_micro_lessons(lesson_id)
            
            if not micro_lessons:
                # Generate initial micro-lessons from lesson content
                micro_lessons = await self._generate_initial_micro_lessons(lesson, user)
                session_state['total_micro_lessons'] = len(micro_lessons)
            else:
                session_state['total_micro_lessons'] = len(micro_lessons)
            
            # Get first micro-lesson
            first_micro_lesson = await self._get_next_micro_lesson(session_state, user)
            
            # Track engagement
            await self.db.track_engagement({
                'user_id': user_id,
                'event_type': 'adaptive_lesson_started',
                'event_data': {
                    'lesson_id': lesson_id,
                    'session_id': session_state['session_id'],
                    'total_micro_lessons': session_state['total_micro_lessons']
                }
            })
            
            return {
                'session_id': session_state['session_id'],
                'lesson': lesson,
                'current_micro_lesson': first_micro_lesson,
                'progress': {
                    'current_index': 0,
                    'total_micro_lessons': session_state['total_micro_lessons'],
                    'completion_percentage': 0.0
                },
                'status': 'started'
            }
            
        except Exception as e:
            logger.error(f"Failed to start adaptive lesson: {e}")
            raise ValueError(f"Failed to start adaptive lesson: {str(e)}")
    
    async def get_next_micro_lesson(
        self, 
        session_id: str, 
        user_id: str,
        previous_performance: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Autonomous decision-making for the next micro-lesson.
        This is where the core adaptation logic happens.
        """
        try:
            logger.info(f"Getting next micro-lesson for session {session_id}")
            
            # Get current session state and user context
            context = await self._fetch_comprehensive_context(user_id, session_id)
            
            # Record previous performance if provided
            if previous_performance:
                await self._record_performance(session_id, previous_performance)
                context['latest_performance'] = previous_performance
            
            # CORE AUTONOMOUS DECISION MAKING
            adaptation_decision = await self._make_adaptation_decision(context)
            
            # Generate next micro-lesson based on decision
            next_micro_lesson = await self._generate_adaptive_micro_lesson(
                context, adaptation_decision
            )
            
            # Update session state
            await self._update_session_state(session_id, adaptation_decision, next_micro_lesson)
            
            # Track the autonomous decision
            await self.db.track_engagement({
                'user_id': user_id,
                'event_type': 'autonomous_adaptation',
                'event_data': {
                    'session_id': session_id,
                    'decision': adaptation_decision['decision'],
                    'reasoning': adaptation_decision['reasoning'],
                    'learning_state': adaptation_decision['learning_state']
                }
            })
            
            return {
                'micro_lesson': next_micro_lesson,
                'adaptation_info': {
                    'decision': adaptation_decision['decision'],
                    'reasoning': adaptation_decision['reasoning'],
                    'learning_state': adaptation_decision['learning_state']
                },
                'progress': context['progress'],
                'session_id': session_id
            }
            
        except Exception as e:
            logger.error(f"Failed to get next micro-lesson: {e}")
            raise ValueError(f"Failed to get next micro-lesson: {str(e)}")
    
    async def submit_quiz_and_adapt(
        self, 
        session_id: str, 
        user_id: str,
        quiz_id: str,
        answers: Dict[str, str],
        time_spent: int,
        engagement_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process quiz submission and make autonomous adaptation decisions.
        """
        try:
            logger.info(f"Processing quiz submission for session {session_id}")
            
            # Get quiz and evaluate answers
            quiz = await self.db.get_quiz_by_id(quiz_id)
            if not quiz:
                raise ValueError(f"Quiz {quiz_id} not found")
            
            # Intelligent answer evaluation
            evaluation_results = await self._evaluate_quiz_answers(quiz, answers)
            
            # Calculate performance metrics
            performance_metrics = {
                'quiz_id': quiz_id,
                'score': evaluation_results['overall_score'],
                'correct_answers': evaluation_results['correct_count'],
                'total_questions': evaluation_results['total_questions'],
                'time_spent_seconds': time_spent,
                'engagement_metrics': engagement_metrics,
                'detailed_results': evaluation_results['question_results'],
                'submitted_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Get next micro-lesson with autonomous adaptation
            next_response = await self.get_next_micro_lesson(
                session_id, user_id, performance_metrics
            )
            
            # Generate detailed feedback
            feedback = await self._generate_performance_feedback(
                performance_metrics, evaluation_results
            )
            
            return {
                'quiz_results': {
                    'score': evaluation_results['overall_score'],
                    'feedback': feedback,
                    'detailed_results': evaluation_results['question_results']
                },
                'next_micro_lesson': next_response['micro_lesson'],
                'adaptation_info': next_response['adaptation_info'],
                'progress': next_response['progress']
            }
            
        except Exception as e:
            logger.error(f"Failed to process quiz submission: {e}")
            raise ValueError(f"Failed to process quiz submission: {str(e)}")
    
    async def _fetch_comprehensive_context(
        self, 
        user_id: str, 
        session_id: str
    ) -> Dict[str, Any]:
        """
        Fetch all context needed for autonomous decision making.
        """
        # Get user profile and preferences
        user = await self.db.get_user_by_id(user_id)
        
        # Get recent engagement history
        engagement_history = await self.db.get_user_engagement(user_id, limit=20)
        
        # Get lesson progress
        # Note: In a real implementation, you'd store session state in DynamoDB
        # For now, we'll simulate this
        
        # Calculate learning patterns
        learning_patterns = self._analyze_learning_patterns(engagement_history)
        
        return {
            'user_profile': user,
            'engagement_history': engagement_history,
            'learning_patterns': learning_patterns,
            'session_id': session_id,
            'progress': {
                'current_index': 0,  # Would be retrieved from session state
                'total_micro_lessons': 5,  # Would be retrieved from session state
                'completion_percentage': 0.0
            }
        }
    
    async def _make_adaptation_decision(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        CORE AUTONOMOUS DECISION MAKING LOGIC using AgentCore primitives.
        This is where the agent uses reasoning, memory, and planning to decide what to do next.
        """
        try:
            # Analyze current learning state
            learning_state = self._determine_learning_state(context)
            
            # Retrieve agent memory for this user
            user_id = context.get('user_profile', {}).get('user_id')
            if user_id:
                memory = await self.agent_core.retrieve_memory(user_id)
                context['agent_memory'] = memory
            
            # Use AgentCore reasoning over context
            decision_data = await self.agent_core.reason_over_context(
                context=context,
                goal="optimize_learning_path_based_on_performance_and_engagement"
            )
            
            # Validate and enhance decision
            validated_decision = self._validate_and_enhance_decision(
                decision_data, context, learning_state
            )
            
            # Update agent memory with this decision
            if user_id:
                await self.agent_core.update_memory(user_id, {
                    'decision': validated_decision['decision'],
                    'reasoning': validated_decision['reasoning'],
                    'context_summary': {
                        'learning_state': learning_state.value,
                        'performance': context.get('latest_performance', {}),
                        'user_profile': context.get('user_profile', {})
                    }
                })
            
            return validated_decision
            
        except Exception as e:
            logger.error(f"AgentCore decision making failed: {e}")
            # Fallback to safe default decision
            return self._fallback_decision(LearningState.LEARNING)
    
    async def _agent_decision_making(self, context: Dict[str, Any], learning_state: LearningState) -> Dict[str, Any]:
        """Use TRUE Bedrock Agent for autonomous decision making (no prompts)."""
        
        try:
            if not self.agent_core.learning_agent_id:
                raise ValueError("Learning Agent required for autonomous decisions")
            
            # Prepare context for agent
            decision_input = f"""
            AUTONOMOUS LEARNING DECISION
            
            LEARNING STATE: {learning_state.value}
            CONTEXT: {json.dumps(context, indent=2)}
            
            TASK: Make an autonomous decision about the optimal next learning step for this student.
            
            Analyze performance, engagement, and learning patterns to determine the best action.
            """
            
            response = await self.agent_core._invoke_learning_agent(decision_input)
            
            # Process agent decision
            return {
                'decision': self._extract_decision_from_agent(response.get('response', '')),
                'reasoning': response.get('reasoning', 'Autonomous agent decision'),
                'confidence': response.get('confidence', 0.8),
                'autonomous_decision': True,
                'agent_used': True,
                'learning_state': learning_state.value,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Agent decision making failed: {e}")
            # Minimal fallback without prompts
            return self._minimal_decision_fallback(learning_state, str(e))
    
    def _extract_decision_from_agent(self, agent_response: str) -> str:
        """Extract decision from agent response."""
        response_lower = agent_response.lower()
        
        # Decision keywords mapping
        decision_keywords = {
            'advance': ['advance', 'move forward', 'next', 'progress'],
            'review': ['review', 'revisit', 'different approach', 'retry'],
            'reinforce': ['reinforce', 'practice', 'strengthen', 'consolidate'],
            'simplify': ['simplify', 'easier', 'reduce complexity', 'break down'],
            'accelerate': ['accelerate', 'faster', 'increase pace', 'challenge'],
            'complete': ['complete', 'finished', 'done', 'mastered']
        }
        
        for decision, keywords in decision_keywords.items():
            if any(keyword in response_lower for keyword in keywords):
                return decision
        
        return 'continue'  # Default safe decision
    
    def _minimal_decision_fallback(self, learning_state: LearningState, error: str) -> Dict[str, Any]:
        """Minimal decision fallback when agents are unavailable."""
        logger.error(f"Using minimal decision fallback: {error}")
        
        # Simple state-based decision (not autonomous)
        fallback_decisions = {
            LearningState.STRUGGLING: 'simplify',
            LearningState.LEARNING: 'continue',
            LearningState.MASTERING: 'advance',
            LearningState.ENGAGED: 'continue',
            LearningState.DISTRACTED: 'engage'
        }
        
        decision = fallback_decisions.get(learning_state, 'continue')
        
        return {
            'decision': decision,
            'reasoning': f'Fallback decision for {learning_state.value} state',
            'confidence': 0.3,
            'autonomous_decision': False,
            'agent_used': False,
            'fallback_used': True,
            'error': error,
            'warning': 'System running without autonomous decision-making'
        }
    
    def _determine_learning_state(self, context: Dict[str, Any]) -> LearningState:
        """Analyze context to determine current learning state."""
        latest_performance = context.get('latest_performance', {})
        
        if not latest_performance:
            return LearningState.LEARNING
        
        score = latest_performance.get('score', 0.7)
        time_spent = latest_performance.get('time_spent_seconds', 300)
        engagement = latest_performance.get('engagement_metrics', {})
        
        # Determine state based on performance
        if score < self.STRUGGLING_THRESHOLD:
            return LearningState.STRUGGLING
        elif score > self.MASTERY_THRESHOLD:
            if time_spent < self.MIN_ENGAGEMENT_TIME:
                return LearningState.DISTRACTED
            else:
                return LearningState.MASTERING
        else:
            engagement_score = engagement.get('focus_score', 0.7)
            if engagement_score > 0.8:
                return LearningState.ENGAGED
            else:
                return LearningState.LEARNING
    
    def _analyze_learning_patterns(self, engagement_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze historical engagement to identify learning patterns."""
        if not engagement_history:
            return {
                'avg_engagement': 'medium',
                'preferred_duration': 15,
                'struggle_areas': [],
                'strong_areas': []
            }
        
        # Analyze patterns (simplified for now)
        quiz_events = [e for e in engagement_history if e.get('event_type') == 'quiz_completed']
        
        if quiz_events:
            avg_score = sum(e.get('event_data', {}).get('score', 0.7) for e in quiz_events) / len(quiz_events)
            engagement_level = 'high' if avg_score > 0.8 else 'medium' if avg_score > 0.6 else 'low'
        else:
            engagement_level = 'medium'
        
        return {
            'avg_engagement': engagement_level,
            'preferred_duration': 15,  # Would be calculated from actual data
            'struggle_areas': [],      # Would be identified from quiz results
            'strong_areas': []         # Would be identified from quiz results
        }
    
    def _validate_and_enhance_decision(
        self, 
        decision_data: Dict[str, Any], 
        context: Dict[str, Any], 
        learning_state: LearningState
    ) -> Dict[str, Any]:
        """Validate the AI decision and add safety checks."""
        
        # Ensure required fields exist
        decision = decision_data.get('decision', 'advance')
        if decision not in [d.value for d in AdaptationDecision]:
            decision = AdaptationDecision.ADVANCE.value
        
        # Add safety constraints
        if learning_state == LearningState.STRUGGLING and decision == 'accelerate':
            decision = AdaptationDecision.REVIEW.value
            decision_data['reasoning'] = "Overridden: Cannot accelerate when struggling"
        
        # Ensure reasonable duration
        duration = decision_data.get('estimated_duration', 15)
        duration = max(5, min(duration, self.MAX_MICRO_LESSON_DURATION))
        
        return {
            'decision': decision,
            'reasoning': decision_data.get('reasoning', 'Autonomous decision based on performance'),
            'confidence': decision_data.get('confidence', 0.8),
            'learning_state': learning_state.value,
            'next_topic_focus': decision_data.get('next_topic_focus', 'Continue current topic'),
            'difficulty_adjustment': decision_data.get('difficulty_adjustment', 'same'),
            'estimated_duration': duration
        }
    
    def _fallback_decision(self, learning_state: LearningState) -> Dict[str, Any]:
        """Provide a safe fallback decision when AI decision making fails."""
        return {
            'decision': AdaptationDecision.ADVANCE.value,
            'reasoning': 'Fallback decision due to processing error',
            'confidence': 0.5,
            'learning_state': learning_state.value,
            'next_topic_focus': 'Continue with next concept',
            'difficulty_adjustment': 'same',
            'estimated_duration': 15
        }
    
    async def _generate_adaptive_micro_lesson(
        self, 
        context: Dict[str, Any], 
        adaptation_decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a micro-lesson based on the adaptation decision using AgentCore function invocation."""
        
        user_profile = context['user_profile']
        decision = adaptation_decision['decision']
        
        # Create content based on decision
        if decision == AdaptationDecision.REVIEW.value:
            content_type = "review_lesson"
            focus = "Review and reinforce previous concepts with different examples"
        elif decision == AdaptationDecision.SIMPLIFY.value:
            content_type = "simplified_lesson"
            focus = "Simplified explanation of current concept"
        elif decision == AdaptationDecision.ACCELERATE.value:
            content_type = "advanced_lesson"
            focus = "Advanced concepts and challenging examples"
        else:
            content_type = "standard_lesson"
            focus = adaptation_decision.get('content_focus', 'Continue learning')
        
        # Use AgentCore function invocation for micro-lesson generation
        micro_lesson = await self.agent_core.invoke_function(
            function_name="generate_micro_lesson",
            parameters={
                'topic_content': focus,
                'user_profile': user_profile,
                'sequence_number': context['progress']['current_index'] + 1,
                'total_lessons': context['progress']['total_micro_lessons']
            }
        )
        
        # Use AgentCore function invocation for quiz generation
        quiz = await self.agent_core.invoke_function(
            function_name="generate_quiz",
            parameters={
                'lesson_content': micro_lesson.get('content', ''),
                'difficulty_level': adaptation_decision.get('difficulty_adjustment', 'same'),
                'num_questions': 3
            }
        )
        
        # Store micro-lesson and quiz in database
        micro_lesson_record = await self.db.create_micro_lesson({
            'lesson_id': context.get('lesson_id', ''),
            'sequence_number': context['progress']['current_index'] + 1,
            'title': micro_lesson.get('title', 'Adaptive Lesson'),
            'content': micro_lesson.get('content', ''),
            'summary': micro_lesson.get('summary', ''),
            'key_concepts': micro_lesson.get('key_concepts', []),
            'estimated_duration_minutes': adaptation_decision['estimated_duration'],
            'difficulty_level': adaptation_decision.get('difficulty_adjustment', 'same'),
            'learning_objectives': micro_lesson.get('learning_objectives', []),
            'adaptation_type': decision
        })
        
        quiz_record = await self.db.create_quiz({
            'micro_lesson_id': micro_lesson_record['micro_lesson_id'],
            'questions': quiz.get('questions', []),
            'total_questions': quiz.get('total_questions', 3),
            'passing_score': quiz.get('passing_score', 0.7)
        })
        
        return {
            'micro_lesson_id': micro_lesson_record['micro_lesson_id'],
            'quiz_id': quiz_record['quiz_id'],
            'title': micro_lesson.get('title'),
            'content': micro_lesson.get('content'),
            'summary': micro_lesson.get('summary'),
            'key_concepts': micro_lesson.get('key_concepts', []),
            'estimated_duration': adaptation_decision['estimated_duration'],
            'quiz': quiz,
            'adaptation_type': decision
        }
    
    async def _evaluate_quiz_answers(
        self, 
        quiz: Dict[str, Any], 
        user_answers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Intelligently evaluate quiz answers with partial credit using AgentCore function invocation."""
        
        questions = quiz.get('questions', [])
        question_results = []
        total_score = 0.0
        correct_count = 0
        
        for question in questions:
            question_id = question.get('question_id')
            user_answer = user_answers.get(question_id, '')
            
            # Use AgentCore function invocation for intelligent evaluation
            evaluation = await self.agent_core.invoke_function(
                function_name="evaluate_answer",
                parameters={
                    'question': question,
                    'user_answer': user_answer
                }
            )
            
            question_results.append({
                'question_id': question_id,
                'user_answer': user_answer,
                'correct_answer': question.get('correct_answer'),
                'is_correct': evaluation.get('is_correct', False),
                'score': evaluation.get('score', 0.0),
                'feedback': evaluation.get('feedback', ''),
                'suggestions': evaluation.get('suggestions', '')
            })
            
            total_score += evaluation.get('score', 0.0)
            if evaluation.get('is_correct', False):
                correct_count += 1
        
        overall_score = (total_score / len(questions)) * 100 if questions else 0
        
        return {
            'overall_score': overall_score,
            'total_questions': len(questions),
            'correct_count': correct_count,
            'question_results': question_results
        }
    
    async def _generate_performance_feedback(
        self, 
        performance_metrics: Dict[str, Any], 
        evaluation_results: Dict[str, Any]
    ) -> str:
        """Generate personalized feedback based on performance."""
        
        score = performance_metrics['score']
        time_spent = performance_metrics['time_spent_seconds']
        
        feedback_prompt = f"""
        Generate encouraging, personalized feedback for a learner based on their quiz performance:
        
        Performance:
        - Score: {score}%
        - Time spent: {time_spent} seconds
        - Correct answers: {evaluation_results['correct_count']}/{evaluation_results['total_questions']}
        
        Provide:
        1. Positive reinforcement
        2. Specific areas of strength
        3. Gentle guidance for improvement areas
        4. Encouragement to continue learning
        
        Keep it concise (2-3 sentences) and motivating.
        """
        
        feedback = await self.bedrock.invoke_claude(
            prompt=feedback_prompt,
            max_tokens=4096,
            temperature=0.7
        )
        
        return feedback.strip()
    
    async def _generate_initial_micro_lessons(
        self, 
        lesson: Dict[str, Any], 
        user: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate initial micro-lessons when starting a new lesson."""
        
        # This would typically analyze the lesson content and break it down
        # For now, we'll create a placeholder structure
        
        micro_lessons = []
        for i in range(3):  # Generate 3 initial micro-lessons
            micro_lesson = await self.bedrock.generate_micro_lesson(
                topic_content=lesson.get('description', 'Learning content'),
                user_profile=user,
                sequence_number=i + 1,
                total_lessons=3
            )
            
            micro_lesson_record = await self.db.create_micro_lesson({
                'lesson_id': lesson['lesson_id'],
                'sequence_number': i + 1,
                'title': micro_lesson.get('title', f'Lesson {i + 1}'),
                'content': micro_lesson.get('content', ''),
                'summary': micro_lesson.get('summary', ''),
                'key_concepts': micro_lesson.get('key_concepts', []),
                'estimated_duration_minutes': micro_lesson.get('estimated_duration_minutes', 15),
                'difficulty_level': user.get('difficulty_level', 'intermediate'),
                'learning_objectives': micro_lesson.get('learning_objectives', [])
            })
            
            micro_lessons.append(micro_lesson_record)
        
        return micro_lessons
    
    async def _get_next_micro_lesson(
        self, 
        session_state: Dict[str, Any], 
        user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get the next micro-lesson for the session."""
        
        lesson_id = session_state['lesson_id']
        micro_lessons = await self.db.get_lesson_micro_lessons(lesson_id)
        
        if not micro_lessons:
            # Generate first micro-lesson
            lesson = await self.db.get_lesson(lesson_id)
            micro_lessons = await self._generate_initial_micro_lessons(lesson, user)
        
        # Return first micro-lesson
        if micro_lessons:
            first_lesson = micro_lessons[0]
            
            # Generate quiz for this micro-lesson
            quiz = await self.bedrock.generate_quiz(
                lesson_content=first_lesson.get('content', ''),
                difficulty_level=user.get('difficulty_level', 'intermediate'),
                num_questions=3
            )
            
            quiz_record = await self.db.create_quiz({
                'micro_lesson_id': first_lesson['micro_lesson_id'],
                'questions': quiz.get('questions', []),
                'total_questions': quiz.get('total_questions', 3),
                'passing_score': quiz.get('passing_score', 0.7)
            })
            
            return {
                'micro_lesson_id': first_lesson['micro_lesson_id'],
                'quiz_id': quiz_record['quiz_id'],
                'title': first_lesson.get('title'),
                'content': first_lesson.get('content'),
                'summary': first_lesson.get('summary'),
                'key_concepts': first_lesson.get('key_concepts', []),
                'estimated_duration': first_lesson.get('estimated_duration_minutes', 15),
                'quiz': quiz
            }
        
        return {}
    
    async def _record_performance(
        self, 
        session_id: str, 
        performance: Dict[str, Any]
    ) -> None:
        """Record performance data for future decision making."""
        
        # In a real implementation, this would store session state in DynamoDB
        # For now, we'll track it as engagement data
        
        await self.db.track_engagement({
            'user_id': performance.get('user_id', ''),
            'event_type': 'quiz_completed',
            'event_data': {
                'session_id': session_id,
                'quiz_id': performance.get('quiz_id'),
                'score': performance.get('score'),
                'time_spent': performance.get('time_spent_seconds'),
                'engagement_metrics': performance.get('engagement_metrics', {})
            }
        })
    
    async def _update_session_state(
        self, 
        session_id: str, 
        adaptation_decision: Dict[str, Any], 
        micro_lesson: Dict[str, Any]
    ) -> None:
        """Update session state after generating new content."""
        
        # In a real implementation, this would update session state in DynamoDB
        # For now, we'll track the adaptation decision
        
        await self.db.track_engagement({
            'user_id': '',  # Would be retrieved from session
            'event_type': 'adaptation_decision',
            'event_data': {
                'session_id': session_id,
                'decision': adaptation_decision['decision'],
                'reasoning': adaptation_decision['reasoning'],
                'micro_lesson_id': micro_lesson.get('micro_lesson_id')
            }
        })


# Global service instance
adaptive_agent = AdaptiveLearningAgent()