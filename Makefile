.PHONY: help wizard up up-gpu up-no-ollama down restart restart-gpu restart-no-ollama build logs logs-ollama logs-backoffice ps pull-models test-agent test-api run run-raw shell-agent docs clean health status init init-gpu init-env show-compose-files list-agents create-network remove-network update-version

# ============================================================================
# OLLAMA AGENTS - Makefile
# ============================================================================

.DEFAULT_GOAL := help

# -----------------------------
# Colors 
# -----------------------------
BLUE   := \033[34m
GREEN  := \033[32m
YELLOW := \033[33m
RED    := \033[31m
NC     := \033[0m   # No Color

# -----------------------------
# Docker Network
# -----------------------------
NETWORK_NAME := ollama-agent-network

create-network:
	@docker network inspect $(NETWORK_NAME) >/dev/null 2>&1 || \
		(echo "$(BLUE)Creating Docker network: $(NETWORK_NAME)$(NC)" && \
		 docker network create $(NETWORK_NAME) && \
		 echo "$(GREEN)Network $(NETWORK_NAME) created$(NC)")

remove-network:
	@docker network inspect $(NETWORK_NAME) >/dev/null 2>&1 && \
		(echo "$(YELLOW)Removing Docker network: $(NETWORK_NAME)$(NC)" && \
		 docker network rm $(NETWORK_NAME) && \
		 echo "$(GREEN)Network removed$(NC)") || true

# -----------------------------
# Dynamic Agent Compose Files
# -----------------------------
# Include both example agents (git-tracked) and runtime agents (gitignored)
EXAMPLE_COMPOSE_FILES := $(wildcard examples/compose/*.yml)
RUNTIME_COMPOSE_FILES := $(wildcard runtime/compose/*.yml)
AGENT_COMPOSE_FILES   := $(EXAMPLE_COMPOSE_FILES) $(RUNTIME_COMPOSE_FILES)
# Base compose files (without Ollama service)
COMPOSE_FILES         := -f docker-compose.yml $(foreach file,$(AGENT_COMPOSE_FILES),-f $(file))
COMPOSE_FILES_GPU     := -f docker-compose.yml $(foreach file,$(AGENT_COMPOSE_FILES),-f $(file)) -f docker-compose.gpu.yml
# With Ollama profile enabled
COMPOSE_CMD           := docker compose
COMPOSE_CMD_OLLAMA    := docker compose --profile ollama

# ============================================================================
# Help
# ============================================================================
help: ## Show this help message
	@echo "$(BLUE)╔══════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║          OLLAMA AGENTS - Available Commands                  ║$(NC)"
	@echo "$(BLUE)╚══════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)QUICK START$(NC)"
	@echo " $(GREEN)wizard$(NC)        Interactive setup guide"
	@echo " $(GREEN)init$(NC)          Initialize project (CPU mode)"
	@echo " $(GREEN)init-gpu$(NC)      Initialize with GPU support"
	@echo " $(GREEN)init-env$(NC)      Auto-configure HOST_PROJECT_ROOT"
	@echo ""
	@echo "$(YELLOW)BASIC OPERATIONS$(NC)"
	@echo " $(GREEN)up$(NC)                Start services with Ollama (CPU)"
	@echo " $(GREEN)up-gpu$(NC)            Start services with Ollama + GPU"
	@echo " $(GREEN)up-no-ollama$(NC)      Start without Ollama (external server)"
	@echo " $(GREEN)down$(NC)              Stop all services"
	@echo " $(GREEN)restart$(NC)           Restart services"
	@echo " $(GREEN)restart-no-ollama$(NC) Restart without Ollama"
	@echo " $(GREEN)status$(NC)            Show service status"
	@echo " $(GREEN)health$(NC)            Check agent health"
	@echo ""
	@echo "$(YELLOW)AGENT OPERATIONS$(NC)"
	@echo " $(GREEN)list-agents$(NC)                   List all agents"
	@echo " $(GREEN)test-agent agent=X$(NC)            Test agent health & info"
	@echo " $(GREEN)test-api$(NC)                      Run comprehensive API tests"
	@echo " $(GREEN)run agent=X file=Y$(NC)            Run agent with file (JSON output)"
	@echo " $(GREEN)run-raw agent=X file=Y$(NC)        Run agent with file (raw output)"
	@echo " $(GREEN)logs [agent=X] [follow=true]$(NC)  View logs"
	@echo " $(GREEN)logs-ollama$(NC)                   View Ollama logs"
	@echo " $(GREEN)logs-backoffice$(NC)               View Backoffice logs"
	@echo " $(GREEN)shell-agent agent=X$(NC)           Enter agent shell"
	@echo " $(GREEN)docs agent=X$(NC)                  Open Swagger UI"
	@echo ""
	@echo "$(YELLOW)MODELS & DEV$(NC)"
	@echo " $(GREEN)pull-models$(NC)                   Pull default models"
	@echo " $(GREEN)build$(NC)                         Build services"
	@echo " $(GREEN)show-compose-files$(NC)            Show compose files"
	@echo ""
	@echo "$(YELLOW)CLEANUP$(NC)"
	@echo " $(GREEN)clean$(NC)           Remove everything (data + network)"
	@echo ""
	@echo "$(BLUE)For full list: grep '##' Makefile$(NC)"
	@echo ""

# ============================================================================
# Wizard Mode
# ============================================================================
wizard: init-env create-network ## Interactive setup guide
	@echo "$(BLUE)╔══════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║             OLLAMA AGENTS - Setup Wizard                     ║$(NC)"
	@echo "$(BLUE)╚══════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)Welcome! This wizard will help you get started.$(NC)"
	@echo ""
	@echo "$(BLUE)Step 1: Choose execution mode$(NC)"
	@echo " 1) CPU Mode (works everywhere)"
	@echo " 2) GPU Mode (requires NVIDIA GPU + drivers)"
	@echo ""
	@read -p "Enter choice [1-2] (default: 1): " choice; \
	choice=$${choice:-1}; \
	echo ""; \
	if [ "$$choice" = "2" ]; then \
		echo "$(YELLOW)Checking GPU...$(NC)"; \
		if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then \
			echo "$(GREEN)NVIDIA GPU detected and working$(NC)"; \
		else \
			echo "$(RED)nvidia-smi not available or not working$(NC)"; \
			echo "$(YELLOW)Falling back to CPU mode...$(NC)"; \
			choice=1; \
		fi; \
	fi; \
	\
	echo "$(BLUE)Step 2: Initialize project$(NC)"; \
	echo "$(YELLOW)This will build containers, start services and download models (~5-15 min)$(NC)"; \
	read -p "Continue? [Y/n]: " confirm; confirm=$${confirm:-y}; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		if [ "$$choice" = "2" ]; then \
			echo "$(GREEN)Starting initialization with GPU support...$(NC)"; \
			make init-gpu; \
		else \
			echo "$(GREEN)Starting initialization in CPU mode...$(NC)"; \
			make init; \
		fi; \
	else \
		echo "$(BLUE)Setup cancelled. Run 'make wizard' again when ready.$(NC)"; \
		exit 0; \
	fi; \
	\
	echo ""; \
	echo "$(BLUE)Step 3: All done!$(NC)"; \
	echo "$(YELLOW)Open the Backoffice Web UI at:$(NC) http://localhost:8080"; \
	read -p "Open browser now? [Y/n]: " openui; openui=$${openui:-y}; \
	if [ "$$openui" = "y" ] || [ "$$openui" = "Y" ]; then \
		xdg-open http://localhost:8080 2>/dev/null || open http://localhost:8080 2>/dev/null || start http://localhost:8080 2>/dev/null || echo "Please open: http://localhost:8080"; \
	fi; \
	echo ""; \
	echo "$(GREEN)Setup complete! Run 'make help' for all commands.$(NC)"

# ============================================================================
# Docker Compose Operations
# ============================================================================
up: create-network ## Start all services with Ollama (CPU mode)
	@echo "$(BLUE)Starting Ollama Agents with Ollama service (CPU mode)...$(NC)"
	$(COMPOSE_CMD_OLLAMA) $(COMPOSE_FILES) up -d
	@echo "$(GREEN)Services started$(NC)"
	@echo "$(YELLOW)Waiting for Ollama to be ready...$(NC)"
	@sleep 10
	@make status

up-gpu: create-network ## Start all services with Ollama + GPU support
	@echo "$(BLUE)Starting Ollama Agents with Ollama service (GPU mode)...$(NC)"
	@echo "$(YELLOW)Requires NVIDIA GPU + nvidia-docker runtime$(NC)"
	$(COMPOSE_CMD_OLLAMA) $(COMPOSE_FILES_GPU) up -d
	@echo "$(GREEN)Services started with GPU$(NC)"
	@echo "$(YELLOW)Waiting for Ollama to be ready...$(NC)"
	@sleep 10
	@make status

up-no-ollama: create-network ## Start services WITHOUT Ollama (use external Ollama server)
	@echo "$(BLUE)Starting Ollama Agents (without Ollama service)...$(NC)"
	@echo "$(YELLOW)Make sure OLLAMA_HOST in .env points to your external Ollama server$(NC)"
	$(COMPOSE_CMD) $(COMPOSE_FILES) up -d
	@echo "$(GREEN)Services started (using external Ollama)$(NC)"
	@make status

down: ## Stop all services
	@echo "$(BLUE)Stopping Ollama Agents...$(NC)"
	$(COMPOSE_CMD_OLLAMA) $(COMPOSE_FILES) down
	@echo "$(GREEN)Services stopped$(NC)"

restart: ## Restart all services with Ollama (CPU)
	@echo "$(BLUE)Restarting services with Ollama...$(NC)"
	$(COMPOSE_CMD_OLLAMA) $(COMPOSE_FILES) restart

restart-gpu: ## Restart all services with Ollama (GPU)
	@echo "$(BLUE)Restarting services with Ollama (GPU mode)...$(NC)"
	$(COMPOSE_CMD_OLLAMA) $(COMPOSE_FILES_GPU) restart

restart-no-ollama: ## Restart services without Ollama
	@echo "$(BLUE)Restarting services (without Ollama)...$(NC)"
	$(COMPOSE_CMD) $(COMPOSE_FILES) restart

build: create-network ## Build all services
	@echo "$(BLUE)Building services...$(NC)"
	$(COMPOSE_CMD) $(COMPOSE_FILES) build --no-cache
	@echo "$(GREEN)Build complete$(NC)"

# ============================================================================
# Environment Initialization
# ============================================================================
init-env: ## Auto-detect and configure HOST_PROJECT_ROOT in .env
	@echo "$(BLUE)Configuring environment...$(NC)"
	@PROJECT_PATH=$$(pwd); \
	if [ ! -f .env ]; then \
		if [ ! -f .env.example ]; then \
			echo "$(RED)Error: .env.example not found$(NC)"; \
			exit 1; \
		fi; \
		echo "$(YELLOW)Creating .env from .env.example...$(NC)"; \
		cp .env.example .env; \
		echo "$(GREEN)✓ Created .env file$(NC)"; \
	fi; \
	if grep -q "^HOST_PROJECT_ROOT=" .env; then \
		CURRENT_VALUE=$$(grep "^HOST_PROJECT_ROOT=" .env | cut -d'=' -f2-); \
		if [ "$$CURRENT_VALUE" = "$$PROJECT_PATH" ]; then \
			echo "$(GREEN)✓ HOST_PROJECT_ROOT is already correctly set to: $$PROJECT_PATH$(NC)"; \
		elif [ "$$CURRENT_VALUE" = "__AUTO_DETECTED__" ]; then \
			echo "$(YELLOW)Placeholder detected, setting to: $$PROJECT_PATH$(NC)"; \
			sed -i.bak "s|^HOST_PROJECT_ROOT=.*|HOST_PROJECT_ROOT=$$PROJECT_PATH|" .env && rm -f .env.bak; \
			echo "$(GREEN)✓ HOST_PROJECT_ROOT configured in .env$(NC)"; \
		else \
			echo "$(YELLOW)Current value: $$CURRENT_VALUE$(NC)"; \
			echo "$(YELLOW)Updating to:   $$PROJECT_PATH$(NC)"; \
			sed -i.bak "s|^HOST_PROJECT_ROOT=.*|HOST_PROJECT_ROOT=$$PROJECT_PATH|" .env && rm -f .env.bak; \
			echo "$(GREEN)✓ HOST_PROJECT_ROOT updated in .env$(NC)"; \
		fi; \
	else \
		echo "$(YELLOW)HOST_PROJECT_ROOT not found in .env, adding it...$(NC)"; \
		echo "" >> .env; \
		echo "# Auto-detected host filesystem path" >> .env; \
		echo "HOST_PROJECT_ROOT=$$PROJECT_PATH" >> .env; \
		echo "$(GREEN)✓ HOST_PROJECT_ROOT added to .env$(NC)"; \
	fi

# ============================================================================
# Quick Initialization
# ============================================================================
init: init-env create-network build up ## Full init: auto-configure + build + start + pull models (CPU)
	@echo "$(YELLOW)Waiting for Ollama to be ready...$(NC)"
	@sleep 12
	@make pull-models
	@echo ""
	@echo "$(GREEN)Initialization complete!$(NC)"
	@echo "Visit http://localhost:8080 for the Web UI"
	@echo "Run 'make health' to check agents"

init-gpu: init-env create-network build up-gpu ## Full init with GPU support
	@echo "$(YELLOW)Waiting for Ollama to be ready...$(NC)"
	@sleep 12
	@make pull-models
	@echo ""
	@echo "$(GREEN)Initialization complete with GPU!$(NC)"
	@echo "Visit http://localhost:8080"

# ============================================================================
# Models & Utils
# ============================================================================
pull-models: ## Pull default models (requires Ollama service running)
	@echo "$(BLUE)Pulling Ollama models...$(NC)"
	@if docker ps | grep -q ollama-engine; then \
		$(COMPOSE_CMD_OLLAMA) $(COMPOSE_FILES) exec ollama ollama pull llama3.2; \
		echo "$(GREEN)Models pulled$(NC)"; \
	else \
		echo "$(RED)Error: Ollama service not running$(NC)"; \
		echo "$(YELLOW)Start with: make up or make up-gpu$(NC)"; \
		exit 1; \
	fi

status: ## Show running services
	@echo "$(BLUE)Service Status:$(NC)"
	@$(COMPOSE_CMD) $(COMPOSE_FILES) ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

health: ## Check health of all services
	@echo "$(BLUE)╔══════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║                    System Health Check                       ║$(NC)"
	@echo "$(BLUE)╚══════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)Core Services:$(NC)"
	@printf "  %-25s" "ollama"; \
		docker inspect ollama-engine --format='{{.State.Health.Status}}' 2>/dev/null | grep -q healthy && \
			echo "$(GREEN)✓ healthy$(NC)" || echo "$(RED)✗ unhealthy$(NC)"
	@printf "  %-25s" "backoffice"; \
		docker inspect backoffice --format='{{.State.Health.Status}}' 2>/dev/null | grep -q healthy && \
			echo "$(GREEN)✓ healthy$(NC)" || echo "$(RED)✗ unhealthy$(NC)"
	@echo ""
	@echo "$(YELLOW)Agents:$(NC)"
	@agent_count=0; \
	for container in $$(docker ps --filter "name=agent-" --format "{{.Names}}" 2>/dev/null); do \
		agent_count=$$((agent_count + 1)); \
		printf "  %-25s" "$$container"; \
		health=$$(docker inspect $$container --format='{{.State.Health.Status}}' 2>/dev/null); \
		if [ "$$health" = "healthy" ]; then \
			echo "$(GREEN)✓ healthy$(NC)"; \
		elif [ "$$health" = "starting" ]; then \
			echo "$(YELLOW)⏳ starting$(NC)"; \
		else \
			echo "$(RED)✗ unhealthy$(NC)"; \
		fi; \
	done; \
	if [ $$agent_count -eq 0 ]; then \
		echo "  $(YELLOW)No agents running$(NC)"; \
	fi
	@echo ""

# ============================================================================
# Agent Operations
# ============================================================================
list-agents: ## List all available agents
	@echo "$(BLUE)╔══════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║                    Available Agents                          ║$(NC)"
	@echo "$(BLUE)╚══════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)Running Agents:$(NC)"
	@for container in $$(docker ps --filter "name=agent-" --format "{{.Names}}" 2>/dev/null); do \
		agent_name=$$(echo $$container | sed 's/agent-//'); \
		port=$$(docker port $$container 8000 2>/dev/null | cut -d: -f2); \
		printf "  $(GREEN)✓$(NC) %-20s http://localhost:$$port\n" "$$agent_name"; \
	done
	@echo ""
	@echo "$(YELLOW)Available Compose Files:$(NC)"
	@for file in $(AGENT_COMPOSE_FILES); do \
		agent=$$(basename $$file .yml); \
		printf "  $(BLUE)•$(NC) $$agent\n"; \
	done
	@echo ""

logs: ## View logs (usage: make logs [agent=NAME] [follow=true])
ifndef agent
	@echo "$(BLUE)Showing logs for all services...$(NC)"
	@$(COMPOSE_CMD) $(COMPOSE_FILES) logs $(if $(filter true,$(follow)),-f,--tail=100)
else
	@echo "$(BLUE)Showing logs for agent-$(agent)...$(NC)"
	@docker logs $(if $(filter true,$(follow)),-f,--tail=100) agent-$(agent)
endif

logs-ollama: ## View Ollama logs
	@echo "$(BLUE)Ollama Logs:$(NC)"
	@docker logs --tail=100 ollama-engine

logs-backoffice: ## View Backoffice logs
	@echo "$(BLUE)Backoffice Logs:$(NC)"
	@docker logs --tail=100 backoffice

test-agent: ## Test an agent (usage: make test-agent agent=NAME)
ifndef agent
	@echo "$(RED)Error: agent parameter required$(NC)"
	@echo "Usage: make test-agent agent=swarm-converter"
	@exit 1
endif
	@echo "$(BLUE)Testing agent: $(agent)$(NC)"
	@port=$$(docker port agent-$(agent) 8000 2>/dev/null | cut -d: -f2); \
	if [ -z "$$port" ]; then \
		echo "$(RED)Error: Agent not running or port not found$(NC)"; \
		exit 1; \
	fi; \
	@echo "$(YELLOW)Checking health...$(NC)"
	curl -s http://localhost:$$port/health | jq . || echo "$(RED)Health check failed$(NC)"; \
	echo ""; \
	echo "$(YELLOW)Agent info:$(NC)"; \
	curl -s http://localhost:$$port/ | jq . || echo "$(RED)Info request failed$(NC)"

test-api: ## Run comprehensive API integration tests
	@echo "$(BLUE)Running API Integration Tests...$(NC)"
	@if [ ! -x ./tests/test-api.sh ]; then \
		echo "$(RED)Error: tests/test-api.sh not found or not executable$(NC)"; \
		echo "$(YELLOW)Run: chmod +x tests/test-api.sh$(NC)"; \
		exit 1; \
	fi
	@./tests/test-api.sh

run: ## Run agent with input file (usage: make run agent=NAME file=input.yml)
ifndef agent
	@echo "$(RED)Error: agent parameter required$(NC)"
	@echo "Usage: make run agent=swarm-converter file=docker-compose.yml"
	@exit 1
endif
ifndef file
	@echo "$(RED)Error: file parameter required$(NC)"
	@echo "Usage: make run agent=swarm-converter file=docker-compose.yml"
	@exit 1
endif
	@echo "$(BLUE)Running agent $(agent) with file $(file)...$(NC)"
	@port=$$(docker port agent-$(agent) 8000 2>/dev/null | cut -d: -f2); \
	if [ -z "$$port" ]; then \
		echo "$(RED)Error: Agent not running or port not found$(NC)"; \
		exit 1; \
	fi; \
	jq -n --arg input "$$(cat $(file))" '{input: $$input}' | \
	curl -s -X POST http://localhost:$$port/process \
		-H "Content-Type: application/json" \
		-d @- | jq .

run-raw: ## Run agent with input file and get raw output (usage: make run-raw agent=NAME file=input.yml)
ifndef agent
	@echo "$(RED)Error: agent parameter required$(NC)"
	@echo "Usage: make run-raw agent=swarm-converter file=docker-compose.yml"
	@exit 1
endif
ifndef file
	@echo "$(RED)Error: file parameter required$(NC)"
	@echo "Usage: make run-raw agent=swarm-converter file=docker-compose.yml"
	@exit 1
endif
	@port=$$(docker port agent-$(agent) 8000 2>/dev/null | cut -d: -f2); \
	if [ -z "$$port" ]; then \
		echo "$(RED)Error: Agent not running or port not found$(NC)" >&2; \
		exit 1; \
	fi; \
	jq -n --arg input "$$(cat $(file))" '{input: $$input}' | \
	curl -s -X POST http://localhost:$$port/process/raw/text \
		-H "Content-Type: application/json" \
		-d @-


shell-agent: ## Enter agent container (usage: make shell-agent agent=NAME)
ifndef agent
	@echo "$(RED)Error: agent parameter required$(NC)"
	@echo "Usage: make shell-agent agent=swarm-converter"
	@exit 1
endif
	@echo "$(BLUE)Opening shell in agent-$(agent)...$(NC)"
	@docker exec -it agent-$(agent) /bin/sh

docs: ## Open Swagger docs for agent (usage: make docs agent=NAME)
ifndef agent
	@echo "$(RED)Error: agent parameter required$(NC)"
	@echo "Usage: make docs agent=swarm-converter"
	@exit 1
endif
	@port=$$(docker port agent-$(agent) 8000 2>/dev/null | cut -d: -f2); \
	if [ -z "$$port" ]; then \
		echo "$(RED)Error: Agent not running or port not found$(NC)"; \
		exit 1; \
	fi; \
	echo "$(GREEN)Opening Swagger UI at http://localhost:$$port/docs$(NC)"; \
	xdg-open http://localhost:$$port/docs 2>/dev/null || \
		open http://localhost:$$port/docs 2>/dev/null || \
		start http://localhost:$$port/docs 2>/dev/null || \
		echo "Please open: http://localhost:$$port/docs"

show-compose-files: ## Show which compose files are being used
	@echo "$(BLUE)Active Compose Files:$(NC)"
	@echo "  $(GREEN)•$(NC) docker-compose.yml (main)"
	@for file in $(AGENT_COMPOSE_FILES); do \
		echo "  $(GREEN)•$(NC) $$file"; \
	done
	@echo ""
	@echo "$(YELLOW)Total: $$(echo $(COMPOSE_FILES) | wc -w) files$(NC)"

# ============================================================================
# Cleanup
# ============================================================================
clean: ## Remove ALL containers, volumes, networks and data
	@echo "$(RED)WARNING: This will delete ALL data and the Docker network!$(NC)"
	@read -p "Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		$(COMPOSE_CMD_OLLAMA) $(COMPOSE_FILES) down -v --remove-orphans; \
		make remove-network; \
		echo "$(GREEN)Full cleanup completed$(NC)"; \
	else \
		echo "$(BLUE)Cleanup cancelled$(NC)"; \
	fi

# ============================================================================
# Development Utilities
# ============================================================================
update-version: ## Update frontend version to current git hash (cache busting)
	@echo "$(BLUE)Updating frontend version...$(NC)"
	@chmod +x backoffice/update-version.sh
	@./backoffice/update-version.sh
	@echo "$(GREEN)Version updated! Restart backoffice to apply: make restart$(NC)"