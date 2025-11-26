# Troubleshooting Guide

Common issues and solutions for Ollama Agents.

## Ollama Issues

### Ollama Not Responding

**Symptoms:**
- Agents fail to start
- "Connection refused" errors
- Health checks fail

**Solutions:**

```bash
# Check Ollama logs
make logs-ollama

# Restart Ollama
docker compose restart ollama

# Verify Ollama is running
curl http://localhost:11434/api/version

# Check if port 11434 is available
sudo lsof -i :11434
```

### Model Not Found

**Symptoms:**
- "model not found" errors
- Agents start but fail on requests

**Solutions:**

```bash
# Pull the model manually
make pull-model model=llama3.2

# Or via Ollama directly
docker compose exec ollama ollama pull llama3.2

# List available models
make list-models

# Check model is loaded
docker compose exec ollama ollama list
```

### Using External Ollama Host

You can configure the system to use an external Ollama instance instead of the built-in Docker service.

**Configuration:**

Edit `.env` and set `OLLAMA_HOST`:

```bash
# Use Ollama running on host machine
OLLAMA_HOST=http://host.docker.internal:11434

# Use external Ollama server
OLLAMA_HOST=http://192.168.1.100:11434

# Use remote Ollama API
OLLAMA_HOST=https://your-ollama-api.com
```

**Restart services to apply:**

```bash
make restart
```

**Verify connection:**

```bash
# Test from backoffice container
docker compose exec backoffice curl -s ${OLLAMA_HOST}/api/version

# Check agent logs to verify they're connecting
make logs agent=swarm-converter
```

**Notes:**
- When using external Ollama, ensure the host is accessible from Docker containers
- You can disable/remove the local `ollama` service from `docker-compose.yml` if not needed
- All agents will automatically use the configured `OLLAMA_HOST`

## Agent Issues

### Agent Not Starting

**Symptoms:**
- Agent container exits immediately
- Agent not responding on its port

**Solutions:**

```bash
# Check agent logs
make logs agent=swarm-converter

# Verify Ollama is healthy
make health

# Rebuild the agent
docker compose up -d --build agent-swarm-converter

# Check if prompt.txt and config.yml exist
ls -la agents/swarm-converter/
```

### Agent Returns Errors

**Symptoms:**
- 500 Internal Server Error
- Timeout errors
- Empty responses

**Solutions:**

```bash
# Check agent logs for details
make logs agent=swarm-converter

# Verify model parameters
curl http://localhost:7001/info | jq .

# Try with lower temperature
curl -X POST http://localhost:7001/process \
  -H "Content-Type: application/json" \
  -d '{"input": "test", "options": {"temperature": 0.1}}'

# Check context size
curl http://localhost:7001/context | jq 'length'

# Clear context if too large
curl -X DELETE http://localhost:7001/context
```

## Resource Issues

### Out of Memory

**Symptoms:**
- Containers being killed (OOM)
- System becomes unresponsive
- Slow responses

**Solutions:**

1. **Increase Docker memory limits:**
   - Docker Desktop: Settings → Resources → Memory
   - Recommended: 8GB minimum, 16GB+ for production

2. **Use smaller models:**
   ```bash
   # Edit .env
   SWARM_CONVERTER_MODEL=mistral  # Instead of llama3.2
   ```

3. **Reduce MAX_TOKENS:**
   ```bash
   # Edit .env
   SWARM_CONVERTER_MAX_TOKENS=2048  # Instead of 8192
   ```

4. **Reduce concurrent agents:**
   ```bash
   # Stop unused agents
   docker compose stop agent-unused-agent
   ```

### Disk Space Issues

**Symptoms:**
- "no space left on device"
- Failed to pull models

**Solutions:**

```bash
# Clean up Docker resources
make clean
make prune

# Remove unused images
docker image prune -a

# Check disk usage
docker system df

# Remove specific models
docker compose exec ollama ollama rm old-model-name
```

## Network Issues

### Port Conflicts

**Symptoms:**
- "port is already allocated"
- Cannot bind to address

**Solutions:**

```bash
# Check what's using the port
sudo lsof -i :7001

# Change port in .env
SWARM_CONVERTER_PORT=7101

# Restart services
make restart
```

### Agents Cannot Communicate

**Symptoms:**
- Inter-agent calls fail
- "connection refused" between agents

**Solutions:**

```bash
# Verify all agents are on the same network
docker network inspect ollama-agents_agent-network

# Check if agents can ping each other
docker compose exec agent-swarm-converter ping agent-swarm-validator

# Restart network
make down
make up
```

## GPU Issues

### GPU Not Detected

**Symptoms:**
- Ollama using CPU instead of GPU
- Slow performance with GPU mode

**Solutions:**

See [GPU-SETUP.md](GPU-SETUP.md) for complete GPU troubleshooting.

```bash
# Verify GPU is available
nvidia-smi

# Check Docker can access GPU
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# Restart with GPU mode
make down
make up-gpu
```

## Backoffice Issues

### Backoffice Not Loading

**Symptoms:**
- Cannot access http://localhost:8080
- 404 errors

**Solutions:**

```bash
# Check backoffice logs
docker compose logs backoffice

# Restart backoffice
docker compose restart backoffice

# Rebuild if needed
docker compose up -d --build backoffice

# Check port 8080 availability
sudo lsof -i :8080
```

### Workflows Not Executing

**Symptoms:**
- Workflow stays in "running" state
- Execution fails immediately

**Solutions:**

```bash
# Check backoffice logs
docker compose logs backoffice

# Verify all referenced agents exist
curl http://localhost:8080/api/agents | jq .

# Test agents individually first
make test-agent agent=swarm-converter

# Check workflow syntax
cat backoffice/workflows/your-workflow.yml
```

## General Debugging

### Check All Services

```bash
# View service status
make status

# Check all health endpoints
make health

# View all logs
make logs

# View specific service logs
make logs agent=swarm-converter
docker compose logs backoffice
docker compose logs ollama
```

### Reset Everything

If all else fails, perform a complete reset:

```bash
# Stop and remove everything
make clean

# Remove all Docker resources
make prune

# Start fresh
make init

# Or with GPU
make init-gpu
```

### Enable Debug Logging

Edit `agents/base/app.py` to enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Then rebuild:
```bash
make rebuild
```

## Getting Help

If you're still experiencing issues:

1. **Check logs** - Most issues are visible in logs
2. **Test components individually** - Isolate the problem
3. **Verify configuration** - Check .env and docker-compose.yml
4. **Review documentation** - Check all docs for relevant info
5. **Create an issue** - Include logs and configuration details
