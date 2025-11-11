# OSINT IntelKit Test Suite

Comprehensive test suite for the OSINT IntelKit automation platform.

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Pytest fixtures and configuration
├── test_security.py            # Security module tests (normalization, hashing)
├── test_api_endpoints.py       # FastAPI endpoint tests
├── test_workers.py             # Worker module tests (collectors, enrichers)
├── test_models.py              # Pydantic model validation tests
├── test_logging.py             # Logging configuration tests
└── test_integration.py         # End-to-end integration tests
```

## Running Tests

### Run All Tests

```bash
# From project root
make test

# Or directly with pytest
PEPPER_HEX=$(openssl rand -hex 32) PYTHONPATH=backend pytest -v
```

### Run Specific Test Files

```bash
PEPPER_HEX=$(openssl rand -hex 32) PYTHONPATH=backend pytest backend/tests/test_security.py -v
```

### Run Tests with Coverage

```bash
make test-cov

# Or directly
PEPPER_HEX=$(openssl rand -hex 32) PYTHONPATH=backend pytest --cov=backend/app --cov-report=html --cov-report=term
```

### Run Only Unit Tests

```bash
PEPPER_HEX=$(openssl rand -hex 32) PYTHONPATH=backend pytest -m "not integration and not slow" -v
```

### Run Integration Tests

```bash
# Requires Docker services running
docker compose up -d postgres neo4j
PEPPER_HEX=$(openssl rand -hex 32) PYTHONPATH=backend pytest -m integration -v
```

## Test Categories

### Unit Tests
- **test_security.py**: Domain normalization, HMAC pseudo-IDs, Argon2 hashing
- **test_models.py**: Pydantic model validation
- **test_logging.py**: Logging configuration

### API Tests
- **test_api_endpoints.py**: FastAPI endpoint structure and validation
  - Health checks
  - Task orchestration endpoints
  - Domain data retrieval
  - Graph query endpoints

### Worker Tests
- **test_workers.py**: Background worker functionality
  - Certificate transparency collection (crt.sh)
  - VirusTotal enrichment
  - Error handling

### Integration Tests
- **test_integration.py**: End-to-end workflows
  - Full collection pipeline
  - Database operations
  - Prefect flow execution

## Test Markers

```python
@pytest.mark.unit          # Fast unit tests
@pytest.mark.integration   # Integration tests (require services)
@pytest.mark.slow          # Slow-running tests
@pytest.mark.asyncio       # Async tests
```

## Coverage Goals

- **Target**: 80%+ code coverage
- **Current**: Run `make test-cov` to see current coverage
- **Report**: HTML coverage report in `htmlcov/index.html`

## Writing New Tests

### Example Test Structure

```python
import pytest

class TestMyFeature:
    \"\"\"Test suite for my feature.\"\"\"

    def test_basic_functionality(self):
        \"\"\"Test basic functionality.\"\"\"
        assert True

    @pytest.mark.asyncio
    async def test_async_functionality(self):
        \"\"\"Test async functionality.\"\"\"
        result = await my_async_function()
        assert result is not None
```

### Using Fixtures

```python
def test_with_fixtures(sample_domain, mock_vt_response):
    \"\"\"Test using shared fixtures from conftest.py.\"\"\"
    assert sample_domain == "example.com"
    assert "data" in mock_vt_response
```

## Continuous Integration

Tests are automatically run on:
- Pre-commit hooks (fast unit tests only)
- Pull request validation (full test suite)
- Scheduled nightly builds (including slow tests)

## Troubleshooting

### Common Issues

**Missing PEPPER_HEX:**
```
AssertionError: PEPPER_HEX must be set in environment
```
Solution: Always set PEPPER_HEX when running tests:
```bash
PEPPER_HEX=$(openssl rand -hex 32) pytest
```

**Database Connection Errors:**
Integration tests require PostgreSQL and Neo4j:
```bash
docker compose up -d postgres neo4j
```

**Import Errors:**
Ensure PYTHONPATH includes backend:
```bash
PYTHONPATH=backend pytest
```

## Dependencies

Test-specific dependencies are in `requirements-dev.txt`:
- pytest
- pytest-asyncio
- pytest-cov
- pytest-mock
- httpx (for API testing)
- faker (for test data generation)
