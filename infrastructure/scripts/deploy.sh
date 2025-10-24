#!/bin/bash

# SnapStudy Infrastructure Deployment Script

set -e

echo "🚀 Starting SnapStudy Infrastructure Deployment"

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI is not configured. Please run 'aws configure' first."
    exit 1
fi

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    echo "❌ AWS CDK is not installed. Please install it with 'npm install -g aws-cdk'"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Build the project
echo "🔨 Building the project..."
npm run build

# Bootstrap CDK (if not already done)
echo "🏗️ Bootstrapping CDK..."
cdk bootstrap

# Synthesize the stack
echo "🔍 Synthesizing the stack..."
cdk synth

# Deploy the stack
echo "🚀 Deploying the stack..."
cdk deploy --require-approval never

echo "✅ Deployment completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Note down the output values (User Pool ID, API Gateway URLs, etc.)"
echo "2. Configure your frontend application with these values"
echo "3. Set up your Lambda functions in the backend directory"
echo ""