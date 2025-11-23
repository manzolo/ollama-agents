#!/usr/bin/env python3
"""
Ollama Agent API Wrapper
A modular FastAPI application that wraps Ollama models with custom prompts
and exposes them as simple HTTP endpoints.
"""

import os
import json
import yaml
import re
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field
import httpx
import uvicorn


# ============================================================================
# Configuration
# ============================================================================
AGENT_NAME = os.getenv("AGENT_NAME", "generic-agent")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.2")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
CONTEXT_DIR = Path("/app/context")
PROMPT_FILE = Path("/app/prompt.txt")
CONFIG_FILE = Path("/app/config.yml")


# ============================================================================
# Data Models
# ============================================================================
class AgentRequest(BaseModel):
    """Request model for agent invocation"""
    input: str = Field(
        ...,
        description="The input text to process",
        examples=["Convert this docker-compose.yml to a Swarm stack file"]
    )
    stream: bool = Field(
        False,
        description="Whether to stream the response (not yet implemented)"
    )
    options: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional model options (temperature, top_k, top_p, etc.)",
        examples=[{"temperature": 0.5, "top_k": 40}]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "input": "version: '3.8'\nservices:\n  web:\n    build: .\n    restart: always",
                    "stream": False,
                    "options": {"temperature": 0.3}
                }
            ]
        }
    }


class AgentResponse(BaseModel):
    """Response model for agent invocation"""
    agent: str = Field(..., description="Name of the agent that processed the request")
    output: str = Field(..., description="The agent's response/output")
    model: str = Field(..., description="The LLM model used")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the response")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata about the processing")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "agent": "swarm-converter",
                    "output": "Converted YAML content...",
                    "model": "llama3.2",
                    "timestamp": "2025-11-23T20:00:00",
                    "metadata": {"temperature": 0.3, "max_tokens": 8192}
                }
            ]
        }
    }


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Health status (healthy/degraded)")
    agent: str = Field(..., description="Agent name")
    model: str = Field(..., description="Model name")
    ollama_connection: bool = Field(..., description="Ollama connectivity status")
    timestamp: str = Field(..., description="ISO 8601 timestamp")


class InfoResponse(BaseModel):
    """Agent information response model"""
    agent: str = Field(..., description="Agent name")
    model: str = Field(..., description="Model name")
    ollama_host: str = Field(..., description="Ollama host URL")
    system_prompt: str = Field(..., description="The agent's system prompt")
    config: Dict[str, Any] = Field(..., description="Agent configuration")
    capabilities: list = Field(..., description="List of agent capabilities")


class ContextResponse(BaseModel):
    """Context history response model"""
    agent: str = Field(..., description="Agent name")
    recent_interactions: list = Field(..., description="Recent interactions from memory")


class StatusResponse(BaseModel):
    """Generic status response model"""
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Status message")


class RawResponse(BaseModel):
    """Raw/clean output response model"""
    agent: str = Field(..., description="Name of the agent")
    output: str = Field(..., description="Extracted clean output (code block content)")
    format: str = Field(..., description="Detected format (yaml, json, text, etc.)")
    timestamp: str = Field(..., description="ISO 8601 timestamp")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "agent": "swarm-converter",
                    "output": "version: '3.8'\nservices:\n  web:\n    image: nginx",
                    "format": "yaml",
                    "timestamp": "2025-11-23T20:30:00"
                }
            ]
        }
    }


# ============================================================================
# Agent Configuration
# ============================================================================
class AgentConfig:
    """Manages agent configuration and system prompts"""

    def __init__(self):
        self.system_prompt = self._load_prompt()
        self.config = self._load_config()

    def _load_prompt(self) -> str:
        """Load system prompt from file"""
        if not PROMPT_FILE.exists():
            return f"You are {AGENT_NAME}, a helpful AI assistant."

        with open(PROMPT_FILE, "r") as f:
            return f.read().strip()

    def _load_config(self) -> Dict[str, Any]:
        """Load additional configuration from YAML"""
        if not CONFIG_FILE.exists():
            return {}

        with open(CONFIG_FILE, "r") as f:
            return yaml.safe_load(f) or {}

    def get_model_options(self, user_options: Optional[Dict] = None) -> Dict[str, Any]:
        """Get model options with precedence: user > config > env"""
        options = {
            "temperature": TEMPERATURE,
            "num_predict": MAX_TOKENS,
        }

        # Override with config file
        if "options" in self.config:
            options.update(self.config["options"])

        # Override with user options
        if user_options:
            options.update(user_options)

        return options


# ============================================================================
# Ollama Client
# ============================================================================
class OllamaClient:
    """Client for interacting with Ollama API"""

    def __init__(self, host: str, model: str):
        self.host = host.rstrip("/")
        self.model = model
        self.client = httpx.AsyncClient(timeout=300.0)

    async def generate(
        self,
        prompt: str,
        system: str,
        options: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> str:
        """Generate a response from Ollama"""

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": stream,
            "options": options or {}
        }

        try:
            response = await self.client.post(
                f"{self.host}/api/generate",
                json=payload
            )
            response.raise_for_status()

            if stream:
                # For streaming, we'd need to handle this differently
                # For now, just return the final response
                pass

            result = response.json()
            return result.get("response", "")

        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ollama API error: {str(e)}"
            )

    async def health_check(self) -> bool:
        """Check if Ollama is healthy"""
        try:
            response = await self.client.get(f"{self.host}/api/version")
            return response.status_code == 200
        except:
            return False


# ============================================================================
# Utility Functions
# ============================================================================
def extract_code_blocks(text: str, language: Optional[str] = None) -> list:
    """
    Extract code blocks from markdown text.

    Args:
        text: The markdown text containing code blocks
        language: Optional language filter (e.g., 'yaml', 'json', 'python')

    Returns:
        List of extracted code block contents
    """
    # Pattern to match markdown code blocks with optional language
    pattern = r'```(\w+)?\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)

    code_blocks = []
    for lang, code in matches:
        # If language filter specified, only include matching blocks
        if language is None or lang.lower() == language.lower():
            code_blocks.append(code.strip())

    return code_blocks


def extract_first_code_block(text: str, language: Optional[str] = None) -> Optional[str]:
    """
    Extract the first code block from markdown text.

    Args:
        text: The markdown text containing code blocks
        language: Optional language filter (e.g., 'yaml', 'json', 'python')

    Returns:
        The first matching code block content, or None if not found
    """
    blocks = extract_code_blocks(text, language)
    return blocks[0] if blocks else None


def clean_output(text: str) -> str:
    """
    Clean output by removing markdown formatting and extracting main content.

    Priority:
    1. Extract first code block if present
    2. Remove common markdown formatting
    3. Return cleaned text
    """
    # Try to extract code block first
    code_block = extract_first_code_block(text)
    if code_block:
        return code_block

    # If no code block, clean markdown formatting
    # Remove headers
    text = re.sub(r'^#{1,6}\s+.*$', '', text, flags=re.MULTILINE)
    # Remove bold/italic
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    # Remove links
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)

    return text.strip()


# ============================================================================
# Context Memory (Optional)
# ============================================================================
class ContextMemory:
    """Simple file-based context memory for agents"""

    def __init__(self, context_dir: Path):
        self.context_dir = context_dir
        self.context_dir.mkdir(parents=True, exist_ok=True)

    def save_interaction(self, request: str, response: str, metadata: Dict = None):
        """Save an interaction to context memory"""
        timestamp = datetime.now().isoformat()
        filename = f"interaction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        data = {
            "timestamp": timestamp,
            "request": request,
            "response": response,
            "metadata": metadata or {}
        }

        filepath = self.context_dir / filename
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def get_recent_context(self, limit: int = 5) -> list:
        """Get recent interactions from context memory"""
        files = sorted(self.context_dir.glob("interaction_*.json"), reverse=True)

        context = []
        for filepath in files[:limit]:
            with open(filepath, "r") as f:
                context.append(json.load(f))

        return context


# ============================================================================
# FastAPI Application
# ============================================================================

# Load agent config early to get description
temp_config = AgentConfig()
agent_description = temp_config.config.get("agent", {}).get("description", f"AI Agent - {AGENT_NAME}")

app = FastAPI(
    title=f"{AGENT_NAME.replace('-', ' ').title()} Agent",
    description=f"""
## {agent_description}

This agent is powered by Ollama using the **{MODEL_NAME}** model.

### Features
- 🤖 AI-powered processing with customizable prompts
- 💾 Context memory for interaction history
- ⚙️ Configurable model parameters
- 🏥 Health monitoring and status checks

### Endpoints
- **POST /process** - Main agent processing endpoint
- **GET /health** - Health check and status
- **GET /info** - Agent information and capabilities
- **GET /context** - View interaction history
- **DELETE /context** - Clear interaction history

### Authentication
Currently no authentication required (add authentication for production use).

### Rate Limiting
No rate limiting currently applied.
    """,
    version="1.0.0",
    contact={
        "name": "Ollama Agents",
        "url": "https://github.com/ollama/ollama",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=[
        {
            "name": "agent",
            "description": "Main agent processing operations"
        },
        {
            "name": "health",
            "description": "Health and monitoring endpoints"
        },
        {
            "name": "context",
            "description": "Context memory operations"
        }
    ]
)

# Initialize components
agent_config = temp_config
ollama_client = OllamaClient(OLLAMA_HOST, MODEL_NAME)
context_memory = ContextMemory(CONTEXT_DIR)


# ============================================================================
# API Endpoints
# ============================================================================

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Health Check",
    description="""
    Check the health status of the agent and its connection to Ollama.

    Returns:
    - **status**: Overall health status (healthy/degraded)
    - **agent**: Name of the agent
    - **model**: LLM model being used
    - **ollama_connection**: Whether Ollama is reachable
    - **timestamp**: Current timestamp
    """
)
async def health_check():
    """Health check endpoint - returns agent and Ollama status"""
    ollama_healthy = await ollama_client.health_check()

    return {
        "status": "healthy" if ollama_healthy else "degraded",
        "agent": AGENT_NAME,
        "model": MODEL_NAME,
        "ollama_connection": ollama_healthy,
        "timestamp": datetime.now().isoformat()
    }


@app.get(
    "/info",
    response_model=InfoResponse,
    tags=["health"],
    summary="Agent Information",
    description="""
    Get detailed information about the agent including its configuration,
    capabilities, and system prompt.

    This endpoint is useful for:
    - Understanding what the agent can do
    - Viewing the agent's system prompt
    - Checking model and configuration details
    """
)
async def get_info():
    """Get comprehensive agent information"""
    return {
        "agent": AGENT_NAME,
        "model": MODEL_NAME,
        "ollama_host": OLLAMA_HOST,
        "system_prompt": agent_config.system_prompt,
        "config": agent_config.config,
        "capabilities": agent_config.config.get("capabilities", [])
    }


@app.post(
    "/process",
    response_model=AgentResponse,
    tags=["agent"],
    summary="Process Input",
    description="""
    Main endpoint for processing input through the AI agent.

    The agent will:
    1. Receive your input text
    2. Apply its specialized system prompt
    3. Process using the configured LLM model
    4. Return the AI-generated output

    **Example Request:**
    ```json
    {
        "input": "Your input text here",
        "options": {
            "temperature": 0.5
        }
    }
    ```

    **Model Options:**
    - `temperature`: Randomness (0.0-1.0, default from config)
    - `top_k`: Top-k sampling (default: 40)
    - `top_p`: Top-p sampling (default: 0.9)
    - `num_predict`: Max tokens to generate
    """
)
async def process_request(request: AgentRequest):
    """Main endpoint for processing agent requests"""

    # Get model options
    options = agent_config.get_model_options(request.options)

    # Generate response from Ollama
    response_text = await ollama_client.generate(
        prompt=request.input,
        system=agent_config.system_prompt,
        options=options,
        stream=request.stream
    )

    # Replace timestamp placeholder with actual current timestamp
    current_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    response_text = response_text.replace('{{TIMESTAMP}}', current_timestamp)

    # Save to context memory
    context_memory.save_interaction(
        request=request.input,
        response=response_text,
        metadata={"model": MODEL_NAME, "options": options}
    )

    # Build response
    return AgentResponse(
        agent=AGENT_NAME,
        output=response_text,
        model=MODEL_NAME,
        timestamp=datetime.now().isoformat(),
        metadata={
            "temperature": options.get("temperature"),
            "max_tokens": options.get("num_predict")
        }
    )


@app.post(
    "/process/raw",
    response_model=RawResponse,
    tags=["agent"],
    summary="Process and Extract Clean Output",
    description="""
    Process input and return only the extracted result (without markdown formatting).

    This endpoint is designed for **inter-agent communication** and **programmatic usage**.
    It automatically extracts code blocks from the response and returns clean output.

    **Use Cases:**
    - Agent-to-agent communication
    - API integrations
    - Automated pipelines
    - Direct result consumption

    **Behavior:**
    1. Processes input through the AI agent (same as /process)
    2. Extracts first code block from response (e.g., ```yaml, ```json)
    3. Returns clean content without markdown formatting
    4. Falls back to cleaned text if no code block found

    **Example Response:**
    ```json
    {
        "agent": "swarm-converter",
        "output": "version: '3.8'\\nservices:\\n  web:\\n    image: nginx",
        "format": "yaml",
        "timestamp": "2025-11-23T20:30:00"
    }
    ```

    Perfect for piping to another agent or saving directly to a file.
    """
)
async def process_raw(request: AgentRequest):
    """Process input and return clean, extracted output"""

    # Get model options
    options = agent_config.get_model_options(request.options)

    # Generate response from Ollama
    response_text = await ollama_client.generate(
        prompt=request.input,
        system=agent_config.system_prompt,
        options=options,
        stream=request.stream
    )

    # Extract clean output
    clean = clean_output(response_text)

    # Replace timestamp placeholder with actual current timestamp
    current_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    clean = clean.replace('{{TIMESTAMP}}', current_timestamp)

    # Detect format from first code block
    code_blocks_with_lang = re.findall(r'```(\w+)?\n', response_text)
    detected_format = code_blocks_with_lang[0] if code_blocks_with_lang else "text"

    # Save to context memory
    context_memory.save_interaction(
        request=request.input,
        response=response_text,
        metadata={"model": MODEL_NAME, "options": options, "format": detected_format}
    )

    # Build response
    return RawResponse(
        agent=AGENT_NAME,
        output=clean,
        format=detected_format,
        timestamp=datetime.now().isoformat()
    )


@app.post(
    "/process/raw/text",
    response_class=PlainTextResponse,
    tags=["agent"],
    summary="Process and Return Plain Text",
    description="""
    Process input and return ONLY the extracted text content (no JSON wrapper).

    This is the simplest endpoint for **direct consumption** of results.
    Returns pure text that can be:
    - Saved directly to a file
    - Piped to another command
    - Used as-is without parsing

    **Example Usage:**
    ```bash
    curl -X POST http://localhost:7001/process/raw/text \\
      -H "Content-Type: application/json" \\
      -d '{"input": "your content"}' \\
      > output.yaml
    ```

    Perfect for shell scripts and command-line usage.
    """
)
async def process_raw_text(request: AgentRequest):
    """Process input and return only plain text output"""

    # Get model options
    options = agent_config.get_model_options(request.options)

    # Generate response from Ollama
    response_text = await ollama_client.generate(
        prompt=request.input,
        system=agent_config.system_prompt,
        options=options,
        stream=request.stream
    )

    # Extract clean output
    clean = clean_output(response_text)

    # Replace timestamp placeholder with actual current timestamp
    current_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    clean = clean.replace('{{TIMESTAMP}}', current_timestamp)

    # Return clean output as plain text
    return clean


@app.get(
    "/context",
    response_model=ContextResponse,
    tags=["context"],
    summary="Get Context History",
    description="""
    Retrieve recent interactions from the agent's context memory.

    The context memory stores all previous interactions with timestamps,
    requests, responses, and metadata. This is useful for:
    - Reviewing past interactions
    - Debugging issues
    - Understanding agent behavior over time

    **Parameters:**
    - `limit`: Number of recent interactions to retrieve (default: 5, max: 100)
    """
)
async def get_context(
    limit: int = Query(5, ge=1, le=100, description="Number of interactions to retrieve")
):
    """Get recent context from memory"""
    return {
        "agent": AGENT_NAME,
        "recent_interactions": context_memory.get_recent_context(limit)
    }


@app.delete(
    "/context",
    response_model=StatusResponse,
    tags=["context"],
    summary="Clear Context History",
    description="""
    Delete all stored interactions from the agent's context memory.

    **Warning:** This action is irreversible. All interaction history
    will be permanently deleted.

    Use this endpoint when:
    - Starting fresh with a new context
    - Removing sensitive data from memory
    - Troubleshooting context-related issues
    """
)
async def clear_context():
    """Clear all context memory"""
    for filepath in CONTEXT_DIR.glob("interaction_*.json"):
        filepath.unlink()

    return {
        "status": "success",
        "message": "Context memory cleared"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "agent": AGENT_NAME,
            "timestamp": datetime.now().isoformat()
        }
    )


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
