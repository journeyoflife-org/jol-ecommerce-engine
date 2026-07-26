.PHONY: help install dev lint typecheck test test-cov security clean run \
       pytest-fast pytest-security pytest-integration validate pre-commit

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -e .
	npm ci

dev: ## Install development dependencies
	pip install -e ".[dev]"
	npm ci
	pre-commit install

lint: ## Run linters (ruff, eslint)
	ruff check .
	ruff format --check .
	npm run lint

typecheck: ## Run mypy (Python) and tsc (TypeScript)
	PYTHONPATH=backend mypy backend/ --show-error-codes
	npm run typecheck

test: ## Run all tests
	PYTHONPATH=backend pytest tests/ -v --cov=backend/jol_commerce --cov-report=term-missing
	npm run test

test-cov: ## Run tests with coverage (HTML + terminal)
	PYTHONPATH=backend pytest tests/ -v --cov=backend/jol_commerce --cov-report=html --cov-report=term-missing
	npm run test

pytest-fast: ## Run unit tests only (excludes integration and e2e)
	pytest tests/ -v -m "not integration and not e2e"

pytest-security: ## Run security-focused tests only
	pytest tests/ -v -m "security"

pytest-integration: ## Run integration tests only
	pytest tests/ -v -m "integration"

security: ## Run security scanners (bandit, detect-secrets, pip-audit)
	bandit -r backend/jol_commerce -c pyproject.toml
	detect-secrets scan --baseline .secrets.baseline
	pip-audit --ignore-vuln PYSEC-2026-1325

pre-commit: ## Run all pre-commit hooks against all files
	pre-commit run --all-files

# ─────────────────────────────────────────────────────────────────────
# Full local validation — run before opening or updating a PR
# Commands match .github/workflows/ci.yml one-for-one
# ─────────────────────────────────────────────────────────────────────
validate: ## Run full local validation sequence (pre-PR gate)
	@echo "=== 1/9 Backend lint (ruff) ==="
	ruff check .
	ruff format --check .
	@echo "=== 2/9 Type check (mypy) ==="
	PYTHONPATH=backend mypy backend/ --show-error-codes
	@echo "=== 3/9 Security scan (bandit) ==="
	bandit -r backend/jol_commerce -c pyproject.toml
	@echo "=== 4/9 Backend tests with coverage ==="
	PYTHONPATH=backend pytest tests/ -v --cov=backend/jol_commerce --cov-report=term-missing
	@echo "=== 5/9 Frontend lint ==="
	npm run lint
	@echo "=== 6/9 Frontend typecheck ==="
	npm run typecheck
	@echo "=== 7/9 Frontend tests ==="
	npm run test
	@echo "=== 8/9 Security: detect-secrets + pip-audit + PAN check ==="
	detect-secrets scan --baseline .secrets.baseline
	pip-audit --ignore-vuln PYSEC-2026-1325
	bash scripts/verify-no-pan-in-logs.sh --code-only
	@echo "=== 9/9 Pre-commit hooks ==="
	pre-commit run --all-files
	@echo ""
	@echo "All validations passed. Safe to push."

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov .coverage dist build *.egg-info

run: ## Start the development server
	uvicorn jol_commerce.api.app:create_app --factory --reload --host 0.0.0.0 --port 8000
