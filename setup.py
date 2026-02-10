#!/usr/bin/env python3
"""Setup infrastructure for auto-creating Bedrock Agents on ECR push"""

import boto3
import json
import time
import zipfile
from io import BytesIO

def setup():
    ecr = boto3.client('ecr')
    s3 = boto3.client('s3')
    iam = boto3.client('iam')
    lambda_client = boto3.client('lambda')
    events = boto3.client('events')
    codebuild = boto3.client('codebuild')
    
    account_id = boto3.client('sts').get_caller_identity()['Account']
    region = boto3.session.Session().region_name or 'us-east-1'
    
    # 1. Create ECR repository
    repo_name = 'agent-core-tools'
    try:
        ecr.create_repository(repositoryName=repo_name)
        print(f"✓ Created ECR: {repo_name}")
    except ecr.exceptions.RepositoryAlreadyExistsException:
        print(f"✓ ECR exists: {repo_name}")
    
    # 2. Create S3 bucket
    bucket_name = f'agent-core-configs-{account_id}'
    try:
        if region == 'us-east-1':
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': region})
        print(f"✓ Created S3: {bucket_name}")
    except:
        print(f"✓ S3 exists: {bucket_name}")
    
    # 3. Create Bedrock Agent execution role
    agent_role_name = 'BedrockAgentCoreExecutionRole'
    agent_trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "bedrock.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }
    
    try:
        agent_role_response = iam.create_role(
            RoleName=agent_role_name,
            AssumeRolePolicyDocument=json.dumps(agent_trust_policy)
        )
        agent_role_arn = agent_role_response['Role']['Arn']
        print(f"✓ Created agent role: {agent_role_name}")
        time.sleep(10)
    except iam.exceptions.EntityAlreadyExistsException:
        agent_role_arn = iam.get_role(RoleName=agent_role_name)['Role']['Arn']
        print(f"✓ Agent role exists: {agent_role_name}")
    
    iam.attach_role_policy(
        RoleName=agent_role_name,
        PolicyArn='arn:aws:iam::aws:policy/AmazonBedrockFullAccess'
    )
    
    # 4. Create Lambda execution role
    lambda_role_name = 'AgentCoreAutoDeployRole'
    lambda_trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }
    
    try:
        role_response = iam.create_role(
            RoleName=lambda_role_name,
            AssumeRolePolicyDocument=json.dumps(lambda_trust_policy)
        )
        role_arn = role_response['Role']['Arn']
        print(f"✓ Created Lambda role: {lambda_role_name}")
        time.sleep(10)
    except iam.exceptions.EntityAlreadyExistsException:
        role_arn = iam.get_role(RoleName=lambda_role_name)['Role']['Arn']
        print(f"✓ Lambda role exists: {lambda_role_name}")
    
    # Attach policies
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": ["bedrock:*"], "Resource": "*"},
            {"Effect": "Allow", "Action": ["ecr:*"], "Resource": "*"},
            {"Effect": "Allow", "Action": ["s3:*"], "Resource": [f"arn:aws:s3:::{bucket_name}*"]},
            {"Effect": "Allow", "Action": ["lambda:*"], "Resource": "*"},
            {"Effect": "Allow", "Action": ["iam:PassRole"], "Resource": agent_role_arn},
            {"Effect": "Allow", "Action": ["logs:*"], "Resource": "*"}
        ]
    }
    
    try:
        iam.put_role_policy(RoleName=lambda_role_name, PolicyName='AgentCorePolicy', PolicyDocument=json.dumps(policy))
    except:
        pass
    
    # 5. Create tool executor Lambda role
    tool_role_name = 'AgentCoreToolExecutorRole'
    try:
        tool_role_response = iam.create_role(
            RoleName=tool_role_name,
            AssumeRolePolicyDocument=json.dumps(lambda_trust_policy)
        )
        tool_role_arn = tool_role_response['Role']['Arn']
        print(f"✓ Created tool executor role: {tool_role_name}")
        time.sleep(10)
    except iam.exceptions.EntityAlreadyExistsException:
        tool_role_arn = iam.get_role(RoleName=tool_role_name)['Role']['Arn']
        print(f"✓ Tool executor role exists: {tool_role_name}")
    
    iam.attach_role_policy(
        RoleName=tool_role_name,
        PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
    )
    
    # 6. Create auto-deploy Lambda
    with open('auto_deploy_lambda.py', 'r') as f:
        code = f.read()
    
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('lambda_function.py', code)
    
    function_name = 'AgentCoreAutoDeployer'
    try:
        lambda_response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.12',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zip_buffer.getvalue()},
            Timeout=300,
            Environment={
                'Variables': {
                    'S3_BUCKET': bucket_name,
                    'ECR_REPO': repo_name,
                    'AGENT_ROLE_ARN': agent_role_arn
                }
            }
        )
        lambda_arn = lambda_response['FunctionArn']
        print(f"✓ Created Lambda: {function_name}")
    except lambda_client.exceptions.ResourceConflictException:
        # Update code
        try:
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_buffer.getvalue()
            )
            time.sleep(5)
        except:
            pass
        
        # Update config
        try:
            lambda_client.update_function_configuration(
                FunctionName=function_name,
                Timeout=300,
                Environment={
                    'Variables': {
                        'S3_BUCKET': bucket_name,
                        'ECR_REPO': repo_name,
                        'AGENT_ROLE_ARN': agent_role_arn
                    }
                }
            )
        except:
            pass
        
        lambda_arn = lambda_client.get_function(FunctionName=function_name)['Configuration']['FunctionArn']
        print(f"✓ Updated Lambda: {function_name}")
    
    # 7. Add EventBridge permission
    try:
        lambda_client.add_permission(
            FunctionName=function_name,
            StatementId='AllowEventBridge',
            Action='lambda:InvokeFunction',
            Principal='events.amazonaws.com'
        )
    except:
        pass
    
    # 8. Create EventBridge rule
    rule_name = 'AgentCoreECRPushTrigger'
    event_pattern = {
        "source": ["aws.ecr"],
        "detail-type": ["ECR Image Action"],
        "detail": {
            "action-type": ["PUSH"],
            "result": ["SUCCESS"],
            "repository-name": [repo_name]
        }
    }
    
    try:
        events.put_rule(
            Name=rule_name,
            EventPattern=json.dumps(event_pattern),
            State='ENABLED'
        )
        print(f"✓ Created EventBridge rule: {rule_name}")
    except:
        print(f"✓ EventBridge rule exists: {rule_name}")
    
    events.put_targets(Rule=rule_name, Targets=[{'Id': '1', 'Arn': lambda_arn}])
    
    # 9. Create CodeBuild project
    codebuild_role = 'AgentCoreCodeBuildRole'
    try:
        cb_role_response = iam.create_role(
            RoleName=codebuild_role,
            AssumeRolePolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "codebuild.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }]
            })
        )
        time.sleep(10)
    except:
        pass
    
    iam.put_role_policy(
        RoleName=codebuild_role,
        PolicyName='CodeBuildPolicy',
        PolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {"Effect": "Allow", "Action": ["ecr:*"], "Resource": "*"},
                {"Effect": "Allow", "Action": ["s3:*"], "Resource": "*"},
                {"Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], "Resource": "*"}
            ]
        })
    )
    
    cb_role_arn = iam.get_role(RoleName=codebuild_role)['Role']['Arn']
    
    project_name = 'agent-core-builder'
    try:
        codebuild.create_project(
            name=project_name,
            source={'type': 'S3', 'location': f'{bucket_name}/source.zip'},
            artifacts={'type': 'NO_ARTIFACTS'},
            environment={
                'type': 'LINUX_CONTAINER',
                'image': 'aws/codebuild/standard:7.0',
                'computeType': 'BUILD_GENERAL1_SMALL',
                'privilegedMode': True,
                'environmentVariables': [
                    {'name': 'AWS_DEFAULT_REGION', 'value': region},
                    {'name': 'AWS_ACCOUNT_ID', 'value': account_id},
                    {'name': 'IMAGE_REPO_NAME', 'value': repo_name},
                    {'name': 'IMAGE_TAG', 'value': 'latest'}
                ]
            },
            serviceRole=cb_role_arn
        )
        print(f"✓ Created CodeBuild: {project_name}")
    except:
        print(f"✓ CodeBuild exists: {project_name}")
    
    print("\n" + "="*60)
    print("SETUP COMPLETE!")
    print("="*60)
    print(f"ECR Repository: {repo_name}")
    print(f"S3 Bucket: {bucket_name}")
    print(f"Agent Role: {agent_role_arn}")
    print(f"Lambda: {function_name}")
    print(f"EventBridge Rule: {rule_name}")
    print(f"\nNext: python3 deploy.py")

if __name__ == '__main__':
    setup()
