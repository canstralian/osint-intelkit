# Development Guide

This guide covers setting up a development environment and contributing to OSINT IntelKit.

## Development Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git
- Make (optional)

### Initial Setup

1. **Clone and create virtual environment:**

```bash
git clone https://github.com/canstralian/osint-intelkit.git
cd osint-intelkit
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install dependencies:**

```bash
make install-dev
# Or manually:
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt
```

3. **Set up pre-commit hooks:**

```bash
make setup-hooks
```

4. **Start services:**

```bash
make docker-up
```

## Code Quality Tools

OSINT IntelKit uses **Ruff** for fast linting and formatting, replacing the traditional black + flake8 + isort stack.

### Ruff - Lightning Fast Linter & Formatter

Ruff is 10-100x faster than traditional tools and combines:
- Code formatting (replaces black)
- Import sorting (replaces isort)
- Linting with 700+ rules (replaces flake8, pylint, and more)

**Quick commands:**

```bash
# Format code
make format
# Or: ruff format backend/app

# Lint code
make lint
# Or: ruff check backend/app

# Lint with auto-fix
make lint-fix
# Or: ruff check backend/app --fix

# Run all checks
make check-all
```

### Other Tools

**Type checking (mypy):**
```bash
make type-check
```

**Security scanning (bandit):**
```bash
make security
```

**Testing:**
```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
PEPPER_HEX=$(openssl rand -hex 32) PYTHONPATH=backend pytest backend/tests/test_security.py -v
```

## Coding Standards

### PEP 8 Compliance

- **Line length:** 100 characters
- **Indentation:** 4 spaces (no tabs)
- **Docstrings:** Google style
- **Formatting:** Automated with Ruff

### Ruff Configuration

Ruff is configured in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "N",      # pep8-naming
    "UP",     # pyupgrade
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "SIM",    # flake8-simplify
    "D",      # pydocstyle
]
```

### Type Hints

Use type hints for all function signatures:

```python
from typing import Optional

def normalize_domain(value: str) -> str:
    """Normalize domain name."""
    return value.lower().strip()

async def get_enrichments(domain: str) -> list[dict[str, Any]]:
    """Fetch enrichments for a domain."""
    ...
```

### Docstrings (Google Style)

```python
def pseudo_id(value: str) -> str:
    """
    Generate stable pseudonymous ID via HMAC.

    Args:
        value: Input string to hash.

    Returns:
        Hexadecimal HMAC digest string.

    Raises:
        AssertionError: If PEPPER_HEX not set.

    Example:
        >>> pseudo_id("example.com")
        '8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4'
    """
    assert PEPPER, "PEPPER_HEX must be set in environment"
    v = normalize_domain(value).encode()
    return hmac.new(PEPPER, v, sha256).hexdigest()
```

## Testing

### Writing Tests

Tests are located in `backend/tests/`. Follow these conventions:

- **File naming:** `test_*.py`
- **Class naming:** `class Test<Feature>:`
- **Function naming:** `def test_<what_it_tests>():`

**Example:**

```python
import pytest

class TestDomainNormalization:
    """Test domain normalization functionality."""

    def test_normalize_lowercase(self):
        """Test that domains are converted to lowercase."""
        from app.security import normalize_domain
        assert normalize_domain("EXAMPLE.COM") == "example.com"

    @pytest.mark.asyncio
    async def test_async_function(self, async_client):
        """Test async functionality."""
        response = await async_client.get("/health")
        assert response.status_code == 200
```

### Running Tests

```bash
# All tests
make test

# With coverage
make test-cov
open htmlcov/index.html

# Specific test file
PEPPER_HEX=$(openssl rand -hex 32) PYTHONPATH=backend pytest backend/tests/test_security.py -v

# Specific test
PEPPER_HEX=$(openssl rand -hex 32) PYTHONPATH=backend pytest backend/tests/test_security.py::TestDomainNormalization::test_normalize_lowercase -v
```

## Pre-commit Hooks

Pre-commit hooks run automatically on every commit:

1. **Ruff linter** - Fixes code issues automatically
2. **Ruff formatter** - Formats code
3. **mypy** - Type checking
4. **bandit** - Security scanning
5. **File cleanup** - Trailing whitespace, EOF, etc.

**Manual run:**
```bash
make pre-commit-run
```

## Project Structure

```
osint-intelkit/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── security.py          # Security primitives
│   │   ├── routers/             # API endpoints
│   │   ├── workers/             # Background workers
│   │   ├── flows/               # Prefect orchestration
│   │   └── db/                  # Database modules
│   ├── tests/                   # Test suite
│   ├── requirements.txt         # Production dependencies
│   └── requirements-dev.txt     # Development dependencies
├── docs/                        # Sphinx documentation
├── pyproject.toml               # Tool configuration
└── Makefile                     # Development commands
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed contribution guidelines.

## Resources

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Prefect Documentation](https://docs.prefect.io/)
- [PEP 8 Style Guide](https://pep8.org/)
