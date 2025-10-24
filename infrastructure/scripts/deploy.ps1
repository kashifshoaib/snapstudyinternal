# SnapStudy Simple Deployment Script

param(
    [string]$Environment = "dev",
    [switch]$SkipTests = $false,
    [switch]$SkipConfirmation = $false
)

# Colors for output
function Write-Info {
    param($message)
    Write-Host "[INFO] $message" -ForegroundColor Blue
}

function Write-Success {
    param($message)
    Write-Host "[SUCCESS] $message" -ForegroundColor Green
}

function Write-Warning {
    param($message)
    Write-Host "[WARNING] $message" -ForegroundColor Yellow
}

function Write-Error {
    param($message)
    Write-Host "[ERROR] $message" -ForegroundColor Red
}

Write-Info "Starting SnapStudy Infrastructure Deployment"
Write-Info "Environment: $Environment"

# Step 1: Load environment variables from .env file
Write-Info "Loading environment variables from .env file..."
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            
            # Remove quotes if present
            if ($value -match '^"(.*)"$' -or $value -match "^'(.*)'$") {
                $value = $matches[1]
            }
            
            [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
            Write-Info "Set $name"
        }
    }
    Write-Success "Environment variables loaded from .env file"
} else {
    Write-Warning ".env file not found"
}

# Step 2: Set deployment environment
$env:ENVIRONMENT = $Environment
Write-Info "Deployment Environment: $Environment"

# Step 3: Check if AWS credentials are available
if ($env:AWS_ACCESS_KEY_ID -and $env:AWS_SECRET_ACCESS_KEY) {
    Write-Success "AWS credentials found in environment"
} else {
    Write-Warning "AWS credentials not found in environment variables"
    Write-Info "Make sure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set"
}

# Step 4: Install dependencies
Write-Info "Installing dependencies..."
try {
    npm install
    Write-Success "Dependencies installed"
} catch {
    Write-Error "Failed to install dependencies: $_"
    exit 1
}

# Step 5: Build the project
Write-Info "Building the project..."
try {
    npm run build
    Write-Success "Build completed"
} catch {
    Write-Error "Build failed: $_"
    exit 1
}

# Step 6: Bootstrap CDK if needed
Write-Info "Checking CDK bootstrap status..."
try {
    $region = $env:AWS_REGION
    if (-not $region) { $region = "us-east-1" }
    
    $bootstrapCheck = aws cloudformation describe-stacks --stack-name CDKToolkit --region $region 2>$null
    if (-not $bootstrapCheck) {
        Write-Info "CDK not bootstrapped. Bootstrapping..."
        cdk bootstrap
        Write-Success "CDK bootstrap completed"
    } else {
        Write-Info "CDK already bootstrapped"
    }
} catch {
    Write-Warning "Could not check bootstrap status, proceeding anyway"
}

# Step 7: Synthesize the stack
Write-Info "Synthesizing CloudFormation template..."
try {
    cdk synth
    Write-Success "Synthesis completed"
} catch {
    Write-Error "Synthesis failed: $_"
    exit 1
}

# Step 8: Final confirmation for production
if ($Environment -eq "prod" -and -not $SkipConfirmation) {
    Write-Warning "You are about to deploy to PRODUCTION!"
    $confirmation = Read-Host "Type 'DEPLOY' to confirm"
    if ($confirmation -ne "DEPLOY") {
        Write-Info "Deployment cancelled"
        exit 0
    }
}

# Step 9: Deploy the stack
Write-Info "Deploying the stack..."
try {
    if ($SkipConfirmation) {
        cdk deploy --require-approval never
    } else {
        cdk deploy
    }
    Write-Success "Deployment completed successfully!"
} catch {
    Write-Error "Deployment failed: $_"
    exit 1
}

# Step 10: Show outputs
Write-Info "Retrieving stack outputs..."
try {
    $stackName = "SnapStudyStack"
    $region = $env:AWS_REGION
    if (-not $region) { $region = "us-east-1" }
    
    aws cloudformation describe-stacks --stack-name $stackName --region $region --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue,Description]' --output table
} catch {
    Write-Warning "Could not retrieve stack outputs"
}

Write-Success "Deployment completed successfully!"
Write-Info ""
Write-Info "Next steps:"
Write-Info "1. Note down the output values above"
Write-Info "2. Configure your frontend application with these values"
Write-Info "3. Deploy your Lambda functions"
Write-Info "4. Test the complete application flow"