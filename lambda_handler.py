#!/usr/bin/env python3
"""
AWS Lambda entrypoint for the MCP server.
"""

import json
import logging
import time
from mangum import Mangum
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from server import mcp
import tools.csv_tools  # auto-registers all MCP tools
import tools.additional_tools  # auto-registers additional MCP tools

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global handler instance (created once per Lambda container)
_handler = None

async def handle_mcp_request(request_body: str) -> dict:
    """Handle MCP request and return JSON-RPC response."""
    try:
        request_data = json.loads(request_body)
        method = request_data.get("method")
        params = request_data.get("params", {})
        request_id = request_data.get("id")
        
        logger.info(f"Processing MCP request: {method}")
        
        if method == "tools/list":
            tools_list = await mcp.list_tools()
            result = [{"name": tool.name, "description": tool.description} for tool in tools_list]
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            tool_result = await mcp.call_tool(tool_name, tool_args)
            result = tool_result.content if hasattr(tool_result, 'content') else str(tool_result)
        else:
            result = {"error": f"Unknown method: {method}"}
        
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
        
    except Exception as e:
        logger.error(f"Error handling MCP request: {e}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "id": request_data.get("id") if 'request_data' in locals() else None,
            "error": {"code": -32603, "message": "Internal error"}
        }


def get_handler():
    """Get or create ASGI handler for Lambda."""
    global _handler
    if _handler is None:
        async def mcp_endpoint(request):
            body = await request.body()
            return JSONResponse(await handle_mcp_request(body.decode()))
        
        async def health_endpoint(request):
            return JSONResponse({
                "status": "healthy",
                "service": "MCP Server",
                "timestamp": time.time()
            })
        
        app = Starlette(routes=[
            Route("/mcp", mcp_endpoint, methods=["POST"]),
            Route("/health", health_endpoint, methods=["GET"])
        ])

        _handler = Mangum(app, lifespan="off")
        logger.info("Lambda handler initialized")
    return _handler

def lambda_handler(event, context):
    """AWS Lambda handler function."""
    start_time = time.time()
    try:
        response = get_handler()(event, context)
        logger.info("Processed request in %.3fs", time.time() - start_time)
        return response
    except Exception as e:
        logger.error("Lambda handler error: %s", str(e), exc_info=True)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": '{"error": "Internal server error"}'
        }

# Local test mode
if __name__ == "__main__":
    test_event = {
        "version": "2.0",
        "routeKey": "POST /mcp",
        "rawPath": "/mcp",
        "headers": {"content-type": "application/json"},
        "requestContext": {
            "http": {
                "method": "POST", 
                "path": "/mcp", 
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1"
            },
            "requestId": "test-request-id"
        },
        "body": '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}',
        "isBase64Encoded": False,
    }

    print("Testing Lambda handler locally...")
    result = lambda_handler(test_event, None)
    print("Response:")
    print(json.dumps(result, indent=2))

