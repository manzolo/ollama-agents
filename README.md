# Ollama Agents - Modular AI Agent Architecture

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

For detailed instructions, see **[Quick Start Guide](docs/QUICK_START.md)**.

## Documentation

### Core Documentation
- **[Quick Start Guide](docs/QUICK_START.md)** - Get up and running in minutes
- **[Agent Documentation](docs/AGENTS.md)** - Create and configure agents
- **[Workflow Guide](docs/WORKFLOWS.md)** - Multi-agent workflow orchestration
- **[API Reference](docs/API_REFERENCE.md)** - Complete API documentation
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions

### Additional Resources
- **[Backoffice Guide](BACKOFFICE-GUIDE.md)** - Detailed backoffice features
- **[GPU Setup](GPU-SETUP.md)** - NVIDIA GPU configuration
- **[Inter-Agent Communication](INTER-AGENT-COMMUNICATION.md)** - Agent-to-agent patterns

## Project Structure

```
ollama-agents/
├── docs/                       # Documentation
│   ├── QUICK_START.md
│   ├── AGENTS.md
│   ├── WORKFLOWS.md
│   ├── API_REFERENCE.md
│   └── TROUBLESHOOTING.md
│
├── agents/                     # Agent definitions
│   ├── base/                   # Base agent implementation
│   ├── swarm-converter/        # Docker Compose to Swarm converter
│   ├── swarm-validator/        # Swarm stack validator
│   └── .agent-template/        # Template for new agents
│
├── backoffice/                 # Workflow management system
│   ├── backend/                # FastAPI server
│   ├── frontend/               # Web UI
│   └── workflows/              # Workflow definitions (YAML)
│
├── docker-compose.agents/      # Runtime agent deployments
├── shared/context/             # Persistent context storage
├── docker-compose.yml          # Main orchestration
├── Makefile                    # Convenient commands
└── .env                        # Environment configuration
```

## Base Agents

### Swarm Converter
Converts Docker Compose files to Docker Swarm stack files.
- **Endpoint**: http://localhost:7001
- **Swagger**: http://localhost:7001/docs

### Swarm Validator
Validates Docker Swarm stack files for correctness and best practices.
- **Endpoint**: http://localhost:7002
- **Swagger**: http://localhost:7002/docs

## Makefile Commands

### Basic Operations

```bash
# Start/Stop
make up              # Start all services
make down            # Stop all services
make restart         # Restart all services

# With GPU support
make up-gpu          # Start with GPU
make init-gpu        # Initialize with GPU
```

### Monitoring

```bash
make status          # Show service status
make health          # Check agent health
make logs            # Show all logs
make logs agent=X    # Show specific agent logs
```

### Agent Operations

```bash
make test-agent agent=swarm-converter       # Test agent
make run agent=X file=input.yml             # Run agent with file
make agent-info agent=X                     # Get agent info
make docs agent=X                           # Open Swagger UI
```

### Development

```bash
make rebuild         # Full rebuild
make clean           # Remove containers and volumes
make prune           # Prune unused Docker resources
```

For all commands, see the [Makefile](Makefile).

## CI/CD

The project includes automated testing via GitHub Actions:

- ✅ Builds all Docker services
- ✅ Tests health endpoints
- ✅ Validates API responses
- ✅ Checks OpenAPI schema

See `.github/workflows/test.yml` for details.

## Contributing

To contribute:
1. Create new agents following the template
2. Document your agent's capabilities
3. Include example usage
4. Test thoroughly before deployment

See **[Agent Documentation](docs/AGENTS.md)** for details.

## License

This project is provided as-is for educational and development purposes.

## Support

For issues and questions:
- Check **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)**
- Review agent logs: `make logs agent=<name>`
- Verify configuration in .env and docker-compose.yml
- Test Ollama: `curl http://localhost:11434/api/version`
