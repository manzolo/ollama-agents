.PHONY: help wizard up up-gpu down restart build logs ps pull-models test-agent clean health status init init-gpu show-compose-files create-network remove-network

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
NETWORK_NAME := ollama-agents-network

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
AGENT_COMPOSE_FILES := $(wildcard docker-compose.agents/*.yml)
COMPOSE_FILES       := -f docker-compose.yml $(foreach file,$(AGENT_COMPOSE_FILES),-f $(file))
COMPOSE_FILES_GPU   := $(COMPOSE_FILES) -f docker-compose.gpu.yml

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
	@echo ""
	@echo "$(YELLOW)BASIC OPERATIONS$(NC)"
	@echo " $(GREEN)up$(NC)            Start services (CPU mode)"
	@echo " $(GREEN)up-gpu$(NC)        Start services with GPU"
	@echo " $(GREEN)down$(NC)          Stop all services"
	@echo " $(GREEN)restart$(NC)       Restart services"
	@echo " $(GREEN)status$(NC)        Show service status"
	@echo " $(GREEN)health$(NC)        Check agent health"
	@echo ""
	@echo "$(YELLOW)AGENT OPERATIONS$(NC)"
	@echo " $(GREEN)run agent=X file=Y$(NC)           Run agent with file"
	@echo " $(GREEN)test-agent agent=X$(NC)           Test single agent"
	@echo " $(GREEN)logs [agent=X]$(NC)                View logs"
	@echo " $(GREEN)docs agent=X$(NC)                  Open Swagger UI"
	@echo ""
	@echo "$(YELLOW)MODELS & DEV$(NC)"
	@echo " $(GREEN)pull-models$(NC)     Pull default models"
	@echo " $(GREEN)build$(NC)           Build services"
	@echo " $(GREEN)shell-agent agent=X$(NC)           Enter agent container"
	@echo ""
	@echo "$(YELLOW)CLEANUP$(NC)"
	@echo " $(GREEN)clean$(NC)           Remove everything (data + network)"
	@echo ""
	@echo "$(BLUE)For full list: grep '##' Makefile$(NC)"
	@echo ""

# ============================================================================
# Wizard Mode
# ============================================================================
wizard: create-network ## Interactive setup guide
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
up: create-network ## Start all services (CPU mode)
	@echo "$(BLUE)Starting Ollama Agents (CPU mode)...$(NC)"
	docker compose $(COMPOSE_FILES) up -d
	@echo "$(GREEN)Services started$(NC)"
	@make status

up-gpu: create-network ## Start all services with GPU support
	@echo "$(BLUE)Starting Ollama Agents (GPU mode)...$(NC)"
	@echo "$(YELLOW)Requires NVIDIA GPU + nvidia-docker runtime$(NC)"
	docker compose $(COMPOSE_FILES_GPU) up -d
	@echo "$(GREEN)Services started with GPU$(NC)"
	@make status

down: ## Stop all services
	@echo "$(BLUE)Stopping Ollama Agents...$(NC)"
	docker compose $(COMPOSE_FILES) down
	@echo "$(GREEN)Services stopped$(NC)"

restart: up ## Restart all services (CPU)
	@echo "$(BLUE)Restarting services...$(NC)"
	docker compose $(COMPOSE_FILES) restart

restart-gpu: up-gpu ## Restart all services (GPU)
	@echo "$(BLUE)Restarting services (GPU mode)...$(NC)"
	docker compose $(COMPOSE_FILES_GPU) restart

build: create-network ## Build all services
	@echo "$(BLUE)Building services...$(NC)"
	docker compose $(COMPOSE_FILES) build --no-cache
	@echo "$(GREEN)Build complete$(NC)"

# ============================================================================
# Quick Initialization
# ============================================================================
init: create-network build up ## Full init: build + start + pull models (CPU)
	@echo "$(YELLOW)Waiting for Ollama to be ready...$(NC)"
	@sleep 12
	@make pull-models
	@echo ""
	@echo "$(GREEN)Initialization complete!$(NC)"
	@echo "Visit http://localhost:8080 for the Web UI"
	@echo "Run 'make health' to check agents"

init-gpu: create-network build up-gpu ## Full init with GPU support
	@echo "$(YELLOW)Waiting for Ollama to be ready...$(NC)"
	@sleep 12
	@make pull-models
	@echo ""
	@echo "$(GREEN)Initialization complete with GPU!$(NC)"
	@echo "Visit http://localhost:8080"

# ============================================================================
# Models & Utils
# ============================================================================
pull-models: ## Pull default models
	@echo "$(BLUE)Pulling Ollama models...$(NC)"
	docker compose $(COMPOSE_FILES) exec ollama ollama pull llama3.2
	@echo "$(GREEN)Models pulled$(NC)"

status: ## Show running services
	@echo "$(BLUE)Service Status:$(NC)"
	@docker compose $(COMPOSE_FILES) ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

health: ## Check health of all agents
	@echo "$(BLUE)Agent Health Check:$(NC)"
	@for svc in $$(docker compose $(COMPOSE_FILES) ps --services | grep agent-); do \
		echo "$(YELLOW)$$svc$(NC)"; \
		port=$$(docker compose $(COMPOSE_FILES) port $$svc 8000 2>/dev/null | cut -d: -f2); \
		if [ -n "$$port" ]; then \
			curl -s http://localhost:$$port/health | grep -q '"status":"healthy"' && \
				echo " $(GREEN)Healthy$(NC)" || echo " $(RED)Unhealthy$(NC)"; \
		else \
			echo " $(RED)Not running$(NC)"; \
		fi; \
	done

# ============================================================================
# Cleanup
# ============================================================================
clean: ## Remove ALL containers, volumes, networks and data
	@echo "$(RED)WARNING: This will delete ALL data and the Docker network!$(NC)"
	@read -p "Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		docker compose $(COMPOSE_FILES) down -v --remove-orphans; \
		make remove-network; \
		echo "$(GREEN)Full cleanup completed$(NC)"; \
	else \
		echo "$(BLUE)Cleanup cancelled$(NC)"; \
	fi