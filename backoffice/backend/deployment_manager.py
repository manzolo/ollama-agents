#!/usr/bin/env python3
"""
Deployment Manager Module
Handles automated agent deployment with Docker support.
"""

import os
import yaml
import docker
import subprocess
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

        # Initialize Docker client first (needed for auto-detection)
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            print(f"Warning: Could not connect to Docker: {e}")
            self.docker_client = None

        # Get host filesystem path for Docker mounts (with auto-detection)
        import os
        self.host_project_root = self._detect_host_project_root(project_root)

        self.docker_compose_path = self.project_root / "docker-compose.yml"
        # Directory for individual agent compose files (runtime, git-ignored)
        self.agents_compose_dir = self.project_root / "runtime" / "compose"
        self.agents_compose_dir.mkdir(parents=True, exist_ok=True)
        # Note: .env.agents is no longer used - compose files have defaults from plugin.yml
        # Runtime agents directory (user-created, git-ignored)
        self.agents_dir = self.project_root / "runtime" / "agents"
        self.agents_dir.mkdir(parents=True, exist_ok=True)

        self.env_path = self.project_root / ".env"

    def _detect_host_project_root(self, project_root: Path) -> Path:
        """
        Auto-detect the host filesystem path for the project.

        This is critical because when running docker-compose via Docker socket,
        volume mounts must use the HOST machine's absolute path, not the
        container's internal path.

        Detection strategy:
        1. Check HOST_PROJECT_ROOT environment variable
        2. If not set, try to auto-detect by inspecting our own container
        3. Fall back to project_root if detection fails

        Args:
            project_root: The project root path inside the container

        Returns:
            Path: The absolute path on the host machine
        """
        import os

        # Strategy 1: Use HOST_PROJECT_ROOT if explicitly set
        env_value = os.getenv("HOST_PROJECT_ROOT")
        if env_value and env_value.strip():
            detected_path = Path(env_value)
            print(f"✓ Using HOST_PROJECT_ROOT from environment: {detected_path}")
            return detected_path

        # Strategy 2: Auto-detect by inspecting our own container
        try:
            if self.docker_client:
                # Try to get the backoffice container
                container = self.docker_client.containers.get("backoffice")

                # Look for the /project mount in the container
                mounts = container.attrs.get("Mounts", [])
                for mount in mounts:
                    # Find the mount that corresponds to our project root
                    destination = mount.get("Destination", "")
                    if destination == "/project":
                        source = mount.get("Source", "")
                        if source:
                            detected_path = Path(source)
                            print(f"✓ Auto-detected host path from container mount: {detected_path}")
                            return detected_path
        except Exception as e:
            print(f"Warning: Could not auto-detect host path from container: {e}")

        # Strategy 3: Fall back to project_root (may not work for Docker socket operations)
        print(f"⚠ Could not detect host path, using container path: {project_root}")
        print(f"⚠ This may cause issues with agent deployment. Run 'make init-env' to configure.")
        return Path(project_root)

    def get_compose_files(self, agent_name: str = None, include_gpu: bool = False) -> list:
        """
        Get list of compose files to use for docker compose commands.
        
        Returns CONTAINER filesystem paths since docker compose runs inside the container.
        The compose files themselves contain host paths for build contexts and volumes.

        Args:
            agent_name: Optional specific agent name to include
            include_gpu: Whether to include GPU compose file

        Returns:
            list: List of compose file arguments for docker compose command
        """
        # Use container paths - docker compose runs inside the container
        files = ["-f", str(self.docker_compose_path)]

        # Add Ollama service (optional, can be external)
        ollama_compose = self.project_root / "docker-compose.ollama.yml"
        if ollama_compose.exists():
            files.extend(["-f", str(ollama_compose)])

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

    def _write_agent_env_file(self, agent_name: str, agent_definition: Dict[str, Any]) -> Path:
        """
        Write a per-agent .env file with agent-specific configuration.

        Args:
            agent_name: Name of the agent
            agent_definition: Agent configuration

        Returns:
            Path: Path to the created .env file
        """
        port = agent_definition["deployment"]["port"]
        model = agent_definition["deployment"]["model"]
        temperature = agent_definition["deployment"]["temperature"]
        max_tokens = agent_definition["deployment"]["max_tokens"]
        ollama_host = agent_definition["deployment"].get("ollama_host", "http://ollama:11434")
        description = agent_definition["agent"]["description"]

        # Get global defaults from environment
        default_model = os.getenv("DEFAULT_MODEL", "llama3.2")
        default_temp = os.getenv("DEFAULT_TEMPERATURE", "0.7")
        default_tokens = os.getenv("DEFAULT_MAX_TOKENS", "4096")

        # Prepare env var lines (uncomment if different from default)
        model_line = f"MODEL_NAME={model}" if model != default_model else f"# MODEL_NAME={model}"
        
        # Handle numeric comparisons safely
        try:
            temp_changed = float(temperature) != float(default_temp)
        except (ValueError, TypeError):
            temp_changed = str(temperature) != str(default_temp)
        temp_line = f"TEMPERATURE={temperature}" if temp_changed else f"# TEMPERATURE={temperature}"

        try:
            tokens_changed = int(max_tokens) != int(default_tokens)
        except (ValueError, TypeError):
            tokens_changed = str(max_tokens) != str(default_tokens)
        tokens_line = f"MAX_TOKENS={max_tokens}" if tokens_changed else f"# MAX_TOKENS={max_tokens}"

        # Always uncomment OLLAMA_HOST if it's different from the default/inferred one
        default_host = os.getenv("OLLAMA_HOST", "http://ollama:11434")
        ollama_host_line = f"OLLAMA_HOST={ollama_host}" if ollama_host != default_host else f"# OLLAMA_HOST={ollama_host}"

        env_content = f'''# ============================================================================
# AGENT: {agent_name}
# ============================================================================
# {description}
# This file contains environment-specific configuration for the agent.
# ============================================================================

# Port to expose the agent on
PORT={port}

# Ollama model to use (optional - defaults to DEFAULT_MODEL={default_model})
# Uncomment to override the global default model
{model_line}

# Model temperature (optional - defaults to DEFAULT_TEMPERATURE={default_temp})
# Uncomment to override: 0.0 = deterministic, 1.0 = creative
{temp_line}

# Maximum tokens to generate (optional - defaults to DEFAULT_MAX_TOKENS={default_tokens})
# Uncomment to override
{tokens_line}

# Ollama host URL (optional - defaults to OLLAMA_HOST from main .env)
# Uncomment to override for this specific agent
{ollama_host_line}

# Agent name (used for logging and identification)
AGENT_NAME={agent_name}
'''

        env_path = self.agents_compose_dir / f".env.{agent_name}"
        with open(env_path, "w") as f:
            f.write(env_content)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk

        return env_path

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

        # Create a complete, standalone compose file
        # Unified Standalone Architecture: Use named volumes for portability
        # The 'runtime' is defined in the main docker-compose.yml
        # In Dev: it's bind-mounted to host directories
        # In Prod: they are standard Docker volumes
        
        # The agent service will use the pre-built base image
        compose_content = f'''# ==========================================================================
# AGENT: {agent_name.upper()}
# ==========================================================================
# {description}
# Endpoint: http://localhost:{port}/process
# Auto-generated - do not edit manually
# ==========================================================================

services:
  {agent_name}:
    image: ollama-agent-base:latest
    container_name: agent-{agent_name}
    restart: unless-stopped
    env_file:
      - runtime/compose/.env.{agent_name}
    environment:
      - AGENT_DATA_DIR=/app/runtime/agents/{agent_name}
      - CONTEXT_DIR=/app/runtime/context/{agent_name}
      # Pass through global defaults from main .env
      - DEFAULT_MODEL=${{DEFAULT_MODEL:-llama3.2}}
      - DEFAULT_TEMPERATURE=${{DEFAULT_TEMPERATURE:-0.7}}
      - DEFAULT_MAX_TOKENS=${{DEFAULT_MAX_TOKENS:-4096}}
      - OLLAMA_HOST=${{OLLAMA_HOST:-http://ollama:11434}}
    ports:
      - "{port}:8000"
    volumes:
      # Mount the runtime directory to access agent config, prompt and context
      - ./runtime:/app/runtime
    networks:
      - agent-network
    healthcheck:
      test: [ "CMD", "curl", "-f", "http://localhost:8000/health" ]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s

networks:
  agent-network:
    external: true
    name: ${{DOCKER_NETWORK_NAME:-ollama-agent-network}}
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
            context_dir = self.agents_dir.parent / "context" / agent_name
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

            config_file = agent_dir / "config.yml"
            with open(config_file, "w") as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk

            # Verify config.yml was created and is a file
            if not config_file.is_file():
                raise Exception(f"Failed to create config.yml as a file at {config_file}")

            # Create prompt.txt
            prompt_file = agent_dir / "prompt.txt"
            with open(prompt_file, "w") as f:
                f.write(agent_definition["system_prompt"])
                f.flush()
                os.fsync(f.fileno())  # Force write to disk

            # Verify prompt.txt was created and is a file
            if not prompt_file.is_file():
                raise Exception(f"Failed to create prompt.txt as a file at {prompt_file}")

            # Create plugin.yml
            plugin_data = {
                "plugin": {
                    "id": agent_name,
                    "name": agent_definition["agent"]["description"],
                    "description": agent_definition["agent"]["description"],
                    "version": agent_definition["agent"].get("version", "1.0.0"),
                    "author": "User",
                    "tags": agent_definition.get("capabilities", [])[:3],
                    "icon": "🔌"
                },
                "agent": {
                    "port": agent_definition["deployment"]["port"],
                    "model": agent_definition["deployment"]["model"],
                    "temperature": agent_definition["deployment"]["temperature"],
                    "max_tokens": agent_definition["deployment"]["max_tokens"],
                    "resources": {
                        "memory": "512M",
                        "cpu": "1.0"
                    }
                },
                "capabilities": agent_definition.get("capabilities", []),
                "api": {
                    "endpoint": "/process",
                    "input": {
                        "type": "text",
                        "format": "text",
                        "description": "Input text to process"
                    },
                    "output": {
                        "type": "text",
                        "format": "text",
                        "description": "Processed output"
                    }
                },
                "requires": {
                    "ollama": ">=0.1.0",
                    "models": [agent_definition["deployment"]["model"]]
                },
                "health": {
                    "endpoint": "/health",
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 3
                }
            }

            plugin_file = agent_dir / "plugin.yml"
            with open(plugin_file, "w") as f:
                yaml.dump(plugin_data, f, default_flow_style=False, sort_keys=False)
                f.flush()
                os.fsync(f.fileno())  # Force write to disk

            # Verify plugin.yml was created and is a file
            if not plugin_file.is_file():
                raise Exception(f"Failed to create plugin.yml as a file at {plugin_file}")

            # Final verification: ensure all required files exist and are files
            required_files = [config_file, prompt_file, plugin_file]
            for file_path in required_files:
                if not file_path.exists():
                    raise Exception(f"Required file does not exist: {file_path}")
                if not file_path.is_file():
                    raise Exception(f"Path exists but is not a file: {file_path}")

            print(f"✓ Agent files created successfully for {agent_name}")
            print(f"  - config.yml: {config_file}")
            print(f"  - prompt.txt: {prompt_file}")
            print(f"  - plugin.yml: {plugin_file}")

            return True

        except Exception as e:
            print(f"Error creating agent files: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_docker_compose(self, agent_definition: Dict[str, Any]) -> bool:
        """
        Create a standalone docker-compose file and .env file for the agent.

        Args:
            agent_definition: Agent configuration

        Returns:
            bool: Success status
        """
        try:
            agent_name = agent_definition["agent"]["name"]
            # Create both .env file and compose file
            self._write_agent_env_file(agent_name, agent_definition)
            self._write_agent_compose_file(agent_name, agent_definition)
            return True
        except Exception as e:
            print(f"Error creating agent compose/env files: {e}")
            return False

    def update_env_file(self, agent_definition: Dict[str, Any]) -> bool:
        """
        No-op: Per-agent .env files are now created by update_docker_compose().
        Configuration is stored in per-agent .env files (e.g., .env.agent-name).

        Args:
            agent_definition: Agent configuration

        Returns:
            bool: Always True (no-op)
        """
        # No longer needed - per-agent .env files are created by _write_agent_env_file()
        return True

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

                # Small delay to ensure filesystem has synced (especially important in containers)
                import time
                print("⏳ Waiting for filesystem to sync...")
                time.sleep(2)

                # Detect GPU mode
                gpu_mode = self.detect_gpu_mode()

                # Get compose files for this specific agent
                compose_files = self.get_compose_files(agent_name=agent_name, include_gpu=gpu_mode)

                # Remove existing container if it exists (to avoid mount issues)
                try:
                    rm_cmd = ["docker", "compose", "-p", "ollama-agents"] + compose_files + ["rm", "-f", "-s", "-v", agent_name]
                    subprocess.run(rm_cmd, cwd=str(self.project_root), check=False, capture_output=True)
                except Exception:
                    pass  # Ignore if container doesn't exist

                # Verify files exist on host before starting container
                agent_dir = self.agents_dir / agent_name
                host_agent_dir = self.host_project_root / "runtime" / "agents" / agent_name
                required_files = ["config.yml", "prompt.txt", "plugin.yml"]

                print(f"🔍 Verifying files exist before container start...")
                for filename in required_files:
                    file_path = agent_dir / filename
                    if not file_path.is_file():
                        raise Exception(f"Required file missing before container start: {file_path}")
                    print(f"  ✓ {filename} exists")

                # Start the service with force-recreate to avoid mount issues
                result["steps"].append({"step": "start_container", "status": "running"})
                up_cmd = ["docker", "compose", "-p", "ollama-agents"] + compose_files + ["up", "-d", "--force-recreate", agent_name]
                subprocess.run(up_cmd, cwd=str(self.project_root), check=True, capture_output=True)
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
            result = subprocess.run(up_cmd, cwd=str(self.project_root), check=True, capture_output=True)

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

            # Step 3: Remove agent's .env file
            result["steps"].append({"step": "remove_env_file", "status": "running"})
            env_path = self.agents_compose_dir / f".env.{agent_name}"
            try:
                if env_path.exists():
                    env_path.unlink()
                result["steps"][-1]["status"] = "completed"
            except Exception as e:
                result["errors"].append(f"Failed to remove .env file: {str(e)}")
                result["steps"][-1]["status"] = "failed"

            # Step 4: Optionally delete agent files on disk
            if remove_files:
                result["steps"].append({"step": "remove_files", "status": "running"})
                try:
                    import shutil
                    agent_dir = self.agents_dir / agent_name
                    if agent_dir.exists():
                        shutil.rmtree(agent_dir)
                    context_dir = self.agents_dir.parent / "context" / agent_name
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
