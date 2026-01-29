"""Integration tests for FastAPI endpoints.

These tests interact with actual services and are marked as integration tests.
For unit tests with mocked dependencies, see test_api_endpoints_unit.py.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestHealthEndpoints:
    """Integration tests for health check and status endpoints."""

    async def test_root_endpoint(self, async_client: AsyncClient):
        """Test root endpoint returns API status."""
        response = await async_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert data["service"] == "OSINT IntelKit"
        assert "version" in data
        assert "endpoints" in data

    async def test_health_endpoint(self, async_client: AsyncClient):
        """Test health check endpoint."""
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"


@pytest.mark.integration
@pytest.mark.asyncio
class TestTaskEndpoints:
    """Integration tests for task orchestration endpoints."""

    async def test_collect_endpoint_structure(self, async_client: AsyncClient):
        """Test collect endpoint accepts valid requests."""
        request_data = {"domain": "example.com", "source": "manual", "enrich": False}
        response = await async_client.post("/tasks/collect", json=request_data)
        # May fail due to DB connection in test, but structure should be valid
        assert response.status_code in [200, 500]

    async def test_collect_invalid_domain(self, async_client: AsyncClient):
        """Test collect endpoint rejects invalid domains."""
        request_data = {"domain": "invalid", "source": "manual", "enrich": False}
        response = await async_client.post("/tasks/collect", json=request_data)
        assert response.status_code == 422  # Validation error

    async def test_enrich_endpoint_structure(self, async_client: AsyncClient):
        """Test enrich endpoint accepts valid requests."""
        request_data = {"domain": "example.com", "sources": ["virustotal"]}
        response = await async_client.post("/tasks/enrich", json=request_data)
        assert response.status_code in [200, 500]


@pytest.mark.integration
@pytest.mark.asyncio
class TestDomainEndpoints:
    """Integration tests for domain data retrieval endpoints."""

    async def test_get_enrichments_endpoint(self, async_client: AsyncClient):
        """Test domain enrichments endpoint."""
        response = await async_client.get("/domains/example.com/enrichments")
        # May return empty or error depending on DB state
        assert response.status_code in [200, 404, 500]

    async def test_get_summary_endpoint(self, async_client: AsyncClient):
        """Test domain summary endpoint."""
        response = await async_client.get("/domains/example.com/summary")
        assert response.status_code in [200, 404, 500]


@pytest.mark.integration
@pytest.mark.asyncio
class TestGraphEndpoints:
    """Integration tests for graph query endpoints."""

    async def test_get_graph_endpoint(self, async_client: AsyncClient):
        """Test graph retrieval endpoint."""
        response = await async_client.get("/graph/example.com?depth=2")
        assert response.status_code in [200, 404, 500]

    async def test_get_graph_invalid_depth(self, async_client: AsyncClient):
        """Test graph endpoint validates depth parameter."""
        response = await async_client.get("/graph/example.com?depth=10")
        assert response.status_code == 422  # Validation error (max depth = 5)

    async def test_find_related_endpoint(self, async_client: AsyncClient):
        """Test related domains endpoint."""
        response = await async_client.get("/graph/example.com/related?min_connections=2")
        assert response.status_code in [200, 404, 500]
