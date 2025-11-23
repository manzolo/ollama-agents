.PHONY: help up down restart build logs ps pull-models test-agent clean health status

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
# Help
# ============================================================================
help: ## Show this help message
	@echo "$(BLUE)╔══════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║           OLLAMA AGENTS - Available Commands                 ║$(NC)"
	@echo "$(BLUE)╚══════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make up                    # Start all services"
	@echo "  make logs agent=swarm-converter"
	@echo "  make test-agent agent=swarm-converter"
	@echo ""

# ============================================================================
# Docker Compose Operations
# ============================================================================
up: ## Start all services
	@echo "$(BLUE)Starting Ollama Agents...$(NC)"
	docker compose up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@make status

down: ## Stop all services
	@echo "$(BLUE)Stopping Ollama Agents...$(NC)"
	docker compose down
	@echo "$(GREEN)✓ Services stopped$(NC)"

restart: ## Restart all services
	@echo "$(BLUE)Restarting Ollama Agents...$(NC)"
	docker compose restart
	@echo "$(GREEN)✓ Services restarted$(NC)"

build: ## Build/rebuild all services
	@echo "$(BLUE)Building services...$(NC)"
	docker compose build --no-cache
	@echo "$(GREEN)✓ Build complete$(NC)"

rebuild: down build up ## Full rebuild: stop, build, start

# ============================================================================
# Logging and Monitoring
# ============================================================================
logs: ## Show logs (use: make logs agent=<name>)
	@if [ -z "$(agent)" ]; then \
		docker compose logs -f; \
	else \
		docker compose logs -f agent-$(agent); \
	fi

logs-ollama: ## Show Ollama service logs
	docker compose logs -f ollama

ps: ## Show running containers
	@echo "$(BLUE)Running Services:$(NC)"
	@docker compose ps

status: ## Show health status of all services
	@echo "$(BLUE)Service Health Status:$(NC)"
	@docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

# ============================================================================
# Ollama Model Management
# ============================================================================
pull-models: ## Pull Ollama models specified in .env
	@echo "$(BLUE)Pulling Ollama models...$(NC)"
	docker compose exec ollama ollama pull llama3.2
	@echo "$(GREEN)✓ Models pulled$(NC)"

pull-model: ## Pull specific model (use: make pull-model model=<name>)
	@if [ -z "$(model)" ]; then \
		echo "$(RED)Error: model parameter required$(NC)"; \
		echo "Usage: make pull-model model=llama3.2"; \
		exit 1; \
	fi
	@echo "$(BLUE)Pulling model: $(model)$(NC)"
	docker compose exec ollama ollama pull $(model)
	@echo "$(GREEN)✓ Model $(model) pulled$(NC)"

list-models: ## List available Ollama models
	@echo "$(BLUE)Available Models:$(NC)"
	docker compose exec ollama ollama list

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
	@curl -s http://localhost:$$(docker compose port agent-$(agent) 8000 | cut -d':' -f2)/health | jq . || \
		echo "$(RED)Health check failed$(NC)"
	@echo ""
	@echo "$(GREEN)To test with input, use:$(NC)"
	@echo "curl -X POST http://localhost:$$(docker compose port agent-$(agent) 8000 | cut -d':' -f2)/process \\"
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
	@for service in $$(docker compose ps --format json | jq -r 'select(.Name | contains("agent-")) | .Service'); do \
		echo "$(YELLOW)$$service:$(NC)"; \
		port=$$(docker compose port $$service 8000 2>/dev/null | cut -d':' -f2); \
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
	@port=$$(docker compose port agent-$(agent) 8000 | cut -d':' -f2); \
	curl -s http://localhost:$$port/info | jq .

agent-context: ## View agent context (use: make agent-context agent=<name>)
	@if [ -z "$(agent)" ]; then \
		echo "$(RED)Error: agent parameter required$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Agent Context: $(agent)$(NC)"
	@port=$$(docker compose port agent-$(agent) 8000 | cut -d':' -f2); \
	curl -s http://localhost:$$port/context | jq .

agent-clear-context: ## Clear agent context (use: make agent-clear-context agent=<name>)
	@if [ -z "$(agent)" ]; then \
		echo "$(RED)Error: agent parameter required$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Clearing context for: $(agent)$(NC)"
	@port=$$(docker compose port agent-$(agent) 8000 | cut -d':' -f2); \
	curl -s -X DELETE http://localhost:$$port/context | jq .

# ============================================================================
# Cleanup
# ============================================================================
clean: ## Remove all containers, volumes, and networks
	@echo "$(YELLOW)Warning: This will remove all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose down -v; \
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
	docker compose exec ollama bash

shell-agent: ## Open shell in agent container (use: make shell-agent agent=<name>)
	@if [ -z "$(agent)" ]; then \
		echo "$(RED)Error: agent parameter required$(NC)"; \
		exit 1; \
	fi
	docker compose exec agent-$(agent) bash

dev-watch: ## Watch logs of all services
	docker compose logs -f --tail=50

# ============================================================================
# Quick Actions
# ============================================================================
quick-test: up ## Quick start and test swarm-converter
	@echo "$(BLUE)Waiting for services to be ready...$(NC)"
	@sleep 5
	@make test-agent agent=swarm-converter

init: ## Initialize project (pull models, start services)
	@echo "$(BLUE)Initializing Ollama Agents project...$(NC)"
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
	@echo "  - Check README.md for API usage examples"
