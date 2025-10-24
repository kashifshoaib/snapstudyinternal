#!/bin/bash

# Create a new API Gateway with proper CORS using AWS CLI
# This bypasses CloudFormation issues

set -e

BACKEND_URL="snapstudy-backend-env.eba-ygmxm24z.us-east-1.elasticbeanstalk.com"
REGION="us-east-1"
API_NAME="SnapStudy-Backend-Proxy-v2"

echo "🚀 Creating new API Gateway with proper CORS..."
echo "   Backend URL: $BACKEND_URL"
echo "   Region: $REGION"
echo ""

# Create REST API
echo "📦 Creating REST API..."
API_ID=$(aws apigateway create-rest-api \
    --name "$API_NAME" \
    --description "HTTPS proxy to SnapStudy backend with CORS" \
    --endpoint-configuration types=REGIONAL \
    --region $REGION \
    --query 'id' \
    --output text)

echo "✅ API created with ID: $API_ID"

# Get root resource ID
ROOT_RESOURCE_ID=$(aws apigateway get-resources \
    --rest-api-id $API_ID \
    --region $REGION \
    --query 'items[0].id' \
    --output text)

echo "✅ Root resource ID: $ROOT_RESOURCE_ID"

# Create {proxy+} resource
echo "📦 Creating proxy resource..."
PROXY_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_RESOURCE_ID \
    --path-part '{proxy+}' \
    --region $REGION \
    --query 'id' \
    --output text)

echo "✅ Proxy resource ID: $PROXY_RESOURCE_ID"

# Add OPTIONS method to root resource
echo "📦 Adding OPTIONS method to root..."
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $ROOT_RESOURCE_ID \
    --http-method OPTIONS \
    --authorization-type NONE \
    --region $REGION

# Add OPTIONS integration to root resource
aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $ROOT_RESOURCE_ID \
    --http-method OPTIONS \
    --type MOCK \
    --integration-http-method OPTIONS \
    --request-templates '{"application/json": "{\"statusCode\": 200}"}' \
    --region $REGION

# Add OPTIONS method response to root resource
aws apigateway put-method-response \
    --rest-api-id $API_ID \
    --resource-id $ROOT_RESOURCE_ID \
    --http-method OPTIONS \
    --status-code 200 \
    --response-parameters \
        'method.response.header.Access-Control-Allow-Origin=true,method.response.header.Access-Control-Allow-Methods=true,method.response.header.Access-Control-Allow-Headers=true' \
    --region $REGION

# Add OPTIONS integration response to root resource
aws apigateway put-integration-response \
    --rest-api-id $API_ID \
    --resource-id $ROOT_RESOURCE_ID \
    --http-method OPTIONS \
    --status-code 200 \
    --response-parameters \
        'method.response.header.Access-Control-Allow-Origin='"'"'*'"'"',method.response.header.Access-Control-Allow-Methods='"'"'GET,POST,PUT,DELETE,OPTIONS,PATCH'"'"',method.response.header.Access-Control-Allow-Headers='"'"'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Requested-With'"'"'' \
    --region $REGION

# Add OPTIONS method to proxy resource
echo "📦 Adding OPTIONS method to proxy..."
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $PROXY_RESOURCE_ID \
    --http-method OPTIONS \
    --authorization-type NONE \
    --region $REGION

# Add OPTIONS integration to proxy resource
aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $PROXY_RESOURCE_ID \
    --http-method OPTIONS \
    --type MOCK \
    --integration-http-method OPTIONS \
    --request-templates '{"application/json": "{\"statusCode\": 200}"}' \
    --region $REGION

# Add OPTIONS method response to proxy resource
aws apigateway put-method-response \
    --rest-api-id $API_ID \
    --resource-id $PROXY_RESOURCE_ID \
    --http-method OPTIONS \
    --status-code 200 \
    --response-parameters \
        'method.response.header.Access-Control-Allow-Origin=true,method.response.header.Access-Control-Allow-Methods=true,method.response.header.Access-Control-Allow-Headers=true' \
    --region $REGION

# Add OPTIONS integration response to proxy resource
aws apigateway put-integration-response \
    --rest-api-id $API_ID \
    --resource-id $PROXY_RESOURCE_ID \
    --http-method OPTIONS \
    --status-code 200 \
    --response-parameters \
        'method.response.header.Access-Control-Allow-Origin='"'"'*'"'"',method.response.header.Access-Control-Allow-Methods='"'"'GET,POST,PUT,DELETE,OPTIONS,PATCH'"'"',method.response.header.Access-Control-Allow-Headers='"'"'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Requested-With'"'"'' \
    --region $REGION

# Add ANY method to root resource
echo "📦 Adding ANY method to root..."
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $ROOT_RESOURCE_ID \
    --http-method ANY \
    --authorization-type NONE \
    --region $REGION

# Add ANY integration to root resource
aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $ROOT_RESOURCE_ID \
    --http-method ANY \
    --type HTTP_PROXY \
    --integration-http-method ANY \
    --uri "http://$BACKEND_URL/" \
    --region $REGION

# Add ANY method to proxy resource
echo "📦 Adding ANY method to proxy..."
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $PROXY_RESOURCE_ID \
    --http-method ANY \
    --authorization-type NONE \
    --request-parameters 'method.request.path.proxy=true' \
    --region $REGION

# Add ANY integration to proxy resource
aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $PROXY_RESOURCE_ID \
    --http-method ANY \
    --type HTTP_PROXY \
    --integration-http-method ANY \
    --uri "http://$BACKEND_URL/{proxy}" \
    --request-parameters 'integration.request.path.proxy=method.request.path.proxy' \
    --region $REGION

# Create deployment
echo "📦 Creating deployment..."
DEPLOYMENT_ID=$(aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name prod \
    --region $REGION \
    --query 'id' \
    --output text)

echo "✅ Deployment created with ID: $DEPLOYMENT_ID"

# Get the new API Gateway URL
NEW_API_URL="https://$API_ID.execute-api.$REGION.amazonaws.com/prod"

echo ""
echo "🎉 New API Gateway created successfully!"
echo ""
echo "🌐 New API Gateway URL:"
echo "   $NEW_API_URL"
echo ""
echo "🧪 Test CORS preflight:"
echo "   curl -X OPTIONS -H \"Origin: https://example.com\" -H \"Access-Control-Request-Method: POST\" $NEW_API_URL/api/v1/auth/login"
echo ""
echo "🧪 Test health endpoint:"
echo "   curl $NEW_API_URL/health"
echo ""
echo "📝 Update your frontend config with the new URL:"
echo "   const API_BASE_URL = '$NEW_API_URL';"
echo ""
echo "🗑️  Don't forget to delete the old API Gateway if this works!"
echo ""