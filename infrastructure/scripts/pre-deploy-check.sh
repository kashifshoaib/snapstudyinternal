#!/bin/bash

# SnapStudy Pre-Deployment Validation Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASSED++))
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((WARNINGS++))
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    ((FAILED++))
}

# Function to check command availability
check_command() {
    local cmd=$1
    local description=$2
    
    if command -v "$cmd" &> /dev/null; then
        print_success "$description is installed"
        return 0
    else
        print_error "$description is not installed"
        return 1
    fi
}

# Function to check AWS service availability
check_aws_service() {
    local service=$1
    local region=${2:-us-east-1}
    
    case $service in
        "bedrock")
            if aws bedrock list-foundation-models --region "$region" > /dev/null 2>&1; then
                print_success "AWS Bedrock is available in $region"
            else
                print_warning "AWS Bedrock may not be available in $region or access not enabled"
            fi
            ;;
        "textract")
            if aws textract detect-document-text --document '{"Bytes":""}' --region "$region" 2>&1 | grep -q "InvalidParameterException"; then
                print_success "AWS Textract is available in $region"
            else
                print_warning "AWS Textract may not be available in $region"
            fi
            ;;
        "transcribe")
            if aws transcribe list-transcription-jobs --region "$region" > /dev/null 2>&1; then
                print_success "AWS Transcribe is available in $region"
            else
                print_warning "AWS Transcribe may not be available in $region"
            fi
            ;;
        *)
            print_warning "Unknown service: $service"
            ;;
    esac
}

echo "🔍 SnapStudy Pre-Deployment Validation"
echo "======================================"

# 1. Check required tools
print_info "1. Checking required tools..."
check_command "node" "Node.js"
check_command "npm" "npm"
check_command "aws" "AWS CLI"
check_command "cdk" "AWS CDK"
check_command "jq" "jq (JSON processor)"

# Check Node.js version
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version | sed 's/v//')
    MAJOR_VERSION=$(echo $NODE_VERSION | cut -d. -f1)
    if [ "$MAJOR_VERSION" -ge 18 ]; then
        print_success "Node.js version $NODE_VERSION is supported"
    else
        print_error "Node.js version $NODE_VERSION is not supported. Minimum required: 18.x"
    fi
fi

# Check CDK version
if command -v cdk &> /dev/null; then
    CDK_VERSION=$(cdk --version | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+')
    print_success "CDK version $CDK_VERSION detected"
fi

echo ""

# 2. Check AWS credentials and permissions
print_info "2. Checking AWS credentials and permissions..."

if aws sts get-caller-identity > /dev/null 2>&1; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    USER_ARN=$(aws sts get-caller-identity --query Arn --output text)
    print_success "AWS credentials are valid"
    print_info "Account ID: $ACCOUNT_ID"
    print_info "User/Role: $USER_ARN"
else
    print_error "AWS credentials are not configured or invalid"
fi

# Check basic permissions
print_info "Checking basic AWS permissions..."

# CloudFormation
if aws cloudformation list-stacks --max-items 1 > /dev/null 2>&1; then
    print_success "CloudFormation access confirmed"
else
    print_error "CloudFormation access denied"
fi

# DynamoDB
if aws dynamodb list-tables --max-items 1 > /dev/null 2>&1; then
    print_success "DynamoDB access confirmed"
else
    print_error "DynamoDB access denied"
fi

# S3
if aws s3 ls > /dev/null 2>&1; then
    print_success "S3 access confirmed"
else
    print_error "S3 access denied"
fi

# IAM
if aws iam list-roles --max-items 1 > /dev/null 2>&1; then
    print_success "IAM access confirmed"
else
    print_error "IAM access denied"
fi

echo ""

# 3. Check AWS service availability
print_info "3. Checking AWS service availability..."

REGION=${AWS_DEFAULT_REGION:-us-east-1}
print_info "Checking services in region: $REGION"

check_aws_service "bedrock" "$REGION"
check_aws_service "textract" "$REGION"
check_aws_service "transcribe" "$REGION"

echo ""

# 4. Check project structure and dependencies
print_info "4. Checking project structure..."

# Check required files
required_files=(
    "package.json"
    "tsconfig.json"
    "cdk.json"
    "lib/snapstudy-stack.ts"
    "bin/snapstudy.ts"
    "config/environments.json"
)

for file in "${required_files[@]}"; do
    if [[ -f "$file" ]]; then
        print_success "Required file exists: $file"
    else
        print_error "Required file missing: $file"
    fi
done

# Check if node_modules exists
if [[ -d "node_modules" ]]; then
    print_success "Dependencies are installed"
else
    print_warning "Dependencies not installed. Run 'npm install' first."
fi

echo ""

# 5. Check environment configuration
print_info "5. Checking environment configuration..."

if [[ -f "config/environments.json" ]]; then
    # Validate JSON syntax
    if jq empty config/environments.json > /dev/null 2>&1; then
        print_success "Environment configuration is valid JSON"
        
        # Check required environments
        for env in dev staging prod; do
            if jq -e ".${env}" config/environments.json > /dev/null 2>&1; then
                print_success "Environment '$env' configuration found"
            else
                print_error "Environment '$env' configuration missing"
            fi
        done
    else
        print_error "Environment configuration has invalid JSON syntax"
    fi
else
    print_error "Environment configuration file missing"
fi

echo ""

# 6. Check AWS service limits (basic checks)
print_info "6. Checking AWS service limits..."

# Check DynamoDB table limit
DYNAMODB_TABLES=$(aws dynamodb list-tables --query 'length(TableNames)' --output text 2>/dev/null || echo "0")
if [[ "$DYNAMODB_TABLES" -lt 250 ]]; then
    print_success "DynamoDB table limit OK ($DYNAMODB_TABLES/256)"
else
    print_warning "DynamoDB table limit approaching ($DYNAMODB_TABLES/256)"
fi

# Check S3 bucket limit (soft limit)
S3_BUCKETS=$(aws s3 ls | wc -l 2>/dev/null || echo "0")
if [[ "$S3_BUCKETS" -lt 90 ]]; then
    print_success "S3 bucket limit OK ($S3_BUCKETS/100)"
else
    print_warning "S3 bucket limit approaching ($S3_BUCKETS/100)"
fi

echo ""

# 7. Check for potential conflicts
print_info "7. Checking for potential conflicts..."

# Check if stack already exists
STACK_NAME="SnapStudyStack"
if aws cloudformation describe-stacks --stack-name "$STACK_NAME" > /dev/null 2>&1; then
    STACK_STATUS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --query 'Stacks[0].StackStatus' --output text)
    if [[ "$STACK_STATUS" == "CREATE_COMPLETE" || "$STACK_STATUS" == "UPDATE_COMPLETE" ]]; then
        print_warning "Stack '$STACK_NAME' already exists with status: $STACK_STATUS"
        print_info "This will be an update deployment"
    else
        print_error "Stack '$STACK_NAME' exists but in problematic state: $STACK_STATUS"
    fi
else
    print_success "No existing stack conflicts detected"
fi

# Check for existing resources that might conflict
BUCKET_PREFIX="snapstudy-content"
EXISTING_BUCKETS=$(aws s3 ls | grep "$BUCKET_PREFIX" | wc -l 2>/dev/null || echo "0")
if [[ "$EXISTING_BUCKETS" -gt 0 ]]; then
    print_warning "Found $EXISTING_BUCKETS existing buckets with prefix '$BUCKET_PREFIX'"
fi

echo ""

# 8. Security checks
print_info "8. Running security checks..."

# Check if MFA is enabled (if possible)
if aws sts get-session-token --duration-seconds 900 > /dev/null 2>&1; then
    print_success "AWS session token can be obtained"
else
    print_warning "Cannot obtain session token (MFA may be required for some operations)"
fi

# Check for overly permissive policies (basic check)
if aws iam list-attached-user-policies --user-name "$(aws sts get-caller-identity --query 'Arn' --output text | cut -d'/' -f2)" 2>/dev/null | grep -q "AdministratorAccess"; then
    print_warning "User has AdministratorAccess policy attached"
fi

echo ""

# Summary
echo "======================================"
echo "Pre-Deployment Validation Summary"
echo "======================================"
print_success "Passed: $PASSED"
print_warning "Warnings: $WARNINGS"
print_error "Failed: $FAILED"

echo ""

if [[ $FAILED -eq 0 ]]; then
    if [[ $WARNINGS -eq 0 ]]; then
        print_success "🎉 All checks passed! Ready for deployment."
        exit 0
    else
        print_warning "⚠️  Some warnings detected. Review them before deployment."
        echo ""
        echo "You can proceed with deployment, but consider addressing the warnings."
        exit 0
    fi
else
    print_error "❌ Some critical checks failed. Please fix the issues before deployment."
    echo ""
    echo "Common solutions:"
    echo "1. Install missing tools (Node.js, AWS CLI, CDK, jq)"
    echo "2. Configure AWS credentials: aws configure"
    echo "3. Install project dependencies: npm install"
    echo "4. Check AWS service availability in your region"
    echo "5. Verify IAM permissions for your user/role"
    exit 1
fi