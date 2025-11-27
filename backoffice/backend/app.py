#!/usr/bin/env python3
"""
Backoffice API Server
Provides REST API for managing agents and executing workflows.
"""

import os
import re
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from pydantic import BaseModel, Field
import uvicorn
import httpx

from orchestrator import WorkflowOrchestrator, WorkflowManager, Workflow
from agent_manager import AgentManager, AgentDefinition
from deployment_manager import DeploymentManager
from plugin_manager import PluginRegistry, PluginValidator, PluginManifest


# ============================================================================
# Configuration
# ============================================================================
# Runtime directories (user-created, gitignored)
WORKFLOWS_DIR = Path(os.getenv("WORKFLOWS_DIR", "/app/runtime/workflows"))
AGENT_DEFINITIONS_DIR = Path(os.getenv("AGENT_DEFINITIONS_DIR", "/app/runtime/agent-definitions"))
COMPOSE_DIR = Path(os.getenv("COMPOSE_DIR", "/app/runtime/compose"))

# Examples directories (git-tracked templates)
WORKFLOWS_EXAMPLES_DIR = Path(os.getenv("WORKFLOWS_EXAMPLES_DIR", "/app/examples/workflows"))
EXAMPLES_DIR = Path(os.getenv("EXAMPLES_DIR", "/app/examples"))

# Other paths
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", "/app/frontend"))
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", "/project"))

# Initialize Plugin Registry (replaces static AGENT_REGISTRY)
plugin_registry = PluginRegistry(PROJECT_ROOT)


# ============================================================================
# Data Models
# ============================================================================
class WorkflowExecuteRequest(BaseModel):
    """Request to execute a workflow"""
    input: str = Field(..., description="Input data for the workflow")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context variables")


class WorkflowCreateRequest(BaseModel):
    """Request to create a new workflow"""
    name: str = Field(..., description="Workflow name")
    description: str = Field("", description="Workflow description")
    version: str = Field("1.0.0", description="Workflow version")
    steps: List[Dict[str, Any]] = Field(..., description="Workflow steps")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class AgentTestRequest(BaseModel):
    """Request to test an agent"""
    agent_name: str = Field(..., description="Name of the agent to test")
    input: str = Field(..., description="Test input")


class AgentCreateRequest(BaseModel):
    """Request to create a new agent"""
    name: str = Field(..., description="Agent name (alphanumeric with hyphens)", pattern="^[a-z0-9-]+$")
    description: str = Field(..., description="Agent description")
    port: int = Field(..., description="Port number (7000-7999)", ge=7000, le=7999)
    model: str = Field("llama3.2", description="Model to use")
    temperature: float = Field(0.7, description="Temperature (0.0-1.0)", ge=0.0, le=1.0)
    max_tokens: int = Field(4096, description="Max tokens", ge=256, le=32768)
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    system_prompt: str = Field(..., description="System prompt for the agent")


class PromptGenerateRequest(BaseModel):
    """Request to generate an agent prompt using AI"""
    agent_purpose: str = Field(..., description="What should this agent do?")
    agent_expertise: str = Field("", description="What domain expertise should it have?")
    input_format: str = Field("", description="What format of input will it receive?")
    output_format: str = Field("", description="What format should the output be?")


# ============================================================================
# FastAPI Application
# ============================================================================
app = FastAPI(
    title="Ollama Agents Backoffice",
    description="""
## Multi-Agent Workflow Management System

This backoffice provides a web interface and API for managing multiple AI agents
and executing complex workflows.

### Features
- 🤖 Discover and manage multiple agents
- 🔄 Create and execute custom workflows
- 📊 Monitor workflow execution in real-time
- 📝 YAML-based workflow definitions
- 🔗 Agent chaining and orchestration

### Workflow System
Workflows are defined in YAML format and can:
- Chain multiple agents in sequence
- Use output from previous steps
- Handle errors gracefully
- Retry failed steps
- Execute conditionally

### Example Workflow
```yaml
name: convert-and-validate
description: Convert docker-compose to swarm and validate
steps:
  - name: convert
    agent: swarm-converter
    input: original
  - name: validate
    agent: swarm-validator
    input: previous
```
    """,
    version="1.0.0",
    openapi_tags=[
        {"name": "agents", "description": "Agent discovery and management"},
        {"name": "workflows", "description": "Workflow management and execution"},
        {"name": "health", "description": "Health and status endpoints"}
    ]
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
workflow_manager = WorkflowManager(WORKFLOWS_DIR, WORKFLOWS_EXAMPLES_DIR)
agent_manager = AgentManager(AGENT_DEFINITIONS_DIR)
deployment_manager = DeploymentManager(PROJECT_ROOT)

# Orchestrator will be initialized after plugin discovery
orchestrator = None

# Store for workflow executions (in-memory for now)
executions = {}


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Redirect to frontend"""
    if FRONTEND_DIR.exists() and (FRONTEND_DIR / "index.html").exists():
        return FileResponse(FRONTEND_DIR / "index.html")
    return {"message": "Ollama Agents Backoffice API", "docs": "/docs"}


@app.get("/api/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "backoffice",
        "timestamp": datetime.now().isoformat(),
        "workflows_runtime": str(WORKFLOWS_DIR),
        "workflows_examples": str(WORKFLOWS_EXAMPLES_DIR),
        "registered_agents": len(plugin_registry.list_all())
    }


# ============================================================================
# Agent Endpoints
# ============================================================================

async def discover_runtime_agents() -> Dict[str, Any]:
    """
    Helper to discover all running agents from Docker and static definitions.
    Returns a dictionary of agent info.
    """
    # Get running agents from Docker
    discovered_agents = {}

    if deployment_manager.docker_client:
        try:
            # Use low-level API to avoid crashes from "ghost" containers
            # client.containers.list() tries to inspect every container and crashes if one is dead/missing
            containers = deployment_manager.docker_client.api.containers(all=True)
            
            for c_dict in containers:
                try:
                    # Parse container info from dict
                    c_id = c_dict.get('Id')
                    names = c_dict.get('Names', [])
                    status = c_dict.get('State', 'unknown')
                    
                    # Names usually come as ['/name']
                    name = names[0].lstrip('/') if names else ""
                    
                    if not name.startswith("agent-"):
                        continue

                    agent_name = name.replace("agent-", "")
                    
                    # Prioritize internal Docker network URL
                    url = f"http://{name}:8000"
                    
                    agent_info = {
                        "name": agent_name,
                        "url": url,
                        "container_status": status,
                        "status": "stopped"
                    }

                    if status == "running":
                        # Try to get agent info via health/info endpoint
                        try:
                            async with httpx.AsyncClient(timeout=2.0) as client:
                                response = await client.get(f"{url}/info")
                                if response.status_code == 200:
                                    info = response.json()
                                    agent_info.update(info)
                                    agent_info["status"] = "healthy"
                                else:
                                    agent_info["status"] = "unhealthy"
                        except Exception:
                            # Container is running but not responsive yet
                            agent_info["status"] = "starting"
                    
                    # Get source information from plugin registry
                    plugin = plugin_registry.get(agent_name)
                    if plugin:
                        agent_info["source"] = plugin.get("source", "runtime")
                    else:
                        # If not in plugin registry, assume runtime
                        agent_info["source"] = "runtime"

                    discovered_agents[agent_name] = agent_info

                except Exception as e:
                    # Log error but don't crash the loop
                    print(f"Error processing container {c_dict.get('Id', 'unknown')}: {e}")
                    continue

        except Exception as e:
            print(f"Error discovering agents: {e}")

    # Merge with original discovery (for backwards compatibility)
    # Only add from original if not already discovered
    try:
        original_agents = await orchestrator.discover_agents()
        for name, info in original_agents.items():
            if name not in discovered_agents:
                # Get source from plugin registry
                plugin = plugin_registry.get(name)
                if plugin:
                    info["source"] = plugin.get("source", "runtime")
                else:
                    info["source"] = "runtime"
                discovered_agents[name] = info
    except Exception as e:
        print(f"Error in original discovery: {e}")

    return discovered_agents


@app.get("/api/agents", tags=["agents"], summary="List all agents")
async def list_agents():
    """
    Discover and list all available agents.

    Returns information about each agent including:
    - URL
    - Health status
    - Model being used
    - Capabilities
    - Description

    This endpoint now discovers ALL agents by scanning:
    1. Docker containers with prefix "agent-"
    2. Agent definitions waiting to be deployed
    """
    discovered_agents = await discover_runtime_agents()
    
    # Sync with orchestrator registry so workflows can use these agents
    for name, info in discovered_agents.items():
        if info.get("url"):
            orchestrator.agent_registry[name] = info["url"]

    print(f"Returning {len(discovered_agents)} agents: {list(discovered_agents.keys())}")
    # import json
    # print(json.dumps(discovered_agents, indent=2))

    return {
        "count": len(discovered_agents),
        "agents": discovered_agents
    }


@app.get("/api/agents/definitions", tags=["agents"], summary="List agent definitions")
async def list_agent_definitions():
    """
    List all agent definitions (both deployed and pending).
    """
    definitions = agent_manager.list_agent_definitions()
    return {
        "count": len(definitions),
        "definitions": definitions
    }


@app.get("/api/agents/{agent_name}", tags=["agents"], summary="Get agent details")
async def get_agent_details(agent_name: str):
    """Get detailed information about a specific agent"""
    plugin = plugin_registry.get(agent_name)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found in registry")

    agents = await orchestrator.discover_agents()
    if agent_name not in agents:
        raise HTTPException(status_code=503, detail=f"Agent '{agent_name}' is unavailable")

    # Merge plugin manifest with runtime info
    agent_info = agents[agent_name]
    if plugin.get("manifest"):
        agent_info["plugin"] = plugin["manifest"]

    return agent_info


@app.post("/api/agents/test", tags=["agents"], summary="Test an agent")
async def test_agent(request: AgentTestRequest):
    """
    Test an agent with sample input.

    This endpoint allows you to quickly test if an agent is working correctly
    by sending it test input and seeing the response.
    """
    # Ensure agent is known to orchestrator
    if request.agent_name not in orchestrator.agent_registry:
        # Try to discover agents and update registry
        print(f"Agent {request.agent_name} not in registry, discovering...")
        agents = await discover_runtime_agents()
        for name, info in agents.items():
            if info.get("url"):
                orchestrator.agent_registry[name] = info["url"]
    
    result = await orchestrator.call_agent(
        agent_name=request.agent_name,
        input_text=request.input
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=502,
            detail=f"Agent call failed: {result.get('error')}"
        )

    return result


@app.get("/api/agents/{agent_name}/deploy-script", tags=["agents"], summary="Get deploy script")
async def get_deploy_script(agent_name: str):
    """
    Get the deployment script for an agent.
    Download and run this script to deploy the agent.
    """
    try:
        script = agent_manager.generate_deploy_script(agent_name)
        return PlainTextResponse(
            content=script,
            media_type="text/x-shellscript",
            headers={
                "Content-Disposition": f"attachment; filename=deploy-{agent_name}.sh"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/agents/create", tags=["agents"], summary="Create a new agent")
async def create_agent(request: AgentCreateRequest):
    """
    Create a new agent definition.

    This endpoint creates a declarative agent definition file that can be
    deployed using the provided deploy script or CLI tool.

    This modular approach:
    - Separates definition from deployment
    - No direct filesystem access needed
    - Easy to version control
    - Can be deployed manually or automatically
    """
    try:
        # Create agent definition
        agent_def = AgentDefinition(
            name=request.name,
            description=request.description,
            port=request.port,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            capabilities=request.capabilities,
            system_prompt=request.system_prompt
        )

        # Save agent definition
        definition_file = agent_manager.save_agent_definition(agent_def)

        # Generate deploy script
        deploy_script = agent_manager.generate_deploy_script(request.name)

        return {
            "status": "created",
            "agent_name": request.name,
            "message": f"Agent definition created successfully!",
            "details": {
                "definition_file": definition_file,
                "port": request.port,
                "model": request.model,
                "deploy_script": deploy_script
            },
            "next_steps": [
                f"Download the deploy script from /api/agents/{request.name}/deploy-script",
                "Run the script: bash deploy-script.sh",
                "Or manually add the service to docker-compose.yml",
                f"Test the agent: curl http://localhost:{request.port}/health"
            ]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create agent definition: {str(e)}"
        )


@app.delete("/api/agents/definitions/{agent_name}", tags=["agents"], summary="Delete agent definition")
async def delete_agent_definition(agent_name: str):
    """Delete an agent definition"""
    success = agent_manager.delete_agent_definition(agent_name)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Agent definition '{agent_name}' not found"
        )

    return {
        "status": "deleted",
        "agent_name": agent_name,
        "message": "Agent definition deleted. The deployed agent (if any) is not affected."
    }


@app.post("/api/agents/generate-prompt", tags=["agents"], summary="Generate agent prompt with AI")
async def generate_agent_prompt(request: PromptGenerateRequest):
    """
    Use AI to generate a well-structured agent prompt based on user requirements.

    This uses Ollama directly to help users write better agent prompts.
    """
    # Meta-prompt for generating agent prompts
    meta_prompt = f"""You are an expert at writing system prompts for AI agents.

Create a comprehensive, well-structured system prompt for an AI agent with these requirements:

**Purpose:** {request.agent_purpose}
{f"**Expertise Domain:** {request.agent_expertise}" if request.agent_expertise else ""}
{f"**Input Format:** {request.input_format}" if request.input_format else ""}
{f"**Output Format:** {request.output_format}" if request.output_format else ""}

Create a system prompt that includes:
1. A clear role definition
2. The agent's expertise and capabilities
3. Step-by-step task instructions
4. Guidelines and best practices
5. Output format specification
6. Any constraints or limitations

Format the prompt professionally with markdown headers (##) and bullet points.
Make it clear, actionable, and comprehensive.

Return ONLY the system prompt itself, ready to use. Do not include explanations or meta-commentary."""

    try:
        # Call Ollama directly
        import httpx
        import traceback
        ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434")

        # Use longer timeout for CPU mode (5 minutes) vs GPU (2 minutes)
        # Check for GPU mode via OLLAMA_GPU env var or default to longer timeout
        is_gpu = os.getenv("OLLAMA_GPU", "false").lower() == "true"
        timeout = 120.0 if is_gpu else 300.0
        print(f"Using timeout of {timeout}s for prompt generation ({'GPU' if is_gpu else 'CPU'} mode)")

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{ollama_host}/api/generate",
                json={
                    "model": "llama3.2",
                    "prompt": meta_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 2048
                    }
                }
            )
            response.raise_for_status()
            result = response.json()
            generated_prompt = result.get("response", "")

            return {
                "status": "success",
                "generated_prompt": generated_prompt.strip(),
                "message": "Prompt generated successfully! Review and edit as needed."
            }

    except Exception as e:
        # Log the actual error for debugging
        print(f"ERROR: Failed to generate prompt: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate prompt: {str(e)}"
        )


@app.post("/api/agents/{agent_name}/deploy", tags=["agents"], summary="Deploy an agent")
async def deploy_agent(agent_name: str):
    """
    Fully deploy an agent with one click.

    This endpoint:
    1. Loads the agent definition
    2. Creates all necessary files
    3. Updates docker-compose.yml and .env
    4. Builds and starts the container
    5. Detects and handles GPU mode automatically
    """
    try:
        # Load agent definition
        definition = agent_manager.get_agent_definition(agent_name)
        if not definition:
            raise HTTPException(
                status_code=404,
                detail=f"Agent definition '{agent_name}' not found"
            )

        # Deploy the agent
        result = deployment_manager.deploy_agent(agent_name, definition)

        if result["status"] == "success":
            return {
                "status": "success",
                "message": f"Agent '{agent_name}' deployed successfully!",
                "details": result,
                "gpu_mode": result.get("gpu_mode", False)
            }
        elif result["status"] == "partial":
            return {
                "status": "partial",
                "message": f"Agent files created but container deployment failed",
                "details": result
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Deployment failed: {', '.join(result['errors'])}"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Deployment error: {str(e)}"
        )


@app.get("/api/agents/{agent_name}/status", tags=["agents"], summary="Get agent deployment status")
async def get_agent_deployment_status(agent_name: str):
    """
    Get the deployment status of an agent.

    Returns information about:
    - Files existence
    - Docker compose configuration
    - Environment variables
    - Container status
    - Health status
    """
    status = deployment_manager.get_agent_status(agent_name)
    return status


@app.post("/api/agents/{agent_name}/restart", tags=["agents"], summary="Restart an agent")
async def restart_agent_container(agent_name: str):
    """Restart an agent's container"""
    result = deployment_manager.restart_agent(agent_name)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@app.post("/api/agents/{agent_name}/stop", tags=["agents"], summary="Stop an agent")
async def stop_agent_container(agent_name: str):
    """Stop an agent's container"""
    result = deployment_manager.stop_agent(agent_name)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@app.post("/api/agents/{agent_name}/start", tags=["agents"], summary="Start a stopped agent")
async def start_agent_container(agent_name: str):
    """Start a stopped agent container using docker-compose"""
    result = deployment_manager.start_agent(agent_name)
    if result["status"] == "success":
        return result
    else:
        raise HTTPException(status_code=500, detail=result["message"])


@app.delete("/api/agents/{agent_name}", tags=["agents"], summary="Delete an agent completely")
async def delete_agent_completely(agent_name: str, remove_files: bool = True):
    """
    Completely delete an agent.

    This will:
    1. Stop and remove the container
    2. Remove from docker-compose.yml
    3. Remove from .env
    4. Delete agent files (if remove_files=true)
    5. Delete agent definition
    6. Remove from agent registry

    Warning: This is irreversible!
    """
    # Delete from deployment
    result = deployment_manager.delete_agent(agent_name, remove_files)

    # Also delete the agent definition
    agent_manager.delete_agent_definition(agent_name)

    # Remove from orchestrator registry
    if orchestrator and agent_name in orchestrator.agent_registry:
        del orchestrator.agent_registry[agent_name]
        print(f"Removed {agent_name} from orchestrator registry")

    # Unregister from plugin registry
    plugin_registry.unregister(agent_name)
    print(f"Unregistered plugin: {agent_name}")

    if result["status"] == "failed":
        raise HTTPException(
            status_code=500,
            detail=f"Deletion failed: {', '.join(result['errors'])}"
        )

    return {
        "status": result["status"],
        "message": f"Agent '{agent_name}' deleted successfully",
        "details": result
    }


# ============================================================================
# Plugin Endpoints
# ============================================================================

@app.get("/api/plugins", tags=["plugins"], summary="List all registered plugins")
async def list_plugins():
    """
    List all registered plugins with their manifests.

    Returns detailed information about all discovered plugins including
    metadata, capabilities, and API contracts.
    """
    plugins = plugin_registry.list_all()

    return {
        "count": len(plugins),
        "plugins": [
            {
                "id": plugin_id,
                "url": data["url"],
                "status": data.get("status", "unknown"),
                "registered_at": data.get("registered_at"),
                **data.get("manifest", {})
            }
            for plugin_id, data in plugins.items()
        ]
    }


@app.get("/api/plugins/{plugin_id}", tags=["plugins"], summary="Get plugin details")
async def get_plugin(plugin_id: str):
    """Get detailed information about a specific plugin"""
    plugin = plugin_registry.get(plugin_id)

    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    return plugin


@app.post("/api/plugins/discover", tags=["plugins"], summary="Re-discover plugins")
async def rediscover_plugins():
    """
    Trigger plugin re-discovery.

    Scans filesystem and Docker for new or updated plugins.
    """
    global orchestrator

    # Re-discover plugins
    plugin_count = plugin_registry.discover_all()

    # Reinitialize orchestrator with updated registry
    agent_registry_legacy = plugin_registry.to_legacy_registry()
    orchestrator = WorkflowOrchestrator(agent_registry_legacy)

    return {
        "status": "success",
        "plugins_discovered": plugin_count,
        "plugins": list(plugin_registry.list_all().keys())
    }


@app.post("/api/plugins/{plugin_id}/validate", tags=["plugins"], summary="Validate plugin manifest")
async def validate_plugin_manifest(plugin_id: str):
    """
    Validate a plugin's manifest file.

    Checks if the plugin.yml file is valid and conforms to the schema.
    """
    # Find plugin manifest file
    plugin_paths = [
        PROJECT_ROOT / "examples" / "agents" / plugin_id / "plugin.yml",
        PROJECT_ROOT / "runtime" / "agents" / plugin_id / "plugin.yml",
    ]

    plugin_yml = None
    for path in plugin_paths:
        if path.exists():
            plugin_yml = path
            break

    if not plugin_yml:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin manifest not found for '{plugin_id}'"
        )

    is_valid, errors, manifest = PluginValidator.validate_file(plugin_yml)

    if is_valid:
        return {
            "status": "valid",
            "plugin_id": plugin_id,
            "manifest": manifest.to_dict()
        }
    else:
        return {
            "status": "invalid",
            "plugin_id": plugin_id,
            "errors": errors
        }


# ============================================================================
# Workflow Endpoints
# ============================================================================

@app.get("/api/workflows", tags=["workflows"], summary="List all workflows")
async def list_workflows():
    """
    List all available workflow definitions.

    Returns a list of workflows that can be executed.
    """
    workflows = workflow_manager.list_workflows()
    return {
        "count": len(workflows),
        "workflows": workflows
    }


@app.post("/api/workflows/{workflow_name}/execute", tags=["workflows"], summary="Execute a workflow")
async def execute_workflow(workflow_name: str, request: WorkflowExecuteRequest):
    """
    Execute a specific workflow with the given input.

    This is a resource-oriented endpoint where the workflow name is part of the URL path.
    The request body only needs to contain the input data and optional context.

    The workflow will be executed asynchronously and return immediately with
    an execution ID. Use the execution ID to check the status and results.
    """
    # Load workflow
    workflow = workflow_manager.load_workflow(workflow_name)
    if not workflow:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{workflow_name}' not found"
        )

    # Execute workflow
    try:
        execution = await orchestrator.execute_workflow(
            workflow=workflow,
            initial_input=request.input,
            context=request.context
        )

        # Store execution
        executions[execution.execution_id] = execution

        return {
            "status": "executed",
            "execution_id": execution.execution_id,
            "result": execution.to_dict()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Workflow execution failed: {str(e)}"
        )


@app.get("/api/workflows/{workflow_name}", tags=["workflows"], summary="Get workflow details")
async def get_workflow(workflow_name: str):
    """Get detailed information about a specific workflow"""
    workflow = workflow_manager.load_workflow(workflow_name)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")

    return {
        "name": workflow.name,
        "description": workflow.description,
        "version": workflow.version,
        "steps": [
            {
                "name": step.name,
                "agent": step.agent,
                "input_source": step.input_source,
                "timeout": step.timeout,
                "retry": step.retry,
                "on_error": step.on_error
            }
            for step in workflow.steps
        ],
        "metadata": workflow.metadata
    }


@app.post("/api/workflows", tags=["workflows"], summary="Create a new workflow")
async def create_workflow(request: WorkflowCreateRequest):
    """
    Create a new workflow definition.

    The workflow will be saved as a YAML file and can be executed immediately.
    """
    workflow_config = {
        "name": request.name,
        "description": request.description,
        "version": request.version,
        "steps": request.steps,
        "metadata": request.metadata or {}
    }

    try:
        filepath = workflow_manager.save_workflow(workflow_config)
        return {
            "status": "created",
            "workflow_name": request.name,
            "filepath": filepath
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create workflow: {str(e)}")


@app.put("/api/workflows/{workflow_name}", tags=["workflows"], summary="Update a workflow")
async def update_workflow(workflow_name: str, request: WorkflowCreateRequest):
    """
    Update an existing workflow definition.

    This will overwrite the existing workflow file with the new configuration.
    """
    # Check if workflow exists
    existing_workflow = workflow_manager.load_workflow(workflow_name)
    if not existing_workflow:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")

    # If the name is changing, delete the old file
    if request.name != workflow_name:
        workflow_manager.delete_workflow(workflow_name)

    workflow_config = {
        "name": request.name,
        "description": request.description,
        "version": request.version,
        "steps": request.steps,
        "metadata": request.metadata or {}
    }

    try:
        filepath = workflow_manager.save_workflow(workflow_config)
        return {
            "status": "updated",
            "workflow_name": request.name,
            "filepath": filepath
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update workflow: {str(e)}")


@app.delete("/api/workflows/{workflow_name}", tags=["workflows"], summary="Delete a workflow")
async def delete_workflow(workflow_name: str):
    """Delete a workflow definition"""
    success = workflow_manager.delete_workflow(workflow_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")

    return {
        "status": "deleted",
        "workflow_name": workflow_name
    }


@app.get("/api/executions/{execution_id}", tags=["workflows"], summary="Get execution status")
async def get_execution_status(execution_id: str):
    """Get the status and results of a workflow execution"""
    if execution_id not in executions:
        raise HTTPException(status_code=404, detail=f"Execution '{execution_id}' not found")

    execution = executions[execution_id]
    return execution.to_dict()


@app.get("/api/executions", tags=["workflows"], summary="List recent executions")
async def list_executions(limit: int = 20):
    """List recent workflow executions"""
    recent = sorted(
        executions.values(),
        key=lambda e: e.start_time,
        reverse=True
    )[:limit]

    return {
        "count": len(recent),
        "executions": [e.to_dict() for e in recent]
    }


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    global orchestrator

    print(f"Starting Backoffice API...")
    print(f"Workflows (runtime): {WORKFLOWS_DIR}")
    print(f"Workflows (examples): {WORKFLOWS_EXAMPLES_DIR}")
    print(f"Agent definitions directory: {AGENT_DEFINITIONS_DIR}")
    print(f"Compose directory: {COMPOSE_DIR}")
    print(f"Examples directory: {EXAMPLES_DIR}")

    # Ensure directories exist
    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
    AGENT_DEFINITIONS_DIR.mkdir(parents=True, exist_ok=True)
    COMPOSE_DIR.mkdir(parents=True, exist_ok=True)

    # Discover plugins
    print(f"\n🔌 Discovering plugins...")
    plugin_count = plugin_registry.discover_all()
    print(f"✓ Discovered {plugin_count} plugins")

    # List discovered plugins
    for plugin_id, plugin_data in plugin_registry.list_all().items():
        manifest = plugin_data.get("manifest")
        if manifest:
            print(f"  • {plugin_id} - {manifest.get('name', plugin_id)} v{manifest.get('version', '1.0.0')}")
        else:
            print(f"  • {plugin_id} (no manifest)")

    # Initialize orchestrator with discovered plugins
    agent_registry_legacy = plugin_registry.to_legacy_registry()
    orchestrator = WorkflowOrchestrator(agent_registry_legacy)
    print(f"✓ Orchestrator initialized with {len(agent_registry_legacy)} agents\n")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await orchestrator.close()


# ============================================================================
# Static Files (Frontend)
# ============================================================================

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
