"""
Intelligent Quiz Generation and Evaluation Engine.

This service creates adaptive quizzes with mixed question types and provides
intelligent evaluation with partial credit and detailed feedback.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import uuid

from .bedrock import bedrock_service
from .dynamodb import db_service
from ..config import settings

logger = logging.getLogger(__name__)


class QuestionType(str, Enum):
    """Supported question types for adaptive quizzes."""
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    FILL_IN_BLANK = "fill_in_blank"
    MATCHING = "matching"


class DifficultyLevel(str, Enum):
    """Quiz difficulty levels."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    ADAPTIVE = "adaptive"  # Adjusts based on performance


class QuizEngine:
    """
    Intelligent quiz generation and evaluation engine.
    Creates adaptive assessments and provides detailed feedback.
    """
    
    def __init__(self):
        self.bedrock = bedrock_service
        self.db = db_service
        
        # Quiz generation parameters
        self.DEFAULT_QUESTIONS_PER_QUIZ = 5
        self.MAX_QUESTIONS_PER_QUIZ = 10
        self.MIN_QUESTIONS_PER_QUIZ = 3
        
        # Question type distribution for balanced quizzes
        self.QUESTION_TYPE_DISTRIBUTION = {
            DifficultyLevel.EASY: {
                QuestionType.MULTIPLE_CHOICE: 0.4,
                QuestionType.TRUE_FALSE: 0.4,
                QuestionType.SHORT_ANSWER: 0.2
            },
            DifficultyLevel.MEDIUM: {
                QuestionType.MULTIPLE_CHOICE: 0.3,
                QuestionType.TRUE_FALSE: 0.2,
                QuestionType.SHORT_ANSWER: 0.3,
                QuestionType.FILL_IN_BLANK: 0.2
            },
            DifficultyLevel.HARD: {
                QuestionType.MULTIPLE_CHOICE: 0.2,
                QuestionType.SHORT_ANSWER: 0.4,
                QuestionType.FILL_IN_BLANK: 0.2,
                QuestionType.MATCHING: 0.2
            }
        }
    
    async def generate_adaptive_quiz(
        self,
        lesson_content: str,
        user_profile: Dict[str, Any],
        performance_history: List[Dict[str, Any]] = None,
        target_difficulty: str = "adaptive",
        num_questions: int = None
    ) -> Dict[str, Any]:
        """
        Generate an adaptive quiz based on lesson content and user performance.
        """
        try:
            logger.info("Generating adaptive quiz")
            
            # Determine optimal quiz parameters
            quiz_params = await self._analyze_quiz_requirements(
                lesson_content, user_profile, performance_history, target_difficulty
            )
            
            # Generate questions with mixed types
            questions = await self._generate_mixed_questions(
                lesson_content=lesson_content,
                quiz_params=quiz_params,
                num_questions=num_questions or quiz_params['recommended_questions']
            )
            
            # Create quiz metadata
            quiz_metadata = {
                'quiz_id': str(uuid.uuid4()),
                'title': quiz_params['title'],
                'description': quiz_params['description'],
                'difficulty_level': quiz_params['difficulty'],
                'estimated_duration_minutes': quiz_params['estimated_duration'],
                'total_questions': len(questions),
                'total_points': sum(q.get('points', 1) for q in questions),
                'passing_score': quiz_params['passing_score'],
                'question_types': list(set(q['question_type'] for q in questions)),
                'adaptive_features': quiz_params['adaptive_features'],
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            return {
                'quiz_metadata': quiz_metadata,
                'questions': questions,
                'instructions': quiz_params['instructions'],
                'hints_available': quiz_params['hints_enabled']
            }
            
        except Exception as e:
            logger.error(f"Failed to generate adaptive quiz: {e}")
            raise ValueError(f"Quiz generation failed: {str(e)}")
    
    async def evaluate_quiz_submission(
        self,
        quiz_id: str,
        questions: List[Dict[str, Any]],
        user_answers: Dict[str, str],
        time_spent_seconds: int,
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Intelligently evaluate quiz submission with partial credit and detailed feedback.
        """
        try:
            logger.info(f"Evaluating quiz submission: {quiz_id}")
            
            # Evaluate each question individually
            question_evaluations = []
            total_score = 0.0
            total_possible_points = 0
            
            for question in questions:
                question_id = question.get('question_id')
                user_answer = user_answers.get(question_id, '')
                
                evaluation = await self._evaluate_individual_question(
                    question, user_answer, user_profile
                )
                
                question_evaluations.append(evaluation)
                total_score += evaluation['score']
                total_possible_points += question.get('points', 1)
            
            # Calculate overall performance metrics
            percentage_score = (total_score / total_possible_points * 100) if total_possible_points > 0 else 0
            
            # Generate comprehensive feedback
            overall_feedback = await self._generate_comprehensive_feedback(
                question_evaluations, percentage_score, time_spent_seconds, user_profile
            )
            
            # Analyze performance patterns
            performance_analysis = await self._analyze_performance_patterns(
                question_evaluations, user_profile
            )
            
            # Generate recommendations
            recommendations = await self._generate_learning_recommendations(
                performance_analysis, percentage_score
            )
            
            return {
                'quiz_id': quiz_id,
                'overall_score': percentage_score,
                'total_points_earned': total_score,
                'total_possible_points': total_possible_points,
                'time_spent_seconds': time_spent_seconds,
                'question_evaluations': question_evaluations,
                'overall_feedback': overall_feedback,
                'performance_analysis': performance_analysis,
                'recommendations': recommendations,
                'completion_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to evaluate quiz: {e}")
            raise ValueError(f"Quiz evaluation failed: {str(e)}")
    
    async def generate_contextual_hint(
        self,
        question: Dict[str, Any],
        user_context: Dict[str, Any],
        previous_attempts: List[str] = None
    ) -> Dict[str, Any]:
        """
        Generate contextual hints for quiz questions without giving away answers.
        """
        try:
            hint_prompt = f"""
            Generate a helpful hint for this quiz question without revealing the answer:
            
            Question: {question.get('question_text', '')}
            Question Type: {question.get('question_type', 'multiple_choice')}
            Difficulty: {question.get('difficulty', 'medium')}
            
            User Context:
            - Learning Style: {user_context.get('learning_style', 'visual')}
            - Difficulty Level: {user_context.get('difficulty_level', 'intermediate')}
            - Previous Attempts: {previous_attempts or 'None'}
            
            Create a hint that:
            1. Guides thinking without revealing the answer
            2. Matches the user's learning style
            3. Provides just enough guidance to help them reason through it
            4. Encourages critical thinking
            5. Is supportive and encouraging
            
            Return JSON:
            {{
                "hint_text": "The helpful hint text",
                "hint_type": "conceptual|procedural|example",
                "confidence": 0.85
            }}
            """
            
            response = await self.bedrock.invoke_claude(
                prompt=hint_prompt,
                max_tokens=4096,
                temperature=0.7
            )
            
            try:
                hint_data = json.loads(response.strip())
            except json.JSONDecodeError:
                hint_data = {
                    'hint_text': response.strip(),
                    'hint_type': 'general',
                    'confidence': 0.7
                }
            
            return {
                'question_id': question.get('question_id'),
                'hint': hint_data['hint_text'],
                'hint_type': hint_data.get('hint_type', 'general'),
                'confidence': hint_data.get('confidence', 0.7),
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate hint: {e}")
            return {
                'question_id': question.get('question_id'),
                'hint': "Think about the key concepts from the lesson and how they apply to this question.",
                'hint_type': 'general',
                'confidence': 0.5,
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
    
    async def _analyze_quiz_requirements(
        self,
        lesson_content: str,
        user_profile: Dict[str, Any],
        performance_history: List[Dict[str, Any]],
        target_difficulty: str
    ) -> Dict[str, Any]:
        """
        Analyze requirements for optimal quiz generation.
        """
        analysis_prompt = f"""
        Analyze the learning content and user profile to determine optimal quiz parameters:
        
        Lesson Content: {lesson_content[:2000]}...
        
        User Profile:
        - Learning Style: {user_profile.get('learning_style', 'visual')}
        - Attention Span: {user_profile.get('attention_span', 15)} minutes
        - Difficulty Level: {user_profile.get('difficulty_level', 'intermediate')}
        
        Performance History: {len(performance_history or [])} previous quizzes
        Target Difficulty: {target_difficulty}
        
        Determine:
        1. Optimal number of questions (3-10)
        2. Appropriate difficulty level
        3. Question type distribution
        4. Estimated completion time
        5. Passing score threshold
        
        Return JSON:
        {{
            "recommended_questions": 5,
            "difficulty": "medium",
            "estimated_duration": 10,
            "passing_score": 0.7,
            "title": "Lesson Assessment",
            "description": "Quiz description",
            "instructions": "Clear instructions for the quiz",
            "adaptive_features": ["difficulty_adjustment", "hint_system"],
            "hints_enabled": true
        }}
        """
        
        try:
            response = await self.bedrock.invoke_claude(
                prompt=analysis_prompt,
                max_tokens=4096,
                temperature=0.3
            )
            
            return json.loads(response.strip())
            
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Quiz analysis failed, using defaults: {e}")
            return {
                'recommended_questions': 5,
                'difficulty': 'medium',
                'estimated_duration': 10,
                'passing_score': 0.7,
                'title': 'Lesson Assessment',
                'description': 'Test your understanding of the lesson content',
                'instructions': 'Answer all questions to the best of your ability. You can request hints if needed.',
                'adaptive_features': ['hint_system'],
                'hints_enabled': True
            }
    
    async def _generate_mixed_questions(
        self,
        lesson_content: str,
        quiz_params: Dict[str, Any],
        num_questions: int
    ) -> List[Dict[str, Any]]:
        """
        Generate a mix of different question types for comprehensive assessment.
        """
        difficulty = quiz_params.get('difficulty', 'medium')
        
        # Determine question type distribution
        if difficulty in self.QUESTION_TYPE_DISTRIBUTION:
            type_distribution = self.QUESTION_TYPE_DISTRIBUTION[DifficultyLevel(difficulty)]
        else:
            type_distribution = self.QUESTION_TYPE_DISTRIBUTION[DifficultyLevel.MEDIUM]
        
        # Calculate number of each question type
        question_types = []
        for q_type, ratio in type_distribution.items():
            count = max(1, int(num_questions * ratio))
            question_types.extend([q_type] * count)
        
        # Adjust to exact number needed
        while len(question_types) > num_questions:
            question_types.pop()
        while len(question_types) < num_questions:
            question_types.append(QuestionType.MULTIPLE_CHOICE)
        
        # Generate questions for each type
        questions = []
        for i, q_type in enumerate(question_types):
            question = await self._generate_single_question(
                lesson_content, q_type, difficulty, i + 1
            )
            questions.append(question)
        
        return questions
    
    async def _generate_single_question(
        self,
        lesson_content: str,
        question_type: QuestionType,
        difficulty: str,
        question_number: int
    ) -> Dict[str, Any]:
        """
        Generate a single question of the specified type.
        """
        question_prompt = f"""
        Generate a {question_type.value} question based on this lesson content:
        
        Content: {lesson_content[:1500]}...
        
        Requirements:
        - Difficulty: {difficulty}
        - Question Number: {question_number}
        - Test understanding, not memorization
        - Include clear, unambiguous wording
        - Provide detailed explanation for the correct answer
        
        Format for {question_type.value}:
        """
        
        if question_type == QuestionType.MULTIPLE_CHOICE:
            question_prompt += """
            {
                "question_id": "q1",
                "question_type": "multiple_choice",
                "question_text": "Clear question text?",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": "Option A",
                "explanation": "Detailed explanation of why this is correct",
                "difficulty": "medium",
                "points": 1,
                "tags": ["concept1", "concept2"]
            }
            """
        elif question_type == QuestionType.TRUE_FALSE:
            question_prompt += """
            {
                "question_id": "q1",
                "question_type": "true_false",
                "question_text": "Statement to evaluate as true or false",
                "correct_answer": "true",
                "explanation": "Explanation of why this statement is true/false",
                "difficulty": "medium",
                "points": 1,
                "tags": ["concept1"]
            }
            """
        elif question_type == QuestionType.SHORT_ANSWER:
            question_prompt += """
            {
                "question_id": "q1",
                "question_type": "short_answer",
                "question_text": "Open-ended question requiring explanation?",
                "correct_answer": "Sample ideal answer",
                "key_points": ["point1", "point2", "point3"],
                "explanation": "What makes a good answer to this question",
                "difficulty": "medium",
                "points": 2,
                "tags": ["concept1", "application"]
            }
            """
        elif question_type == QuestionType.FILL_IN_BLANK:
            question_prompt += """
            {
                "question_id": "q1",
                "question_type": "fill_in_blank",
                "question_text": "Complete this sentence: The main concept is _____ because _____.",
                "correct_answer": "specific term, it enables understanding",
                "acceptable_answers": ["term1", "concept1", "idea1"],
                "explanation": "Explanation of the correct completion",
                "difficulty": "medium",
                "points": 1,
                "tags": ["vocabulary", "concept1"]
            }
            """
        
        question_prompt += "\nReturn only valid JSON."
        
        try:
            response = await self.bedrock.invoke_claude(
                prompt=question_prompt,
                max_tokens=4096,
                temperature=0.5
            )
            
            question_data = json.loads(response.strip())
            
            # Ensure required fields
            question_data['question_id'] = question_data.get('question_id', f'q{question_number}')
            question_data['question_type'] = question_type.value
            question_data['difficulty'] = difficulty
            question_data['points'] = question_data.get('points', 1)
            
            return question_data
            
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to generate {question_type.value} question: {e}")
            # Return a fallback question
            return self._create_fallback_question(question_type, difficulty, question_number)
    
    def _create_fallback_question(
        self,
        question_type: QuestionType,
        difficulty: str,
        question_number: int
    ) -> Dict[str, Any]:
        """
        Create a fallback question when generation fails.
        """
        if question_type == QuestionType.MULTIPLE_CHOICE:
            return {
                'question_id': f'q{question_number}',
                'question_type': 'multiple_choice',
                'question_text': 'Which of the following best describes the main concept from the lesson?',
                'options': ['Option A', 'Option B', 'Option C', 'Option D'],
                'correct_answer': 'Option A',
                'explanation': 'This option correctly identifies the main concept.',
                'difficulty': difficulty,
                'points': 1,
                'tags': ['general']
            }
        else:
            return {
                'question_id': f'q{question_number}',
                'question_type': 'true_false',
                'question_text': 'The lesson covered important concepts that are relevant to learning.',
                'correct_answer': 'true',
                'explanation': 'This statement is true based on the lesson content.',
                'difficulty': difficulty,
                'points': 1,
                'tags': ['general']
            }
    
    async def _evaluate_individual_question(
        self,
        question: Dict[str, Any],
        user_answer: str,
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate a single question with intelligent partial credit.
        """
        question_type = question.get('question_type')
        
        if question_type in ['multiple_choice', 'true_false']:
            return await self._evaluate_exact_match_question(question, user_answer)
        elif question_type in ['short_answer', 'fill_in_blank']:
            return await self._evaluate_open_ended_question(question, user_answer, user_profile)
        else:
            return await self._evaluate_exact_match_question(question, user_answer)
    
    async def _evaluate_exact_match_question(
        self,
        question: Dict[str, Any],
        user_answer: str
    ) -> Dict[str, Any]:
        """
        Evaluate questions that require exact matches (MC, T/F).
        """
        correct_answer = question.get('correct_answer', '').strip().lower()
        user_answer_clean = user_answer.strip().lower()
        
        is_correct = correct_answer == user_answer_clean
        score = question.get('points', 1) if is_correct else 0
        
        return {
            'question_id': question.get('question_id'),
            'user_answer': user_answer,
            'correct_answer': question.get('correct_answer'),
            'is_correct': is_correct,
            'score': score,
            'max_points': question.get('points', 1),
            'feedback': question.get('explanation', '') if is_correct else f"The correct answer is: {question.get('correct_answer')}. {question.get('explanation', '')}",
            'evaluation_type': 'exact_match'
        }
    
    async def _evaluate_open_ended_question(
        self,
        question: Dict[str, Any],
        user_answer: str,
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate open-ended questions with intelligent partial credit.
        """
        evaluation_prompt = f"""
        Evaluate this student's answer with partial credit and detailed feedback:
        
        Question: {question.get('question_text', '')}
        Correct Answer: {question.get('correct_answer', '')}
        Key Points: {question.get('key_points', [])}
        Student Answer: {user_answer}
        
        Max Points: {question.get('points', 2)}
        
        Evaluate based on:
        1. Accuracy of key concepts
        2. Completeness of explanation
        3. Understanding demonstrated
        4. Partial credit for partially correct elements
        
        Return JSON:
        {{
            "score": 1.5,
            "is_correct": false,
            "partial_credit_given": true,
            "key_points_covered": ["point1", "point2"],
            "key_points_missed": ["point3"],
            "feedback": "Detailed constructive feedback",
            "suggestions": "Specific suggestions for improvement"
        }}
        """
        
        try:
            response = await self.bedrock.invoke_claude(
                prompt=evaluation_prompt,
                max_tokens=4096,
                temperature=0.3
            )
            
            evaluation = json.loads(response.strip())
            
            return {
                'question_id': question.get('question_id'),
                'user_answer': user_answer,
                'correct_answer': question.get('correct_answer'),
                'is_correct': evaluation.get('is_correct', False),
                'score': evaluation.get('score', 0),
                'max_points': question.get('points', 2),
                'feedback': evaluation.get('feedback', ''),
                'suggestions': evaluation.get('suggestions', ''),
                'key_points_covered': evaluation.get('key_points_covered', []),
                'key_points_missed': evaluation.get('key_points_missed', []),
                'partial_credit_given': evaluation.get('partial_credit_given', False),
                'evaluation_type': 'intelligent_partial_credit'
            }
            
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to evaluate open-ended question: {e}")
            # Fallback evaluation
            return {
                'question_id': question.get('question_id'),
                'user_answer': user_answer,
                'correct_answer': question.get('correct_answer'),
                'is_correct': False,
                'score': 0,
                'max_points': question.get('points', 2),
                'feedback': 'Unable to evaluate answer automatically. Please review with instructor.',
                'evaluation_type': 'fallback'
            }
    
    async def _generate_comprehensive_feedback(
        self,
        question_evaluations: List[Dict[str, Any]],
        percentage_score: float,
        time_spent_seconds: int,
        user_profile: Dict[str, Any]
    ) -> str:
        """
        Generate comprehensive feedback based on overall quiz performance.
        """
        feedback_prompt = f"""
        Generate encouraging, comprehensive feedback for a student's quiz performance:
        
        Overall Score: {percentage_score:.1f}%
        Time Spent: {time_spent_seconds // 60} minutes {time_spent_seconds % 60} seconds
        Questions Answered: {len(question_evaluations)}
        
        Question Performance:
        {json.dumps([{
            'question_id': q['question_id'],
            'score': q['score'],
            'max_points': q['max_points'],
            'is_correct': q['is_correct']
        } for q in question_evaluations], indent=2)}
        
        User Learning Style: {user_profile.get('learning_style', 'visual')}
        
        Provide:
        1. Positive reinforcement for what they did well
        2. Specific areas of strength
        3. Gentle guidance for improvement areas
        4. Encouragement to continue learning
        5. Personalized suggestions based on their learning style
        
        Keep it encouraging, constructive, and motivating (3-4 sentences).
        """
        
        try:
            feedback = await self.bedrock.invoke_claude(
                prompt=feedback_prompt,
                max_tokens=4096,
                temperature=0.7
            )
            return feedback.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate feedback: {e}")
            if percentage_score >= 80:
                return "Excellent work! You demonstrated strong understanding of the concepts."
            elif percentage_score >= 60:
                return "Good effort! You're on the right track. Review the areas where you missed points and try again."
            else:
                return "Keep practicing! Learning takes time, and you're making progress. Focus on the key concepts and don't give up."
    
    async def _analyze_performance_patterns(
        self,
        question_evaluations: List[Dict[str, Any]],
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze performance patterns to identify strengths and weaknesses.
        """
        # Group by question type
        type_performance = {}
        difficulty_performance = {}
        
        for evaluation in question_evaluations:
            # This would require question metadata to be passed through
            # For now, we'll do basic analysis
            pass
        
        # Calculate basic metrics
        total_questions = len(question_evaluations)
        correct_answers = sum(1 for q in question_evaluations if q['is_correct'])
        partial_credit_questions = sum(1 for q in question_evaluations if q.get('partial_credit_given', False))
        
        return {
            'total_questions': total_questions,
            'correct_answers': correct_answers,
            'accuracy_rate': correct_answers / total_questions if total_questions > 0 else 0,
            'partial_credit_questions': partial_credit_questions,
            'strengths': ['conceptual_understanding'] if correct_answers > total_questions * 0.7 else [],
            'areas_for_improvement': ['application_skills'] if correct_answers < total_questions * 0.6 else [],
            'question_type_performance': type_performance,
            'difficulty_performance': difficulty_performance
        }
    
    async def _generate_learning_recommendations(
        self,
        performance_analysis: Dict[str, Any],
        percentage_score: float
    ) -> List[str]:
        """
        Generate personalized learning recommendations based on performance.
        """
        recommendations = []
        
        if percentage_score >= 90:
            recommendations.extend([
                "Excellent mastery! Consider exploring advanced topics in this area.",
                "You're ready to move on to more challenging concepts."
            ])
        elif percentage_score >= 70:
            recommendations.extend([
                "Good understanding! Review any missed concepts to strengthen your knowledge.",
                "Practice applying these concepts in different contexts."
            ])
        elif percentage_score >= 50:
            recommendations.extend([
                "You're making progress! Focus on the key concepts you missed.",
                "Consider reviewing the lesson material before attempting similar questions."
            ])
        else:
            recommendations.extend([
                "Take time to review the lesson material thoroughly.",
                "Consider seeking additional help or resources for these concepts.",
                "Practice with simpler examples before tackling complex problems."
            ])
        
        return recommendations


# Global service instance
quiz_engine = QuizEngine()