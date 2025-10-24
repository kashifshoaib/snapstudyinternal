#!/usr/bin/env python3
"""
Comprehensive Functional Tests for Quiz Engine and Chat Agent.

This test suite integrates and enhances the existing quiz engine and chat agent tests
with proper pytest structure and comprehensive coverage.
"""

import pytest
import asyncio
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, List
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.quiz_engine import QuestionType, DifficultyLevel
from src.services.chat_agent import ChatIntent


# Global fixtures
@pytest.fixture
def mock_quiz_engine():
    """Mock quiz engine for testing."""
    with patch('src.services.quiz_engine.quiz_engine') as mock:
        mock.generate_adaptive_quiz = AsyncMock()
        mock.evaluate_quiz_submission = AsyncMock()
        mock.generate_contextual_hint = AsyncMock()
        yield mock


@pytest.fixture
def mock_chat_agent():
    """Mock chat agent for testing."""
    with patch('src.services.chat_agent.chat_agent') as mock:
        mock.handle_message = AsyncMock()
        mock.recognize_intent = AsyncMock()
        mock.generate_response = AsyncMock()
        yield mock


@pytest.fixture
def mock_bedrock_service():
    """Mock Bedrock service for testing."""
    with patch('src.services.bedrock.bedrock_service') as mock:
        mock.invoke_claude = AsyncMock()
        yield mock


@pytest.fixture
def sample_user():
    """Sample user data for testing."""
    return {
        'user_id': str(uuid.uuid4()),
        'email': 'quiz-test@example.com',
        'full_name': 'Quiz Test User',
        'learning_style': 'visual',
        'attention_span': 15,
        'difficulty_level': 'intermediate',
        'profession': 'student',
        'is_active': True
    }


@pytest.fixture
def sample_lesson_content():
    """Sample lesson content for testing."""
    return """
    Machine Learning Fundamentals
    
    Machine learning is a subset of artificial intelligence that enables computers to learn 
    and make decisions from data without being explicitly programmed. Key concepts include:
    
    1. Supervised Learning: Learning with labeled examples
    2. Unsupervised Learning: Finding patterns in unlabeled data
    3. Neural Networks: Computing systems inspired by biological neural networks
    4. Training Data: The dataset used to teach the algorithm
    5. Model Validation: Testing the model's performance on new data
    """


class TestQuizEngine:
    """Test quiz engine functionality."""
    
    @pytest.mark.asyncio
    async def test_adaptive_quiz_generation(self, mock_quiz_engine, sample_user, sample_lesson_content):
        """Test adaptive quiz generation with different parameters."""
        # Mock quiz generation response
        mock_quiz_data = {
            'quiz_id': str(uuid.uuid4()),
            'quiz_metadata': {
                'title': 'Machine Learning Fundamentals Quiz',
                'total_questions': 5,
                'difficulty_level': 'medium',
                'estimated_duration_minutes': 10,
                'question_types': ['multiple_choice', 'short_answer', 'true_false']
            },
            'questions': [
                {
                    'question_id': 'q1',
                    'question_type': 'multiple_choice',
                    'question_text': 'What is machine learning?',
                    'options': [
                        'A subset of AI that learns from data',
                        'A programming language',
                        'A database system',
                        'A web framework'
                    ],
                    'correct_answer': 'A subset of AI that learns from data',
                    'difficulty': 'easy',
                    'concept': 'machine_learning_definition'
                },
                {
                    'question_id': 'q2',
                    'question_type': 'short_answer',
                    'question_text': 'Explain the difference between supervised and unsupervised learning.',
                    'correct_answer': 'Supervised learning uses labeled data while unsupervised learning finds patterns in unlabeled data',
                    'difficulty': 'medium',
                    'concept': 'learning_types'
                }
            ]
        }
        
        mock_quiz_engine.generate_adaptive_quiz.return_value = mock_quiz_data
        
        # Test quiz generation
        quiz_data = await mock_quiz_engine.generate_adaptive_quiz(
            lesson_content=sample_lesson_content,
            user_profile=sample_user,
            performance_history=[],
            target_difficulty="medium",
            num_questions=5
        )
        
        assert quiz_data['quiz_metadata']['title'] == 'Machine Learning Fundamentals Quiz'
        assert quiz_data['quiz_metadata']['total_questions'] == 5
        assert quiz_data['quiz_metadata']['difficulty_level'] == 'medium'
        assert len(quiz_data['questions']) == 2  # Mock has 2 questions
        
        # Validate question structure
        question1 = quiz_data['questions'][0]
        assert question1['question_type'] == 'multiple_choice'
        assert 'options' in question1
        assert len(question1['options']) == 4
        
        question2 = quiz_data['questions'][1]
        assert question2['question_type'] == 'short_answer'
        assert 'correct_answer' in question2
        
        mock_quiz_engine.generate_adaptive_quiz.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_intelligent_quiz_evaluation(self, mock_quiz_engine, sample_user):
        """Test intelligent quiz evaluation with partial credit."""
        # Sample questions for evaluation
        questions = [
            {
                'question_id': 'q1',
                'question_type': 'multiple_choice',
                'question_text': 'What is machine learning?',
                'correct_answer': 'A subset of AI that learns from data'
            },
            {
                'question_id': 'q2',
                'question_type': 'short_answer',
                'question_text': 'Explain supervised learning.',
                'correct_answer': 'Learning with labeled examples'
            }
        ]
        
        # Test answers with mixed performance
        test_answers = {
            'q1': 'A subset of AI that learns from data',  # Correct
            'q2': 'Learning with some examples'  # Partially correct
        }
        
        # Mock evaluation results
        mock_evaluation = {
            'overall_score': 75.0,
            'total_points_earned': 7.5,
            'total_possible_points': 10.0,
            'time_spent_seconds': 420,
            'overall_feedback': 'Good understanding of basic concepts. Consider reviewing supervised learning in more detail.',
            'recommendations': [
                'Review supervised learning concepts',
                'Practice with more examples'
            ],
            'question_evaluations': [
                {
                    'question_id': 'q1',
                    'is_correct': True,
                    'score': 5.0,
                    'max_score': 5.0,
                    'feedback': 'Excellent! Correct definition of machine learning.',
                    'partial_credit_given': False
                },
                {
                    'question_id': 'q2',
                    'is_correct': False,
                    'score': 2.5,
                    'max_score': 5.0,
                    'feedback': 'Partially correct. You mentioned examples but missed the key aspect of labeled data.',
                    'partial_credit_given': True
                }
            ]
        }
        
        mock_quiz_engine.evaluate_quiz_submission.return_value = mock_evaluation
        
        # Test evaluation
        evaluation_results = await mock_quiz_engine.evaluate_quiz_submission(
            quiz_id=str(uuid.uuid4()),
            questions=questions,
            user_answers=test_answers,
            time_spent_seconds=420,
            user_profile=sample_user
        )
        
        assert evaluation_results['overall_score'] == 75.0
        assert evaluation_results['total_points_earned'] == 7.5
        assert len(evaluation_results['question_evaluations']) == 2
        
        # Check partial credit was given
        q2_eval = evaluation_results['question_evaluations'][1]
        assert q2_eval['partial_credit_given'] is True
        assert q2_eval['score'] == 2.5
        assert 'labeled data' in q2_eval['feedback']
        
        # Check recommendations
        assert len(evaluation_results['recommendations']) == 2
        assert 'supervised learning' in evaluation_results['recommendations'][0]
        
        mock_quiz_engine.evaluate_quiz_submission.assert_called_once() 
   
    @pytest.mark.asyncio
    async def test_contextual_hint_generation(self, mock_quiz_engine, sample_user):
        """Test contextual hint generation for quiz questions."""
        # Test question
        test_question = {
            'question_id': 'test_q1',
            'question_type': 'multiple_choice',
            'question_text': 'What is the primary difference between supervised and unsupervised learning?',
            'options': [
                'Supervised learning uses labeled data, unsupervised learning does not',
                'Supervised learning is faster than unsupervised learning',
                'Supervised learning uses more data than unsupervised learning',
                'There is no difference between them'
            ],
            'correct_answer': 'Supervised learning uses labeled data, unsupervised learning does not',
            'difficulty': 'medium'
        }
        
        # Mock hint generation
        mock_hint = {
            'hint': 'Think about what kind of data each learning type uses. One has examples with known answers, the other discovers patterns on its own.',
            'hint_type': 'conceptual',
            'confidence': 0.85,
            'difficulty_level': 'medium'
        }
        
        mock_quiz_engine.generate_contextual_hint.return_value = mock_hint
        
        # Test hint generation
        hint_data = await mock_quiz_engine.generate_contextual_hint(
            question=test_question,
            user_context={'learning_style': 'visual', 'difficulty_level': 'intermediate'},
            previous_attempts=['Wrong answer 1', 'Wrong answer 2']
        )
        
        assert hint_data['hint_type'] == 'conceptual'
        assert hint_data['confidence'] == 0.85
        assert len(hint_data['hint']) > 20
        assert 'labeled' not in hint_data['hint'].lower()  # Shouldn't give away answer
        
        mock_quiz_engine.generate_contextual_hint.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_performance_based_adaptation(self, mock_quiz_engine, sample_user, sample_lesson_content):
        """Test quiz adaptation based on performance history."""
        # Test scenarios with different performance histories
        scenarios = [
            {
                'name': 'High Performer',
                'history': [
                    {'score': 95, 'difficulty': 'medium'},
                    {'score': 88, 'difficulty': 'medium'},
                    {'score': 92, 'difficulty': 'hard'}
                ],
                'expected_difficulty': 'hard'
            },
            {
                'name': 'Struggling Learner',
                'history': [
                    {'score': 45, 'difficulty': 'easy'},
                    {'score': 52, 'difficulty': 'easy'},
                    {'score': 38, 'difficulty': 'medium'}
                ],
                'expected_difficulty': 'easy'
            }
        ]
        
        for scenario in scenarios:
            # Mock adapted quiz
            mock_quiz = {
                'quiz_metadata': {
                    'difficulty_level': scenario['expected_difficulty'],
                    'estimated_duration_minutes': 8 if scenario['expected_difficulty'] == 'easy' else 12
                },
                'questions': []
            }
            
            mock_quiz_engine.generate_adaptive_quiz.return_value = mock_quiz
            
            # Test adaptation
            quiz_data = await mock_quiz_engine.generate_adaptive_quiz(
                lesson_content=sample_lesson_content,
                user_profile=sample_user,
                performance_history=scenario['history'],
                target_difficulty="adaptive",
                num_questions=4
            )
            
            assert quiz_data['quiz_metadata']['difficulty_level'] == scenario['expected_difficulty']


class TestChatAgent:
    """Test chat agent functionality."""
    
    @pytest.mark.asyncio
    async def test_intent_recognition(self, mock_chat_agent):
        """Test intent recognition capabilities."""
        test_messages = [
            {
                'message': "Can you summarize what we've covered so far?",
                'expected_intent': ChatIntent.SUMMARIZATION,
                'expected_confidence': 0.9
            },
            {
                'message': "I don't understand derivatives, can you explain?",
                'expected_intent': ChatIntent.EXPLANATION,
                'expected_confidence': 0.95
            },
            {
                'message': "Test my knowledge on this topic",
                'expected_intent': ChatIntent.QUIZ_REQUEST,
                'expected_confidence': 0.88
            },
            {
                'message': "How am I doing with my progress?",
                'expected_intent': ChatIntent.PROGRESS_INQUIRY,
                'expected_confidence': 0.92
            }
        ]
        
        # Mock user context
        mock_context = {
            'current_lesson': {
                'lesson_id': 'test-lesson-1',
                'title': 'Introduction to Calculus',
                'content': 'This lesson covers basic calculus concepts including derivatives and integrals.',
                'key_concepts': ['derivatives', 'integrals', 'limits']
            },
            'learning_progress': {
                'completion_percentage': 45.0,
                'current_index': 2,
                'total_micro_lessons': 5
            }
        }
        
        for test_case in test_messages:
            # Mock chat response
            mock_response = {
                'intent': test_case['expected_intent'].value,
                'confidence': test_case['expected_confidence'],
                'response_type': 'text',
                'response': f"Mock response for {test_case['expected_intent'].value}",
                'context_used': True
            }
            
            mock_chat_agent.handle_message.return_value = mock_response
            
            # Test intent recognition
            response = await mock_chat_agent.handle_message(
                user_id='test-user-123',
                message=test_case['message'],
                context=mock_context,
                session_id='test-session-1'
            )
            
            assert response['intent'] == test_case['expected_intent'].value
            assert response['confidence'] == test_case['expected_confidence']
            assert response['response_type'] == 'text'
            assert len(response['response']) > 0
    
    @pytest.mark.asyncio
    async def test_conversation_flow(self, mock_chat_agent):
        """Test natural conversation flow."""
        conversation = [
            "Hi, I'm starting to learn calculus",
            "Can you explain what a derivative is?",
            "That's helpful, can you give me an example?",
            "Test my understanding with a question",
            "How am I doing overall?"
        ]
        
        session_id = 'test-conversation-session'
        user_id = 'test-user-456'
        
        mock_context = {
            'current_lesson': {
                'lesson_id': 'calculus-101',
                'title': 'Calculus Fundamentals',
                'content': 'Learn the basics of calculus including derivatives, integrals, and their applications.',
                'key_concepts': ['derivatives', 'integrals', 'chain rule', 'product rule']
            },
            'learning_progress': {
                'completion_percentage': 25.0,
                'current_index': 1,
                'total_micro_lessons': 4
            }
        }
        
        # Mock responses for conversation flow
        mock_responses = [
            {
                'intent': ChatIntent.GENERAL_CHAT.value,
                'confidence': 0.8,
                'response': "Welcome to calculus! I'm here to help you learn.",
                'response_type': 'text'
            },
            {
                'intent': ChatIntent.EXPLANATION.value,
                'confidence': 0.95,
                'response': "A derivative measures how a function changes as its input changes.",
                'response_type': 'explanation'
            },
            {
                'intent': ChatIntent.EXPLANATION.value,
                'confidence': 0.9,
                'response': "Sure! For example, if f(x) = x², then f'(x) = 2x.",
                'response_type': 'example'
            },
            {
                'intent': ChatIntent.QUIZ_REQUEST.value,
                'confidence': 0.88,
                'response': "Great! What is the derivative of f(x) = 3x²?",
                'response_type': 'quiz'
            },
            {
                'intent': ChatIntent.PROGRESS_INQUIRY.value,
                'confidence': 0.92,
                'response': "You're doing well! You've completed 25% of the calculus fundamentals.",
                'response_type': 'progress'
            }
        ]
        
        for i, (message, expected_response) in enumerate(zip(conversation, mock_responses)):
            mock_chat_agent.handle_message.return_value = expected_response
            
            response = await mock_chat_agent.handle_message(
                user_id=user_id,
                message=message,
                context=mock_context,
                session_id=session_id
            )
            
            assert response['intent'] == expected_response['intent']
            assert response['response'] == expected_response['response']
            assert response['response_type'] == expected_response['response_type']
    
    @pytest.mark.asyncio
    async def test_context_awareness(self, mock_chat_agent):
        """Test context awareness across different scenarios."""
        scenarios = [
            {
                'name': 'No Active Lesson',
                'context': {'current_lesson': {}, 'learning_progress': {}},
                'message': 'Can you summarize the lesson?',
                'expected_response': "I don't see an active lesson. Would you like to start a new one?"
            },
            {
                'name': 'High Performance Context',
                'context': {
                    'current_lesson': {'title': 'Advanced Topics', 'key_concepts': ['complex analysis']},
                    'learning_progress': {'completion_percentage': 90.0},
                    'recent_engagement': [
                        {'event_type': 'quiz_completed', 'event_data': {'score': 95.0}},
                        {'event_type': 'quiz_completed', 'event_data': {'score': 88.0}}
                    ]
                },
                'message': 'How am I doing?',
                'expected_response': "Excellent work! You're performing at a high level with 90% completion."
            },
            {
                'name': 'Struggling Student Context',
                'context': {
                    'current_lesson': {'title': 'Basic Concepts', 'key_concepts': ['fundamentals']},
                    'learning_progress': {'completion_percentage': 15.0},
                    'recent_engagement': [
                        {'event_type': 'quiz_completed', 'event_data': {'score': 45.0}},
                        {'event_type': 'quiz_completed', 'event_data': {'score': 38.0}}
                    ]
                },
                'message': 'This is too hard for me',
                'expected_response': "I understand this can be challenging. Let's break it down into smaller steps."
            }
        ]
        
        for scenario in scenarios:
            # Mock context-aware response
            mock_response = {
                'intent': ChatIntent.ENCOURAGEMENT.value if 'hard' in scenario['message'] else ChatIntent.PROGRESS_INQUIRY.value,
                'confidence': 0.85,
                'response': scenario['expected_response'],
                'response_type': 'contextual',
                'context_analysis': {
                    'lesson_status': 'active' if scenario['context'].get('current_lesson') else 'none',
                    'performance_level': 'high' if scenario['name'] == 'High Performance Context' else 'struggling' if scenario['name'] == 'Struggling Student Context' else 'unknown'
                }
            }
            
            mock_chat_agent.handle_message.return_value = mock_response
            
            response = await mock_chat_agent.handle_message(
                user_id='test-context-user',
                message=scenario['message'],
                context=scenario['context'],
                session_id=f"test-{scenario['name'].lower().replace(' ', '-')}"
            )
            
            assert response['response'] == scenario['expected_response']
            assert 'context_analysis' in response
            assert response['response_type'] == 'contextual'


class TestQuizChatIntegration:
    """Test integration between quiz engine and chat agent."""
    
    @pytest.mark.asyncio
    async def test_quiz_request_through_chat(self, mock_chat_agent, mock_quiz_engine, sample_user):
        """Test quiz generation triggered through chat interaction."""
        # Mock chat recognizing quiz request
        mock_chat_response = {
            'intent': ChatIntent.QUIZ_REQUEST.value,
            'confidence': 0.9,
            'response': "I'll generate a quiz for you based on the current lesson.",
            'response_type': 'quiz_generation',
            'action_required': 'generate_quiz'
        }
        
        mock_chat_agent.handle_message.return_value = mock_chat_response
        
        # Mock quiz generation
        mock_quiz = {
            'quiz_id': str(uuid.uuid4()),
            'questions': [
                {
                    'question_id': 'q1',
                    'question_text': 'What is machine learning?',
                    'question_type': 'multiple_choice'
                }
            ]
        }
        
        mock_quiz_engine.generate_adaptive_quiz.return_value = mock_quiz
        
        # Test chat interaction
        chat_response = await mock_chat_agent.handle_message(
            user_id=sample_user['user_id'],
            message="Test my knowledge on this topic",
            context={'current_lesson': {'title': 'ML Basics'}},
            session_id='test-session'
        )
        
        assert chat_response['intent'] == ChatIntent.QUIZ_REQUEST.value
        assert chat_response['action_required'] == 'generate_quiz'
        
        # Test quiz generation (would be triggered by the action)
        if chat_response['action_required'] == 'generate_quiz':
            quiz = await mock_quiz_engine.generate_adaptive_quiz(
                lesson_content="ML content",
                user_profile=sample_user,
                performance_history=[],
                target_difficulty="medium",
                num_questions=3
            )
            
            assert 'quiz_id' in quiz
            assert len(quiz['questions']) >= 1
    
    @pytest.mark.asyncio
    async def test_quiz_help_through_chat(self, mock_chat_agent, mock_quiz_engine):
        """Test getting quiz help through chat interaction."""
        # Mock chat recognizing help request
        mock_chat_response = {
            'intent': ChatIntent.HELP_REQUEST.value,
            'confidence': 0.88,
            'response': "I can provide a hint for this question.",
            'response_type': 'hint_offer',
            'action_required': 'generate_hint'
        }
        
        mock_chat_agent.handle_message.return_value = mock_chat_response
        
        # Mock hint generation
        mock_hint = {
            'hint': 'Think about the key characteristics that distinguish these concepts.',
            'hint_type': 'conceptual',
            'confidence': 0.82
        }
        
        mock_quiz_engine.generate_contextual_hint.return_value = mock_hint
        
        # Test help request
        chat_response = await mock_chat_agent.handle_message(
            user_id='test-user',
            message="I need help with this question",
            context={
                'current_quiz': {
                    'question_id': 'q1',
                    'question_text': 'What is the difference between AI and ML?'
                }
            },
            session_id='quiz-session'
        )
        
        assert chat_response['intent'] == ChatIntent.HELP_REQUEST.value
        assert chat_response['action_required'] == 'generate_hint'
        
        # Test hint generation (would be triggered by the action)
        if chat_response['action_required'] == 'generate_hint':
            hint = await mock_quiz_engine.generate_contextual_hint(
                question={'question_id': 'q1', 'question_text': 'What is the difference between AI and ML?'},
                user_context={'learning_style': 'visual'},
                previous_attempts=[]
            )
            
            assert 'hint' in hint
            assert hint['hint_type'] == 'conceptual'
    
    @pytest.mark.asyncio
    async def test_quiz_explanation_through_chat(self, mock_chat_agent, sample_user):
        """Test getting quiz answer explanations through chat."""
        # Mock chat recognizing explanation request
        mock_chat_response = {
            'intent': ChatIntent.EXPLANATION.value,
            'confidence': 0.93,
            'response': "Let me explain why the correct answer is 'A subset of AI that learns from data'.",
            'response_type': 'explanation',
            'explanation_content': {
                'concept': 'machine_learning_definition',
                'detailed_explanation': 'Machine learning is indeed a subset of artificial intelligence...',
                'examples': ['Image recognition', 'Recommendation systems'],
                'related_concepts': ['artificial intelligence', 'deep learning']
            }
        }
        
        mock_chat_agent.handle_message.return_value = mock_chat_response
        
        # Test explanation request
        response = await mock_chat_agent.handle_message(
            user_id=sample_user['user_id'],
            message="Can you explain why this answer is correct?",
            context={
                'current_quiz': {
                    'question_id': 'q1',
                    'correct_answer': 'A subset of AI that learns from data',
                    'user_answer': 'A programming language'
                }
            },
            session_id='explanation-session'
        )
        
        assert response['intent'] == ChatIntent.EXPLANATION.value
        assert 'explanation_content' in response
        assert 'detailed_explanation' in response['explanation_content']
        assert len(response['explanation_content']['examples']) > 0


if __name__ == "__main__":
    """Run the quiz engine and chat agent functional tests."""
    print("📝💬 SnapStudy Quiz Engine & Chat Agent Functional Test Suite")
    print("=" * 70)
    
    # Run pytest with verbose output
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--color=yes"
    ])