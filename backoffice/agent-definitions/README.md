# Agent Definitions Directory

This directory stores **declarative agent definitions** created through the Backoffice Web UI.

## How It Works

### 1. **Separation of Concerns**
- **Definition**: Agent specifications stored as YAML files (this directory)
- **Deployment**: Actual agent deployment handled separately

### 2. **Modular Architecture Benefits**
✅ **No Direct Filesystem Access**: Backoffice only writes to its own data directory
✅ **Version Control Friendly**: Agent definitions are simple YAML files
✅ **Portable**: Copy definitions between environments
✅ **Auditable**: Track who created what and when
✅ **Safe**: Failed deployments don't affect definitions

### 3. **Workflow**

#### Creating an Agent:
1. Use the Web UI: http://localhost:8080 → Agents → Create Agent
2. Fill in the form (name, description, model, prompt, etc.)
3. Agent definition is saved to this directory as `<agent-name>.yml`
4. Download the auto-generated deployment script

#### Deploying an Agent:
Option A: **Via Deploy Script**
```bash
# Download script from Web UI or API
curl http://localhost:8080/api/agents/<agent-name>/deploy-script > deploy-agent.sh
bash deploy-agent.sh
docker compose up -d --build <agent-name>
```

Option B: **Manual Deployment**
1. Read the agent definition YAML file
2. Create the agent directory structure
3. Copy prompt and config
4. Add service to docker-compose.yml
5. Update .env with environment variables

Option C: **CLI Tool** (future)
```bash
./deploy-agent.sh <agent-name>
```

## Agent Definition Format

Each agent definition is a YAML file with this structure:

```yaml
agent:
  name: my-agent
  description: What this agent does
  version: 1.0.0

deployment:
  port: 7003
  model: llama3.2
  temperature: 0.7
  max_tokens: 4096

capabilities:
  - capability-1
  - capability-2

system_prompt: |
  You are a specialized AI agent...
  [Full system prompt here]
```

## API Endpoints

- `POST /api/agents/create` - Create a new agent definition
- `GET /api/agents/definitions` - List all definitions
- `GET /api/agents/{name}/deploy-script` - Download deploy script
- `DELETE /api/agents/definitions/{name}` - Delete a definition

## Security

This approach is more secure because:
- Backoffice container has no access to host filesystem
- No direct modification of docker-compose.yml or .env
- Deployment is an explicit, auditable step
- Failed deployments don't corrupt the system

## Example Usage

### Create Agent via Web UI
1. Open http://localhost:8080
2. Click "Create Agent"
3. Fill form and submit
4. Download deploy script

### Deploy the Agent
```bash
# From project root
cd /path/to/ollama-agents

# Download and run deploy script
curl http://localhost:8080/api/agents/my-agent/deploy-script | bash

# Start the agent
docker compose up -d --build my-agent

# Test it
curl http://localhost:7003/health
```

## Benefits Over Previous Approach

### Before (Direct Mount):
```yaml
volumes:
  - ./agents:/app/../agents              # ❌ Direct filesystem access
  - ./docker-compose.yml:/app/../docker-compose.yml  # ❌ Dangerous
  - ./.env:/app/../.env                   # ❌ Security risk
```

### After (Modular):
```yaml
volumes:
  - ./backoffice/agent-definitions:/app/agent-definitions  # ✅ Isolated
```

## Future Enhancements

- [ ] Auto-deployment option (with Docker socket)
- [ ] Git integration for version control
- [ ] Agent templates library
- [ ] Bulk deployment CLI tool
- [ ] Agent validation before deployment
