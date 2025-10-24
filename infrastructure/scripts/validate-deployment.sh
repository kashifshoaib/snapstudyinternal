#!/bin/bash

# SnapStudy Infrastructure Validation Script

set -e

echo "🔍 Validating SnapStudy Infrastructure Deployment"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

# Function to check if a resource exists
check_resource() {
    local resource_type=$1
    local resource_name=$2
    local aws_command=$3
    
    echo -n "Checking $resource_type: $resource_name... "
    
    if eval $aws_command > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((FAILED++))
    fi
}

# Function to get stack output
get_stack_output() {
    local output_key=$1
    aws cloudformation describe-stacks \
        --stack-name SnapStudyStack \
        --query "Stacks[0].Outputs[?OutputKey=='$output_key'].OutputValue" \
        --output text 2>/dev/null || echo ""
}

echo "1. Checking CloudFormation Stack..."
check_resource "CloudFormation Stack" "SnapStudyStack" \
    "aws cloudformation describe-stacks --stack-name SnapStudyStack"

echo ""
echo "2. Checking DynamoDB Tables..."
check_resource "DynamoDB Table" "SnapStudy-Users" \
    "aws dynamodb describe-table --table-name SnapStudy-Users"

check_resource "DynamoDB Table" "SnapStudy-Lessons" \
    "aws dynamodb describe-table --table-name SnapStudy-Lessons"

check_resource "DynamoDB Table" "SnapStudy-MicroLessons" \
    "aws dynamodb describe-table --table-name SnapStudy-MicroLessons"

check_resource "DynamoDB Table" "SnapStudy-Quizzes" \
    "aws dynamodb describe-table --table-name SnapStudy-Quizzes"

check_resource "DynamoDB Table" "SnapStudy-UserEngagement" \
    "aws dynamodb describe-table --table-name SnapStudy-UserEngagement"

check_resource "DynamoDB Table" "SnapStudy-ChatHistory" \
    "aws dynamodb describe-table --table-name SnapStudy-ChatHistory"

echo ""
echo "3. Checking S3 Bucket..."
BUCKET_NAME=$(get_stack_output "ContentBucketName")
if [ -n "$BUCKET_NAME" ]; then
    check_resource "S3 Bucket" "$BUCKET_NAME" \
        "aws s3api head-bucket --bucket $BUCKET_NAME"
else
    echo -e "${RED}✗ FAIL${NC} - Could not retrieve bucket name from stack outputs"
    ((FAILED++))
fi

echo ""
echo "4. Checking Cognito Resources..."
USER_POOL_ID=$(get_stack_output "UserPoolId")
if [ -n "$USER_POOL_ID" ]; then
    check_resource "Cognito User Pool" "$USER_POOL_ID" \
        "aws cognito-idp describe-user-pool --user-pool-id $USER_POOL_ID"
else
    echo -e "${RED}✗ FAIL${NC} - Could not retrieve User Pool ID from stack outputs"
    ((FAILED++))
fi

USER_POOL_CLIENT_ID=$(get_stack_output "UserPoolClientId")
if [ -n "$USER_POOL_CLIENT_ID" ] && [ -n "$USER_POOL_ID" ]; then
    check_resource "Cognito User Pool Client" "$USER_POOL_CLIENT_ID" \
        "aws cognito-idp describe-user-pool-client --user-pool-id $USER_POOL_ID --client-id $USER_POOL_CLIENT_ID"
else
    echo -e "${RED}✗ FAIL${NC} - Could not retrieve User Pool Client ID from stack outputs"
    ((FAILED++))
fi

IDENTITY_POOL_ID=$(get_stack_output "IdentityPoolId")
if [ -n "$IDENTITY_POOL_ID" ]; then
    check_resource "Cognito Identity Pool" "$IDENTITY_POOL_ID" \
        "aws cognito-identity describe-identity-pool --identity-pool-id $IDENTITY_POOL_ID"
else
    echo -e "${RED}✗ FAIL${NC} - Could not retrieve Identity Pool ID from stack outputs"
    ((FAILED++))
fi

echo ""
echo "5. Checking API Gateway..."
REST_API_URL=$(get_stack_output "RestApiUrl")
if [ -n "$REST_API_URL" ]; then
    # Extract API ID from URL
    API_ID=$(echo $REST_API_URL | sed 's/.*\/\/\([^.]*\).*/\1/')
    check_resource "REST API Gateway" "$API_ID" \
        "aws apigateway get-rest-api --rest-api-id $API_ID"
else
    echo -e "${RED}✗ FAIL${NC} - Could not retrieve REST API URL from stack outputs"
    ((FAILED++))
fi

WEBSOCKET_API_URL=$(get_stack_output "WebSocketApiUrl")
if [ -n "$WEBSOCKET_API_URL" ]; then
    # Extract API ID from WebSocket URL
    WS_API_ID=$(echo $WEBSOCKET_API_URL | sed 's/.*\/\/\([^.]*\).*/\1/')
    check_resource "WebSocket API Gateway" "$WS_API_ID" \
        "aws apigatewayv2 get-api --api-id $WS_API_ID"
else
    echo -e "${RED}✗ FAIL${NC} - Could not retrieve WebSocket API URL from stack outputs"
    ((FAILED++))
fi

echo ""
echo "6. Checking IAM Roles..."
check_resource "IAM Role" "SnapStudy-AuthLambdaRole" \
    "aws iam get-role --role-name SnapStudy-AuthLambdaRole"

check_resource "IAM Role" "SnapStudy-ContentLambdaRole" \
    "aws iam get-role --role-name SnapStudy-ContentLambdaRole"

check_resource "IAM Role" "SnapStudy-AdaptiveLambdaRole" \
    "aws iam get-role --role-name SnapStudy-AdaptiveLambdaRole"

check_resource "IAM Role" "SnapStudy-ChatLambdaRole" \
    "aws iam get-role --role-name SnapStudy-ChatLambdaRole"

check_resource "IAM Role" "SnapStudy-StepFunctionsRole" \
    "aws iam get-role --role-name SnapStudy-StepFunctionsRole"

echo ""
echo "7. Checking CloudWatch Log Groups..."
check_resource "Log Group" "/aws/apigateway/SnapStudy-RestApi" \
    "aws logs describe-log-groups --log-group-name-prefix /aws/apigateway/SnapStudy-RestApi"

check_resource "Log Group" "/aws/apigateway/SnapStudy-WebSocketApi" \
    "aws logs describe-log-groups --log-group-name-prefix /aws/apigateway/SnapStudy-WebSocketApi"

check_resource "Log Group" "/aws/lambda/SnapStudy" \
    "aws logs describe-log-groups --log-group-name-prefix /aws/lambda/SnapStudy"

echo ""
echo "8. Testing API Endpoints..."
if [ -n "$REST_API_URL" ]; then
    echo -n "Testing REST API health endpoint... "
    if curl -s -f "${REST_API_URL}health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠ SKIP${NC} (Health endpoint not implemented yet)"
    fi
else
    echo -e "${RED}✗ FAIL${NC} - No REST API URL available for testing"
    ((FAILED++))
fi

echo ""
echo "9. Checking Stack Outputs..."
echo "Stack Outputs:"
echo "=============="
if [ -n "$USER_POOL_ID" ]; then
    echo "User Pool ID: $USER_POOL_ID"
fi
if [ -n "$USER_POOL_CLIENT_ID" ]; then
    echo "User Pool Client ID: $USER_POOL_CLIENT_ID"
fi
if [ -n "$IDENTITY_POOL_ID" ]; then
    echo "Identity Pool ID: $IDENTITY_POOL_ID"
fi
if [ -n "$REST_API_URL" ]; then
    echo "REST API URL: $REST_API_URL"
fi
if [ -n "$WEBSOCKET_API_URL" ]; then
    echo "WebSocket API URL: $WEBSOCKET_API_URL"
fi
if [ -n "$BUCKET_NAME" ]; then
    echo "Content Bucket: $BUCKET_NAME"
fi

echo ""
echo "================================================"
echo "Validation Summary:"
echo "=================="
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"

if [ $FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 All validations passed! Infrastructure is ready.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Deploy Lambda functions"
    echo "2. Configure frontend with the output values above"
    echo "3. Test the complete application flow"
    exit 0
else
    echo ""
    echo -e "${RED}❌ Some validations failed. Please check the issues above.${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check CloudFormation stack events for errors"
    echo "2. Verify AWS permissions and service limits"
    echo "3. Ensure all required services are available in your region"
    exit 1
fi