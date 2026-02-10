# Quick Start Guide

Get your first auto-created Bedrock Agent in 5 minutes!

## Prerequisites

```bash
# Install AWS CLI
aws --version

# Configure credentials
aws configure

# Install Python dependencies
pip install boto3

# Verify Bedrock access
aws bedrock list-foundation-models --region us-east-1 | head -20
```

## Step 1: Clone Repository

```bash
git clone https://github.com/hakohli/bedrock-agent-ecr-auto-deploy.git
cd bedrock-agent-ecr-auto-deploy
```

## Step 2: Setup Infrastructure (One-Time, ~2 minutes)

```bash
python3 setup.py
```

**Expected Output:**
```
✓ Created ECR: agent-core-tools
✓ Created S3: agent-core-schemas-395102750341
✓ Created agent role: BedrockAgentCoreExecutionRole
✓ Created Lambda role: AgentCoreAutoDeployRole
✓ Created Lambda: AgentCoreAutoDeployer
✓ Created EventBridge rule: AgentCoreECRPushTrigger
✓ Created CodeBuild: agent-core-builder

============================================================
SETUP COMPLETE!
============================================================
```

## Step 3: Deploy First Agent (~3 minutes)

```bash
python3 deploy.py
```

**Expected Output:**
```
📦 Packaging source...
✓ Uploaded to S3
🔨 Starting CodeBuild...
✓ Build started
⏳ Building (2-3 minutes)...
✅ Build succeeded!
⏳ Waiting for auto-deploy Lambda...
✓ Updated Lambda: AgentCoreToolExecutor

============================================================
DEPLOYMENT COMPLETE!
============================================================
```

## Step 4: Verify Agent Created

```bash
aws bedrock-agent list-agents \
  --query 'agentSummaries[?starts_with(agentName, `agent-core-`)].{id:agentId,name:agentName,status:agentStatus}' \
  --output table
```

**Expected Output:**
```
----------------------------------------------------------
|                       ListAgents                       |
+-------------+------------------------------+-----------+
|     id      |            name              |  status   |
+-------------+------------------------------+-----------+
|  AJBLDDFYAC |  agent-core-20260210-203439  |  PREPARED |
+-------------+------------------------------+-----------+
```

## Step 5: Test Your Agent

Create `test_agent.py`:

```python
import boto3
import json

# Get latest agent
bedrock = boto3.client('bedrock-agent')
agents = bedrock.list_agents()
agent_id = [a['agentId'] for a in agents['agentSummaries'] if a['agentName'].startswith('agent-core-')][0]

print(f"Testing agent: {agent_id}")

# Invoke agent
bedrock_runtime = boto3.client('bedrock-agent-runtime')
response = bedrock_runtime.invoke_agent(
    agentId=agent_id,
    agentAliasId='TSTALIASID',
    sessionId='test-123',
    inputText='What is the weather in Tokyo?'
)

# Print response
for event in response['completion']:
    if 'chunk' in event:
        chunk = event['chunk']
        if 'bytes' in chunk:
            print(chunk['bytes'].decode(), end='')
```

Run it:

```bash
python3 test_agent.py
```

## Step 6: Make Changes and Redeploy

Edit `tool_executor.py`:

```python
# Add new tool
elif tool_name == "greet":
    name = params.get("name", "World")
    result = {"greeting": f"Hello, {name}!"}
```

Edit `auto_deploy_lambda.py` to add function spec:

```python
{
    'name': 'greet',
    'description': 'Greet someone by name',
    'parameters': {
        'name': {
            'type': 'string',
            'description': 'Name to greet',
            'required': True
        }
    }
}
```

Deploy again:

```bash
python3 deploy.py
```

A new agent will be automatically created with your new tool!

## Troubleshooting

### Setup fails with permissions error

```bash
# Check your AWS credentials
aws sts get-caller-identity

# Ensure you have Bedrock access
aws bedrock list-foundation-models --region us-east-1
```

### Build fails

```bash
# Check CodeBuild logs
aws logs tail /aws/codebuild/agent-core-builder --follow
```

### Agent not created

```bash
# Check Lambda logs
aws logs tail /aws/lambda/AgentCoreAutoDeployer --follow

# Check EventBridge rule
aws events describe-rule --name AgentCoreECRPushTrigger
```

## Next Steps

- Add more tools to `tool_executor.py`
- Customize agent instructions in `auto_deploy_lambda.py`
- Set up CI/CD pipeline
- Create agent aliases for production

## Clean Up

```bash
# Delete all agents
aws bedrock-agent list-agents \
  --query 'agentSummaries[?starts_with(agentName, `agent-core-`)].agentId' \
  --output text | xargs -I {} aws bedrock-agent delete-agent --agent-id {} --skip-resource-in-use-check

# Delete infrastructure
aws lambda delete-function --function-name AgentCoreAutoDeployer
aws lambda delete-function --function-name AgentCoreToolExecutor
aws events remove-targets --rule AgentCoreECRPushTrigger --ids 1
aws events delete-rule --name AgentCoreECRPushTrigger
aws ecr delete-repository --repository-name agent-core-tools --force
```

---

**Total Time:** ~5 minutes  
**Result:** Fully automated Bedrock Agent creation pipeline! 🎉
