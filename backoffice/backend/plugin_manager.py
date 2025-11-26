#!/usr/bin/env python3
"""
Plugin Manager Module
Handles plugin discovery, validation, and dynamic registration.
"""

import os
import yaml
import docker
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PluginManifest:
    """Represents a plugin manifest (plugin.yml)"""

    def __init__(self, data: Dict[str, Any], source_path: Optional[Path] = None):
        self.data = data
        self.source_path = source_path

    @property
    def id(self) -> str:
        return self.data.get("plugin", {}).get("id", "")

    @property
    def name(self) -> str:
        return self.data.get("plugin", {}).get("name", self.id)

    @property
    def description(self) -> str:
        return self.data.get("plugin", {}).get("description", "")

    @property
    def version(self) -> str:
        return self.data.get("plugin", {}).get("version", "1.0.0")

    @property
    def author(self) -> str:
        return self.data.get("plugin", {}).get("author", "")

    @property
    def tags(self) -> List[str]:
        return self.data.get("plugin", {}).get("tags", [])

    @property
    def icon(self) -> str:
        return self.data.get("plugin", {}).get("icon", "🔌")

    @property
    def port(self) -> int:
        return self.data.get("agent", {}).get("port", 8000)

    @property
    def capabilities(self) -> List[str]:
        return self.data.get("capabilities", [])

    @property
    def api_endpoint(self) -> str:
        return self.data.get("api", {}).get("endpoint", "/process")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "icon": self.icon,
            "port": self.port,
            "capabilities": self.capabilities,
            "api": self.data.get("api", {}),
            "requires": self.data.get("requires", {}),
        }


class PluginValidator:
    """Validates plugin manifests"""

    REQUIRED_FIELDS = [
        ("plugin", "id"),
        ("plugin", "name"),
        ("plugin", "description"),
        ("agent", "port"),
    ]

    @staticmethod
    def validate(manifest_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate a plugin manifest.

        Returns:
            (is_valid, errors): Tuple of validation result and list of errors
        """
        errors = []

        # Check required fields
        for *parents, field in PluginValidator.REQUIRED_FIELDS:
            current = manifest_data
            path = []

            for parent in parents:
                path.append(parent)
                if parent not in current:
                    errors.append(f"Missing required field: {'.'.join(path)}")
                    break
                current = current[parent]
            else:
                if field not in current:
                    path.append(field)
                    errors.append(f"Missing required field: {'.'.join(path)}")

        # Validate plugin ID format
        plugin_id = manifest_data.get("plugin", {}).get("id", "")
        if plugin_id:
            if not plugin_id.replace("-", "").replace("_", "").isalnum():
                errors.append(f"Invalid plugin ID format: {plugin_id} (use lowercase alphanumeric with hyphens)")
            if plugin_id != plugin_id.lower():
                errors.append(f"Plugin ID must be lowercase: {plugin_id}")

        # Validate port
        port = manifest_data.get("agent", {}).get("port")
        if port is not None:
            if not isinstance(port, int):
                errors.append(f"Port must be an integer: {port}")
            elif port < 1024 or port > 65535:
                errors.append(f"Port must be between 1024-65535: {port}")

        # Validate version format (basic check)
        version = manifest_data.get("plugin", {}).get("version", "")
        if version and not version.replace(".", "").replace("-", "").replace("alpha", "").replace("beta", "").isalnum():
            errors.append(f"Invalid version format: {version}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_file(plugin_yml_path: Path) -> tuple[bool, List[str], Optional[PluginManifest]]:
        """
        Validate a plugin.yml file.

        Returns:
            (is_valid, errors, manifest): Tuple of validation result, errors, and manifest
        """
        try:
            if not plugin_yml_path.exists():
                return False, [f"Plugin manifest not found: {plugin_yml_path}"], None

            with open(plugin_yml_path, "r") as f:
                data = yaml.safe_load(f)

            is_valid, errors = PluginValidator.validate(data)

            if is_valid:
                manifest = PluginManifest(data, plugin_yml_path)
                return True, [], manifest
            else:
                return False, errors, None

        except yaml.YAMLError as e:
            return False, [f"YAML parse error: {e}"], None
        except Exception as e:
            return False, [f"Validation error: {e}"], None


class PluginRegistry:
    """
    Dynamic plugin registry with Docker-based discovery.
    Replaces the static AGENT_REGISTRY dictionary.
    """

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.plugins: Dict[str, Dict[str, Any]] = {}
        self.docker_client = None

        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.warning(f"Could not connect to Docker: {e}")

    def register(self, plugin_id: str, url: str, manifest: Optional[PluginManifest] = None):
        """Register a plugin manually"""
        self.plugins[plugin_id] = {
            "id": plugin_id,
            "url": url,
            "manifest": manifest.to_dict() if manifest else None,
            "registered_at": datetime.utcnow().isoformat(),
            "status": "registered",
        }
        logger.info(f"Registered plugin: {plugin_id} at {url}")

    def unregister(self, plugin_id: str):
        """Unregister a plugin"""
        if plugin_id in self.plugins:
            del self.plugins[plugin_id]
            logger.info(f"Unregistered plugin: {plugin_id}")

    def get(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get plugin by ID"""
        return self.plugins.get(plugin_id)

    def get_url(self, plugin_id: str) -> Optional[str]:
        """Get plugin URL by ID"""
        plugin = self.plugins.get(plugin_id)
        return plugin["url"] if plugin else None

    def list_all(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered plugins"""
        return self.plugins.copy()

    def discover_from_filesystem(self):
        """Discover plugins from filesystem (examples + runtime)"""
        discovered = 0

        # Discover from examples (git-tracked base agents)
        examples_dir = self.project_root / "examples" / "agents"
        if examples_dir.exists():
            discovered += self._discover_from_directory(examples_dir, "example")

        # Discover from runtime (user-created agents)
        runtime_dir = self.project_root / "runtime" / "agents"
        if runtime_dir.exists():
            discovered += self._discover_from_directory(runtime_dir, "runtime")

        logger.info(f"Discovered {discovered} plugins from filesystem")
        return discovered

    def _discover_from_directory(self, base_dir: Path, source: str) -> int:
        """Discover plugins from a directory"""
        count = 0

        for agent_dir in base_dir.iterdir():
            if not agent_dir.is_dir():
                continue

            plugin_yml = agent_dir / "plugin.yml"
            if not plugin_yml.exists():
                logger.debug(f"Skipping {agent_dir.name}: no plugin.yml")
                continue

            is_valid, errors, manifest = PluginValidator.validate_file(plugin_yml)

            if not is_valid:
                logger.warning(f"Invalid plugin manifest in {agent_dir.name}: {errors}")
                continue

            # Construct URL based on agent name
            agent_name = manifest.id
            url = f"http://agent-{agent_name}:8000"

            self.register(agent_name, url, manifest)
            count += 1

        return count

    def discover_from_docker(self):
        """Discover running agent containers from Docker"""
        if not self.docker_client:
            logger.warning("Docker client not available, skipping Docker discovery")
            return 0

        discovered = 0

        try:
            # Find all containers with name pattern "agent-*"
            containers = self.docker_client.containers.list(
                filters={"name": "agent-"}
            )

            for container in containers:
                container_name = container.name
                if not container_name.startswith("agent-"):
                    continue

                # Extract agent name
                agent_name = container_name.replace("agent-", "")

                # Get port mapping
                port_mapping = container.attrs.get("NetworkSettings", {}).get("Ports", {})
                internal_port = "8000/tcp"

                if internal_port in port_mapping and port_mapping[internal_port]:
                    host_port = port_mapping[internal_port][0]["HostPort"]
                    url = f"http://localhost:{host_port}"

                    # Try to read plugin.yml from container if not already registered
                    if agent_name not in self.plugins:
                        # Use internal network URL for service-to-service communication
                        internal_url = f"http://{container_name}:8000"
                        self.register(agent_name, internal_url)
                        discovered += 1
                        logger.info(f"Discovered running agent from Docker: {agent_name}")

        except Exception as e:
            logger.error(f"Error discovering agents from Docker: {e}")

        return discovered

    def discover_all(self):
        """Run all discovery methods"""
        fs_count = self.discover_from_filesystem()
        docker_count = self.discover_from_docker()

        total = len(self.plugins)
        logger.info(f"Plugin discovery complete: {total} total plugins ({fs_count} from filesystem, {docker_count} from Docker)")

        return total

    def to_legacy_registry(self) -> Dict[str, str]:
        """Convert to legacy AGENT_REGISTRY format (plugin_id -> url)"""
        return {plugin_id: plugin["url"] for plugin_id, plugin in self.plugins.items()}
