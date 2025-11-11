# Contributing to OSINT IntelKit

Thank you for your interest in contributing to OSINT IntelKit! This document provides guidelines and instructions for contributing to the project.

## 🤝 Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

## 🎯 How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce** the issue
- **Expected behavior** vs **actual behavior**
- **Environment details** (OS, Python version, Docker version)
- **Logs and error messages** (use code blocks)
- **Screenshots** if applicable

**Example Bug Report:**
```markdown
## Bug: VirusTotal enrichment fails with rate limit error

**Description:** VT enrichment worker crashes instead of gracefully handling rate limits.

**Steps to Reproduce:**
1. Set VT_RATE_LIMIT=4 in .env
2. Trigger enrichment for 10+ domains
3. Observe crash after 5th request

**Expected:** Worker should wait and retry
**Actual:** Worker crashes with exception

**Environment:**
- OS: Ubuntu 22.04
- Python: 3.11.5
- Docker: 24.0.6

**Logs:**
\`\`\`
ERROR: Rate limit exceeded (429)
Traceback (most recent call last):
  ...
\`\`\`
```

### Suggesting Enhancements

Enhancement suggestions are welcome! Please create an issue with:

- **Clear title** describing the enhancement
- **Use case** explaining why this would be useful
- **Proposed solution** with implementation details
- **Alternatives considered**
- **Additional context** (mockups, examples, etc.)

### Pull Requests

1. **Fork the repository** and create a feature branch:
   ```bash
   git checkout -b feature/amazing-feature
   ```

2. **Make your changes** following our coding standards

3. **Test your changes**:
   ```bash
   make check-all  # Run all quality checks
   make test       # Run test suite
   ```

4. **Commit your changes** with clear messages:
   ```bash
   git commit -m "Add feature: amazing new capability"
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/amazing-feature
   ```

6. **Open a Pull Request** with:
   - Clear description of changes
   - Link to related issues
   - Screenshots/examples if applicable
   - Confirmation that tests pass

## 📋 Development Setup

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git
- Make (optional, for convenience commands)

### Initial Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/canstralian/osint-intelkit.git
   cd osint-intelkit
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   make install-dev
   # Or manually:
   pip install -r backend/requirements.txt
   pip install -r backend/requirements-dev.txt
   ```

4. **Set up pre-commit hooks:**
   ```bash
   make setup-hooks
   # Or manually:
   pre-commit install
   ```

5. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

6. **Start services:**
   ```bash
   make docker-up
   ```

## 🎨 Coding Standards

### Python Style Guide

We follow **PEP 8** with the following specifications:

- **Line length:** 100 characters
- **Indentation:** 4 spaces (no tabs)
- **String quotes:** Double quotes for docstrings
- **Import order:** Standard library → Third-party → Local (automated)
- **Tooling:** Ruff (replaces black + flake8 + isort)

### Ruff - Lightning Fast Linter & Formatter

We use **Ruff** for code formatting and linting. Ruff is **10-100x faster** than traditional tools and replaces:
- black (code formatting)
- isort (import sorting)
- flake8 (linting)
- Plus 700+ additional rules from pylint, pyupgrade, and more

**Format code:**
```bash
make format
# Or:
ruff format backend/app
```

**Lint code:**
```bash
make lint
# Or:
ruff check backend/app
```

**Lint with auto-fix:**
```bash
make lint-fix
# Or:
ruff check backend/app --fix
```

### Type Checking

We use **mypy** for static type checking:

```bash
make type-check
# Or:
mypy backend/app --config-file=pyproject.toml
```

### Security Scanning

We use **bandit** for security analysis:

```bash
make security
# Or:
bandit -r backend/app -c pyproject.toml
```

### Run All Checks

```bash
make check-all
```

This runs: formatting → linting → type checking → security scanning

## ✅ Testing Guidelines

### Writing Tests

- **Test file naming:** `test_*.py`
- **Test class naming:** `class Test<Feature>:`
- **Test function naming:** `def test_<what_it_tests>():`
- **One assertion per test** (when possible)
- **Use fixtures** from `conftest.py` for common setup

**Example:**

```python
import pytest

class TestDomainNormalization:
    """Test domain normalization functionality."""

    def test_normalize_lowercase(self):
        """Test that domains are converted to lowercase."""
        from app.security import normalize_domain
        assert normalize_domain("EXAMPLE.COM") == "example.com"

    def test_normalize_strip_whitespace(self):
        """Test that whitespace is stripped."""
        from app.security import normalize_domain
        assert normalize_domain("  example.com  ") == "example.com"
```

### Running Tests

```bash
# All tests
make test

# With coverage
make test-cov

# Specific file
PEPPER_HEX=$(openssl rand -hex 32) PYTHONPATH=backend pytest backend/tests/test_security.py -v

# Specific test
PEPPER_HEX=$(openssl rand -hex 32) PYTHONPATH=backend pytest backend/tests/test_security.py::TestDomainNormalization::test_normalize_lowercase -v
```

### Test Coverage

- **Minimum coverage:** 80%
- **New features:** Must include tests
- **Bug fixes:** Must include regression test
- **View coverage report:** `htmlcov/index.html`

## 📝 Documentation Standards

### Docstrings

We use **Google-style docstrings**:

```python
def normalize_domain(value: str) -> str:
    """
    Normalize domain name for consistent hashing and comparison.

    Performs the following transformations:
    - Converts to lowercase
    - Strips whitespace
    - Applies IDNA encoding for international domains

    Args:
        value: Raw domain name to normalize.

    Returns:
        Normalized domain name in lowercase ASCII.

    Raises:
        ValueError: If domain format is invalid.

    Example:
        >>> normalize_domain("  EXAMPLE.COM  ")
        'example.com'
        >>> normalize_domain("münchen.de")
        'xn--mnchen-3ya.de'
    """
    value = value.strip().lower()
    try:
        value = idna.encode(value).decode()
    except idna.IDNAError:
        pass
    return value
```

### Code Comments

- **When:** Explain *why*, not *what*
- **Be concise** but clear
- **Update comments** when changing code
- **Avoid obvious comments:**
  ```python
  # Bad:
  x = x + 1  # Increment x

  # Good:
  x = x + 1  # Account for zero-indexing offset
  ```

### README and Documentation

- Keep README.md up-to-date
- Add examples for new features
- Update architecture diagrams if structure changes
- Document new environment variables in .env.example

## 🔒 Security Guidelines

### Never Commit Secrets

- **API keys** go in `.env` (gitignored)
- **Passwords** use environment variables
- **Private keys** never in repository
- Use `detect-private-key` pre-commit hook

### Security Best Practices

- Validate all user input
- Use parameterized queries (no SQL injection)
- Sanitize data before logging
- Follow principle of least privilege
- Rate limit API calls
- Implement proper authentication/authorization

### Reporting Security Issues

**DO NOT** create public issues for security vulnerabilities.

Instead, email: security@yourdomain.com

Include:
- Description of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## 🏗️ Project Structure

```
osint-intelkit/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application
│   │   ├── security.py          # Security primitives
│   │   ├── logging_config.py    # Structured logging
│   │   ├── errors.py            # Error handling
│   │   ├── routers/             # API endpoints
│   │   │   ├── tasks.py         # Task orchestration
│   │   │   ├── domains.py       # Domain queries
│   │   │   └── graph.py         # Graph analysis
│   │   ├── workers/             # Background workers
│   │   │   ├── collector.py    # OSINT collection
│   │   │   └── vt_enricher.py  # VirusTotal enrichment
│   │   ├── flows/               # Prefect orchestration
│   │   │   ├── vt_flow.py       # Main OSINT flow
│   │   │   └── deploy.py        # Deployment config
│   │   └── db/                  # Database modules
│   │       ├── postgres.py      # PostgreSQL operations
│   │       └── neo4j.py         # Neo4j graph operations
│   ├── tests/                   # Test suite
│   ├── requirements.txt         # Production dependencies
│   └── requirements-dev.txt     # Development dependencies
├── sql/
│   └── schema.sql               # Database schema
├── .github/                     # GitHub Actions workflows
├── docker-compose.yml           # Service orchestration
├── Makefile                     # Development commands
├── pyproject.toml               # Tool configuration (Ruff, mypy, pytest)
├── .pre-commit-config.yaml      # Pre-commit hooks
└── .editorconfig                # Editor configuration
```

## 🚀 Adding New Features

### 1. Plan Your Feature

- Create an issue describing the feature
- Discuss approach with maintainers
- Break down into smaller tasks

### 2. Implement

- Create feature branch
- Write code following standards
- Add comprehensive tests
- Update documentation

### 3. Quality Checks

```bash
make format      # Format code
make lint        # Check linting
make type-check  # Type checking
make security    # Security scan
make test        # Run tests
```

### 4. Submit PR

- Clear description
- Link related issues
- Passing CI/CD checks
- Reviewer approval

## 📊 Commit Message Guidelines

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat:** New feature
- **fix:** Bug fix
- **docs:** Documentation changes
- **style:** Code style changes (formatting)
- **refactor:** Code refactoring
- **test:** Test additions/changes
- **chore:** Build process, dependencies

### Examples

```
feat(enrichment): add Shodan API integration

- Implement Shodan enricher worker
- Add rate limiting for Shodan API
- Update documentation with Shodan setup

Closes #42
```

```
fix(collector): handle crt.sh timeout gracefully

Previously, crt.sh timeouts would crash the collector.
Now we catch the exception and log a warning.

Fixes #56
```

## 🎓 Learning Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Prefect Documentation](https://docs.prefect.io/)
- [PEP 8 Style Guide](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/current/)

## 🙏 Recognition

Contributors are recognized in:
- GitHub contributors page
- Release notes
- Project README

Thank you for contributing to OSINT IntelKit! 🎉
