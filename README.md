# Ollama Agents - Modular AI Agent Architecture

A clean, modular, and extensible Docker Compose architecture for hosting multiple specialized AI agents powered by Ollama, with a powerful **Backoffice Web UI** for managing multi-agent workflows.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Backoffice - Workflow Manager](#backoffice---workflow-manager)
- [Project Structure](#project-structure)
- [Base Agents](#base-agents)
- [Swagger UI / API Documentation](#swagger-ui--api-documentation)
- [Creating Workflows](#creating-workflows)
- [Adding New Agents](#adding-new-agents)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Makefile Commands](#makefile-commands)
- [Troubleshooting](#troubleshooting)

## Overview

This project provides a modular framework for deploying multiple specialized AI agents, each with:

- **Its own Ollama model** - Choose the best model for each task
- **Custom prompt configuration** - Define agent behavior via YAML
- **Dedicated API endpoint** - Each agent has its own REST API
- **Optional context memory** - Agents can remember past interactions
- **Independent scaling** - Scale agents individually based on load

**NEW**: **Backoffice Web UI** - A modern web interface for creating and executing multi-agent workflows without writing code!

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│               Backoffice Web UI (:8080)                 │
│   - Workflow Management  - Agent Discovery              │
│   - Visual Execution     - History Tracking             │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  Ollama Engine (:11434)                 │
│                  (LLM Model Server)                     │
└────────────┬─────────────┬─────────────┬────────────────┘
             │             │             │
             ▼             ▼             ▼
     ┌───────────┐  ┌───────────┐  ┌───────────┐
     │  Agent 1  │  │  Agent 2  │  │  Agent N  │
     │  (Swarm   │  │ (Swarm    │  │  (Custom) │
     │ Converter)│  │ Validator)│  │           │
     └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
           │              │              │
           ▼              ▼              ▼
        :7001          :7002          :700N
         API            API            API
```

The system supports:
- **Individual agents** - Call agents directly via their APIs
- **Workflow orchestration** - Chain agents through the Backoffice
- **YAML-based workflows** - Define complex pipelines without coding
- **Error handling** - Automatic retries and graceful failures

## Quick Start

### Prerequisites

- Docker and Docker Compose
- At least 8GB RAM (16GB+ recommended)
- (Optional) NVIDIA GPU with Docker GPU support - see [GPU-SETUP.md](GPU-SETUP.md) for details

### 1. Initialize the Project

```bash
# Clone or navigate to the project directory
cd ollama-agents

# Initialize and start all services
make init
```

This will:
- Build all containers (agents + backoffice)
- Start Ollama, agents, and the backoffice
- Pull the required models (llama3.2)
- Display service status

### 2. Access the Backoffice Web UI

Open your browser to:
```
http://localhost:8080
```

The Backoffice provides:
- **Agents Tab** - View all available agents and their status
- **Workflows Tab** - Create and manage multi-agent workflows
- **Execute Tab** - Run workflows with custom input
- **History Tab** - Review past workflow executions

### 3. Test an Agent Directly (Optional)

You can also call agents directly via their APIs:

```bash
# Quick health check
make test-agent agent=swarm-converter

# Run with a YAML file
make run agent=swarm-converter file=docker-compose.yml

# Or manually test with curl
curl -X POST http://localhost:7001/process \
  -H "Content-Type: application/json" \
  -d '{
    "input": "version: \"3.8\"\nservices:\n  web:\n    build: .\n    ports:\n      - \"80:80\"\n    restart: always"
  }' | jq .
```

### 4. Check All Services

```bash
# View status
make status

# Check health
make health

# View logs
make logs
```

## Backoffice - Workflow Manager

The **Backoffice** is a web-based interface for managing agents and orchestrating multi-agent workflows.

### Features

- 🤖 **Agent Discovery** - Automatically detect and monitor all agents
- 🔄 **Workflow Management** - Create, edit, and delete workflows via UI or YAML
- ▶️ **Visual Execution** - Run workflows and see real-time progress
- 📊 **Execution History** - Track all workflow runs with detailed results
- 🎨 **Modern UI** - Clean, responsive interface with toast notifications
- 🔗 **REST API** - Full API for programmatic access

### Quick Example

1. **Access the UI**: http://localhost:8080
2. **Create a Workflow** (or use the pre-built example):
   ```yaml
   name: convert-and-validate
   description: Convert docker-compose to swarm and validate
   steps:
     - name: convert
       agent: swarm-converter
       input: original
     - name: validate
       agent: swarm-validator
       input: previous
   ```
3. **Execute the Workflow** with your docker-compose file
4. **View Results** in real-time with step-by-step output

For complete documentation, see [backoffice/README.md](backoffice/README.md) and [BACKOFFICE-GUIDE.md](BACKOFFICE-GUIDE.md).

## Project Structure

```
ollama-agents/
├── docker-compose.yml          # Main orchestration file
├── .env                        # Environment configuration
├── Makefile                    # Convenient commands
├── README.md                   # This file
├── BACKOFFICE-GUIDE.md        # Complete backoffice guide
│
├── agents/
│   ├── base/                   # Base agent implementation
│   │   ├── Dockerfile         # Agent container definition
│   │   ├── app.py            # FastAPI application
│   │   └── requirements.txt  # Python dependencies
│   │
│   ├── swarm-converter/       # Docker Compose to Swarm converter
│   │   ├── prompt.txt        # System prompt
│   │   └── config.yml        # Agent configuration
│   │
│   ├── swarm-validator/       # Swarm stack validator
│   │   ├── prompt.txt        # System prompt
│   │   └── config.yml        # Agent configuration
│   │
│   └── .agent-template/       # Template for new agents
│       ├── prompt.txt
│       └── config.yml
│
├── backoffice/                 # Workflow management system
│   ├── Dockerfile             # Backoffice container
│   ├── README.md              # Detailed documentation
│   ├── backend/               # FastAPI server
│   │   ├── app.py            # Main API server
│   │   ├── orchestrator.py   # Workflow engine
│   │   └── requirements.txt  # Dependencies
│   ├── frontend/              # Web UI
│   │   ├── index.html        # Main page
│   │   ├── app.js            # Application logic
│   │   └── styles.css        # Styling
│   └── workflows/             # Workflow definitions (YAML)
│       └── convert-and-validate.yml
│
└── shared/
    └── context/               # Persistent context storage
        ├── swarm-converter/   # Agent-specific context
        └── swarm-validator/
```

## Base Agents

### Swarm Converter

The swarm-converter agent converts Docker Compose files to Docker Swarm stack files.

**Endpoint**: http://localhost:7001

### Swarm Validator

The swarm-validator agent validates Docker Swarm stack files for correctness and best practices.

**Endpoint**: http://localhost:7002

### Features

- Analyzes Docker Compose YAML structure
- Converts to Swarm-compatible format
- Provides conversion notes and warnings
- Validates Swarm compatibility
- Suggests best practices

### API Endpoints

#### POST /process
Process a Docker Compose file

```bash
curl -X POST http://localhost:7001/process \
  -H "Content-Type: application/json" \
  -d '{
    "input": "your docker-compose.yml content here",
    "stream": false,
    "options": {
      "temperature": 0.3
    }
  }' | jq .
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

#### GET /health
Check agent health

```bash
curl http://localhost:7001/health | jq .
```

#### GET /info
Get agent information

```bash
curl http://localhost:7001/info | jq .
```

#### GET /context
View recent interactions

```bash
curl http://localhost:7001/context | jq .
```

#### DELETE /context
Clear context memory

```bash
curl -X DELETE http://localhost:7001/context | jq .
```

## Swagger UI / API Documentation

Every agent includes comprehensive interactive API documentation powered by Swagger UI and OpenAPI 3.0.

### Accessing Swagger UI

Each agent exposes its API documentation at:
- **Swagger UI**: `http://localhost:<AGENT_PORT>/docs`
- **ReDoc**: `http://localhost:<AGENT_PORT>/redoc`
- **OpenAPI JSON**: `http://localhost:<AGENT_PORT>/openapi.json`

For the swarm-converter agent:
```bash
# Open Swagger UI in browser
open http://localhost:7001/docs

# Or use curl to view the OpenAPI schema
curl http://localhost:7001/openapi.json | jq .
```

### Features

The Swagger UI provides:

1. **Interactive Testing** - Try out API endpoints directly from your browser
2. **Request Examples** - Pre-filled example requests for each endpoint
3. **Response Schemas** - Detailed response models and examples
4. **Authentication Testing** - Test authenticated requests (when enabled)
5. **Model Schemas** - View all Pydantic models and their fields

### Example: Using Swagger UI

1. Navigate to `http://localhost:7001/docs`
2. Click on **POST /process** to expand the endpoint
3. Click **"Try it out"**
4. Enter your input in the request body:
   ```json
   {
     "input": "version: '3.8'\nservices:\n  web:\n    build: .\n    restart: always",
     "options": {
       "temperature": 0.3
     }
   }
   ```
5. Click **"Execute"** to send the request
6. View the response below with full details

### API Tags

Endpoints are organized into logical groups:

- **agent** - Main agent processing operations
- **health** - Health and monitoring endpoints
- **context** - Context memory operations

### OpenAPI Specification

The OpenAPI specification includes:
- Detailed endpoint descriptions
- Request/response examples
- Model schemas with field descriptions
- Parameter validation rules
- HTTP status codes
- Authentication requirements (when configured)

### Customizing Documentation

To customize the Swagger UI for your agents:

1. Edit `agents/base/app.py`
2. Modify the `FastAPI` initialization:
   ```python
   app = FastAPI(
       title="Your Agent Name",
       description="Your description",
       version="1.0.0",
       # ... more options
   )
   ```
3. Add/modify tags for endpoints:
   ```python
   @app.post("/process", tags=["agent"], summary="...")
   ```
4. Rebuild the agent: `make rebuild`

## Inter-Agent Communication

Agents can communicate with each other using the `/process/raw` endpoints for clean output extraction.

### Raw Output Endpoints

The framework provides three levels of output:

1. **`/process`** - Full output with markdown and explanations (for humans)
2. **`/process/raw`** - Clean extracted output as JSON (for agents/APIs)
3. **`/process/raw/text`** - Pure plain text (for files/pipes)

### Quick Example

```bash
# Get clean YAML output (without markdown formatting)
make run-raw agent=swarm-converter file=docker-compose.yml

# Or with curl
curl -X POST http://localhost:7001/process/raw \
  -H "Content-Type: application/json" \
  -d '{"input": "your content"}' \
  | jq -r '.output'

# Save directly to file
curl -X POST http://localhost:7001/process/raw/text \
  -H "Content-Type: application/json" \
  -d '{"input": "your content"}' \
  > output.yml
```

### Agent-to-Agent Communication (Python)

```python
import httpx

async def call_agent(agent_url: str, input_text: str) -> str:
    """Call another agent and get clean output"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{agent_url}/process/raw",
            json={"input": input_text}
        )
        result = response.json()
        return result["output"]  # Clean extracted output

# Usage
swarm_stack = await call_agent(
    "http://agent-swarm-converter:8000",
    docker_compose_content
)
```

### Multi-Agent Pipeline Example

```python
# Step 1: Analyze with one agent
analysis = await call_agent("http://agent-analyzer:8000", input_data)

# Step 2: Convert based on analysis
converted = await call_agent("http://agent-swarm-converter:8000", input_data)

# Step 3: Validate the result
validation = await call_agent("http://agent-validator:8000", converted)
```

For detailed examples and patterns, see [INTER-AGENT-COMMUNICATION.md](INTER-AGENT-COMMUNICATION.md).

## Creating Workflows

Workflows allow you to chain multiple agents together through the Backoffice. They are defined in YAML format and stored in `backoffice/workflows/`.

### Workflow Format

```yaml
name: workflow-name
description: What this workflow does
version: 1.0.0

steps:
  - name: step-name
    agent: agent-name        # Name from agent registry
    input: original          # Input source (see below)
    timeout: 300             # Optional timeout in seconds
    retry: 1                 # Optional number of retries
    on_error: stop           # stop, continue, or skip

metadata:
  author: Your Name
  tags: [docker, validation]
```

### Input Sources

- **`original`** - Use the initial workflow input
- **`previous`** - Use output from the previous step (default)
- **`step[N]`** - Use output from step N (0-indexed)
- Direct string - Any other value is used as literal input

### Error Handling

- **`stop`** - Stop workflow execution on error (default)
- **`continue`** - Continue to next step even if this step fails
- **`skip`** - Skip remaining steps if this step fails

### Example: Sequential Pipeline

```yaml
name: convert-and-validate
description: Convert docker-compose to swarm and validate it
version: 1.0.0

steps:
  - name: convert-to-swarm
    agent: swarm-converter
    input: original
    timeout: 300
    retry: 1
    on_error: stop

  - name: validate-swarm-stack
    agent: swarm-validator
    input: previous
    timeout: 300
    retry: 1
    on_error: stop
```

### Managing Workflows

**Via Web UI:**
1. Go to http://localhost:8080
2. Click the **Workflows** tab
3. Click **Create** button
4. Fill in the workflow details and YAML

**Via File System:**
1. Create a YAML file in `backoffice/workflows/`
2. Refresh the Workflows tab in the UI
3. The workflow appears automatically

**Via API:**
```bash
curl -X POST http://localhost:8080/api/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-workflow",
    "description": "My custom workflow",
    "version": "1.0.0",
    "steps": [...]
  }'
```

For more examples and advanced patterns, see [backoffice/workflows/README.md](backoffice/workflows/README.md).

## Adding New Agents

### Step 1: Create Agent Configuration

```bash
# Create a new agent directory
mkdir -p agents/my-new-agent

# Copy templates
cp agents/.agent-template/prompt.txt agents/my-new-agent/
cp agents/.agent-template/config.yml agents/my-new-agent/
```

### Step 2: Customize the Prompt

Edit `agents/my-new-agent/prompt.txt`:

```text
You are a specialized [DESCRIPTION] agent.

## Your Role and Expertise
[Define the agent's expertise]

## Your Task
[Describe what the agent should do]

## Guidelines
- [Guideline 1]
- [Guideline 2]

## Output Format
[Specify expected output format]
```

### Step 3: Configure the Agent

Edit `agents/my-new-agent/config.yml`:

```yaml
agent:
  name: my-new-agent
  description: Brief description
  version: 1.0.0

capabilities:
  - capability-1
  - capability-2

options:
  temperature: 0.7
  num_predict: 4096
  top_k: 40
  top_p: 0.9
```

### Step 4: Add to Docker Compose

Edit `docker-compose.yml` and add:

```yaml
  my-new-agent:
    build:
      context: ./agents/base
      dockerfile: Dockerfile
    container_name: agent-my-new-agent
    restart: unless-stopped
    ports:
      - "${MY_NEW_AGENT_PORT:-7002}:8000"
    volumes:
      - ./agents/my-new-agent/prompt.txt:/app/prompt.txt:ro
      - ./agents/my-new-agent/config.yml:/app/config.yml:ro
      - ./shared/context/my-new-agent:/app/context
    networks:
      - agent-network
    environment:
      - AGENT_NAME=my-new-agent
      - OLLAMA_HOST=http://ollama:11434
      - MODEL_NAME=${MY_NEW_AGENT_MODEL:-llama3.2}
      - TEMPERATURE=${MY_NEW_AGENT_TEMPERATURE:-0.7}
      - MAX_TOKENS=${MY_NEW_AGENT_MAX_TOKENS:-4096}
    depends_on:
      ollama:
        condition: service_healthy
```

### Step 5: Add Environment Variables

Edit `.env` and add:

```bash
# My New Agent Configuration
MY_NEW_AGENT_PORT=7002
MY_NEW_AGENT_MODEL=llama3.2
MY_NEW_AGENT_TEMPERATURE=0.7
MY_NEW_AGENT_MAX_TOKENS=4096
```

### Step 6: Deploy the Agent

```bash
# Build and start the new agent
make rebuild

# Test the new agent
make test-agent agent=my-new-agent

# Check health
make health
```

## API Reference

All agents expose the same API interface:

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

### Request Format

```json
{
  "input": "string (required)",
  "stream": "boolean (optional, default: false)",
  "options": {
    "temperature": "float (optional)",
    "num_predict": "int (optional)"
  }
}
```

### Response Format

```json
{
  "agent": "string",
  "output": "string",
  "model": "string",
  "timestamp": "string (ISO 8601)",
  "metadata": {}
}
```

## Configuration

### Environment Variables

Key environment variables in `.env`:

```bash
# Ollama
OLLAMA_PORT=11434

# Per-Agent Configuration
<AGENT>_PORT=700X          # Agent API port
<AGENT>_MODEL=llama3.2     # Model to use
<AGENT>_TEMPERATURE=0.7    # Temperature (0.0-1.0)
<AGENT>_MAX_TOKENS=4096    # Max tokens to generate
```

### Temperature Guidelines

- **0.0-0.3**: Technical, deterministic tasks (code, SQL, conversions)
- **0.4-0.7**: Balanced tasks (documentation, explanations)
- **0.8-1.0**: Creative tasks (brainstorming, content generation)

### Model Selection

- **llama3.2**: General purpose, balanced performance
- **codellama**: Code-focused tasks
- **mistral**: Fast, efficient for simpler tasks
- **mixtral**: Complex reasoning, multi-task

## Makefile Commands

### Basic Operations

```bash
# CPU Mode (Default)
make up          # Start all services
make init        # Initialize project (build, start, pull models)
make down        # Stop all services
make restart     # Restart all services
make build       # Build/rebuild services
make rebuild     # Full rebuild (down, build, up)

# GPU Mode (Optional - requires NVIDIA GPU)
make up-gpu      # Start all services with GPU support
make init-gpu    # Initialize project with GPU support
make restart-gpu # Restart all services with GPU
make rebuild-gpu # Full rebuild with GPU
```

### Monitoring

```bash
make status      # Show service status
make health      # Check agent health
make ps          # Show running containers
make logs        # Show all logs
make logs agent=swarm-converter  # Show specific agent logs
```

### Model Management

```bash
make pull-models              # Pull default models
make pull-model model=llama3.2  # Pull specific model
make list-models             # List available models
```

### Agent Operations

```bash
# Run agent with file input
make run agent=swarm-converter file=docker-compose.yml         # Run and show output
make run-full agent=swarm-converter file=docker-compose.yml    # Run and show full JSON
make run-raw agent=swarm-converter file=docker-compose.yml     # Run and show only extracted result
make run-raw-json agent=swarm-converter file=docker-compose.yml # Run and show raw JSON response

# Save output to file (status messages go to stderr, so piping works cleanly)
make run-raw agent=swarm-converter file=docker-compose.yml > swarm-stack.yml

# Test and information
make test-agent agent=swarm-converter    # Test an agent
make agent-info agent=swarm-converter    # Get agent info
make agent-context agent=swarm-converter # View context
make agent-clear-context agent=swarm-converter  # Clear context

# API Documentation
make docs agent=swarm-converter          # Open Swagger UI
make redoc agent=swarm-converter         # Open ReDoc
make openapi agent=swarm-converter       # View OpenAPI schema
```

### Cleanup

```bash
make clean       # Remove all containers and volumes
make prune       # Prune unused Docker resources
```

### Development

```bash
make shell-ollama           # Shell into Ollama container
make shell-agent agent=X    # Shell into agent container
make dev-watch             # Watch all logs
```

## Troubleshooting

### Ollama Not Responding

```bash
# Check Ollama logs
make logs-ollama

# Restart Ollama
docker compose restart ollama

# Verify Ollama is running
curl http://localhost:11434/api/version
```

### Agent Not Starting

```bash
# Check agent logs
make logs agent=swarm-converter

# Verify Ollama is healthy
make health

# Rebuild the agent
docker compose up -d --build agent-swarm-converter
```

### Model Not Found

```bash
# Pull the model manually
make pull-model model=llama3.2

# Or via Ollama directly
docker compose exec ollama ollama pull llama3.2

# List available models
make list-models
```

### Port Conflicts

```bash
# Check what's using the port
sudo lsof -i :7001

# Change port in .env
SWARM_CONVERTER_PORT=7101

# Restart services
make restart
```

### GPU Support

This project supports both **CPU mode** (default) and **GPU mode** (optional).

**CPU Mode** (Default):
```bash
make up          # Start in CPU mode
make init        # Initialize in CPU mode
```

**GPU Mode** (Requires NVIDIA GPU):
```bash
make up-gpu      # Start with GPU support
make init-gpu    # Initialize with GPU support
```

For complete GPU setup instructions, prerequisites, and troubleshooting, see **[GPU-SETUP.md](GPU-SETUP.md)**.

### Out of Memory

- Increase Docker memory limits
- Use smaller models (e.g., mistral instead of llama3.2)
- Reduce MAX_TOKENS in .env
- Reduce concurrent agent count

## Advanced Usage

### Inter-Agent Communication

Agents can communicate via the shared network:

```python
# From within an agent, call another agent
import httpx

async def call_another_agent(input_text: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://agent-swarm-converter:8000/process",
            json={"input": input_text}
        )
        return response.json()
```

### Custom Model Parameters

Override model parameters per request:

```bash
curl -X POST http://localhost:7001/process \
  -H "Content-Type: application/json" \
  -d '{
    "input": "your input",
    "options": {
      "temperature": 0.1,
      "top_k": 20,
      "top_p": 0.8,
      "repeat_penalty": 1.2
    }
  }'
```

### Context Management

The context system stores interactions for continuity:

```bash
# View last 10 interactions
curl "http://localhost:7001/context?limit=10" | jq .

# Clear context to start fresh
curl -X DELETE http://localhost:7001/context
```

### Scaling Agents

To run multiple instances of an agent:

```yaml
  swarm-converter:
    # ... existing config ...
    deploy:
      replicas: 3  # Run 3 instances
```

## CI/CD with GitHub Actions

The project includes automated testing via GitHub Actions that runs on every push and pull request.

### What Gets Tested

The CI/CD workflow (`.github/workflows/test.yml`) automatically:

1. ✅ **Builds** all Docker services
2. ✅ **Starts** Ollama and agents
3. ✅ **Pulls** required models (llama3.2)
4. ✅ **Tests** health endpoints
5. ✅ **Validates** API responses
6. ✅ **Checks** OpenAPI schema
7. ✅ **Verifies** raw endpoints
8. ✅ **Tests** context endpoints

### Test Coverage

```bash
Tests include:
- Health check endpoint (/health)
- Agent info endpoint (/info)
- Process endpoint (/process)
- Raw endpoint (/process/raw)
- OpenAPI schema (/openapi.json)
- Context endpoints (/context)
```

### Running Tests Locally

```bash
# Run the same tests locally
./.github/workflows/test.yml  # Review test steps

# Or run tests manually
make up
make health
make test-agent agent=swarm-converter
```

### Workflow Triggers

Tests run automatically on:
- **Push** to `main` or `develop` branches
- **Pull requests** to `main` or `develop` branches

### Viewing Test Results

Check the **Actions** tab in your GitHub repository to see:
- Test results and logs
- Service health status
- Performance metrics
- Failure details (if any)

## License

This project is provided as-is for educational and development purposes.

## Contributing

To contribute:
1. Create new agents following the template
2. Document your agent's capabilities
3. Include example usage
4. Test thoroughly before deployment

## Support

For issues and questions:
- Check the troubleshooting section
- Review agent logs: `make logs agent=<name>`
- Verify configuration in .env and docker-compose.yml
- Test Ollama directly: `curl http://localhost:11434/api/version`
