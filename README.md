# Ollama Agents - Modular AI Agent Architecture

![Docker](https://img.shields.io/badge/docker-ready-2496ED?style=flat&logo=docker&logoColor=white)
![GPU Support](https://img.shields.io/badge/GPU-NVIDIA-76B900?style=flat&logo=nvidia&logoColor=white)
![Python](https://img.shields.io/badge/python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![Version](https://img.shields.io/badge/version-2.0.0-blue?style=flat)
![License](https://img.shields.io/badge/license-MIT-green?style=flat)

A clean, modular, and extensible Docker Compose architecture for hosting multiple specialized AI agents powered by Ollama, with a powerful **Backoffice Web UI** for managing multi-agent workflows.

## Overview

This project provides a modular framework for deploying multiple specialized AI agents, each with:

- **Its own Ollama model** - Choose the best model for each task
- **Custom prompt configuration** - Define agent behavior via YAML
- **Dedicated API endpoint** - Each agent has its own REST API
- **Optional context memory** - Agents can remember past interactions
- **Independent scaling** - Scale agents individually based on load

**NEW**: **Backoffice Web UI** - A modern web interface for creating and executing multi-agent workflows without writing code!

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│               Backoffice Web UI (:8080)                 │
│   - Workflow Management  - Agent Discovery              │
│   - Visual Execution     - History Tracking             │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  Ollama Engine (:11434)                 │
│                  (LLM Model Server)                     │
└────────────┬─────────────┬─────────────┬────────────────┘
             │             │             │
             ▼             ▼             ▼
     ┌───────────┐  ┌───────────┐  ┌───────────┐
     │  Agent 1  │  │  Agent 2  │  │  Agent N  │
     │  (Swarm   │  │ (Swarm    │  │  (Custom) │
     │ Converter)│  │ Validator)│  │           │
     └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
           │              │              │
           ▼              ▼              ▼
        :7001          :7002          :700N
         API            API            API
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Make and jq (for Makefile commands)
- At least 8GB RAM (16GB+ recommended)
- (Optional) NVIDIA GPU with Docker GPU support

### Installation

**Option 1: Interactive Wizard (Recommended)**

```bash
make wizard
```

**Option 2: Manual Setup**

```bash
# CPU mode
make init

# GPU mode (requires NVIDIA GPU)
make init-gpu
```

### Access the Backoffice

Open your browser to:
```
http://localhost:8080
```

### Test an Agent

```bash
# Quick health check
make test-agent agent=swarm-converter

# Run with a file
make run agent=swarm-converter file=docker-compose.yml
```

For detailed instructions, see **[Quick Start Guide](docs/QUICKSTART.md)**.

## Documentation

### Core Documentation
- **[Quick Start Guide](docs/QUICKSTART.md)** - Get up and running in minutes
- **[Agent Documentation](docs/AGENTS.md)** - Create and configure agents
- **[Plugin System](docs/PLUGINS.md)** - Plugin architecture and development
- **[Workflow Guide](docs/WORKFLOWS.md)** - Multi-agent workflow orchestration
- **[API Reference](docs/API_REFERENCE.md)** - Complete API documentation
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions

### Additional Resources
- **[Backoffice Guide](docs/BACKOFFICE-GUIDE.md)** - Detailed backoffice features
- **[GPU Setup](docs/GPU-SETUP.md)** - NVIDIA GPU configuration
- **[Inter-Agent Communication](docs/INTER-AGENT-COMMUNICATION.md)** - Agent-to-agent patterns

## Project Structure

```
ollama-agents/
├── docs/                       # Documentation
├── agents/                     # Agent definitions
│   ├── base/                   # Base agent implementation
│   ├── swarm-converter/        # Docker Compose to Swarm converter
│   ├── swarm-validator/        # Swarm stack validator
│   └── .agent-template/        # Template for new agents
├── backoffice/                 # Workflow management system
│   ├── backend/                # FastAPI server
│   ├── frontend/               # Web UI
│   └── workflows/              # Workflow definitions (YAML)
├── docker-compose.yml          # Main orchestration
├── Makefile                    # Convenient commands
└── .env                        # Environment configuration
```

## Key Features

- 🤖 **Multiple Specialized Agents** - Each with its own model and configuration
- 🎨 **Backoffice Web UI** - Visual workflow management and execution
- 🔄 **YAML-Based Workflows** - Chain agents without coding
- 📊 **Execution History** - Track all workflow runs
- 🔌 **REST API** - Full programmatic access
- 🐳 **Docker Compose** - Easy deployment and scaling
- 🎯 **GPU Support** - Optional NVIDIA GPU acceleration

## Common Commands

```bash
# Start/Stop
make up              # Start all services
make down            # Stop all services
make restart         # Restart all services

# Monitoring
make status          # Show service status
make health          # Check agent health
make logs            # Show all logs

# Agent Operations
make test-agent agent=swarm-converter       # Test agent
make run agent=X file=input.yml             # Run agent with file
make docs agent=X                           # Open Swagger UI
```

For all commands, see the [Makefile](Makefile) or run `make help`.

## License

This project is provided as-is for educational and development purposes.

## Support

For issues and questions:
- Check **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)**
- Review agent logs: `make logs agent=<name>`
- Verify configuration in .env and docker-compose.yml
- Test Ollama: `curl http://localhost:11434/api/version`

---

## 🧠 Local AI Lab

This project is part of **[manzolo's Local AI Lab](https://github.com/manzolo/local-ai-lab)** — a family of self-hosted AI projects (LLM, voice, vision & documents) that share the same conventions and can be wired together through the shared `local-ai-net` Docker network.

This repo ships a `docker-compose.local-ai.yml` override to join the shared network — see the [conventions](https://github.com/manzolo/local-ai-lab#conventions).

Explore the whole family: [`topic:local-ai`](https://github.com/search?q=user%3Amanzolo+topic%3Alocal-ai&type=repositories)
