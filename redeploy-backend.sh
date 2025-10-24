#!/bin/bash

# Quick redeploy of backend to Elastic Beanstalk
# This assumes you have EB CLI installed and configured

set -e

echo "🚀 Redeploying SnapStudy backend to Elastic Beanstalk..."
echo ""

# Check if we're in the backend directory
if [ ! -f "application.py" ]; then
    echo "❌ Please run this script from the backend directory"
    exit 1
fi

# Check if EB CLI is available
if ! command -v eb &> /dev/null; then
    echo "❌ EB CLI not found. Install with: pip install awsebcli"
    echo ""
    echo "Alternative: Deploy manually via AWS Console:"
    echo "1. Zip the backend directory"
    echo "2. Go to Elastic Beanstalk console"
    echo "3. Upload and deploy the zip file"
    exit 1
fi

# Create deployment package (exclude unnecessary files)
echo "📦 Creating deployment package..."
zip -r ../backend-deploy.zip . \
    -x "*.git*" \
    -x "*__pycache__*" \
    -x "*.pyc" \
    -x "*tests*" \
    -x "*infrastructure*" \
    -x "*.md" \
    -x "*deploy*.sh" \
    -x "*update*.sh"

echo "✅ Deployment package created: ../backend-deploy.zip"
echo ""

# Deploy using EB CLI
echo "🚀 Deploying to Elastic Beanstalk..."
eb deploy

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Deployment successful!"
    echo ""
    echo "🧪 Test the updated CORS:"
    echo "   curl -X OPTIONS -H \"Origin: https://example.com\" -H \"Access-Control-Request-Method: POST\" http://snapstudy-backend-env.eba-ygmxm24z.us-east-1.elasticbeanstalk.com/api/v1/auth/login"
    echo ""
    echo "🌐 Test via API Gateway:"
    echo "   curl -X POST -H \"Content-Type: application/json\" https://1w0yyb3an4.execute-api.us-east-1.amazonaws.com/prod/api/v1/auth/login -d '{\"email\":\"test@example.com\",\"password\":\"test123\"}'"
else
    echo "❌ Deployment failed"
    exit 1
fi

# Clean up
rm -f ../backend-deploy.zip