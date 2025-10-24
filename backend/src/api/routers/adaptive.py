"""
Adaptive Learning Router - Autonomous Agent-Based Learning Path Adaptation.

This router provides endpoints for the autonomous adaptive learning system that
uses Amazon Bedrock Agents to make real-time decisions about learning paths,
content difficulty, and personalization without human intervention.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import logging

from ...services.adaptive_agent import adaptive_agent
from ...services.dynamodb import db_service
from ...middleware.auth_middleware import require_auth
from ...middleware.error_handler import (
    ResourceNotFoundError,
    ValidationError,
    ServiceUnavailableError
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/start-lesson",
    summary="Start Autonomous Adaptive Learning Session",
    description="""
    Initiates an adaptive learning session with autonomous AI agent control.

    The system autonomously:
    - Analyzes user profile and learning history
    - Generates personalized micro-lessons
    - Determines optimal starting difficulty
    - Creates initial assessment

    Returns the first micro-lesson and adaptation info.
    """,
    response_description="Adaptive learning session with first micro-lesson"
)
async def start_adaptive_lesson(
    lesson_id: str,
    user: Dict[str, Any] = Depends(require_auth)
) -> Dict[str, Any]:
    """
    Start an autonomous adaptive learning session.

    Args:
        lesson_id: ID of the lesson to start
        user: Authenticated user (injected by dependency)

    Returns:
        Dict containing session_id, lesson, first micro-lesson, and progress
    """
    try:
        user_id = user.get('user_id')

        logger.info(f"Starting adaptive lesson {lesson_id} for user {user_id}")

        # Start adaptive session with agent
        result = await adaptive_agent.start_adaptive_lesson(user_id, lesson_id)

        # Track session start
        await db_service.track_engagement({
            'user_id': user_id,
            'event_type': 'adaptive_session_started',
            'event_data': {
                'session_id': result['session_id'],
                'lesson_id': lesson_id,
                'autonomous_mode': True
            }
        })

        return {
            'success': True,
            'session_id': result['session_id'],
            'lesson': result['lesson'],
            'current_micro_lesson': result['current_micro_lesson'],
            'progress': result['progress'],
            'status': result['status'],
            'message': 'Adaptive learning session started with autonomous agent control'
        }

    except ResourceNotFoundError as e:
        logger.error(f"Resource not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to start adaptive lesson: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start adaptive learning session: {str(e)}"
        )


@router.post(
    "/next-micro-lesson",
    summary="Get Next Micro-Lesson with Autonomous Adaptation",
    description="""
    Requests the next micro-lesson with autonomous AI agent adaptation.

    The agent autonomously:
    - Analyzes previous performance data
    - Makes adaptation decision (advance, review, reinforce, simplify, etc.)
    - Generates personalized next micro-lesson
    - Adjusts difficulty based on learning state

    This is the core of the autonomous learning system.
    """,
    response_description="Next micro-lesson with adaptation reasoning"
)
async def get_next_micro_lesson(
    session_id: str,
    previous_performance: Optional[Dict[str, Any]] = None,
    user: Dict[str, Any] = Depends(require_auth)
) -> Dict[str, Any]:
    """
    Get next micro-lesson with autonomous adaptation.

    Args:
        session_id: Active learning session ID
        previous_performance: Optional performance data from previous micro-lesson
        user: Authenticated user

    Returns:
        Dict containing next micro-lesson and adaptation decision info
    """
    try:
        user_id = user.get('user_id')

        logger.info(f"Getting next micro-lesson for session {session_id}")

        # Get next micro-lesson with autonomous adaptation
        result = await adaptive_agent.get_next_micro_lesson(
            session_id,
            user_id,
            previous_performance
        )

        # Log autonomous decision
        logger.info(
            f"Autonomous decision for session {session_id}: "
            f"{result['adaptation_info']['decision']} - "
            f"{result['adaptation_info']['reasoning']}"
        )

        return {
            'success': True,
            'micro_lesson': result['micro_lesson'],
            'adaptation_info': {
                'decision': result['adaptation_info']['decision'],
                'reasoning': result['adaptation_info']['reasoning'],
                'learning_state': result['adaptation_info']['learning_state'],
                'autonomous': True,
                'confidence': result['adaptation_info'].get('confidence', 0.8)
            },
            'progress': result['progress'],
            'session_id': result['session_id']
        }

    except ValueError as e:
        logger.error(f"Invalid session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get next micro-lesson: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get next micro-lesson: {str(e)}"
        )


@router.post(
    "/submit-quiz",
    summary="Submit Quiz and Get Autonomous Adaptation",
    description="""
    Submits quiz answers and receives autonomous adaptation decision.

    The agent autonomously:
    - Evaluates answers with intelligent grading (including partial credit)
    - Analyzes performance metrics and engagement
    - Makes adaptation decision for next steps
    - Generates personalized feedback
    - Returns next micro-lesson based on performance

    This demonstrates real-time autonomous learning path adjustment.
    """,
    response_description="Quiz results, feedback, and next micro-lesson"
)
async def submit_quiz_and_adapt(
    session_id: str,
    quiz_id: str,
    answers: Dict[str, str],
    time_spent: int,
    engagement_metrics: Optional[Dict[str, Any]] = None,
    user: Dict[str, Any] = Depends(require_auth)
) -> Dict[str, Any]:
    """
    Submit quiz and get autonomous adaptation decision.

    Args:
        session_id: Active learning session ID
        quiz_id: ID of the quiz being submitted
        answers: User's answers {question_id: answer}
        time_spent: Time spent on quiz in seconds
        engagement_metrics: Optional engagement data (focus_score, etc.)
        user: Authenticated user

    Returns:
        Dict containing quiz results, feedback, and next micro-lesson
    """
    try:
        user_id = user.get('user_id')

        # Validate inputs
        if not answers:
            raise ValidationError("No answers provided")

        if time_spent < 0:
            raise ValidationError("Invalid time spent value")

        logger.info(
            f"Submitting quiz {quiz_id} for session {session_id}, "
            f"{len(answers)} answers, {time_spent}s"
        )

        # Default engagement metrics if not provided
        if not engagement_metrics:
            engagement_metrics = {'focus_score': 0.7}

        # Process quiz submission with autonomous adaptation
        result = await adaptive_agent.submit_quiz_and_adapt(
            session_id=session_id,
            user_id=user_id,
            quiz_id=quiz_id,
            answers=answers,
            time_spent=time_spent,
            engagement_metrics=engagement_metrics
        )

        # Log autonomous adaptation
        logger.info(
            f"Quiz submitted - Score: {result['quiz_results']['score']}%, "
            f"Adaptation: {result['adaptation_info']['decision']}"
        )

        return {
            'success': True,
            'quiz_results': {
                'score': result['quiz_results']['score'],
                'feedback': result['quiz_results']['feedback'],
                'detailed_results': result['quiz_results']['detailed_results']
            },
            'adaptation_info': {
                'decision': result['adaptation_info']['decision'],
                'reasoning': result['adaptation_info']['reasoning'],
                'learning_state': result['adaptation_info']['learning_state'],
                'autonomous': True
            },
            'next_micro_lesson': result['next_micro_lesson'],
            'progress': result['progress']
        }

    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ResourceNotFoundError as e:
        logger.error(f"Resource not found: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to submit quiz: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process quiz submission: {str(e)}"
        )


@router.get(
    "/adaptation-history/{session_id}",
    summary="Get Autonomous Adaptation Decision History",
    description="""
    Retrieves the history of autonomous adaptation decisions for a session.

    Shows how the agent has been adapting the learning path:
    - What decisions were made (advance, review, simplify, etc.)
    - Reasoning for each decision
    - Performance metrics that influenced decisions
    - Learning state transitions

    Useful for transparency and understanding the agent's decision-making.
    """,
    response_description="List of adaptation decisions with reasoning"
)
async def get_adaptation_history(
    session_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    user: Dict[str, Any] = Depends(require_auth)
) -> Dict[str, Any]:
    """
    Get adaptation decision history for a session.

    Args:
        session_id: Learning session ID
        limit: Maximum number of decisions to return
        user: Authenticated user

    Returns:
        Dict containing adaptation history
    """
    try:
        user_id = user.get('user_id')

        logger.info(f"Retrieving adaptation history for session {session_id}")

        # Query engagement events for adaptation decisions
        adaptations = await db_service.query_items(
            table_name='UserEngagement',
            index_name='UserEngagementIndex',
            key_condition={
                'user_id': user_id
            },
            filter_expression='event_type = :event_type AND event_data.session_id = :session_id',
            expression_values={
                ':event_type': 'autonomous_adaptation',
                ':session_id': session_id
            },
            limit=limit,
            scan_index_forward=False  # Most recent first
        )

        # Format adaptation history
        history = []
        for adaptation in adaptations:
            event_data = adaptation.get('event_data', {})
            history.append({
                'decision': event_data.get('decision'),
                'reasoning': event_data.get('reasoning'),
                'learning_state': event_data.get('learning_state'),
                'timestamp': adaptation.get('timestamp'),
                'confidence': event_data.get('confidence', 0.8)
            })

        return {
            'success': True,
            'session_id': session_id,
            'adaptation_count': len(history),
            'adaptations': history,
            'autonomous_decisions': True
        }

    except Exception as e:
        logger.error(f"Failed to retrieve adaptation history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve adaptation history: {str(e)}"
        )


@router.post(
    "/analyze-performance",
    summary="Analyze Learning Performance",
    description="""
    Analyzes learner performance using autonomous AI agents.

    Provides insights about:
    - Overall learning progress
    - Strengths and weaknesses
    - Recommended next actions
    - Learning velocity and patterns
    """,
    response_description="Performance analysis and recommendations"
)
async def analyze_performance(
    lesson_id: Optional[str] = None,
    time_period_days: int = Query(default=7, ge=1, le=90),
    user: Dict[str, Any] = Depends(require_auth)
) -> Dict[str, Any]:
    """
    Analyze user's learning performance.

    Args:
        lesson_id: Optional specific lesson to analyze
        time_period_days: Number of days to analyze (default 7)
        user: Authenticated user

    Returns:
        Dict containing performance analysis and recommendations
    """
    try:
        user_id = user.get('user_id')

        logger.info(f"Analyzing performance for user {user_id}")

        # Get engagement data
        from datetime import timedelta
        cutoff_date = (
            datetime.now(timezone.utc) - timedelta(days=time_period_days)
        ).isoformat()

        engagement_data = await db_service.query_items(
            table_name='UserEngagement',
            index_name='UserEngagementIndex',
            key_condition={
                'user_id': user_id
            },
            filter_expression='timestamp >= :cutoff',
            expression_values={
                ':cutoff': cutoff_date
            },
            limit=100
        )

        # Calculate metrics
        quiz_events = [
            e for e in engagement_data
            if e.get('event_type') == 'quiz_completed'
        ]

        if quiz_events:
            scores = [
                e.get('event_data', {}).get('score', 0)
                for e in quiz_events
            ]
            avg_score = sum(scores) / len(scores)

            # Determine performance level
            if avg_score >= 85:
                performance_level = 'excellent'
                recommendation = 'Consider advancing to more challenging material'
            elif avg_score >= 70:
                performance_level = 'good'
                recommendation = 'Continue current pace with occasional challenges'
            elif avg_score >= 60:
                performance_level = 'satisfactory'
                recommendation = 'Focus on reinforcing current concepts'
            else:
                performance_level = 'needs_improvement'
                recommendation = 'Review foundational concepts and simplify material'
        else:
            avg_score = 0
            performance_level = 'insufficient_data'
            recommendation = 'Complete more quizzes to get performance insights'

        return {
            'success': True,
            'user_id': user_id,
            'time_period_days': time_period_days,
            'metrics': {
                'quizzes_completed': len(quiz_events),
                'average_score': round(avg_score, 2),
                'performance_level': performance_level,
                'total_engagement_events': len(engagement_data)
            },
            'recommendation': recommendation,
            'analyzed_at': datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to analyze performance: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze performance: {str(e)}"
        )


@router.get(
    "/learning-state/{session_id}",
    summary="Get Current Learning State",
    description="""
    Gets the current autonomous learning state for a session.

    Returns information about:
    - Current learning state (struggling, learning, mastering, etc.)
    - Agent's assessment of learner progress
    - Recommended actions
    """,
    response_description="Current learning state assessment"
)
async def get_learning_state(
    session_id: str,
    user: Dict[str, Any] = Depends(require_auth)
) -> Dict[str, Any]:
    """
    Get current learning state for a session.

    Args:
        session_id: Learning session ID
        user: Authenticated user

    Returns:
        Dict containing current learning state
    """
    try:
        user_id = user.get('user_id')

        # Get recent adaptations to determine current state
        recent_adaptations = await db_service.query_items(
            table_name='UserEngagement',
            index_name='UserEngagementIndex',
            key_condition={
                'user_id': user_id
            },
            filter_expression='event_type = :event_type AND event_data.session_id = :session_id',
            expression_values={
                ':event_type': 'autonomous_adaptation',
                ':session_id': session_id
            },
            limit=1,
            scan_index_forward=False
        )

        if recent_adaptations:
            latest = recent_adaptations[0].get('event_data', {})
            return {
                'success': True,
                'session_id': session_id,
                'learning_state': latest.get('learning_state', 'learning'),
                'latest_decision': latest.get('decision', 'continue'),
                'reasoning': latest.get('reasoning', 'Continuing learning journey'),
                'timestamp': recent_adaptations[0].get('timestamp'),
                'autonomous': True
            }
        else:
            return {
                'success': True,
                'session_id': session_id,
                'learning_state': 'learning',
                'latest_decision': 'start',
                'reasoning': 'Session just started',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'autonomous': True
            }

    except Exception as e:
        logger.error(f"Failed to get learning state: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get learning state: {str(e)}"
        )
