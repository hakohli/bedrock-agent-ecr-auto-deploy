#!/usr/bin/env python3
"""Deploy Agent Core tools to ECR - triggers auto-configuration"""

import boto3
import zipfile
from io import BytesIO
import time

def deploy():
    s3 = boto3.client('s3')
    codebuild = boto3.client('codebuild')
    lambda_client = boto3.client('lambda')
    ecr = boto3.client('ecr')
    
    account_id = boto3.client('sts').get_caller_identity()['Account']
    region = boto3.session.Session().region_name or 'us-east-1'
    bucket_name = f'agent-core-configs-{account_id}'
    repo_name = 'agent-core-tools'
    
    # Package source
    print("📦 Packaging source...")
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write('tool_executor.py')
        zf.write('Dockerfile')
        zf.write('buildspec.yml')
    
    s3.put_object(Bucket=bucket_name, Key='source.zip', Body=zip_buffer.getvalue())
    print("✓ Uploaded to S3")
    
    # Trigger CodeBuild
    print("🔨 Starting CodeBuild...")
    response = codebuild.start_build(projectName='agent-core-builder')
    build_id = response['build']['id']
    print(f"✓ Build started: {build_id.split(':')[1]}")
    
    # Wait for build
    print("⏳ Building (2-3 minutes)...")
    while True:
        response = codebuild.batch_get_builds(ids=[build_id])
        status = response['builds'][0]['buildStatus']
        
        if status == 'SUCCEEDED':
            print("✅ Build succeeded!")
            break
        elif status in ['FAILED', 'FAULT', 'TIMED_OUT', 'STOPPED']:
            print(f"❌ Build failed: {status}")
            return False
        
        time.sleep(15)
    
    # Wait for EventBridge + Lambda
    print("⏳ Waiting for auto-deploy Lambda...")
    time.sleep(10)
    
    # Get latest image
    images = ecr.describe_images(repositoryName=repo_name, maxResults=1)
    image_digest = images['imageDetails'][0]['imageDigest']
    image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{repo_name}@{image_digest}"
    
    # Create/update tool executor Lambda
    function_name = 'AgentCoreToolExecutor'
    role_arn = boto3.client('iam').get_role(RoleName='AgentCoreAutoDeployRole')['Role']['Arn']
    
    try:
        lambda_client.create_function(
            FunctionName=function_name,
            Role=role_arn,
            Code={'ImageUri': image_uri},
            PackageType='Image',
            Timeout=60
        )
        print(f"✓ Created Lambda: {function_name}")
    except lambda_client.exceptions.ResourceConflictException:
        lambda_client.update_function_code(
            FunctionName=function_name,
            ImageUri=image_uri
        )
        print(f"✓ Updated Lambda: {function_name}")
    
    # Verify config in S3
    try:
        response = s3.get_object(Bucket=bucket_name, Key='agent-configs/latest.json')
        config = response['Body'].read().decode()
        print("✓ Agent Core config created in S3")
    except:
        print("⚠️  Config not yet in S3, may take a moment")
    
    print("\n" + "="*60)
    print("DEPLOYMENT COMPLETE!")
    print("="*60)
    print(f"Image: {image_uri}")
    print(f"Config: s3://{bucket_name}/agent-configs/latest.json")
    print(f"\nTest with:")
    print(f"python3 agent_core_client.py {bucket_name}")

if __name__ == '__main__':
    deploy()
