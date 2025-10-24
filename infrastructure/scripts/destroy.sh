#!/bin/bash

# SnapStudy Infrastructure Destruction Script

set -e

echo "🗑️ Starting SnapStudy Infrastructure Destruction"

# Warning message
echo "⚠️  WARNING: This will destroy all AWS resources created by the SnapStudy stack."
echo "⚠️  This action cannot be undone!"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Destruction cancelled."
    exit 0
fi

# Additional confirmation for production
if [ "$ENVIRONMENT" = "prod" ] || [ "$ENVIRONMENT" = "production" ]; then
    echo "🚨 PRODUCTION ENVIRONMENT DETECTED!"
    echo "🚨 This will destroy production resources!"
    echo ""
    read -p "Type 'DESTROY_PRODUCTION' to confirm: " prod_confirm
    
    if [ "$prod_confirm" != "DESTROY_PRODUCTION" ]; then
        echo "❌ Production destruction cancelled."
        exit 0
    fi
fi

# Destroy the stack
echo "🗑️ Destroying the stack..."
cdk destroy --force

echo "✅ Destruction completed!"
echo ""
echo "📋 Manual cleanup required:"
echo "1. Check S3 buckets for any remaining objects"
echo "2. Verify DynamoDB tables are deleted (if retention policy allows)"
echo "3. Check CloudWatch logs for any remaining log groups"
echo ""