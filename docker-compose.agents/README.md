# Agent Compose Files Directory

This directory contains individual Docker Compose files for each runtime-created agent. These files are generated automatically by the backoffice when you create a new agent through the web UI.

## Architecture

**Key Principles:**
- Each agent has its own standalone compose file: `{agent-name}.yml`
- Files are Git-ignored (runtime-generated, not version-controlled)
- Agents can be created and deleted at runtime without modifying `docker-compose.yml`
- Docker Compose automatically merges multiple `-f` files

## File Structure

Each agent compose file follows this pattern:

```yaml
# ==========================================================================
# AGENT: AGENT-NAME
# ==========================================================================
# Agent description
# Endpoint: http://localhost:PORT/process
# Auto-generated - do not edit manually
# ==========================================================================

services:
  agent-name:
    build:
      context: ./agents/base
      dockerfile: Dockerfile
    container_name: agent-{name}
    restart: unless-stopped
    ports:
      - "${AGENT_PORT:-7001}:8000"
    volumes:
      - ./agents/{name}/prompt.txt:/app/prompt.txt:ro
      - ./agents/{name}/config.yml:/app/config.yml:ro
      - ./shared/context/{name}:/app/context
    networks:
      - agent-network
    environment:
      - AGENT_NAME={name}
      - OLLAMA_HOST=http://ollama:11434
      - MODEL_NAME=${AGENT_MODEL:-llama3.2}
      - TEMPERATURE=${AGENT_TEMPERATURE:-0.7}
      - MAX_TOKENS=${AGENT_MAX_TOKENS:-4096}
    depends_on:
      ollama:
        condition: service_healthy
    healthcheck:
      test: [ "CMD", "curl", "-f", "http://localhost:8000/health" ]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s

networks:
  agent-network:
    external: true
    name: ollama-agent-network
```

## Lifecycle Management

### Creating an Agent

When you create an agent through the backoffice UI:

1. **Agent Definition Created**: `backoffice/agent-definitions/{name}.yml`
2. **Agent Files Created**: `agents/{name}/` directory with `prompt.txt` and `config.yml`
3. **Compose File Generated**: `docker-compose.agents/{name}.yml` (this file)
4. **Environment Variables Added**: `.env` file updated with agent-specific vars
5. **Container Deployed**: `docker compose -f docker-compose.yml -f docker-compose.agents/{name}.yml up -d {name}`

### Starting/Stopping Agents

- **Start**: `docker compose -f docker-compose.yml -f docker-compose.agents/{name}.yml up -d {name}`
- **Stop**: `docker compose -f docker-compose.yml -f docker-compose.agents/{name}.yml stop {name}`
- **Restart**: `docker compose -f docker-compose.yml -f docker-compose.agents/{name}.yml restart {name}`

### Deleting an Agent

When you delete an agent:

1. **Container Stopped & Removed**: Docker container is stopped and removed
2. **Compose File Deleted**: This file (`{name}.yml`) is removed
3. **Environment Variables Removed**: Agent section removed from `.env`
4. **Agent Files Deleted** (optional): `agents/{name}/` directory deleted

## Manual Management

You can also manage agents manually:

### List all agent compose files
```bash
ls -la docker-compose.agents/
```

### Deploy a specific agent
```bash
docker compose -f docker-compose.yml -f docker-compose.agents/my-agent.yml up -d my-agent
```

### Deploy all agents
```bash
# Combine all agent compose files
docker compose -f docker-compose.yml -f docker-compose.agents/*.yml up -d
```

### Remove an agent manually
```bash
# Stop and remove container
docker compose -f docker-compose.yml -f docker-compose.agents/my-agent.yml down my-agent

# Delete the compose file
rm docker-compose.agents/my-agent.yml

# Clean up agent files (optional)
rm -rf agents/my-agent
rm -rf shared/context/my-agent
```

## Benefits of This Architecture

✅ **Git-Friendly**: Agent compose files are not tracked in version control
✅ **Modular**: Each agent is completely independent
✅ **No Conflicts**: No need to modify `docker-compose.yml` for new agents
✅ **Easy Cleanup**: Deleting an agent is just removing one file
✅ **Discoverable**: Agents are automatically discovered by scanning Docker containers
✅ **Robust**: Agents can be created/deleted at runtime without affecting other agents

## Migration from Old System

If you have agents defined in `docker-compose.yml`, they will continue to work. To migrate them to the new system:

1. Create an agent definition in `backoffice/agent-definitions/{name}.yml`
2. Use the backoffice UI to "deploy" the agent (it will create the compose file)
3. Remove the agent from `docker-compose.yml`
4. Restart with the new compose file

## Troubleshooting

**Agent not appearing in UI?**
- Check if the compose file exists in this directory
- Verify the container name starts with `agent-`
- Check Docker container status: `docker ps -a --filter "name=agent-"`

**Deployment failed?**
- Check agent definition YAML syntax
- Verify port is not already in use
- Check Docker logs: `docker logs agent-{name}`

**Container won't start?**
- Verify `agents/{name}/prompt.txt` exists
- Check `agents/{name}/config.yml` syntax
- Ensure Ollama service is healthy: `docker compose ps ollama`
