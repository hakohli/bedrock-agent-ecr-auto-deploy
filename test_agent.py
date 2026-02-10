#!/usr/bin/env python3
"""Test the newly created agent with get_time tool"""

import boto3
import json

# Get latest agent
bedrock = boto3.client('bedrock-agent')
agents = bedrock.list_agents()
latest_agent = sorted(
    [a for a in agents['agentSummaries'] if a['agentName'].startswith('agent-core-')],
    key=lambda x: x['updatedAt'],
    reverse=True
)[0]

agent_id = latest_agent['agentId']
agent_name = latest_agent['agentName']

print(f"🤖 Testing Agent: {agent_name}")
print(f"   Agent ID: {agent_id}")
print(f"   Status: {latest_agent['agentStatus']}\n")

# Test the new get_time tool
print("=" * 60)
print("TEST 1: Get time in New York")
print("=" * 60)

bedrock_runtime = boto3.client('bedrock-agent-runtime')

try:
    response = bedrock_runtime.invoke_agent(
        agentId=agent_id,
        agentAliasId='TSTALIASID',
        sessionId='test-time-1',
        inputText='What time is it in New York?'
    )
    
    print("Response:")
    for event in response['completion']:
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                print(chunk['bytes'].decode(), end='')
    print("\n")
except Exception as e:
    print(f"Error: {e}\n")

# Test weather (existing tool)
print("=" * 60)
print("TEST 2: Get weather (existing tool)")
print("=" * 60)

try:
    response = bedrock_runtime.invoke_agent(
        agentId=agent_id,
        agentAliasId='TSTALIASID',
        sessionId='test-weather-1',
        inputText='What is the weather in Tokyo?'
    )
    
    print("Response:")
    for event in response['completion']:
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                print(chunk['bytes'].decode(), end='')
    print("\n")
except Exception as e:
    print(f"Error: {e}\n")

# Test calculate (existing tool)
print("=" * 60)
print("TEST 3: Calculate (existing tool)")
print("=" * 60)

try:
    response = bedrock_runtime.invoke_agent(
        agentId=agent_id,
        agentAliasId='TSTALIASID',
        sessionId='test-calc-1',
        inputText='What is 123 + 456?'
    )
    
    print("Response:")
    for event in response['completion']:
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                print(chunk['bytes'].decode(), end='')
    print("\n")
except Exception as e:
    print(f"Error: {e}\n")

print("=" * 60)
print("✅ Testing complete!")
print("=" * 60)
