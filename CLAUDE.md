# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ollama Agents is a modular Docker-based architecture for deploying multiple specialized AI agents powered by Ollama, with a **Backoffice Web UI** for managing multi-agent workflows. The system uses a **plugin architecture** for dynamic agent discovery and hot-pluggable agent management.

## Key Architecture Concepts

### Plugin-Based Architecture

The system uses a dual-directory pattern for separating git-tracked examples from user-created content:

- **`examples/`** - Git-tracked, read-only templates (agents, workflows, compose files)
- **`runtime/`** - Gitignored, user-created content (agents, workflows, compose files)

When loading resources, **runtime takes priority over examples** (user overrides). Example items cannot be deleted from the UI or API.

### Core Backend Components

Located in `backoffice/backend/`:

- **`plugin_manager.py`** - `PluginRegistry` discovers agents from filesystem (`examples/agents/`, `runtime/agents/`) and Docker containers. Each plugin tracks its `source` (`example`, `runtime`, or `docker`)
- **`deployment_manager.py`** - `DeploymentManager` handles agent creation, Docker compose file generation, and container deployment. Uses `HOST_PROJECT_ROOT` for absolute volume paths
- **`orchestrator.py`** - `WorkflowOrchestrator` executes multi-step workflows, `WorkflowManager` handles workflow storage (runtime + examples directories)
- **`agent_manager.py`** - `AgentManager` manages agent definitions before deployment
- **`app.py`** - FastAPI backend, ties all managers together, provides REST API

### Agent Structure

Each agent requires three files:
```
agents/my-agent/
├── plugin.yml    # Manifest (metadata, capabilities, API contract)
├── prompt.txt    # System prompt
└── config.yml    # Agent configuration (model, temperature, etc.)
```

Agents run as Docker containers with pattern `agent-{name}` on internal network, exposed via compose files in `examples/compose/` or `runtime/compose/`.

### Workflow System

Workflows support sequential multi-agent processing with three input types:
- `original` - Use workflow's initial input
- `previous` - Use previous step's output
- `custom` - Static custom input for the step

Workflows stored in `examples/workflows/` (templates) or `runtime/workflows/` (user-created).

## Common Commands

### Development & Testing

```bash
# Start system (CPU mode)
make up

# Start with GPU support
make up-gpu

# Full initialization (build + start + pull models)
make init          # CPU
make init-gpu      # GPU

# Health checks
make health        # All services
make status        # Service status
make test-agent agent=NAME  # Test specific agent

# View logs
make logs agent=NAME        # Specific agent
make logs agent=NAME follow=true  # Follow mode
make logs-ollama           # Ollama logs
make logs-backoffice       # Backoffice logs

# Agent management
make list-agents           # List running agents
make shell-agent agent=NAME  # Enter agent shell
make docs agent=NAME       # Open agent Swagger UI

# Restart services
make restart              # All services
docker restart backoffice # Just backoffice (for frontend changes)
```

### Frontend Cache Busting

When modifying CSS/JS files:
```bash
make update-version   # Updates version to current git hash
# Automatically updates: styles.css?v=abc1234 and app.js?v=abc1234
```

### Plugin Discovery

```bash
# Trigger plugin re-discovery without restart
curl -X POST http://localhost:8080/api/plugins/discover
```

## Project Structure

```
.
├── agents/base/           # Base Docker image for all agents
├── backoffice/
│   ├── backend/          # Python FastAPI backend
│   │   ├── app.py                  # Main API server
│   │   ├── plugin_manager.py      # Plugin discovery & registry
│   │   ├── deployment_manager.py  # Docker deployment
│   │   ├── orchestrator.py        # Workflow execution
│   │   └── agent_manager.py       # Agent definition management
│   ├── frontend/         # Vanilla JS frontend
│   │   ├── index.html
│   │   ├── app.js
│   │   └── styles.css
│   └── update-version.sh # Git hash-based cache busting
├── examples/             # Git-tracked templates (READ-ONLY)
│   ├── agents/          # Example agent plugins
│   ├── compose/         # Example compose files
│   └── workflows/       # Example workflow templates
├── runtime/             # Gitignored user content (READ-WRITE)
│   ├── agents/          # User-created agents
│   ├── compose/         # User-created compose files
│   └── workflows/       # User-created workflows
├── shared/context/      # Agent context memory (per-agent dirs)
└── docs/               # Documentation
```

## Important File Patterns

### Docker Compose Override Pattern

Agent compose files use environment variable defaults:
```yaml
ports:
  - "${AGENT_PORT:-7001}:8000"
environment:
  - MODEL_NAME=${AGENT_MODEL:-llama3.2}
```

No `.env.agents` file needed - defaults are in the compose files themselves.

### Volume Mounts

**Critical**: Use `HOST_PROJECT_ROOT` environment variable for volume mounts when running docker-compose via Docker socket:
```python
host_agent_dir = self.host_project_root / "runtime" / "agents" / agent_name
```

This prevents "IsADirectoryError" when Docker mounts files before they're fully written.

**Auto-Detection**: The system automatically detects `HOST_PROJECT_ROOT` through:
1. `make init-env` command (recommended during setup)
2. Automatic configuration during `make init`, `make init-gpu`, or `make wizard`
3. Runtime auto-detection by inspecting the backoffice container's mounts (fallback)

### Plugin Manifest Validation

All plugins must pass `PluginValidator.validate()` checks:
- Required fields: `plugin.id`, `plugin.name`, `plugin.description`, `agent.port`
- Port must be valid integer
- ID must match directory name (lowercase, hyphenated)

## Development Workflow

### Creating a New Agent

1. Use Backoffice UI (http://localhost:8080) or manually create:
```bash
mkdir -p runtime/agents/my-agent
# Add plugin.yml, prompt.txt, config.yml
```

2. Agent automatically discovered on next startup or via `/api/plugins/discover`

3. Compose file auto-generated in `runtime/compose/my-agent.yml`

4. Container deployed with name `agent-my-agent`

### Modifying Frontend

1. Edit files in `backoffice/frontend/`
2. Run `make update-version` to update cache-busting hash
3. Restart: `docker restart backoffice`
4. Hard refresh browser (Ctrl+Shift+R) if needed

### Backend Changes

Backend uses live reload in development mode (uncomment volumes in docker-compose.yml):
```yaml
volumes:
  - ./backoffice/backend:/app:ro
```

Otherwise: `docker restart backoffice`

## Key Behaviors

### Agent Discovery Priority
1. Filesystem (`examples/` then `runtime/`) via `PluginRegistry.discover_from_filesystem()`
2. Docker containers via `PluginRegistry.discover_from_docker()`
3. Runtime agents override example agents with same name

### Workflow Execution
- Sequential processing (no parallel steps)
- Each step gets input based on configuration
- Results stored in execution history
- Streaming support for real-time output

### File Creation Timing
When creating agents via API, the system:
1. Creates all files (plugin.yml, prompt.txt, config.yml)
2. Calls `fsync()` to force disk write
3. Waits 2 seconds for filesystem sync
4. Verifies files exist before Docker deployment
5. Uses `--force-recreate` to avoid mount issues

This prevents Docker from creating directories instead of mounting files.

## Testing

### Health Checks
```bash
# All services
curl http://localhost:8080/api/health

# Specific agent
curl http://localhost:7001/health

# Via Makefile
make test-agent agent=swarm-converter
```

### Workflow Execution
```bash
curl -X POST http://localhost:8080/api/workflows/convert-and-validate/execute \
  -H "Content-Type: application/json" \
  -d '{
    "input": "version: '\''3.8'\''\nservices:\n  web:\n    image: nginx"
  }'
```

## Environment Variables

The project uses `.env.example` as a template (git-tracked) and `.env` for local configuration (gitignored).

**First-time setup:**
- Run `make init`, `make wizard`, or `make init-env` - this creates `.env` from `.env.example` and auto-configures all values

Key variables in `.env`:
- `HOST_PROJECT_ROOT` - Absolute host path (required for Docker socket operations)
  - **Auto-configured**: Automatically detected and set when you run `make init-env`
  - Also set by `make init`, `make init-gpu`, or `make wizard`
  - Runtime fallback: Auto-detected by inspecting backoffice container mounts
  - **Never commit this value to git** - `.env` is gitignored for this reason
- `OLLAMA_HOST` - Ollama service URL (default: `http://ollama:11434`)
- `OLLAMA_PORT` - Ollama external port (default: `11434`)
- `BACKOFFICE_PORT` - Backoffice UI port (default: `8080`)

## Troubleshooting

### Agent Won't Start
- Check `docker logs agent-NAME`
- Verify files exist: `ls runtime/agents/NAME/`
- Check plugin.yml validation: `curl http://localhost:8080/api/plugins/NAME`

### Frontend Not Updating
- Run `make update-version`
- Restart backoffice
- Clear browser cache (Ctrl+Shift+R)

### "IsADirectoryError" on Agent Creation
- Run `make init-env` to auto-detect and configure `HOST_PROJECT_ROOT`
- Check absolute paths in generated compose files
- Verify: `grep HOST_PROJECT_ROOT .env` shows correct path

### Plugin Not Discovered
- Verify `plugin.yml` exists and is valid YAML
- Check logs: `docker logs backoffice`
- Manually trigger discovery: `POST /api/plugins/discover`

## API Endpoints

Key endpoints (full docs at http://localhost:8080/docs):

- `GET /api/agents` - List all discovered agents (with source field)
- `GET /api/plugins` - List all plugins with manifests
- `POST /api/plugins/discover` - Trigger plugin re-discovery
- `GET /api/workflows` - List workflows (runtime + examples)
- `GET /api/workflows/{name}` - Get single workflow details
- `POST /api/workflows` - Create workflow (saved to runtime/)
- `PUT /api/workflows/{name}` - Update workflow (runtime only)
- `DELETE /api/workflows/{name}` - Delete workflow (runtime only, examples protected)
- `POST /api/workflows/{name}/execute` - Execute specific workflow
- `POST /api/agents/create` - Create and deploy agent

## Visual Workflow Builder

The frontend includes a drag-and-drop workflow builder:
- Add agents to workflow steps
- Reorder steps via drag-and-drop or arrow buttons
- Configure input sources per step (original/previous/custom)
- Edit step names inline
- Visual badges for example (read-only) vs runtime workflows

Delete buttons are automatically disabled for example workflows and agents (source === 'examples' or 'example').
