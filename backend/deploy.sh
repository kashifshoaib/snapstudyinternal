#!/bin/bash
# SnapStudy Backend Deployment Script for AWS
# Automated deployment for hackathon submission

set -e  # Exit on error

echo "🚀 SnapStudy Backend Deployment"
echo "================================"

# Configuration
STACK_NAME="SnapStudyStack"
REGION="${AWS_REGION:-us-east-1}"
PROFILE="${AWS_PROFILE:-default}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_step() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_step "Checking prerequisites..."

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found. Please install: https://aws.amazon.com/cli/"
        exit 1
    fi

    # Check CDK
    if ! command -v cdk &> /dev/null; then
        print_error "AWS CDK not found. Install: npm install -g aws-cdk"
        exit 1
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found. Please install Docker Desktop"
        exit 1
    fi

    # Check Python
    if ! command -v python &> /dev/null; then
        print_error "Python not found. Please install Python 3.11+"
        exit 1
    fi

    print_step "✓ All prerequisites met"
}

# Deploy infrastructure
deploy_infrastructure() {
    print_step "📦 Deploying AWS infrastructure with CDK..."

    cd infrastructure

    # Install CDK dependencies if needed
    if [ ! -d "node_modules" ]; then
        print_step "Installing CDK dependencies..."
        npm install
    fi

    # Bootstrap CDK if needed (first time only)
    print_step "Bootstrapping CDK (if needed)..."
    cdk bootstrap --profile $PROFILE --region $REGION || true

    # Deploy stack
    print_step "Deploying CloudFormation stack..."
    cdk deploy --all --require-approval never --profile $PROFILE --region $REGION

    if [ $? -eq 0 ]; then
        print_step "✓ Infrastructure deployed successfully"
    else
        print_error "Infrastructure deployment failed"
        exit 1
    fi

    cd ..
}

# Get outputs from CloudFormation
get_stack_outputs() {
    print_step "📋 Retrieving stack outputs..."

    # Get Cognito User Pool ID
    USER_POOL_ID=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' \
        --output text \
        --profile $PROFILE \
        --region $REGION)

    # Get Cognito Client ID
    CLIENT_ID=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --query 'Stacks[0].Outputs[?OutputKey==`UserPoolClientId`].OutputValue' \
        --output text \
        --profile $PROFILE \
        --region $REGION)

    # Get API Gateway URL
    API_URL=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --query 'Stacks[0].Outputs[?OutputKey==`RestApiUrl`].OutputValue' \
        --output text \
        --profile $PROFILE \
        --region $REGION)

    # Get S3 Content Bucket
    CONTENT_BUCKET=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --query 'Stacks[0].Outputs[?OutputKey==`ContentBucketName`].OutputValue' \
        --output text \
        --profile $PROFILE \
        --region $REGION)

    # Get DynamoDB Tables
    USERS_TABLE=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --query 'Stacks[0].Outputs[?OutputKey==`UsersTableName`].OutputValue' \
        --output text \
        --profile $PROFILE \
        --region $REGION)

    print_step "✓ Stack outputs retrieved"
}

# Update environment configuration
update_environment() {
    print_step "⚙️  Updating environment configuration..."

    # Create .env file
    cat > .env << EOF
# AWS Configuration
AWS_REGION=$REGION
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --profile $PROFILE)

# Cognito
USER_POOL_ID=$USER_POOL_ID
USER_POOL_CLIENT_ID=$CLIENT_ID

# API Gateway
API_URL=$API_URL

# DynamoDB Tables
USERS_TABLE=$USERS_TABLE
LESSONS_TABLE=SnapStudy-Lessons
MICRO_LESSONS_TABLE=SnapStudy-MicroLessons
QUIZZES_TABLE=SnapStudy-Quizzes
USER_ENGAGEMENT_TABLE=SnapStudy-UserEngagement
CHAT_HISTORY_TABLE=SnapStudy-ChatHistory

# S3
CONTENT_BUCKET=$CONTENT_BUCKET

# Application
ENVIRONMENT=production
JWT_SECRET_KEY=$(openssl rand -hex 32)

# Bedrock (Update these after creating agents)
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0
BEDROCK_AGENT_ALIAS_ID=PRODUCTION

# IMPORTANT: Set these after deploying Bedrock Agents
# LEARNING_AGENT_ID=your-agent-id
# ADAPTIVE_AGENT_ID=your-agent-id
# KNOWLEDGE_BASE_ID=your-kb-id
EOF

    print_step "✓ Environment configuration updated (.env)"
}

# Build Docker image
build_docker_image() {
    print_step "🐳 Building Docker image..."

    docker build -t snapstudy-backend:latest .

    if [ $? -eq 0 ]; then
        print_step "✓ Docker image built successfully"
    else
        print_error "Docker build failed"
        exit 1
    fi
}

# Test Docker image locally
test_docker_image() {
    print_step "🧪 Testing Docker image locally..."

    print_warning "Starting container on port 8000..."
    print_warning "Press Ctrl+C to stop after testing"

    docker run --rm \
        --env-file .env \
        -p 8000:8000 \
        snapstudy-backend:latest
}

# Create deployment summary
create_deployment_summary() {
    print_step "📄 Creating deployment summary..."

    cat > DEPLOYMENT_INFO.md << EOF
# SnapStudy Deployment Information

**Deployment Date:** $(date)
**Region:** $REGION
**Stack:** $STACK_NAME

## 🔗 Endpoints

- **API Gateway URL:** $API_URL
- **Health Check:** ${API_URL}health
- **API Documentation:** ${API_URL}docs
- **API Docs (ReDoc):** ${API_URL}redoc

## 🔐 Authentication

- **User Pool ID:** $USER_POOL_ID
- **Client ID:** $CLIENT_ID

## 🗄️ Resources

- **Content Bucket:** $CONTENT_BUCKET
- **Users Table:** $USERS_TABLE
- **Region:** $REGION

## 📊 Monitoring

View CloudWatch dashboard:
\`\`\`bash
aws cloudwatch get-dashboard --dashboard-name SnapStudy-Metrics --profile $PROFILE --region $REGION
\`\`\`

## 🧪 Test Deployment

Test health endpoint:
\`\`\`bash
curl ${API_URL}health
\`\`\`

Register test user:
\`\`\`bash
curl -X POST ${API_URL}api/v1/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "test@example.com",
    "password": "Test123!",
    "full_name": "Test User",
    "profession": "Software Engineer",
    "learning_style": "visual"
  }'
\`\`\`

## 🚨 Important Next Steps

1. **Deploy Bedrock Agents** (if not done):
   - Create agents via AWS Console or CLI
   - Update LEARNING_AGENT_ID and ADAPTIVE_AGENT_ID in .env

2. **Update CORS** in API Gateway:
   - Restrict allowed origins from '*' to your frontend domain

3. **Enable CloudWatch Alarms**:
   - Set up SNS topic for alerts
   - Configure alarm actions

4. **Test All Endpoints**:
   - Run integration tests
   - Verify multi-agent strands
   - Test WebSocket connections

## 🎯 Demo URLs for Judges

- Adaptive Learning: ${API_URL}api/v1/adaptive/
- Multi-Agent Strands: ${API_URL}api/v1/orchestrator/
- Chat: ${API_URL}api/v1/chat/
- Analytics: ${API_URL}api/v1/analytics/

## 📝 Notes

- All resources created with RETAIN removal policy
- Point-in-time recovery enabled on DynamoDB tables
- S3 versioning enabled
- CloudWatch logging enabled

EOF

    print_step "✓ Deployment summary created (DEPLOYMENT_INFO.md)"
}

# Print deployment instructions
print_deployment_instructions() {
    echo ""
    echo "================================================"
    echo "✅ Deployment Complete!"
    echo "================================================"
    echo ""
    echo "📋 Important Files Created:"
    echo "   - .env (environment configuration)"
    echo "   - DEPLOYMENT_INFO.md (deployment details)"
    echo ""
    echo "🔗 Your API is available at:"
    echo "   $API_URL"
    echo ""
    echo "📖 Next Steps:"
    echo ""
    echo "1. Review .env and update Bedrock Agent IDs"
    echo "2. Test deployment:"
    echo "   curl ${API_URL}health"
    echo ""
    echo "3. View API documentation:"
    echo "   ${API_URL}docs"
    echo ""
    echo "4. Test locally with Docker:"
    echo "   docker run --env-file .env -p 8000:8000 snapstudy-backend:latest"
    echo ""
    echo "5. For production frontend deployment:"
    echo "   cd ../frontend && npm run build"
    echo "   aws s3 sync build/ s3://$CONTENT_BUCKET-frontend/"
    echo ""
    echo "================================================"
}

# Main deployment flow
main() {
    echo ""
    print_step "Starting deployment process..."
    echo ""

    # Run deployment steps
    check_prerequisites
    deploy_infrastructure
    get_stack_outputs
    update_environment
    create_deployment_summary

    # Optional: Build Docker image
    read -p "$(echo -e ${YELLOW}Build Docker image? [y/N]:${NC} )" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        build_docker_image

        read -p "$(echo -e ${YELLOW}Test Docker image locally? [y/N]:${NC} )" -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            test_docker_image
        fi
    fi

    print_deployment_instructions
}

# Run main function
main "$@"
