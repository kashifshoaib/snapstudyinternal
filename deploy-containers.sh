#!/bin/bash

# SnapStudy Container Deployment Script
# This script deploys SnapStudy as Docker containers

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
ENVIRONMENT=${ENVIRONMENT:-production}
STACK_NAME="SnapStudy-${ENVIRONMENT}"

echo -e "${BLUE}🐳 Starting SnapStudy Container Deployment${NC}"
echo -e "${BLUE}Region: ${AWS_REGION}${NC}"
echo -e "${BLUE}Environment: ${ENVIRONMENT}${NC}"
echo ""

# Function to print status
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
echo -e "${BLUE}📋 Checking Prerequisites${NC}"

if ! command -v docker >/dev/null 2>&1; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose >/dev/null 2>&1; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

if ! command -v aws >/dev/null 2>&1; then
    print_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

print_status "All prerequisites are installed"

# Check AWS credentials
echo -e "${BLUE}🔐 Checking AWS Credentials${NC}"
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    print_error "AWS credentials are not configured. Please run 'aws configure' first."
    exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
print_status "AWS credentials are configured (Account: ${AWS_ACCOUNT_ID})"

# Deploy AWS infrastructure (DynamoDB, S3, Cognito only)
echo -e "${BLUE}🏗️  Deploying AWS Infrastructure (Database & Storage)${NC}"
cd infrastructure

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    npm install
fi

# Deploy infrastructure stack (without Lambda functions)
cdk deploy ${STACK_NAME} --require-approval never --outputs-file ../deployment-outputs.json
if [ $? -eq 0 ]; then
    print_status "AWS infrastructure deployed successfully"
else
    print_error "AWS infrastructure deployment failed"
    exit 1
fi

cd ..

# Get infrastructure outputs
if [ -f deployment-outputs.json ]; then
    USER_POOL_ID=$(cat deployment-outputs.json | python3 -c "import sys, json; print(json.load(sys.stdin)['${STACK_NAME}']['UserPoolId'])" 2>/dev/null || echo "")
    USER_POOL_CLIENT_ID=$(cat deployment-outputs.json | python3 -c "import sys, json; print(json.load(sys.stdin)['${STACK_NAME}']['UserPoolClientId'])" 2>/dev/null || echo "")
    CONTENT_BUCKET=$(cat deployment-outputs.json | python3 -c "import sys, json; print(json.load(sys.stdin)['${STACK_NAME}']['ContentBucketName'])" 2>/dev/null || echo "")
    
    print_status "Retrieved infrastructure configuration"
else
    print_warning "Could not find deployment outputs, using environment variables"
fi

# Set environment variables for containers
export AWS_REGION
export USER_POOL_ID
export USER_POOL_CLIENT_ID
export CONTENT_BUCKET
export JWT_SECRET_KEY=${JWT_SECRET_KEY:-$(openssl rand -base64 32)}

# Build and start containers
echo -e "${BLUE}🐳 Building and Starting Containers${NC}"

# Build images
docker-compose build
if [ $? -eq 0 ]; then
    print_status "Container images built successfully"
else
    print_error "Container build failed"
    exit 1
fi

# Start containers
docker-compose up -d
if [ $? -eq 0 ]; then
    print_status "Containers started successfully"
else
    print_error "Container startup failed"
    exit 1
fi

# Wait for services to be ready
echo -e "${BLUE}⏳ Waiting for services to be ready${NC}"
sleep 10

# Test backend health
echo -e "${BLUE}🧪 Testing Backend Health${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        print_status "Backend is healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Backend health check failed after 30 attempts"
        docker-compose logs snapstudy-backend
        exit 1
    fi
    sleep 2
done

# Test frontend
echo -e "${BLUE}🎨 Testing Frontend${NC}"
for i in {1..30}; do
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        print_status "Frontend is accessible"
        break
    fi
    if [ $i -eq 30 ]; then
        print_error "Frontend accessibility check failed after 30 attempts"
        docker-compose logs snapstudy-frontend
        exit 1
    fi
    sleep 2
done

# Display deployment summary
echo ""
echo -e "${GREEN}🎉 Container Deployment Summary${NC}"
echo -e "${GREEN}================================${NC}"
echo -e "${BLUE}Backend URL:${NC} http://localhost:8000"
echo -e "${BLUE}Frontend URL:${NC} http://localhost:3000"
echo -e "${BLUE}API Docs:${NC} http://localhost:8000/docs"
echo -e "${BLUE}User Pool ID:${NC} ${USER_POOL_ID}"
echo -e "${BLUE}Content Bucket:${NC} ${CONTENT_BUCKET}"
echo ""
echo -e "${GREEN}✅ SnapStudy containers are running successfully!${NC}"
echo ""
echo -e "${YELLOW}📝 Container Management Commands:${NC}"
echo -e "${YELLOW}• View logs: docker-compose logs -f${NC}"
echo -e "${YELLOW}• Stop containers: docker-compose down${NC}"
echo -e "${YELLOW}• Restart containers: docker-compose restart${NC}"
echo -e "${YELLOW}• View status: docker-compose ps${NC}"
echo ""

# Save deployment info
cat > container-deployment-info.txt << EOF
SnapStudy Container Deployment Information
==========================================
Deployment Date: $(date)
Deployment Type: Docker Containers
AWS Region: ${AWS_REGION}
Environment: ${ENVIRONMENT}
AWS Account: ${AWS_ACCOUNT_ID}

Application URLs:
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- API Documentation: http://localhost:8000/docs

AWS Resources:
- User Pool ID: ${USER_POOL_ID}
- User Pool Client ID: ${USER_POOL_CLIENT_ID}
- Content Bucket: ${CONTENT_BUCKET}

Container Status: RUNNING
EOF

print_status "Container deployment information saved to container-deployment-info.txt"

echo -e "${GREEN}🚀 Container deployment completed successfully!${NC}"