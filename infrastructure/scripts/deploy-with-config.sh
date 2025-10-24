#!/bin/bash

# SnapStudy Infrastructure Deployment Script with Environment Configuration

set -e

# Default values
ENVIRONMENT="dev"
PROFILE=""
REGION=""
ACCOUNT_ID=""
ALERT_EMAIL=""
SKIP_TESTS=false
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
    echo "  -e, --environment ENV    Environment to deploy (dev, staging, prod) [default: dev]"
    echo "  -p, --profile PROFILE    AWS profile to use"
    echo "  -r, --region REGION      AWS region to deploy to"
    echo "  -a, --account ACCOUNT    AWS account ID"
    echo "  --alert-email EMAIL      Email for alerts (required for prod)"
    echo "  --skip-tests            Skip running tests before deployment"
    echo "  --skip-confirmation     Skip deployment confirmation"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -e dev"
    echo "  $0 -e staging -p staging-profile"
    echo "  $0 -e prod -p prod-profile --alert-email admin@company.com"
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
        -a|--account)
            ACCOUNT_ID="$2"
            shift 2
            ;;
        --alert-email)
            ALERT_EMAIL="$2"
            shift 2
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
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

print_info "Starting SnapStudy Infrastructure Deployment"
print_info "Environment: $ENVIRONMENT"

# Load environment configuration
CONFIG_FILE="config/environments.json"
if [[ ! -f "$CONFIG_FILE" ]]; then
    print_error "Configuration file not found: $CONFIG_FILE"
    exit 1
fi

# Extract configuration using jq (install if not available)
if ! command -v jq &> /dev/null; then
    print_error "jq is required but not installed. Please install jq first."
    exit 1
fi

STACK_NAME=$(jq -r ".${ENVIRONMENT}.stackName" "$CONFIG_FILE")
CONFIG_REGION=$(jq -r ".${ENVIRONMENT}.region" "$CONFIG_FILE")

# Use provided region or fall back to config
if [[ -z "$REGION" ]]; then
    REGION="$CONFIG_REGION"
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
    print_info "Please run 'aws configure' or set up your AWS credentials."
    exit 1
fi

# Get AWS account ID if not provided
if [[ -z "$ACCOUNT_ID" ]]; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
fi

print_info "AWS Account ID: $ACCOUNT_ID"

# Validate production deployment requirements
if [[ "$ENVIRONMENT" == "prod" ]]; then
    if [[ -z "$ALERT_EMAIL" ]]; then
        print_error "Alert email is required for production deployment."
        print_info "Use --alert-email option to specify an email address."
        exit 1
    fi
    
    if [[ "$SKIP_CONFIRMATION" == false ]]; then
        print_warning "You are about to deploy to PRODUCTION environment!"
        print_warning "This will create/update production resources."
        echo ""
        read -p "Are you sure you want to continue? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            print_info "Deployment cancelled."
            exit 0
        fi
    fi
fi

# Set environment variables
export CDK_DEFAULT_ACCOUNT="$ACCOUNT_ID"
export CDK_DEFAULT_REGION="$REGION"
export ENVIRONMENT="$ENVIRONMENT"
export ALERT_EMAIL="$ALERT_EMAIL"

print_info "Environment variables set:"
print_info "  CDK_DEFAULT_ACCOUNT=$CDK_DEFAULT_ACCOUNT"
print_info "  CDK_DEFAULT_REGION=$CDK_DEFAULT_REGION"
print_info "  ENVIRONMENT=$ENVIRONMENT"
if [[ -n "$ALERT_EMAIL" ]]; then
    print_info "  ALERT_EMAIL=$ALERT_EMAIL"
fi

# Check if CDK is installed
print_info "Checking CDK installation..."
if ! command -v cdk &> /dev/null; then
    print_error "AWS CDK is not installed. Please install it with 'npm install -g aws-cdk'"
    exit 1
fi

CDK_VERSION=$(cdk --version)
print_info "CDK Version: $CDK_VERSION"

# Install dependencies
print_info "Installing dependencies..."
npm install

# Run tests unless skipped
if [[ "$SKIP_TESTS" == false ]]; then
    print_info "Running tests..."
    npm test
    print_success "Tests passed!"
else
    print_warning "Skipping tests as requested."
fi

# Build the project
print_info "Building the project..."
npm run build
print_success "Build completed!"

# Bootstrap CDK if needed
print_info "Checking CDK bootstrap status..."
if ! aws cloudformation describe-stacks --stack-name CDKToolkit --region "$REGION" > /dev/null 2>&1; then
    print_info "CDK not bootstrapped in this region. Bootstrapping..."
    cdk bootstrap "aws://${ACCOUNT_ID}/${REGION}"
    print_success "CDK bootstrap completed!"
else
    print_info "CDK already bootstrapped in this region."
fi

# Synthesize the stack
print_info "Synthesizing CloudFormation template..."
cdk synth "$STACK_NAME"
print_success "Synthesis completed!"

# Show diff if stack exists
print_info "Checking for changes..."
if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" > /dev/null 2>&1; then
    print_info "Stack exists. Showing differences..."
    cdk diff "$STACK_NAME" || true
else
    print_info "Stack does not exist. This will be a new deployment."
fi

# Final confirmation for production
if [[ "$ENVIRONMENT" == "prod" && "$SKIP_CONFIRMATION" == false ]]; then
    echo ""
    print_warning "FINAL CONFIRMATION: Deploy to production?"
    read -p "Type 'DEPLOY' to confirm: " final_confirm
    if [[ "$final_confirm" != "DEPLOY" ]]; then
        print_info "Deployment cancelled."
        exit 0
    fi
fi

# Deploy the stack
print_info "Deploying the stack..."
if [[ "$SKIP_CONFIRMATION" == true ]]; then
    cdk deploy "$STACK_NAME" --require-approval never
else
    cdk deploy "$STACK_NAME"
fi

print_success "Deployment completed successfully!"

# Run validation
print_info "Running post-deployment validation..."
if [[ -f "scripts/validate-deployment.sh" ]]; then
    chmod +x scripts/validate-deployment.sh
    ./scripts/validate-deployment.sh
else
    print_warning "Validation script not found. Skipping validation."
fi

# Show outputs
print_info "Retrieving stack outputs..."
aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue,Description]' \
    --output table

print_success "🎉 Deployment completed successfully!"
echo ""
print_info "Next steps:"
echo "1. Note down the output values above"
echo "2. Configure your frontend application with these values"
echo "3. Deploy your Lambda functions"
echo "4. Test the complete application flow"
echo ""

# Save deployment info
DEPLOYMENT_INFO_FILE="deployments/${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S).json"
mkdir -p deployments

cat > "$DEPLOYMENT_INFO_FILE" << EOF
{
  "environment": "$ENVIRONMENT",
  "stackName": "$STACK_NAME",
  "region": "$REGION",
  "accountId": "$ACCOUNT_ID",
  "deploymentTime": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "cdkVersion": "$CDK_VERSION",
  "deployedBy": "$(whoami)"
}
EOF

print_info "Deployment information saved to: $DEPLOYMENT_INFO_FILE"