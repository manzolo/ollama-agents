# Agent Definitions (Legacy - Deprecated)

> ⚠️ **DEPRECATED**: This directory is no longer used as of the plugin system implementation.
>
> **New Structure:**
> - **Git-tracked examples**: `examples/agents/` with `plugin.yml` manifests
> - **User-created agents**: `runtime/agents/` (gitignored) with `plugin.yml` manifests
>
> **Documentation**: See [Plugin System Guide](../../docs/PLUGINS.md)

## What Changed

The system now uses a **plugin-based architecture** with self-describing agents:

### Old Approach (Deprecated)
- Separate definition files → `backoffice/agent-definitions/my-agent.yml`
- Separate agent code → `agents/my-agent/`
- Separate compose files → `docker-compose.agents/my-agent.yml`
- Hardcoded agent registry in code
- Manual deployment steps

### New Approach (Current)
- Self-contained plugin folders → `runtime/agents/my-agent/`
- Plugin manifest → `plugin.yml` (metadata, capabilities, API contract)
- Dynamic discovery (filesystem + Docker)
- Hot-pluggable (no restarts needed)
- Clean git structure (examples/ tracked, runtime/ gitignored)

## Migration Guide

If you have old agent definitions here:

1. **View the new plugin structure**:
   ```bash
   ls -la examples/agents/swarm-converter/
   # plugin.yml  prompt.txt  config.yml
   ```

2. **Create plugin using Backoffice UI**:
   - Open http://localhost:8080
   - Click "Create New Agent"
   - System auto-generates plugin.yml

3. **Or manually from template**:
   ```bash
   cp -r agents/.agent-template runtime/agents/my-agent
   # Edit plugin.yml, prompt.txt, config.yml
   ```

4. **Learn more**:
   - [Plugin System Documentation](../../docs/PLUGINS.md)
   - [Agent Documentation](../../docs/AGENTS.md)

## Why This Folder Remains

This folder is kept for reference but is no longer used by the system. It may be removed in a future version.
