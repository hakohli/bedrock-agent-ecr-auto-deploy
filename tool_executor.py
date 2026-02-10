"""
Lambda function for executing Bedrock Agent actions from container.
This is called by Bedrock Agents (not Agent Core client).
"""

import json

def lambda_handler(event, context):
    """Execute tool for Bedrock Agent"""
    
    # Bedrock Agent format
    action_group = event.get('actionGroup')
    api_path = event.get('apiPath')
    function_name = event.get('function')
    parameters = event.get('parameters', [])
    
    # Convert parameters to dict
    params = {p['name']: p['value'] for p in parameters} if isinstance(parameters, list) else parameters
    
    # Determine tool name
    tool_name = function_name or (api_path.strip('/') if api_path else None)
    
    # Tool implementations
    if tool_name == "get_weather":
        city = params.get("city", "Unknown")
        result = {
            "weather": f"Sunny in {city}",
            "temperature": 72,
            "humidity": 65
        }
    
    elif tool_name == "calculate":
        a = float(params.get("a", 0))
        b = float(params.get("b", 0))
        result = {"result": a + b}
    
    elif tool_name == "get_time":
        from datetime import datetime
        import pytz
        
        timezone = params.get("timezone", "UTC")
        try:
            tz = pytz.timezone(timezone)
            current_time = datetime.now(tz)
            result = {
                "time": current_time.strftime("%I:%M %p"),
                "date": current_time.strftime("%Y-%m-%d"),
                "timezone": timezone,
                "day": current_time.strftime("%A")
            }
        except:
            result = {"error": f"Invalid timezone: {timezone}"}
    
    else:
        result = {"error": f"Unknown tool: {tool_name}"}
    
    # Return in Bedrock Agent format
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
