#!/bin/bash

# SnapStudy Backend Deployment Script
# Simple deployment to Elastic Beanstalk - just run it!

set -e

# Configuration
APPLICATION_NAME="snapstudy-backend"
ENVIRONMENT_NAME="snapstudy-backend-env"
BACKEND_DIR="backend"
VERSION_LABEL="v$(date +%Y%m%d-%H%M%S)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Deploying SnapStudy Backend${NC}"
echo "==============================="

# Auto-detect AWS region
AWS_REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")

# Check if backend directory exists
if [ ! -d "$BACKEND_DIR" ]; then
    echo "❌ Backend directory not found: $BACKEND_DIR"
    echo "💡 Make sure you're running this from the project root directory"
    exit 1
fi

# Auto-detect or create S3 bucket
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
S3_BUCKET="${APPLICATION_NAME}-deployments-${ACCOUNT_ID}"

# Create bucket if it doesn't exist
if ! aws s3api head-bucket --bucket "$S3_BUCKET" 2>/dev/null; then
    echo "📦 Creating S3 bucket: $S3_BUCKET"
    if [ "$AWS_REGION" = "us-east-1" ]; then
        aws s3api create-bucket --bucket "$S3_BUCKET" --region "$AWS_REGION" >/dev/null
    else
        aws s3api create-bucket --bucket "$S3_BUCKET" --region "$AWS_REGION" \
            --create-bucket-configuration LocationConstraint="$AWS_REGION" >/dev/null
    fi
    aws s3api put-bucket-versioning --bucket "$S3_BUCKET" \
        --versioning-configuration Status=Enabled >/dev/null
fi

# Create deployment package
TEMP_DIR=$(mktemp -d)
echo "📦 Packaging application..."

# Copy backend files
cp -r "$BACKEND_DIR"/* "$TEMP_DIR/"

# Create application.py if it doesn't exist (Beanstalk expects this)
if [ ! -f "$TEMP_DIR/application.py" ]; then
    if [ -f "$TEMP_DIR/main.py" ]; then
        cat > "$TEMP_DIR/application.py" << 'EOF'
# Beanstalk entry point
from main import app as application

if __name__ == '__main__':
    application.run(debug=False, host='0.0.0.0', port=5000)
EOF
    else
        cat > "$TEMP_DIR/application.py" << 'EOF'
from flask import Flask, jsonify
from flask_cors import CORS

application = Flask(__name__)
CORS(application)

@application.route('/')
def hello():
    return jsonify({"message": "SnapStudy Backend API", "status": "running"})

@application.route('/health')
def health():
    return jsonify({"status": "healthy"})

@application.route('/api/health')
def api_health():
    return jsonify({"status": "healthy", "service": "snapstudy-backend"})

if __name__ == '__main__':
    application.run(debug=False, host='0.0.0.0', port=5000)
EOF
    fi
fi

# Create basic .ebextensions config
mkdir -p "$TEMP_DIR/.ebextensions"
cat > "$TEMP_DIR/.ebextensions/python.config" << 'EOF'
option_settings:
  aws:elasticbeanstalk:container:python:
    WSGIPath: application:application
  aws:elasticbeanstalk:application:environment:
    PYTHONPATH: "/var/app/current:$PYTHONPATH"
    FLASK_ENV: production
EOF

# Package and upload
cd "$TEMP_DIR"
ZIP_FILE="$APPLICATION_NAME-$VERSION_LABEL.zip"
zip -r "$ZIP_FILE" . -x "*.git*" "__pycache__/*" "*.pyc" "venv/*" "*.log" >/dev/null
aws s3 cp "$ZIP_FILE" "s3://$S3_BUCKET/$ZIP_FILE" >/dev/null

# Deploy to Beanstalk
echo "🚀 Deploying to Beanstalk..."

# Create application version
aws elasticbeanstalk create-application-version \
    --application-name "$APPLICATION_NAME" \
    --version-label "$VERSION_LABEL" \
    --description "Deployed on $(date)" \
    --source-bundle S3Bucket="$S3_BUCKET",S3Key="$ZIP_FILE" \
    --region "$AWS_REGION" >/dev/null

# Deploy to environment
aws elasticbeanstalk update-environment \
    --environment-name "$ENVIRONMENT_NAME" \
    --version-label "$VERSION_LABEL" \
    --region "$AWS_REGION" >/dev/null

echo "⏳ Waiting for deployment to complete..."
aws elasticbeanstalk wait environment-updated \
    --environment-names "$ENVIRONMENT_NAME" \
    --region "$AWS_REGION"

# Get environment URL
ENVIRONMENT_URL=$(aws elasticbeanstalk describe-environments \
    --environment-names "$ENVIRONMENT_NAME" \
    --region "$AWS_REGION" \
    --query 'Environments[0].CNAME' \
    --output text)

# Cleanup
rm -rf "$TEMP_DIR"

# Success!
echo ""
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo "=================================="
echo "🌐 Your API is available at: http://$ENVIRONMENT_URL"
echo "🔗 Health check: http://$ENVIRONMENT_URL/health"
echo "📋 Version deployed: $VERSION_LABEL"
echo ""
echo -e "${YELLOW}💡 Update your frontend config to use: http://$ENVIRONMENT_URL/api${NC}"
echo ""
echo "To redeploy after changes, just run this script again!"