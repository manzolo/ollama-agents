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

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
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
# Other paths
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", "/app/frontend"))

# Detect standalone mode
STANDALONE_MODE = os.getenv("STANDALONE_MODE", "false").lower() == "true"
DEFAULT_PROJECT_ROOT = "/app" if STANDALONE_MODE else "/project"
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", DEFAULT_PROJECT_ROOT))

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
    ollama_host: str = Field("http://ollama:11434", description="Ollama server URL for this agent")
    model: str = Field("llama3.2", description="Model to use")
    temperature: float = Field(0.7, description="Temperature (0.0-1.0)", ge=0.0, le=1.0)
    max_tokens: int = Field(4096, description="Max tokens", ge=256, le=32768)
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    system_prompt: str = Field(..., description="System prompt for the agent")


class AgentUpdateRequest(BaseModel):
    """Request to update an existing agent"""
    name: str = Field(..., description="Agent name (alphanumeric with hyphens)", pattern="^[a-z0-9-]+$")
    description: str = Field(..., description="Agent description")
    port: int = Field(..., description="Port number (7000-7999)", ge=7000, le=7999)
    ollama_host: str = Field("http://ollama:11434", description="Ollama server URL for this agent")
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


@app.get("/api/config", tags=["system"], summary="Get system configuration")
async def get_config():
    """
    Get system configuration defaults for the frontend.
    Returns default values from environment variables.
    """
    return {
        "ollama_host": os.getenv("OLLAMA_HOST", "http://ollama:11434"),
        "default_model": os.getenv("DEFAULT_MODEL", "llama3.2"),
        "default_temperature": float(os.getenv("DEFAULT_TEMPERATURE", "0.7")),
        "default_max_tokens": int(os.getenv("DEFAULT_MAX_TOKENS", "4096")),
        "backoffice_port": int(os.getenv("BACKOFFICE_PORT", "8080"))
    }


@app.get("/api/models", tags=["ollama"], summary="Get available Ollama models")
async def get_available_models(ollama_host: Optional[str] = None):
    """
    Get list of available models from Ollama server.

    Args:
        ollama_host: Optional Ollama host URL (defaults to OLLAMA_HOST env var)

    Returns:
        List of model information including name, size, and modification date
    """
    try:
        # Use provided host or fallback to environment variable
        if not ollama_host:
            ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434")

        # Normalize host URL (ensure it starts with http:// or https://)
        if not ollama_host.startswith(("http://", "https://")):
            ollama_host = f"http://{ollama_host}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{ollama_host}/api/tags")
            response.raise_for_status()
            data = response.json()

            # Extract and format model information
            models = []
            for model in data.get("models", []):
                models.append({
                    "name": model.get("name", "").replace(":latest", ""),
                    "full_name": model.get("name", ""),
                    "size": model.get("size", 0),
                    "size_gb": round(model.get("size", 0) / (1024**3), 2),
                    "modified_at": model.get("modified_at", ""),
                    "family": model.get("details", {}).get("family", ""),
                    "parameter_size": model.get("details", {}).get("parameter_size", ""),
                    "quantization": model.get("details", {}).get("quantization_level", "")
                })

            return {
                "status": "success",
                "models": models,
                "count": len(models),
                "ollama_host": ollama_host
            }

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to Ollama server at {ollama_host}: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching models from {ollama_host}: {str(e)}"
        )


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
            ollama_host=request.ollama_host,
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


@app.get("/api/agents/{agent_name}/definition", tags=["agents"], summary="Get agent definition for editing")
async def get_agent_definition_for_edit(agent_name: str):
    """
    Get the full agent definition for editing.
    
    Returns the agent definition from the YAML file, formatted for the edit form.
    """
    try:
        definition = agent_manager.get_agent_definition(agent_name)
        if not definition:
            raise HTTPException(
                status_code=404,
                detail=f"Agent definition '{agent_name}' not found"
            )
        
        # Transform the YAML structure to match the form fields
        # The agent definition YAML might not have the host if it's an old file.
        # So, we'll get it from the definition, but fall back to the global env var.
        global_ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434")
        ollama_host = definition.get("deployment", {}).get("ollama_host", global_ollama_host)

        return {
            "name": definition["agent"]["name"],
            "description": definition["agent"].get("description", ""),
            "port": definition["deployment"]["port"],
            "ollama_host": ollama_host,
            "model": definition["deployment"]["model"],
            "temperature": definition["deployment"]["temperature"],
            "max_tokens": definition["deployment"]["max_tokens"],
            "capabilities": definition.get("capabilities", []),
            "system_prompt": definition.get("system_prompt", "")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load agent definition: {str(e)}"
        )


@app.put("/api/agents/{agent_name}", tags=["agents"], summary="Update an existing agent")
async def update_agent(agent_name: str, request: AgentUpdateRequest):
    """
    Update an existing agent definition.
    
    This endpoint updates the agent definition file. If the agent is currently
    deployed, it will need to be redeployed for changes to take effect.
    
    Note: The agent name cannot be changed. To rename an agent, create a new one.
    """
    # Verify the name matches
    if agent_name != request.name:
        raise HTTPException(
            status_code=400,
            detail="Agent name in URL must match name in request body"
        )
    
    try:
        # Check if definition exists
        existing = agent_manager.get_agent_definition(agent_name)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Agent definition '{agent_name}' not found"
            )
        
        # Create updated agent definition
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
        
        # Update the definition
        definition_file = agent_manager.update_agent_definition(agent_def)
        
        return {
            "status": "updated",
            "agent_name": request.name,
            "message": f"Agent definition updated successfully!",
            "details": {
                "definition_file": definition_file,
                "port": request.port,
                "model": request.model
            },
            "note": "If the agent is currently deployed, redeploy it for changes to take effect."
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update agent definition: {str(e)}"
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

        # Use configurable model with fallback options
        # Allow user to specify model via PROMPT_MODEL env var, or try common variations
        preferred_model = os.getenv("PROMPT_MODEL", None)
        model_variations = [
            preferred_model,
            "llama3.2",
            "llama3:latest",
            "llama3.2:latest",
            "llama3",
            "llama2"
        ] if preferred_model else [
            "llama3.2",
            "llama3:latest",
            "llama3.2:latest",
            "llama3",
            "llama2"
        ]

        # Use longer timeout for CPU mode (5 minutes) vs GPU (2 minutes)
        # Check for GPU mode via OLLAMA_GPU env var or default to longer timeout
        is_gpu = os.getenv("OLLAMA_GPU", "false").lower() == "true"
        timeout = 120.0 if is_gpu else 300.0
        print(f"Using timeout of {timeout}s for prompt generation ({'GPU' if is_gpu else 'CPU'} mode)")

        last_error = None
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Try each model variation until one works
            for model in model_variations:
                if not model:  # Skip None values
                    continue

                try:
                    print(f"Attempting prompt generation with model: {model}")
                    response = await client.post(
                        f"{ollama_host}/api/generate",
                        json={
                            "model": model,
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

                    print(f"✓ Successfully generated prompt using model: {model}")
                    return {
                        "status": "success",
                        "generated_prompt": generated_prompt.strip(),
                        "message": f"Prompt generated successfully using {model}! Review and edit as needed.",
                        "model_used": model
                    }
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        print(f"Model '{model}' not found, trying next...")
                        last_error = e
                        continue  # Try next model
                    else:
                        raise  # Other HTTP errors should be raised
                except Exception as e:
                    last_error = e
                    continue  # Try next model

            # If we get here, none of the models worked
            raise Exception(
                f"None of the attempted models are available on {ollama_host}. "
                f"Tried: {', '.join([m for m in model_variations if m])}. "
                f"Set PROMPT_MODEL env var to specify a different model, or install one of: llama3.2, llama3"
            )

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

# Serve frontend static files (CSS, JS, etc.) but not HTML to avoid intercepting API routes
# The root endpoint at "/" already handles serving index.html
if FRONTEND_DIR.exists():
    # Mount static files at /static to avoid conflicts with API routes
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# ============================================================================
# ============================================================================
# Import/Export Endpoints
# ============================================================================

@app.get("/api/agents/{agent_name}/export", tags=["agents"], summary="Export agent as ZIP bundle")
async def export_agent(agent_name: str):
    """
    Export a complete agent bundle as a ZIP file containing:
    - Agent definition YAML
    - Docker compose service definition
    - Environment file
    - Agent-specific files (prompt.txt, config.yml, etc.)
    - Plugin manifest (if exists)
    """
    import tempfile
    import zipfile
    import shutil
    from pathlib import Path as PathlibPath
    
    # Get agent definition
    definition = agent_manager.get_agent_definition(agent_name)
    if not definition:
        debug_info = f"Looking in: {agent_manager.definitions_dir}. Files found: {[f.name for f in agent_manager.definitions_dir.glob('*.yml')]}"
        print(f"DEBUG: {debug_info}")
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found. {debug_info}")

    # Create temporary directory for bundle
    temp_dir = tempfile.mkdtemp(prefix=f"agent_export_{agent_name}_")
    zip_path = None
    
    try:
        bundle_dir = PathlibPath(temp_dir) / agent_name
        bundle_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Save agent definition YAML
        agent_def_content = yaml.dump(definition, default_flow_style=False, sort_keys=False)
        (bundle_dir / "agent.yml").write_text(agent_def_content)
        
        # 2. Find and copy docker-compose service definition
        compose_paths = [
            PROJECT_ROOT / "runtime" / "compose" / f"{agent_name}.yml",
            PROJECT_ROOT / "examples" / "compose" / f"{agent_name}.yml"
        ]
        for compose_path in compose_paths:
            if compose_path.exists():
                shutil.copy2(compose_path, bundle_dir / "docker-compose.yml")
                break
        
        # 3. Find and copy environment file
        env_paths = [
            PROJECT_ROOT / "runtime" / "compose" / f".env.{agent_name}",
            PROJECT_ROOT / "examples" / "compose" / f".env.{agent_name}"
        ]
        for env_path in env_paths:
            if env_path.exists():
                shutil.copy2(env_path, bundle_dir / ".env")
                break
        
        # 4. Copy agent-specific files from agent directory
        agent_dir_paths = [
            PROJECT_ROOT / "agents" / agent_name,
            PROJECT_ROOT / "runtime" / "agents" / agent_name,
            PROJECT_ROOT / "examples" / "agents" / agent_name
        ]
        
        for agent_dir in agent_dir_paths:
            if agent_dir.exists() and agent_dir.is_dir():
                # Copy all files from agent directory
                for item in agent_dir.iterdir():
                    if item.is_file():
                        shutil.copy2(item, bundle_dir / item.name)
                break
        
        # 5. Create README with import instructions
        readme_content = f"""# Agent Bundle: {agent_name}

This bundle contains all files needed to deploy the '{agent_name}' agent.

## Contents

- `agent.yml` - Agent definition
- `docker-compose.yml` - Docker service configuration (if available)
- `.env` - Environment variables (if available)
- Additional agent-specific files (prompt.txt, config.yml, plugin.yml, etc.)

## Import Instructions

1. Go to the Backoffice UI
2. Navigate to the Agents tab
3. Click "Import Agent"
4. Select this ZIP file
5. Choose whether to overwrite if the agent already exists
6. Deploy the agent after import

## Manual Import

Alternatively, you can manually extract this bundle:

1. Extract to `runtime/agents/{agent_name}/`
2. Copy `agent.yml` to `runtime/agent-definitions/{agent_name}.yml`
3. Copy `docker-compose.yml` to `runtime/compose/{agent_name}.yml`
4. Copy `.env` to `runtime/compose/.env.{agent_name}`
5. Use the backoffice to deploy the agent

---
Exported: {datetime.now().isoformat()}
"""
        (bundle_dir / "README.md").write_text(readme_content)
        
        # Create ZIP archive
        zip_path = PathlibPath(temp_dir) / f"{agent_name}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in bundle_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(bundle_dir.parent)
                    zipf.write(file_path, arcname)
        
        # Return ZIP file
        return FileResponse(
            path=str(zip_path),
            media_type="application/zip",
            filename=f"{agent_name}.zip",
            headers={
                "Content-Disposition": f"attachment; filename={agent_name}.zip"
            }
        )
    
    except Exception as e:
        # Clean up on error
        if temp_dir and PathlibPath(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
    
    finally:
        # Note: We can't clean up temp_dir here because FileResponse needs the file
        # The file will be cleaned up by the OS eventually
        pass


@app.post("/api/agents/import", tags=["agents"], summary="Import agent from ZIP bundle")
async def import_agent(
    file: UploadFile = File(...),
    overwrite: bool = Form(False)
):
    """
    Import a complete agent bundle from a ZIP file.
    Extracts and validates all files, then creates the agent structure.
    """
    import tempfile
    import zipfile
    import shutil
    from pathlib import Path as PathlibPath
    
    # Validate file type
    if not file.filename.endswith('.zip'):
        # Try to support legacy YAML imports
        if file.filename.endswith('.yml') or file.filename.endswith('.yaml'):
            try:
                content = await file.read()
                definition = yaml.safe_load(content)

                # Basic validation
                if "agent" not in definition or "name" not in definition["agent"]:
                    raise HTTPException(status_code=400, detail="Invalid agent definition: missing agent name")

                agent_name = definition["agent"]["name"]
                
                # Check if exists
                existing = agent_manager.get_agent_definition(agent_name)
                if existing and not overwrite:
                    raise HTTPException(
                        status_code=409, 
                        detail=f"Agent '{agent_name}' already exists. Set overwrite=true to replace."
                    )

                # Save definition (legacy YAML-only import)
                filepath = agent_manager.definitions_dir / f"{agent_name}.yml"
                with open(filepath, "w") as f:
                    yaml.dump(definition, f, default_flow_style=False, sort_keys=False)

                return {
                    "status": "success",
                    "message": f"Agent '{agent_name}' imported successfully (YAML only - no additional files)",
                    "agent_name": agent_name,
                    "files_imported": ["agent.yml"]
                }

            except yaml.YAMLError as e:
                raise HTTPException(status_code=400, detail=f"Invalid YAML file: {str(e)}")
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
        else:
            raise HTTPException(status_code=400, detail="File must be a ZIP bundle or YAML file")
    
    # Create temporary directory for extraction
    temp_dir = tempfile.mkdtemp(prefix="agent_import_")
    
    try:
        # Save uploaded file
        zip_path = PathlibPath(temp_dir) / file.filename
        with open(zip_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Validate ZIP file size (max 50MB)
        if zip_path.stat().st_size > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="ZIP file too large (max 50MB)")
        
        # Extract ZIP
        extract_dir = PathlibPath(temp_dir) / "extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            # Validate ZIP structure - prevent path traversal
            for member in zipf.namelist():
                if member.startswith('/') or '..' in member:
                    raise HTTPException(status_code=400, detail=f"Invalid ZIP structure: unsafe path '{member}'")
            
            zipf.extractall(extract_dir)
        
        # Find agent.yml in extracted files
        agent_yml_candidates = list(extract_dir.rglob("agent.yml"))
        if not agent_yml_candidates:
            raise HTTPException(status_code=400, detail="Invalid bundle: agent.yml not found")
        
        agent_yml_path = agent_yml_candidates[0]
        bundle_root = agent_yml_path.parent
        
        # Load and validate agent definition
        with open(agent_yml_path, 'r') as f:
            definition = yaml.safe_load(f)
        
        if "agent" not in definition or "name" not in definition["agent"]:
            raise HTTPException(status_code=400, detail="Invalid agent definition: missing agent name")
        
        agent_name = definition["agent"]["name"]
        
        # Sanitize agent name to prevent path injection
        if not agent_name.replace('-', '').replace('_', '').isalnum():
            raise HTTPException(status_code=400, detail=f"Invalid agent name: '{agent_name}' contains unsafe characters")
        
        # Check if exists
        existing = agent_manager.get_agent_definition(agent_name)
        if existing and not overwrite:
            raise HTTPException(
                status_code=409, 
                detail=f"Agent '{agent_name}' already exists. Set overwrite=true to replace."
            )
        
        # Track imported files
        imported_files = []
        
        # 1. Create agent directory structure
        runtime_agent_dir = PROJECT_ROOT / "runtime" / "agents" / agent_name
        runtime_agent_dir.mkdir(parents=True, exist_ok=True)
        
        # 2. Copy agent-specific files to agent directory
        for item in bundle_root.iterdir():
            if item.is_file() and item.name not in ["agent.yml", "docker-compose.yml", ".env", "README.md"]:
                dest = runtime_agent_dir / item.name
                shutil.copy2(item, dest)
                imported_files.append(f"agents/{agent_name}/{item.name}")
        
        # 3. Save agent definition
        agent_def_path = PROJECT_ROOT / "runtime" / "agent-definitions" / f"{agent_name}.yml"
        agent_def_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(agent_yml_path, agent_def_path)
        imported_files.append(f"agent-definitions/{agent_name}.yml")
        
        # 4. Save docker-compose service definition if exists
        compose_file = bundle_root / "docker-compose.yml"
        if compose_file.exists():
            compose_dest = PROJECT_ROOT / "runtime" / "compose" / f"{agent_name}.yml"
            compose_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(compose_file, compose_dest)
            imported_files.append(f"compose/{agent_name}.yml")
        
        # 5. Save environment file if exists
        env_file = bundle_root / ".env"
        if env_file.exists():
            env_dest = PROJECT_ROOT / "runtime" / "compose" / f".env.{agent_name}"
            shutil.copy2(env_file, env_dest)
            imported_files.append(f"compose/.env.{agent_name}")
        
        return {
            "status": "success",
            "message": f"Agent '{agent_name}' imported successfully",
            "agent_name": agent_name,
            "files_imported": imported_files,
            "note": "Agent definition imported. Use the Deploy button to start the agent."
        }

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML in bundle: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
    
    finally:
        # Clean up temporary directory
        if temp_dir and PathlibPath(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


@app.get("/api/workflows/{workflow_name}/export", tags=["workflows"], summary="Export workflow as ZIP bundle")
async def export_workflow(workflow_name: str):
    """
    Export a workflow bundle as a ZIP file containing:
    - Workflow definition YAML
    - README with import instructions
    """
    import tempfile
    import zipfile
    import shutil
    from pathlib import Path as PathlibPath
    
    workflow = workflow_manager.load_workflow(workflow_name)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")

    # Create temporary directory for bundle
    temp_dir = tempfile.mkdtemp(prefix=f"workflow_export_{workflow_name}_")
    
    try:
        bundle_dir = PathlibPath(temp_dir) / workflow_name
        bundle_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Get workflow YAML content
        filepath = workflow_manager.workflows_dir / f"{workflow_name}.yml"
        if not filepath.exists() and workflow_manager.examples_dir:
            filepath = workflow_manager.examples_dir / f"{workflow_name}.yml"
        
        if filepath.exists():
            with open(filepath, "r") as f:
                yaml_content = f.read()
        else:
            # Fallback: construct from object
            data = {
                "name": workflow.name,
                "description": workflow.description,
                "version": workflow.version,
                "steps": [
                    {
                        "name": step.name,
                        "agent": step.agent,
                        "input": step.input_source,
                    } for step in workflow.steps
                ]
            }
            yaml_content = yaml.dump(data, default_flow_style=False, sort_keys=False)
        
        # Save workflow YAML
        (bundle_dir / "workflow.yml").write_text(yaml_content)
        
        # 2. Create README with import instructions
        readme_content = f"""# Workflow Bundle: {workflow_name}

This bundle contains the workflow definition for '{workflow_name}'.

## Contents

- `workflow.yml` - Workflow definition

## Import Instructions

1. Go to the Backoffice UI
2. Navigate to the Workflows tab
3. Click "Import Workflow"
4. Select this ZIP file
5. Choose whether to overwrite if the workflow already exists
6. Execute the workflow from the Execute tab

## Manual Import

Alternatively, you can manually extract this bundle:

1. Extract to `runtime/workflows/{workflow_name}.yml`
2. Reload workflows in the backoffice

---
Exported: {datetime.now().isoformat()}
"""
        (bundle_dir / "README.md").write_text(readme_content)
        
        # Create ZIP archive
        zip_path = PathlibPath(temp_dir) / f"{workflow_name}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in bundle_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(bundle_dir.parent)
                    zipf.write(file_path, arcname)
        
        # Return ZIP file
        return FileResponse(
            path=str(zip_path),
            media_type="application/zip",
            filename=f"{workflow_name}.zip",
            headers={
                "Content-Disposition": f"attachment; filename={workflow_name}.zip"
            }
        )
    
    except Exception as e:
        # Clean up on error
        if temp_dir and PathlibPath(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@app.post("/api/workflows/import", tags=["workflows"], summary="Import workflow from ZIP bundle")
async def import_workflow(
    file: UploadFile = File(...),
    overwrite: bool = Form(False)
):
    """
    Import a workflow bundle from a ZIP file.
    """
    import tempfile
    import zipfile
    import shutil
    from pathlib import Path as PathlibPath
    
    # Validate file type
    if not file.filename.endswith('.zip'):
        # Try to support legacy YAML imports
        if file.filename.endswith('.yml') or file.filename.endswith('.yaml'):
            try:
                content = await file.read()
                definition = yaml.safe_load(content)

                # Basic validation
                if "name" not in definition or "steps" not in definition:
                    raise HTTPException(status_code=400, detail="Invalid workflow definition: missing name or steps")

                workflow_name = definition["name"]
                
                # Check if exists
                existing_path = workflow_manager.workflows_dir / f"{workflow_name}.yml"
                if existing_path.exists() and not overwrite:
                    raise HTTPException(
                        status_code=409, 
                        detail=f"Workflow '{workflow_name}' already exists. Set overwrite=true to replace."
                    )

                # Save using manager (legacy YAML-only import)
                workflow_manager.save_workflow(definition)

                return {
                    "status": "success",
                    "message": f"Workflow '{workflow_name}' imported successfully (YAML only)",
                    "workflow_name": workflow_name,
                    "files_imported": ["workflow.yml"]
                }

            except yaml.YAMLError as e:
                raise HTTPException(status_code=400, detail=f"Invalid YAML file: {str(e)}")
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
        else:
            raise HTTPException(status_code=400, detail="File must be a ZIP bundle or YAML file")
    
    # Create temporary directory for extraction
    temp_dir = tempfile.mkdtemp(prefix="workflow_import_")
    
    try:
        # Save uploaded file
        zip_path = PathlibPath(temp_dir) / file.filename
        with open(zip_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Validate ZIP file size (max 50MB)
        if zip_path.stat().st_size > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="ZIP file too large (max 50MB)")
        
        # Extract ZIP
        extract_dir = PathlibPath(temp_dir) / "extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            # Validate ZIP structure - prevent path traversal
            for member in zipf.namelist():
                if member.startswith('/') or '..' in member:
                    raise HTTPException(status_code=400, detail=f"Invalid ZIP structure: unsafe path '{member}'")
            
            zipf.extractall(extract_dir)
        
        # Find workflow.yml in extracted files
        workflow_yml_candidates = list(extract_dir.rglob("workflow.yml"))
        if not workflow_yml_candidates:
            raise HTTPException(status_code=400, detail="Invalid bundle: workflow.yml not found")
        
        workflow_yml_path = workflow_yml_candidates[0]
        
        # Load and validate workflow definition
        with open(workflow_yml_path, 'r') as f:
            definition = yaml.safe_load(f)
        
        if "name" not in definition or "steps" not in definition:
            raise HTTPException(status_code=400, detail="Invalid workflow definition: missing name or steps")
        
        workflow_name = definition["name"]
        
        # Sanitize workflow name
        if not workflow_name.replace('-', '').replace('_', '').isalnum():
            raise HTTPException(status_code=400, detail=f"Invalid workflow name: '{workflow_name}' contains unsafe characters")
        
        # Check if exists
        existing_path = workflow_manager.workflows_dir / f"{workflow_name}.yml"
        if existing_path.exists() and not overwrite:
            raise HTTPException(
                status_code=409, 
                detail=f"Workflow '{workflow_name}' already exists. Set overwrite=true to replace."
            )
        
        # Save using manager
        workflow_manager.save_workflow(definition)
        
        return {
            "status": "success",
            "message": f"Workflow '{workflow_name}' imported successfully",
            "workflow_name": workflow_name,
            "files_imported": [f"workflows/{workflow_name}.yml"]
        }

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML in bundle: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
    
    finally:
        # Clean up temporary directory
        if temp_dir and PathlibPath(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


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
