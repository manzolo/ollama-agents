# Workflow Definitions

This directory contains YAML workflow definitions that can be executed by the orchestrator.

## Workflow Format

```yaml
name: workflow-name
description: Description of what this workflow does
version: 1.0.0

steps:
  - name: step-name
    agent: agent-name           # Name of the agent to call
    agent_url: http://...       # Optional: explicit agent URL (overrides registry)
    input: original             # Input source: 'original', 'previous', 'step[N]', or direct value
    timeout: 300                # Timeout in seconds (default: 300)
    retry: 0                    # Number of retries on failure (default: 0)
    on_error: stop              # Error handling: 'stop', 'continue', 'skip' (default: stop)
    transform: ...              # Optional: transformation to apply
    condition: ...              # Optional: condition for execution

metadata:
  author: Your Name
  created: 2025-11-24
  tags:
    - tag1
    - tag2
```

## Input Sources

- `original`: Use the original workflow input
- `previous`: Use output from the previous step (default)
- `step[N]`: Use output from step N (0-indexed)
- Direct string: Any other value is treated as a direct input string

## Error Handling

- `stop`: Stop workflow execution on error (default)
- `continue`: Continue to next step even if this step fails
- `skip`: Skip remaining steps if this step fails

## Examples

### Simple Sequential Pipeline

```yaml
name: simple-pipeline
description: Chain two agents in sequence
steps:
  - name: first-step
    agent: agent-1
    input: original
  - name: second-step
    agent: agent-2
    input: previous
```

### Advanced Pipeline with Error Handling

```yaml
name: robust-pipeline
description: Pipeline with retries and error handling
steps:
  - name: critical-step
    agent: agent-1
    input: original
    retry: 3
    timeout: 600
    on_error: stop
  - name: optional-step
    agent: agent-2
    input: previous
    on_error: continue
```

### Using Specific Step Output

```yaml
name: branching-pipeline
description: Reuse output from earlier steps
steps:
  - name: analyze
    agent: analyzer
    input: original
  - name: transform
    agent: transformer
    input: original
  - name: validate
    agent: validator
    input: step[1]  # Use output from transform step
```
