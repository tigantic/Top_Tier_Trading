SHELL := /bin/bash

# Default target: display help
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  bootstrap    - Copy .env.example to .env if needed"
	@echo "  build        - Build all Docker images"
	@echo "  up           - Start all containers in detached mode"
	@echo "  down         - Stop and remove containers"
	@echo "  lint         - Run linters for API and workers"
	@echo "  test         - Run unit tests"
	@echo "  paper        - Run a paper trading backtest"
	@echo "  enable-live  - Enable live trading (requires confirmation)"
	@echo "  logs         - Tail logs from all services"
	@echo "  migrate      - Run database migrations"

.PHONY: bootstrap
bootstrap:
	./scripts/bootstrap.sh

.PHONY: build
build:
	./scripts/build.sh

.PHONY: up
up:
	./scripts/up.sh

.PHONY: down
down:
	./scripts/down.sh

.PHONY: lint
lint:
	./scripts/lint.sh

.PHONY: test
test:
	./scripts/test.sh

.PHONY: paper
paper:
	./scripts/paper.sh

.PHONY: enable-live
enable-live:
	./scripts/enable-live.sh

.PHONY: logs
logs:
	./scripts/logs.sh

.PHONY: migrate
migrate:
	./scripts/migrate.sh
