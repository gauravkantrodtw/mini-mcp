#!/usr/bin/env python3
"""
MCP Proxy to connect Cursor to the deployed Lambda function.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurable API Gateway URL
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL")

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
server = Server("mini-mcp-server")

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools from the API Gateway."""
    if not API_GATEWAY_URL:
        logger.error("API_GATEWAY_URL not configured")
        return []
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                API_GATEWAY_URL,
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                headers={"Content-Type": "application/json"},
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
        async with httpx.AsyncClient() as client:
            response = await client.post(
                API_GATEWAY_URL,
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments}
                },
                headers={"Content-Type": "application/json"},
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
