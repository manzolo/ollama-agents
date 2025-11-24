# Ollama Agents Backoffice

A web-based management interface for orchestrating multiple AI agents through flexible workflows.

## Overview

The Backoffice provides:
- **Web UI**: Modern, responsive interface for managing agents and workflows
- **REST API**: Complete API for programmatic access
- **Workflow Engine**: Execute complex multi-agent pipelines
- **Agent Discovery**: Automatically discover and monitor available agents
- **Execution History**: Track and review workflow executions

## Quick Start

### 1. Start the Backoffice

```bash
# From the project root
docker compose up -d backoffice

# Check status
docker compose ps backoffice
```

### 2. Access the Web UI

Open your browser to:
```
http://localhost:8080
```

You'll see four main tabs:
- **Agents**: View and test available agents
- **Workflows**: Manage workflow definitions
- **Execute**: Run workflows with custom input
- **History**: View execution history

## Features

### Agent Management

The Agents tab shows all registered agents with:
- Real-time health status
- Model information
- Capabilities
- Quick test functionality

### Workflow Management

Create and manage workflows that:
- Chain multiple agents in sequence
- Handle errors gracefully
- Retry failed steps
- Use outputs from previous steps

### Workflow Execution

Execute workflows with:
- Custom input data
- Real-time progress tracking
- Detailed step-by-step results
- Error reporting

### Execution History

Review past executions with:
- Status and duration
- Step-by-step breakdown
- Error details
- Full output from each step

## API Reference

### Base URL
```
http://localhost:8080/api
```

### Endpoints

#### Health Check
```bash
GET /api/health
```

#### List Agents
```bash
GET /api/agents
```

Response:
```json
{
  "count": 2,
  "agents": {
    "swarm-converter": {
      "url": "http://agent-swarm-converter:8000",
      "status": "healthy",
      "model": "llama3.2",
      "capabilities": ["conversion", "yaml"],
      "description": "Converts docker-compose to swarm"
    }
  }
}
```

#### List Workflows
```bash
GET /api/workflows
```

Response:
```json
{
  "count": 1,
  "workflows": [
    {
      "name": "convert-and-validate",
      "description": "Convert and validate swarm stack",
      "steps": 2,
      "version": "1.0.0"
    }
  ]
}
```

#### Execute Workflow
```bash
POST /api/workflows/execute
Content-Type: application/json

{
  "workflow_name": "convert-and-validate",
  "input": "version: '3.8'\nservices:\n  web:\n    image: nginx"
}
```

Response:
```json
{
  "status": "executed",
  "execution_id": "20251124_123456",
  "result": {
    "execution_id": "20251124_123456",
    "workflow_name": "convert-and-validate",
    "status": "completed",
    "current_step": 2,
    "total_steps": 2,
    "duration_seconds": 12.5,
    "step_results": [...]
  }
}
```

#### Get Execution Status
```bash
GET /api/executions/{execution_id}
```

#### Create Workflow
```bash
POST /api/workflows
Content-Type: application/json

{
  "name": "my-workflow",
  "description": "My custom workflow",
  "version": "1.0.0",
  "steps": [
    {
      "name": "step1",
      "agent": "agent-name",
      "input": "original"
    }
  ]
}
```

## Workflow Definition Format

Workflows are defined in YAML format:

```yaml
name: my-workflow
description: Description of what this workflow does
version: 1.0.0

steps:
  - name: first-step
    agent: swarm-converter
    input: original           # Use original workflow input
    timeout: 300              # Timeout in seconds
    retry: 1                  # Number of retries
    on_error: stop            # stop, continue, or skip

  - name: second-step
    agent: swarm-validator
    input: previous           # Use output from previous step
    timeout: 300
    retry: 1
    on_error: stop

metadata:
  author: Your Name
  created: 2025-11-24
  tags:
    - docker
    - validation
```

### Input Sources

- `original`: Use the original workflow input
- `previous`: Use output from the previous step
- `step[N]`: Use output from step N (0-indexed)
- Direct string: Any other value is used as-is

### Error Handling

- `stop`: Stop execution on error (default)
- `continue`: Continue to next step even if current fails
- `skip`: Skip remaining steps if current fails

## Adding Custom Agents to the Backoffice

To register a new agent with the backoffice:

1. **Add the agent URL to docker-compose.yml**:

```yaml
backoffice:
  environment:
    # ... existing env vars ...
    - MY_AGENT_URL=http://agent-my-agent:8000
```

2. **Update the agent registry in app.py**:

```python
AGENT_REGISTRY = {
    "swarm-converter": os.getenv("SWARM_CONVERTER_URL", "..."),
    "swarm-validator": os.getenv("SWARM_VALIDATOR_URL", "..."),
    "my-agent": os.getenv("MY_AGENT_URL", "http://agent-my-agent:8000"),
}
```

3. **Rebuild and restart**:

```bash
docker compose build backoffice
docker compose up -d backoffice
```

The agent will now appear in the Agents tab and can be used in workflows.

## Architecture

```
┌─────────────────────────────────┐
│      Web Browser                │
│   (localhost:8080)              │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│   Backoffice FastAPI Server     │
│   - REST API                    │
│   - Static File Server          │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│   Workflow Orchestrator         │
│   - Load workflow definitions   │
│   - Execute steps sequentially  │
│   - Handle errors & retries     │
└──────────────┬──────────────────┘
               │
       ┌───────┴───────┐
       │               │
       ▼               ▼
┌────────────┐   ┌────────────┐
│  Agent 1   │   │  Agent 2   │
│ (Converter)│   │(Validator) │
└────────────┘   └────────────┘
```

## Directory Structure

```
backoffice/
├── Dockerfile              # Container definition
├── README.md              # This file
├── backend/               # Backend API
│   ├── app.py            # FastAPI server
│   ├── orchestrator.py   # Workflow engine
│   └── requirements.txt  # Python dependencies
├── frontend/              # Frontend UI
│   ├── index.html        # Main page
│   ├── app.js            # Application logic
│   └── styles.css        # Styles
└── workflows/             # Workflow definitions
    ├── convert-and-validate.yml
    └── README.md
```

## Development

### Running Locally

```bash
# Install dependencies
cd backoffice/backend
pip install -r requirements.txt

# Set environment variables
export WORKFLOWS_DIR=../workflows
export FRONTEND_DIR=../frontend
export SWARM_CONVERTER_URL=http://localhost:7001
export SWARM_VALIDATOR_URL=http://localhost:7002

# Run server
python app.py
```

### API Documentation

Interactive API documentation is available at:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

## Troubleshooting

### Backoffice not starting

```bash
# Check logs
docker compose logs backoffice

# Check if agents are healthy
docker compose ps

# Restart backoffice
docker compose restart backoffice
```

### Agents not appearing

1. Check agent health endpoints
2. Verify agent URLs in docker-compose.yml
3. Check network connectivity
4. Review agent registry in app.py

### Workflow execution fails

1. Check agent health status
2. Verify workflow YAML syntax
3. Check agent compatibility
4. Review execution logs in History tab

## Security Notes

**Important**: The current implementation has no authentication. For production use:

1. Add authentication middleware
2. Implement API key validation
3. Use HTTPS/TLS
4. Add rate limiting
5. Validate all user inputs
6. Restrict network access

## Examples

### Example 1: Convert and Validate

```bash
# Using the API
curl -X POST http://localhost:8080/api/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "convert-and-validate",
    "input": "version: '\''3.8'\''\nservices:\n  web:\n    image: nginx\n    ports:\n      - 80:80"
  }'
```

### Example 2: Custom Workflow

Create `workflows/my-workflow.yml`:

```yaml
name: my-custom-workflow
description: My custom multi-step workflow
version: 1.0.0

steps:
  - name: analyze
    agent: swarm-converter
    input: original

  - name: validate
    agent: swarm-validator
    input: previous
```

Then execute via the Web UI or API.

## License

Same as parent project.

## Support

For issues specific to the backoffice:
1. Check logs: `docker compose logs backoffice`
2. Verify agent connectivity
3. Review workflow syntax
4. Check API documentation at `/docs`
