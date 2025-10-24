#!/bin/bash

# Frontend Deployment Script for SnapStudy
# This script builds the React app and deploys it to AWS S3 with CloudFront invalidation

set -e  # Exit on any error

# Configuration
S3_BUCKET="aws-hackathon-snapstudy"
CLOUDFRONT_DISTRIBUTION_ID="E14OU2B88K9RN3"
FRONTEND_DIR="frontend"
BUILD_DIR="$FRONTEND_DIR/build"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 Starting frontend deployment...${NC}"

# Check if we're in the right directory
if [ ! -d "$FRONTEND_DIR" ]; then
    echo -e "${RED}❌ Error: frontend directory not found. Make sure you're in the project root.${NC}"
    exit 1
fi

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ Error: AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Navigate to frontend directory
cd "$FRONTEND_DIR"

echo -e "${YELLOW}📦 Installing dependencies...${NC}"
npm install

echo -e "${YELLOW}🔨 Building React app...${NC}"
npm run build

# Check if build was successful
if [ ! -d "build" ]; then
    echo -e "${RED}❌ Error: Build failed. No build directory found.${NC}"
    exit 1
fi

echo -e "${YELLOW}☁️  Uploading to S3 bucket: $S3_BUCKET${NC}"
aws s3 sync build/ s3://$S3_BUCKET --delete

echo -e "${YELLOW}🔄 Creating CloudFront invalidation...${NC}"
INVALIDATION_ID=$(aws cloudfront create-invalidation \
    --distribution-id $CLOUDFRONT_DISTRIBUTION_ID \
    --paths "/*" \
    --query 'Invalidation.Id' \
    --output text)

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}📋 Invalidation ID: $INVALIDATION_ID${NC}"
echo -e "${GREEN}🌐 Your app should be updated in a few minutes.${NC}"

# Return to project root
cd ..