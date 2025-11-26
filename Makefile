# ============================================================================
# OLLAMA AGENTS - Makefile
# ============================================================================

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# ============================================================================
# Dynamic Agent Compose Files
# ============================================================================
# Find all agent compose files in docker-compose.agents/ directory
AGENT_COMPOSE_FILES := $(wildcard docker-compose.agents/*.yml)
# Build compose file arguments: -f docker-compose.yml -f docker-compose.agents/agent1.yml -f docker-compose.agents/agent2.yml ...
COMPOSE_FILES := -f docker-compose.yml $(foreach file,$(AGENT_COMPOSE_FILES),-f $(file))
COMPOSE_FILES_GPU := $(COMPOSE_FILES) -f docker-compose.gpu.yml

# ============================================================================
# Help
# ============================================================================
help: ## Show this help message
    @echo "$(BLUE)╔══════════════════════════════════════════════════════════════╗$(NC)"
    @echo "$(BLUE)║           OLLAMA AGENTS - Available Commands                 ║$(NC)"
    @echo "$(BLUE)╚══════════════════════════════════════════════════════════════╝$(NC)"
    @echo ""
    @echo "$(YELLOW)🚀 QUICK START$(NC)"
    @echo "  $(GREEN)wizard$(NC)              Interactive setup guide"
    @echo "  $(GREEN)init$(NC)                Initialize project (CPU mode)"
    @echo "  $(GREEN)init-gpu$(NC)            Initialize with GPU support"
    @echo ""
    @echo "$(YELLOW)🎮 BASIC OPERATIONS$(NC)"
    @echo "  $(GREEN)up$(NC)                  Start services (CPU mode)"
    @echo "  $(GREEN)up-gpu$(NC)              Start services with GPU"
    @echo "  $(GREEN)down$(NC)                Stop all services"
    @echo "  $(GREEN)restart$(NC)             Restart services"
    @echo "  $(GREEN)status$(NC)              Show service status"
    @echo "  $(GREEN)health$(NC)              Check agent health"
    @echo "  $(GREEN)show-compose-files$(NC) Show active compose files"
    @echo ""
    @echo "$(YELLOW)🤖 AGENT OPERATIONS$(NC)"
    @echo "  $(GREEN)run$(NC)                 Run agent with file (agent=X file=Y)"
    @echo "  $(GREEN)test-agent$(NC)          Test agent health (agent=X)"
    @echo "  $(GREEN)logs$(NC)                View logs (agent=X, optional)"
    @echo "  $(GREEN)docs$(NC)                Open Swagger UI (agent=X)"
    @echo ""
    @echo "$(YELLOW)📦 MODELS$(NC)"
    @echo "  $(GREEN)pull-models$(NC)         Pull default models"
    @echo "  $(GREEN)list-models$(NC)         List available models"
    @echo "  $(GREEN)pull-model$(NC)          Pull specific model (model=X)"
    @echo ""
    @echo "$(YELLOW)🛠️  DEVELOPMENT$(NC)"
    @echo "  $(GREEN)build$(NC)               Build services"
    @echo "  $(GREEN)rebuild$(NC)             Full rebuild (CPU)"
    @echo "  $(GREEN)rebuild-gpu$(NC)         Full rebuild with GPU"
    @echo "  $(GREEN)shell-agent$(NC)         Shell into agent (agent=X)"
    @echo ""
    @echo "$(YELLOW)🧹 CLEANUP$(NC)"
    @echo "  $(GREEN)clean$(NC)               Remove all data"
    @echo "  $(GREEN)prune$(NC)               Prune Docker resources"
    @echo ""
    @echo "$(YELLOW)💡 Examples:$(NC)"
    @echo "  make wizard                              # Interactive guide"
    @echo "  make run agent=swarm-converter file=docker-compose.yml"
    @echo "  make logs agent=swarm-converter          # View specific logs"
    @echo ""
    @echo "$(BLUE)For full command list: grep '##' Makefile$(NC)"
    @echo ""

# ============================================================================
# Wizard Mode
# ============================================================================
wizard: ensure-env-agents ## Interactive setup guide
    @echo "$(BLUE)╔══════════════════════════════════════════════════════════════╗$(NC)"
    @echo "$(BLUE)║           OLLAMA AGENTS - Setup Wizard                       ║$(NC)"
    @echo "$(BLUE)╚══════════════════════════════════════════════════════════════╝$(NC)"
    @echo ""
    @echo "$(YELLOW)Welcome! This wizard will help you get started.$(NC)"
    @echo ""
    @echo "$(BLUE)Step 1: Choose Mode$(NC)"
    @echo "  1) CPU Mode (works everywhere, recommended for first time)"
    @echo "  2) GPU Mode (requires NVIDIA GPU + nvidia-docker)"
    @echo ""
    @read -p "Enter choice [1-2] (default: 1): " choice; \
    choice=$${choice:-1}; \
    echo ""; \
    if [ "$$choice" = "2" ]; then \
        echo "$(YELLOW)Checking GPU availability...$(NC)"; \
        if command -v nvidia-smi > /dev/null 2>&1; then \
            nvidia-smi > /dev/null 2>&1 && echo "$(GREEN)✓ NVIDIA GPU detected$(NC)" || echo "$(RED)⚠ NVIDIA driver may not be working$(NC)"; \
        else \
            echo "$(RED)⚠ nvidia-smi not found. See GPU-SETUP.md for installation.$(NC)"; \
            echo "$(YELLOW)Continuing with CPU mode...$(NC)"; \
            choice=1; \
        fi; \
        echo ""; \
    fi; \
    \
    echo "$(BLUE)Step 2: Initialize Project$(NC)"; \
    echo "$(YELLOW)This will build containers, start services, and pull models (~5-10 min)$(NC)"; \
    read -p "Continue? [Y/n]: " confirm; \
    confirm=$${confirm:-y}; \
    echo ""; \
    if [ "$$confirm" != "y" ] && [ "$$confirm" != "Y" ]; then \
        echo "$(BLUE)Setup cancelled. Run 'make wizard' when ready.$(NC)"; \
        exit 0; \
    fi; \
    \
    if [ "$$choice" = "2" ]; then \
        echo "$(GREEN)Initializing with GPU support...$(NC)"; \
        echo ""; \
        make init-gpu; \
    else \
        echo "$(GREEN)Initializing in CPU mode...$(NC)"; \
        echo ""; \
        make init; \
    fi; \
    \
    echo ""; \
    echo "$(BLUE)Step 3: What's Next?$(NC)"; \
    echo ""; \
    echo "$(YELLOW)🌐 Backoffice Web UI$(NC)"; \
    echo "  Open http://localhost:8080 to:"; \
    echo "  • Discover available agents"; \
    echo "  • Create multi-agent workflows"; \
    echo "  • Execute workflows visually"; \
    echo ""; \
    echo "$(YELLOW)🧪 Test an Agent$(NC)"; \
    echo "  make run agent=swarm-converter file=docker-compose.yml"; \
    echo ""; \
    echo "$(YELLOW)📖 Documentation$(NC)"; \
    echo "  • README.md - Full documentation"; \
    echo "  • QUICKSTART.md - Quick start guide"; \
    echo "  • GPU-SETUP.md - GPU setup instructions"; \
    echo ""; \
    read -p "Open Backoffice Web UI now? [Y/n]: " open_ui; \
    open_ui=$${open_ui:-y}; \
    if [ "$$open_ui" = "y" ] || [ "$$open_ui" = "Y" ]; then \
        echo "$(GREEN)Opening http://localhost:8080...$(NC)"; \
        xdg-open "http://localhost:8080" 2>/dev/null || \
        open "http://localhost:8080" 2>/dev/null || \
        echo "$(YELLOW)Please open: http://localhost:8080$(NC)"; \
    fi; \
    echo ""; \
    echo "$(GREEN)✓ Setup complete! Run 'make help' to see all commands.$(NC)"; \
    echo ""

# ============================================================================
# Docker Compose Operations
# ============================================================================
up: ## Start all services (CPU mode)
    @echo "$(BLUE)Starting Ollama Agents (CPU mode)...$(NC)"
    docker compose $(COMPOSE_FILES) up -d
    @echo "$(GREEN)✓ Services started$(NC)"
    @make status

up-gpu: ## Start all services with GPU support
    @echo "$(BLUE)Starting Ollama Agents (GPU mode)...$(NC)"
    @echo "$(YELLOW)Note: Requires NVIDIA GPU and nvidia-docker runtime$(NC)"
    docker compose $(COMPOSE_FILES_GPU) up -d
    @echo "$(GREEN)✓ Services started with GPU$(NC)"
    @make status

down: ## Stop all services
    @echo "$(BLUE)Stopping Ollama Agents...$(NC)"
    docker compose $(COMPOSE_FILES) down
    @echo "$(GREEN)✓ Services stopped$(NC)"

restart: ## Restart all services
    @echo "$(BLUE)Restarting Ollama Agents...$(NC)"
    docker compose $(COMPOSE_FILES) restart
    @echo "$(GREEN)✓ Services restarted$(NC)"

restart-gpu: ## Restart all services with GPU
    @echo "$(BLUE)Restarting Ollama Agents (GPU mode)...$(NC)"
    docker compose $(COMPOSE_FILES_GPU) restart
    @echo "$(GREEN)✓ Services restarted with GPU$(NC)"

build: ensure-env-agents ## Build/rebuild all services
    @echo "$(BLUE)Building services...$(NC)"
    docker compose $(COMPOSE_FILES) build --no-cache
    @echo "$(GREEN)✓ Build complete$(NC)"

rebuild: down build up ## Full rebuild: stop, build, start (CPU)

rebuild-gpu: down build up-gpu ## Full rebuild with GPU: stop, build, start

# ============================================================================
# Logging and Monitoring
# ============================================================================
logs: ## Show logs (use: make logs agent=<name>)
    @if [ -z "$(agent)" ]; then \
        docker compose $(COMPOSE_FILES) logs -f; \
    else \
        docker compose $(COMPOSE_FILES) logs -f $(agent); \
    fi

logs-ollama: ## Show Ollama service logs
    docker compose $(COMPOSE_FILES) logs -f ollama

ps: ## Show running containers
    @echo "$(BLUE)Running Services:$(NC)"
    @docker compose $(COMPOSE_FILES) ps

status: ## Show health status of all services
    @echo "$(BLUE)Service Health Status:$(NC)"
    @docker compose $(COMPOSE_FILES) ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

show-compose-files: ## Show all compose files being used
    @echo "$(BLUE)Active Compose Files:$(NC)"
    @echo "  - docker-compose.yml (main)"
    @if [ -n "$(AGENT_COMPOSE_FILES)" ]; then \
        for file in $(AGENT_COMPOSE_FILES); do \
            echo "  - $$file (agent)"; \
        done; \
    else \
        echo "  $(YELLOW)No agent compose files found in docker-compose.agents/$(NC)"; \
    fi
    @echo ""
    @echo "$(BLUE)GPU Compose File:$(NC)"
    @if [ -f docker-compose.gpu.yml ]; then \
        echo "  - docker-compose.gpu.yml (available, use 'make up-gpu')"; \
    else \
        echo "  $(YELLOW)docker-compose.gpu.yml not found$(NC)"; \
    fi

# ============================================================================
# Ollama Model Management
# ============================================================================
pull-models: ## Pull Ollama models specified in .env
    @echo "$(BLUE)Pulling Ollama models...$(NC)"
    docker compose $(COMPOSE_FILES) exec ollama ollama pull llama3.2
    @echo "$(GREEN)✓ Models pulled$(NC)"

pull-model: ## Pull specific model (use: make pull-model model=<name>)
    @if [ -z "$(model)" ]; then \
        echo "$(RED)Error: model parameter required$(NC)"; \
        echo "Usage: make pull-model model=llama3.2"; \
        exit 1; \
    fi
    @echo "$(BLUE)Pulling model: $(model)$(NC)"
    docker compose $(COMPOSE_FILES) exec ollama ollama pull $(model)
    @echo "$(GREEN)✓ Model $(model) pulled$(NC)"

list-models: ## List available Ollama models
    @echo "$(BLUE)Available Models:$(NC)"
    docker compose $(COMPOSE_FILES) exec ollama ollama list

# ============================================================================
# Agent Testing
# ============================================================================
test-agent: ## Test an agent (use: make test-agent agent=<name>)
    @if [ -z "$(agent)" ]; then \
        echo "$(RED)Error: agent parameter required$(NC)"; \
        echo "Usage: make test-agent agent=swarm-converter"; \
        exit 1; \
    fi
    @echo "$(BLUE)Testing agent: $(agent)$(NC)"
    @echo "Checking health..."
    @curl -s http://localhost:$$(docker compose port $(agent) 8000 | cut -d':' -f2)/health | jq . || \
        echo "$(RED)Health check failed$(NC)"
    @echo ""
    @echo "$(GREEN)To test with input, use:$(NC)"
    @echo "curl -X POST http://localhost:$$(docker compose port $(agent) 8000 | cut -d':' -f2)/process \\"
    @echo "  -H 'Content-Type: application/json' \\"
    @echo "  -d '{\"input\": \"your test input here\"}' | jq ."

run: ## Run agent with file input (use: make run agent=<name> file=<path>)
    @if [ -z "$(agent)" ]; then \
        echo "$(RED)Error: agent parameter required$(NC)"; \
        echo "Usage: make run agent=swarm-converter file=docker-compose.yml"; \
        exit 1; \
    fi
    @if [ -z "$(file)" ]; then \
        echo "$(RED)Error: file parameter required$(NC)"; \
        echo "Usage: make run agent=swarm-converter file=docker-compose.yml"; \
        exit 1; \
    fi
    @if [ ! -f "$(file)" ]; then \
        echo "$(RED)Error: File '$(file)' not found$(NC)"; \
        exit 1; \
    fi
    @port=$$(docker compose port $(agent) 8000 2>/dev/null | cut -d':' -f2); \
    if [ -z "$$port" ]; then \
        echo "$(RED)Agent $(agent) not running$(NC)"; \
        exit 1; \
    fi; \
    echo "$(BLUE)Running $(agent) with file: $(file)$(NC)"; \
    echo "$(YELLOW)Processing...$(NC)"; \
    echo ""; \
    payload=$$(jq -Rs '{input: .}' < "$(file)"); \
    curl -X POST "http://localhost:$$port/process" \
        -H "Content-Type: application/json" \
        -d "$$payload" \
        -s | jq -r '.output // .error // .'

run-full: ## Run agent and show full response (use: make run-full agent=<name> file=<path>)
    @if [ -z "$(agent)" ]; then \
        echo "$(RED)Error: agent parameter required$(NC)"; \
        echo "Usage: make run-full agent=swarm-converter file=docker-compose.yml"; \
        exit 1; \
    fi
    @if [ -z "$(file)" ]; then \
        echo "$(RED)Error: file parameter required$(NC)"; \
        echo "Usage: make run-full agent=swarm-converter file=docker-compose.yml"; \
        exit 1; \
    fi
    @if [ ! -f "$(file)" ]; then \
        echo "$(RED)Error: File '$(file)' not found$(NC)"; \
        exit 1; \
    fi
    @port=$$(docker compose port $(agent) 8000 2>/dev/null | cut -d':' -f2); \
    if [ -z "$$port" ]; then \
        echo "$(RED)Agent $(agent) not running$(NC)"; \
        exit 1; \
    fi; \
    echo "$(BLUE)Running $(agent) with file: $(file)$(NC)"; \
    echo "$(YELLOW)Processing...$(NC)"; \
    echo ""; \
    payload=$$(jq -Rs '{input: .}' < "$(file)"); \
    curl -X POST "http://localhost:$$port/process" \
        -H "Content-Type: application/json" \
        -d "$$payload" \
        -s | jq .

run-raw: ## Run agent and return only extracted result (use: make run-raw agent=<name> file=<path>)
    @if [ -z "$(agent)" ]; then \
        echo "$(RED)Error: agent parameter required$(NC)" >&2; \
        echo "Usage: make run-raw agent=swarm-converter file=docker-compose.yml" >&2; \
        exit 1; \
    fi
    @if [ -z "$(file)" ]; then \
        echo "$(RED)Error: file parameter required$(NC)" >&2; \
        echo "Usage: make run-raw agent=swarm-converter file=docker-compose.yml" >&2; \
        exit 1; \
    fi
    @if [ ! -f "$(file)" ]; then \
        echo "$(RED)Error: File '$(file)' not found$(NC)" >&2; \
        exit 1; \
    fi
    @port=$$(docker compose port $(agent) 8000 2>/dev/null | cut -d':' -f2); \
    if [ -z "$$port" ]; then \
        echo "$(RED)Agent $(agent) not running$(NC)" >&2; \
        exit 1; \
    fi; \
    payload=$$(jq -Rs '{input: .}' < "$(file)"); \
    curl -X POST "http://localhost:$$port/process/raw" \
        -H "Content-Type: application/json" \
        -d "$$payload" \
        -s | jq -r '.output'

run-raw-json: ## Run agent and return extracted result as JSON (use: make run-raw-json agent=<name> file=<path>)
    @if [ -z "$(agent)" ]; then \
        echo "$(RED)Error: agent parameter required$(NC)"; \
        echo "Usage: make run-raw-json agent=swarm-converter file=docker-compose.yml"; \
        exit 1; \
    fi
    @if [ -z "$(file)" ]; then \
        echo "$(RED)Error: file parameter required$(NC)"; \
        echo "Usage: make run-raw-json agent=swarm-converter file=docker-compose.yml"; \
        exit 1; \
    fi
    @if [ ! -f "$(file)" ]; then \
        echo "$(RED)Error: File '$(file)' not found$(NC)"; \
        exit 1; \
    fi
    @port=$$(docker compose port $(agent) 8000 2>/dev/null | cut -d':' -f2); \
    if [ -z "$$port" ]; then \
        echo "$(RED)Agent $(agent) not running$(NC)"; \
        exit 1; \
    fi; \
    echo "$(BLUE)Running $(agent) with file: $(file)$(NC)"; \
    echo "$(YELLOW)Processing...$(NC)"; \
    echo ""; \
    payload=$$(jq -Rs '{input: .}' < "$(file)"); \
    curl -X POST "http://localhost:$$port/process/raw" \
        -H "Content-Type: application/json" \
        -d "$$payload" \
        -s | jq .

health: ## Check health of all agents
    @echo "$(BLUE)Checking Agent Health:$(NC)"
    @echo ""
    @for service in $$(docker compose $(COMPOSE_FILES) ps --format json | jq -r 'select(.Name | contains("agent-")) | .Service'); do \
        echo "$(YELLOW)$$service:$(NC)"; \
        port=$$(docker compose $(COMPOSE_FILES) port $$service 8000 2>/dev/null | cut -d':' -f2); \
        if [ -n "$$port" ]; then \
            curl -s http://localhost:$$port/health | jq -r '"  Status: " + .status + " | Model: " + .model' 2>/dev/null || \
                echo "  $(RED)Unreachable$(NC)"; \
        else \
            echo "  $(RED)Not running$(NC)"; \
        fi; \
        echo ""; \
    done

# ============================================================================
# API Documentation / Swagger
# ============================================================================
docs: ## Open Swagger UI for agent (use: make docs agent=<name>)
    @if [ -z "$(agent)" ]; then \
        echo "$(RED)Error: agent parameter required$(NC)"; \
        echo "Usage: make docs agent=swarm-converter"; \
        exit 1; \
    fi
    @port=$$(docker compose port $(agent) 8000 2>/dev/null | cut -d':' -f2); \
    if [ -n "$$port" ]; then \
        echo "$(BLUE)Opening Swagger UI for $(agent)...$(NC)"; \
        echo "URL: http://localhost:$$port/docs"; \
        xdg-open "http://localhost:$$port/docs" 2>/dev/null || \
        open "http://localhost:$$port/docs" 2>/dev/null || \
        echo "$(YELLOW)Please open: http://localhost:$$port/docs$(NC)"; \
    else \
        echo "$(RED)Agent $(agent) not running$(NC)"; \
    fi

redoc: ## Open ReDoc for agent (use: make redoc agent=<name>)
    @if [ -z "$(agent)" ]; then \
        echo "$(RED)Error: agent parameter required$(NC)"; \
        echo "Usage: make redoc agent=swarm-converter"; \
        exit 1; \
    fi
    @port=$$(docker compose port $(agent) 8000 2>/dev/null | cut -d':' -f2); \
    if [ -n "$$port" ]; then \
        echo "$(BLUE)Opening ReDoc for $(agent)...$(NC)"; \
        echo "URL: http://localhost:$$port/redoc"; \
        xdg-open "http://localhost:$$port/redoc" 2>/dev/null || \
        open "http://localhost:$$port/redoc" 2>/dev/null || \
        echo "$(YELLOW)Please open: http://localhost:$$port/redoc$(NC)"; \
    else \
        echo "$(RED)Agent $(agent) not running$(NC)"; \
    fi

openapi: ## View OpenAPI schema for agent (use: make openapi agent=<name>)
    @if [ -z "$(agent)" ]; then \
        echo "$(RED)Error: agent parameter required$(NC)"; \
        echo "Usage: make openapi agent=swarm-converter"; \
        exit 1; \
    fi
    @port=$$(docker compose port $(agent) 8000 2>/dev/null | cut -d':' -f2); \
    if [ -n "$$port" ]; then \
        curl -s http://localhost:$$port/openapi.json | jq .; \
    else \
        echo "$(RED)Agent $(agent) not running$(NC)"; \
    fi

# ============================================================================
# Agent Management
# ============================================================================
agent-info: ## Get agent info (use: make agent-info agent=<name>)
    @if [ -z "$(agent)" ]; then \
        echo "$(RED)Error: agent parameter required$(NC)"; \
        exit 1; \
    fi
    @echo "$(BLUE)Agent Info: $(agent)$(NC)"
    @port=$$(docker compose port $(agent) 8000 | cut -d':' -f2); \
    curl -s http://localhost:$$port/info | jq .

agent-context: ## View agent context (use: make agent-context agent=<name>)
    @if [ -z "$(agent)" ]; then \
        echo "$(RED)Error: agent parameter required$(NC)"; \
        exit 1; \
    fi
    @echo "$(BLUE)Agent Context: $(agent)$(NC)"
    @port=$$(docker compose port $(agent) 8000 | cut -d':' -f2); \
    curl -s http://localhost:$$port/context | jq .

agent-clear-context: ## Clear agent context (use: make agent-clear-context agent=<name>)
    @if [ -z "$(agent)" ]; then \
        echo "$(RED)Error: agent parameter required$(NC)"; \
        exit 1; \
    fi
    @echo "$(BLUE)Clearing context for: $(agent)$(NC)"
    @port=$$(docker compose port $(agent) 8000 | cut -d':' -f2); \
    curl -s -X DELETE http://localhost:$$port/context | jq .

# ============================================================================
# Cleanup
# ============================================================================
clean: ## Remove all containers, volumes, and networks
    @echo "$(YELLOW)Warning: This will remove all data!$(NC)"
    @read -p "Are you sure? [y/N] " -n 1 -r; \
    echo; \
    if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
        docker compose $(COMPOSE_FILES) down -v; \
        echo "$(GREEN)✓ Cleanup complete$(NC)"; \
    else \
        echo "$(BLUE)Cancelled$(NC)"; \
    fi

prune: ## Prune unused Docker resources
    @echo "$(BLUE)Pruning Docker resources...$(NC)"
    docker system prune -f
    @echo "$(GREEN)✓ Prune complete$(NC)"

# ============================================================================
# Development
# ============================================================================
shell-ollama: ## Open shell in Ollama container
    docker compose $(COMPOSE_FILES) exec ollama bash

shell-agent: ## Open shell in agent container (use: make shell-agent agent=<name>)
    @if [ -z "$(agent)" ]; then \
        echo "$(RED)Error: agent parameter required$(NC)"; \
        exit 1; \
    fi
    docker compose $(COMPOSE_FILES) exec $(agent) bash

dev-watch: ## Watch logs of all services
    docker compose $(COMPOSE_FILES) logs -f --tail=50

# ============================================================================
# UTILS (New Section)
# ============================================================================
ensure-env-agents:
    @if [ ! -f .env.agents ]; then \
        echo "$(YELLOW)Creating default .env.agents file...$(NC)"; \
        echo "# AGENT_CONFIGURATIONS" > .env.agents; \
        echo "# Example: SWARM_CONVERTER_MODEL=llama3.2" >> .env.agents; \
        echo "# Add your agent-specific environment variables here" >> .env.agents; \
        echo "$(GREEN)✓ .env.agents created. Please review and customize it.$(NC)"; \
    fi

# ============================================================================
# Quick Actions
# ============================================================================
quick-test: up ## Quick start and test swarm-converter
    @echo "$(BLUE)Waiting for services to be ready...$(NC)"
    @sleep 5
    @make test-agent agent=swarm-converter

init: ensure-env-agents ## Initialize project (pull models, start services) - CPU mode
    @echo "$(BLUE)Initializing Ollama Agents project (CPU mode)...$(NC)"
    @make build
    @make up
    @echo "$(YELLOW)Waiting for Ollama to be ready...$(NC)"
    @sleep 10
    @make pull-models
    @make status
    @echo ""
    @echo "$(GREEN)✓ Initialization complete!$(NC)"
    @echo ""
    @echo "$(YELLOW)Next steps:$(NC)"
    @echo "  - Run 'make health' to check agent status"
    @echo "  - Run 'make test-agent agent=swarm-converter' to test the agent"
    @echo "  - Visit http://localhost:8080 for the Backoffice Web UI"
    @echo "  - Check README.md for API usage examples"

init-gpu: ensure-env-agents ## Initialize project with GPU support
    @echo "$(BLUE)Initializing Ollama Agents project (GPU mode)...$(NC)"
    @echo "$(YELLOW)Note: Requires NVIDIA GPU and nvidia-docker runtime$(NC)"
    @make build
    @make up-gpu
    @echo "$(YELLOW)Waiting for Ollama to be ready...$(NC)"
    @sleep 10
    @make pull-models
    @make status
    @echo ""
    @echo "$(GREEN)✓ Initialization complete with GPU!$(NC)"
    @echo ""
    @echo "$(YELLOW)Next steps:$(NC)"
    @echo "  - Run 'make health' to check agent status"
    @echo "  - Run 'make test-agent agent=swarm-converter' to test the agent"
    @echo "  - Visit http://localhost:8080 for the Backoffice Web UI"
    @echo "  - Check README.md for API usage examples"