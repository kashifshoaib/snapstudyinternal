# SnapStudy Infrastructure

This directory contains the AWS CDK infrastructure code for the SnapStudy platform.

## Architecture Overview

The SnapStudy platform is built using serverless AWS services:

- **DynamoDB**: Six tables for storing users, lessons, micro-lessons, quizzes, user engagement, and chat history
- **S3**: Encrypted bucket for content storage with lifecycle policies
- **Cognito**: User Pool and Identity Pool for authentication
- **API Gateway**: REST API and WebSocket API for client communication
- **IAM**: Least privilege roles for Lambda functions
- **CloudWatch**: Logging and monitoring

## Prerequisites

1. **AWS CLI**: Configured with appropriate credentials
2. **Node.js**: Version 18 or higher
3. **AWS CDK**: Version 2.87.0 or higher
4. **TypeScript**: For development

## Setup

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your AWS account details
   ```

3. **Bootstrap CDK** (first time only):
   ```bash
   cdk bootstrap
   ```

## Deployment

### Quick Deployment
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### Manual Deployment
```bash
# Build the project
npm run build

# Synthesize the CloudFormation template
cdk synth

# Deploy the stack
cdk deploy
```

## Stack Resources

### DynamoDB Tables

1. **SnapStudy-Users**
   - Primary Key: `user_id`
   - GSI: `EmailIndex` (email)
   - Features: Streams, encryption, point-in-time recovery

2. **SnapStudy-Lessons**
   - Primary Key: `lesson_id`
   - GSI: `UserLessonsIndex` (user_id, created_at)
   - Features: TTL, streams, encryption

3. **SnapStudy-MicroLessons**
   - Primary Key: `micro_lesson_id`
   - GSI: `LessonMicroLessonsIndex` (lesson_id, sequence_number)
   - Features: Streams, encryption

4. **SnapStudy-Quizzes**
   - Primary Key: `quiz_id`
   - GSI: `MicroLessonQuizzesIndex` (micro_lesson_id)
   - Features: Streams, encryption

5. **SnapStudy-UserEngagement**
   - Primary Key: `engagement_id`
   - GSI: `UserEngagementIndex` (user_id, timestamp)
   - Features: TTL (365 days), streams, encryption

6. **SnapStudy-ChatHistory**
   - Primary Key: `session_id`
   - GSI: `UserChatHistoryIndex` (user_id, created_at)
   - Features: TTL (30 days), encryption

### S3 Bucket

- **Name**: `snapstudy-content-{account}-{region}`
- **Features**: Encryption, versioning, lifecycle policies, CORS
- **Lifecycle**: Transition to IA after 30 days

### Cognito

- **User Pool**: Email-based authentication with custom attributes
- **Identity Pool**: For AWS resource access
- **Client**: Web client with OAuth configuration

### API Gateway

- **REST API**: Regional endpoint with CORS and throttling
- **WebSocket API**: For real-time chat functionality
- **Features**: Logging, metrics, throttling (1000 req/sec, 2000 burst)

### IAM Roles

1. **AuthLambdaRole**: Cognito and Users table access
2. **ContentLambdaRole**: S3, Textract, Transcribe, Bedrock access
3. **AdaptiveLambdaRole**: Bedrock and all tables access
4. **ChatLambdaRole**: Bedrock, chat tables, WebSocket API access
5. **StepFunctionsRole**: Lambda invocation permissions

## Configuration

### Environment Variables

The stack uses the following environment variables:

- `AWS_REGION`: AWS region for deployment
- `AWS_ACCOUNT_ID`: Your AWS account ID
- `ENVIRONMENT`: Environment name (dev/staging/prod)
- `DOMAIN_NAME`: Custom domain (optional)
- `CERTIFICATE_ARN`: SSL certificate ARN (optional)

### Security Features

- All data encrypted at rest and in transit
- Least privilege IAM roles
- API throttling and rate limiting
- CORS configuration
- Input validation and sanitization
- CloudWatch logging and monitoring

## Monitoring

The stack creates CloudWatch log groups for:

- API Gateway REST API
- API Gateway WebSocket API
- Lambda functions
- Step Functions

## Cleanup

To destroy the infrastructure:

```bash
chmod +x scripts/destroy.sh
./scripts/destroy.sh
```

**Warning**: This will permanently delete all resources. Make sure to backup any important data first.

## Troubleshooting

### Common Issues

1. **CDK Bootstrap Error**: Run `cdk bootstrap` in your target region
2. **Permission Denied**: Ensure your AWS credentials have sufficient permissions
3. **Resource Limits**: Check AWS service limits in your account
4. **Region Availability**: Ensure all services are available in your chosen region

### Useful Commands

- `cdk ls`: List all stacks
- `cdk synth`: Synthesize CloudFormation template
- `cdk diff`: Compare deployed stack with current state
- `cdk docs`: Open CDK documentation

## Next Steps

After successful deployment:

1. Note the output values (User Pool ID, API endpoints, etc.)
2. Configure your Lambda functions with the created IAM roles
3. Set up your frontend application with the Cognito and API Gateway details
4. Configure monitoring and alerting as needed

## Support

For issues related to the infrastructure setup, please check:

1. AWS CloudFormation console for stack events
2. CloudWatch logs for detailed error messages
3. AWS service health dashboard for any service issues