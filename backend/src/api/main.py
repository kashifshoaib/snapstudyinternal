"""Main FastAPI application for SnapStudy backend."""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

import logging
import time
import uuid

from ..config import settings
from ..services.auth import auth_service
from ..services.dynamodb import db_service
from .routers import auth, users, lessons, content, ai_services, adaptive, quiz, chat, analytics, multimedia, health

# Import middleware and error handlers
from ..middleware.error_handler import (
    SnapStudyException,
    snapstudy_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)
# Removed complex security middleware imports

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="SnapStudy API",
    description="Backend API for SnapStudy adaptive learning platform with comprehensive error handling and security",
    version=settings.api_version,
    docs_url="/docs" if settings.api_version != "production" else None,
    redoc_url="/redoc" if settings.api_version != "production" else None
)

# Add exception handlers
app.add_exception_handler(SnapStudyException, snapstudy_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Add simple CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Removed dependencies import

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(lessons.router, prefix="/api/v1/lessons", tags=["Lessons"])
app.include_router(content.router, prefix="/api/v1/content", tags=["Content"])
app.include_router(ai_services.router, prefix="/api/v1/ai", tags=["AI Services"])
app.include_router(adaptive.router, prefix="/api/v1/adaptive", tags=["Adaptive Learning"])
app.include_router(quiz.router, prefix="/api/v1/quiz", tags=["Quiz System"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Agentic Chat"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Learning Analytics"])
app.include_router(multimedia.router, prefix="/api/v1/multimedia", tags=["Multimedia Generation"])
app.include_router(health.router, prefix="/api/v1/health", tags=["Health Monitoring"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "SnapStudy API",
        "version": settings.api_version,
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": time.time()}

@app.get("/health")
async def health_check():
    """Enhanced health check endpoint with system status."""
    from datetime import datetime
    import sys
    import os

    try:
        # Check database connectivity
        db_status = "healthy"
        try:
            db_service.health_check()
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"

        # Check AWS services
        aws_status = "healthy"
        try:
            # Basic AWS connectivity check
            import boto3
            sts = boto3.client('sts')
            sts.get_caller_identity()
        except Exception as e:
            aws_status = f"unhealthy: {str(e)}"

        health_data = {
            "status": "healthy" if db_status == "healthy" and aws_status == "healthy" else "degraded",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "version": settings.api_version,
            "environment": os.getenv("ENVIRONMENT", "development"),
            "python_version": sys.version,
            "services": {
                "database": db_status,
                "aws": aws_status
            },
            "uptime_seconds": time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0
        }

        return health_data

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(e)
        }


@app.get("/api-docs")
async def api_documentation():
    """
    Comprehensive API documentation endpoint.

    Returns detailed information about all available API endpoints,
    request/response models, and usage examples.
    """
    return {
        "api_name": "SnapStudy API",
        "version": settings.api_version,
        "description": "Backend API for SnapStudy adaptive learning platform",
        "base_url": "/api/v1",
        "authentication": {
            "type": "Bearer Token",
            "description": "Include the access token in the Authorization header",
            "example": "Authorization: Bearer <your-access-token>"
        },
        "endpoints": {
            "authentication": {
                "base_path": "/api/v1/auth",
                "endpoints": [
                    {
                        "method": "POST",
                        "path": "/login",
                        "description": "Authenticate user with email and password",
                        "requires_auth": False,
                        "request_body": {
                            "email": "string (email)",
                            "password": "string"
                        },
                        "response": {
                            "access_token": "string",
                            "token_type": "bearer",
                            "user": "object"
                        }
                    },
                    {
                        "method": "POST",
                        "path": "/register",
                        "description": "Register a new user account",
                        "requires_auth": False,
                        "request_body": {
                            "email": "string (email)",
                            "password": "string",
                            "first_name": "string",
                            "last_name": "string"
                        }
                    },
                    {
                        "method": "POST",
                        "path": "/logout",
                        "description": "Logout and invalidate session",
                        "requires_auth": True
                    }
                ]
            },
            "lessons": {
                "base_path": "/api/v1/lessons",
                "endpoints": [
                    {
                        "method": "GET",
                        "path": "/",
                        "description": "Get all lessons for the authenticated user",
                        "requires_auth": True,
                        "response": "array of lesson objects"
                    },
                    {
                        "method": "POST",
                        "path": "/upload",
                        "description": "Upload a new lesson file (PDF, DOCX, TXT)",
                        "requires_auth": True,
                        "content_type": "multipart/form-data",
                        "request_body": {
                            "file": "file upload"
                        }
                    },
                    {
                        "method": "GET",
                        "path": "/{lesson_id}",
                        "description": "Get a specific lesson by ID",
                        "requires_auth": True,
                        "path_params": {
                            "lesson_id": "string"
                        }
                    },
                    {
                        "method": "GET",
                        "path": "/{lesson_id}/micro-lessons",
                        "description": "Get all micro-lessons for a specific lesson",
                        "requires_auth": True,
                        "path_params": {
                            "lesson_id": "string"
                        }
                    },
                    {
                        "method": "DELETE",
                        "path": "/{lesson_id}",
                        "description": "Delete a lesson and all associated micro-lessons",
                        "requires_auth": True,
                        "path_params": {
                            "lesson_id": "string"
                        }
                    }
                ]
            },
            "analytics": {
                "base_path": "/api/v1/analytics",
                "endpoints": [
                    {
                        "method": "GET",
                        "path": "/dashboard",
                        "description": "Get comprehensive analytics dashboard data",
                        "requires_auth": True,
                        "response": {
                            "metrics": "object (lessons_completed, quizzes_taken, average_score, total_time_spent_minutes)",
                            "retention": "object (current_streak, longest_streak, retention_rate, consistency_score)",
                            "learning_patterns": "array of strings",
                            "generated_at": "ISO 8601 timestamp"
                        }
                    },
                    {
                        "method": "GET",
                        "path": "/velocity",
                        "description": "Get learning velocity metrics",
                        "requires_auth": True,
                        "query_params": {
                            "period": "integer (days, default: 7)"
                        },
                        "response": {
                            "learning_pace": "string (fast, moderate, slow)",
                            "daily_averages": "object",
                            "activity_score": "float"
                        }
                    },
                    {
                        "method": "GET",
                        "path": "/struggling-concepts",
                        "description": "Get concepts the user is struggling with",
                        "requires_auth": True,
                        "response": {
                            "struggling_concepts": "array of concept objects"
                        }
                    },
                    {
                        "method": "GET",
                        "path": "/recommendations",
                        "description": "Get personalized learning recommendations",
                        "requires_auth": True,
                        "response": {
                            "recommendations": "array of recommendation objects"
                        }
                    },
                    {
                        "method": "POST",
                        "path": "/track-event",
                        "description": "Track a learning event for analytics",
                        "requires_auth": True,
                        "request_body": {
                            "event_name": "string",
                            "event_data": "object"
                        }
                    }
                ]
            },
            "users": {
                "base_path": "/api/v1/users",
                "description": "User profile and settings management"
            },
            "content": {
                "base_path": "/api/v1/content",
                "description": "Content generation and management"
            },
            "ai_services": {
                "base_path": "/api/v1/ai",
                "description": "AI-powered learning features"
            },
            "adaptive": {
                "base_path": "/api/v1/adaptive",
                "description": "Adaptive learning algorithms"
            },
            "quiz": {
                "base_path": "/api/v1/quiz",
                "description": "Quiz generation and management"
            },
            "chat": {
                "base_path": "/api/v1/chat",
                "description": "Agentic chat and study buddy"
            },
            "multimedia": {
                "base_path": "/api/v1/multimedia",
                "description": "Multimedia content generation"
            }
        },
        "error_handling": {
            "description": "All errors follow a standard format",
            "format": {
                "detail": "string (error message)",
                "status_code": "integer (HTTP status code)"
            },
            "common_status_codes": {
                "200": "Success",
                "201": "Created",
                "204": "No Content",
                "400": "Bad Request",
                "401": "Unauthorized",
                "403": "Forbidden",
                "404": "Not Found",
                "500": "Internal Server Error"
            }
        },
        "rate_limits": {
            "requests_per_minute": 100,
            "requests_per_hour": 2000,
            "burst_limit": 20
        },
        "swagger_ui": "/docs" if settings.api_version != "production" else "Disabled in production",
        "redoc": "/redoc" if settings.api_version != "production" else "Disabled in production"
    }

@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    import time
    app.state.start_time = time.time()
    logger.info("SnapStudy API starting up...")
    
    # Initialize services
    try:
        db_service.initialize()
        logger.info("Database service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database service: {str(e)}")
    
    logger.info("SnapStudy API startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("SnapStudy API shutting down...")
    
    # Cleanup resources
    try:
        db_service.cleanup()
        logger.info("Database service cleanup complete")
    except Exception as e:
        logger.error(f"Error during database cleanup: {str(e)}")
    
    logger.info("SnapStudy API shutdown complete")

# Container/Server deployment - no Lambda handler needed