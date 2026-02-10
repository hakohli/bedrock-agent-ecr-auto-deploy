# 🤖 Bedrock Agent Auto-Creator

Automatically create new Amazon Bedrock Agents when you push code to ECR. Perfect for CI/CD pipelines and rapid agent iteration.

## 🎯 What This Does

Push code → New Bedrock Agent automatically created!

```
1. Developer: python3 deploy.py
2. CodeBuild builds Docker image
3. Pushes to ECR → agent-core-tools
4. EventBridge detects ECR push
5. Lambda executes → AgentCoreAutoDeployer
6. Lambda calls → bedrock.create_agent()
7. Lambda calls → bedrock.create_agent_action_group()
8. Lambda calls → bedrock.prepare_agent()
9. ✅ New Agent Created!
```

## ✨ Features

- **Fully Automated** - Push code, get agent
- **Version Tracking** - Each push creates timestamped agent
- **Containerized Tools** - Tools run in Lambda containers
- **Production Ready** - Uses AWS Managed Agents
- **No Manual Steps** - EventBridge handles everything

## 🏗️ Architecture

```
┌─────────────┐
│  Developer  │
│             │
│ Edit tools  │
│ Run deploy  │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│   CodeBuild     │
│                 │
│ Build image     │
│ Push to ECR     │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│   EventBridge   │
│                 │
│ Detect push     │
│ Trigger Lambda  │
└──────┬──────────┘
       │
       ▼
┌─────────────────────────────┐
│  Lambda: AgentCoreAutoDeployer │
│                             │
│ 1. Get ECR image digest     │
│ 2. Update tool executor     │
│ 3. Create Bedrock Agent     │
│ 4. Add action group         │
│ 5. Prepare agent            │
└──────┬──────────────────────┘
       │
       ▼
┌─────────────────┐
│ Bedrock Agent   │
│                 │
│ ID: AJBLDDFYAC  │
│ Status: PREPARED│
└─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- AWS Account with Bedrock access
- AWS CLI configured
- Python 3.9+
- boto3: `pip install boto3`

### 1. Setup Infrastructure (One-Time)

```bash
git clone https://github.com/YOUR_USERNAME/bedrock-agent-auto-creator.git
cd bedrock-agent-auto-creator

python3 setup.py
```

**Creates:**
- ECR repository: `agent-core-tools`
- S3 bucket: `agent-core-schemas-{account-id}`
- IAM roles for Bedrock Agent and Lambda
- Lambda: `AgentCoreAutoDeployer` (creates agents)
- Lambda: `AgentCoreToolExecutor` (executes tools)
- EventBridge rule: Triggers on ECR push
- CodeBuild project: Builds Docker images

### 2. Deploy Your First Agent

```bash
python3 deploy.py
```

**What happens:**
1. ⏳ Packages your code
2. 🔨 CodeBuild builds Docker image (~2 minutes)
3. 📦 Pushes to ECR
4. ⚡ EventBridge triggers Lambda
5. 🤖 Lambda creates Bedrock Agent
6. ✅ Agent ready!

**Output:**
```
✅ Build succeeded!
⏳ Waiting for auto-deploy Lambda...
✓ Updated Lambda: AgentCoreToolExecutor
✓ Agent Core config created in S3

============================================================
DEPLOYMENT COMPLETE!
============================================================
Image: 395102750341.dkr.ecr.us-east-1.amazonaws.com/agent-core-tools@sha256:...
```

### 3. Verify Agent Created

```bash
aws bedrock-agent list-agents \
  --query 'agentSummaries[?starts_with(agentName, `agent-core-`)].{id:agentId,name:agentName,status:agentStatus}' \
  --output table
```

**Output:**
```
----------------------------------------------------------
|                       ListAgents                       |
+-------------+------------------------------+-----------+
|     id      |            name              |  status   |
+-------------+------------------------------+-----------+
|  AJBLDDFYAC |  agent-core-20260210-203439  |  PREPARED |
+-------------+------------------------------+-----------+
```

### 4. Test Your Agent

```python
import boto3
import json

bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')

response = bedrock_agent_runtime.invoke_agent(
    agentId='AJBLDDFYAC',
    agentAliasId='TSTALIASID',
    sessionId='test-123',
    inputText='What is the weather in Tokyo?'
)

# Process streaming response
for event in response['completion']:
    if 'chunk' in event:
        print(event['chunk']['bytes'].decode())
```

## 🔧 Customize Your Agent

### Add New Tools

Edit `tool_executor.py`:

```python
def lambda_handler(event, context):
    # ... existing code ...
    
    elif tool_name == "search_database":
        query = params.get("query", "")
        # Your database search logic
        result = {"results": [...]}
    
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': action_group,
            'function': function_name,
            'functionResponse': {
                'responseBody': {
                    'TEXT': {
                        'body': json.dumps(result)
                    }
                }
            }
        }
    }
```

Edit `auto_deploy_lambda.py` to add function spec:

```python
functionSchema={
    'functions': [
        # ... existing functions ...
        {
            'name': 'search_database',
            'description': 'Search customer database',
            'parameters': {
                'query': {
                    'type': 'string',
                    'description': 'Search query',
                    'required': True
                }
            }
        }
    ]
}
```

Then deploy:

```bash
python3 deploy.py
```

A new agent will be automatically created with your new tool!

## 🔐 Security & IAM Permissions

This system uses **least privilege IAM permissions**. See [IAM_PERMISSIONS.md](./IAM_PERMISSIONS.md) for detailed documentation.

### IAM Roles Created

1. **BedrockAgentCoreExecutionRole** - For Bedrock Agents
   - Invoke foundation models
   - Call Lambda functions (specific function only)

2. **AgentCoreAutoDeployRole** - For auto-deploy Lambda
   - Create Bedrock Agents
   - Update Lambda functions
   - Read ECR images
   - Write to S3 (specific bucket only)
   - PassRole (with condition)

3. **AgentCoreToolExecutorRole** - For tool executor Lambda
   - CloudWatch Logs only (specific log group)
   - Add custom permissions for your tools

4. **AgentCoreCodeBuildRole** - For CodeBuild
   - Push to ECR
   - Read from S3 (specific object only)
   - CloudWatch Logs (specific log group)

**All permissions are scoped to specific resources where possible.**

See [IAM_PERMISSIONS.md](./IAM_PERMISSIONS.md) for complete policy documents and customization guide.

---

## 📁 Files

- `setup.py` - One-time infrastructure setup
- `deploy.py` - Build and deploy (triggers agent creation)
- `tool_executor.py` - Tool implementations (runs in Lambda container)
- `auto_deploy_lambda.py` - Auto-creates agents on ECR push
- `Dockerfile` - Container for tool executor
- `buildspec.yml` - CodeBuild instructions

## 🔄 Development Workflow

```bash
# 1. Edit tools
vim tool_executor.py

# 2. Deploy (creates new agent automatically)
python3 deploy.py

# 3. Test new agent
aws bedrock-agent list-agents

# 4. Repeat!
```

## 💡 How It Works

### EventBridge Rule

Monitors ECR for push events:

```json
{
  "source": ["aws.ecr"],
  "detail-type": ["ECR Image Action"],
  "detail": {
    "action-type": ["PUSH"],
    "result": ["SUCCESS"],
    "repository-name": ["agent-core-tools"]
  }
}
```

### Lambda: AgentCoreAutoDeployer

Triggered by EventBridge, creates agent:

```python
# 1. Get latest image
image_uri = get_latest_ecr_image()

# 2. Update tool executor Lambda
lambda_client.update_function_code(ImageUri=image_uri)

# 3. Create Bedrock Agent
agent = bedrock.create_agent(
    agentName=f"agent-core-{timestamp}",
    foundationModel='claude-3-sonnet',
    instruction='Your agent instructions'
)

# 4. Add action group
bedrock.create_agent_action_group(
    agentId=agent['agentId'],
    actionGroupExecutor={'lambda': lambda_arn},
    functionSchema={...}
)

# 5. Prepare agent
bedrock.prepare_agent(agentId=agent['agentId'])
```

## 📊 Comparison with Manual Creation

| Task | Manual | Auto-Creator |
|------|--------|--------------|
| Create agent | AWS Console | Automatic |
| Update tools | Redeploy agent | Push code |
| Version control | Manual naming | Timestamped |
| Time to deploy | 10-15 minutes | 2-3 minutes |
| Consistency | Manual steps | Automated |

## 💰 Cost Estimate

- CodeBuild: ~$0.01 per build
- ECR: $0.10/GB/month
- Lambda: Free tier (tool execution)
- S3: Minimal (<$0.01/month)
- Bedrock: ~$0.003 per 1K tokens
- EventBridge: Free tier

**Total: ~$1-2/month for development**

## 🐛 Troubleshooting

### Agent not created?

```bash
# Check Lambda logs
aws logs tail /aws/lambda/AgentCoreAutoDeployer --follow

# Check EventBridge rule
aws events describe-rule --name AgentCoreECRPushTrigger
```

### Build fails?

```bash
# Check CodeBuild logs
aws logs tail /aws/codebuild/agent-core-builder --follow

# Check ECR repository
aws ecr describe-repositories --repository-names agent-core-tools
```

### Tool execution fails?

```bash
# Test tool executor directly
aws lambda invoke \
  --function-name AgentCoreToolExecutor \
  --payload '{"function":"get_weather","parameters":[{"name":"city","value":"Seattle"}]}' \
  response.json

cat response.json
```

## 🧹 Cleanup

```bash
# Delete all auto-created agents
aws bedrock-agent list-agents \
  --query 'agentSummaries[?starts_with(agentName, `agent-core-`)].agentId' \
  --output text | xargs -I {} aws bedrock-agent delete-agent --agent-id {} --skip-resource-in-use-check

# Delete Lambda functions
aws lambda delete-function --function-name AgentCoreAutoDeployer
aws lambda delete-function --function-name AgentCoreToolExecutor

# Delete EventBridge rule
aws events remove-targets --rule AgentCoreECRPushTrigger --ids 1
aws events delete-rule --name AgentCoreECRPushTrigger

# Delete ECR repository
aws ecr delete-repository --repository-name agent-core-tools --force

# Delete S3 bucket
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws s3 rb s3://agent-core-schemas-${ACCOUNT_ID} --force

# Delete IAM roles
aws iam delete-role --role-name BedrockAgentCoreExecutionRole
aws iam delete-role --role-name AgentCoreAutoDeployRole
aws iam delete-role --role-name AgentCoreToolExecutorRole
aws iam delete-role --role-name AgentCoreCodeBuildRole
```

## 🎓 Advanced Usage

### Multiple Environments

```python
# In auto_deploy_lambda.py
env = os.environ.get('ENVIRONMENT', 'dev')
agent_name = f"agent-{env}-{timestamp}"
```

### Custom Foundation Models

```python
# In auto_deploy_lambda.py
foundationModel='anthropic.claude-3-haiku-20240307-v1:0'  # Faster, cheaper
# or
foundationModel='anthropic.claude-3-opus-20240229-v1:0'   # Most capable
```

### Agent Aliases

```python
# Create alias after agent creation
bedrock.create_agent_alias(
    agentId=agent_id,
    agentAliasName='production',
    description='Production version'
)
```

## 📚 Resources

- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Bedrock Agents Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [EventBridge Documentation](https://docs.aws.amazon.com/eventbridge/)
- [Lambda Container Images](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🎉 Success Story

**Tested and Working:**
- ✅ Agent ID: `AJBLDDFYAC`
- ✅ Agent Name: `agent-core-20260210-203439`
- ✅ Status: `PREPARED`
- ✅ Tools: `get_weather`, `calculate`
- ✅ Automatic creation on ECR push

---

**Built with ❤️ for rapid Bedrock agent development**

Push code, get agents! 🚀
