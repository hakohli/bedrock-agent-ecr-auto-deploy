#!/usr/bin/env python3
"""
Lambda that auto-creates Bedrock Agent when ECR image is pushed.
Agent uses the containerized Lambda for action execution.
"""

import json
import boto3
import os
from datetime import datetime

def lambda_handler(event, context):
    """
    Triggered by EventBridge when ECR image is pushed.
    Creates a new Bedrock Agent with Lambda action group.
    """
    
    bedrock = boto3.client('bedrock-agent')
    ecr = boto3.client('ecr')
    lambda_client = boto3.client('lambda')
    iam = boto3.client('iam')
    
    bucket = os.environ['S3_BUCKET']
    repo_name = os.environ['ECR_REPO']
    agent_role_arn = os.environ['AGENT_ROLE_ARN']
    
    account_id = context.invoked_function_arn.split(':')[4]
    region = os.environ['AWS_REGION']
    
    # Get latest image
    images = ecr.describe_images(
        repositoryName=repo_name,
        maxResults=1
    )
    
    if not images['imageDetails']:
        return {'statusCode': 400, 'body': 'No images found'}
    
    image_digest = images['imageDetails'][0]['imageDigest']
    image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{repo_name}@{image_digest}"
    
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    
    # Update/Create Lambda with new image
    lambda_function_name = 'AgentCoreToolExecutor'
    try:
        lambda_client.update_function_code(
            FunctionName=lambda_function_name,
            ImageUri=image_uri
        )
        print(f"✓ Updated Lambda: {lambda_function_name}")
    except lambda_client.exceptions.ResourceNotFoundException:
        # Lambda doesn't exist, will be created by setup
        print(f"⚠️  Lambda not found: {lambda_function_name}")
        return {'statusCode': 400, 'body': 'Lambda not found'}
    
    lambda_arn = lambda_client.get_function(FunctionName=lambda_function_name)['Configuration']['FunctionArn']
    
    # Wait for Lambda to be ready
    import time
    time.sleep(5)
    
    # Create new Bedrock Agent
    agent_name = f"agent-core-{timestamp}"
    
    print(f"Creating agent: {agent_name}")
    
    agent_response = bedrock.create_agent(
        agentName=agent_name,
        agentResourceRoleArn=agent_role_arn,
        foundationModel='anthropic.claude-3-sonnet-20240229-v1:0',
        instruction='You are a helpful assistant with custom tools for weather, calculations, and more.'
    )
    
    agent_id = agent_response['agent']['agentId']
    print(f"✓ Created agent: {agent_id}")
    
    # Wait for agent to be ready
    time.sleep(10)
    
    # Add action group with Lambda
    bedrock.create_agent_action_group(
        agentId=agent_id,
        agentVersion='DRAFT',
        actionGroupName='core-tools',
        actionGroupExecutor={'lambda': lambda_arn},
        functionSchema={
            'functions': [
                {
                    'name': 'get_weather',
                    'description': 'Get current weather for a city',
                    'parameters': {
                        'city': {
                            'type': 'string',
                            'description': 'City name',
                            'required': True
                        }
                    }
                },
                {
                    'name': 'calculate',
                    'description': 'Add two numbers',
                    'parameters': {
                        'a': {
                            'type': 'number',
                            'description': 'First number',
                            'required': True
                        },
                        'b': {
                            'type': 'number',
                            'description': 'Second number',
                            'required': True
                        }
                    }
                }
            ]
        }
    )
    print(f"✓ Added action group")
    
    # Prepare agent
    bedrock.prepare_agent(agentId=agent_id)
    print(f"✓ Agent prepared")
    
    # Store agent info in S3 for reference
    agent_info = {
        "agent_id": agent_id,
        "agent_name": agent_name,
        "version": timestamp,
        "image_uri": image_uri,
        "lambda_arn": lambda_arn,
        "created_at": timestamp
    }
    
    s3 = boto3.client('s3')
    s3.put_object(
        Bucket=bucket,
        Key=f'agents/agent-{timestamp}.json',
        Body=json.dumps(agent_info, indent=2),
        ContentType='application/json'
    )
    
    s3.put_object(
        Bucket=bucket,
        Key='agents/latest.json',
        Body=json.dumps(agent_info, indent=2),
        ContentType='application/json'
    )
    
    print(f"✅ Agent creation complete: {agent_id}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'agent_id': agent_id,
            'agent_name': agent_name,
            'version': timestamp,
            'image_uri': image_uri
        })
    }
