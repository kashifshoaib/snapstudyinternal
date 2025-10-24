#!/bin/bash

# SnapStudy Frontend Deployment Script
# This script deploys the CloudFormation stack and uploads the frontend files

set -e

# Configuration
STACK_NAME="snapstudy-frontend"
TEMPLATE_FILE="frontend-infrastructure.yaml"
BUCKET_NAME="aws-hackathon-snapstudy"
FRONTEND_BUILD_DIR="../frontend/build"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 SnapStudy Frontend Deployment${NC}"
echo "=================================="

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Build frontend if build directory doesn't exist
if [ ! -d "$FRONTEND_BUILD_DIR" ]; then
    echo -e "${YELLOW}🔨 Building frontend...${NC}"
    cd ../frontend
    npm install
    npm run build
    cd ../CFT
    echo -e "${GREEN}✅ Frontend built successfully${NC}"
fi

# Check if template file exists
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo -e "${RED}❌ CloudFormation template not found: $TEMPLATE_FILE${NC}"
    exit 1
fi

echo -e "${BLUE}📋 Deployment Configuration:${NC}"
echo "  Stack Name: $STACK_NAME"
echo "  Bucket Name: $BUCKET_NAME"
echo "  Template: $TEMPLATE_FILE"
echo "  Frontend Build: $FRONTEND_BUILD_DIR"
echo ""

# Deploy CloudFormation stack
echo -e "${YELLOW}🏗️  Deploying CloudFormation stack...${NC}"
aws cloudformation deploy \
    --template-file "$TEMPLATE_FILE" \
    --stack-name "$STACK_NAME" \
    --parameter-overrides BucketName="$BUCKET_NAME" \
    --capabilities CAPABILITY_IAM \
    --no-fail-on-empty-changeset

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ CloudFormation stack deployed successfully${NC}"
else
    echo -e "${RED}❌ CloudFormation deployment failed${NC}"
    exit 1
fi

# Get stack outputs
echo -e "${YELLOW}📊 Getting stack outputs...${NC}"
CLOUDFRONT_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontURL`].OutputValue' \
    --output text)

DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' \
    --output text)

# Upload frontend files to S3
echo -e "${YELLOW}📤 Uploading frontend files to S3...${NC}"
aws s3 sync "$FRONTEND_BUILD_DIR/" "s3://$BUCKET_NAME/" \
    --delete \
    --cache-control "public, max-age=31536000" \
    --exclude "*.html" \
    --exclude "asset-manifest.json"

# Upload HTML files with no-cache headers
aws s3 sync "$FRONTEND_BUILD_DIR/" "s3://$BUCKET_NAME/" \
    --delete \
    --cache-control "no-cache, no-store, must-revalidate" \
    --include "*.html" \
    --include "asset-manifest.json"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Frontend files uploaded successfully${NC}"
else
    echo -e "${RED}❌ Frontend upload failed${NC}"
    exit 1
fi

# Create CloudFront invalidation
echo -e "${YELLOW}🔄 Creating CloudFront invalidation...${NC}"
INVALIDATION_ID=$(aws cloudfront create-invalidation \
    --distribution-id "$DISTRIBUTION_ID" \
    --paths "/*" \
    --query 'Invalidation.Id' \
    --output text)

echo -e "${GREEN}✅ CloudFront invalidation created: $INVALIDATION_ID${NC}"

# Display results
echo ""
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo "=================================="
echo -e "${BLUE}📱 Your SnapStudy app is available at:${NC}"
echo -e "${GREEN}   $CLOUDFRONT_URL${NC}"
echo ""
echo -e "${BLUE}📋 Useful commands:${NC}"
echo "  Check invalidation status:"
echo "    aws cloudfront get-invalidation --distribution-id $DISTRIBUTION_ID --id $INVALIDATION_ID"
echo ""
echo "  Update frontend (after rebuilding):"
echo "    aws s3 sync $FRONTEND_BUILD_DIR/ s3://$BUCKET_NAME/ --delete"
echo "    aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths '/*'"
echo ""
echo -e "${YELLOW}⏰ Note: CloudFront distribution may take 5-15 minutes to fully deploy${NC}"