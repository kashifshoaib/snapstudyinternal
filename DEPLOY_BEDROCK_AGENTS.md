# 🤖 Deploying AWS Bedrock Agents for SnapStudy

## Overview

This guide walks you through deploying **TRUE autonomous AI agents** using AWS Bedrock AgentCore primitives. Once deployed, SnapStudy will use real Bedrock Agents for autonomous decision-making, not just LLM prompts.

## Prerequisites

### 1. AWS Account Setup
- AWS account with Bedrock access enabled
- Bedrock models enabled in your region:
  - `anthropic.claude-3-5-sonnet-20240620-v1:0`
  - `amazon.titan-embed-text-v1` (for Knowledge Base)
- IAM permissions for:
  - Bedrock (CreateAgent, CreateKnowledgeBase)
  - OpenSearch Serverless
  - DynamoDB, S3, Lambda, IAM
  - CloudFormation

### 2. Local Development Environment
```bash
# Install AWS CDK
npm install -g aws-cdk

# Install Python dependencies
cd backend/infrastructure
pip install -r requirements.txt

# Configure AWS credentials
aws configure
```

### 3. Request Bedrock Model Access
1. Go to AWS Console → Bedrock → Model access
2. Request access for:
   - Claude 3.5 Sonnet
   - Titan Embeddings
3. Wait for approval (usually instant to 24 hours)

## Deployment Steps

### Step 1: Bootstrap CDK (First Time Only)
```bash
cd backend/infrastructure

# Bootstrap CDK in your account/region
cdk bootstrap aws://YOUR-ACCOUNT-ID/us-east-1
```

### Step 2: Synthesize CloudFormation Template
```bash
# Generate CloudFormation template
cdk synth

# This will show you what will be deployed
# Review the output to ensure Bedrock Agents are included
```

Look for these resources in the output:
- `AWS::Bedrock::Agent` (Learning Agent)
- `AWS::Bedrock::Agent` (Adaptive Agent)
- `AWS::Bedrock::KnowledgeBase`
- `AWS::OpenSearchServerless::Collection`

### Step 3: Deploy Infrastructure
```bash
# Deploy the full stack including Bedrock Agents
cdk deploy

# Approve the IAM changes when prompted
# This will take 10-15 minutes
```

**What gets deployed:**
- ✅ DynamoDB tables (Users, Lessons, MicroLessons, Quizzes, Engagement, ChatHistory)
- ✅ S3 buckets (content storage, frontend hosting)
- ✅ Cognito User Pool
- ✅ API Gateway (structure)
- ✅ AWS WAF (protection rules)
- ✅ **Bedrock Learning Agent** (autonomous reasoning)
- ✅ **Bedrock Adaptive Agent** (learning path optimization)
- ✅ **Knowledge Base** (educational content with vector search)
- ✅ **OpenSearch Serverless Collection** (vector storage)
- ✅ CloudWatch Dashboard & Alarms

### Step 4: Capture Agent IDs from CDK Outputs

After deployment completes, CDK will output important values:

```bash
Outputs:
SnapStudyStack.LearningAgentId = AGENT123ABC456
SnapStudyStack.AdaptiveAgentId = AGENT789DEF012
SnapStudyStack.KnowledgeBaseId = KB123XYZ789
SnapStudyStack.UserPoolId = us-east-1_ABC123
SnapStudyStack.RestApiUrl = https://abc123.execute-api.us-east-1.amazonaws.com/prod/
```

### Step 5: Configure Environment Variables

Update your backend `.env` file:

```bash
# backend/.env

# AWS Configuration
AWS_REGION=us-east-1

# Bedrock Agents - COPY FROM CDK OUTPUTS
LEARNING_AGENT_ID=AGENT123ABC456
ADAPTIVE_AGENT_ID=AGENT789DEF012
BEDROCK_AGENT_ALIAS_ID=PRODUCTION
KNOWLEDGE_BASE_ID=KB123XYZ789

# Bedrock Model
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0

# DynamoDB Tables
USERS_TABLE=SnapStudy-Users
LESSONS_TABLE=SnapStudy-Lessons
MICRO_LESSONS_TABLE=SnapStudy-MicroLessons
QUIZZES_TABLE=SnapStudy-Quizzes
USER_ENGAGEMENT_TABLE=SnapStudy-UserEngagement
CHAT_HISTORY_TABLE=SnapStudy-ChatHistory

# S3
CONTENT_BUCKET=snapstudy-content-YOUR-ACCOUNT-ID-us-east-1

# Cognito
USER_POOL_ID=us-east-1_ABC123
USER_POOL_CLIENT_ID=1234567890abcdefg

# JWT
JWT_SECRET_KEY=your-secure-secret-key-change-this
```

### Step 6: Restart Backend

```bash
cd backend

# If running locally
python -m uvicorn src.main:app --reload

# If using Docker
docker-compose restart backend
```

### Step 7: Verify Agent Integration

Test that agents are working:

```python
# test_agents.py
import boto3
import json

bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

response = bedrock_agent.invoke_agent(
    agentId='YOUR_LEARNING_AGENT_ID',
    agentAliasId='PRODUCTION',
    sessionId='test-session-123',
    inputText='Hello, analyze a student with 85% quiz scores and high engagement'
)

# Process streaming response
for event in response['completion']:
    if 'chunk' in event:
        print(event['chunk']['bytes'].decode('utf-8'))
```

## Architecture Verification

### Confirm TRUE Autonomous Agents Are Active

Check `adaptive_agent.py` initialization:

```python
# Should NOT see this error anymore:
# "Bedrock Learning Agent not configured. Deploy infrastructure first."

# Should see successful agent invocations:
# "BedrockAgentCore initialized with Learning Agent: AGENT123..."
```

### Monitor Agent Activity

1. **CloudWatch Logs:**
   ```bash
   aws logs tail /aws/bedrock/agent/YOUR_AGENT_ID --follow
   ```

2. **CloudWatch Dashboard:**
   - Go to CloudWatch → Dashboards → SnapStudy-Metrics
   - View API metrics, DynamoDB throughput

3. **Bedrock Console:**
   - Go to Bedrock → Agents
   - View your Learning Agent and Adaptive Agent
   - Check invocation metrics

## Understanding the Agent Architecture

### Learning Agent
**Purpose:** General educational assistance and content generation

**Capabilities:**
- Autonomous reasoning about student needs
- Memory of past interactions
- Multi-step planning for learning sequences
- Function invocation for content generation

**Functions It Can Call:**
- `analyze_student_performance`
- `generate_personalized_content`
- `get_student_context`
- `recommend_next_action`

### Adaptive Agent
**Purpose:** Learning path optimization and real-time adaptation

**Capabilities:**
- Performance analysis (quiz scores, engagement, velocity)
- Autonomous adaptation decisions (ADVANCE, REVIEW, REINFORCE, SIMPLIFY)
- Content difficulty calibration
- Predictive learning challenge detection

**Adaptation Strategies:**
- **ADVANCE:** Score > 85%, high engagement → Move to next topic
- **REVIEW:** Score < 60% → Different teaching approach
- **REINFORCE:** Score 60-80% → Additional practice
- **SIMPLIFY:** Struggling detected → Break down complexity
- **ACCELERATE:** High performance → Increase pace

### Knowledge Base
**Purpose:** Educational content retrieval with semantic search

**Features:**
- Vector embeddings using Titan
- OpenSearch Serverless for scaling
- RAG (Retrieval Augmented Generation)
- Automatic content indexing from S3

## Troubleshooting

### Issue: "Bedrock Agent not configured"

**Cause:** Environment variables not set

**Fix:**
```bash
# Verify CDK outputs
cd backend/infrastructure
cdk deploy --outputs-file outputs.json

# Check outputs.json for agent IDs
cat outputs.json

# Update .env file with correct values
```

### Issue: Agent invocation fails with permissions error

**Cause:** IAM role lacks permissions

**Fix:**
```bash
# Check agent role in AWS Console
aws bedrock get-agent --agent-id YOUR_AGENT_ID

# Verify IAM policy includes:
# - bedrock:InvokeModel
# - dynamodb:GetItem, PutItem
# - s3:GetObject
```

### Issue: Knowledge Base returns no results

**Cause:** No content ingested

**Fix:**
```bash
# Upload educational content to S3
aws s3 cp ./educational_content/ s3://YOUR-BUCKET/educational/ --recursive

# Start ingestion job
aws bedrock start-ingestion-job \
  --knowledge-base-id YOUR_KB_ID \
  --data-source-id YOUR_DS_ID
```

### Issue: CDK deploy fails with "Bedrock constructs not found"

**Cause:** aws-cdk-lib version too old

**Fix:**
```bash
# Upgrade CDK
npm install -g aws-cdk@latest

# Update CDK lib
cd backend/infrastructure
pip install --upgrade aws-cdk-lib
```

## Cost Estimates

### Monthly Costs (Light Development Usage)
- **Bedrock Agents:** $0 (no charge for agent itself)
- **Bedrock Model Invocations:** ~$10-50 (Claude 3.5 Sonnet)
- **OpenSearch Serverless:** ~$90/month (minimum OCU)
- **DynamoDB:** $1-5 (on-demand pricing)
- **S3:** $1-3
- **API Gateway:** $1-5
- **CloudWatch:** $2-5
- **Total:** ~$105-158/month

### Cost Optimization Tips
1. Use Bedrock batch inference for non-real-time operations
2. Set DynamoDB to on-demand mode (pay per request)
3. Enable S3 lifecycle policies (transition to IA after 30 days)
4. Use CloudWatch Logs retention (7 days for development)

## Next Steps

1. ✅ **Deploy agents** (you just did this!)
2. 📝 **Update Inspiration.txt** with accurate technical details
3. 🧪 **Test agent decision-making** with real student data
4. 📊 **Monitor agent performance** in CloudWatch
5. 🚀 **Optimize prompts and functions** for better decisions

## Verification Checklist

- [ ] CDK deployment succeeded without errors
- [ ] Agent IDs captured from outputs
- [ ] Environment variables updated in `.env`
- [ ] Backend restarted with new config
- [ ] No "Bedrock Agent not configured" errors in logs
- [ ] Test agent invocation succeeds
- [ ] CloudWatch dashboard shows metrics
- [ ] Bedrock console shows 2 active agents

## Support Resources

- [AWS Bedrock Agents Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Bedrock AgentCore Primitives](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-capabilities.html)
- [Knowledge Bases for Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
- [OpenSearch Serverless](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless.html)

---

🎉 **Congratulations!** You now have TRUE autonomous AI agents powered by AWS Bedrock AgentCore, not just simulated agent behavior with prompts!
