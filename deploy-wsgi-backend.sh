#!/bin/bash

echo "Deploying backend with WSGI compatibility (no a2wsgi dependency)..."

cd backend

echo "Current requirements.txt:"
cat requirements.txt

# Create deployment package
echo "Creating deployment package..."
zip -r ../backend-wsgi.zip . -x "*.git*" "*__pycache__*" "*.pyc" "tests/*" "requirements-*.txt"

# Get AWS account ID for S3 bucket
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="elasticbeanstalk-us-east-1-$ACCOUNT_ID"
VERSION_LABEL="backend-wsgi-$(date +%Y%m%d-%H%M%S)"

echo "Uploading to S3 bucket: $BUCKET_NAME"
aws s3 cp ../backend-wsgi.zip s3://$BUCKET_NAME/$VERSION_LABEL.zip

# Create application version
echo "Creating application version: $VERSION_LABEL"
aws elasticbeanstalk create-application-version \
    --application-name "snapstudy-backend" \
    --version-label "$VERSION_LABEL" \
    --source-bundle S3Bucket="$BUCKET_NAME",S3Key="$VERSION_LABEL.zip" \
    --region us-east-1

# Deploy to environment
echo "Deploying to environment..."
aws elasticbeanstalk update-environment \
    --environment-name "snapstudy-backend-env" \
    --version-label "$VERSION_LABEL" \
    --region us-east-1

echo "Deployment initiated with WSGI compatibility."
echo "Environment URL: http://snapstudy-backend-env.eba-ygmxm24z.us-east-1.elasticbeanstalk.com"
echo ""
echo "This version provides basic CORS support and health endpoints."
echo "Once deployed successfully, we can work on adding full FastAPI functionality."

# Clean up
rm ../backend-wsgi.zip

cd ..