# Tools package for MCP server
# Auto-register all tools by importing them

# Import all tool modules to auto-register them
from . import csv_tools
from . import s3_csv_tools

# This ensures all tools are registered when the package is imported
__all__ = ['csv_tools', 's3_csv_tools']
