# Simple Pre-Deployment Check for SnapStudy

Write-Host "SnapStudy Pre-Deployment Validation" -ForegroundColor Blue
Write-Host "====================================" -ForegroundColor Blue

$passed = 0
$failed = 0

# Check Node.js
try {
    $nodeVersion = node --version
    Write-Host "[PASS] Node.js $nodeVersion is installed" -ForegroundColor Green
    $passed++
} catch {
    Write-Host "[FAIL] Node.js is not installed" -ForegroundColor Red
    $failed++
}

# Check npm
try {
    $npmVersion = npm --version 2>$null
    Write-Host "[PASS] npm $npmVersion is installed" -ForegroundColor Green
    $passed++
} catch {
    Write-Host "[FAIL] npm is not installed" -ForegroundColor Red
    $failed++
}

# Check AWS CLI
try {
    $awsVersion = aws --version 2>$null
    Write-Host "[PASS] AWS CLI is installed" -ForegroundColor Green
    $passed++
} catch {
    Write-Host "[FAIL] AWS CLI is not installed" -ForegroundColor Red
    $failed++
}

# Check CDK
try {
    $cdkVersion = cdk --version 2>$null
    Write-Host "[PASS] AWS CDK is installed" -ForegroundColor Green
    $passed++
} catch {
    Write-Host "[FAIL] AWS CDK is not installed" -ForegroundColor Red
    $failed++
}

# Check TypeScript
try {
    $tscVersion = tsc --version 2>$null
    Write-Host "[PASS] TypeScript is installed" -ForegroundColor Green
    $passed++
} catch {
    Write-Host "[FAIL] TypeScript is not installed" -ForegroundColor Red
    $failed++
}

Write-Host ""

# Check AWS credentials
Write-Host "Checking AWS credentials..." -ForegroundColor Blue
try {
    $identity = aws sts get-caller-identity 2>$null | ConvertFrom-Json
    if ($identity) {
        Write-Host "[PASS] AWS credentials are valid" -ForegroundColor Green
        Write-Host "       Account ID: $($identity.Account)" -ForegroundColor Gray
        $passed++
    }
} catch {
    Write-Host "[FAIL] AWS credentials are not configured" -ForegroundColor Red
    $failed++
}

Write-Host ""

# Check project files
Write-Host "Checking project structure..." -ForegroundColor Blue

$requiredFiles = @(
    "package.json",
    "tsconfig.json", 
    "cdk.json",
    "lib/snapstudy-stack.ts",
    "bin/snapstudy.ts",
    "config/environments.json"
)

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "[PASS] $file exists" -ForegroundColor Green
        $passed++
    } else {
        Write-Host "[FAIL] $file missing" -ForegroundColor Red
        $failed++
    }
}

# Check node_modules
if (Test-Path "node_modules") {
    Write-Host "[PASS] Dependencies are installed" -ForegroundColor Green
    $passed++
} else {
    Write-Host "[FAIL] Dependencies not installed" -ForegroundColor Red
    $failed++
}

Write-Host ""
Write-Host "====================================" -ForegroundColor Blue
Write-Host "Summary:" -ForegroundColor Blue
Write-Host "Passed: $passed" -ForegroundColor Green
Write-Host "Failed: $failed" -ForegroundColor Red

if ($failed -eq 0) {
    Write-Host "All checks passed! Ready for deployment." -ForegroundColor Green
    exit 0
} else {
    Write-Host "Some checks failed. Please fix the issues before deployment." -ForegroundColor Red
    exit 1
}