"""AWS Bedrock service for AI/ML operations using Amazon Nova Lite."""

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
from ..utils.aws_client import get_boto3_client

logger = logging.getLogger(__name__)


class BedrockService:
    """Service for AWS Bedrock operations with Amazon Nova Lite."""
    
    def __init__(self):
        self.bedrock_client = get_boto3_client('bedrock-runtime')
        self.model_id = settings.bedrock_model_id
        
        # Retry configuration optimized for Nova Lite
        self.max_retries = 3  # Nova Lite is generally more reliable
        self.base_delay = 0.5  # Start with 0.5 second delay
        self.max_delay = 30.0  # Max 30s delay
        self.backoff_multiplier = 2.0  # Standard exponential backoff
        self.jitter_range = 0.2  # Less jitter needed
    
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

    def _extract_json_from_response(self, response: str) -> str:
        """
        Extract JSON from a response that may be wrapped in markdown code fences.

        Handles responses like:
        ```json
        { ... }
        ```

        or just:
        { ... }
        """
        response = response.strip()

        # Check for markdown code fences
        if response.startswith('```'):
            # Find the first newline after the opening fence
            first_newline = response.find('\n')
            if first_newline != -1:
                # Find the closing fence
                closing_fence = response.rfind('```')
                if closing_fence > first_newline:
                    # Extract content between fences
                    response = response[first_newline + 1:closing_fence].strip()

        return response
    
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
        """Invoke Amazon Nova Lite model with a prompt and retry logic."""
        
        # Log input token usage
        full_input = f"{system_prompt or ''}\n\n{prompt}"
        input_stats = token_counter.estimate_tokens_detailed(full_input)
        logger.info(
            f"🧠 Nova Lite Input: {input_stats['estimated_tokens']} tokens "
            f"({input_stats['characters']} chars, {input_stats['words']} words) "
            f"| Max Output: {max_tokens} tokens"
        )
        
        def _invoke_model():
            """Internal function to invoke the model (for retry logic)."""
            # Prepare the request body for Nova Lite (official AWS format)
            
            # Define system prompt in Nova Lite format
            system_list = []
            if system_prompt:
                system_list = [{"text": system_prompt}]
            
            # Define messages in Nova Lite format
            message_list = [
                {
                    "role": "user", 
                    "content": [{"text": prompt}]
                }
            ]
            
            # Configure inference parameters
            inf_params = {
                "maxTokens": max_tokens,
                "temperature": temperature,
                "topP": 0.9
            }
            
            # Build request body according to AWS docs
            body = {
                "schemaVersion": "messages-v1",
                "messages": message_list,
                "inferenceConfig": inf_params
            }
            
            # Add system prompt if provided
            if system_list:
                body["system"] = system_list
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType='application/json'
            )
            
            response_body = json.loads(response['body'].read())

            # Parse Nova Lite response format
            if 'output' in response_body and 'message' in response_body['output']:
                message = response_body['output']['message']
                if 'content' in message and message['content']:
                    output_text = message['content'][0]['text']

                    # Log complete token usage
                    token_counter.log_token_usage(
                        operation="bedrock_nova_invoke",
                        input_text=full_input,
                        output_text=output_text,
                        model_id=self.model_id
                    )

                    return output_text

            # Log detailed error information
            logger.error(f"Unexpected Bedrock response format. Full response: {json.dumps(response_body, indent=2)}")
            logger.error(f"Model ID used: {self.model_id}")
            logger.error(f"AWS Region: {settings.aws_region}")
            if settings.aws_profile:
                logger.error(f"AWS Profile: {settings.aws_profile}")
            raise ValueError("Invalid response format from Nova Lite")
        
        try:
            # Use coordinator to space out the request, then apply retry logic
            async def _coordinated_invoke():
                return await self._retry_with_backoff(_invoke_model)

            return await bedrock_coordinator.execute_bedrock_request(
                'model', _coordinated_invoke
            )

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))

            # Provide helpful error messages for common issues
            if error_code in ['UnrecognizedClientException', 'InvalidSignatureException', 'SignatureDoesNotMatch']:
                logger.error(f"AWS Credentials Error: {error_message}")
                if settings.aws_profile:
                    logger.error(f"Check that AWS profile '{settings.aws_profile}' is properly configured in ~/.aws/credentials")
                raise ValueError(f"AWS credentials error - check your AWS_PROFILE setting: {error_message}")
            elif error_code == 'AccessDeniedException':
                logger.error(f"AWS Permissions Error: {error_message}")
                logger.error(f"The AWS credentials do not have permission to invoke Bedrock model: {self.model_id}")
                raise ValueError(f"Access denied - check IAM permissions for Bedrock: {error_message}")
            elif error_code == 'ResourceNotFoundException':
                logger.error(f"Bedrock Model Not Found: {self.model_id} in region {settings.aws_region}")
                raise ValueError(f"Model {self.model_id} not found in region {settings.aws_region}")
            else:
                logger.error(f"Bedrock API error [{error_code}]: {error_message}")
                raise ValueError(f"Bedrock API error: {error_message}")
        except Exception as e:
            logger.error(f"Error invoking Nova Lite after retries: {e}")
            raise ValueError(f"Error invoking Nova Lite: {str(e)}")
    
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

            # Strip markdown code fences if present
            cleaned_response = self._extract_json_from_response(response)

            # Parse JSON response
            analysis = json.loads(cleaned_response)
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

            # Log the raw response for debugging
            logger.debug(f"Raw Bedrock response (first 500 chars): {response[:500] if response else 'EMPTY RESPONSE'}")

            if not response or not response.strip():
                logger.error("Bedrock returned an empty response")
                raise ValueError("Failed to generate micro-lesson: Empty response from Bedrock")

            # Strip markdown code fences if present
            cleaned_response = self._extract_json_from_response(response)

            micro_lesson = json.loads(cleaned_response)
            return micro_lesson

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse micro-lesson JSON: {e}")
            logger.error(f"Response content that failed to parse: {response[:1000] if response else 'EMPTY'}")
            raise ValueError("Failed to generate micro-lesson: Invalid JSON response")
    
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

            # Strip markdown code fences if present
            cleaned_response = self._extract_json_from_response(response)

            quiz = json.loads(cleaned_response)
            return quiz

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse quiz JSON: {e}")
            logger.error(f"Response content that failed to parse: {response[:1000] if response else 'EMPTY'}")
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

            # Strip markdown code fences if present
            cleaned_response = self._extract_json_from_response(response)

            evaluation = json.loads(cleaned_response)
            return evaluation

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse evaluation JSON: {e}")
            logger.error(f"Response content that failed to parse: {response[:1000] if response else 'EMPTY'}")
            raise ValueError("Failed to evaluate answer")
    
    async def check_query_relevance(
        self,
        user_message: str,
        lesson_context: str
    ) -> Dict[str, Any]:
        """
        Check if user query is related to the current micro-lesson context.

        Returns:
            Dict with 'is_relevant' (bool), 'confidence' (float), and 'reason' (str)
        """
        system_prompt = """You are a content relevance analyzer. Determine if a user's query is related to the given lesson context."""

        prompt = f"""
        Analyze whether the user's query is related to the current lesson context.

        Current Lesson Context:
        {lesson_context[:800]}

        User Query: {user_message}

        Determine if the query is:
        1. DIRECTLY related to the lesson content (asking about topics, concepts, or examples from this lesson)
        2. TANGENTIALLY related (general questions about the subject area)
        3. UNRELATED (completely off-topic, personal questions, or about different subjects)

        Return ONLY valid JSON:
        {{
            "is_relevant": true/false,
            "confidence": 0.0-1.0,
            "reason": "Brief explanation",
            "category": "DIRECTLY_RELATED" | "TANGENTIALLY_RELATED" | "UNRELATED"
        }}
        """

        try:
            response = await self.invoke_claude(prompt, max_tokens=512, temperature=0.3, system_prompt=system_prompt)
            cleaned_response = self._extract_json_from_response(response)
            relevance_check = json.loads(cleaned_response)

            logger.info(f"Relevance check: {relevance_check}")
            return relevance_check

        except Exception as e:
            logger.error(f"Failed to check query relevance: {e}")
            # Default to allowing the query if check fails
            return {
                "is_relevant": True,
                "confidence": 0.5,
                "reason": "Unable to verify relevance",
                "category": "TANGENTIALLY_RELATED"
            }

    async def generate_chat_response(
        self,
        user_message: str,
        lesson_context: str,
        chat_history: List[Dict[str, str]] = None,
        check_relevance: bool = True
    ) -> Dict[str, Any]:
        """
        Generate contextual chat response for tutoring with optional relevance guardrail.

        Returns:
            Dict with 'response' (str), 'is_relevant' (bool), and 'relevance_info' (dict)
        """
        # Check if query is related to the lesson
        relevance_info = None
        if check_relevance and lesson_context:
            relevance_info = await self.check_query_relevance(user_message, lesson_context)

            # If query is unrelated, politely decline
            if not relevance_info.get('is_relevant', True):
                polite_decline = (
                    "I appreciate your question, but I'm here to help you with the current lesson. "
                    f"Your question seems to be about something different from what we're studying right now. "
                    f"\n\nLet's focus on the lesson at hand. Feel free to ask me questions about:\n"
                    f"- The key concepts in this lesson\n"
                    f"- Examples or explanations of the topics covered\n"
                    f"- Practice questions or summaries\n\n"
                    f"How can I help you understand this lesson better?"
                )

                return {
                    'response': polite_decline,
                    'is_relevant': False,
                    'relevance_info': relevance_info
                }

        system_prompt = """You are an AI tutor helping students learn. Be helpful, encouraging, and educational. Keep responses concise but informative. Focus on the current lesson context."""

        history_text = ""
        if chat_history:
            history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history[-5:]])

        prompt = f"""
        Current lesson context: {lesson_context[:1000]}

        Recent conversation:
        {history_text}

        Student message: {user_message}

        Provide a helpful response as an AI tutor focused on THIS LESSON. If the student asks for:
        - Summary: Provide a summary of the current lesson
        - Explanation: Explain concepts from this lesson in simple terms
        - Quiz: Suggest they take the quiz for this lesson
        - Examples: Provide examples related to this lesson

        Keep responses under 200 words, be encouraging, and stay focused on the lesson content.
        """

        try:
            response_text = await self.invoke_claude(prompt, max_tokens=4096, temperature=0.7, system_prompt=system_prompt)

            return {
                'response': response_text.strip(),
                'is_relevant': True,
                'relevance_info': relevance_info
            }

        except Exception as e:
            logger.error(f"Failed to generate chat response: {e}")
            return {
                'response': "I'm sorry, I'm having trouble responding right now. Please try again.",
                'is_relevant': True,
                'relevance_info': None
            }


# Global service instance
bedrock_service = BedrockService()