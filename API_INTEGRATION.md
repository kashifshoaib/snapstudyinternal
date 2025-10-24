# SnapStudy API Integration Guide

## Overview

This document explains how the SnapStudy frontend and backend APIs are integrated, and how to configure the application for different deployment scenarios.

## Architecture

### Frontend (React + TypeScript)
- **Location**: `frontend/src/services/`
- **API Client**: Axios-based service with automatic authentication
- **Services**:
  - `api.ts` - Base API configuration and interceptors
  - `authService.ts` - Authentication (login, register, logout)
  - `lessonService.ts` - Lesson management and uploads
  - `analyticsService.ts` - Learning analytics and tracking
  - `profileService.ts` - Guest user authentication via profile.json

### Backend (FastAPI + Python)
- **Location**: `backend/src/api/`
- **Framework**: FastAPI with automatic OpenAPI documentation
- **Base URL**: `/api/v1`
- **Authentication**: Bearer token (JWT)

## API Endpoints

### Authentication (`/api/v1/auth`)

#### POST /login
Authenticate user with email and password.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "user-123",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

#### POST /register
Register a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "first_name": "John",
  "last_name": "Doe"
}
```

### Lessons (`/api/v1/lessons`)

#### GET /
Get all lessons for the authenticated user.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
[
  {
    "lesson_id": "lesson-1",
    "title": "Introduction to Python",
    "subject": "Programming",
    "created_at": "2025-10-15T10:00:00Z",
    "status": "active",
    "difficulty": "beginner"
  }
]
```

#### POST /upload
Upload a new lesson file (PDF, DOCX, TXT).

**Headers:**
- `Authorization: Bearer <token>`
- `Content-Type: multipart/form-data`

**Form Data:** `file: <lesson-file>`

#### GET /{lesson_id}/micro-lessons
Get all micro-lessons for a specific lesson.

**Response:**
```json
[
  {
    "micro_lesson_id": "ml-1",
    "lesson_id": "lesson-1",
    "title": "Introduction",
    "content": "Content here...",
    "order": 1,
    "estimated_duration_minutes": 5
  }
]
```

### Analytics (`/api/v1/analytics`)

#### GET /dashboard
Get comprehensive analytics dashboard data.

**Response:**
```json
{
  "metrics": {
    "lessons_completed": 12,
    "quizzes_taken": 8,
    "average_score": 85.5,
    "total_time_spent_minutes": 240
  },
  "retention": {
    "current_streak": 5,
    "longest_streak": 12,
    "retention_rate": 78.0,
    "consistency_score": 82.0
  },
  "learning_patterns": ["visual_learner", "morning_study"],
  "generated_at": "2025-10-21T12:00:00Z"
}
```

#### GET /velocity?period={days}
Get learning velocity metrics over a time period.

**Query Params:** `period` (integer, default: 7 days)

#### GET /struggling-concepts
Get concepts the user is struggling with.

#### GET /recommendations
Get personalized learning recommendations.

#### POST /track-event
Track a learning event for analytics.

**Request:**
```json
{
  "event_name": "quiz_completed",
  "event_data": {
    "quizId": "quiz-123",
    "score": 85,
    "timeSpent": 120
  }
}
```

## Configuration

### Frontend Configuration

**File**: `frontend/src/config/index.ts`

Update the `API_BASE_URL` constant or set the `REACT_APP_API_URL` environment variable:

```typescript
// Option 1: Update the constant
const API_BASE_URL = 'https://your-api-domain.com';

// Option 2: Use environment variable
// .env file
REACT_APP_API_URL=https://your-api-domain.com
```

### Backend API Toggle

The analytics service has a flag to enable/disable backend API usage:

**File**: `frontend/src/services/analyticsService.ts`

```typescript
private useBackendAPI = false; // Set to true when backend is configured
```

Change to `true` to use real backend APIs instead of mock data.

### Guest Login (Profile.json)

For demo purposes, you can use guest authentication without the backend:

**File**: `frontend/public/profile.json`

```json
{
  "guestEnabled": true,
  "guestUser": {
    "email": "guest@snapstudy.com",
    "password": "guest123",
    "id": "guest-user-001",
    "username": "Guest User"
  }
}
```

Login with these credentials to bypass backend authentication.

## API Documentation

### Interactive Documentation

When the backend is running, access:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Custom API Docs**: `http://localhost:8000/api-docs`

### Health Check

Check backend status: `GET http://localhost:8000/health`

## Authentication Flow

1. **Frontend** sends credentials to `/api/v1/auth/login`
2. **Backend** validates and returns JWT token
3. **Frontend** stores token in localStorage
4. **Frontend** includes token in all subsequent requests via Authorization header
5. **Backend** validates token on protected endpoints

## Error Handling

All API errors follow a standard format:

```json
{
  "detail": "Error message here",
  "status_code": 400
}
```

**Common Status Codes:**
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized (invalid/missing token)
- `404` - Not Found
- `500` - Internal Server Error

## Rate Limiting

The backend implements rate limiting:
- **100 requests/minute** per IP
- **2000 requests/hour** per IP
- **20 burst limit**

Exceeding limits returns `429 Too Many Requests`.

## Development Workflow

### Running Locally

1. **Start Backend**:
   ```bash
   cd backend
   python start_server.py
   ```
   Backend runs on `http://localhost:8000`

2. **Start Frontend**:
   ```bash
   cd frontend
   npm start
   ```
   Frontend runs on `http://localhost:3000`

3. **Configure Frontend**:
   ```typescript
   // frontend/src/config/index.ts
   const API_BASE_URL = 'http://localhost:8000';
   ```

4. **Enable Backend API**:
   ```typescript
   // frontend/src/services/analyticsService.ts
   private useBackendAPI = true;
   ```

### Testing API Integration

1. Login with credentials or guest account
2. Check browser console for API calls
3. Verify responses in Network tab
4. Check backend logs for requests

## Deployment

### Production Checklist

- [ ] Update `API_BASE_URL` to production domain
- [ ] Set `useBackendAPI = true` in analytics service
- [ ] Configure CORS in backend for frontend domain
- [ ] Set up proper authentication (AWS Cognito or similar)
- [ ] Enable HTTPS for all endpoints
- [ ] Configure environment variables
- [ ] Test all API endpoints
- [ ] Set up monitoring and logging

## Mock Data vs. Backend API

The application is designed to work in two modes:

### 1. **Mock Mode** (Default)
- `useBackendAPI = false`
- Uses local mock data
- No backend required
- Great for frontend development and demos

### 2. **Backend Mode**
- `useBackendAPI = true`
- Uses real backend APIs
- Requires backend server running
- Full feature set with real data

## Troubleshooting

### Frontend can't connect to backend
- Check `API_BASE_URL` in config
- Verify backend is running
- Check CORS settings
- Inspect browser console for errors

### Authentication fails
- Verify credentials
- Check token expiration
- Clear localStorage and try again
- Check backend logs for errors

### Analytics not loading
- Check `useBackendAPI` flag
- Verify analytics endpoints are implemented
- Check network tab for failed requests
- Falls back to mock data on error

## Next Steps

To fully integrate the backend:

1. Implement actual database operations in backend routers
2. Set up AWS Cognito or similar authentication service
3. Implement real analytics calculation logic
4. Add file processing for lesson uploads
5. Set up production deployment
6. Configure monitoring and logging
7. Add automated tests for API endpoints

## Support

For issues or questions:
- Check backend logs: `backend/logs/`
- Review API documentation: `http://localhost:8000/api-docs`
- Inspect network requests in browser DevTools
