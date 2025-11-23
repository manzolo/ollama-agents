# Quick Start Guide

## Initial Setup

```bash
# 1. Initialize the project (first time only)
make init

# This will:
# - Build all containers
# - Start Ollama + swarm-converter agent
# - Pull llama3.2 model
# - Show service status
```

## Daily Usage

```bash
# Start services
make up

# Check status
make health

# Test the swarm-converter agent
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

## Port Map

- `11434` - Ollama API
- `7001` - swarm-converter agent
- `7002+` - Your custom agents

## Next Steps

1. Read the full [README.md](README.md)
2. Customize the swarm-converter prompt
3. Add your own specialized agents
4. Explore inter-agent communication
5. Set up production deployment

## Tips

- Use lower temperature (0.1-0.3) for technical tasks
- Use higher temperature (0.7-0.9) for creative tasks
- Check context memory for debugging: `make agent-context agent=X`
- Use `make dev-watch` to monitor all logs in real-time
- GPU recommended but not required
