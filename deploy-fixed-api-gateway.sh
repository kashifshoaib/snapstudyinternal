#!/bin/bash

# Deploy the fixed API Gateway with explicit CORS handling
echo "Deploying fixed API Gateway with explicit CORS handling..."

# Get the current backend URL
BACKEND_URL="snapstudy-backend-env.eba-ygmxm24z.us-east-1.elasticbeanstalk.com"

# Deploy the CloudFormation stack
aws cloudformation deploy \
  --template-file api-gateway-fixed-cors.yaml \
  --stack-name snapstudy-api-gateway-fixed \
  --parameter-overrides BackendUrl=$BACKEND_URL \
  --capabilities CAPABILITY_IAM \
  --region us-east-1

if [ $? -eq 0 ]; then
    echo "API Gateway deployed successfully!"
    
    # Get the new API Gateway URL
    API_URL=$(aws cloudformation describe-stacks \
      --stack-name snapstudy-api-gateway-fixed \
      --region us-east-1 \
      --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
      --output text)
    
    echo "New API Gateway URL: $API_URL"
    echo ""
    echo "Test the CORS preflight with:"
    echo "curl -X OPTIONS $API_URL/api/v1/auth/login \\"
    echo "  -H 'Origin: https://d334lncig0w4ow.cloudfront.net' \\"
    echo "  -H 'Access-Control-Request-Method: POST' \\"
    echo "  -H 'Access-Control-Request-Headers: content-type' \\"
    echo "  -v"
else
    echo "Failed to deploy API Gateway"
    exit 1
fi