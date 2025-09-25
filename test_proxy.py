#!/usr/bin/env python3
"""
Simple test script for the MCP proxy.
"""

import asyncio
import os
from mcp_proxy import list_tools, call_tool

async def test_proxy():
    """Test the MCP proxy functionality."""
    print("Testing MCP Proxy...")
    
    # Show current configuration
    mcp_url = os.getenv("MCP_SERVER_URL")
    print(f"🔗 MCP Server URL: {mcp_url}")
    
    # Test list_tools
    print("\n1. Testing list_tools...")
    try:
        tools = await list_tools()
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool.name}: {tool.description[:50]}...")
    except Exception as e:
        print(f"❌ Error listing tools: {e}")
    
    # Test call_tool
    print("\n2. Testing call_tool...")
    try:
        result = await call_tool("summarize_csv_file", {"filename": "sample.csv"})
        print(f"✅ Tool executed successfully:")
        print(f"   Result: {result[0].text[:100]}...")
    except Exception as e:
        print(f"❌ Error calling tool: {e}")
    
    print("\n🎉 Test completed!")

if __name__ == "__main__":
    asyncio.run(test_proxy())
