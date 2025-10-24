#!/bin/bash

# Deploy API Gateway HTTPS proxy for SnapStudy backend
# This creates an HTTPS endpoint that proxies to your HTTP Elastic Beanstalk backend

set -e

STACK_NAME="SnapStudy-API-Gateway"
TEMPLATE_FILE="api-gateway-https-proxy.yaml"
REGION="us-east-1"
BACKEND_URL="snapstudy-backend-env.eba-ygmxm24z.us-east-1.elasticbeanstalk.com"

echo "🚀 Deploying API Gateway HTTPS proxy for SnapStudy..."
echo "   Stack Name: $STACK_NAME"
echo "   Region: $REGION"
echo "   Backend URL: $BACKEND_URL"
echo ""

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Deploy the CloudFormation stack
echo "📦 Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file "$TEMPLATE_FILE" \
    --stack-name "$STACK_NAME" \
    --parameter-overrides \
        BackendUrl="$BACKEND_URL" \
        StageName="prod" \
    --region "$REGION" \
    --capabilities CAPABILITY_IAM

# Get the API Gateway URL
echo ""
echo "✅ Deployment complete!"
echo ""

API_GATEWAY_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
    --output text)

echo "🌐 Your HTTPS API Gateway URL:"
echo "   $API_GATEWAY_URL"
echo ""
echo "🔧 Next steps:"
echo "   1. Update your frontend config to use this HTTPS URL"
echo "   2. Test the API Gateway:"
echo "      curl $API_GATEWAY_URL/health"
echo "   3. Update your frontend production config:"
echo "      REACT_APP_API_URL=$API_GATEWAY_URL"
echo ""
echo "📝 Frontend config update:"
echo "   Replace the API_BASE_URL in frontend/src/config/index.ts with:"
echo "   const API_BASE_URL = '$API_GATEWAY_URL';"
echo ""