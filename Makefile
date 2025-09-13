# VPN Bot Makefile

.PHONY: help build up down restart logs clean test lint format migrate backup

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build all Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## Show logs from all services
	docker-compose logs -f

logs-bot: ## Show logs from bot service
	docker-compose logs -f bot

logs-api: ## Show logs from API service
	docker-compose logs -f api

logs-worker: ## Show logs from Celery worker
	docker-compose logs -f celery_worker

clean: ## Clean up Docker images and volumes
	docker-compose down -v --rmi all
	docker system prune -f

test: ## Run tests
	docker-compose exec bot python -m pytest tests/

lint: ## Run linting
	docker-compose exec bot python -m flake8 bot/ services/ database/ tasks/
	docker-compose exec bot python -m black --check bot/ services/ database/ tasks/

format: ## Format code
	docker-compose exec bot python -m black bot/ services/ database/ tasks/

migrate: ## Run database migrations
	docker-compose exec bot python -m alembic upgrade head

migrate-create: ## Create new migration
	@read -p "Enter migration name: " name; \
	docker-compose exec bot python -m alembic revision --autogenerate -m "$$name"

migrate-downgrade: ## Downgrade database migration
	docker-compose exec bot python -m alembic downgrade -1

backup: ## Create database backup
	docker-compose exec bot python -c "from tasks.backup import backup_database; backup_database()"

shell-bot: ## Open shell in bot container
	docker-compose exec bot /bin/bash

shell-db: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U admin -d vpn_bot

redis-cli: ## Open Redis CLI
	docker-compose exec redis redis-cli

flower: ## Open Flower (Celery monitoring)
	@echo "Opening Flower at http://localhost:5555"
	@open http://localhost:5555 || xdg-open http://localhost:5555 || echo "Please open http://localhost:5555 in your browser"

grafana: ## Open Grafana dashboard
	@echo "Opening Grafana at http://localhost:3000"
	@open http://localhost:3000 || xdg-open http://localhost:3000 || echo "Please open http://localhost:3000 in your browser"

prometheus: ## Open Prometheus
	@echo "Opening Prometheus at http://localhost:9090"
	@open http://localhost:9090 || xdg-open http://localhost:9090 || echo "Please open http://localhost:9090 in your browser"

api-docs: ## Open API documentation
	@echo "Opening API docs at http://localhost:8000/docs"
	@open http://localhost:8000/docs || xdg-open http://localhost:8000/docs || echo "Please open http://localhost:8000/docs in your browser"

setup: ## Initial setup - create .env and start services
	@if [ ! -f .env ]; then \
		echo "Creating .env from template..."; \
		cp .env.example .env; \
		echo "Please edit .env with your configuration"; \
	fi
	@echo "Starting services..."
	make up
	@echo "Waiting for services to start..."
	sleep 10
	@echo "Running database migrations..."
	make migrate
	@echo "Setup complete!"

dev: ## Start development environment
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

prod: ## Start production environment
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

status: ## Show service status
	docker-compose ps

stats: ## Show container stats
	docker stats

update: ## Update and restart services
	git pull
	docker-compose build
	docker-compose up -d
	make migrate

# Development helpers
install-pre-commit: ## Install pre-commit hooks
	pip install pre-commit
	pre-commit install

check: ## Run all checks (lint, test, etc.)
	make lint
	make test

# Backup and restore
backup-full: ## Full backup (database + files)
	mkdir -p backups
	make backup
	docker run --rm -v vpn_bot_postgres_data:/data -v $(PWD)/backups:/backup alpine tar czf /backup/postgres_data_$(shell date +%Y%m%d_%H%M%S).tar.gz -C /data .

restore-db: ## Restore database from backup
	@read -p "Enter backup file path: " file; \
	docker-compose exec -T postgres psql -U admin -d vpn_bot < "$$file"

# Monitoring
monitor: ## Show real-time logs and stats
	@echo "Press Ctrl+C to stop monitoring"
	@(make logs &) && docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

health: ## Check health of all services
	@echo "Checking service health..."
	@docker-compose ps --format table
	@echo ""
	@echo "Database connection:"
	@docker-compose exec postgres pg_isready -U admin -d vpn_bot && echo "✅ PostgreSQL: OK" || echo "❌ PostgreSQL: FAIL"
	@echo "Redis connection:"
	@docker-compose exec redis redis-cli ping && echo "✅ Redis: OK" || echo "❌ Redis: FAIL"
