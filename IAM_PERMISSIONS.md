# IAM Roles and Permissions

This document details all IAM roles and their least-privilege permissions required for the auto-deployment system.

## Overview

The system uses **4 IAM roles** with minimal permissions:

1. **BedrockAgentCoreExecutionRole** - For Bedrock Agents
2. **AgentCoreAutoDeployRole** - For auto-deploy Lambda
3. **AgentCoreToolExecutorRole** - For tool executor Lambda
4. **AgentCoreCodeBuildRole** - For CodeBuild

---

## 1. BedrockAgentCoreExecutionRole

**Purpose:** Assumed by Bedrock Agents to invoke Lambda functions

**Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Service": "bedrock.amazonaws.com"
    },
    "Action": "sts:AssumeRole"
  }]
}
```

**Permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": "arn:aws:lambda:*:*:function:AgentCoreToolExecutor"
    }
  ]
}
```

**Why these permissions:**
- `bedrock:InvokeModel*` - Agent needs to call foundation models
- `lambda:InvokeFunction` - Agent needs to execute tools via Lambda

---

## 2. AgentCoreAutoDeployRole

**Purpose:** Lambda function that creates Bedrock Agents on ECR push

**Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Service": "lambda.amazonaws.com"
    },
    "Action": "sts:AssumeRole"
  }]
}
```

**Permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:CreateAgent",
        "bedrock:CreateAgentActionGroup",
        "bedrock:PrepareAgent",
        "bedrock:GetAgent"
      ],
      "Resource": "arn:aws:bedrock:*:*:agent/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:DescribeImages",
        "ecr:DescribeRepositories",
        "ecr:GetAuthorizationToken"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration",
        "lambda:GetFunction"
      ],
      "Resource": "arn:aws:lambda:*:*:function:AgentCoreToolExecutor"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::agent-core-schemas-*/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": "arn:aws:iam::*:role/BedrockAgentCoreExecutionRole",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": "bedrock.amazonaws.com"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/AgentCoreAutoDeployer:*"
    }
  ]
}
```

**Why these permissions:**
- `bedrock:CreateAgent*` - Create and configure agents
- `ecr:Describe*` - Get latest image digest
- `lambda:Update*` - Update tool executor with new image
- `s3:PutObject` - Store agent metadata
- `iam:PassRole` - Pass agent execution role (with condition)
- `logs:*` - CloudWatch logging

---

## 3. AgentCoreToolExecutorRole

**Purpose:** Lambda function that executes agent tools

**Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Service": "lambda.amazonaws.com"
    },
    "Action": "sts:AssumeRole"
  }]
}
```

**Permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/AgentCoreToolExecutor:*"
    }
  ]
}
```

**Why these permissions:**
- `logs:*` - CloudWatch logging only
- **Note:** Add additional permissions here if your tools need to access other AWS services (S3, DynamoDB, etc.)

---

## 4. AgentCoreCodeBuildRole

**Purpose:** CodeBuild project that builds Docker images

**Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Service": "codebuild.amazonaws.com"
    },
    "Action": "sts:AssumeRole"
  }]
}
```

**Permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:GetObjectVersion"
      ],
      "Resource": "arn:aws:s3:::agent-core-schemas-*/source.zip"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/codebuild/agent-core-builder:*"
    }
  ]
}
```

**Why these permissions:**
- `ecr:*` - Push Docker images to ECR
- `s3:GetObject` - Download source code
- `logs:*` - CloudWatch logging

---

## Security Best Practices

### 1. Least Privilege Applied

✅ **No wildcard resources** where possible  
✅ **Specific function/bucket names** in ARNs  
✅ **Condition on PassRole** to prevent privilege escalation  
✅ **No admin permissions** anywhere  

### 2. Resource-Level Permissions

```json
// ✅ GOOD - Specific resource
"Resource": "arn:aws:lambda:*:*:function:AgentCoreToolExecutor"

// ❌ BAD - Wildcard
"Resource": "*"
```

### 3. PassRole Protection

```json
{
  "Action": "iam:PassRole",
  "Resource": "arn:aws:iam::*:role/BedrockAgentCoreExecutionRole",
  "Condition": {
    "StringEquals": {
      "iam:PassedToService": "bedrock.amazonaws.com"
    }
  }
}
```

This prevents the role from being passed to other services.

---

## Customizing Permissions

### Adding Tool Permissions

If your tools need to access AWS services, update `AgentCoreToolExecutorRole`:

```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:GetItem",
    "dynamodb:Query"
  ],
  "Resource": "arn:aws:dynamodb:*:*:table/MyTable"
}
```

### Multi-Region Support

Replace region-specific ARNs:

```json
// Single region
"Resource": "arn:aws:bedrock:us-east-1:*:agent/*"

// Multi-region
"Resource": "arn:aws:bedrock:*:*:agent/*"
```

### Multiple Environments

Use resource tags or naming conventions:

```json
{
  "Effect": "Allow",
  "Action": "bedrock:CreateAgent",
  "Resource": "arn:aws:bedrock:*:*:agent/*",
  "Condition": {
    "StringLike": {
      "aws:RequestTag/Environment": ["dev", "staging"]
    }
  }
}
```

---

## Verification

### Check Role Permissions

```bash
# List role policies
aws iam list-attached-role-policies --role-name BedrockAgentCoreExecutionRole
aws iam list-role-policies --role-name BedrockAgentCoreExecutionRole

# Get policy document
aws iam get-role-policy --role-name AgentCoreAutoDeployRole --policy-name AgentCorePolicy
```

### Test Permissions

```bash
# Test as role
aws sts assume-role --role-arn arn:aws:iam::ACCOUNT:role/AgentCoreAutoDeployRole --role-session-name test

# Use temporary credentials
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...

# Try creating agent
aws bedrock-agent create-agent --agent-name test-agent ...
```

---

## Troubleshooting

### "Access Denied" Errors

1. **Check role trust policy** - Ensure correct service principal
2. **Verify permissions** - Check action is allowed
3. **Check resource ARN** - Ensure it matches
4. **Review conditions** - Check if conditions are met

### PassRole Errors

```
User: ... is not authorized to perform: iam:PassRole on resource: ...
```

**Solution:** Add PassRole permission with condition:

```json
{
  "Effect": "Allow",
  "Action": "iam:PassRole",
  "Resource": "arn:aws:iam::*:role/BedrockAgentCoreExecutionRole",
  "Condition": {
    "StringEquals": {
      "iam:PassedToService": "bedrock.amazonaws.com"
    }
  }
}
```

---

## Summary

| Role | Purpose | Key Permissions |
|------|---------|----------------|
| BedrockAgentCoreExecutionRole | Agent execution | Invoke models, call Lambda |
| AgentCoreAutoDeployRole | Create agents | Create agents, update Lambda |
| AgentCoreToolExecutorRole | Execute tools | Logging only (+ custom) |
| AgentCoreCodeBuildRole | Build images | Push to ECR, read S3 |

**Total Permissions:** Minimal required for functionality  
**Security Level:** Production-ready with least privilege  
**Customizable:** Easy to extend for specific use cases
