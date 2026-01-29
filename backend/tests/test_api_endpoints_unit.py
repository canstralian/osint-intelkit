"""Unit tests for FastAPI endpoints with mocked dependencies."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient


@pytest.mark.unit
@pytest.mark.asyncio
class TestTaskEndpointsUnit:
    """Unit tests for task orchestration endpoints with mocked dependencies."""

    async def test_collect_endpoint_success(self, async_client: AsyncClient, mocker):
        """Test collect endpoint with mocked background tasks."""
        # Mock the background task functions
        mock_collect = mocker.patch("app.routers.tasks.collect_domain", new_callable=AsyncMock)
        mock_enrich = mocker.patch("app.routers.tasks.vt_enrich_domain", new_callable=AsyncMock)

        request_data = {"domain": "example.com", "source": "manual", "enrich": True}
        response = await async_client.post("/tasks/collect", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["domain"] == "example.com"
        assert data["source"] == "manual"
        assert data["enrichment_enabled"] is True

    async def test_collect_endpoint_without_enrichment(self, async_client: AsyncClient, mocker):
        """Test collect endpoint without enrichment."""
        mock_collect = mocker.patch("app.routers.tasks.collect_domain", new_callable=AsyncMock)
        mock_enrich = mocker.patch("app.routers.tasks.vt_enrich_domain", new_callable=AsyncMock)

        request_data = {"domain": "test.com", "source": "api", "enrich": False}
        response = await async_client.post("/tasks/collect", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["enrichment_enabled"] is False

    async def test_collect_invalid_domain(self, async_client: AsyncClient, mocker):
        """Test collect endpoint rejects invalid domains."""
        request_data = {"domain": "invalid", "source": "manual", "enrich": False}
        response = await async_client.post("/tasks/collect", json=request_data)
        assert response.status_code == 422  # Validation error

    async def test_enrich_endpoint_success(self, async_client: AsyncClient, mocker):
        """Test enrich endpoint with mocked background tasks."""
        mock_enrich = mocker.patch("app.routers.tasks.vt_enrich_domain", new_callable=AsyncMock)

        request_data = {"domain": "example.com", "sources": ["virustotal"]}
        response = await async_client.post("/tasks/enrich", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["domain"] == "example.com"


@pytest.mark.unit
@pytest.mark.asyncio
class TestDomainEndpointsUnit:
    """Unit tests for domain data retrieval endpoints with mocked dependencies."""

    async def test_get_enrichments_success(
        self, async_client: AsyncClient, mocker, mock_enrichment_data
    ):
        """Test domain enrichments endpoint with mocked database."""
        mock_db = mocker.patch(
            "app.routers.domains.get_domain_enrichments",
            new_callable=AsyncMock,
            return_value=mock_enrichment_data,
        )

        response = await async_client.get("/domains/example.com/enrichments")

        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "example.com"
        assert data["count"] == 1
        assert len(data["enrichments"]) == 1
        mock_db.assert_called_once_with("example.com")

    async def test_get_enrichments_empty(self, async_client: AsyncClient, mocker):
        """Test domain enrichments endpoint when no data exists."""
        mock_db = mocker.patch(
            "app.routers.domains.get_domain_enrichments", new_callable=AsyncMock, return_value=[]
        )

        response = await async_client.get("/domains/example.com/enrichments")

        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "example.com"
        assert data["enrichments"] == []
        assert "No enrichments found" in data["message"]

    async def test_get_enrichments_db_error(self, async_client: AsyncClient, mocker):
        """Test domain enrichments endpoint handles database errors."""
        mock_db = mocker.patch(
            "app.routers.domains.get_domain_enrichments",
            new_callable=AsyncMock,
            side_effect=Exception("Database connection failed"),
        )

        response = await async_client.get("/domains/example.com/enrichments")

        assert response.status_code == 500
        data = response.json()
        assert "Database connection failed" in data["detail"]

    async def test_get_summary_success(
        self, async_client: AsyncClient, mocker, mock_enrichment_data
    ):
        """Test domain summary endpoint with mocked database."""
        mock_db = mocker.patch(
            "app.routers.domains.get_domain_enrichments",
            new_callable=AsyncMock,
            return_value=mock_enrichment_data,
        )

        response = await async_client.get("/domains/example.com/summary")

        assert response.status_code == 200
        mock_db.assert_called_once_with("example.com")


@pytest.mark.unit
@pytest.mark.asyncio
class TestGraphEndpointsUnit:
    """Unit tests for graph query endpoints with mocked dependencies."""

    async def test_get_graph_success(self, async_client: AsyncClient, mocker, mock_graph_data):
        """Test graph retrieval endpoint with mocked Neo4j."""
        mock_neo4j = mocker.patch(
            "app.routers.graph.get_domain_graph",
            new_callable=AsyncMock,
            return_value=mock_graph_data,
        )

        response = await async_client.get("/graph/example.com?depth=2")

        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "example.com"
        assert data["depth"] == 2
        assert data["node_count"] == 2
        assert data["relationship_count"] == 1
        mock_neo4j.assert_called_once_with("example.com", 2)

    async def test_get_graph_invalid_depth(self, async_client: AsyncClient, mocker):
        """Test graph endpoint validates depth parameter."""
        response = await async_client.get("/graph/example.com?depth=10")
        assert response.status_code == 422  # Validation error (max depth = 5)

    async def test_get_graph_db_error(self, async_client: AsyncClient, mocker):
        """Test graph endpoint handles database errors."""
        mock_neo4j = mocker.patch(
            "app.routers.graph.get_domain_graph",
            new_callable=AsyncMock,
            side_effect=Exception("Neo4j connection failed"),
        )

        response = await async_client.get("/graph/example.com?depth=2")

        assert response.status_code == 500
        data = response.json()
        assert "Neo4j connection failed" in data["detail"]

    async def test_find_related_success(
        self, async_client: AsyncClient, mocker, mock_related_domains
    ):
        """Test related domains endpoint with mocked Neo4j."""
        mock_neo4j = mocker.patch(
            "app.routers.graph.find_related_domains",
            new_callable=AsyncMock,
            return_value=mock_related_domains,
        )

        response = await async_client.get("/graph/example.com/related?min_connections=2")

        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "example.com"
        assert data["related_count"] == 2
        assert data["min_connections"] == 2
        mock_neo4j.assert_called_once_with("example.com", 2)

    async def test_find_related_db_error(self, async_client: AsyncClient, mocker):
        """Test related domains endpoint handles database errors."""
        mock_neo4j = mocker.patch(
            "app.routers.graph.find_related_domains",
            new_callable=AsyncMock,
            side_effect=Exception("Neo4j query failed"),
        )

        response = await async_client.get("/graph/example.com/related?min_connections=2")

        assert response.status_code == 500
        data = response.json()
        assert "Neo4j query failed" in data["detail"]
