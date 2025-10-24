#!/bin/bash

echo "Redeploying backend with missing a2wsgi dependency..."

cd backend

# Create a new application version with updated requirements
echo "Creating application version with updated dependencies..."

# Zip the application
zip -r ../backend-with-deps.zip . -x "*.git*" "*__pycache__*" "*.pyc" "tests/*"

# Upload to S3 (you may need to adjust the bucket name)
BUCKET_NAME="elasticbeanstalk-us-east-1-$(aws sts get-caller-identity --query Account --output text)"
VERSION_LABEL="backend-with-deps-$(date +%Y%m%d-%H%M%S)"

echo "Uploading to S3..."
aws s3 cp ../backend-with-deps.zip s3://$BUCKET_NAME/$VERSION_LABEL.zip

# Create application version
echo "Creating application version..."
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

echo "Deployment initiated. Check the Elastic Beanstalk console for progress."
echo "Environment URL: http://snapstudy-backend-env.eba-ygmxm24z.us-east-1.elasticbeanstalk.com"

# Clean up
rm ../backend-with-deps.zip

cd ..