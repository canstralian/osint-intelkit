# OSINT IntelKit Test Suite

Comprehensive test suite for the OSINT IntelKit automation platform.

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Pytest fixtures and configuration
├── test_security.py            # Security module tests (normalization, hashing)
├── test_api_endpoints.py       # Integration tests for FastAPI endpoints
├── test_api_endpoints_unit.py  # Unit tests for FastAPI endpoints (with mocks)
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
- **test_api_endpoints_unit.py**: FastAPI endpoint unit tests with mocked dependencies
  - Mocked database operations
  - Mocked background tasks
  - Precise assertions for expected behavior

### Integration Tests
- **test_api_endpoints.py**: FastAPI endpoint integration tests
  - Tests with real service dependencies
  - Health checks
  - Task orchestration endpoints
  - Domain data retrieval
  - Graph query endpoints
  - Note: May use weak assertions due to external service dependencies

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

## Test Philosophy: Unit vs Integration Tests

### Unit Tests (`test_api_endpoints_unit.py`)
**Purpose:** Fast, isolated tests with mocked dependencies

**Characteristics:**
- All external dependencies (databases, background tasks) are mocked
- Use specific assertions (e.g., `assert status_code == 200`)
- Run independently without external services
- Provide precise control over test conditions
- Fast execution (milliseconds per test)

**Example:**
```python
@pytest.mark.unit
async def test_get_enrichments_success(async_client, mocker, mock_enrichment_data):
    """Test with mocked database - always returns predictable results."""
    mock_db = mocker.patch("app.routers.domains.get_domain_enrichments", 
                           return_value=mock_enrichment_data)
    response = await async_client.get("/domains/example.com/enrichments")
    assert response.status_code == 200  # Precise assertion
```

### Integration Tests (`test_api_endpoints.py`)
**Purpose:** Verify real-world behavior with actual services

**Characteristics:**
- Interact with real databases and services (when available)
- May use weak assertions (e.g., `assert status_code in [200, 500]`)
- Require external services to be running
- Test actual integration points
- Slower execution

**Example:**
```python
@pytest.mark.integration
async def test_collect_endpoint_structure(async_client):
    """Test with real services - may fail if database unavailable."""
    response = await async_client.post("/tasks/collect", json={"domain": "example.com"})
    assert response.status_code in [200, 500]  # Accepts both success and service unavailable
```

### When to Use Each

**Write Unit Tests When:**
- Testing business logic and validation
- You need fast, predictable tests
- You want to test error conditions
- External services are not needed to verify logic

**Write Integration Tests When:**
- Testing actual service integration
- Verifying database schema compatibility
- Testing deployment configurations
- End-to-end workflow validation

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

### Mocking Dependencies

Unit tests use `pytest-mock` to mock external dependencies:

```python
from unittest.mock import AsyncMock

async def test_with_mocked_db(async_client, mocker, mock_enrichment_data):
    \"\"\"Test with mocked database calls.\"\"\"
    # Mock the database function
    mock_db = mocker.patch(
        "app.routers.domains.get_domain_enrichments",
        new_callable=AsyncMock,
        return_value=mock_enrichment_data
    )
    
    # Make request
    response = await async_client.get("/domains/example.com/enrichments")
    
    # Verify mock was called correctly
    assert response.status_code == 200
    mock_db.assert_called_once_with("example.com")
```

**Available Mock Fixtures in conftest.py:**
- `mock_enrichment_data` - Sample database enrichment records
- `mock_graph_data` - Sample Neo4j graph data
- `mock_related_domains` - Sample related domain data
- `mock_vt_response` - VirusTotal API response
- `mock_crtsh_response` - crt.sh API response

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
