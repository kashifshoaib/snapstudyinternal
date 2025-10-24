#!/bin/bash

# SnapStudy Beanstalk Deployment Configuration
# Source this file to set default deployment parameters
# Usage: source scripts/beanstalk-config.sh

# =============================================================================
# DEPLOYMENT CONFIGURATION - UPDATE THESE VALUES
# =============================================================================

# Beanstalk Application Settings
export BEANSTALK_APPLICATION_NAME="snapstudy-backend"
export BEANSTALK_ENVIRONMENT_NAME="snapstudy-backend-env"

# AWS Settings
export AWS_REGION="us-east-1"  # Change to your preferred region

# S3 Bucket for Deployments (leave empty for auto-detection/creation)
export S3_DEPLOYMENT_BUCKET=""

# CloudFormation Stack Name (if you used CloudFormation to create the infrastructure)
export CLOUDFORMATION_STACK_NAME=""

# Backend Source Directory
export BACKEND_SOURCE_DIR="backend"

# =============================================================================
# DEPLOYMENT FUNCTIONS
# =============================================================================

# Function to deploy with current configuration
deploy_backend() {
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local deploy_script="$script_dir/deploy-app-to-beanstalk.sh"
    
    if [ ! -f "$deploy_script" ]; then
        echo "❌ Deploy script not found: $deploy_script"
        return 1
    fi
    
    local args=()
    
    # Add arguments based on configuration
    if [ ! -z "$BEANSTALK_APPLICATION_NAME" ]; then
        args+=("-a" "$BEANSTALK_APPLICATION_NAME")
    fi
    
    if [ ! -z "$BEANSTALK_ENVIRONMENT_NAME" ]; then
        args+=("-e" "$BEANSTALK_ENVIRONMENT_NAME")
    fi
    
    if [ ! -z "$AWS_REGION" ]; then
        args+=("-r" "$AWS_REGION")
    fi
    
    if [ ! -z "$S3_DEPLOYMENT_BUCKET" ]; then
        args+=("-s" "$S3_DEPLOYMENT_BUCKET")
    fi
    
    if [ ! -z "$CLOUDFORMATION_STACK_NAME" ]; then
        args+=("--stack-name" "$CLOUDFORMATION_STACK_NAME")
    fi
    
    if [ ! -z "$BACKEND_SOURCE_DIR" ]; then
        args+=("-b" "$BACKEND_SOURCE_DIR")
    fi
    
    echo "🚀 Deploying with configuration:"
    echo "   Application: $BEANSTALK_APPLICATION_NAME"
    echo "   Environment: $BEANSTALK_ENVIRONMENT_NAME"
    echo "   Region: $AWS_REGION"
    echo ""
    
    "$deploy_script" "${args[@]}"
}

# Function to show current configuration
show_config() {
    echo "📋 Current Beanstalk Configuration:"
    echo "=================================="
    echo "Application Name: ${BEANSTALK_APPLICATION_NAME:-'(not set)'}"
    echo "Environment Name: ${BEANSTALK_ENVIRONMENT_NAME:-'(not set)'}"
    echo "AWS Region: ${AWS_REGION:-'(not set)'}"
    echo "S3 Bucket: ${S3_DEPLOYMENT_BUCKET:-'(auto-detect)'}"
    echo "CloudFormation Stack: ${CLOUDFORMATION_STACK_NAME:-'(not used)'}"
    echo "Backend Directory: ${BACKEND_SOURCE_DIR:-'backend'}"
    echo ""
    echo "💡 To deploy: run 'deploy_backend' or use the script directly"
}

# Function to check Beanstalk environment status
check_environment() {
    if [ -z "$BEANSTALK_ENVIRONMENT_NAME" ] || [ -z "$AWS_REGION" ]; then
        echo "❌ Environment name and region must be configured"
        return 1
    fi
    
    echo "🔍 Checking environment status..."
    aws elasticbeanstalk describe-environments \
        --environment-names "$BEANSTALK_ENVIRONMENT_NAME" \
        --region "$AWS_REGION" \
        --query 'Environments[0].{Name:EnvironmentName,Status:Status,Health:Health,URL:CNAME,Version:VersionLabel}' \
        --output table
}

# Function to view recent logs
view_logs() {
    if [ -z "$BEANSTALK_ENVIRONMENT_NAME" ] || [ -z "$AWS_REGION" ]; then
        echo "❌ Environment name and region must be configured"
        return 1
    fi
    
    echo "📋 Viewing recent logs for $BEANSTALK_ENVIRONMENT_NAME..."
    aws logs tail "/aws/elasticbeanstalk/$BEANSTALK_ENVIRONMENT_NAME/var/log/eb-engine.log" \
        --region "$AWS_REGION" \
        --follow
}

# =============================================================================
# ALIASES FOR CONVENIENCE
# =============================================================================

alias eb-deploy='deploy_backend'
alias eb-config='show_config'
alias eb-status='check_environment'
alias eb-logs='view_logs'

# =============================================================================
# INITIALIZATION
# =============================================================================

# Show configuration when sourced
if [ "${BASH_SOURCE[0]}" != "${0}" ]; then
    echo "✅ Beanstalk configuration loaded"
    echo "💡 Available commands: deploy_backend, show_config, check_environment, view_logs"
    echo "💡 Available aliases: eb-deploy, eb-config, eb-status, eb-logs"
    echo ""
fi