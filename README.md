# Mini MCP Server

A lightweight MCP (Model Context Protocol) server for CSV analysis, deployable to AWS Lambda.

## Features

- **CSV Analysis**: Analyze CSV files with row/column counts
- **AWS Lambda Deployment**: Serverless deployment with API Gateway
- **Cursor Integration**: Works with Cursor IDE via MCP proxy
- **Configurable**: Environment-based configuration

## Configuration

### Environment Variables

- `MCP_SERVER_URL`: Your deployed MCP server URL (default: current Lambda URL)
- `AWS_PROFILE`: AWS profile for local development
- `AWS_REGION`: AWS region (default: eu-central-1)

### Setup

1. **Copy environment template**:
   ```bash
   cp env.example .env
   ```

2. **Update your MCP server URL** in `.env`:
   ```
   MCP_SERVER_URL=https://your-api-gateway-id.execute-api.eu-central-1.amazonaws.com/prod/mcp
   ```

### Centralized Configuration

All deployment scripts use centralized configuration from `config.env`:

- `FUNCTION_NAME`: Lambda function name
- `API_GATEWAY_NAME`: API Gateway name
- `AWS_REGION`: AWS region
- `MCP_SERVER_URL`: MCP server endpoint URL

## Usage

### Local Testing

```bash
# Test Lambda handler
uv run lambda_handler.py

# Test MCP proxy
uv run test_proxy.py
```

### Deployment

```bash
# Create deployment package
./create_deployment_package.sh

# Deploy via GitHub Actions (manual trigger)
# Or upload mcp-server-deployment.zip to AWS Lambda
```

### Cursor Integration

The MCP proxy automatically connects to your deployed server using the configured URL.

## Project Structure

```
├── lambda_handler.py          # AWS Lambda entry point
├── mcp_proxy.py              # MCP proxy for Cursor
├── server.py                 # MCP server configuration
├── tools/csv_tools.py        # CSV analysis tools
├── utils/file_reader.py      # File utilities
├── create_deployment_package.sh  # Deployment script
└── .github/workflows/deploy.yml  # GitHub Actions
```
