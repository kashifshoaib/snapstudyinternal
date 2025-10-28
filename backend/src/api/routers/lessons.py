"""Lessons router."""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from ...middleware.auth_middleware import require_auth

router = APIRouter()
logger = logging.getLogger(__name__)


class LessonResponse(BaseModel):
    """Lesson response model."""
    lesson_id: str
    title: str
    subject: str
    created_at: str
    status: str
    difficulty: Optional[str] = "intermediate"


class MicroLessonResponse(BaseModel):
    """Micro lesson response model."""
    micro_lesson_id: str
    lesson_id: str
    title: str
    content: str
    summary: Optional[str] = None
    order: int
    estimated_duration_minutes: int
    key_concepts: Optional[List[str]] = []
    learning_objectives: Optional[List[str]] = []
    examples: Optional[List[Dict[str, Any]]] = []
    visual_aids: Optional[List[str]] = []
    quiz: Optional[Dict[str, Any]] = None  # Only for first micro-lesson


@router.get("/test")
async def test_lessons_endpoint():
    """Test endpoint to verify lessons router is working."""
    return {"message": "Lessons router is working", "timestamp": datetime.now().isoformat()}

@router.get("/", response_model=List[LessonResponse])
@router.get("", response_model=List[LessonResponse])  # Handle both with and without trailing slash
async def get_lessons(current_user: Dict[str, Any] = Depends(require_auth)):
    """
    Get lessons for the current user.

    Returns the last 3 unique processed lessons (with micro-lessons generated).
    """
    logger.info(f"GET /lessons request from user: {current_user.get('user_id', 'unknown')}")
    try:
        # Get real lessons from database
        from ...services.dynamodb import db_service
        from ...services.s3 import s3_service
        import asyncio

        user_lessons = await db_service.get_user_lessons(current_user["user_id"])

        # Filter for completed lessons only
        completed_lessons = [
            lesson for lesson in user_lessons
            if lesson.get("processing_status", "pending") == "completed"
        ]

        # Fast parallel cache checks for all lessons
        async def check_lesson_has_content(lesson):
            """Check if lesson has micro-lessons (cache or DB)"""
            # Fast check: Does cache exist? (uses head_object, doesn't retrieve data)
            has_cache = s3_service.check_cache_exists(
                lesson["lesson_id"],
                'micro_lessons'
            )

            if has_cache:
                return lesson

            # No cache, check DynamoDB (only if needed)
            micro_lessons = await db_service.get_lesson_micro_lessons(lesson["lesson_id"])
            if micro_lessons:
                return lesson

            return None

        # Check all lessons in parallel for speed
        check_tasks = [check_lesson_has_content(lesson) for lesson in completed_lessons]
        results = await asyncio.gather(*check_tasks, return_exceptions=True)

        # Filter out None results and exceptions
        processed_lessons = [
            result for result in results
            if result is not None and not isinstance(result, Exception)
        ]

        # Sort by created_at descending (most recent first)
        processed_lessons.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        # Take only the last 3 unique processed lessons
        recent_lessons = processed_lessons[:3]

        # Format lessons for response
        formatted_lessons = []
        for lesson in recent_lessons:
            formatted_lessons.append({
                "lesson_id": lesson["lesson_id"],
                "title": lesson["title"],
                "subject": lesson.get("subject", "General"),
                "created_at": lesson["created_at"],
                "status": lesson.get("status", "active"),
                "difficulty": lesson.get("difficulty", "intermediate")
            })

        logger.info(f"Returning {len(formatted_lessons)} processed lessons for user {current_user['user_id']}")
        return formatted_lessons
    except Exception as e:
        logger.error(f"Failed to get lessons: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve lessons"
        )


@router.post("/upload", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
async def upload_lesson(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Upload a new lesson file.

    Accepts PDF, DOCX, or TXT files and creates a new lesson.
    The system will automatically generate micro-lessons from the uploaded content.
    """
    try:
        # Validate file type
        allowed_types = ['.pdf', '.docx', '.txt', '.doc', '.ppt', '.pptx', '.md', '.rtf']
        file_ext = '.' + file.filename.split('.')[-1].lower()

        if file_ext not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not supported. Allowed types: {', '.join(allowed_types)}"
            )

        # Read file content
        content = await file.read()
        file_content = content.decode('utf-8') if file_ext in ['.txt', '.md'] else f"Uploaded file: {file.filename}"

        # Create lesson data for database with processing status
        lesson_data = {
            "user_id": current_user["user_id"],
            "title": file.filename.rsplit('.', 1)[0],
            "subject": "General",
            "content": file_content,
            "difficulty": "intermediate",
            "status": "active",
            "processing_status": "processing",  # Mark as processing
            "file_type": file_ext,
            "original_filename": file.filename
        }

        # Save to database
        from ...services.dynamodb import db_service
        from ...services.s3 import s3_service
        created_lesson = await db_service.create_lesson(lesson_data)

        lesson_id = created_lesson["lesson_id"]
        user_id = current_user["user_id"]

        # Clear any existing cache for this lesson (in case of re-upload)
        try:
            await s3_service.clear_lesson_cache(lesson_id)
        except Exception as cache_error:
            logger.warning(f"Failed to clear lesson cache: {cache_error}")

        # Generate micro-lessons asynchronously using adaptive agent
        try:
            logger.info(f"Generating micro-lessons for lesson {lesson_id}")
            from ...services.adaptive_agent import adaptive_agent

            # Get the full lesson object for micro-lesson generation
            lesson = await db_service.get_lesson(lesson_id)

            # Get the full user object
            user = await db_service.get_user_by_id(user_id)

            # Generate initial micro-lessons
            await adaptive_agent._generate_initial_micro_lessons(
                lesson=lesson,
                user=user
            )

            # Update lesson status to completed
            await db_service.update_lesson(lesson_id, {
                'processing_status': 'completed',
                'status': 'active'
            })

            logger.info(f"Successfully generated micro-lessons for lesson {lesson_id}")

        except Exception as gen_error:
            logger.error(f"Failed to generate micro-lessons for lesson {lesson_id}: {str(gen_error)}")

            # Update lesson status to failed
            await db_service.update_lesson(lesson_id, {
                'processing_status': 'failed',
                'error_message': str(gen_error)
            })

            # Don't fail the upload, just log the error
            # The lesson is created but micro-lessons generation failed

        # Return the created lesson
        return {
            "lesson_id": created_lesson["lesson_id"],
            "title": created_lesson["title"],
            "subject": created_lesson["subject"],
            "created_at": created_lesson["created_at"],
            "status": created_lesson["status"],
            "difficulty": created_lesson["difficulty"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload lesson: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload lesson"
        )


@router.get("/{lesson_id}", response_model=LessonResponse)
async def get_lesson(
    lesson_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get a specific lesson by ID.

    Returns detailed information about a single lesson.
    """
    try:
        from ...services.dynamodb import db_service

        lesson = await db_service.get_lesson(lesson_id)
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lesson {lesson_id} not found"
            )

        if lesson.get('user_id') != current_user['user_id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: lesson does not belong to user"
            )

        return {
            "lesson_id": lesson["lesson_id"],
            "title": lesson["title"],
            "subject": lesson.get("subject", "General"),
            "created_at": lesson["created_at"],
            "status": lesson.get("status", "active"),
            "difficulty": lesson.get("difficulty", "intermediate")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get lesson {lesson_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lesson {lesson_id} not found"
        )


class ProcessingStatusResponse(BaseModel):
    """Processing status response model."""
    status: str
    progress_percentage: int
    stage: str
    error_message: Optional[str] = None


@router.get("/{lesson_id}/processing-status", response_model=ProcessingStatusResponse)
async def get_processing_status(
    lesson_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get processing status for a lesson.

    Returns the current processing status, progress, and stage information.
    """
    try:
        from ...services.dynamodb import db_service

        # Get lesson
        lesson = await db_service.get_lesson(lesson_id)
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lesson {lesson_id} not found"
            )

        if lesson.get('user_id') != current_user['user_id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: lesson does not belong to user"
            )

        # Get micro-lessons to determine completion
        micro_lessons = await db_service.get_lesson_micro_lessons(lesson_id)

        # Determine status based on micro-lessons existence
        processing_status = lesson.get('processing_status', 'pending')
        has_micro_lessons = len(micro_lessons) > 0

        if has_micro_lessons:
            status_value = 'completed'
            progress = 100
            stage = 'completed'
        elif processing_status == 'failed':
            status_value = 'failed'
            progress = 0
            stage = 'failed'
        elif processing_status == 'processing':
            status_value = 'processing'
            progress = 50
            stage = 'generating_micro_lessons'
        else:
            status_value = 'pending'
            progress = 0
            stage = 'pending'

        return {
            'status': status_value,
            'progress_percentage': progress,
            'stage': stage,
            'error_message': lesson.get('error_message')
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get processing status for lesson {lesson_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get processing status"
        )


@router.get("/{lesson_id}/micro-lessons", response_model=List[MicroLessonResponse])
async def get_micro_lessons(
    lesson_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get all micro-lessons for a specific lesson.

    Returns a list of micro-lessons that belong to the specified lesson.
    Checks S3 cache first before querying database.
    """
    try:
        from ...services.dynamodb import db_service
        from ...services.s3 import s3_service

        # Verify lesson exists and belongs to user
        lesson = await db_service.get_lesson(lesson_id)
        if not lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lesson {lesson_id} not found"
            )

        if lesson.get('user_id') != current_user['user_id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: lesson does not belong to user"
            )

        # Try to get from S3 cache first
        cached_data = await s3_service.get_cached_lesson_data(lesson_id, 'micro_lessons')
        if cached_data:
            logger.info(f"Returning cached micro-lessons for lesson {lesson_id}")
            return cached_data

        # Get real micro-lessons from database
        micro_lessons = await db_service.get_lesson_micro_lessons(lesson_id)

        # Format for response
        formatted_micro_lessons = []
        for idx, ml in enumerate(micro_lessons):
            micro_lesson_response = {
                "micro_lesson_id": ml.get("micro_lesson_id"),
                "lesson_id": ml.get("lesson_id"),
                "title": ml.get("title", ""),
                "content": ml.get("content", ""),
                "summary": ml.get("summary", ""),
                "order": ml.get("sequence_number", 0),
                "estimated_duration_minutes": ml.get("estimated_duration_minutes", 5),
                "key_concepts": ml.get("key_concepts", []),
                "learning_objectives": ml.get("learning_objectives", []),
                "examples": ml.get("examples", []),
                "visual_aids": ml.get("visual_aids", []),
                "quiz": None
            }

            # Get quiz ONLY for the first micro-lesson (sequence_number == 1)
            if ml.get("sequence_number") == 1:
                try:
                    quiz = await db_service.get_micro_lesson_quiz(ml.get("micro_lesson_id"))
                    if quiz:
                        micro_lesson_response["quiz"] = {
                            "quiz_id": quiz.get("quiz_id"),
                            "questions": quiz.get("questions", []),
                            "total_questions": quiz.get("total_questions", 0),
                            "passing_score": quiz.get("passing_score", 0.7)
                        }
                        logger.info(f"Quiz loaded for first micro-lesson: {quiz.get('quiz_id')}")
                except Exception as e:
                    logger.warning(f"Could not load quiz for first micro-lesson: {e}")

            formatted_micro_lessons.append(micro_lesson_response)

        # Cache the formatted micro-lessons to S3 for future requests
        if formatted_micro_lessons:
            try:
                await s3_service.cache_lesson_data(lesson_id, 'micro_lessons', formatted_micro_lessons)
            except Exception as cache_error:
                logger.warning(f"Failed to cache micro-lessons: {cache_error}")

        logger.info(f"Returning {len(formatted_micro_lessons)} micro-lessons for lesson {lesson_id}")
        return formatted_micro_lessons
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get micro-lessons for lesson {lesson_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve micro-lessons"
        )


@router.delete("/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson(
    lesson_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Delete a lesson.

    Removes a lesson and all associated micro-lessons.
    """
    try:
        # Mock implementation - replace with actual database deletion
        logger.info(f"Deleting lesson {lesson_id}")
        return None
    except Exception as e:
        logger.error(f"Failed to delete lesson {lesson_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete lesson"
        )


# Adaptive Learning Endpoint Aliases (for frontend compatibility)

@router.post("/adaptive/initialize")
async def initialize_adaptive_learning(
    request: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Initialize adaptive learning session.

    Alias endpoint that forwards to /api/v1/adaptive/start-lesson for frontend compatibility.
    """
    try:
        from ...services.adaptive_agent import adaptive_agent

        lesson_id = request.get('lesson_id')
        if not lesson_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="lesson_id is required"
            )

        user_id = current_user.get('user_id')
        logger.info(f"Initializing adaptive learning for lesson {lesson_id}, user {user_id}")

        # Start adaptive session
        result = await adaptive_agent.start_adaptive_lesson(user_id, lesson_id)

        # Track session start
        from ...services.dynamodb import db_service
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
            'data': {
                'current_micro_lesson_id': result.get('current_micro_lesson', {}).get('micro_lesson_id'),
                'lesson_id': lesson_id,
                'progress': result.get('progress', 0),
                'next_content_type': 'micro_lesson',
                'difficulty_adjustment': 0,
                'learning_path': [],
                'completed_micro_lessons': []
            },
            'session_id': result['session_id']
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to initialize adaptive learning: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start adaptive learning session: {str(e)}"
        )


@router.post("/adaptive/next-content")
async def get_next_adaptive_content(
    request: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get next adaptive content.

    Alias endpoint that forwards to /api/v1/adaptive/next-micro-lesson for frontend compatibility.
    """
    try:
        from ...services.adaptive_agent import adaptive_agent

        lesson_id = request.get('lesson_id')
        current_micro_lesson_id = request.get('current_micro_lesson_id')
        user_performance = request.get('user_performance', {})

        if not lesson_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="lesson_id is required"
            )

        user_id = current_user.get('user_id')
        logger.info(f"Getting next adaptive content for lesson {lesson_id}, user {user_id}")

        # For now, get the session_id from the lesson (simplified approach)
        # In production, you'd track session_id on the frontend
        from ...services.dynamodb import db_service

        # Get next micro-lesson using adaptive agent
        # Note: This is a simplified version - the adaptive agent expects session_id
        # We'll need to either track it or create a new session
        result = await adaptive_agent.get_next_micro_lesson(
            session_id=f"session_{lesson_id}_{user_id}",  # Temporary session ID
            user_id=user_id,
            previous_performance=user_performance
        )

        return {
            'success': True,
            'data': {
                'content_type': 'micro_lesson',
                'micro_lesson': result.get('micro_lesson'),
                'transition_reason': result.get('reasoning', 'Adaptive learning progression'),
                'progress_update': {
                    'overall_progress': result.get('progress', 0),
                    'micro_lesson_progress': result.get('progress', 0),
                    'estimated_completion_time': 30
                },
                'next_available': True
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get next adaptive content: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load next content: {str(e)}"
        )