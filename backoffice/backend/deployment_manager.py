#!/usr/bin/env python3
"""
Deployment Manager Module
Handles automated agent deployment with Docker support.
"""

import os
import yaml
import docker
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class DeploymentManager:
    """
    Manages automated agent deployment via Docker API.
    Handles docker-compose updates, container deployment, and GPU detection.
    """

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        # Get host filesystem path for Docker mounts
        import os
        self.host_project_root = Path(os.getenv("HOST_PROJECT_ROOT", str(project_root)))
        self.docker_compose_path = self.project_root / "docker-compose.yml"
        # Directory for individual agent compose files (runtime, git-ignored)
        self.agents_compose_dir = self.project_root / "runtime" / "compose"
        self.agents_compose_dir.mkdir(parents=True, exist_ok=True)
        # Separate env files: base (git-tracked) and agents (git-ignored)
        self.env_path = self.project_root / ".env"
        self.env_agents_path = self.project_root / ".env.agents"
        # Ensure .env.agents exists with proper header
        if not self.env_agents_path.exists():
            header = """# ============================================================================
# DYNAMIC AGENT CONFIGURATIONS
# ============================================================================
# ⚠️  AUTO-MANAGED FILE - DO NOT EDIT MANUALLY
#
# This file is automatically managed by the backoffice when you:
# - Create a new agent → variables added
# - Delete an agent → variables removed
#
# This file is gitignored to keep dynamic runtime configs separate from
# the git-tracked .env file.
# ============================================================================
#
# Format for each agent:
# AGENT_NAME_PORT=7XXX
# AGENT_NAME_MODEL=llama3.2
# AGENT_NAME_TEMPERATURE=0.7
# AGENT_NAME_MAX_TOKENS=4096
# ============================================================================

# Agent configurations will appear below (auto-generated)
# ----------------------------------------------------------------------------

"""
            self.env_agents_path.write_text(header)
        # Runtime agents directory (user-created, git-ignored)
        self.agents_dir = self.project_root / "runtime" / "agents"
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        self.shared_dir = self.project_root / "shared"

        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            print(f"Warning: Could not connect to Docker: {e}")
            self.docker_client = None

    def get_compose_files(self, agent_name: str = None, include_gpu: bool = False) -> list:
        """
        Get list of compose files to use for docker compose commands.

        Args:
            agent_name: Optional specific agent name to include
            include_gpu: Whether to include GPU compose file

        Returns:
            list: List of compose file arguments for docker compose command
        """
        files = ["-f", str(self.docker_compose_path)]

        # Add specific agent compose file or all agent compose files
        if agent_name:
            agent_compose = self.agents_compose_dir / f"{agent_name}.yml"
            if agent_compose.exists():
                files.extend(["-f", str(agent_compose)])
        else:
            # Include all agent compose files
            for agent_compose in sorted(self.agents_compose_dir.glob("*.yml")):
                files.extend(["-f", str(agent_compose)])

        if include_gpu:
            gpu_compose = self.project_root / "docker-compose.gpu.yml"
            if gpu_compose.exists():
                files.extend(["-f", str(gpu_compose)])

        return files

    def _write_agent_compose_file(self, agent_name: str, agent_definition: Dict[str, Any]) -> Path:
        """
        Write a standalone docker-compose file for an agent.

        Args:
            agent_name: Name of the agent
            agent_definition: Agent configuration

        Returns:
            Path: Path to the created compose file
        """
        description = agent_definition["agent"]["description"]
        port = agent_definition["deployment"]["port"]
        model = agent_definition["deployment"]["model"]
        temperature = agent_definition["deployment"]["temperature"]
        max_tokens = agent_definition["deployment"]["max_tokens"]

        env_prefix = agent_name.upper().replace("-", "_")

        # Create a complete, standalone compose file
        # Use host filesystem paths for volume mounts (required when running docker-compose via socket)
        # But use relative path for build context (relative to where docker-compose runs)
        host_runtime_agents = self.host_project_root / "runtime" / "agents" / agent_name
        host_shared_context = self.host_project_root / "shared" / "context" / agent_name

        compose_content = f'''# ==========================================================================
# AGENT: {agent_name.upper()}
# ==========================================================================
# {description}
# Endpoint: http://localhost:{port}/process
# Auto-generated - do not edit manually
# ==========================================================================

services:
  {agent_name}:
    build:
      context: ./agents/base
      dockerfile: Dockerfile
    container_name: agent-{agent_name}
    restart: unless-stopped
    ports:
      - "${{{env_prefix}_PORT:-{port}}}:8000"
    volumes:
      - {host_runtime_agents}/prompt.txt:/app/prompt.txt:ro
      - {host_runtime_agents}/config.yml:/app/config.yml:ro
      - {host_shared_context}:/app/context
    networks:
      - agent-network
    environment:
      - AGENT_NAME={agent_name}
      - OLLAMA_HOST=http://ollama:11434
      - MODEL_NAME=${{{env_prefix}_MODEL:-{model}}}
      - TEMPERATURE=${{{env_prefix}_TEMPERATURE:-{temperature}}}
      - MAX_TOKENS=${{{env_prefix}_MAX_TOKENS:-{max_tokens}}}
    depends_on:
      ollama:
        condition: service_healthy
    healthcheck:
      test: [ "CMD", "curl", "-f", "http://localhost:8000/health" ]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s

# Use the existing network from docker-compose.yml
networks:
  agent-network:
    external: true
    name: ollama-agent-network
'''

        compose_path = self.agents_compose_dir / f"{agent_name}.yml"
        with open(compose_path, "w") as f:
            f.write(compose_content)

        return compose_path

    def detect_gpu_mode(self) -> bool:
        """
        Detect if the project was started with GPU support.
        Checks for gpu-specific compose file or NVIDIA runtime.
        """
        if not self.docker_client:
            return False

        try:
            # Check if ollama container is using GPU
            try:
                container = self.docker_client.containers.get("ollama-engine")
                # Check for NVIDIA runtime or device requests
                config = container.attrs.get("HostConfig", {})
                runtime = config.get("Runtime", "")
                device_requests = config.get("DeviceRequests", [])

                if runtime == "nvidia" or device_requests:
                    return True
            except docker.errors.NotFound:
                pass

            # Check if docker-compose.gpu.yml exists
            gpu_compose = self.project_root / "docker-compose.gpu.yml"
            return gpu_compose.exists()

        except Exception as e:
            print(f"GPU detection error: {e}")
            return False

    def create_agent_files(self, agent_definition: Dict[str, Any]) -> bool:
        """
        Create agent directory structure and configuration files.

        Args:
            agent_definition: Agent configuration from YAML definition

        Returns:
            bool: Success status
        """
        try:
            agent_name = agent_definition["agent"]["name"]

            # Create agent directory
            agent_dir = self.agents_dir / agent_name
            agent_dir.mkdir(parents=True, exist_ok=True)

            # Create context directory
            context_dir = self.shared_dir / "context" / agent_name
            context_dir.mkdir(parents=True, exist_ok=True)

            # Create config.yml
            config_data = {
                "agent": agent_definition["agent"],
                "capabilities": agent_definition.get("capabilities", []),
                "options": {
                    "temperature": agent_definition["deployment"]["temperature"],
                    "num_predict": agent_definition["deployment"]["max_tokens"],
                    "top_k": 40,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1
                }
            }

            with open(agent_dir / "config.yml", "w") as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

            # Create prompt.txt
            with open(agent_dir / "prompt.txt", "w") as f:
                f.write(agent_definition["system_prompt"])

            return True

        except Exception as e:
            print(f"Error creating agent files: {e}")
            return False

    def update_docker_compose(self, agent_definition: Dict[str, Any]) -> bool:
        """
        Create a standalone docker-compose file for the agent.

        Args:
            agent_definition: Agent configuration

        Returns:
            bool: Success status
        """
        try:
            agent_name = agent_definition["agent"]["name"]
            self._write_agent_compose_file(agent_name, agent_definition)
            return True
        except Exception as e:
            print(f"Error creating agent compose file: {e}")
            return False

    def update_env_file(self, agent_definition: Dict[str, Any]) -> bool:
        """
        Update .env.agents file with agent environment variables.
        Uses separate .env.agents file to avoid modifying git-tracked .env.

        Args:
            agent_definition: Agent configuration

        Returns:
            bool: Success status
        """
        try:
            agent_name = agent_definition["agent"]["name"]
            port = agent_definition["deployment"]["port"]
            model = agent_definition["deployment"]["model"]
            temperature = agent_definition["deployment"]["temperature"]
            max_tokens = agent_definition["deployment"]["max_tokens"]

            env_prefix = agent_name.upper().replace("-", "_")

            # Read current .env.agents
            env_content = ""
            if self.env_agents_path.exists():
                with open(self.env_agents_path, "r") as f:
                    env_content = f.read()

            # Check if already exists
            if f"{env_prefix}_PORT" in env_content:
                print(f"Agent {agent_name} already in .env.agents")
                return True

            # Append new variables to .env.agents (not .env!)
            new_env = f"\n# ----------------------------------------------------------------------------\n"
            new_env += f"# {agent_name.title().replace('-', ' ')} Agent Configuration\n"
            new_env += f"# ----------------------------------------------------------------------------\n"
            new_env += f"{env_prefix}_PORT={port}\n"
            new_env += f"{env_prefix}_MODEL={model}\n"
            new_env += f"{env_prefix}_TEMPERATURE={temperature}\n"
            new_env += f"{env_prefix}_MAX_TOKENS={max_tokens}\n"

            with open(self.env_agents_path, "a") as f:
                f.write(new_env)

            return True

        except Exception as e:
            print(f"Error updating .env.agents: {e}")
            return False

    def deploy_agent(self, agent_name: str, agent_definition: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fully deploy an agent: create files, update configs, start container.

        Args:
            agent_name: Name of the agent to deploy
            agent_definition: Agent configuration

        Returns:
            dict: Deployment result with status and details
        """
        result = {
            "status": "failed",
            "steps": [],
            "errors": []
        }

        try:
            # Step 1: Create agent files
            result["steps"].append({"step": "create_files", "status": "running"})
            if not self.create_agent_files(agent_definition):
                result["errors"].append("Failed to create agent files")
                return result
            result["steps"][-1]["status"] = "completed"

            # Step 2: Update docker-compose.yml
            result["steps"].append({"step": "update_compose", "status": "running"})
            if not self.update_docker_compose(agent_definition):
                result["errors"].append("Failed to update docker-compose.yml")
                return result
            result["steps"][-1]["status"] = "completed"

            # Step 3: Update .env
            result["steps"].append({"step": "update_env", "status": "running"})
            if not self.update_env_file(agent_definition):
                result["errors"].append("Failed to update .env")
                return result
            result["steps"][-1]["status"] = "completed"

            # Step 4: Build and start container
            if self.docker_client:
                result["steps"].append({"step": "build_container", "status": "running"})

                # Detect GPU mode
                gpu_mode = self.detect_gpu_mode()

                # Get compose files for this specific agent
                compose_files = self.get_compose_files(agent_name=agent_name, include_gpu=gpu_mode)

                # Build the service (use same project name as main compose)
                build_cmd = ["docker", "compose", "-p", "ollama-agents"] + compose_files + ["build", agent_name]
                import subprocess
                subprocess.run(build_cmd, cwd=self.project_root, check=True, capture_output=True)
                result["steps"][-1]["status"] = "completed"

                # Remove existing container if it exists (to avoid mount issues)
                try:
                    rm_cmd = ["docker", "compose", "-p", "ollama-agents"] + compose_files + ["rm", "-f", "-s", "-v", agent_name]
                    subprocess.run(rm_cmd, cwd=self.project_root, check=False, capture_output=True)
                except Exception:
                    pass  # Ignore if container doesn't exist

                # Start the service with force-recreate to avoid mount issues
                result["steps"].append({"step": "start_container", "status": "running"})
                up_cmd = ["docker", "compose", "-p", "ollama-agents"] + compose_files + ["up", "-d", "--force-recreate", agent_name]
                subprocess.run(up_cmd, cwd=self.project_root, check=True, capture_output=True)
                result["steps"][-1]["status"] = "completed"

                # Deploy completed
                result["status"] = "success"
                result["gpu_mode"] = gpu_mode
                # Refresh in‑memory agent registry so UI sees the new agent
                try:
                    import asyncio
                    # This import is likely missing, adding it here for completeness if it's used elsewhere
                    # from your_module import discover_runtime_agents, orchestrator 
                    # For now, commenting out as discover_runtime_agents and orchestrator are not defined in this snippet
                    # discovered = asyncio.run(discover_runtime_agents())
                    # orchestrator.agent_registry.clear()
                    # orchestrator.agent_registry.update({
                    #     n: i["url"] for n, i in discovered.items() if i.get("url")
                    # })
                    pass # Placeholder for actual registry refresh logic
                except Exception as e:
                    print(f"Warning: Could not refresh agent registry after deploy: {e}")
            else:
                result["errors"].append("Docker not available - files created but container not started")
                result["status"] = "partial"

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode().strip() if e.stderr else str(e)
            # Extract the actual error from docker compose output
            if "no such service" in error_msg.lower():
                result["errors"].append(f"Service '{agent_name}' not found in docker-compose.yml. The service definition may not have been added correctly. Please check docker-compose.yml.")
            else:
                result["errors"].append(f"Docker command failed: {error_msg}")
        except Exception as e:
            result["errors"].append(f"Deployment error: {str(e)}")

        return result

    def get_agent_status(self, agent_name: str) -> Dict[str, Any]:
        """
        Get the deployment status of an agent.

        Args:
            agent_name: Name of the agent

        Returns:
            dict: Status information
        """
        status = {
            "agent_name": agent_name,
            "files_exist": False,
            "in_compose": False,
            "in_env": False,
            "container_status": "not_found",
            "healthy": False
        }

        try:
            # Check if files exist
            agent_dir = self.agents_dir / agent_name
            status["files_exist"] = agent_dir.exists() and (agent_dir / "prompt.txt").exists()

            # Check if compose file exists
            compose_path = self.agents_compose_dir / f"{agent_name}.yml"
            status["in_compose"] = compose_path.exists()

            # Check if in .env
            if self.env_path.exists():
                with open(self.env_path, "r") as f:
                    content = f.read()
                    env_prefix = agent_name.upper().replace("-", "_")
                    status["in_env"] = f"{env_prefix}_PORT" in content

            # Check container status
            if self.docker_client:
                try:
                    container_name = f"agent-{agent_name}"
                    container = self.docker_client.containers.get(container_name)
                    status["container_status"] = container.status
                    status["healthy"] = container.status == "running"
                except docker.errors.NotFound:
                    status["container_status"] = "not_found"

        except Exception as e:
            status["error"] = str(e)

        return status

    def restart_agent(self, agent_name: str) -> Dict[str, Any]:
        """
        Restart an agent container.

        Args:
            agent_name: Name of the agent

        Returns:
            dict: Restart result
        """
        try:
            if not self.docker_client:
                return {"status": "error", "message": "Docker not available"}

            container_name = f"agent-{agent_name}"
            container = self.docker_client.containers.get(container_name)
            container.restart()

            return {
                "status": "success",
                "message": f"Agent {agent_name} restarted successfully"
            }
        except docker.errors.NotFound:
            return {"status": "error", "message": f"Container {container_name} not found"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def stop_agent(self, agent_name: str) -> Dict[str, Any]:
        """
        Stop an agent container.

        Args:
            agent_name: Name of the agent

        Returns:
            dict: Stop result
        """
        try:
            if not self.docker_client:
                return {"status": "error", "message": "Docker not available"}

            container_name = f"agent-{agent_name}"
            container = self.docker_client.containers.get(container_name)
            container.stop()

            return {
                "status": "success",
                "message": f"Agent {agent_name} stopped successfully"
            }
        except docker.errors.NotFound:
            return {"status": "error", "message": f"Container {container_name} not found"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def start_agent(self, agent_name: str) -> Dict[str, Any]:
        """
        Start an agent container using docker-compose.
        This will create the container if it doesn't exist, or start it if stopped.

        Args:
            agent_name: Name of the agent

        Returns:
            dict: Start result
        """
        try:
            if not self.docker_client:
                return {"status": "error", "message": "Docker not available"}

            # Check if compose file exists
            compose_path = self.agents_compose_dir / f"{agent_name}.yml"
            if not compose_path.exists():
                return {
                    "status": "error",
                    "message": f"Agent compose file not found. Please deploy the agent first."
                }

            # Detect GPU mode
            gpu_mode = self.detect_gpu_mode()

            # Get compose files for this specific agent
            compose_files = self.get_compose_files(agent_name=agent_name, include_gpu=gpu_mode)

            # Start the service using docker-compose (use same project name and force-recreate)
            import subprocess
            up_cmd = ["docker", "compose", "-p", "ollama-agents"] + compose_files + ["up", "-d", "--force-recreate", agent_name]
            result = subprocess.run(up_cmd, cwd=self.project_root, check=True, capture_output=True)

            return {
                "status": "success",
                "message": f"Agent {agent_name} started successfully"
            }
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode().strip() if e.stderr else str(e)
            return {"status": "error", "message": f"Failed to start agent: {error_msg}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def delete_agent(self, agent_name: str, remove_files: bool = True) -> Dict[str, Any]:
        """
        Completely delete an agent: stop container, remove snippet, refresh compose, and optionally delete files.
        """
        result = {
            "status": "success",
            "steps": [],
            "errors": []
        }

        try:
            # Step 1: Stop and remove container (if exists)
            if self.docker_client:
                result["steps"].append({"step": "stop_container", "status": "running"})
                container_name = f"agent-{agent_name}"
                try:
                    container = self.docker_client.containers.get(container_name)
                    container.stop(timeout=10)
                    container.remove(force=True)
                    result["steps"][-1]["status"] = "completed"
                except docker.errors.NotFound:
                    result["steps"][-1]["status"] = "skipped"
                    result["steps"][-1]["message"] = "Container not found"
                except Exception as e:
                    result["errors"].append(f"Container removal failed: {str(e)}")

            # Step 2: Remove compose file
            result["steps"].append({"step": "remove_compose_file", "status": "running"})
            compose_path = self.agents_compose_dir / f"{agent_name}.yml"
            try:
                if compose_path.exists():
                    compose_path.unlink()
                result["steps"][-1]["status"] = "completed"
            except Exception as e:
                result["errors"].append(f"Failed to remove compose file: {str(e)}")
                result["steps"][-1]["status"] = "failed"

            # Step 3: Remove from .env.agents (not .env!)
            result["steps"].append({"step": "remove_from_env", "status": "running"})
            try:
                if self.env_agents_path.exists():
                    with open(self.env_agents_path, "r") as f:
                        content = f.read()
                    env_prefix = agent_name.upper().replace("-", "_")
                    lines = content.split('\n')
                    new_lines = []
                    skip_section = False
                    for line in lines:
                        if f"# {agent_name.title().replace('-', ' ')} Agent Configuration" in line:
                            skip_section = True
                            continue
                        if skip_section:
                            if line.startswith(env_prefix) or line.startswith('#'):
                                continue
                            else:
                                skip_section = False
                        new_lines.append(line)
                    with open(self.env_agents_path, "w") as f:
                        f.write('\n'.join(new_lines))
                result["steps"][-1]["status"] = "completed"
            except Exception as e:
                result["errors"].append(f".env.agents update failed: {str(e)}")
                result["steps"][-1]["status"] = "failed"

            # Step 4: Optionally delete agent files on disk
            if remove_files:
                result["steps"].append({"step": "remove_files", "status": "running"})
                try:
                    import shutil
                    agent_dir = self.agents_dir / agent_name
                    if agent_dir.exists():
                        shutil.rmtree(agent_dir)
                    context_dir = self.shared_dir / "context" / agent_name
                    if context_dir.exists():
                        shutil.rmtree(context_dir)
                    result["steps"][-1]["status"] = "completed"
                except Exception as e:
                    result["errors"].append(f"File removal failed: {str(e)}")
                    result["steps"][-1]["status"] = "failed"

            # Final status aggregation
            if result["errors"]:
                result["status"] = "partial"
            else:
                result["status"] = "success"

        except Exception as e:
            result["status"] = "failed"
            result["errors"].append(str(e))

        return result
