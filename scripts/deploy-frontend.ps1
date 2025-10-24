# Frontend Deployment Script for SnapStudy (PowerShell)
# This script builds the React app and deploys it to AWS S3 with CloudFront invalidation

param(
    [string]$S3Bucket = "aws-hackathon-snapstudy",
    [string]$CloudFrontDistributionId = "E14OU2B88K9RN3",
    [string]$FrontendDir = "frontend"
)

# Set error action preference
$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting frontend deployment..." -ForegroundColor Yellow

# Check if we're in the right directory
if (-not (Test-Path $FrontendDir)) {
    Write-Host "❌ Error: frontend directory not found. Make sure you're in the project root." -ForegroundColor Red
    exit 1
}

# Check if AWS CLI is installed
try {
    aws --version | Out-Null
} catch {
    Write-Host "❌ Error: AWS CLI is not installed. Please install it first." -ForegroundColor Red
    exit 1
}

# Check if Node.js and npm are installed
try {
    npm --version | Out-Null
} catch {
    Write-Host "❌ Error: npm is not installed. Please install Node.js first." -ForegroundColor Red
    exit 1
}

# Navigate to frontend directory
Push-Location $FrontendDir

try {
    Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
    npm install
    
    if ($LASTEXITCODE -ne 0) {
        throw "npm install failed"
    }

    Write-Host "🔨 Building React app..." -ForegroundColor Yellow
    npm run build
    
    if ($LASTEXITCODE -ne 0) {
        throw "npm run build failed"
    }

    # Check if build was successful
    if (-not (Test-Path "build")) {
        throw "Build failed. No build directory found."
    }

    Write-Host "☁️  Uploading to S3 bucket: $S3Bucket" -ForegroundColor Yellow
    aws s3 sync build/ s3://$S3Bucket --delete
    
    if ($LASTEXITCODE -ne 0) {
        throw "S3 sync failed"
    }

    Write-Host "🔄 Creating CloudFront invalidation..." -ForegroundColor Yellow
    $InvalidationResult = aws cloudfront create-invalidation `
        --distribution-id $CloudFrontDistributionId `
        --paths "/*" `
        --query 'Invalidation.Id' `
        --output text
    
    if ($LASTEXITCODE -ne 0) {
        throw "CloudFront invalidation failed"
    }

    Write-Host "✅ Deployment completed successfully!" -ForegroundColor Green
    Write-Host "📋 Invalidation ID: $InvalidationResult" -ForegroundColor Green
    Write-Host "🌐 Your app should be updated in a few minutes." -ForegroundColor Green

} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    # Return to project root
    Pop-Location
}