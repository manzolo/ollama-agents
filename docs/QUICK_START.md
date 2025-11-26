# Quick Start Guide

Get up and running with Ollama Agents in minutes.

## Prerequisites

- Docker and Docker Compose
- At least 8GB RAM (16GB+ recommended)
- (Optional) NVIDIA GPU with Docker GPU support - see [GPU-SETUP.md](../GPU-SETUP.md)

## Installation

### Option 1: Interactive Wizard (Recommended)

```bash
# Run the setup wizard (guides you step-by-step)
make wizard
```

The wizard will guide you through CPU/GPU selection, initialization, and next steps.

### Option 2: Manual Setup

**CPU Mode (Default):**
```bash
# Initialize in CPU mode (works everywhere)
make init
```

**GPU Mode (Requires NVIDIA GPU):**
```bash
# Initialize with GPU support
make init-gpu
```

This will:
- Build all containers (agents + backoffice)
- Start Ollama, agents, and the backoffice
- Pull the required models (llama3.2)
- Display service status

## First Steps

### 1. Access the Backoffice Web UI

Open your browser to:
```
http://localhost:8080
```

The Backoffice provides:
- **Agents Tab** - View all available agents and their status
- **Workflows Tab** - Create and manage multi-agent workflows
- **Execute Tab** - Run workflows with custom input
- **History Tab** - Review past workflow executions

### 2. Test an Agent

You can call agents directly via their APIs:

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

### 3. Create Your First Workflow

1. **Access the UI**: http://localhost:8080
2. **Go to Workflows Tab**
3. **Click Create** and use this example:
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
4. **Execute the Workflow** with your docker-compose file
5. **View Results** in real-time

### 4. Monitor Services

```bash
# View status
make status

# Check health
make health

# View logs
make logs
```

## Next Steps

- [Learn about Agents](AGENTS.md)
- [Create Workflows](WORKFLOWS.md)
- [Explore the API](API_REFERENCE.md)
- [Troubleshooting](TROUBLESHOOTING.md)
