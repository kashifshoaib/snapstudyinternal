# SnapStudy Backend

Python-based backend for the SnapStudy adaptive learning platform.

## Architecture

- **Framework**: FastAPI for container deployment
- **Database**: Amazon DynamoDB
- **Authentication**: AWS Cognito
- **Storage**: Amazon S3
- **AI/ML**: Amazon Bedrock (Claude 3)
- **Infrastructure**: AWS CDK (Python)

## Project Structure

```
backend/
├── src/                    # Application source code
│   ├── api/               # FastAPI application and routers
│   ├── models/            # Pydantic data models
│   ├── services/          # Business logic services
│   └── config.py          # Configuration settings
├── tests/                 # Comprehensive test suite
│   ├── test_*.py         # Individual test files
│   ├── __init__.py       # Test package initialization
│   └── README.md         # Test documentation
├── infrastructure/        # AWS CDK infrastructure code
│   ├── stacks/           # CDK stack definitions
│   ├── app.py            # CDK app entry point
│   └── cdk.json          # CDK configuration
├── requirements.txt       # Python dependencies
├── deploy.py             # Deployment script
├── run_tests.py          # Test runner script
└── README.md             # This file
```

## Quick Start

### Prerequisites

- Python 3.11+
- AWS CLI configured with appropriate credentials
- AWS CDK CLI installed (`npm install -g aws-cdk`)

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r infrastructure/requirements.txt
```

2. Deploy the infrastructure:
```bash
python deploy.py
```

### Manual Deployment

If you prefer to deploy manually:

```bash
# Navigate to infrastructure directory
cd infrastructure

# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy the stack
cdk deploy
```

## Configuration

The application uses environment variables for configuration. Key variables:

- `AWS_REGION`: AWS region (default: us-east-1)
- `USER_POOL_ID`: Cognito User Pool ID
- `USER_POOL_CLIENT_ID`: Cognito User Pool Client ID
- `ANTHROPIC_API_KEY`: Anthropic API key for Claude
- `JWT_SECRET_KEY`: Secret key for JWT tokens

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/logout` - User logout
- `GET /api/v1/auth/me` - Get current user info

### Users
- `GET /api/v1/users/{user_id}` - Get user profile
- `PUT /api/v1/users/{user_id}` - Update user profile

### Lessons
- `POST /api/v1/lessons` - Create new lesson
- `GET /api/v1/lessons/{lesson_id}` - Get lesson details
- `GET /api/v1/users/{user_id}/lessons` - Get user's lessons

### Content
- `POST /api/v1/content/upload` - Upload content for processing

## Database Schema

### DynamoDB Tables

1. **Users** (`SnapStudy-Users`)
   - Primary Key: `user_id`
   - GSI: `EmailIndex` on `email`

2. **Lessons** (`SnapStudy-Lessons`)
   - Primary Key: `lesson_id`
   - GSI: `UserLessonsIndex` on `user_id` + `created_at`

3. **MicroLessons** (`SnapStudy-MicroLessons`)
   - Primary Key: `micro_lesson_id`
   - GSI: `LessonMicroLessonsIndex` on `lesson_id` + `sequence_number`

4. **Quizzes** (`SnapStudy-Quizzes`)
   - Primary Key: `quiz_id`
   - GSI: `MicroLessonQuizzesIndex` on `micro_lesson_id`

5. **UserEngagement** (`SnapStudy-UserEngagement`)
   - Primary Key: `engagement_id`
   - GSI: `UserEngagementIndex` on `user_id` + `timestamp`

6. **ChatHistory** (`SnapStudy-ChatHistory`)
   - Primary Key: `session_id`
   - GSI: `UserChatHistoryIndex` on `user_id` + `created_at`

## Testing

### Test Suite Overview

The `tests/` directory contains comprehensive tests for all backend functionality:

- **Analytics System**: Learning analytics and progress tracking
- **Chat Agent**: Agentic chat and tutoring system  
- **Quiz Engine**: Intelligent quiz generation and evaluation
- **Bedrock Integration**: AI service integration with retry logic
- **API Endpoints**: REST API functionality
- **Adaptive Agent**: AgentCore integration and adaptive learning

### Running Tests

#### Quick Test Runner
```bash
# Interactive test runner with options
python run_tests.py
```

#### Individual Tests
```bash
# Run specific test
python tests/test_analytics_system.py
python tests/test_quiz_engine.py
python tests/test_chat_agent.py

# Run mocked tests (no AWS required)
python tests/test_chat_agent_mock.py
python tests/test_bedrock_retry.py
```

#### All Tests with pytest
```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### Test Categories

- **🧪 Unit Tests**: Individual service functionality
- **🔗 Integration Tests**: AWS service integration  
- **🎭 Mocked Tests**: No AWS credentials required
- **📊 System Tests**: End-to-end functionality

### Prerequisites for Testing

1. **AWS Credentials**: Configure `hackathon-user-01` profile
   ```bash
   $env:AWS_PROFILE = "hackathon-user-01"
   aws sts get-caller-identity  # Verify
   ```

2. **Dependencies**: Install test requirements
   ```bash
   pip install -r requirements.txt
   ```

3. **Permissions**: Ensure access to DynamoDB, Bedrock, and S3

### Test Documentation

See `tests/README.md` for detailed test documentation, troubleshooting, and contribution guidelines.

## Development

### Local Development

1. Set up environment variables in `.env` file
2. Install dependencies: `pip install -r requirements.txt`
3. Run tests: `python run_tests.py`
4. Start development server: `python start_server.py`

### Adding New Features

1. Create data models in `src/models/`
2. Implement business logic in `src/services/`
3. Add API endpoints in `src/api/routers/`
4. **Write tests** in `tests/test_[feature].py`
5. Update infrastructure if needed in `infrastructure/stacks/`

## Deployment

The deployment script (`deploy.py`) handles:
1. Installing dependencies
2. CDK bootstrapping
3. Stack synthesis
4. Stack deployment

## Monitoring

- CloudWatch logs for Lambda functions
- API Gateway metrics and logging
- DynamoDB metrics

## Security

- JWT-based authentication
- AWS Cognito for user management
- IAM roles with least privilege
- Input validation with Pydantic
- CORS configuration

## Next Steps

After deployment, you'll need to:
1. Configure Anthropic API key in AWS Secrets Manager
2. Set up proper CORS origins for production
3. Configure custom domain for API Gateway
4. Set up monitoring and alerting