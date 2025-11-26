#!/usr/bin/env python3
"""
Dynamic Workflow Orchestrator
Executes multi-agent workflows defined in YAML configuration files.
"""

import httpx
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import asyncio
import json


class WorkflowStep:
    """Represents a single step in a workflow"""

    def __init__(self, config: Dict[str, Any]):
        self.name = config.get("name", "unnamed-step")
        self.agent = config.get("agent")
        self.agent_url = config.get("agent_url")
        self.input_source = config.get("input", "previous")  # 'previous', 'original', or direct value
        self.transform = config.get("transform")  # Optional transformation
        self.condition = config.get("condition")  # Optional conditional execution
        self.timeout = config.get("timeout", 300)
        self.retry = config.get("retry", 0)
        self.on_error = config.get("on_error", "stop")  # 'stop', 'continue', 'skip'

    def __repr__(self):
        return f"WorkflowStep(name={self.name}, agent={self.agent})"


class Workflow:
    """Represents a complete workflow definition"""

    def __init__(self, config: Dict[str, Any]):
        self.name = config.get("name", "unnamed-workflow")
        self.description = config.get("description", "")
        self.version = config.get("version", "1.0.0")
        self.steps = [WorkflowStep(step) for step in config.get("steps", [])]
        self.metadata = config.get("metadata", {})

    @classmethod
    def from_file(cls, filepath: Path) -> "Workflow":
        """Load workflow from YAML file"""
        with open(filepath, "r") as f:
            config = yaml.safe_load(f)
        return cls(config)

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "Workflow":
        """Create workflow from dictionary"""
        return cls(config)

    def __repr__(self):
        return f"Workflow(name={self.name}, steps={len(self.steps)})"


class WorkflowExecution:
    """Tracks the execution of a workflow"""

    def __init__(self, workflow: Workflow, initial_input: str):
        self.workflow = workflow
        self.initial_input = initial_input
        self.execution_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.status = "pending"  # pending, running, completed, failed
        self.current_step_index = -1
        self.step_results = []
        self.error = None
        self.start_time = None
        self.end_time = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert execution state to dictionary"""
        duration = None
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()

        return {
            "execution_id": self.execution_id,
            "workflow_name": self.workflow.name,
            "status": self.status,
            "current_step": self.current_step_index + 1,
            "total_steps": len(self.workflow.steps),
            "step_results": self.step_results,
            "error": self.error,
            "duration_seconds": duration,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }


class WorkflowOrchestrator:
    """Orchestrates workflow execution across multiple agents"""

    def __init__(self, agent_registry: Dict[str, str] = None):
        """
        Initialize orchestrator

        Args:
            agent_registry: Dictionary mapping agent names to their URLs
                           e.g., {"swarm-converter": "http://agent-swarm-converter:8000"}
        """
        self.agent_registry = agent_registry or {}
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(300.0))

    async def discover_agents(self) -> Dict[str, Any]:
        """
        Discover available agents by checking their health endpoints

        Returns:
            Dictionary of agent info: {name: {url, status, capabilities}}
        """
        discovered = {}

        for agent_name, agent_url in self.agent_registry.items():
            try:
                response = await self.client.get(f"{agent_url}/health")
                if response.status_code == 200:
                    health = response.json()

                    # Get additional info
                    try:
                        info_response = await self.client.get(f"{agent_url}/info")
                        info = info_response.json() if info_response.status_code == 200 else {}
                    except:
                        info = {}

                    discovered[agent_name] = {
                        "url": agent_url,
                        "status": health.get("status", "unknown"),
                        "model": health.get("model", "unknown"),
                        "capabilities": info.get("capabilities", []),
                        "description": info.get("config", {}).get("agent", {}).get("description", "")
                    }
            except Exception as e:
                discovered[agent_name] = {
                    "url": agent_url,
                    "status": "unavailable",
                    "error": str(e)
                }

        return discovered

    async def call_agent(
        self,
        agent_name: str,
        input_text: str,
        agent_url: Optional[str] = None,
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Call an agent and get the response

        Args:
            agent_name: Name of the agent to call
            input_text: Input text to send to the agent
            agent_url: Optional explicit agent URL (overrides registry)
            timeout: Request timeout in seconds

        Returns:
            Dictionary with 'success', 'output', 'raw_response' keys
        """
        # Determine agent URL
        url = agent_url or self.agent_registry.get(agent_name)
        if not url:
            return {
                "success": False,
                "error": f"Agent '{agent_name}' not found in registry",
                "agent": agent_name
            }

        # Call agent's /process/raw endpoint for clean output
        endpoint = f"{url}/process/raw"

        try:
            response = await self.client.post(
                endpoint,
                json={"input": input_text},
                timeout=timeout
            )
            response.raise_for_status()

            result = response.json()

            return {
                "success": True,
                "agent": agent_name,
                "output": result.get("output", ""),
                "format": result.get("format", "text"),
                "raw_response": result,
                "timestamp": result.get("timestamp", datetime.now().isoformat())
            }

        except httpx.HTTPError as e:
            return {
                "success": False,
                "agent": agent_name,
                "error": f"HTTP error: {str(e)}",
                "error_type": "http_error"
            }
        except Exception as e:
            return {
                "success": False,
                "agent": agent_name,
                "error": f"Unexpected error: {str(e)}",
                "error_type": "unexpected_error"
            }

    def _get_step_input(
        self,
        step: WorkflowStep,
        initial_input: str,
        previous_output: Optional[str],
        step_results: List[Dict[str, Any]]
    ) -> str:
        """
        Determine the input for a workflow step based on its configuration

        Args:
            step: The workflow step
            initial_input: The original workflow input
            previous_output: Output from the previous step
            step_results: List of all previous step results

        Returns:
            Input text for this step
        """
        if isinstance(step.input_source, str):
            if step.input_source == "original":
                return initial_input
            elif step.input_source == "previous":
                return previous_output or initial_input
            elif step.input_source.startswith("step["):
                # Reference a specific step by index, e.g., "step[0]"
                try:
                    index = int(step.input_source[5:-1])
                    if 0 <= index < len(step_results):
                        return step_results[index].get("output", "")
                except (ValueError, IndexError):
                    pass
                return initial_input
            else:
                # Direct string value
                return step.input_source
        else:
            # Assume it's a direct value
            return str(step.input_source)

    async def execute_workflow(
        self,
        workflow: Workflow,
        initial_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> WorkflowExecution:
        """
        Execute a workflow with the given input

        Args:
            workflow: Workflow definition to execute
            initial_input: Initial input to the workflow
            context: Optional context variables for the execution

        Returns:
            WorkflowExecution object with results
        """
        execution = WorkflowExecution(workflow, initial_input)
        execution.status = "running"
        execution.start_time = datetime.now()

        current_output = initial_input

        try:
            for i, step in enumerate(workflow.steps):
                execution.current_step_index = i

                # Determine input for this step
                step_input = self._get_step_input(
                    step,
                    initial_input,
                    current_output,
                    execution.step_results
                )

                # Execute step with retry logic
                attempts = 0
                max_attempts = step.retry + 1
                step_result = None

                while attempts < max_attempts:
                    attempts += 1

                    step_result = await self.call_agent(
                        agent_name=step.agent,
                        input_text=step_input,
                        agent_url=step.agent_url,
                        timeout=step.timeout
                    )

                    if step_result.get("success"):
                        break

                    # If not successful and retries remain, wait and retry
                    if attempts < max_attempts:
                        await asyncio.sleep(2 ** attempts)  # Exponential backoff

                # Add step metadata
                step_result["step_name"] = step.name
                step_result["step_index"] = i
                step_result["attempts"] = attempts

                execution.step_results.append(step_result)

                # Handle step failure
                if not step_result.get("success"):
                    if step.on_error == "stop":
                        execution.status = "failed"
                        execution.error = f"Step '{step.name}' failed: {step_result.get('error')}"
                        execution.end_time = datetime.now()
                        return execution
                    elif step.on_error == "skip":
                        continue  # Skip to next step
                    # If 'continue', proceed to next step

                # Update current output for next step
                current_output = step_result.get("output", current_output)

            # All steps completed successfully
            execution.status = "completed"
            execution.end_time = datetime.now()

        except Exception as e:
            execution.status = "failed"
            execution.error = f"Workflow execution error: {str(e)}"
            execution.end_time = datetime.now()

        return execution

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


class WorkflowManager:
    """Manages workflow definitions and executions"""

    def __init__(self, workflows_dir: Path, examples_dir: Path = None):
        # Primary directory for user workflows (runtime, gitignored)
        self.workflows_dir = Path(workflows_dir)
        self.workflows_dir.mkdir(parents=True, exist_ok=True)

        # Examples directory for template workflows (git-tracked)
        self.examples_dir = Path(examples_dir) if examples_dir else None
        if self.examples_dir:
            self.examples_dir.mkdir(parents=True, exist_ok=True)

        self._workflow_cache = {}

    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all available workflows from both examples and runtime directories"""
        workflows = []
        workflow_names = set()  # Track names to avoid duplicates

        # First, scan runtime workflows (user-created, higher priority)
        for filepath in self.workflows_dir.glob("*.yml"):
            try:
                workflow = Workflow.from_file(filepath)
                workflow_names.add(workflow.name)
                workflows.append({
                    "name": workflow.name,
                    "description": workflow.description,
                    "version": workflow.version,
                    "steps": len(workflow.steps),
                    "file": filepath.name,
                    "source": "runtime"
                })
            except Exception as e:
                workflows.append({
                    "name": filepath.stem,
                    "error": f"Failed to load: {str(e)}",
                    "file": filepath.name,
                    "source": "runtime"
                })

        # Then, scan example workflows (git-tracked templates)
        if self.examples_dir:
            for filepath in self.examples_dir.glob("*.yml"):
                try:
                    workflow = Workflow.from_file(filepath)
                    # Skip if already loaded from runtime (user override)
                    if workflow.name not in workflow_names:
                        workflows.append({
                            "name": workflow.name,
                            "description": workflow.description,
                            "version": workflow.version,
                            "steps": len(workflow.steps),
                            "file": filepath.name,
                            "source": "examples"
                        })
                except Exception as e:
                    if filepath.stem not in workflow_names:
                        workflows.append({
                            "name": filepath.stem,
                            "error": f"Failed to load: {str(e)}",
                            "file": filepath.name,
                            "source": "examples"
                        })

        return workflows

    def load_workflow(self, name: str) -> Optional[Workflow]:
        """Load a workflow by name from runtime or examples directory"""
        # Check cache first
        if name in self._workflow_cache:
            return self._workflow_cache[name]

        # Try runtime directory first (user workflows take priority)
        filepath = self.workflows_dir / f"{name}.yml"
        if filepath.exists():
            workflow = Workflow.from_file(filepath)
            self._workflow_cache[name] = workflow
            return workflow

        # Fall back to examples directory
        if self.examples_dir:
            filepath = self.examples_dir / f"{name}.yml"
            if filepath.exists():
                workflow = Workflow.from_file(filepath)
                self._workflow_cache[name] = workflow
                return workflow

        return None

    def save_workflow(self, workflow_config: Dict[str, Any]) -> str:
        """Save a workflow configuration to runtime directory"""
        name = workflow_config.get("name", "unnamed")
        # Always save to runtime directory (user workflows)
        filepath = self.workflows_dir / f"{name}.yml"

        with open(filepath, "w") as f:
            yaml.dump(workflow_config, f, default_flow_style=False, sort_keys=False)

        # Clear cache for this workflow
        if name in self._workflow_cache:
            del self._workflow_cache[name]

        return str(filepath)

    def delete_workflow(self, name: str) -> bool:
        """Delete a workflow from runtime directory only (example workflows cannot be deleted)"""
        # Only delete from runtime directory - example workflows are read-only
        filepath = self.workflows_dir / f"{name}.yml"
        if filepath.exists():
            filepath.unlink()
            if name in self._workflow_cache:
                del self._workflow_cache[name]
            return True
        return False
