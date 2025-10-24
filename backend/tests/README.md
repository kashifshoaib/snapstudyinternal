# SnapStudy Backend Test Suite

This directory contains comprehensive functional tests for all SnapStudy backend services and functionality.

## Core Test Suite (Pytest-based)

### Primary Test Files
- **`test_functional_comprehensive.py`** - Core API infrastructure, database operations, authentication, error handling (37 tests)
- **`test_services_functional.py`** - Detailed service integration, retry mechanisms, data consistency (24 tests)
- **`test_lambda_functional.py`** - Lambda function handlers, content processing, multimedia generation (17 tests)
- **`test_ai_services_functional.py`** - AI/ML services integration, Bedrock, S3, Textract, Transcribe (19 tests)

### Extended Test Files
- **`test_adaptive_analytics_functional.py`** - Adaptive learning agent and analytics system integration
- **`test_quiz_chat_functional.py`** - Quiz engine and chat agent functionality

### Test Runners
- **`run_core_tests.py`** - Simple, reliable test runner for core functionality
- **`run_all_functional_tests.py`** - Comprehensive test runner for all test suites

## Running Tests

### Quick Start (Recommended)

```bash
# Run core test suite (most reliable)
cd backend/tests
python run_core_tests.py
```

### Running Individual Test Suites

```bash
# Run from the backend/tests directory
cd backend/tests

# Core functionality tests
python -m pytest test_functional_comprehensive.py -v
python -m pytest test_services_functional.py -v
python -m pytest test_lambda_functional.py -v
python -m pytest test_ai_services_functional.py -v

# Extended functionality tests
python -m pytest test_adaptive_analytics_functional.py -v
python -m pytest test_quiz_chat_functional.py -v
```

### Running All Tests

```bash
# Run all test suites
cd backend/tests
python run_all_functional_tests.py

# Or use pytest directly
python -m pytest . -v
```

## Test Coverage

### 🎯 **Comprehensive Backend Coverage (97+ Tests)**
- **Core API Infrastructure**: FastAPI, health endpoints, CORS, security headers
- **Database Operations**: DynamoDB CRUD, serialization, async operations
- **Authentication & Authorization**: JWT validation, user sessions
- **Error Handling & Middleware**: Custom exceptions, AWS error handling
- **Lambda Functions**: Main handler, content/multimedia processors
- **AI Services Integration**: Bedrock, S3, Textract, Transcribe
- **Adaptive Learning**: Autonomous decision-making, analytics
- **Quiz & Chat Systems**: Intelligent generation, evaluation, conversation
- **Performance & Reliability**: Concurrent operations, error recovery

### 🧪 **Test Types**
- **Functional Tests**: End-to-end workflow validation
- **Integration Tests**: Service interaction testing
- **Mocked Tests**: Isolated functionality (no AWS required)
- **Performance Tests**: Concurrent operations, scaling, timeouts

## Test Data

Tests create temporary test data in DynamoDB tables. All test data is automatically cleaned up or uses TTL for automatic expiration.

## AWS Requirements

Most tests require AWS credentials for the `hackathon-user-01` user with permissions for:
- DynamoDB (read/write access to SnapStudy tables)
- Bedrock (model invocation permissions)
- S3 (content bucket access)

## Troubleshooting

### Common Issues

1. **AWS Credentials Error**
   ```bash
   # Verify AWS profile
   aws sts get-caller-identity
   # Should show hackathon-user-01
   ```

2. **Import Errors**
   ```bash
   # Ensure you're running from backend directory
   cd backend
   python tests/test_name.py
   ```

3. **Bedrock Throttling**
   - Tests include retry logic with exponential backoff
   - Some tests may take longer due to rate limiting
   - This is expected behavior

### Test Output

Successful tests will show:
```
✅ All tests passed!
🎉 [Service] functionality is working correctly!
```

Failed tests will show detailed error messages and stack traces for debugging.

## Contributing

When adding new functionality:
1. Create corresponding test files in this directory
2. Follow the naming convention: `test_[service_name].py`
3. Include both success and failure test cases
4. Add documentation for new test files in this README