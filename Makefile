.DEFAULT_GOAL := help
PYTHON        := .venv/bin/python

# ── Help ──────────────────────────────────────────────────────────────────────

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Environment ───────────────────────────────────────────────────────────────

.PHONY: install
install: ## Install dev dependencies into .venv
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements/dev.txt

.PHONY: install-prod
install-prod: ## Install prod dependencies into .venv
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements/prod.txt

.PHONY: outdated
outdated: ## List outdated packages
	.venv/bin/pip list --outdated

# ── Lint ──────────────────────────────────────────────────────────────────────

.PHONY: lint
lint: ## Run pylint over the project
	.venv/bin/pylint app

.PHONY: typecheck
typecheck: ## Run Pyright type checker (includes reportUnknownArgumentType)
	.venv/bin/pyright app

# ── Tests ─────────────────────────────────────────────────────────────────────

.PHONY: test
test: ## Run all tests
	.venv/bin/pytest app/tests --verbosity=2

.PHONY: test-fast
test-fast: ## Run all tests (minimal output)
	.venv/bin/pytest app/tests -q

# ── Dev server ────────────────────────────────────────────────────────────────

.PHONY: run
run: ## Start FastAPI dev server locally
	.venv/bin/fastapi dev app/main.py

# ── Docker ────────────────────────────────────────────────────────────────────

.PHONY: docker-dev
docker-dev: ## Build and run dev container
	docker compose --profile dev up --build

.PHONY: docker-prod
docker-prod: ## Build and run prod container
	docker compose --profile prod up --build

.PHONY: docker-down
docker-down: ## Stop all containers
	docker compose down

# ── Scripts ───────────────────────────────────────────────────────────────────

.PHONY: seed
seed: ## Post sample readings to the dev API (http://localhost:8000)
	$(PYTHON) scripts/seed_readings.py

# ── Combined ──────────────────────────────────────────────────────────────────

.PHONY: ci
ci: lint typecheck test ## Run all checks (lint + typecheck + tests)
