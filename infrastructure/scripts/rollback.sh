#!/bin/bash

# SnapStudy Infrastructure Rollback Script

set -e

# Default values
ENVIRONMENT="dev"
PROFILE=""
REGION=""
STACK_NAME=""
SKIP_CONFIRMATION=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -e, --environment ENV    Environment to rollback (dev, staging, prod) [default: dev]"
    echo "  -p, --profile PROFILE    AWS profile to use"
    echo "  -r, --region REGION      AWS region"
    echo "  -s, --stack-name NAME    Stack name to rollback"
    echo "  --skip-confirmation     Skip rollback confirmation"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -e dev"
    echo "  $0 -e prod -p prod-profile --stack-name SnapStudy-Production"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -p|--profile)
            PROFILE="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -s|--stack-name)
            STACK_NAME="$2"
            shift 2
            ;;
        --skip-confirmation)
            SKIP_CONFIRMATION=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    print_error "Invalid environment: $ENVIRONMENT. Must be dev, staging, or prod."
    exit 1
fi

print_warning "🔄 Starting SnapStudy Infrastructure Rollback"
print_info "Environment: $ENVIRONMENT"

# Load environment configuration if available
CONFIG_FILE="config/environments.json"
if [[ -f "$CONFIG_FILE" ]] && command -v jq &> /dev/null; then
    if [[ -z "$STACK_NAME" ]]; then
        STACK_NAME=$(jq -r ".${ENVIRONMENT}.stackName" "$CONFIG_FILE")
    fi
    if [[ -z "$REGION" ]]; then
        REGION=$(jq -r ".${ENVIRONMENT}.region" "$CONFIG_FILE")
    fi
fi

# Set defaults if still empty
if [[ -z "$STACK_NAME" ]]; then
    case $ENVIRONMENT in
        "dev") STACK_NAME="SnapStudy-Dev" ;;
        "staging") STACK_NAME="SnapStudy-Staging" ;;
        "prod") STACK_NAME="SnapStudy-Production" ;;
    esac
fi

if [[ -z "$REGION" ]]; then
    REGION="us-east-1"
fi

print_info "Stack Name: $STACK_NAME"
print_info "Region: $REGION"

# Set AWS profile if provided
if [[ -n "$PROFILE" ]]; then
    export AWS_PROFILE="$PROFILE"
    print_info "Using AWS Profile: $PROFILE"
fi

# Check if AWS CLI is configured
print_info "Checking AWS CLI configuration..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    print_error "AWS CLI is not configured or credentials are invalid."
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
print_info "AWS Account ID: $ACCOUNT_ID"

# Check if stack exists
print_info "Checking stack status..."
if ! aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" > /dev/null 2>&1; then
    print_error "Stack '$STACK_NAME' does not exist in region '$REGION'"
    exit 1
fi

STACK_STATUS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].StackStatus' --output text)
print_info "Current stack status: $STACK_STATUS"

# Check if rollback is possible
case $STACK_STATUS in
    "UPDATE_FAILED"|"UPDATE_ROLLBACK_FAILED"|"CREATE_FAILED")
        print_info "Stack is in a failed state. Rollback is possible."
        ;;
    "UPDATE_COMPLETE"|"CREATE_COMPLETE")
        print_warning "Stack is in a stable state. This will rollback to the previous version."
        ;;
    "UPDATE_IN_PROGRESS"|"CREATE_IN_PROGRESS"|"DELETE_IN_PROGRESS")
        print_error "Stack is currently being modified. Cannot rollback now."
        print_info "Wait for the current operation to complete, then try again."
        exit 1
        ;;
    "ROLLBACK_IN_PROGRESS"|"UPDATE_ROLLBACK_IN_PROGRESS")
        print_error "Stack is already rolling back."
        exit 1
        ;;
    *)
        print_warning "Stack status '$STACK_STATUS' may not support rollback."
        ;;
esac

# Get stack events to show recent changes
print_info "Recent stack events:"
aws cloudformation describe-stack-events \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --max-items 10 \
    --query 'StackEvents[*].[Timestamp,ResourceStatus,ResourceType,LogicalResourceId]' \
    --output table

# Show what will be rolled back
print_info "Checking rollback target..."
if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].LastUpdatedTime' --output text > /dev/null 2>&1; then
    LAST_UPDATE=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].LastUpdatedTime' --output text)
    print_info "Stack was last updated: $LAST_UPDATE"
    print_warning "Rollback will revert changes made after this time."
else
    print_info "This appears to be the initial stack creation."
fi

# Production safety check
if [[ "$ENVIRONMENT" == "prod" ]]; then
    print_error "🚨 PRODUCTION ROLLBACK DETECTED!"
    print_error "This will rollback production infrastructure!"
    echo ""
    
    if [[ "$SKIP_CONFIRMATION" == false ]]; then
        print_warning "Please confirm the following:"
        echo "1. You have notified the team about this rollback"
        echo "2. You have identified the issue requiring rollback"
        echo "3. You understand the impact of rolling back"
        echo ""
        read -p "Type 'ROLLBACK_PRODUCTION' to confirm: " prod_confirm
        
        if [[ "$prod_confirm" != "ROLLBACK_PRODUCTION" ]]; then
            print_info "Rollback cancelled."
            exit 0
        fi
    fi
fi

# Final confirmation
if [[ "$SKIP_CONFIRMATION" == false ]]; then
    echo ""
    print_warning "⚠️  FINAL CONFIRMATION"
    print_warning "This will rollback stack: $STACK_NAME"
    print_warning "Environment: $ENVIRONMENT"
    print_warning "Region: $REGION"
    echo ""
    read -p "Are you sure you want to proceed? (yes/no): " confirm
    
    if [[ "$confirm" != "yes" ]]; then
        print_info "Rollback cancelled."
        exit 0
    fi
fi

# Perform rollback based on stack status
print_info "Starting rollback process..."

case $STACK_STATUS in
    "UPDATE_FAILED"|"UPDATE_ROLLBACK_FAILED")
        print_info "Continuing failed rollback..."
        aws cloudformation continue-update-rollback \
            --stack-name "$STACK_NAME" \
            --region "$REGION"
        ;;
    "CREATE_FAILED")
        print_info "Deleting failed stack..."
        aws cloudformation delete-stack \
            --stack-name "$STACK_NAME" \
            --region "$REGION"
        ;;
    *)
        print_info "Initiating stack rollback..."
        # For CDK stacks, we need to use CDK rollback if available
        if command -v cdk &> /dev/null && [[ -f "cdk.json" ]]; then
            print_info "Using CDK for rollback..."
            # CDK doesn't have direct rollback, so we'll use CloudFormation
            aws cloudformation cancel-update-stack \
                --stack-name "$STACK_NAME" \
                --region "$REGION" 2>/dev/null || true
            
            # Wait a moment and then check if we can continue rollback
            sleep 5
            
            CURRENT_STATUS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].StackStatus' --output text)
            if [[ "$CURRENT_STATUS" == "UPDATE_ROLLBACK_IN_PROGRESS" ]]; then
                print_info "Rollback initiated successfully."
            else
                print_warning "Could not initiate automatic rollback. Manual intervention may be required."
            fi
        else
            print_warning "CDK not available. Using CloudFormation directly."
            aws cloudformation cancel-update-stack \
                --stack-name "$STACK_NAME" \
                --region "$REGION"
        fi
        ;;
esac

# Monitor rollback progress
print_info "Monitoring rollback progress..."
print_info "You can also monitor progress in the AWS Console:"
print_info "https://console.aws.amazon.com/cloudformation/home?region=${REGION}#/stacks/stackinfo?stackId=${STACK_NAME}"

# Wait for rollback to complete
TIMEOUT=1800  # 30 minutes
ELAPSED=0
INTERVAL=30

while [[ $ELAPSED -lt $TIMEOUT ]]; do
    CURRENT_STATUS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "STACK_NOT_FOUND")
    
    case $CURRENT_STATUS in
        "UPDATE_ROLLBACK_COMPLETE"|"DELETE_COMPLETE")
            print_success "Rollback completed successfully!"
            break
            ;;
        "UPDATE_ROLLBACK_FAILED"|"DELETE_FAILED")
            print_error "Rollback failed!"
            print_info "Check the CloudFormation console for details."
            exit 1
            ;;
        "STACK_NOT_FOUND")
            print_success "Stack has been deleted successfully!"
            break
            ;;
        "UPDATE_ROLLBACK_IN_PROGRESS"|"DELETE_IN_PROGRESS")
            print_info "Rollback in progress... (${ELAPSED}s elapsed)"
            ;;
        *)
            print_info "Current status: $CURRENT_STATUS (${ELAPSED}s elapsed)"
            ;;
    esac
    
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [[ $ELAPSED -ge $TIMEOUT ]]; then
    print_error "Rollback timed out after ${TIMEOUT} seconds."
    print_info "Check the CloudFormation console for current status."
    exit 1
fi

# Show final status
FINAL_STATUS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "STACK_NOT_FOUND")

if [[ "$FINAL_STATUS" != "STACK_NOT_FOUND" ]]; then
    print_info "Final stack status: $FINAL_STATUS"
    
    # Show recent events
    print_info "Recent rollback events:"
    aws cloudformation describe-stack-events \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --max-items 10 \
        --query 'StackEvents[*].[Timestamp,ResourceStatus,ResourceType,LogicalResourceId,ResourceStatusReason]' \
        --output table
fi

# Log rollback information
ROLLBACK_INFO_FILE="rollbacks/${ENVIRONMENT}-rollback-$(date +%Y%m%d-%H%M%S).json"
mkdir -p rollbacks

cat > "$ROLLBACK_INFO_FILE" << EOF
{
  "environment": "$ENVIRONMENT",
  "stackName": "$STACK_NAME",
  "region": "$REGION",
  "accountId": "$ACCOUNT_ID",
  "rollbackTime": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "originalStatus": "$STACK_STATUS",
  "finalStatus": "$FINAL_STATUS",
  "rolledBackBy": "$(whoami)"
}
EOF

print_info "Rollback information saved to: $ROLLBACK_INFO_FILE"

print_success "🎉 Rollback process completed!"
echo ""
print_info "Next steps:"
echo "1. Verify that the application is working correctly"
echo "2. Investigate the root cause of the issue that required rollback"
echo "3. Fix the issue and prepare for a new deployment"
echo "4. Update monitoring and alerting if needed"
echo ""

if [[ "$ENVIRONMENT" == "prod" ]]; then
    print_warning "Don't forget to:"
    echo "- Notify stakeholders about the rollback"
    echo "- Update incident documentation"
    echo "- Schedule a post-mortem if needed"
fi