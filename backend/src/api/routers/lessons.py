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
    order: int
    estimated_duration_minutes: int


@router.get("/", response_model=List[LessonResponse])
async def get_lessons(current_user: Dict[str, Any] = Depends(require_auth)):
    """
    Get all lessons for the current user.

    Returns a list of lessons owned by the authenticated user.
    """
    try:
        # Get real lessons from database
        from ...services.dynamodb import db_service
        user_lessons = await db_service.get_user_lessons(current_user["user_id"])
        
        # Format lessons for response
        formatted_lessons = []
        for lesson in user_lessons:
            formatted_lessons.append({
                "lesson_id": lesson["lesson_id"],
                "title": lesson["title"],
                "subject": lesson.get("subject", "General"),
                "created_at": lesson["created_at"],
                "status": lesson.get("status", "active"),
                "difficulty": lesson.get("difficulty", "intermediate")
            })
        
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
    """
    try:
        # Validate file type
        allowed_types = ['.pdf', '.docx', '.txt', '.doc']
        file_ext = '.' + file.filename.split('.')[-1].lower()

        if file_ext not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not supported. Allowed types: {', '.join(allowed_types)}"
            )

        # Read file content
        content = await file.read()
        file_content = content.decode('utf-8') if file_ext in ['.txt'] else f"Uploaded file: {file.filename}"
        
        # Create lesson data for database
        lesson_data = {
            "user_id": current_user["user_id"],
            "title": file.filename.rsplit('.', 1)[0],
            "subject": "General",
            "content": file_content,
            "difficulty": "intermediate",
            "status": "active",
            "file_type": file_ext,
            "original_filename": file.filename
        }
        
        # Save to database
        from ...services.dynamodb import db_service
        created_lesson = await db_service.create_lesson(lesson_data)
        
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
        # Mock data - replace with actual database query
        mock_lesson = {
            "lesson_id": lesson_id,
            "title": "Sample Lesson",
            "subject": "General",
            "created_at": "2025-10-20T12:00:00Z",
            "status": "active",
            "difficulty": "intermediate"
        }
        return mock_lesson
    except Exception as e:
        logger.error(f"Failed to get lesson {lesson_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lesson {lesson_id} not found"
        )


@router.get("/{lesson_id}/micro-lessons", response_model=List[MicroLessonResponse])
async def get_micro_lessons(
    lesson_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get all micro-lessons for a specific lesson.

    Returns a list of micro-lessons that belong to the specified lesson.
    """
    try:
        # Mock data - replace with actual database query
        mock_micro_lessons = [
            {
                "micro_lesson_id": "ml-1",
                "lesson_id": lesson_id,
                "title": "Introduction",
                "content": "This is the introduction content...",
                "order": 1,
                "estimated_duration_minutes": 5
            },
            {
                "micro_lesson_id": "ml-2",
                "lesson_id": lesson_id,
                "title": "Core Concepts",
                "content": "These are the core concepts...",
                "order": 2,
                "estimated_duration_minutes": 10
            },
            {
                "micro_lesson_id": "ml-3",
                "lesson_id": lesson_id,
                "title": "Practice Exercises",
                "content": "Practice what you learned...",
                "order": 3,
                "estimated_duration_minutes": 15
            }
        ]
        return mock_micro_lessons
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