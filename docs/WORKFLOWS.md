# Workflow Guide

Complete guide to creating and managing multi-agent workflows.

## Overview

Workflows allow you to chain multiple agents together through the Backoffice. They are defined in YAML format and stored in `backoffice/workflows/`.

## Workflow Format

```yaml
name: workflow-name
description: What this workflow does
version: 1.0.0

steps:
  - name: step-name
    agent: agent-name        # Name from agent registry
    input: original          # Input source (see below)
    timeout: 300             # Optional timeout in seconds
    retry: 1                 # Optional number of retries
    on_error: stop           # stop, continue, or skip

metadata:
  author: Your Name
  tags: [docker, validation]
```

## Input Sources

- **`original`** - Use the initial workflow input
- **`previous`** - Use output from the previous step (default)
- **`step[N]`** - Use output from step N (0-indexed)
- Direct string - Any other value is used as literal input

## Error Handling

- **`stop`** - Stop workflow execution on error (default)
- **`continue`** - Continue to next step even if this step fails
- **`skip`** - Skip remaining steps if this step fails

## Example Workflows

### Sequential Pipeline

```yaml
name: convert-and-validate
description: Convert docker-compose to swarm and validate it
version: 1.0.0

steps:
  - name: convert-to-swarm
    agent: swarm-converter
    input: original
    timeout: 300
    retry: 1
    on_error: stop

  - name: validate-swarm-stack
    agent: swarm-validator
    input: previous
    timeout: 300
    retry: 1
    on_error: stop
```

### Parallel Analysis

```yaml
name: multi-analysis
description: Run multiple analyses in parallel
version: 1.0.0

steps:
  - name: security-check
    agent: security-analyzer
    input: original

  - name: performance-check
    agent: performance-analyzer
    input: original

  - name: combine-results
    agent: result-aggregator
    input: step[0] + step[1]
```

## Managing Workflows

### Via Web UI

1. Go to http://localhost:8080
2. Click the **Workflows** tab
3. Click **Create** button
4. Fill in the workflow details and YAML

### Via File System

1. Create a YAML file in `backoffice/workflows/`
2. Refresh the Workflows tab in the UI
3. The workflow appears automatically

### Via API

```bash
curl -X POST http://localhost:8080/api/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-workflow",
    "description": "My custom workflow",
    "version": "1.0.0",
    "steps": [...]
  }'
```

## Executing Workflows

### Via Web UI

1. Go to **Execute** tab
2. Select your workflow
3. Enter input data
4. Click **Execute Workflow**
5. View results in real-time

### Via API

```bash
curl -X POST http://localhost:8080/api/workflows/my-workflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "input": "your input data here"
  }'
```

## Best Practices

1. **Keep workflows focused** - One workflow = one clear purpose
2. **Use meaningful names** - Both for workflow and step names
3. **Add descriptions** - Help others understand what it does
4. **Handle errors appropriately** - Use `on_error` strategically
5. **Test incrementally** - Test each agent before chaining them
6. **Document metadata** - Add author, tags, and version info

## Advanced Features

### Conditional Execution

```yaml
steps:
  - name: analyze
    agent: analyzer
    input: original

  - name: fix-if-needed
    agent: fixer
    input: previous
    on_error: continue  # Don't fail if already valid
```

### Timeout Management

```yaml
steps:
  - name: quick-check
    agent: validator
    timeout: 30  # 30 seconds

  - name: deep-analysis
    agent: analyzer
    timeout: 600  # 10 minutes
```

### Retry Logic

```yaml
steps:
  - name: external-api-call
    agent: api-caller
    retry: 3  # Retry up to 3 times
    timeout: 60
```
