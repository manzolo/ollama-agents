# Plugin System

The Ollama Agents system uses a **plugin architecture** for dynamic agent discovery and management. This allows agents to be self-describing, easily shared, and hot-pluggable without system restarts.

## Table of Contents

- [Overview](#overview)
- [Plugin Manifest](#plugin-manifest)
- [Creating a Plugin](#creating-a-plugin)
- [Plugin Discovery](#plugin-discovery)
- [API Endpoints](#api-endpoints)
- [Sharing Plugins](#sharing-plugins)

---

## Overview

### What is a Plugin?

A **plugin** is a self-contained agent with a manifest file (`plugin.yml`) that describes:
- **Metadata**: Name, version, author, description
- **Capabilities**: What the agent can do
- **API Contract**: Input/output formats and endpoints
- **Requirements**: Dependencies and models needed
- **Configuration**: Port, model settings, resources

### Benefits

✅ **Self-describing**: Rich metadata included with the agent
✅ **Dynamic discovery**: Auto-detected on startup
✅ **Hot-pluggable**: Add/remove without restarting the system
✅ **Versioned**: Track plugin versions for compatibility
✅ **Easy to share**: Zip folder + manifest = distributable plugin
✅ **Validated**: Manifests are validated before registration

---

## Plugin Manifest

### File Structure

Every plugin must have a `plugin.yml` manifest in its root directory:

```
agents/my-agent/
├── plugin.yml      # Plugin manifest (required)
├── prompt.txt      # System prompt
├── config.yml      # Agent configuration
└── README.md       # Optional documentation
```

### Manifest Schema

```yaml
# ============================================================================
# PLUGIN MANIFEST
# ============================================================================

plugin:
  # Unique identifier (must match agent name - lowercase, hyphenated)
  id: my-agent

  # Human-readable information
  name: "My Agent"
  description: "Brief description of what this agent does"
  version: 1.0.0
  author: "Your Name"

  # Optional metadata
  homepage: https://github.com/yourorg/my-agent
  license: MIT
  tags:
    - category1
    - category2
    - category3

  # Plugin icon (emoji or path to icon file)
  icon: 🤖

# Agent runtime configuration
agent:
  # Network port (must be unique, recommended: 7000-7999)
  port: 7003

  # Model configuration
  model: llama3.2
  temperature: 0.7
  max_tokens: 4096

  # Resource requirements (optional)
  resources:
    memory: "512M"
    cpu: "1.0"

# Capabilities - what this agent can do
capabilities:
  - capability-1
  - capability-2
  - capability-3

# API Contract - how to interact with this plugin
api:
  # Base endpoint for processing requests
  endpoint: /process

  # Input/output types
  input:
    type: text
    format: text|json|yaml|markdown
    description: "What input does this agent expect?"

  output:
    type: text
    format: text|json|yaml|markdown
    description: "What output does this agent produce?"

  # Example usage
  examples:
    - name: "Basic usage"
      description: "Describe what this example does"
      input: |
        Example input here

# Dependencies
requires:
  # Minimum Ollama version
  ollama: ">=0.1.0"

  # Required models (will be pulled if not available)
  models:
    - llama3.2

# Health check configuration
health:
  endpoint: /health
  interval: 30s
  timeout: 10s
  retries: 3
```

### Required Fields

The following fields are **required** in every plugin manifest:

- `plugin.id` - Unique plugin identifier
- `plugin.name` - Display name
- `plugin.description` - Brief description
- `agent.port` - Network port

All other fields are optional but recommended for better discovery and documentation.

---

## Creating a Plugin

### Method 1: Using the Backoffice UI

1. Open the Backoffice at `http://localhost:8080`
2. Click **"Create New Agent"**
3. Fill in the form (name, description, capabilities, etc.)
4. Click **"Create Agent"**

The system will automatically generate:
- `plugin.yml` - Plugin manifest
- `prompt.txt` - System prompt
- `config.yml` - Agent configuration
- Docker compose file

### Method 2: Manual Creation

1. **Create agent directory**:
   ```bash
   mkdir -p runtime/agents/my-agent
   ```

2. **Create plugin.yml**:
   ```bash
   cp agents/.agent-template/plugin.yml runtime/agents/my-agent/
   # Edit the file with your plugin details
   ```

3. **Create prompt.txt**:
   ```bash
   echo "You are a helpful AI agent that..." > runtime/agents/my-agent/prompt.txt
   ```

4. **Create config.yml**:
   ```bash
   cp agents/.agent-template/config.yml runtime/agents/my-agent/
   ```

5. **Deploy the agent**:
   ```bash
   # Via backoffice API or manually with docker compose
   ```

### Method 3: From Template

Use the provided template:

```bash
cp -r agents/.agent-template runtime/agents/my-new-agent
cd runtime/agents/my-new-agent
# Edit plugin.yml, prompt.txt, and config.yml
```

---

## Plugin Discovery

### Automatic Discovery

The system automatically discovers plugins from:

1. **Filesystem** (`examples/agents/` and `runtime/agents/`)
2. **Running Docker containers** (containers named `agent-*`)

Discovery happens:
- On system startup
- When calling `POST /api/plugins/discover`

### Discovery Process

```
1. Scan directories for plugin.yml files
2. Validate each manifest
3. Register valid plugins in the registry
4. Initialize orchestrator with discovered agents
```

### Checking Discovered Plugins

**View startup logs**:
```bash
docker logs backoffice | grep "Discovering plugins"
```

**Query API**:
```bash
curl http://localhost:8080/api/plugins
```

**Use Makefile**:
```bash
make list-agents
```

---

## API Endpoints

### List All Plugins

**GET** `/api/plugins`

Returns all registered plugins with their manifests.

```bash
curl http://localhost:8080/api/plugins
```

**Response**:
```json
{
  "count": 2,
  "plugins": [
    {
      "id": "swarm-converter",
      "name": "Docker Swarm Converter",
      "version": "1.0.0",
      "capabilities": ["..."],
      "api": {"..."},
      "...": "..."
    }
  ]
}
```

### Get Plugin Details

**GET** `/api/plugins/{plugin_id}`

Get detailed information about a specific plugin.

```bash
curl http://localhost:8080/api/plugins/swarm-converter
```

### Validate Plugin Manifest

**POST** `/api/plugins/{plugin_id}/validate`

Validate a plugin's manifest file.

```bash
curl -X POST http://localhost:8080/api/plugins/swarm-converter/validate
```

**Response**:
```json
{
  "status": "valid",
  "plugin_id": "swarm-converter",
  "manifest": {"..."}
}
```

Or if invalid:
```json
{
  "status": "invalid",
  "plugin_id": "my-agent",
  "errors": [
    "Missing required field: plugin.id",
    "Port must be between 1024-65535: 80"
  ]
}
```

### Re-discover Plugins

**POST** `/api/plugins/discover`

Trigger plugin re-discovery (scans filesystem and Docker).

```bash
curl -X POST http://localhost:8080/api/plugins/discover
```

**Response**:
```json
{
  "status": "success",
  "plugins_discovered": 3,
  "plugins": ["swarm-converter", "swarm-validator", "my-agent"]
}
```

---

## Sharing Plugins

### Packaging a Plugin

1. **Create a ZIP file** of the agent directory:
   ```bash
   cd runtime/agents
   zip -r my-agent.zip my-agent/
   ```

2. **Share the ZIP file**:
   - Upload to GitHub releases
   - Share via file hosting
   - Distribute internally

### Installing a Shared Plugin

1. **Download and extract**:
   ```bash
   cd runtime/agents
   unzip my-agent.zip
   ```

2. **Validate the manifest**:
   ```bash
   curl -X POST http://localhost:8080/api/plugins/my-agent/validate
   ```

3. **Deploy the agent**:
   - Use the Backoffice UI to create the agent
   - Or manually deploy with docker compose

4. **Re-discover plugins**:
   ```bash
   curl -X POST http://localhost:8080/api/plugins/discover
   ```

### Plugin Repository (Future)

In the future, we plan to add:
- Central plugin marketplace
- `make plugin-install name=my-agent`
- Automatic updates
- Version management
- Community ratings and reviews

---

## Best Practices

### 1. Unique Plugin IDs
- Use lowercase with hyphens: `my-agent`
- Avoid conflicts with existing plugins
- Keep it short but descriptive

### 2. Semantic Versioning
- Use `MAJOR.MINOR.PATCH` format
- Increment MAJOR for breaking changes
- Increment MINOR for new features
- Increment PATCH for bug fixes

### 3. Clear Descriptions
- Write clear, concise descriptions
- Explain what the agent does and when to use it
- Include examples in the manifest

### 4. Port Management
- Use ports in the 7000-7999 range
- Ensure ports are unique across agents
- Document the port in README

### 5. Capabilities
- List specific capabilities, not general ones
- Use descriptive capability names
- Keep the list focused (3-5 capabilities)

### 6. Documentation
- Include a README.md with usage examples
- Document input/output formats clearly
- Provide troubleshooting tips

---

## Troubleshooting

### Plugin Not Discovered

**Problem**: Plugin doesn't appear after creation

**Solutions**:
1. Check manifest exists: `ls runtime/agents/my-agent/plugin.yml`
2. Validate manifest: `curl -X POST http://localhost:8080/api/plugins/my-agent/validate`
3. Re-discover: `curl -X POST http://localhost:8080/api/plugins/discover`
4. Check logs: `docker logs backoffice | grep "Discovering plugins"`

### Invalid Manifest

**Problem**: Validation fails

**Solutions**:
1. Check required fields are present
2. Ensure plugin ID is lowercase with hyphens
3. Verify port is in valid range (1024-65535)
4. Validate YAML syntax (use a YAML validator)

### Agent Not Starting

**Problem**: Agent container fails to start

**Solutions**:
1. Check agent logs: `docker logs agent-my-agent`
2. Verify port is not in use: `docker port agent-my-agent`
3. Check model exists: `docker exec ollama ollama list`
4. Review resource limits in plugin.yml

---

## Examples

See the `examples/agents/` directory for reference implementations:

- **swarm-converter**: Docker Compose to Swarm converter
- **swarm-validator**: Swarm stack validator

Each example includes a complete `plugin.yml` with all fields populated.

---

## Related Documentation

- [Agent Documentation](AGENTS.md) - Creating and configuring agents
- [API Reference](API_REFERENCE.md) - Complete API documentation
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions
