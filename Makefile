.PHONY: help install install-dev setup-hooks format lint type-check security test test-cov clean docker-up docker-down

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	pip install -r backend/requirements.txt

install-dev: ## Install development dependencies
	pip install -r backend/requirements.txt
	pip install -r backend/requirements-dev.txt

setup-hooks: ## Install pre-commit hooks
	pre-commit install
	pre-commit install --hook-type commit-msg
	@echo "✅ Pre-commit hooks installed successfully"

format: ## Format code with black and isort
	@echo "🎨 Formatting code with black..."
	black backend/app
	@echo "📦 Sorting imports with isort..."
	isort backend/app
	@echo "✅ Code formatting complete"

lint: ## Run flake8 linting
	@echo "🔍 Running flake8 linter..."
	flake8 backend/app
	@echo "✅ Linting complete"

type-check: ## Run mypy type checking
	@echo "🔎 Running mypy type checker..."
	mypy backend/app
	@echo "✅ Type checking complete"

security: ## Run security scans with bandit
	@echo "🔒 Running bandit security scanner..."
	bandit -r backend/app -c pyproject.toml
	@echo "✅ Security scan complete"

test: ## Run pytest tests
	@echo "🧪 Running tests..."
	PEPPER_HEX=$$(openssl rand -hex 32) PYTHONPATH=backend pytest -v
	@echo "✅ Tests complete"

test-cov: ## Run tests with coverage report
	@echo "🧪 Running tests with coverage..."
	PEPPER_HEX=$$(openssl rand -hex 32) PYTHONPATH=backend pytest --cov=backend/app --cov-report=html --cov-report=term
	@echo "✅ Coverage report generated in htmlcov/"

check-all: format lint type-check security ## Run all code quality checks
	@echo "✅ All checks passed!"

clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf htmlcov/ .coverage
	@echo "✅ Cleanup complete"

docker-up: ## Start Docker services
	docker compose up --build -d
	@echo "✅ Docker services started"

docker-down: ## Stop Docker services
	docker compose down
	@echo "✅ Docker services stopped"

docker-logs: ## View Docker logs
	docker compose logs -f

pre-commit-run: ## Run pre-commit on all files
	pre-commit run --all-files

pre-commit-update: ## Update pre-commit hooks
	pre-commit autoupdate
