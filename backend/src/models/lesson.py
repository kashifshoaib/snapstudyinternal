"""Lesson and content data models."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ContentType(str, Enum):
    PDF = "pdf"
    AUDIO = "audio"
    VIDEO = "video"
    TEXT = "text"
    YOUTUBE = "youtube"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class LessonStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Lesson(BaseModel):
    """Main lesson model."""
    lesson_id: str
    user_id: str
    title: str
    description: Optional[str] = None
    content_type: ContentType
    original_content_url: Optional[str] = None
    s3_content_key: Optional[str] = None
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    status: LessonStatus = LessonStatus.DRAFT
    total_micro_lessons: int = 0
    completed_micro_lessons: int = 0
    estimated_duration_minutes: Optional[int] = None
    difficulty_level: str = "intermediate"
    learning_objectives: List[str] = []
    prerequisites: List[str] = []
    created_at: datetime
    updated_at: datetime
    ttl: Optional[int] = None  # For automatic cleanup


class MicroLesson(BaseModel):
    """Individual micro-lesson model."""
    micro_lesson_id: str
    lesson_id: str
    sequence_number: int
    title: str
    content: str
    summary: str
    key_concepts: List[str] = []
    estimated_duration_minutes: int = Field(..., ge=1, le=30)
    difficulty_level: str = "intermediate"
    learning_objectives: List[str] = []
    is_completed: bool = False
    created_at: datetime
    updated_at: datetime


class Quiz(BaseModel):
    """Quiz model for micro-lessons."""
    quiz_id: str
    micro_lesson_id: str
    questions: List[Dict[str, Any]]  # Will contain question objects
    total_questions: int
    passing_score: float = 0.7
    time_limit_minutes: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class QuizQuestion(BaseModel):
    """Individual quiz question model."""
    question_id: str
    question_type: str  # "multiple_choice", "true_false", "short_answer"
    question_text: str
    options: Optional[List[str]] = None  # For multiple choice
    correct_answer: str
    explanation: str
    difficulty: str = "medium"
    points: int = 1


class QuizAttempt(BaseModel):
    """Quiz attempt tracking model."""
    attempt_id: str
    quiz_id: str
    user_id: str
    answers: Dict[str, str]  # question_id -> user_answer
    score: float
    total_questions: int
    correct_answers: int
    time_taken_seconds: int
    completed_at: datetime
    feedback: Optional[str] = None


class ContentUpload(BaseModel):
    """Content upload request model."""
    title: str
    description: Optional[str] = None
    content_type: ContentType
    file_url: Optional[str] = None  # For YouTube URLs
    learning_objectives: Optional[List[str]] = None


class LessonProgress(BaseModel):
    """Lesson progress tracking model."""
    lesson_id: str
    user_id: str
    current_micro_lesson: int = 0
    completed_micro_lessons: List[str] = []
    quiz_scores: Dict[str, float] = {}  # micro_lesson_id -> best_score
    total_time_spent_minutes: int = 0
    completion_percentage: float = 0.0
    last_accessed: datetime
    updated_at: datetime