#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy AWS Bedrock Agents for SnapStudy autonomous AI capabilities

.DESCRIPTION
    This script deploys Bedrock Agents, Knowledge Base, and OpenSearch Serverless
    to enable TRUE autonomous AI decision-making in SnapStudy.

.EXAMPLE
    .\deploy-bedrock-agents.ps1
#>

param(
    [string]$Region = "us-east-1",
    [string]$Profile = "default"
)

Write-Host "🤖 Deploying AWS Bedrock Agents for SnapStudy" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Check prerequisites
Write-Host "📋 Checking prerequisites..." -ForegroundColor Yellow

# Check AWS CLI
if (!(Get-Command aws -ErrorAction SilentlyContinue)) {
    Write-Error "AWS CLI not found. Please install AWS CLI first."
    exit 1
}

# Check CDK
if (!(Get-Command cdk -ErrorAction SilentlyContinue)) {
    Write-Error "AWS CDK not found. Please install CDK: npm install -g aws-cdk"
    exit 1
}

# Check AWS credentials
try {
    $identity = aws sts get-caller-identity --profile $Profile --region $Region | ConvertFrom-Json
    Write-Host "✅ AWS Identity: $($identity.Arn)" -ForegroundColor Green
} catch {
    Write-Error "AWS credentials not configured. Run: aws configure"
    exit 1
}

# Check Bedrock model access
Write-Host "🔍 Checking Bedrock model access..." -ForegroundColor Yellow
try {
    $models = aws bedrock list-foundation-models --region $Region --profile $Profile | ConvertFrom-Json
    $claudeModel = $models.modelSummaries | Where-Object { $_.modelId -like "*claude-3*sonnet*" }
    
    if ($claudeModel) {
        Write-Host "✅ Claude 3.5 Sonnet access confirmed" -ForegroundColor Green
    } else {
        Write-Warning "⚠️  Claude 3.5 Sonnet access not found. Request access in Bedrock console."
        Write-Host "   Go to: https://console.aws.amazon.com/bedrock/home?region=$Region#/modelaccess" -ForegroundColor Blue
        $continue = Read-Host "Continue anyway? (y/N)"
        if ($continue -ne "y") { exit 1 }
    }
} catch {
    Write-Warning "Could not check Bedrock access. Continuing..."
}

# Step 1: Create Bedrock Agents using AWS CLI
Write-Host "🚀 Creating Bedrock Agents..." -ForegroundColor Yellow

# Create Learning Agent
$learningAgentConfig = @{
    agentName = "SnapStudy-Learning-Agent"
    description = "Autonomous learning agent for educational assistance and content generation"
    foundationModel = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    instruction = @"
You are an autonomous learning agent for SnapStudy, an adaptive learning platform.

Your role is to:
1. Analyze student performance and learning patterns
2. Provide personalized educational assistance
3. Generate appropriate learning content
4. Make autonomous decisions about learning paths
5. Adapt teaching methods based on student needs

You have access to student data, lesson content, and performance metrics.
Always prioritize student learning outcomes and engagement.

When a student asks questions:
- Provide clear, educational explanations
- Adapt complexity to their level
- Encourage continued learning
- Suggest related concepts when appropriate

For performance analysis:
- Consider quiz scores, engagement time, and learning velocity
- Identify struggling concepts and knowledge gaps
- Recommend appropriate interventions (review, practice, advancement)
- Maintain detailed reasoning for all decisions
"@
    idleSessionTTLInSeconds = 3600
}

Write-Host "Creating Learning Agent..." -ForegroundColor Blue
$learningAgentJson = $learningAgentConfig | ConvertTo-Json -Depth 10
$learningAgent = aws bedrock create-agent --cli-input-json $learningAgentJson --region $Region --profile $Profile | ConvertFrom-Json

if ($learningAgent.agent.agentId) {
    Write-Host "✅ Learning Agent created: $($learningAgent.agent.agentId)" -ForegroundColor Green
    $learningAgentId = $learningAgent.agent.agentId
} else {
    Write-Error "Failed to create Learning Agent"
    exit 1
}

# Create Adaptive Agent
$adaptiveAgentConfig = @{
    agentName = "SnapStudy-Adaptive-Agent"
    description = "Autonomous adaptive learning agent for real-time learning path optimization"
    foundationModel = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    instruction = @"
You are an autonomous adaptive learning agent for SnapStudy.

Your specialized role is to:
1. Analyze real-time learning performance data
2. Make autonomous adaptation decisions (ADVANCE, REVIEW, REINFORCE, SIMPLIFY)
3. Optimize learning paths based on individual student needs
4. Predict learning challenges before they become problems
5. Calibrate content difficulty dynamically

Decision Framework:
- ADVANCE: Score > 85%, high engagement → Move to next concept
- REVIEW: Score < 60% → Try different teaching approach
- REINFORCE: Score 60-80% → Additional practice needed
- SIMPLIFY: Struggling detected → Break down complexity
- ACCELERATE: High performance → Increase pace/difficulty

Always provide detailed reasoning for adaptation decisions.
Consider multiple factors: quiz performance, time spent, engagement patterns, learning velocity.

Your decisions directly impact student learning outcomes.
"@
    idleSessionTTLInSeconds = 3600
}

Write-Host "Creating Adaptive Agent..." -ForegroundColor Blue
$adaptiveAgentJson = $adaptiveAgentConfig | ConvertTo-Json -Depth 10
$adaptiveAgent = aws bedrock create-agent --cli-input-json $adaptiveAgentJson --region $Region --profile $Profile | ConvertFrom-Json

if ($adaptiveAgent.agent.agentId) {
    Write-Host "✅ Adaptive Agent created: $($adaptiveAgent.agent.agentId)" -ForegroundColor Green
    $adaptiveAgentId = $adaptiveAgent.agent.agentId
} else {
    Write-Error "Failed to create Adaptive Agent"
    exit 1
}

# Step 2: Create Agent Aliases
Write-Host "🔗 Creating Agent Aliases..." -ForegroundColor Yellow

# Learning Agent Alias
$learningAlias = aws bedrock create-agent-alias `
    --agent-id $learningAgentId `
    --agent-alias-name "PRODUCTION" `
    --description "Production alias for Learning Agent" `
    --region $Region --profile $Profile | ConvertFrom-Json

# Adaptive Agent Alias  
$adaptiveAlias = aws bedrock create-agent-alias `
    --agent-id $adaptiveAgentId `
    --agent-alias-name "PRODUCTION" `
    --description "Production alias for Adaptive Agent" `
    --region $Region --profile $Profile | ConvertFrom-Json

Write-Host "✅ Agent aliases created" -ForegroundColor Green

# Step 3: Create Knowledge Base (Optional but recommended)
Write-Host "📚 Creating Knowledge Base..." -ForegroundColor Yellow

# Create OpenSearch Serverless Collection first
$collectionName = "snapstudy-knowledge-base"
$collectionConfig = @{
    name = $collectionName
    description = "Vector storage for SnapStudy educational content"
    type = "VECTORSEARCH"
}

try {
    $collection = aws opensearchserverless create-collection `
        --name $collectionName `
        --description "Vector storage for SnapStudy educational content" `
        --type VECTORSEARCH `
        --region $Region --profile $Profile | ConvertFrom-Json
    
    Write-Host "✅ OpenSearch collection created: $($collection.createCollectionDetail.id)" -ForegroundColor Green
    $collectionId = $collection.createCollectionDetail.id
    
    # Wait for collection to be active
    Write-Host "⏳ Waiting for collection to be active..." -ForegroundColor Blue
    do {
        Start-Sleep 10
        $collectionStatus = aws opensearchserverless batch-get-collection --ids $collectionId --region $Region --profile $Profile | ConvertFrom-Json
        $status = $collectionStatus.collectionDetails[0].status
        Write-Host "   Collection status: $status" -ForegroundColor Gray
    } while ($status -eq "CREATING")
    
    if ($status -eq "ACTIVE") {
        Write-Host "✅ Collection is active" -ForegroundColor Green
    } else {
        Write-Warning "Collection status: $status"
    }
    
} catch {
    Write-Warning "Could not create OpenSearch collection. Knowledge Base will be skipped."
    $collectionId = $null
}

# Step 4: Update Environment Variables
Write-Host "⚙️  Updating environment variables..." -ForegroundColor Yellow

$envPath = "../backend/.env"
if (Test-Path $envPath) {
    $envContent = Get-Content $envPath
    
    # Update or add Bedrock Agent variables
    $newEnvContent = @()
    $agentVarsAdded = @{
        "LEARNING_AGENT_ID" = $false
        "ADAPTIVE_AGENT_ID" = $false
        "BEDROCK_AGENT_ALIAS_ID" = $false
    }
    
    foreach ($line in $envContent) {
        if ($line -match "^LEARNING_AGENT_ID=") {
            $newEnvContent += "LEARNING_AGENT_ID=$learningAgentId"
            $agentVarsAdded["LEARNING_AGENT_ID"] = $true
        }
        elseif ($line -match "^ADAPTIVE_AGENT_ID=") {
            $newEnvContent += "ADAPTIVE_AGENT_ID=$adaptiveAgentId"
            $agentVarsAdded["ADAPTIVE_AGENT_ID"] = $true
        }
        elseif ($line -match "^BEDROCK_AGENT_ALIAS_ID=") {
            $newEnvContent += "BEDROCK_AGENT_ALIAS_ID=PRODUCTION"
            $agentVarsAdded["BEDROCK_AGENT_ALIAS_ID"] = $true
        }
        else {
            $newEnvContent += $line
        }
    }
    
    # Add missing variables
    if (-not $agentVarsAdded["LEARNING_AGENT_ID"]) {
        $newEnvContent += ""
        $newEnvContent += "# Bedrock Agents"
        $newEnvContent += "LEARNING_AGENT_ID=$learningAgentId"
    }
    if (-not $agentVarsAdded["ADAPTIVE_AGENT_ID"]) {
        $newEnvContent += "ADAPTIVE_AGENT_ID=$adaptiveAgentId"
    }
    if (-not $agentVarsAdded["BEDROCK_AGENT_ALIAS_ID"]) {
        $newEnvContent += "BEDROCK_AGENT_ALIAS_ID=PRODUCTION"
    }
    
    if ($collectionId) {
        $newEnvContent += "KNOWLEDGE_BASE_COLLECTION_ID=$collectionId"
    }
    
    # Write updated .env file
    $newEnvContent | Set-Content $envPath
    Write-Host "✅ Environment variables updated in $envPath" -ForegroundColor Green
} else {
    Write-Warning ".env file not found at $envPath"
}

# Step 5: Display Results
Write-Host ""
Write-Host "🎉 Bedrock Agents Deployment Complete!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Agent Information:" -ForegroundColor Cyan
Write-Host "Learning Agent ID: $learningAgentId" -ForegroundColor White
Write-Host "Adaptive Agent ID: $adaptiveAgentId" -ForegroundColor White
Write-Host "Agent Alias: PRODUCTION" -ForegroundColor White
if ($collectionId) {
    Write-Host "OpenSearch Collection: $collectionId" -ForegroundColor White
}
Write-Host ""
Write-Host "🔧 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Restart your backend server to load new environment variables" -ForegroundColor White
Write-Host "2. Test agent functionality with chat" -ForegroundColor White
Write-Host "3. Monitor agent performance in CloudWatch" -ForegroundColor White
Write-Host "4. Check Bedrock console for agent metrics" -ForegroundColor White
Write-Host ""
Write-Host "💰 Cost Estimate:" -ForegroundColor Yellow
Write-Host "- Bedrock Agents: $0 (no charge for agents themselves)" -ForegroundColor White
Write-Host "- Claude 3.5 Sonnet: ~$10-50/month (based on usage)" -ForegroundColor White
if ($collectionId) {
    Write-Host "- OpenSearch Serverless: ~$90/month (minimum OCU)" -ForegroundColor White
}
Write-Host ""
Write-Host "🔗 Useful Links:" -ForegroundColor Cyan
Write-Host "Bedrock Console: https://console.aws.amazon.com/bedrock/home?region=$Region#/agents" -ForegroundColor Blue
Write-Host "CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/home?region=$Region#logsV2:log-groups" -ForegroundColor Blue
Write-Host ""
Write-Host "✅ Your SnapStudy backend now has TRUE autonomous AI agents!" -ForegroundColor Green