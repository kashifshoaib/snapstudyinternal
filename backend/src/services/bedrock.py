"""AWS Bedrock service for AI/ML operations using Amazon Nova Micro."""

import boto3
import json
import time
import random
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError
import logging
import asyncio

from ..config import settings
from ..utils.token_counter import token_counter
from ..utils.rate_limiter import bedrock_rate_limiter
from ..utils.bedrock_coordinator import bedrock_coordinator

logger = logging.getLogger(__name__)


class BedrockService:
    """Service for AWS Bedrock operations with Amazon Nova Micro."""
    
    def __init__(self):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=settings.aws_region)
        self.model_id = settings.bedrock_model_id
        
        # Enhanced retry configuration for throttling
        self.max_retries = 6  # Increased for throttling scenarios
        self.base_delay = 2.0  # Longer initial delay
        self.max_delay = 120.0  # Longer max delay for severe throttling
        self.backoff_multiplier = 2.5  # More aggressive backoff
        self.jitter_range = 0.2  # More jitter to spread requests
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter."""
        # Exponential backoff: base_delay * (backoff_multiplier ^ attempt)
        delay = self.base_delay * (self.backoff_multiplier ** attempt)
        
        # Cap at max_delay
        delay = min(delay, self.max_delay)
        
        # Add jitter to prevent thundering herd
        jitter = delay * self.jitter_range * (2 * random.random() - 1)
        delay += jitter
        
        # Ensure delay is positive
        return max(0.1, delay)
    
    def _is_retryable_error(self, error: ClientError) -> bool:
        """Check if the error is retryable."""
        error_code = error.response['Error']['Code']
        retryable_codes = [
            'ThrottlingException',
            'TooManyRequestsException', 
            'ServiceUnavailableException',
            'InternalServerError',
            'InternalFailure',
            'ServiceQuotaExceededException',
            'ModelTimeoutException',
            'ModelNotReadyException'
        ]
        return error_code in retryable_codes
    
    async def _retry_with_backoff(self, operation, *args, **kwargs):
        """Execute operation with exponential backoff retry logic."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return operation(*args, **kwargs)
                
            except ClientError as e:
                last_exception = e
                error_code = e.response['Error']['Code']
                
                if not self._is_retryable_error(e):
                    # Non-retryable error, raise immediately
                    logger.error(f"Non-retryable Bedrock error: {error_code}")
                    raise
                
                if attempt == self.max_retries:
                    # Last attempt, raise the error
                    logger.error(f"Bedrock operation failed after {self.max_retries} retries: {error_code}")
                    raise
                
                # Calculate delay and wait
                delay = self._calculate_delay(attempt)
                logger.warning(f"Bedrock {error_code} on attempt {attempt + 1}/{self.max_retries + 1}, retrying in {delay:.2f}s")
                
                await asyncio.sleep(delay)
                
            except Exception as e:
                # Non-ClientError exceptions are not retryable
                logger.error(f"Non-retryable Bedrock error: {e}")
                raise
        
        # This should never be reached, but just in case
        raise last_exception
    
    def configure_retry_settings(
        self, 
        max_retries: int = None,
        base_delay: float = None,
        max_delay: float = None,
        backoff_multiplier: float = None
    ):
        """Configure retry settings for Bedrock operations."""
        if max_retries is not None:
            self.max_retries = max_retries
        if base_delay is not None:
            self.base_delay = base_delay
        if max_delay is not None:
            self.max_delay = max_delay
        if backoff_multiplier is not None:
            self.backoff_multiplier = backoff_multiplier
            
        logger.info(f"Bedrock retry settings updated: max_retries={self.max_retries}, "
                   f"base_delay={self.base_delay}s, max_delay={self.max_delay}s, "
                   f"backoff_multiplier={self.backoff_multiplier}")
    
    def get_retry_stats(self) -> Dict[str, Any]:
        """Get current retry configuration."""
        return {
            'max_retries': self.max_retries,
            'base_delay': self.base_delay,
            'max_delay': self.max_delay,
            'backoff_multiplier': self.backoff_multiplier,
            'jitter_range': self.jitter_range
        }
    
    async def invoke_claude(
        self, 
        prompt: str, 
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """Invoke Nova Micro model with a prompt and retry logic."""
        
        # Log input token usage
        full_input = f"{system_prompt or ''}\n\n{prompt}"
        input_stats = token_counter.estimate_tokens_detailed(full_input)
        logger.info(
            f"🧠 Claude Input: {input_stats['estimated_tokens']} tokens "
            f"({input_stats['characters']} chars, {input_stats['words']} words) "
            f"| Max Output: {max_tokens} tokens"
        )
        
        def _invoke_model():
            """Internal function to invoke the model (for retry logic)."""
            # Prepare the conversation for Nova using invoke_model format
            conversation = []
            
            # Add system message if provided
            if system_prompt:
                logger.info(f"📋 Adding system prompt: {system_prompt[:100]}...")
                conversation.append({
                    "role": "system",
                    "content": [{"text": system_prompt}]
                })
            
            # Add user message
            logger.info(f"💬 Adding user prompt: {prompt[:100]}...")
            conversation.append({
                "role": "user",
                "content": [{"text": prompt}]
            })
            
            # Use invoke_model with Nova's native format (compatible with older boto3)
            body = {
                "messages": conversation
            }
            
            # Log the request being sent
            logger.info(f"📤 Nova Request Body: {json.dumps(body, indent=2)}")
            logger.info(f"🎯 Nova Model ID: {self.model_id}")
            
            try:
                logger.info("🚀 Sending request to Nova...")
                start_time = time.time()
                
                response = self.bedrock_client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(body),
                    contentType='application/json'
                )
                
                end_time = time.time()
                logger.info(f"⏱️ Nova request completed in {end_time - start_time:.2f}s")
                
            except Exception as e:
                logger.error(f"❌ Nova request failed: {type(e).__name__}: {str(e)}")
                raise
            
            response_body = json.loads(response['body'].read())
            
            # Log the full response for debugging
            logger.info(f"🔍 Nova Response Body: {json.dumps(response_body, indent=2)}")
            
            # Extract response text from Nova invoke_model format
            if 'output' in response_body and 'message' in response_body['output']:
                output_text = response_body['output']['message']['content'][0]['text']
                
                # Log the extracted text
                logger.info(f"✅ Nova Output Text: {output_text[:200]}...")
                
                # Log Nova usage information if available
                if 'usage' in response_body:
                    usage = response_body['usage']
                    logger.info(f"📊 Nova Usage: {json.dumps(usage, indent=2)}")
                
                # Log stop reason
                if 'stopReason' in response_body:
                    logger.info(f"🛑 Nova Stop Reason: {response_body['stopReason']}")
                
                # Log complete token usage
                token_counter.log_token_usage(
                    operation="bedrock_nova_invoke",
                    input_text=full_input,
                    output_text=output_text,
                    model_id=self.model_id
                )
                
                return output_text
            else:
                logger.error(f"❌ Unexpected Nova response format: {json.dumps(response_body, indent=2)}")
                raise ValueError("Invalid response format from Nova")
        
        try:
            # Use coordinator to space out the request, then apply retry logic
            async def _coordinated_invoke():
                return await self._retry_with_backoff(_invoke_model)
            
            # Add timeout to prevent hanging requests
            logger.info("⏳ Starting Nova request with 30s timeout...")
            result = await asyncio.wait_for(
                bedrock_coordinator.execute_bedrock_request('model', _coordinated_invoke),
                timeout=30.0
            )
            logger.info("✅ Nova request completed successfully")
            return result
            
        except asyncio.TimeoutError:
            logger.error("⏰ Nova request timed out after 30 seconds")
            raise RuntimeError("Nova request timed out")
        except ClientError as e:
            logger.error(f"❌ Bedrock API error after retries: {e}")
            raise ValueError(f"Bedrock API error: {e.response['Error']['Message']}")
        except Exception as e:
            logger.error(f"❌ Error invoking Nova after retries: {e}")
            import traceback
            logger.error(f"📋 Full traceback: {traceback.format_exc()}")
            raise ValueError(f"Error invoking Nova: {str(e)}")
    
    async def analyze_content(self, content: str, content_type: str) -> Dict[str, Any]:
        """Analyze content and extract learning structure."""
        system_prompt = """You are an expert educational content analyzer. Your task is to analyze content and extract key learning information."""
        
        prompt = f"""
        Analyze the following {content_type} content and provide a structured analysis:

        Content:
        {content[:8000]}  # Limit content to avoid token limits

        Please provide a JSON response with the following structure:
        {{
            "title": "Suggested title for the content",
            "summary": "Brief summary of the content",
            "learning_objectives": ["objective1", "objective2", "objective3"],
            "key_concepts": ["concept1", "concept2", "concept3"],
            "difficulty_level": "beginner|intermediate|advanced",
            "estimated_duration_minutes": 30,
            "prerequisites": ["prerequisite1", "prerequisite2"],
            "topics": [
                {{
                    "title": "Topic 1",
                    "content": "Detailed explanation",
                    "key_points": ["point1", "point2"]
                }}
            ]
        }}
        
        Ensure the response is valid JSON only, no additional text.
        """
        
        try:
            response = await self.invoke_claude(prompt, max_tokens=4096, temperature=0.3, system_prompt=system_prompt)
            
            # Parse JSON response
            analysis = json.loads(response.strip())
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Raw response: {response}")
            raise ValueError("Failed to parse content analysis response")
    
    async def generate_micro_lesson(
        self, 
        topic_content: str, 
        user_profile: Dict[str, Any],
        sequence_number: int,
        total_lessons: int
    ) -> Dict[str, Any]:
        """Generate a personalized micro-lesson."""
        system_prompt = """You are an expert educational content creator specializing in personalized micro-learning. Create engaging, bite-sized lessons tailored to individual learners."""
        
        learning_style = user_profile.get('learning_style', 'visual')
        attention_span = user_profile.get('attention_span', 15)
        difficulty_level = user_profile.get('difficulty_level', 'intermediate')
        profession = user_profile.get('profession', 'general')
        
        prompt = f"""
        Create a personalized micro-lesson based on the following:

        Topic Content: {topic_content}
        
        User Profile:
        - Learning Style: {learning_style}
        - Attention Span: {attention_span} minutes
        - Difficulty Level: {difficulty_level}
        - Profession: {profession}
        
        Lesson Context:
        - This is lesson {sequence_number} of {total_lessons}
        - Target duration: {min(attention_span, 15)} minutes
        
        Create a JSON response with this structure:
        {{
            "title": "Engaging lesson title",
            "content": "Detailed lesson content in markdown format, adapted for {learning_style} learners",
            "summary": "Brief summary of key takeaways",
            "key_concepts": ["concept1", "concept2"],
            "estimated_duration_minutes": {min(attention_span, 15)},
            "learning_objectives": ["objective1", "objective2"],
            "examples": [
                {{
                    "title": "Example relevant to {profession}",
                    "description": "Practical example"
                }}
            ],
            "visual_aids": ["suggestion1", "suggestion2"] // for visual learners
        }}
        
        Adapt the content style based on learning preference:
        - Visual: Include diagrams, charts, visual metaphors
        - Auditory: Include discussion points, verbal explanations
        - Reading: Include detailed text, bullet points
        - Kinesthetic: Include hands-on activities, practical exercises
        
        Return only valid JSON.
        """
        
        try:
            response = await self.invoke_claude(prompt, max_tokens=4096, temperature=0.7, system_prompt=system_prompt)
            micro_lesson = json.loads(response.strip())
            return micro_lesson
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse micro-lesson JSON: {e}")
            raise ValueError("Failed to generate micro-lesson")
    
    async def generate_quiz(
        self, 
        lesson_content: str, 
        difficulty_level: str = "intermediate",
        num_questions: int = 3
    ) -> Dict[str, Any]:
        """Generate a quiz for a micro-lesson."""
        system_prompt = """You are an expert quiz creator. Generate engaging, educational quizzes that test understanding and reinforce learning."""
        
        prompt = f"""
        Create a quiz based on this lesson content:

        {lesson_content}

        Requirements:
        - Difficulty: {difficulty_level}
        - Number of questions: {num_questions}
        - Mix of question types: multiple choice, true/false, short answer
        - Include detailed explanations for each answer

        Return JSON in this format:
        {{
            "questions": [
                {{
                    "question_id": "q1",
                    "question_type": "multiple_choice",
                    "question_text": "Question text here?",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct_answer": "Option A",
                    "explanation": "Detailed explanation of why this is correct",
                    "difficulty": "{difficulty_level}",
                    "points": 1
                }},
                {{
                    "question_id": "q2", 
                    "question_type": "true_false",
                    "question_text": "Statement to evaluate",
                    "correct_answer": "true",
                    "explanation": "Explanation",
                    "difficulty": "{difficulty_level}",
                    "points": 1
                }},
                {{
                    "question_id": "q3",
                    "question_type": "short_answer", 
                    "question_text": "Open-ended question?",
                    "correct_answer": "Sample correct answer",
                    "explanation": "What makes a good answer",
                    "difficulty": "{difficulty_level}",
                    "points": 2
                }}
            ],
            "total_questions": {num_questions},
            "total_points": 4,
            "passing_score": 0.7
        }}
        
        Return only valid JSON.
        """
        
        try:
            response = await self.invoke_claude(prompt, max_tokens=4096, temperature=0.5, system_prompt=system_prompt)
            quiz = json.loads(response.strip())
            return quiz
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse quiz JSON: {e}")
            raise ValueError("Failed to generate quiz")
    
    async def evaluate_quiz_answer(
        self, 
        question: Dict[str, Any], 
        user_answer: str
    ) -> Dict[str, Any]:
        """Intelligently evaluate a quiz answer with partial credit."""
        system_prompt = """You are an expert educator who evaluates student answers fairly and provides constructive feedback."""
        
        prompt = f"""
        Evaluate this quiz answer:

        Question: {question['question_text']}
        Question Type: {question['question_type']}
        Correct Answer: {question['correct_answer']}
        User Answer: {user_answer}
        
        For multiple choice and true/false: exact match required
        For short answer: evaluate based on key concepts and understanding
        
        Return JSON:
        {{
            "is_correct": true/false,
            "score": 0.0-1.0,  // partial credit for short answers
            "feedback": "Constructive feedback explaining the evaluation",
            "key_points_covered": ["point1", "point2"],
            "suggestions": "How to improve the answer"
        }}
        
        Return only valid JSON.
        """
        
        try:
            response = await self.invoke_claude(prompt, max_tokens=4096, temperature=0.3, system_prompt=system_prompt)
            evaluation = json.loads(response.strip())
            return evaluation
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse evaluation JSON: {e}")
            raise ValueError("Failed to evaluate answer")
    
    async def generate_chat_response(
        self, 
        user_message: str, 
        lesson_context: str,
        chat_history: List[Dict[str, str]] = None
    ) -> str:
        """Generate contextual chat response for tutoring."""
        system_prompt = """You are an AI tutor helping students learn. Be helpful, encouraging, and educational. Keep responses concise but informative."""
        
        history_text = ""
        if chat_history:
            history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history[-5:]])
        
        prompt = f"""
        Current lesson context: {lesson_context[:1000]}
        
        Recent conversation:
        {history_text}
        
        Student message: {user_message}
        
        Provide a helpful response as an AI tutor. If the student asks for:
        - /summarize: Provide a summary of the current lesson
        - /explain [topic]: Explain the topic in simple terms
        - /quiz: Suggest they take the quiz for this lesson
        - /help: List available commands
        
        Keep responses under 200 words and be encouraging.
        """
        
        try:
            response = await self.invoke_claude(prompt, max_tokens=4096, temperature=0.7, system_prompt=system_prompt)
            return response.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate chat response: {e}")
            return "I'm sorry, I'm having trouble responding right now. Please try again."


# Global service instance
bedrock_service = BedrockService()