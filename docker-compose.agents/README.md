# Agent Compose Files (Legacy - Deprecated)

> ⚠️ **DEPRECATED**: This directory is no longer used as of the plugin system implementation.
>
> **New Structure:**
> - **Git-tracked examples**: `examples/compose/` for base agent compose files
> - **User-created agents**: `runtime/compose/` (gitignored) for user agent compose files
>
> **Documentation**: See [Plugin System Guide](../docs/PLUGINS.md)

## What Changed

The system now uses a **unified plugin structure** with automatic compose file generation:

### Old Approach (Deprecated)
- Manual compose files → `docker-compose.agents/my-agent.yml`
- Manual Makefile integration
- Hardcoded agent registry
- Separate from agent code

### New Approach (Current)
- Compose files in plugin folders:
  - `examples/compose/my-agent.yml` (git-tracked base agents)
  - `runtime/compose/my-agent.yml` (user-created agents, gitignored)
- Makefile auto-discovers from both locations
- Dynamic plugin registry
- Self-contained agent folders with manifests

## Migration Guide

If you have old compose files here:

1. **For base/example agents**:
   ```bash
   mv docker-compose.agents/my-agent.yml examples/compose/
   ```

2. **For user-created agents**:
   ```bash
   mv docker-compose.agents/my-agent.yml runtime/compose/
   ```

3. **Update agent structure**:
   - Ensure agent has `plugin.yml` manifest
   - See [Plugin System Guide](../docs/PLUGINS.md)

4. **Makefile automatically discovers**:
   ```bash
   make show-compose-files  # Shows all discovered compose files
   make list-agents         # Shows all running agents
   ```

## Current Makefile Configuration

The Makefile now loads compose files from:

```makefile
EXAMPLE_COMPOSE_FILES := $(wildcard examples/compose/*.yml)
RUNTIME_COMPOSE_FILES := $(wildcard runtime/compose/*.yml)
COMPOSE_FILES := -f docker-compose.yml $(foreach file,$(AGENT_COMPOSE_FILES),-f $(file))
```

## Why This Folder Remains

This folder is kept for reference but is no longer used by the system. It may be removed in a future version.

For the current plugin-based approach, see:
- [Plugin System Documentation](../docs/PLUGINS.md)
- [Agent Documentation](../docs/AGENTS.md)
- [Quick Start Guide](../docs/QUICK_START.md)
