# Agent Documentation

Complete guide to working with agents in Ollama Agents.

## Base Agents

### Swarm Converter

Converts Docker Compose files to Docker Swarm stack files.

**Endpoint**: http://localhost:7001

**Features:**
- Analyzes Docker Compose YAML structure
- Converts to Swarm-compatible format
- Provides conversion notes and warnings

### Swarm Validator

Validates Docker Swarm stack files for correctness and best practices.

**Endpoint**: http://localhost:7002

**Features:**
- Validates Swarm compatibility
- Checks for common issues
- Suggests best practices

## Creating New Agents

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
      - "${MY_NEW_AGENT_PORT:-7003}:8000"
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
MY_NEW_AGENT_PORT=7003
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

## Configuration

### Temperature Guidelines

- **0.0-0.3**: Technical, deterministic tasks (code, SQL, conversions)
- **0.4-0.7**: Balanced tasks (documentation, explanations)
- **0.8-1.0**: Creative tasks (brainstorming, content generation)

### Model Selection

- **llama3.2**: General purpose, balanced performance
- **codellama**: Code-focused tasks
- **mistral**: Fast, efficient for simpler tasks
- **mixtral**: Complex reasoning, multi-task

## Inter-Agent Communication

Agents can communicate with each other using the `/process/raw` endpoints.

### Example: Python

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
        return result["output"]

# Usage
swarm_stack = await call_agent(
    "http://agent-swarm-converter:8000",
    docker_compose_content
)
```

### Multi-Agent Pipeline

```python
# Step 1: Analyze with one agent
analysis = await call_agent("http://agent-analyzer:8000", input_data)

# Step 2: Convert based on analysis
converted = await call_agent("http://agent-swarm-converter:8000", input_data)

# Step 3: Validate the result
validation = await call_agent("http://agent-validator:8000", converted)
```

For detailed examples, see [INTER-AGENT-COMMUNICATION.md](../INTER-AGENT-COMMUNICATION.md).
