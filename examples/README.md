# Examples Directory

This directory contains base/example agents that are tracked in git and serve as templates for creating new agents.

## Structure

```
examples/
├── agents/                    # Agent configurations (prompt + config)
│   ├── swarm-converter/
│   │   ├── prompt.txt        # System prompt
│   │   └── config.yml        # Agent configuration
│   └── swarm-validator/
│       ├── prompt.txt
│       └── config.yml
├── agent-definitions/         # Agent definition files (YAML)
│   ├── swarm-converter.yml
│   └── swarm-validator.yml
└── compose/                   # Docker Compose files for agents
    ├── swarm-converter.yml
    └── swarm-validator.yml
```

## Purpose

- **Read-only in containers** - Mounted as `:ro` in Docker
- **Git-tracked** - These are the base agents included with the project
- **Templates** - Use these as starting points for your own agents
- **Examples** - Demonstrate best practices for agent creation

## Using Examples as Templates

### Via Backoffice UI

1. Open http://localhost:8080
2. Click "Create Agent"
3. Use the AI Assistant or manually configure
4. The agent will be created in `runtime/` (not here)

### Manually

1. Copy an example agent:
   ```bash
   cp -r examples/agents/swarm-converter runtime/agents/my-agent
   ```

2. Modify the files:
   ```bash
   # Edit prompt
   nano runtime/agents/my-agent/prompt.txt

   # Edit config
   nano runtime/agents/my-agent/config.yml
   ```

3. Deploy via backoffice or manually add to docker-compose

## Example Agents

### Swarm Converter
- **Purpose**: Converts Docker Compose files to Swarm stacks
- **Model**: llama3.2
- **Temperature**: 0.3 (deterministic)
- **Port**: 7001

### Swarm Validator
- **Purpose**: Validates Swarm stack files
- **Model**: llama3.2
- **Temperature**: 0.3 (deterministic)
- **Port**: 7002

## Notes

- These files are **read-only** and should not be modified for runtime use
- All user-created agents go in `runtime/` directory
- To customize an example, copy it to `runtime/` first
- Examples are automatically available as templates in the backoffice UI
