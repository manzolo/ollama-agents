# Getting Started with Ollama Agents

Complete guide to installing, configuring, and using Ollama Agents.

## Prerequisites

Before you begin, ensure you have:

- **Docker** and **Docker Compose** installed
  - Docker version 20.10 or higher
  - Docker Compose version 2.0 or higher
- **Make** - Build automation tool (usually pre-installed on Linux/macOS)
  - Linux: `sudo apt install make` or `sudo yum install make`
  - macOS: Included with Xcode Command Line Tools
  - Windows: Use WSL2 or install via chocolatey
- **jq** - JSON processor for command-line operations
  - Linux: `sudo apt install jq` or `sudo yum install jq`
  - macOS: `brew install jq`
  - Windows: Use WSL2 or download from https://stedolan.github.io/jq/
- **System Requirements**:
  - At least 8GB RAM (16GB+ recommended for multiple agents)
  - 10GB free disk space (for models and containers)
  - Linux, macOS, or Windows with WSL2
- **Optional**: NVIDIA GPU with Docker GPU support
  - See [GPU Setup Guide](GPU-SETUP.md) for configuration

## Installation

### Option 1: Interactive Wizard (Recommended)

The easiest way to get started:

```bash
# Clone the repository
git clone https://github.com/manzolo/ollama-agents.git
cd ollama-agents

# Run the interactive setup wizard
make wizard
```

The wizard will:
- Guide you through CPU/GPU mode selection
- Initialize the project automatically
- Pull required models
- Start all services
- Show you next steps

### Option 2: Manual Setup

For more control over the installation:

**CPU Mode (Works Everywhere):**

```bash
# Initialize in CPU mode
make init

# This will:
# - Build all Docker containers
# - Start Ollama, agents, and backoffice
# - Pull the llama3.2 model
# - Display service status
```

**GPU Mode (NVIDIA GPU Required):**

```bash
# Initialize with GPU support
make init-gpu

# Requires:
# - NVIDIA GPU with CUDA support
# - nvidia-docker2 installed
# - See GPU-SETUP.md for details
```

## First Steps

### 1. Verify Installation

Check that all services are running:

```bash
# View service status
make status

# Check health of all agents
make health

# Expected output:
# ✓ ollama: healthy
# ✓ swarm-converter: healthy
# ✓ swarm-validator: healthy
# ✓ backoffice: healthy
```

### 2. Access the Backoffice Web UI

Open your browser to:
```
http://localhost:8080
```

The Backoffice provides:
- **Agents Tab** - View and test all available agents
- **Workflows Tab** - Create and manage multi-agent workflows
- **Execute Tab** - Run workflows with custom input
- **History Tab** - Review past workflow executions

### 3. Test Your First Agent

Test the swarm-converter agent:

```bash
# Quick health check
make test-agent agent=swarm-converter

# Run with a sample file
make run agent=swarm-converter file=docker-compose.yml

# Or use curl directly
curl -X POST http://localhost:7001/process \
  -H "Content-Type: application/json" \
  -d '{"input": "version: \"3.8\"\nservices:\n  web:\n    image: nginx"}' \
  | jq .
```

### 4. Execute Your First Workflow

Using the Web UI:

1. Go to http://localhost:8080
2. Click on **Execute** tab
3. Select "convert-and-validate" workflow
4. Paste a docker-compose file:
   ```yaml
   version: '3.8'
   services:
     web:
       image: nginx
       ports:
         - "80:80"
       restart: always
   ```
5. Click **Execute Workflow**
6. View real-time results

Using the API:

```bash
curl -X POST http://localhost:8080/api/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_name": "convert-and-validate",
    "input": "version: \"3.8\"\nservices:\n  web:\n    image: nginx"
  }' | jq .
```

## Daily Usage

### Starting and Stopping

```bash
# Start all services
make up

# Stop all services
make down

# Restart all services
make restart
```

### Monitoring

```bash
# View service status
make status

# Check agent health
make health

# View all logs
make logs

# View specific agent logs
make logs agent=swarm-converter

# Follow logs in real-time
make dev-watch
```

### Working with Agents

```bash
# Test an agent
make test-agent agent=swarm-converter

# Run agent with a file
make run agent=swarm-converter file=input.yml

# Get agent information
make agent-info agent=swarm-converter

# View agent context/history
make agent-context agent=swarm-converter

# Open Swagger UI for an agent
make docs agent=swarm-converter
```

### Working with Models

```bash
# List available models
make list-models

# Pull a new model
make pull-model model=codellama

# Pull all default models
make pull-models
```

## Creating Your First Custom Agent

### Step 1: Create Agent Directory

```bash
# Create a new agent directory
mkdir -p agents/my-agent

# Copy template files
cp agents/.agent-template/prompt.txt agents/my-agent/
cp agents/.agent-template/config.yml agents/my-agent/
```

### Step 2: Customize the Prompt

Edit `agents/my-agent/prompt.txt`:

```text
You are a specialized [YOUR DESCRIPTION] agent.

## Your Role and Expertise
[Define the agent's expertise and capabilities]

## Your Task
[Describe what the agent should do with input]

## Guidelines
- [Guideline 1]
- [Guideline 2]

## Output Format
[Specify expected output format]
```

### Step 3: Configure the Agent

Edit `agents/my-agent/config.yml`:

```yaml
agent:
  name: my-agent
  description: Brief description of what this agent does
  version: 1.0.0

capabilities:
  - capability-1
  - capability-2

options:
  temperature: 0.7      # 0.0-1.0 (lower = more deterministic)
  num_predict: 4096     # Max tokens to generate
  top_k: 40
  top_p: 0.9
```

### Step 4: Add to Docker Compose

Edit `docker-compose.yml` and add your agent service (copy from existing agent and modify).

### Step 5: Add Environment Variables

Edit `.env` and add:

```bash
# My Agent Configuration
MY_AGENT_PORT=7003
MY_AGENT_MODEL=llama3.2
MY_AGENT_TEMPERATURE=0.7
MY_AGENT_MAX_TOKENS=4096
```

### Step 6: Deploy and Test

```bash
# Rebuild and start
make rebuild

# Test your new agent
make test-agent agent=my-agent

# Check health
make health
```

For more details, see [Agent Documentation](AGENTS.md).

## Creating Custom Workflows

### Via YAML File

Create `backoffice/workflows/my-workflow.yml`:

```yaml
name: my-workflow
description: My custom workflow
version: 1.0.0

steps:
  - name: first-step
    agent: swarm-converter
    input: original        # Use original workflow input
    timeout: 300
    retry: 1
    on_error: stop

  - name: second-step
    agent: swarm-validator
    input: previous        # Use output from previous step
    timeout: 300
    retry: 1
    on_error: stop
```

Refresh the Workflows tab - it appears automatically!

### Via Web UI

1. Go to http://localhost:8080
2. Click **Workflows** tab
3. Click **Create Workflow**
4. Fill in the form
5. Save

For more details, see [Workflow Guide](WORKFLOWS.md).

## Common Tasks

### View API Documentation

Every agent has interactive API documentation:

```bash
# Open Swagger UI
make docs agent=swarm-converter

# Or access directly
open http://localhost:7001/docs
```

### Troubleshooting

If something goes wrong:

```bash
# Check logs
make logs agent=swarm-converter

# Verify health
make health

# Restart a specific service
docker compose restart agent-swarm-converter

# Start fresh (removes all data)
make clean
make init
```

For more help, see [Troubleshooting Guide](TROUBLESHOOTING.md).

## Next Steps

Now that you're set up, explore:

1. **[Agent Documentation](AGENTS.md)** - Learn how to create and configure agents
2. **[Workflow Guide](WORKFLOWS.md)** - Build multi-agent pipelines
3. **[Backoffice Guide](BACKOFFICE-GUIDE.md)** - Master the web UI
4. **[API Reference](API_REFERENCE.md)** - Integrate with your applications
5. **[GPU Setup](GPU-SETUP.md)** - Enable GPU acceleration

## Tips and Best Practices

- **Temperature Settings**:
  - Use 0.1-0.3 for technical tasks (code, SQL, conversions)
  - Use 0.4-0.7 for balanced tasks (documentation, explanations)
  - Use 0.8-1.0 for creative tasks (brainstorming, content)

- **Model Selection**:
  - `llama3.2` - General purpose, balanced
  - `codellama` - Code-focused tasks
  - `mistral` - Fast, efficient for simpler tasks

- **Performance**:
  - GPU recommended but not required
  - Monitor memory usage with `docker stats`
  - Use `make dev-watch` to monitor all logs

- **Context Memory**:
  - Agents remember past interactions
  - Clear context if responses become inconsistent: `curl -X DELETE http://localhost:7001/context`
  - View context: `make agent-context agent=swarm-converter`

## Getting Help

If you need assistance:

1. Check the [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Review agent logs: `make logs agent=<name>`
3. Verify configuration in `.env` and `docker-compose.yml`
4. Test Ollama: `curl http://localhost:11434/api/version`
5. Open an issue on GitHub with logs and configuration

Happy building! 🚀
