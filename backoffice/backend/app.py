#!/usr/bin/env python3
"""
Backoffice API Server
Provides REST API for managing agents and executing workflows.
"""

import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn

from orchestrator import WorkflowOrchestrator, WorkflowManager, Workflow


# ============================================================================
# Configuration
# ============================================================================
WORKFLOWS_DIR = Path(os.getenv("WORKFLOWS_DIR", "/app/workflows"))
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", "/app/frontend"))

# Agent Registry - Maps agent names to their internal URLs
AGENT_REGISTRY = {
    "swarm-converter": os.getenv("SWARM_CONVERTER_URL", "http://agent-swarm-converter:8000"),
    "swarm-validator": os.getenv("SWARM_VALIDATOR_URL", "http://agent-swarm-validator:8000"),
}


# ============================================================================
# Data Models
# ============================================================================
class WorkflowExecuteRequest(BaseModel):
    """Request to execute a workflow"""
    workflow_name: str = Field(..., description="Name of the workflow to execute")
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
workflow_manager = WorkflowManager(WORKFLOWS_DIR)
orchestrator = WorkflowOrchestrator(AGENT_REGISTRY)

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
        "workflows_dir": str(WORKFLOWS_DIR),
        "registered_agents": len(AGENT_REGISTRY)
    }


# ============================================================================
# Agent Endpoints
# ============================================================================

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
    """
    agents = await orchestrator.discover_agents()
    return {
        "count": len(agents),
        "agents": agents
    }


@app.get("/api/agents/{agent_name}", tags=["agents"], summary="Get agent details")
async def get_agent_details(agent_name: str):
    """Get detailed information about a specific agent"""
    if agent_name not in AGENT_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    agents = await orchestrator.discover_agents()
    if agent_name not in agents:
        raise HTTPException(status_code=503, detail=f"Agent '{agent_name}' is unavailable")

    return agents[agent_name]


@app.post("/api/agents/test", tags=["agents"], summary="Test an agent")
async def test_agent(request: AgentTestRequest):
    """
    Test an agent with sample input.

    This endpoint allows you to quickly test if an agent is working correctly
    by sending it test input and seeing the response.
    """
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


@app.post("/api/workflows/execute", tags=["workflows"], summary="Execute a workflow")
async def execute_workflow(request: WorkflowExecuteRequest):
    """
    Execute a workflow with the given input.

    The workflow will be executed asynchronously and return immediately with
    an execution ID. Use the execution ID to check the status and results.
    """
    # Load workflow
    workflow = workflow_manager.load_workflow(request.workflow_name)
    if not workflow:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{request.workflow_name}' not found"
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
    print(f"Starting Backoffice API...")
    print(f"Workflows directory: {WORKFLOWS_DIR}")
    print(f"Registered agents: {list(AGENT_REGISTRY.keys())}")

    # Ensure workflows directory exists
    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)


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
