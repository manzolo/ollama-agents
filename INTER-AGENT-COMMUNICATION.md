# Inter-Agent Communication Guide

This guide explains how to enable communication between agents and use the `/process/raw` endpoint for programmatic access.

## Table of Contents

- [Overview](#overview)
- [Available Endpoints](#available-endpoints)
- [Using /process/raw](#using-processraw)
- [Inter-Agent Communication](#inter-agent-communication)
- [Examples](#examples)
- [Best Practices](#best-practices)

## Overview

The Ollama Agents framework provides three levels of output for different use cases:

1. **`/process`** - Full output with markdown, explanations, and metadata
2. **`/process/raw`** - Extracted clean output in JSON format
3. **`/process/raw/text`** - Pure plain text output (no JSON wrapper)

## Available Endpoints

### 1. /process - Full Response

**Use for**: Human consumption, debugging, learning

```bash
POST /process
```

**Returns**:
```json
{
  "agent": "swarm-converter",
  "output": "```yaml\n...\n```\n\n## Summary\n...",
  "model": "llama3.2",
  "timestamp": "2025-11-23T20:30:00",
  "metadata": {...}
}
```

### 2. /process/raw - Clean Output (JSON)

**Use for**: Inter-agent communication, API integration

```bash
POST /process/raw
```

**Returns**:
```json
{
  "agent": "swarm-converter",
  "output": "version: '3.8'\nservices:\n  web:\n    image: nginx",
  "format": "yaml",
  "timestamp": "2025-11-23T20:30:00"
}
```

**Features**:
- Automatically extracts code blocks
- Removes markdown formatting
- Detects output format
- Returns clean, usable content

### 3. /process/raw/text - Plain Text

**Use for**: File output, piping, shell scripts

```bash
POST /process/raw/text
```

**Returns**: Raw text (no JSON):
```yaml
version: '3.8'
services:
  web:
    image: nginx
```

## Using /process/raw

### Command Line

```bash
# Using Makefile (recommended)
make run-raw agent=swarm-converter file=input.yml

# Using curl
curl -X POST http://localhost:7001/process/raw \
  -H "Content-Type: application/json" \
  -d '{"input": "your content here"}' \
  | jq -r '.output'

# Save directly to file
curl -X POST http://localhost:7001/process/raw \
  -H "Content-Type: application/json" \
  -d '{"input": "version: 3.8..."}' \
  | jq -r '.output' > output.yml
```

### Python

```python
import httpx
import json

async def call_agent(agent_url: str, input_text: str) -> str:
    """Call agent and get clean output"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{agent_url}/process/raw",
            json={"input": input_text}
        )
        result = response.json()
        return result["output"]

# Usage
clean_output = await call_agent(
    "http://agent-swarm-converter:8000",
    docker_compose_content
)
```

### JavaScript/TypeScript

```typescript
async function callAgent(agentUrl: string, input: string): Promise<string> {
  const response = await fetch(`${agentUrl}/process/raw`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ input })
  });

  const result = await response.json();
  return result.output;
}

// Usage
const cleanOutput = await callAgent(
  'http://agent-swarm-converter:8000',
  dockerComposeContent
);
```

## Inter-Agent Communication

### Architecture

```
┌─────────────┐
│   Agent A   │
│  (Analyzer) │
└──────┬──────┘
       │ /process/raw
       ▼
┌─────────────┐
│   Agent B   │
│ (Converter) │
└──────┬──────┘
       │ /process/raw
       ▼
┌─────────────┐
│   Agent C   │
│ (Validator) │
└─────────────┘
```

### Example: Multi-Agent Pipeline

**Scenario**: Analyze → Convert → Validate a Docker Compose file

#### Step 1: Create Analyzer Agent

```python
# agents/analyzer/prompt.txt
You are a Docker Compose analyzer. Analyze the provided docker-compose.yml
and output a JSON summary of services, networks, and potential issues.
```

#### Step 2: Create Pipeline

```python
import httpx

async def pipeline(compose_file: str):
    async with httpx.AsyncClient() as client:
        # Step 1: Analyze
        analysis = await client.post(
            "http://agent-analyzer:8000/process/raw",
            json={"input": compose_file}
        )
        analysis_result = analysis.json()["output"]

        # Step 2: Convert based on analysis
        conversion = await client.post(
            "http://agent-swarm-converter:8000/process/raw",
            json={
                "input": compose_file,
                "options": {
                    "context": analysis_result  # Optional context
                }
            }
        )
        swarm_stack = conversion.json()["output"]

        # Step 3: Validate
        validation = await client.post(
            "http://agent-validator:8000/process/raw",
            json={"input": swarm_stack}
        )

        return {
            "analysis": analysis_result,
            "stack": swarm_stack,
            "validation": validation.json()["output"]
        }
```

### Agent-to-Agent Best Practices

1. **Use /process/raw** for inter-agent communication
2. **Handle errors** - Agents may fail or timeout
3. **Add retry logic** - Network issues happen
4. **Pass context** - Use metadata to chain operations
5. **Validate output** - Check format before next step

## Examples

### Example 1: Save Clean Output to File

```bash
# Using Makefile
make run-raw agent=swarm-converter file=docker-compose.yml > stack.yml

# Using curl
curl -X POST http://localhost:7001/process/raw/text \
  -H "Content-Type: application/json" \
  -d "$(jq -Rs '{input: .}' < docker-compose.yml)" \
  > swarm-stack.yml
```

### Example 2: Chain Two Agents

```bash
#!/bin/bash
# Convert docker-compose to swarm, then validate

# Step 1: Convert
swarm_yaml=$(curl -X POST http://localhost:7001/process/raw \
  -H "Content-Type: application/json" \
  -d "$(jq -Rs '{input: .}' < docker-compose.yml)" \
  -s | jq -r '.output')

# Step 2: Validate (with hypothetical validator agent)
curl -X POST http://localhost:7002/process/raw \
  -H "Content-Type: application/json" \
  -d "{\"input\": $(echo "$swarm_yaml" | jq -Rs .)}" \
  -s | jq .
```

### Example 3: Python Multi-Agent System

```python
from typing import Dict, Any
import httpx

class AgentOrchestrator:
    """Orchestrate multiple agents in a pipeline"""

    def __init__(self, agent_network: str = "ollama-agent-network"):
        self.client = httpx.AsyncClient(timeout=120.0)
        self.agents = {
            "analyzer": "http://agent-analyzer:8000",
            "converter": "http://agent-swarm-converter:8000",
            "validator": "http://agent-validator:8000",
        }

    async def call_agent(
        self,
        agent_name: str,
        input_data: str,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Call an agent and get clean output"""
        url = f"{self.agents[agent_name]}/process/raw"
        payload = {"input": input_data}
        if options:
            payload["options"] = options

        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    async def pipeline(self, compose_file: str) -> Dict[str, Any]:
        """Run complete analysis → conversion → validation pipeline"""

        # Analysis
        analysis = await self.call_agent("analyzer", compose_file)

        # Conversion with analysis context
        conversion = await self.call_agent(
            "converter",
            compose_file,
            options={"context": analysis["output"]}
        )

        # Validation
        validation = await self.call_agent(
            "validator",
            conversion["output"]
        )

        return {
            "original": compose_file,
            "analysis": analysis["output"],
            "swarm_stack": conversion["output"],
            "validation": validation["output"],
            "format": conversion["format"]
        }

# Usage
orchestrator = AgentOrchestrator()
result = await orchestrator.pipeline(compose_content)
print(result["swarm_stack"])
```

### Example 4: Agent as Microservice

```python
from fastapi import FastAPI, HTTPException
import httpx

app = FastAPI()

@app.post("/convert")
async def convert_to_swarm(compose_content: str):
    """Wrapper service that calls swarm-converter agent"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://agent-swarm-converter:8000/process/raw",
                json={"input": compose_content},
                timeout=120.0
            )
            response.raise_for_status()
            result = response.json()

            return {
                "success": True,
                "stack": result["output"],
                "format": result["format"]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Best Practices

### 1. Error Handling

```python
async def safe_agent_call(agent_url: str, input_data: str, retries: int = 3):
    """Call agent with retry logic"""
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{agent_url}/process/raw",
                    json={"input": input_data}
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            if attempt == retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### 2. Validation

```python
def validate_agent_response(response: Dict[str, Any]) -> bool:
    """Validate agent response structure"""
    required_fields = ["agent", "output", "format", "timestamp"]
    return all(field in response for field in required_fields)
```

### 3. Logging

```python
import logging

logger = logging.getLogger(__name__)

async def call_agent_with_logging(agent_name: str, input_data: str):
    """Call agent with detailed logging"""
    logger.info(f"Calling agent: {agent_name}")

    start_time = time.time()
    result = await call_agent(agent_name, input_data)
    duration = time.time() - start_time

    logger.info(f"Agent {agent_name} responded in {duration:.2f}s")
    logger.debug(f"Output format: {result.get('format')}")

    return result
```

### 4. Timeout Management

```python
import asyncio

async def call_with_timeout(agent_url: str, input_data: str, timeout: int = 60):
    """Call agent with timeout"""
    try:
        return await asyncio.wait_for(
            call_agent(agent_url, input_data),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        raise Exception(f"Agent call timed out after {timeout}s")
```

## Advanced Patterns

### Pattern 1: Fan-Out / Fan-In

```python
async def fan_out_fan_in(input_data: str, agents: list):
    """Call multiple agents in parallel and combine results"""
    tasks = [
        call_agent(agent, input_data)
        for agent in agents
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Combine results
    return {
        agent: result
        for agent, result in zip(agents, results)
        if not isinstance(result, Exception)
    }
```

### Pattern 2: Conditional Routing

```python
async def route_to_agent(input_data: str):
    """Route to different agents based on content"""
    # Analyze input first
    analysis = await call_agent("analyzer", input_data)

    # Route based on analysis
    if "docker-compose" in analysis["output"].lower():
        return await call_agent("swarm-converter", input_data)
    elif "kubernetes" in analysis["output"].lower():
        return await call_agent("k8s-converter", input_data)
    else:
        return await call_agent("generic-processor", input_data)
```

### Pattern 3: Result Caching

```python
from functools import lru_cache
import hashlib

class CachedAgentClient:
    def __init__(self):
        self.cache = {}

    def _get_cache_key(self, agent: str, input_data: str) -> str:
        """Generate cache key"""
        content = f"{agent}:{input_data}"
        return hashlib.sha256(content.encode()).hexdigest()

    async def call_cached(self, agent: str, input_data: str):
        """Call agent with caching"""
        cache_key = self._get_cache_key(agent, input_data)

        if cache_key in self.cache:
            return self.cache[cache_key]

        result = await call_agent(agent, input_data)
        self.cache[cache_key] = result
        return result
```

## Troubleshooting

### Issue: Agent not responding

```bash
# Check agent health
curl http://agent-swarm-converter:8000/health

# Check network connectivity
docker compose exec agent-analyzer ping agent-swarm-converter
```

### Issue: Timeout errors

```python
# Increase timeout
response = await client.post(
    url,
    json=payload,
    timeout=300.0  # 5 minutes
)
```

### Issue: Invalid output format

```python
# Validate before processing
result = response.json()
if not result.get("output"):
    raise ValueError("No output in response")
```

## Summary

The `/process/raw` endpoint enables:

✅ **Clean Output** - No markdown, just results
✅ **Inter-Agent Communication** - Agents calling agents
✅ **API Integration** - Easy programmatic access
✅ **Pipeline Building** - Chain multiple agents
✅ **File Output** - Direct save to files

Use `/process` for humans, `/process/raw` for machines!
