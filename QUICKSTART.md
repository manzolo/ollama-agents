# Quick Start Guide

## Initial Setup

```bash
# 1. Initialize the project (first time only)
make init

# This will:
# - Build all containers (agents + backoffice)
# - Start Ollama, agents, and backoffice
# - Pull llama3.2 model
# - Show service status
```

## Access the Backoffice Web UI

The easiest way to use the system:

```bash
# 1. Open your browser
open http://localhost:8080

# The Backoffice provides:
# - Agents tab: View and test all agents
# - Workflows tab: Create and manage workflows
# - Execute tab: Run workflows with custom input
# - History tab: Review past executions
```

## Daily Usage

```bash
# Start services
make up

# Check status
make health

# Access backoffice
open http://localhost:8080

# Or test agents directly
make test-agent agent=swarm-converter

# View logs
make logs agent=swarm-converter

# Stop services
make down
```

## Test the Swarm Converter

### Easy Method (Recommended)

```bash
# Run with any docker-compose.yml file
make run agent=swarm-converter file=docker-compose.yml

# Or show full JSON response with metadata
make run-full agent=swarm-converter file=docker-compose.yml
```

### Manual Method

```bash
# Create a test docker-compose file
cat > test-compose.yml << 'EOF'
version: '3.8'
services:
  web:
    build: .
    ports:
      - "80:80"
    restart: always
    environment:
      - NODE_ENV=production
EOF

# Convert it using the Makefile
make run agent=swarm-converter file=test-compose.yml

# Or use curl directly
curl -X POST http://localhost:7001/process \
  -H "Content-Type: application/json" \
  -d "{\"input\": \"$(cat test-compose.yml | sed 's/"/\\"/g' | tr '\n' ' ')\"}" \
  | jq -r '.output'
```

## Add Your First Custom Agent

```bash
# 1. Create agent directory
mkdir -p agents/my-agent

# 2. Copy templates
cp agents/.agent-template/* agents/my-agent/

# 3. Edit the prompt
nano agents/my-agent/prompt.txt

# 4. Edit the config
nano agents/my-agent/config.yml

# 5. Add to docker-compose.yml (see template in docker-compose.yml)

# 6. Add to .env
echo "MY_AGENT_PORT=7002" >> .env
echo "MY_AGENT_MODEL=llama3.2" >> .env

# 7. Deploy
make rebuild

# 8. Test
make test-agent agent=my-agent
```

## Useful Commands

```bash
make help                                        # Show all commands
make run agent=X file=Y                          # Run agent with file
make status                                      # Service status
make health                                      # Health checks
make docs agent=swarm-converter                  # Open Swagger UI
make openapi agent=swarm-converter               # View OpenAPI schema
make list-models                                 # List available models
make pull-model model=codellama                  # Pull a new model
make logs                                        # All logs
make clean                                       # Clean everything
```

## Swagger UI / API Documentation

Every agent includes interactive API documentation:

```bash
# Open Swagger UI (interactive API docs)
make docs agent=swarm-converter

# Open ReDoc (alternative API docs)
make redoc agent=swarm-converter

# View OpenAPI JSON schema
make openapi agent=swarm-converter

# Or access directly in browser
open http://localhost:7001/docs
```

## API Quick Reference

All agents expose these endpoints on their port:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/info` | GET | Agent details |
| `/process` | POST | Main processing |
| `/context` | GET | View history |
| `/context` | DELETE | Clear history |

## Example API Call

```bash
curl -X POST http://localhost:7001/process \
  -H "Content-Type: application/json" \
  -d '{
    "input": "your input text here",
    "options": {
      "temperature": 0.7
    }
  }' | jq .
```

## Troubleshooting

```bash
# Ollama not responding?
make logs-ollama
docker compose restart ollama

# Agent not working?
make logs agent=swarm-converter
make health

# Model not found?
make pull-model model=llama3.2
make list-models

# Start fresh?
make clean
make init
```

## Create and Run Workflows

The backoffice allows you to chain multiple agents:

```bash
# 1. Access the backoffice
open http://localhost:8080

# 2. Go to Workflows tab

# 3. Click "Run" on the example workflow: convert-and-validate

# 4. Paste a docker-compose.yml content in the input

# 5. Click "Execute Workflow"

# 6. Watch the real-time execution!
```

You can also create workflows via YAML files:

```bash
# Create a workflow file
cat > backoffice/workflows/my-workflow.yml << 'EOF'
name: my-workflow
description: My custom workflow
version: 1.0.0

steps:
  - name: step1
    agent: swarm-converter
    input: original
  - name: step2
    agent: swarm-validator
    input: previous
EOF

# Refresh the Workflows tab - it appears automatically!
```

## Port Map

- `8080` - **Backoffice Web UI** (main interface)
- `11434` - Ollama API
- `7001` - swarm-converter agent
- `7002` - swarm-validator agent
- `7003+` - Your custom agents

## Next Steps

1. **Read** [BACKOFFICE-GUIDE.md](BACKOFFICE-GUIDE.md) for complete workflow documentation
2. **Explore** the backoffice UI at http://localhost:8080
3. **Create** custom workflows for your use cases
4. **Add** your own specialized agents
5. **Read** the full [README.md](README.md) for advanced topics

## Tips

- Use lower temperature (0.1-0.3) for technical tasks
- Use higher temperature (0.7-0.9) for creative tasks
- Check context memory for debugging: `make agent-context agent=X`
- Use `make dev-watch` to monitor all logs in real-time
- GPU recommended but not required
