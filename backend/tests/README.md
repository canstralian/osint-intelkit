# OSINT IntelKit Test Suite

Comprehensive pytest suite for validating security, enrichment, persistence, and orchestration logic.

## Quick Start

```bash
# Install dependencies
pip install -r backend/requirements-dev.txt

# Run all tests
PEPPER_HEX=$(openssl rand -hex 32) PYTHONPATH=backend pytest -v

# Run specific test file
pytest backend/tests/test_security.py -v

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term
```

## Test Organization

```
backend/tests/
├── __init__.py                  # Test package initialization
├── test_security.py             # Security primitives (6 tests)
├── test_vt_enricher.py          # VirusTotal enrichment (2 tests)
├── test_postgres.py             # Database operations (2 tests)
├── test_prefect_flows.py        # Flow orchestration (13 tests)
├── test_collector.py            # Passive OSINT collection (10 tests)
└── test_flow_deployment.py      # Deployment config (11 tests, skipped)
```

### Test Modules

#### `test_security.py` - Security Primitives
**Coverage:** Domain normalization, HMAC pseudo-IDs, Argon2 password hashing

- `test_normalize_domain_basic()` - Basic lowercase and trimming
- `test_normalize_domain_idna()` - International domain name (punycode) encoding
- `test_domainin_validation()` - Pydantic model validation
- `test_pseudo_id_deterministic()` - HMAC-based stable pseudonymous IDs
- `test_pseudo_id_requires_pepper()` - Environment variable requirement validation
- `test_salted_hash_unique()` - Argon2id salted hash uniqueness

#### `test_vt_enricher.py` - VirusTotal Enrichment
**Coverage:** API mocking, rate limiting, cache fallback

- `test_vt_enrich_domain_success()` - Successful enrichment with mocked VT API
- `test_vt_enrich_domain_rate_limit()` - Rate limiting and fallback behavior

#### `test_postgres.py` - Database Operations
**Coverage:** Domain persistence, enrichment recording

- `test_save_domain_calls_execute()` - Domain saving with provenance
- `test_add_enrichment()` - Enrichment data recording

#### `test_prefect_flows.py` - Flow Orchestration (13 tests)
**Coverage:** Task execution, state transitions, error handling

**Seed Collection:**
- `test_collect_seed_domains_success()` - Successful batch collection
- `test_collect_seed_domains_partial_failure()` - Partial failure handling

**VT Enrichment Tasks:**
- `test_vt_enrich_all_success()` - Batch enrichment success
- `test_vt_enrich_all_with_failures()` - Mixed success/failure scenarios
- `test_vt_enrich_all_no_data()` - API returns no data

**Subdomain Tasks:**
- `test_collect_subdomains_task_success()` - Passive enumeration
- `test_collect_subdomains_task_with_limit()` - 100-subdomain limit enforcement
- `test_collect_subdomains_task_error_handling()` - Graceful error handling

**Pipeline Integration:**
- `test_run_flow_async_complete_pipeline()` - Full flow execution
- `test_run_flow_async_no_domains_collected()` - Early exit behavior

**Configuration:**
- `test_get_seed_domains_from_env()` - Environment-based config
- `test_get_seed_domains_default()` - Default seed domains
- `test_get_seed_domains_validation()` - Domain validation filtering

#### `test_collector.py` - Passive OSINT Collection (10 tests)
**Coverage:** crt.sh integration, subdomain enumeration, error handling

**Domain Collection:**
- `test_collect_domain_success()` - Successful collection with metadata
- `test_collect_domain_error_handling()` - Database error handling
- `test_collect_domain_metadata_structure()` - Metadata validation

**Certificate Transparency:**
- `test_collect_from_crtsh_success()` - Successful crt.sh query
- `test_collect_from_crtsh_http_error()` - HTTP error handling
- `test_collect_from_crtsh_timeout()` - Timeout handling

**Subdomain Enumeration:**
- `test_collect_subdomains_passive_success()` - CT log parsing
- `test_collect_subdomains_passive_no_results()` - Empty results
- `test_collect_subdomains_passive_limit()` - 500-subdomain limit
- `test_collect_subdomains_filters_non_matching()` - Domain filtering

#### `test_flow_deployment.py` - Deployment Configuration (11 tests, skipped)
**Coverage:** Scheduling, deployment registration

**Status:** ⏭️ Skipped - Prefect 3.x API migration needed

Tests cover interval/cron scheduling, deployment creation, and environment configuration.
These tests are skipped when Prefect 3.x is installed due to deprecated `Deployment` API.

## Environment Setup

### Required Environment Variables

```bash
# Security (required for security tests)
export PEPPER_HEX=$(openssl rand -hex 32)

# Optional (tests use mocks, but real values needed for integration tests)
export POSTGRES_URL="postgresql://user:pass@localhost:5432/osint_test"
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="test-password"
export API_KEY_VT="your-virustotal-api-key"
```

### Example `.env.test`

```bash
# Copy to .env.test and customize
PEPPER_HEX=<generate with: openssl rand -hex 32>
POSTGRES_URL=postgresql://postgres:postgres@localhost:5432/osint_test
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=test-password
API_KEY_VT=dummy-key-for-testing
ENABLE_AUDIT_LOG=false
```

## Running Tests

### Basic Usage

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest backend/tests/test_security.py

# Run specific test
pytest backend/tests/test_security.py::test_normalize_domain_basic

# Run tests matching pattern
pytest -k "test_vt_" -v
```

### Advanced Usage

```bash
# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term-missing

# Run with detailed output
pytest -vv --tb=long

# Run only failed tests from last run
pytest --lf

# Run failed tests first
pytest --ff

# Stop on first failure
pytest -x

# Run in parallel (requires pytest-xdist)
pytest -n auto
```

### Filtering Tests

```bash
# Run only async tests
pytest -m asyncio

# Skip slow tests
pytest -m "not slow"

# Run only integration tests
pytest -m integration

# Skip deployment tests
pytest --ignore=backend/tests/test_flow_deployment.py
```

## Mocking Strategy

The test suite uses comprehensive mocking to avoid external dependencies:

### Database Mocking
```python
# Example: Mocking PostgreSQL connections
from unittest.mock import AsyncMock

async def fake_get_conn():
    return AsyncMock()

monkeypatch.setattr("app.db.postgres.get_conn", fake_get_conn)
```

### API Mocking
```python
# Example: Mocking VirusTotal API
async def fake_vt_enrich(domain, **kwargs):
    return {"reputation": 5, "found": True}

monkeypatch.setattr("app.workers.vt_enricher.vt_enrich_domain", fake_vt_enrich)
```

### HTTP Client Mocking
```python
# Example: Mocking aiohttp sessions
class FakeSession:
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass
    def get(self, url, **kwargs):
        return FakeResponse()

monkeypatch.setattr("aiohttp.ClientSession", FakeSession)
```

## Test Guidelines

### Writing New Tests

1. **Use descriptive names:**
   ```python
   # Good
   def test_collect_domain_handles_database_timeout():
       ...

   # Bad
   def test_collection():
       ...
   ```

2. **Follow AAA pattern (Arrange, Act, Assert):**
   ```python
   def test_normalize_domain_basic():
       # Arrange
       input_domain = "Example.COM"

       # Act
       result = normalize_domain(input_domain)

       # Assert
       assert result == "example.com"
   ```

3. **Mock external dependencies:**
   - Always mock: Database connections, API calls, file I/O
   - Never mock: Code under test, simple utilities

4. **Use fixtures for common setup:**
   ```python
   @pytest.fixture
   async def mock_db_connection():
       conn = AsyncMock()
       yield conn
       await conn.close()
   ```

5. **Test both success and failure paths:**
   ```python
   # Test success
   def test_collect_domain_success():
       ...

   # Test failures
   def test_collect_domain_database_error():
       ...

   def test_collect_domain_timeout():
       ...
   ```

### Async Test Guidelines

```python
import pytest

# Mark async tests
@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_function()
    assert result is not None

# Mock async functions
async def fake_async_call():
    return {"status": "success"}

monkeypatch.setattr("module.async_func", fake_async_call)
```

## Continuous Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r backend/requirements.txt
        pip install -r backend/requirements-dev.txt

    - name: Run tests
      env:
        PEPPER_HEX: ${{ secrets.PEPPER_HEX }}
        PYTHONPATH: backend
      run: |
        pytest -v --cov=app --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## Troubleshooting

### Common Issues

#### 1. `ModuleNotFoundError: No module named 'app'`
**Solution:** Set PYTHONPATH
```bash
export PYTHONPATH=/path/to/osint-intelkit/backend
# OR
PYTHONPATH=backend pytest
```

#### 2. `AssertionError: PEPPER_HEX must be set`
**Solution:** Generate and set PEPPER_HEX
```bash
export PEPPER_HEX=$(openssl rand -hex 32)
```

#### 3. Tests hang or timeout
**Solution:** Check for unawait'ed coroutines
```bash
pytest -v --tb=short  # Shows where tests hang
```

#### 4. Import errors with Prefect
**Issue:** Prefect 3.x deprecated `Deployment` API
**Solution:** Tests automatically skip with informative message
```bash
# To see skip reasons:
pytest -v -rs
```

#### 5. `RuntimeWarning: coroutine was never awaited`
**Solution:** Ensure async mocks return awaitable objects
```python
# Wrong
def fake_func():
    return {"result": "value"}

# Correct
async def fake_func():
    return {"result": "value"}
```

## Coverage Goals

| Module | Current | Target |
|--------|---------|--------|
| Security | ~95% | 95%+ |
| VT Enricher | ~70% | 85%+ |
| PostgreSQL | ~60% | 80%+ |
| Prefect Flows | ~80% | 90%+ |
| Collector | ~85% | 90%+ |
| **Overall** | **~75%** | **85%+** |

### Measuring Coverage

```bash
# Generate HTML coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html

# Terminal coverage report
pytest --cov=app --cov-report=term-missing

# Enforce minimum coverage
pytest --cov=app --cov-fail-under=80
```

## Contributing

### Adding New Tests

1. Create test file following naming convention: `test_<module>.py`
2. Import required modules and fixtures
3. Write tests following AAA pattern
4. Mock all external dependencies
5. Run tests locally: `pytest backend/tests/test_<module>.py -v`
6. Update this README if adding new test categories

### Test Review Checklist

- [ ] Test names are descriptive
- [ ] External dependencies are mocked
- [ ] Both success and failure paths tested
- [ ] Async tests properly marked with `@pytest.mark.asyncio`
- [ ] No hardcoded credentials or secrets
- [ ] Tests are isolated (no shared state)
- [ ] Documentation strings explain what is tested
- [ ] Tests run in < 1s each (unless integration test)

## Known Limitations

### Prefect 3.x Compatibility
- `test_flow_deployment.py` skipped due to deprecated API
- Workaround: Tests skip gracefully with informative message
- Long-term: Migrate to `flow.deploy()` API

### Integration Tests
- Current tests use comprehensive mocking
- Real database/Neo4j tests require Docker Compose setup
- Plan: Add `tests/integration/` directory for E2E tests

### Performance Tests
- No load/stress tests currently
- Plan: Add performance benchmarks for rate limiting

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Prefect Testing Guide](https://docs.prefect.io/latest/guides/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review existing test examples
3. Open an issue on GitHub
4. Contact the development team

---

**Last Updated:** 2025-11-11
**Test Count:** 43 tests (33 passing, 11 skipped)
**Python Version:** 3.11+
**Pytest Version:** 9.0+
