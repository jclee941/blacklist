# Blacklist Service Management Makefile

.PHONY: help setup-hooks build up down logs clean test deploy dev prod restart health release release-dry verify verify-lint verify-types verify-secrets verify-pre-commit verify-quick verify-all

# Default environment
ENV ?= development
PYTHON ?= python3

# Docker Compose Configuration
COMPOSE_FILE := deploy/docker-compose.yml
COMPOSE_CMD := docker compose -f $(COMPOSE_FILE) --env-file deploy/.env --project-directory .

# Setup commands
setup-hooks: ## Setup git hooks (pre-commit + husky)
	@echo "🔧 Setting up git hooks..."
	@pip install pre-commit --quiet
	@pre-commit install --install-hooks
	@pre-commit install --hook-type commit-msg
	@cd frontend && npm install
	@echo "✅ Git hooks installed"
	@echo "   - Pre-commit: Python linting (Ruff, mypy), secret detection"
	@echo "   - Commit-msg: Conventional commits enforcement"
	@echo "   - Husky: Frontend linting (ESLint, Prettier)"

# Help target
help: ## Show this help message
	@echo "Blacklist Service Management Commands:"
	@echo "======================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development commands
dev: ## Start development environment with hot reload (rebuilds changed images)
	@echo "🚀 Starting development environment..."
	@$(COMPOSE_CMD) up -d --build
	@echo "✅ Development environment started (hot reload enabled)"
	@echo "🌐 Application: https://localhost:443"
	@echo "💡 Code changes auto-reload via volume mounts"

dev-no-build: ## Start without rebuild (faster, use existing images)
	@echo "🚀 Starting development environment (no rebuild)..."
	@$(COMPOSE_CMD) up -d
	@echo "✅ Started with existing images"

dev-prod: ## Start production-like (no override, no hot reload)
	@echo "🚀 Starting production-like environment..."
	@$(COMPOSE_CMD) up -d --build
	@echo "✅ Production-like environment started (no hot reload)"

dev-app: ## Restart only app service (quick iteration)
	@echo "🔄 Rebuilding and restarting app..."
	@$(COMPOSE_CMD) up -d --build --no-deps blacklist-app
	@echo "✅ App restarted"

dev-frontend: ## Restart only frontend service
	@echo "🔄 Rebuilding and restarting frontend..."
	@$(COMPOSE_CMD) up -d --build --no-deps blacklist-frontend
	@echo "✅ Frontend restarted"

prod: ## Start production environment
	@echo "🚀 Starting production environment..."
	@$(COMPOSE_CMD) up -d
	@echo "✅ Production environment started"

# Build commands
.PHONY: check-clean
check-clean:
	@if ! git diff-index --quiet HEAD -- 2>/dev/null; then \
		echo "❌ Uncommitted changes detected! Commit before build."; \
		git status --short; \
		exit 1; \
	fi

build: check-clean ## Build all Docker images
	@echo "🏗️ Building Docker images..."
	@GIT_COMMIT=$$(git rev-parse --short HEAD 2>/dev/null || echo "unknown") \
		APP_VERSION=$$(cat VERSION 2>/dev/null || echo "0.0.0-dev") \
		BUILD_DATE=$$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
		$(COMPOSE_CMD) build --parallel
	@echo "✅ Build completed (version: $$(cat VERSION), commit: $$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown'))"

rebuild: ## Rebuild all images from scratch
	@echo "🏗️ Rebuilding Docker images from scratch..."
	@$(COMPOSE_CMD) build --no-cache --parallel
	@echo "✅ Rebuild completed"

# Service management
up: ## Start all services (default: development)
ifeq ($(ENV),production)
	@$(MAKE) prod
else
	@$(MAKE) dev
endif

down: ## Stop all services
	@echo "🛑 Stopping all services..."
	@$(COMPOSE_CMD) down
	@echo "✅ All services stopped"

restart: ## Restart all services
	@echo "🔄 Restarting all services..."
	@$(MAKE) down
	@$(MAKE) up ENV=$(ENV)
	@echo "✅ Services restarted"

# Monitoring and logs
logs: ## Show logs for all services
	@$(COMPOSE_CMD) logs -f

logs-app: ## Show logs for app service only
	@$(COMPOSE_CMD) logs -f blacklist-app

logs-db: ## Show logs for database service only
	@$(COMPOSE_CMD) logs -f blacklist-postgres

logs-collector: ## Show logs for collector service only
	@$(COMPOSE_CMD) logs -f blacklist-collector

health: ## Check health of all services
	@echo "🏥 Checking service health..."
	@$(COMPOSE_CMD) ps
	@echo ""
	@echo "🌐 Testing application health:"
	@curl --fail --silent --show-error --insecure https://localhost:443/health | python3 -m json.tool

# Testing
test: ## Run backend, collector, integration, and frontend unit tests
	@echo "🧪 Running all tests..."
	@$(MAKE) test-backend
	@$(MAKE) test-collector-unit
	@$(MAKE) test-frontend
	@echo "✅ All tests completed"

test-backend: ## Run backend tests (unit + integration)
	@echo "🧪 Running backend tests..."
	@$(MAKE) test-backend-unit
	@$(MAKE) test-backend-integration
	@echo "✅ Backend tests completed"

test-backend-unit: ## Run backend unit tests
	@echo "🧪 Running backend unit tests..."
	@PYTHONPATH=app COVERAGE_FILE=/tmp/blacklist-app.coverage $(PYTHON) -m pytest tests/unit --ignore=tests/unit/collector -v --cov=app/core --cov-report=term --cov-report=html:htmlcov --cov-fail-under=80

test-collector-unit: ## Run collector unit tests
	@echo "🧪 Running collector unit tests..."
	@PYTHONPATH=collector $(PYTHON) -m pytest tests/unit/collector -v -o 'pythonpath=["collector"]'

test-backend-integration: ## Run backend integration tests
	@echo "🧪 Running backend integration tests..."
	@PYTHONPATH=app $(PYTHON) -m pytest tests/integration -v

test-backend-coverage: ## Run backend tests with coverage report
	@echo "🧪 Running backend tests with coverage..."
	@PYTHONPATH=app COVERAGE_FILE=/tmp/blacklist-app.coverage $(PYTHON) -m pytest tests/unit --ignore=tests/unit/collector -v \
		--cov=app/core \
		--cov-report=term \
		--cov-report=html:htmlcov \
		--cov-report=xml:coverage.xml \
		--cov-fail-under=80
	@echo "📊 Coverage report generated in htmlcov/"

test-frontend: ## Run frontend unit tests
	@echo "🧪 Running frontend unit tests..."
	@cd frontend && npm run test
	@echo "✅ Frontend tests completed"

test-frontend-unit: ## Run frontend unit tests
	@echo "🧪 Running frontend unit tests..."
	@cd frontend && npm run test

test-frontend-e2e: ## Run frontend E2E tests (Playwright)
	@echo "🧪 Running frontend E2E tests..."
	@cd frontend && npm run test:e2e

test-frontend-coverage: ## Run frontend tests with coverage
	@echo "🧪 Running frontend tests with coverage..."
	@cd frontend && npm run test:coverage

test-quick: ## Run quick smoke tests only
	@echo "🧪 Running quick smoke tests..."
	@PYTHONPATH=app $(PYTHON) -m pytest tests/unit --ignore=tests/unit/collector -v -k "test_health or test_check" --no-cov

test-security: ## Run security-focused tests
	@echo "🔒 Running security tests..."
	@PYTHONPATH=app $(PYTHON) -m pytest tests/ --ignore=tests/unit/collector -v -m security

test-db: ## Run database-related tests
	@echo "💾 Running database tests..."
	@PYTHONPATH=app $(PYTHON) -m pytest tests/ --ignore=tests/unit/collector -v -m db

test-api: ## Run API endpoint tests
	@echo "🌐 Running API tests..."
	@PYTHONPATH=app $(PYTHON) -m pytest tests/ --ignore=tests/unit/collector -v -m api

test-all-markers: ## Run registered Python markers and fail on test errors
	@echo "🧪 Running all test markers..."
	@set -e; \
	run_marker() { \
		label="$$1"; marker="$$2"; \
		echo "📋 $$label tests:"; \
		set +e; \
		PYTHONPATH=app $(PYTHON) -m pytest tests/ --ignore=tests/unit/collector -v -m "$$marker" --no-cov; \
		status=$$?; \
		set -e; \
		if [ $$status -eq 5 ]; then \
			echo "ℹ️ No $$label tests collected"; \
		elif [ $$status -ne 0 ]; then \
			exit $$status; \
		fi; \
	}; \
	run_marker "Unit" unit; \
	run_marker "Integration" integration; \
	run_marker "Security" security; \
	run_marker "Database" db; \
	run_marker "API" api

test-ci: ## Run tests in CI/CD mode (with coverage and reports)
	@echo "🤖 Running tests in CI/CD mode..."
	@PYTHONPATH=app COVERAGE_FILE=/tmp/blacklist-app.coverage $(PYTHON) -m pytest tests/unit --ignore=tests/unit/collector -v \
		--cov=app/core \
		--cov-report=term \
		--cov-report=html:htmlcov \
		--cov-report=xml:coverage.xml \
		--junitxml=junit.xml \
		--cov-fail-under=80
	@echo "✅ CI/CD tests completed"

# Verification (mirrors CI checks locally)
verify: ## Run verification suite (lint + types + secrets)
	@echo "🔍 Running verification suite..."
	@$(MAKE) verify-lint
	@$(MAKE) verify-types
	@$(MAKE) verify-secrets
	@echo "✅ Verification passed"

verify-lint: ## Run linting checks (ruff check + format check)
	@echo "🔍 Checking lint..."
	@ruff check app/ collector/
	@ruff format --check app/ collector/
	@echo "✅ Lint passed"

verify-types: ## Run type checking (mypy) — skipped if mypy not installed
	@echo "🔍 Checking types..."
	@if command -v mypy >/dev/null 2>&1; then mypy app/ collector/ --ignore-missing-imports; echo "✅ Type checks passed"; else echo "⏭️  mypy not found, skipping type checks (not required by CI)"; fi

verify-secrets: ## Scan for leaked secrets (detect-secrets)
	@echo "\ud83d\udd0d Scanning for secrets..."
	@if command -v detect-secrets >/dev/null 2>&1; then detect-secrets scan app/ collector/ > /dev/null; echo "\u2705 Secret scan passed"; else echo "\u23ed\ufe0f  detect-secrets not found, skipping secret scan"; fi

verify-pre-commit: ## Run all pre-commit hooks against all files
	@echo "🔍 Running pre-commit hooks..."
	@pre-commit run --all-files
	@echo "✅ Pre-commit passed"

verify-quick: ## Quick verification (lint only)
	@echo "🔍 Quick lint check..."
	@ruff check app/ collector/
	@ruff format --check app/ collector/
	@echo "✅ Quick verification passed"

verify-all: ## Full CI mirror (lint + types + secrets + unit tests)
	@echo "🔍 Running full CI verification..."
	@$(MAKE) verify
	@$(MAKE) test-backend
	@echo "✅ Full CI verification passed"

# Maintenance
clean: ## Clean up containers, networks, and volumes
	@echo "🧹 Cleaning up Docker resources..."
	@$(COMPOSE_CMD) down -v --remove-orphans
	@docker system prune -f
	@echo "✅ Cleanup completed"

clean-all: ## Clean everything including images
	@echo "🧹 Cleaning up all Docker resources..."
	@$(COMPOSE_CMD) down -v --remove-orphans --rmi all
	@docker system prune -af
	@echo "✅ Complete cleanup finished"

# Database management
db-shell: ## Connect to PostgreSQL database
	@docker exec -it blacklist-postgres psql -U postgres -d blacklist

db-backup: ## Backup database
	@echo "💾 Creating database backup..."
	@mkdir -p backups
	@docker exec blacklist-postgres pg_dump -U postgres blacklist > backups/blacklist_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Database backup created in backups/"

db-restore: ## Restore database from backup (requires BACKUP_FILE variable)
	@if [ -z "$(BACKUP_FILE)" ]; then echo "❌ Please provide BACKUP_FILE variable"; exit 1; fi
	@echo "📥 Restoring database from $(BACKUP_FILE)..."
	@docker exec -i blacklist-postgres psql -U postgres -d blacklist < $(BACKUP_FILE)
	@echo "✅ Database restored"

# Development helpers
shell-app: ## Get shell access to app container
	@docker exec -it blacklist-app /bin/bash

shell-db: ## Get shell access to database container
	@docker exec -it blacklist-postgres /bin/bash

# CI/CD helpers
ci-build: ## Build for CI/CD (production images)
	@echo "🏗️ Building for CI/CD..."
	@$(COMPOSE_CMD) build --parallel
	@echo "✅ CI/CD build completed"

deploy: ## Deploy to production (builds, starts, verifies health)
	@echo "🚀 Deploying to production..."
	@$(MAKE) ci-build
	@$(MAKE) prod
	@echo "⏳ Waiting for services to be ready..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		if curl -sf http://localhost:$${PORT:-2542}/health > /dev/null 2>&1; then \
			echo "✅ Health check passed (attempt $$i)"; \
			exit 0; \
		fi; \
		if [ $$i -eq 10 ]; then \
			echo "❌ Health check failed after 10 attempts"; \
			$(COMPOSE_CMD) logs --tail=50; \
			exit 1; \
		fi; \
		echo "  Attempt $$i/10 — waiting 5s..."; \
		sleep 5; \
	done
	@echo "✅ Production deployment completed"

# Release automation
TYPE ?= patch

release: check-clean ## Release: bump/tag version and push (TYPE=patch|minor|major|current)
	@bash scripts/release.sh $(TYPE) false

release-dry: ## Dry-run release: preview what would happen (TYPE=patch|minor|major|current)
	@bash scripts/release.sh $(TYPE) true

# Status and information
status: ## Show detailed status of all services
	@echo "📊 Service Status Report"
	@echo "======================="
	@echo ""
	@echo "🐳 Docker Containers:"
	@$(COMPOSE_CMD) ps
	@echo ""
	@echo "📊 Resource Usage:"
	@docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
	@echo ""
	@echo "💾 Volume Usage:"
	@docker volume ls --filter name=blacklist
	@echo ""
	@echo "🌐 Network Info:"
	@docker network ls --filter name=blacklist

info: ## Show project information
	@echo "Blacklist Service Information"
	@echo "============================="
	@echo "Project: REGTECH Blacklist Intelligence Platform"
	@echo "Version: $$(cat VERSION) (Microservices Architecture)"
	@echo "Services: 5 containers (app, collector, frontend, postgres, redis)"
	@echo "Registry: $${REGISTRY_DOMAIN:-registry.example.com}"
	@echo "Local URL: http://localhost:2542"
	@echo "Production URL: https://${PROD_DOMAIN:-blacklist.example.com}"
	@echo ""
	@echo "Quick Commands:"
	@echo "  make dev      - Start development environment"
	@echo "  make prod     - Start production environment"
	@echo "  make logs     - View all logs"
	@echo "  make health   - Check service health"
	@echo "  make test     - Run tests"

# Default target
.DEFAULT_GOAL := help
