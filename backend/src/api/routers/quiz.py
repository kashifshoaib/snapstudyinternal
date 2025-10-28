"""Quiz router."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging

from ...services.dynamodb import db_service
from ...services.bedrock import bedrock_service
from ...middleware.auth_middleware import require_auth

logger = logging.getLogger(__name__)
router = APIRouter()


class QuizGenerateRequest(BaseModel):
    """Request model for quiz generation."""
    micro_lesson_id: str
    target_difficulty: Optional[str] = "intermediate"
    num_questions: Optional[int] = 5


class QuizResponse(BaseModel):
    """Response model for quiz."""
    quiz_id: str
    micro_lesson_id: str
    lesson_id: str
    questions: List[Dict[str, Any]]
    total_questions: int
    passing_score: float
    difficulty_level: str
    estimated_duration_minutes: int


class ImmediateFeedbackRequest(BaseModel):
    """Request model for immediate feedback."""
    quiz_id: str
    question_id: str
    user_answer: str


class QuestionProgressRequest(BaseModel):
    """Request model for question progress tracking."""
    quiz_id: str
    question_id: str
    time_spent_seconds: float
    attempts: int = 1


class QuizSubmitRequest(BaseModel):
    """Request model for quiz submission."""
    quiz_id: str
    answers: Dict[str, str]
    time_spent_seconds: int
    engagement_metrics: Optional[Dict[str, Any]] = None


class HintRequest(BaseModel):
    """Request model for hint."""
    quiz_id: str
    question_id: str
    struggle_context: str
    previous_answers: List[str] = []


@router.post("/generate", response_model=QuizResponse)
async def generate_quiz(
    request: QuizGenerateRequest,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Generate a new quiz for a specific micro-lesson.

    - Checks if quiz already exists for the micro-lesson
    - If exists, returns existing quiz
    - If not, generates new quiz using AI
    - Stores quiz in database
    """
    try:
        logger.info(f"Quiz generation requested for micro-lesson: {request.micro_lesson_id}")

        # Check for existing quiz
        existing_quiz = await db_service.get_micro_lesson_quiz(request.micro_lesson_id)
        if existing_quiz:
            logger.info(f"✅ Using existing quiz: {existing_quiz.get('quiz_id')}")
            return QuizResponse(
                quiz_id=existing_quiz.get('quiz_id'),
                micro_lesson_id=existing_quiz.get('micro_lesson_id'),
                lesson_id=existing_quiz.get('lesson_id'),
                questions=existing_quiz.get('questions', []),
                total_questions=existing_quiz.get('total_questions', len(existing_quiz.get('questions', []))),
                passing_score=existing_quiz.get('passing_score', 0.7),
                difficulty_level=existing_quiz.get('difficulty_level', request.target_difficulty),
                estimated_duration_minutes=existing_quiz.get('estimated_duration_minutes', request.num_questions * 2)
            )

        # Get micro-lesson data
        micro_lesson = await db_service.get_micro_lesson(request.micro_lesson_id)
        if not micro_lesson:
            raise HTTPException(status_code=404, detail="Micro-lesson not found")

        lesson_id = micro_lesson.get('lesson_id')

        # Generate new quiz using Bedrock
        logger.info(f"🎯 Generating new quiz with {request.num_questions} questions at {request.target_difficulty} difficulty")

        quiz_data = await bedrock_service.generate_quiz(
            lesson_content=micro_lesson.get('content', ''),
            difficulty_level=request.target_difficulty,
            num_questions=request.num_questions,
            key_concepts=micro_lesson.get('key_concepts', [])
        )

        # Store quiz in database
        quiz_record = await db_service.create_quiz({
            'micro_lesson_id': request.micro_lesson_id,
            'lesson_id': lesson_id,
            'questions': quiz_data.get('questions', []),
            'total_questions': len(quiz_data.get('questions', [])),
            'passing_score': quiz_data.get('passing_score', 0.7),
            'difficulty_level': request.target_difficulty,
            'estimated_duration_minutes': len(quiz_data.get('questions', [])) * 2,
            'quiz_metadata': {
                'generated_by': 'bedrock',
                'user_id': current_user.get('user_id'),
                'target_difficulty': request.target_difficulty,
                'num_questions_requested': request.num_questions
            }
        })

        logger.info(f"✅ Quiz generated and stored successfully: {quiz_record.get('quiz_id')}")

        return QuizResponse(
            quiz_id=quiz_record.get('quiz_id'),
            micro_lesson_id=quiz_record.get('micro_lesson_id'),
            lesson_id=quiz_record.get('lesson_id'),
            questions=quiz_record.get('questions', []),
            total_questions=quiz_record.get('total_questions'),
            passing_score=quiz_record.get('passing_score', 0.7),
            difficulty_level=quiz_record.get('difficulty_level'),
            estimated_duration_minutes=quiz_record.get('estimated_duration_minutes')
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate quiz: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate quiz: {str(e)}"
        )


@router.post("/immediate-feedback")
async def get_immediate_feedback(
    request: ImmediateFeedbackRequest,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get immediate feedback for a quiz answer.

    Returns feedback on whether the answer is correct and explanation.
    """
    try:
        logger.info(f"Immediate feedback requested for quiz {request.quiz_id}, question {request.question_id}")

        # Get the quiz
        quiz = await db_service.get_quiz(request.quiz_id)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        # Find the question
        question = None
        for q in quiz.get('questions', []):
            if q.get('id') == request.question_id or q.get('question_id') == request.question_id:
                question = q
                break

        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        # Check if answer is correct
        correct_answer = question.get('correct_answer', '')
        is_correct = request.user_answer.strip().lower() == correct_answer.strip().lower()

        # Get detailed feedback using AI
        try:
            feedback = await bedrock_service.evaluate_quiz_answer(question, request.user_answer)

            return {
                "is_correct": is_correct,
                "show_immediate_feedback": True,
                "feedback_text": feedback.get('feedback', ''),
                "explanation": question.get('explanation', ''),
                "score": feedback.get('score', 1.0 if is_correct else 0.0)
            }
        except Exception as e:
            logger.warning(f"Failed to get AI feedback: {e}, using basic feedback")
            # Fallback to basic feedback
            return {
                "is_correct": is_correct,
                "show_immediate_feedback": True,
                "feedback_text": "Correct!" if is_correct else "Not quite right. Try again!",
                "explanation": question.get('explanation', ''),
                "score": 1.0 if is_correct else 0.0
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get immediate feedback: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get feedback: {str(e)}"
        )


@router.post("/question-progress")
async def track_question_progress(
    request: QuestionProgressRequest,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Track user's progress on a specific question.

    Records time spent and number of attempts.
    """
    try:
        logger.info(f"Tracking progress for quiz {request.quiz_id}, question {request.question_id}")

        # Store progress in engagement metrics
        # This could be stored in DynamoDB for analytics
        progress_data = {
            'user_id': current_user['user_id'],
            'quiz_id': request.quiz_id,
            'question_id': request.question_id,
            'time_spent_seconds': request.time_spent_seconds,
            'attempts': request.attempts,
            'timestamp': __import__('datetime').datetime.utcnow().isoformat()
        }

        # Log for now (could be stored in DB for analytics)
        logger.info(f"Question progress: {progress_data}")

        return {
            "success": True,
            "message": "Progress tracked successfully"
        }

    except Exception as e:
        logger.error(f"Failed to track question progress: {str(e)}", exc_info=True)
        # Don't raise error - progress tracking is non-critical
        return {
            "success": False,
            "message": "Failed to track progress"
        }


@router.post("/submit")
async def submit_quiz(
    request: QuizSubmitRequest,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Submit a completed quiz and get results.

    Evaluates all answers and returns detailed results with feedback.
    """
    try:
        logger.info(f"Quiz submission for quiz {request.quiz_id} by user {current_user['user_id']}")

        # Get the quiz
        quiz = await db_service.get_quiz(request.quiz_id)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        # Evaluate all answers
        question_results = []
        correct_count = 0
        total_score = 0

        for question in quiz.get('questions', []):
            question_id = question.get('id') or question.get('question_id')
            user_answer = request.answers.get(question_id, '')
            correct_answer = question.get('correct_answer', '')

            # Check if correct
            is_correct = user_answer.strip().lower() == correct_answer.strip().lower()

            if is_correct:
                correct_count += 1

            # Get detailed evaluation
            try:
                evaluation = await bedrock_service.evaluate_quiz_answer(question, user_answer)
                score = evaluation.get('score', 1.0 if is_correct else 0.0)
                feedback = evaluation.get('feedback', '')
            except Exception as e:
                logger.warning(f"Failed to get AI evaluation for question {question_id}: {e}")
                score = 1.0 if is_correct else 0.0
                feedback = "Correct!" if is_correct else f"Incorrect. The correct answer is: {correct_answer}"

            total_score += score

            question_results.append({
                "question_id": question_id,
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "score": score,
                "feedback": feedback,
                "suggestions": question.get('explanation', '')
            })

        # Calculate overall score
        total_questions = len(quiz.get('questions', []))
        overall_score = (total_score / total_questions) if total_questions > 0 else 0
        passing_score = quiz.get('passing_score', 0.7)
        passed = overall_score >= passing_score

        # Store quiz results
        quiz_result = {
            'quiz_id': request.quiz_id,
            'user_id': current_user['user_id'],
            'answers': request.answers,
            'overall_score': overall_score,
            'correct_count': correct_count,
            'total_questions': total_questions,
            'time_spent_seconds': request.time_spent_seconds,
            'passed': passed,
            'engagement_metrics': request.engagement_metrics or {},
            'submitted_at': __import__('datetime').datetime.utcnow().isoformat()
        }

        # Save to database (if needed for analytics)
        try:
            await db_service.save_quiz_result(quiz_result)
        except Exception as e:
            logger.warning(f"Failed to save quiz result to DB: {e}")

        # Generate recommendations if failed
        recommendations = []
        if not passed:
            recommendations.append("Review the material and try again")
            recommendations.append("Focus on the questions you got wrong")
            if overall_score < 0.5:
                recommendations.append("Consider reviewing the lesson content before retaking")

        logger.info(f"Quiz submitted: score={overall_score:.2f}, passed={passed}")

        return {
            "quiz_id": request.quiz_id,
            "overall_score": overall_score,
            "total_questions": total_questions,
            "correct_count": correct_count,
            "time_spent_seconds": request.time_spent_seconds,
            "question_results": question_results,
            "passed": passed,
            "feedback": f"You scored {overall_score*100:.1f}%. " + ("Great job!" if passed else "Keep practicing!"),
            "recommendations": recommendations
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit quiz: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit quiz: {str(e)}"
        )


@router.post("/hint")
async def get_hint(
    request: HintRequest,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """
    Get a hint for a quiz question.

    Provides contextual help without giving away the answer.
    """
    try:
        logger.info(f"Hint requested for quiz {request.quiz_id}, question {request.question_id}")

        # Get the quiz
        quiz = await db_service.get_quiz(request.quiz_id)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")

        # Find the question
        question = None
        for q in quiz.get('questions', []):
            if q.get('id') == request.question_id or q.get('question_id') == request.question_id:
                question = q
                break

        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        # Generate hint using AI
        try:
            hint_prompt = f"""
            Generate a helpful hint for this quiz question without revealing the answer directly.

            Question: {question.get('question') or question.get('question_text')}
            Options: {question.get('options', [])}
            Student's struggle: {request.struggle_context}
            Previous attempts: {request.previous_answers}

            Provide a hint that guides the student's thinking without giving away the answer.
            """

            hint_text = await bedrock_service.invoke_claude(
                hint_prompt,
                max_tokens=200,
                temperature=0.7,
                system_prompt="You are a helpful tutor providing hints to students."
            )

            return {
                "hint_text": hint_text.strip(),
                "hint_type": "contextual",
                "question_id": request.question_id
            }

        except Exception as e:
            logger.warning(f"Failed to generate AI hint: {e}, using fallback")
            # Fallback hint
            return {
                "hint_text": "Think about the key concepts from the lesson. Review the material if needed.",
                "hint_type": "general",
                "question_id": request.question_id
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get hint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get hint: {str(e)}"
        )