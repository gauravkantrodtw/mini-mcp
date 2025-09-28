#!/usr/bin/env python3
"""
MCP Proxy to connect Cursor to the deployed Lambda function.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List

import requests
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurable API Gateway URL
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL")
AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")

# AWS credentials for IAM authentication
def get_aws_session():
    """Get AWS session with profile support."""
    profile = os.getenv("AWS_PROFILE")
    region = os.getenv("AWS_REGION", "eu-central-1")
    
    if profile:
        return boto3.Session(profile_name=profile, region_name=region)
    else:
        return boto3.Session(region_name=region)

aws_session = get_aws_session()
credentials = aws_session.get_credentials()

if not credentials:
    logger.error("No AWS credentials found. Please configure AWS credentials or set AWS_PROFILE.")

def sign_request(url: str, method: str, headers: Dict[str, str], body: str) -> Dict[str, str]:
    """Sign HTTP request with AWS IAM credentials for API Gateway."""
    try:
        # Parse URL to get host and path
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        
        # Create AWS request
        aws_request = AWSRequest(
            method=method,
            url=url,
            data=body.encode('utf-8') if body else None,
            headers=headers
        )
        
        # Sign the request
        region = aws_session.region_name or AWS_REGION
        SigV4Auth(credentials, 'execute-api', region).add_auth(aws_request)
        
        # Return signed headers
        return dict(aws_request.headers)
    except Exception as e:
        logger.error(f"Failed to sign request: {e}")
        return headers

def extract_schema_from_description(tool_data):
    """Extract input schema from tool description."""
    import re
    
    description = tool_data.get("description", "")
    name = tool_data.get("name", "")
    
    # Extract parameters from docstring format
    args_match = re.search(r'Args:\s*\n(.*?)(?:\n\s*\n|\n\s*Returns?:|\Z)', description, re.DOTALL)
    
    if args_match:
        properties = {}
        required = []
        
        for line in args_match.group(1).strip().split('\n'):
            line = line.strip()
            if ':' in line and not line.startswith('#'):
                param_match = re.match(r'(\w+)(?:\s*\([^)]*\))?\s*:\s*(.+)', line)
                if param_match:
                    param_name, param_desc = param_match.groups()
                    param_type = "integer" if "number" in param_desc.lower() or "count" in param_desc.lower() else "string"
                    
                    properties[param_name] = {"type": param_type, "description": param_desc.strip()}
                    required.append(param_name)
        
        if properties:
            return {"type": "object", "properties": properties, "required": required}
    
    # Fallback for file-based tools
    if "filename" in name.lower() or "file" in description.lower():
        return {
            "type": "object",
            "properties": {"filename": {"type": "string", "description": "Name of the file to process"}},
            "required": ["filename"]
        }
    
    return {"type": "object", "properties": {}, "required": []}

# Create the server instance
server = Server("daap-mcp-server")

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools from the API Gateway."""
    if not API_GATEWAY_URL:
        logger.error("API_GATEWAY_URL not configured")
        return []
    
    try:
        # Prepare request data
        request_data = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        import json
        body = json.dumps(request_data)
        headers = {"Content-Type": "application/json"}
        
        # Sign request with AWS IAM credentials
        signed_headers = sign_request(API_GATEWAY_URL, "POST", headers, body)
        
        # Use requests for AWS signed requests
        response = requests.post(
            API_GATEWAY_URL,
            data=body,
            headers=signed_headers,
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = response.json()
            if "result" in result:
                tools = [
                    Tool(
                        name=tool_data["name"],
                        description=tool_data["description"],
                        inputSchema=extract_schema_from_description(tool_data)
                    )
                    for tool_data in result["result"]
                ]
                logger.info(f"Retrieved {len(tools)} tools from API Gateway")
                return tools
            else:
                logger.error(f"Error in Lambda response: {result}")
                return []
        else:
            logger.error(f"HTTP error: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        return []

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Call a tool on the API Gateway."""
    if not API_GATEWAY_URL:
        logger.error("API_GATEWAY_URL not configured")
        return [TextContent(type="text", text="Error: API_GATEWAY_URL not configured")]
    
    try:
        # Prepare request data
        request_data = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments}
        }
        import json
        body = json.dumps(request_data)
        headers = {"Content-Type": "application/json"}
        
        # Sign request with AWS IAM credentials
        signed_headers = sign_request(API_GATEWAY_URL, "POST", headers, body)
        
        # Use requests for AWS signed requests
        response = requests.post(
            API_GATEWAY_URL,
            data=body,
            headers=signed_headers,
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = response.json()
            if "result" in result:
                logger.info(f"Tool {name} executed successfully")
                return [TextContent(type="text", text=str(result["result"]))]
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Tool execution error: {error_msg}")
                return [TextContent(type="text", text=f"Error: {error_msg}")]
        else:
            logger.error(f"HTTP error: {response.status_code}")
            return [TextContent(type="text", text=f"HTTP error: {response.status_code}")]
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    """Main entry point."""
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    except Exception as e:
        logger.error(f"MCP server error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
