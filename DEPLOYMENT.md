# SnapStudy Deployment Guide

Complete guide for deploying SnapStudy's multi-agent autonomous learning system.

## 📋 Prerequisites

### AWS Account Requirements
- AWS Account with Bedrock access enabled
- Bedrock model access granted for:
  - Claude 3.5 Sonnet (`anthropic.claude-3-5-sonnet-20240620-v1:0`)
  - Titan Embeddings G1 (for Knowledge Base)
- Service quotas verified:
  - Bedrock Agents: 2+ agents
  - Knowledge Bases: 1+ knowledge base
  - Step Functions: 3+ state machines

### Local Development Tools
- **Python**: 3.11 or higher
- **Node.js**: 16.x or higher
- **AWS CLI**: v2.x configured with credentials
- **AWS CDK**: 2.x installed globally
- **Git**: Latest version

### AWS CLI Configuration
```bash
aws configure
# AWS Access Key ID: [Your Key]
# AWS Secret Access Key: [Your Secret]
# Default region: us-east-1
# Default output format: json
```

## 🚀 Quick Start (15-Minute Deployment)

### Step 1: Clone Repository
```bash
git clone <repository-url>
cd snapstudy_b
```

### Step 2: Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Environment Configuration

Create `.env` file in `backend/` directory:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=your-account-id

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0
BEDROCK_REGION=us-east-1

# These will be populated after infrastructure deployment
LEARNING_AGENT_ID=
ADAPTIVE_AGENT_ID=
BEDROCK_AGENT_ALIAS_ID=TSTALIASID
KNOWLEDGE_BASE_ID=
BEDROCK_GUARDRAIL_ID=
BEDROCK_GUARDRAIL_VERSION=DRAFT

# DynamoDB Tables
USERS_TABLE=SnapStudy-Users
LESSONS_TABLE=SnapStudy-Lessons
MICRO_LESSONS_TABLE=SnapStudy-MicroLessons
QUIZZES_TABLE=SnapStudy-Quizzes
USER_ENGAGEMENT_TABLE=SnapStudy-UserEngagement
CHAT_HISTORY_TABLE=SnapStudy-ChatHistory

# S3 Buckets
CONTENT_BUCKET=snapstudy-content-${AWS_ACCOUNT_ID}
AUDIO_CONTENT_BUCKET=snapstudy-audio-${AWS_ACCOUNT_ID}

# Security
JWT_SECRET_KEY=your-secure-secret-key-change-this

# Environment
ENVIRONMENT=production
```

### Step 4: Deploy Infrastructure (AWS CDK)

```bash
cd infrastructure

# Install CDK dependencies
npm install

# Bootstrap CDK (first time only)
cdk bootstrap aws://YOUR_ACCOUNT_ID/us-east-1

# Deploy infrastructure
cdk deploy --all --require-approval never

# This deploys:
# - DynamoDB tables (7 tables)
# - S3 buckets (2 buckets with policies)
# - Lambda functions
# - API Gateway
# - CloudWatch dashboards & alarms
# - IAM roles and policies
# - OpenSearch Serverless collection (for Knowledge Base)
```

**⏱️ Expected Time**: 10-15 minutes

**📋 Output**: Note the CloudFormation outputs - you'll need these values

### Step 5: Deploy Bedrock Agents

After infrastructure deployment, create Bedrock Agents:

```bash
cd ../scripts

# Deploy Learning Agent
python deploy_learning_agent.py

# Deploy Adaptive Agent
python deploy_adaptive_agent.py

# Create Knowledge Base
python deploy_knowledge_base.py

# Create Guardrails
python deploy_guardrails.py

# Deploy Step Functions workflows
python deploy_stepfunctions.py
```

**Update your `.env` file** with the agent IDs, KB ID, and guardrail ID from the outputs.

### Step 6: Seed Knowledge Base

```bash
# Upload educational content to S3
python seed_knowledge_base.py --content-dir ./sample_content

# Trigger Knowledge Base sync
python sync_knowledge_base.py
```

### Step 7: Frontend Setup

```bash
cd ../../frontend

# Install dependencies
npm install

# Create .env.local file
cat > .env.local << EOF
REACT_APP_API_URL=https://your-api-gateway-url
REACT_APP_AWS_REGION=us-east-1
REACT_APP_USER_POOL_ID=your-cognito-pool-id
REACT_APP_USER_POOL_CLIENT_ID=your-cognito-client-id
EOF

# Start development server
npm start
```

Frontend will be available at `http://localhost:3000`

### Step 8: Verify Deployment

```bash
# Run health checks
cd ../backend
python tests/test_deployment.py

# Expected output:
# ✅ DynamoDB tables: OK
# ✅ S3 buckets: OK
# ✅ Lambda functions: OK
# ✅ Bedrock Agents: OK (2 agents)
# ✅ Knowledge Base: OK
# ✅ Guardrails: OK
# ✅ Step Functions: OK (3 workflows)
# ✅ API Gateway: OK
```

## 📦 Detailed Component Deployment

### Bedrock Agents Deployment

#### Learning Agent Configuration
```python
{
    "agentName": "SnapStudy-LearningAgent",
    "agentResourceRoleArn": "arn:aws:iam::ACCOUNT:role/SnapStudy-AgentRole",
    "foundationModel": "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "instruction": """You are an expert educational AI agent for SnapStudy.

    Your role is to:
    1. Analyze student learning profiles and identify patterns
    2. Generate personalized educational content adapted to learning styles
    3. Review content quality for educational value
    4. Recognize student intents from natural language
    5. Provide contextual tutoring support

    Use your reasoning capabilities to make autonomous decisions about
    content generation and personalization. Access the Knowledge Base
    for accurate educational information.""",
    "actionGroups": [
        {
            "actionGroupName": "ContentGeneration",
            "actionGroupExecutor": {
                "lambda": "arn:aws:lambda:REGION:ACCOUNT:function:SnapStudy-AgentActions"
            },
            "apiSchema": {
                "payload": """/* OpenAPI schema defining 6 educational functions */"""
            }
        }
    ],
    "knowledgeBases": [
        {
            "knowledgeBaseId": "KB_ID",
            "knowledgeBaseState": "ENABLED"
        }
    ]
}
```

#### Adaptive Agent Configuration
```python
{
    "agentName": "SnapStudy-AdaptiveAgent",
    "agentResourceRoleArn": "arn:aws:iam::ACCOUNT:role/SnapStudy-AgentRole",
    "foundationModel": "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "instruction": """You are an adaptive learning path optimization agent.

    Your role is to:
    1. Analyze student performance data and identify learning patterns
    2. Make autonomous decisions about learning path adaptations
    3. Calibrate content difficulty based on performance
    4. Optimize learning sequences for maximum effectiveness
    5. Recommend next actions in the learning journey

    Use performance metrics and engagement data to make data-driven
    decisions about content adaptation.""",
    "actionGroups": [
        {
            "actionGroupName": "AdaptivePathOptimization",
            "actionGroupExecutor": {
                "lambda": "arn:aws:lambda:REGION:ACCOUNT:function:SnapStudy-AgentActions"
            }
        }
    ]
}
```

### Knowledge Base Deployment

```bash
# 1. Create OpenSearch Serverless collection
aws opensearchserverless create-collection \
  --name snapstudy-educational-content \
  --type VECTORSEARCH

# 2. Create Knowledge Base
aws bedrock-agent create-knowledge-base \
  --name "SnapStudy-EducationalKB" \
  --role-arn "arn:aws:iam::ACCOUNT:role/SnapStudy-KBRole" \
  --knowledge-base-configuration '{
    "type": "VECTOR",
    "vectorKnowledgeBaseConfiguration": {
      "embeddingModelArn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
    }
  }' \
  --storage-configuration '{
    "type": "OPENSEARCH_SERVERLESS",
    "opensearchServerlessConfiguration": {
      "collectionArn": "COLLECTION_ARN",
      "vectorIndexName": "educational-content-index",
      "fieldMapping": {
        "vectorField": "embedding",
        "textField": "text",
        "metadataField": "metadata"
      }
    }
  }'

# 3. Create S3 data source
aws bedrock-agent create-data-source \
  --knowledge-base-id "KB_ID" \
  --name "EducationalContentSource" \
  --data-source-configuration '{
    "type": "S3",
    "s3Configuration": {
      "bucketArn": "arn:aws:s3:::snapstudy-content-ACCOUNT"
    }
  }'

# 4. Start ingestion job
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id "KB_ID" \
  --data-source-id "DS_ID"
```

### Guardrails Deployment

```bash
# Create Bedrock Guardrails
aws bedrock create-guardrail \
  --name "SnapStudy-EducationalGuardrails" \
  --blocked-input-messaging "This content is not appropriate for educational use." \
  --blocked-outputs-messaging "I cannot generate that type of educational content." \
  --content-policy-config '{
    "filtersConfig": [
      {
        "type": "SEXUAL",
        "inputStrength": "HIGH",
        "outputStrength": "HIGH"
      },
      {
        "type": "VIOLENCE",
        "inputStrength": "HIGH",
        "outputStrength": "HIGH"
      },
      {
        "type": "HATE",
        "inputStrength": "HIGH",
        "outputStrength": "HIGH"
      },
      {
        "type": "INSULTS",
        "inputStrength": "MEDIUM",
        "outputStrength": "MEDIUM"
      },
      {
        "type": "MISCONDUCT",
        "inputStrength": "HIGH",
        "outputStrength": "HIGH"
      }
    ]
  }' \
  --sensitive-information-policy-config '{
    "piiEntitiesConfig": [
      {"type": "EMAIL", "action": "ANONYMIZE"},
      {"type": "PHONE", "action": "ANONYMIZE"},
      {"type": "NAME", "action": "ANONYMIZE"},
      {"type": "ADDRESS", "action": "ANONYMIZE"}
    ]
  }' \
  --topic-policy-config '{
    "topicsConfig": [
      {
        "name": "InappropriateEducationalContent",
        "definition": "Content not suitable for learning environments",
        "type": "DENY"
      }
    ]
  }'
```

### Step Functions Workflows Deployment

The Step Functions state machines are deployed via the CDK stack, but you can also deploy them manually:

```bash
aws stepfunctions create-state-machine \
  --name "SnapStudy-AdaptiveLearningPath" \
  --definition file://workflows/adaptive_learning_path.json \
  --role-arn "arn:aws:iam::ACCOUNT:role/SnapStudy-StepFunctionsRole"
```

## 🔧 Configuration Management

### Environment Variables Reference

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `AWS_REGION` | AWS region | Yes | `us-east-1` |
| `LEARNING_AGENT_ID` | Learning Agent ID | Yes | `ABCDEF1234` |
| `ADAPTIVE_AGENT_ID` | Adaptive Agent ID | Yes | `GHIJKL5678` |
| `KNOWLEDGE_BASE_ID` | Knowledge Base ID | Yes | `MNOPQR9012` |
| `BEDROCK_GUARDRAIL_ID` | Guardrail ID | Yes | `stuvwx3456` |
| `BEDROCK_MODEL_ID` | Claude model ID | Yes | `anthropic.claude-3-5-sonnet...` |
| `JWT_SECRET_KEY` | Secret for JWT | Yes | Strong random string |

### IAM Permissions Required

#### For Deployment User
- `bedrock:*` (all Bedrock operations)
- `bedrock-agent:*` (agent management)
- `bedrock-agent-runtime:*` (agent runtime)
- `s3:*` (S3 management)
- `dynamodb:*` (DynamoDB management)
- `lambda:*` (Lambda management)
- `iam:*` (IAM role creation)
- `cloudformation:*` (CDK deployment)
- `stepfunctions:*` (workflow management)
- `opensearchserverless:*` (Knowledge Base vector store)

## 📊 Post-Deployment Verification

### 1. Test Bedrock Agents
```bash
python tests/test_bedrock_agents.py

# Expected output:
# ✅ Learning Agent invocation: SUCCESS
# ✅ Adaptive Agent invocation: SUCCESS
# ✅ Agent response time: < 2s
```

### 2. Test Knowledge Base
```bash
python tests/test_knowledge_base.py

# Expected output:
# ✅ Knowledge Base retrieve: SUCCESS
# ✅ RAG generation: SUCCESS
# ✅ Relevance scores: > 0.7
```

### 3. Test Guardrails
```bash
python tests/test_guardrails.py

# Expected output:
# ✅ Safe content: PASSED
# ✅ Unsafe content: BLOCKED
# ✅ PII redaction: ANONYMIZED
```

### 4. Test Step Functions
```bash
python tests/test_stepfunctions.py

# Expected output:
# ✅ Workflow execution started
# ✅ All agents invoked successfully
# ✅ Workflow completed: SUCCESS
```

### 5. End-to-End Test
```bash
python tests/test_e2e.py

# Simulates complete user journey:
# 1. Upload content
# 2. Agent processes content
# 3. Generate personalized lesson
# 4. Student takes quiz
# 5. Agent adapts next lesson
# 6. Verify adaptation decision
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Bedrock Model Access Denied
```
Error: AccessDeniedException: You don't have access to the model
```
**Solution**: Request model access in Bedrock console → Model access → Request access

#### 2. Agent Creation Fails
```
Error: ValidationException: Foundation model not found
```
**Solution**: Verify model ID is correct and available in your region

#### 3. Knowledge Base Ingestion Fails
```
Error: Data source sync failed
```
**Solution**: Check S3 bucket permissions and content format

#### 4. Step Functions Execution Fails
```
Error: States.TaskFailed
```
**Solution**: Check CloudWatch Logs for detailed error messages

### Debug Commands

```bash
# Check Bedrock Agents status
aws bedrock-agent list-agents

# Check Knowledge Base status
aws bedrock-agent list-knowledge-bases

# Check Step Functions executions
aws stepfunctions list-executions --state-machine-arn ARN

# View CloudWatch logs
aws logs tail /aws/lambda/SnapStudy-AgentActions --follow
```

## 💰 Cost Estimation

### Monthly Cost Breakdown (1000 active users)

| Service | Usage | Monthly Cost |
|---------|-------|--------------|
| Bedrock Claude 3.5 | 10M input tokens, 5M output | ~$150 |
| Bedrock Agents | 50K invocations | ~$75 |
| Knowledge Base | 100K retrievals | ~$50 |
| Guardrails | 50K checks | ~$25 |
| Step Functions | 10K workflows | ~$2.50 |
| DynamoDB | On-demand, 10GB storage | ~$15 |
| S3 | 100GB storage, 1M requests | ~$5 |
| Lambda | 1M invocations | ~$2 |
| CloudWatch | Standard monitoring | ~$10 |
| **Total** | | **~$334.50/month** |

### Cost Optimization Tips
1. Use DynamoDB on-demand pricing for variable workloads
2. Enable S3 Intelligent-Tiering for content storage
3. Set CloudWatch log retention to 7 days
4. Use Step Functions Express workflows where possible
5. Implement caching for Knowledge Base retrievals

## 🚀 Production Deployment Checklist

- [ ] Enable WAF rules in production
- [ ] Configure custom domain with SSL/TLS
- [ ] Set up CloudWatch alarms
- [ ] Enable backup for DynamoDB tables
- [ ] Configure S3 lifecycle policies
- [ ] Set up IAM password policy
- [ ] Enable MFA for admin users
- [ ] Configure log retention policies
- [ ] Set up monitoring dashboard
- [ ] Document runbooks for incidents
- [ ] Perform security audit
- [ ] Load testing completed
- [ ] Disaster recovery plan documented

## 📞 Support

For deployment issues, contact:
- **GitHub Issues**: [Repository URL]/issues
- **AWS Support**: For Bedrock-specific issues

---

**Deployment Guide Version**: 1.0.0
**Last Updated**: October 2025
**AWS AI Agent Global Hackathon 2025**
