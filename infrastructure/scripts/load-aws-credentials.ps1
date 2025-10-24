# Load AWS Credentials Script
# This script loads AWS credentials exclusively from .env file

param(
    [switch]$Verbose
)

function Write-Info {
    param($message)
    if ($Verbose) {
        Write-Host "[INFO] $message" -ForegroundColor Blue
    }
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

function Load-EnvFile {
    param($filePath)
    
    if (Test-Path $filePath) {
        Write-Info "Loading environment variables from $filePath"
        
        Get-Content $filePath | ForEach-Object {
            if ($_ -match '^([^#][^=]+)=(.*)$') {
                $name = $matches[1].Trim()
                $value = $matches[2].Trim()
                
                # Remove quotes if present
                if ($value -match '^"(.*)"$' -or $value -match "^'(.*)'$") {
                    $value = $matches[1]
                }
                
                # Always set from .env file, overriding any existing environment variables
                [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
                Write-Info "Set $name from .env file"
            }
        }
        return $true
    } else {
        Write-Warning ".env file not found at $filePath"
        return $false
    }
}

function Test-AwsCredentials {
    Write-Info "Testing AWS credentials..."
    
    try {
        # Clear any profile settings to use environment variables
        $env:AWS_PROFILE = $null
        $identity = aws sts get-caller-identity 2>$null | ConvertFrom-Json
        if ($identity) {
            Write-Success "AWS credentials are valid"
            Write-Info "Account ID: $($identity.Account)"
            Write-Info "User ARN: $($identity.Arn)"
            return $true
        }
    } catch {
        Write-Warning "AWS credentials test failed: $_"
        return $false
    }
    
    return $false
}

# Main execution
Write-Info "Loading AWS credentials from .env file only..."

# Load credentials exclusively from .env file
$envFileLoaded = Load-EnvFile ".env"

if (-not $envFileLoaded) {
    Write-Error "No .env file found"
    Write-Host ""
    Write-Host "To configure AWS credentials:" -ForegroundColor Yellow
    Write-Host "1. Create a .env file in the infrastructure directory" -ForegroundColor Yellow
    Write-Host "2. Add the following variables:" -ForegroundColor Yellow
    Write-Host "   AWS_ACCESS_KEY_ID=your_access_key" -ForegroundColor Gray
    Write-Host "   AWS_SECRET_ACCESS_KEY=your_secret_key" -ForegroundColor Gray
    Write-Host "   AWS_REGION=your_region" -ForegroundColor Gray
    Write-Host "   AWS_ACCOUNT_ID=your_account_id" -ForegroundColor Gray
    exit 1
}

# Check if required credentials are now available
if ($env:AWS_ACCESS_KEY_ID -and $env:AWS_SECRET_ACCESS_KEY) {
    Write-Success "AWS credentials loaded from .env file"
    
    # Test credentials
    if (Test-AwsCredentials) {
        Write-Success "AWS credentials are configured and valid"
    } else {
        Write-Warning "AWS credentials loaded but validation failed"
        Write-Info "This may be due to expired credentials or network issues"
    }
    
    # Display current configuration
    Write-Host ""
    Write-Host "Current AWS Configuration:" -ForegroundColor Cyan
    Write-Host "=========================" -ForegroundColor Cyan
    
    if ($env:AWS_REGION) {
        Write-Host "Region: $env:AWS_REGION" -ForegroundColor Gray
    }
    if ($env:AWS_ACCOUNT_ID) {
        Write-Host "Account ID: $env:AWS_ACCOUNT_ID" -ForegroundColor Gray
    }
    if ($env:ENVIRONMENT) {
        Write-Host "Environment: $env:ENVIRONMENT" -ForegroundColor Gray
    }
    
    exit 0
} else {
    Write-Error "Required AWS credentials not found in .env file"
    Write-Host ""
    Write-Host "Please ensure your .env file contains:" -ForegroundColor Yellow
    Write-Host "   AWS_ACCESS_KEY_ID=your_access_key" -ForegroundColor Gray
    Write-Host "   AWS_SECRET_ACCESS_KEY=your_secret_key" -ForegroundColor Gray
    Write-Host "   AWS_REGION=your_region (optional)" -ForegroundColor Gray
    
    exit 1
}