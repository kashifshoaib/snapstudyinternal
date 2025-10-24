"""
Chat Router - Agentic Chat Interface with Autonomous Intent Recognition.

This router provides endpoints for the agentic chat system that uses Amazon Bedrock
Agents to autonomously recognize user intent, provide educational assistance, and
engage in natural conversation without requiring special command syntax.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Query, Request
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from decimal import Decimal
import logging
import json
import uuid

from ...services.chat_agent import AgenticChatAgent
from ...services.dynamodb import db_service
from ...middleware.auth_middleware import require_auth
from ...middleware.error_handler import (
    ResourceNotFoundError,
    ValidationError
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize chat agent
chat_agent = AgenticChatAgent()


class ChatMessageRequest(BaseModel):
    """Request model for chat messages."""
    message: str
    lesson_id: Optional[str] = None
    session_id: Optional[str] = None


@router.post("/debug")
async def debug_chat_request(request: Request) -> Dict[str, Any]:
    """Debug endpoint that can handle malformed JSON from UI."""
    try:
        body = await request.body()
        raw_text = body.decode('utf-8')
        logger.info(f"DEBUG: Raw body: {raw_text}")
        
        # Try normal JSON parsing first
        try:
            json_data = json.loads(raw_text)
            return {"status": "success", "parsed_json": json_data}
        except json.JSONDecodeError:
            # Handle malformed JSON by fixing common issues
            try:
                # Fix unquoted keys like {message: "text"} -> {"message": "text"}
                import re
                fixed_json = re.sub(r'(\w+):', r'"\1":', raw_text)
                logger.info(f"DEBUG: Fixed JSON: {fixed_json}")
                
                parsed_data = json.loads(fixed_json)
                logger.info(f"DEBUG: Successfully parsed fixed JSON: {parsed_data}")
                
                return {
                    "status": "fixed_and_parsed",
                    "original": raw_text,
                    "fixed": fixed_json,
                    "parsed": parsed_data
                }
            except Exception as fix_error:
                return {
                    "status": "unfixable",
                    "raw_body": raw_text,
                    "error": str(fix_error)
                }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post(
    "/message",
    summary="Send Message to Autonomous Chat Agent",
    description="""
    Send a message to the autonomous chat agent for educational assistance.

    The agent autonomously:
    - Recognizes user intent from natural language (no commands needed)
    - Provides appropriate response (explanation, summary, quiz, etc.)
    - Maintains conversation context
    - Adapts tone and complexity to user level

    Intent types automatically recognized:
    - SUMMARIZATION: User wants lesson summary
    - EXPLANATION: User wants concept explained
    - QUIZ_REQUEST: User wants to be quizzed
    - PROGRESS_INQUIRY: User wants progress information
    - HELP_REQUEST: User needs general help
    - GENERAL_CHAT: General conversation
    - ENCOURAGEMENT: User needs motivation
    """,
    response_description="Agent response with intent and context"
)
async def send_chat_message(
    request: Request,
    user: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Send a chat message to the autonomous agent.

    Args:
        request: Raw HTTP request (handles malformed JSON from UI)
        user: Authenticated user (optional for anonymous chat)

    Returns:
        Dict containing agent response, recognized intent, and context
    """
    try:
        # Parse the potentially malformed JSON
        body = await request.body()
        raw_text = body.decode('utf-8')
        
        try:
            # Try normal JSON parsing first
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            # Fix malformed JSON (unquoted keys)
            import re
            fixed_json = re.sub(r'(\w+):', r'"\1":', raw_text)
            data = json.loads(fixed_json)
        
        user_id = 'anonymous'
        if user is not None:
            user_id = user.get('user_id', 'anonymous')
        message = data.get('message', '')
        lesson_id = data.get('lesson_id')
        session_id = data.get('session_id')
        
        logger.info(f"Parsed message: '{message}'")

        # Validate message
        if not message or not message.strip():
            raise ValidationError("Message cannot be empty")

        if len(message) > 2000:
            raise ValidationError("Message too long (max 2000 characters)")

        logger.info(f"Chat message from user {user_id}: {message[:100]}...")

        # Build context
        context = {
            'user_id': user_id,
            'user_profile': user
        }

        # Add lesson context if provided
        if lesson_id:
            try:
                lesson = await db_service.get_lesson(lesson_id)
                if lesson:
                    context['current_lesson'] = lesson
            except Exception as e:
                logger.warning(f"Could not load lesson context: {e}")

        # Create or use existing session
        if not session_id:
            session_id = str(uuid.uuid4())
            logger.info(f"Created new chat session: {session_id}")
        else:
            # Load chat history for context
            try:
                history = await db_service.get_chat_session(session_id)
                if history:
                    context['chat_history'] = history.get('messages', [])[-10:]  # Last 10 messages
            except Exception as e:
                logger.warning(f"Could not load chat history: {e}")

        # Process message with autonomous agent
        response = await chat_agent.handle_message(
            user_id=user_id,
            message=message,
            context=context,
            session_id=session_id
        )

        # Store in chat history
        await _store_chat_message(
            session_id=session_id,
            user_id=user_id,
            message=message,
            response=response
        )

        # Track engagement (skip for anonymous users)
        if user_id != 'anonymous':
            try:
                await db_service.track_engagement({
                    'user_id': user_id,
                    'event_type': 'chat_interaction',
                    'event_data': {
                        'session_id': session_id,
                        'intent': response.get('intent'),
                        'confidence': Decimal(str(response.get('confidence', 0.0))),
                        'message_length': len(message)
                    }
                })
            except Exception as e:
                logger.warning(f"Could not track engagement for user {user_id}: {e}")

        return {
            'success': True,
            'session_id': session_id,
            'message': message,
            'response': response.get('response'),
            'intent': response.get('intent'),
            'confidence': Decimal(str(response.get('confidence', 0.0))),
            'autonomous_recognition': response.get('autonomous', True),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to process chat message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat with autonomous agent.

    Protocol:
    - Client sends: {"message": "...", "lesson_id": "...", "user_id": "..."}
    - Server sends: {"response": "...", "intent": "...", "confidence": ...}

    The WebSocket maintains a persistent connection for instant responses
    from the autonomous agent.
    """
    await websocket.accept()
    session_id = str(uuid.uuid4())
    user_id = None

    logger.info(f"WebSocket connection established: session {session_id}")

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({
                    'error': 'Invalid JSON format',
                    'success': False
                })
                continue

            # Extract data
            message = message_data.get('message', '')
            user_id = message_data.get('user_id', 'anonymous')  # Allow anonymous users
            lesson_id = message_data.get('lesson_id')

            if not message:
                await websocket.send_json({
                    'error': 'message required',
                    'success': False
                })
                continue

            logger.info(f"WebSocket message from {user_id}: {message[:100]}...")

            # Build context
            context = {
                'user_id': user_id,
                'websocket': True
            }

            # Add lesson context
            if lesson_id:
                try:
                    lesson = await db_service.get_lesson(lesson_id)
                    if lesson:
                        context['current_lesson'] = lesson
                except Exception as e:
                    logger.warning(f"Could not load lesson: {e}")

            # Get user profile
            try:
                user_profile = await db_service.get_user_by_id(user_id)
                if user_profile:
                    context['user_profile'] = user_profile
            except Exception as e:
                logger.warning(f"Could not load user profile: {e}")

            # Load recent chat history
            try:
                history = await db_service.get_item(
                    'ChatHistory',
                    {'session_id': session_id}
                )
                if history:
                    context['chat_history'] = history.get('messages', [])[-10:]
            except Exception as e:
                logger.warning(f"Could not load chat history: {e}")

            # Process with autonomous agent
            try:
                response = await chat_agent.handle_message(
                    user_id=user_id,
                    message=message,
                    context=context,
                    session_id=session_id
                )

                # Store in chat history
                await _store_chat_message(
                    session_id=session_id,
                    user_id=user_id,
                    message=message,
                    response=response
                )

                # Send response
                await websocket.send_json({
                    'success': True,
                    'session_id': session_id,
                    'response': response.get('response'),
                    'intent': response.get('intent'),
                    'confidence': response.get('confidence', 0.0),
                    'autonomous': response.get('autonomous', True),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })

                # Track engagement
                await db_service.track_engagement({
                    'user_id': user_id,
                    'event_type': 'websocket_chat',
                    'event_data': {
                        'session_id': session_id,
                        'intent': response.get('intent'),
                        'confidence': response.get('confidence', 0.0)
                    }
                })

            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                await websocket.send_json({
                    'success': False,
                    'error': 'Failed to process message',
                    'detail': str(e)
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: session {session_id}, user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass


@router.get(
    "/sessions/{session_id}",
    summary="Get Chat Session History",
    description="""
    Retrieves the complete chat history for a session.

    Returns all messages exchanged with the autonomous agent,
    including recognized intents and responses.
    """,
    response_description="Complete chat session history"
)
async def get_chat_session(
    session_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    user: Dict[str, Any] = Depends(require_auth)
) -> Dict[str, Any]:
    """
    Get chat session history.

    Args:
        session_id: Chat session ID
        limit: Maximum number of messages to return
        user: Authenticated user

    Returns:
        Dict containing chat history
    """
    try:
        user_id = user.get('user_id')

        logger.info(f"Retrieving chat session {session_id} for user {user_id}")

        # Get chat history
        history = await db_service.get_item(
            'ChatHistory',
            {'session_id': session_id}
        )

        if not history:
            return {
                'success': True,
                'session_id': session_id,
                'messages': [],
                'message_count': 0
            }

        # Verify user owns this session
        if history.get('user_id') != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this chat session"
            )

        # Limit messages
        messages = history.get('messages', [])[-limit:]

        return {
            'success': True,
            'session_id': session_id,
            'user_id': user_id,
            'messages': messages,
            'message_count': len(messages),
            'created_at': history.get('created_at'),
            'updated_at': history.get('updated_at')
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve chat session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chat session: {str(e)}"
        )


@router.post(
    "/sessions/{session_id}/clear",
    summary="Clear Chat Session History",
    description="""
    Clears the chat history for a session.

    Useful for starting fresh or resetting context.
    The session ID remains valid for new messages.
    """,
    response_description="Confirmation of cleared session"
)
async def clear_chat_session(
    session_id: str,
    user: Dict[str, Any] = Depends(require_auth)
) -> Dict[str, Any]:
    """
    Clear chat session history.

    Args:
        session_id: Chat session ID to clear
        user: Authenticated user

    Returns:
        Dict containing confirmation
    """
    try:
        user_id = user.get('user_id')

        logger.info(f"Clearing chat session {session_id} for user {user_id}")

        # Get existing history to verify ownership
        history = await db_service.get_item(
            'ChatHistory',
            {'session_id': session_id}
        )

        if history and history.get('user_id') != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this chat session"
            )

        # Update with empty messages
        await db_service.put_item('ChatHistory', {
            'session_id': session_id,
            'user_id': user_id,
            'messages': [],
            'created_at': history.get('created_at') if history else datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'ttl': int((datetime.now(timezone.utc).timestamp() + 86400 * 90))  # 90 days
        })

        # Track engagement
        await db_service.track_engagement({
            'user_id': user_id,
            'event_type': 'chat_session_cleared',
            'event_data': {
                'session_id': session_id
            }
        })

        return {
            'success': True,
            'session_id': session_id,
            'message': 'Chat session cleared successfully'
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear chat session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear chat session: {str(e)}"
        )


@router.get(
    "/sessions",
    summary="List User's Chat Sessions",
    description="""
    Lists all chat sessions for the authenticated user.

    Returns basic information about each session including
    message count and last activity.
    """,
    response_description="List of chat sessions"
)
async def list_chat_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    user: Dict[str, Any] = Depends(require_auth)
) -> Dict[str, Any]:
    """
    List user's chat sessions.

    Args:
        limit: Maximum number of sessions to return
        user: Authenticated user

    Returns:
        Dict containing list of sessions
    """
    try:
        user_id = user.get('user_id')

        logger.info(f"Listing chat sessions for user {user_id}")

        # Query chat sessions
        sessions = await db_service.query_items(
            table_name='ChatHistory',
            index_name='UserChatHistoryIndex',
            key_condition={
                'user_id': user_id
            },
            limit=limit,
            scan_index_forward=False  # Most recent first
        )

        # Format session summaries
        session_list = []
        for session in sessions:
            messages = session.get('messages', [])
            session_list.append({
                'session_id': session.get('session_id'),
                'message_count': len(messages),
                'created_at': session.get('created_at'),
                'updated_at': session.get('updated_at'),
                'last_message_preview': messages[-1].get('user_message', '')[:100] if messages else None
            })

        return {
            'success': True,
            'user_id': user_id,
            'sessions': session_list,
            'total_count': len(session_list)
        }

    except Exception as e:
        logger.error(f"Failed to list chat sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list chat sessions: {str(e)}"
        )


@router.get(
    "/intents",
    summary="Get Supported Intent Types",
    description="""
    Returns information about all intent types the autonomous agent can recognize.

    Useful for understanding what the agent can help with.
    """,
    response_description="List of supported intents"
)
async def get_supported_intents() -> Dict[str, Any]:
    """
    Get list of supported intent types.

    Returns:
        Dict containing intent types and descriptions
    """
    intents = {
        'SUMMARIZATION': {
            'description': 'User wants a summary of lesson content',
            'examples': ['Summarize this lesson', 'What are the main points?', 'Give me an overview']
        },
        'EXPLANATION': {
            'description': 'User wants a concept explained',
            'examples': ['Explain X', 'What does Y mean?', 'How does Z work?']
        },
        'QUIZ_REQUEST': {
            'description': 'User wants to be quizzed on the material',
            'examples': ['Quiz me', 'Test my knowledge', 'Can I have some practice questions?']
        },
        'PROGRESS_INQUIRY': {
            'description': 'User wants to know their progress',
            'examples': ['How am I doing?', 'What\'s my progress?', 'Show my stats']
        },
        'HELP_REQUEST': {
            'description': 'User needs help or is stuck',
            'examples': ['I need help', 'I\'m stuck', 'I don\'t understand']
        },
        'GENERAL_CHAT': {
            'description': 'General conversation or questions',
            'examples': ['Hello', 'Thank you', 'How are you?']
        },
        'ENCOURAGEMENT': {
            'description': 'User needs motivation or is expressing difficulty',
            'examples': ['This is hard', 'I\'m struggling', 'I can\'t do this']
        }
    }

    return {
        'success': True,
        'intents': intents,
        'total_intents': len(intents),
        'autonomous_recognition': True,
        'note': 'Agent automatically recognizes intent - no special commands needed'
    }


# Helper function
async def _store_chat_message(
    session_id: str,
    user_id: str,
    message: str,
    response: Dict[str, Any]
) -> None:
    """
    Store chat message in history.

    Args:
        session_id: Chat session ID
        user_id: User ID
        message: User's message
        response: Agent's response
    """
    try:
        # Get existing history
        history = await db_service.get_chat_session(session_id)

        # Create message entry
        message_entry = {
            'user_message': message,
            'agent_response': response.get('response'),
            'intent': response.get('intent'),
            'confidence': Decimal(str(response.get('confidence', 0.0))),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        if history:
            # Append to existing messages
            messages = history.get('messages', [])
            messages.append(message_entry)

            # Keep only last 100 messages
            if len(messages) > 100:
                messages = messages[-100:]

            await db_service.update_chat_session(session_id, {
                'messages': messages,
                'updated_at': datetime.now(timezone.utc).isoformat()
            })
        else:
            # Create new history
            await db_service.create_chat_session({
                'session_id': session_id,
                'user_id': user_id,
                'messages': [message_entry]
            })

    except Exception as e:
        logger.error(f"Failed to store chat message: {e}")
        # Don't raise - message processing succeeded even if storage failed
