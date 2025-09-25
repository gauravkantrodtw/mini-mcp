import logging
from server import mcp
from tools.csv_tools import summarize_csv_file

logger = logging.getLogger(__name__)

# Entry point to run the server
if __name__ == "__main__":
    logger.info("Starting MCP server...")
    try:
        mcp.run()
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        raise