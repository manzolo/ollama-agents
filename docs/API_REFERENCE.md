# API Reference

Complete API documentation for Ollama Agents.

## Agent API Endpoints

All agents expose the same API interface.

### Common Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/info` | GET | Agent information |
| `/process` | POST | Process input (full response) |
| `/process/raw` | POST | Process input (clean output JSON) |
| `/process/raw/text` | POST | Process input (plain text only) |
| `/context` | GET | View context history |
| `/context` | DELETE | Clear context |
| `/docs` | GET | Swagger UI documentation |
| `/redoc` | GET | ReDoc documentation |
| `/openapi.json` | GET | OpenAPI schema |

### POST /process

Process input and get full response with markdown and explanations.

**Request:**
```json
{
  "input": "string (required)",
  "stream": false,
  "options": {
    "temperature": 0.7,
    "num_predict": 4096
  }
}
```

**Response:**
```json
{
  "agent": "swarm-converter",
  "output": "Converted stack file content...",
  "model": "llama3.2",
  "timestamp": "2025-11-23T10:30:00",
  "metadata": {
    "temperature": 0.3,
    "max_tokens": 8192
  }
}
```

**Example:**
```bash
curl -X POST http://localhost:7001/process \
  -H "Content-Type: application/json" \
  -d '{
    "input": "version: \"3.8\"\nservices:\n  web:\n    build: .\n    ports:\n      - \"80:80\"",
    "options": {
      "temperature": 0.3
    }
  }' | jq .
```

### POST /process/raw

Process input and get clean extracted output as JSON (for agents/APIs).

**Request:** Same as `/process`

**Response:**
```json
{
  "agent": "swarm-converter",
  "output": "clean extracted YAML/JSON/text content",
  "model": "llama3.2",
  "timestamp": "2025-11-23T10:30:00"
}
```

**Example:**
```bash
curl -X POST http://localhost:7001/process/raw \
  -H "Content-Type: application/json" \
  -d '{"input": "your content"}' \
  | jq -r '.output'
```

### POST /process/raw/text

Process input and get pure plain text output (for files/pipes).

**Request:** Same as `/process`

**Response:** Plain text (no JSON wrapping)

**Example:**
```bash
curl -X POST http://localhost:7001/process/raw/text \
  -H "Content-Type: application/json" \
  -d '{"input": "your content"}' \
  > output.yml
```

### GET /health

Check agent health status.

**Response:**
```json
{
  "status": "healthy",
  "agent": "swarm-converter",
  "ollama_connected": true,
  "model": "llama3.2"
}
```

**Example:**
```bash
curl http://localhost:7001/health | jq .
```

### GET /info

Get agent information and capabilities.

**Response:**
```json
{
  "agent": "swarm-converter",
  "version": "1.0.0",
  "description": "Converts Docker Compose to Swarm stacks",
  "model": "llama3.2",
  "capabilities": ["docker-compose", "swarm-stack"],
  "temperature": 0.3,
  "max_tokens": 8192
}
```

### GET /context

View recent interactions and context history.

**Query Parameters:**
- `limit` - Number of interactions to return (default: 10)

**Response:**
```json
{
  "agent": "swarm-converter",
  "context": [
    {
      "timestamp": "2025-11-23T10:30:00",
      "input": "...",
      "output": "..."
    }
  ],
  "total": 25
}
```

**Example:**
```bash
curl "http://localhost:7001/context?limit=5" | jq .
```

### DELETE /context

Clear agent context memory.

**Response:**
```json
{
  "status": "cleared",
  "agent": "swarm-converter"
}
```

**Example:**
```bash
curl -X DELETE http://localhost:7001/context | jq .
```

## Backoffice API Endpoints

### Agents

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents` | GET | List all agents |
| `/api/agents/{name}` | GET | Get agent details |

### Workflows

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/workflows` | GET | List all workflows |
| `/api/workflows` | POST | Create workflow |
| `/api/workflows/{name}` | GET | Get workflow details |
| `/api/workflows/{name}` | DELETE | Delete workflow |
| `/api/workflows/{name}/execute` | POST | Execute workflow |

### Executions

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/executions` | GET | List execution history |
| `/api/executions/{id}` | GET | Get execution details |

## Swagger UI Documentation

Every agent includes interactive API documentation:

- **Swagger UI**: `http://localhost:<AGENT_PORT>/docs`
- **ReDoc**: `http://localhost:<AGENT_PORT>/redoc`
- **OpenAPI JSON**: `http://localhost:<AGENT_PORT>/openapi.json`

### Example

```bash
# Open Swagger UI for swarm-converter
open http://localhost:7001/docs

# View OpenAPI schema
curl http://localhost:7001/openapi.json | jq .
```

## Makefile Commands

Quick commands for API operations:

```bash
# Run agent with file
make run agent=swarm-converter file=docker-compose.yml

# Get raw output
make run-raw agent=swarm-converter file=docker-compose.yml

# Test agent
make test-agent agent=swarm-converter

# Get agent info
make agent-info agent=swarm-converter

# View context
make agent-context agent=swarm-converter

# Open Swagger UI
make docs agent=swarm-converter
```
