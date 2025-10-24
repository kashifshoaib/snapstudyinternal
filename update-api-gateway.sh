#!/bin/bash

# Update API Gateway stack with proper CORS handling

set -e

STACK_NAME="SnapStudy-API-Gateway"
TEMPLATE_FILE="api-gateway-cors-fixed.yaml"
REGION="us-east-1"
BACKEND_URL="snapstudy-backend-env.eba-ygmxm24z.us-east-1.elasticbeanstalk.com"

echo "🔄 Updating API Gateway with proper CORS handling..."
echo "   Stack Name: $STACK_NAME"
echo "   Region: $REGION"
echo "   Backend URL: $BACKEND_URL"
echo ""

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Update the CloudFormation stack
echo "📦 Updating CloudFormation stack..."
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
echo "✅ Update complete!"
echo ""

API_GATEWAY_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
    --output text)

echo "🌐 Your updated HTTPS API Gateway URL:"
echo "   $API_GATEWAY_URL"
echo ""
echo "🧪 Test CORS preflight:"
echo "   curl -X OPTIONS -H \"Origin: https://example.com\" -H \"Access-Control-Request-Method: POST\" $API_GATEWAY_URL/api/v1/auth/login"
echo ""
echo "🧪 Test actual request:"
echo "   curl -X POST -H \"Content-Type: application/json\" $API_GATEWAY_URL/api/v1/auth/login -d '{\"email\":\"test@example.com\",\"password\":\"test123\"}'"
echo ""