"""Pytest configuration and shared fixtures."""

import os
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient

# Set test environment variables
os.environ["PEPPER_HEX"] = "a" * 64  # 32 bytes hex
os.environ["POSTGRES_URL"] = "postgresql://test:test@localhost:5432/testdb"
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USER"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "testpass"
os.environ["API_KEY_VT"] = "test_api_key"


@pytest.fixture
def sample_domain() -> str:
    """Return a sample domain for testing."""
    return "example.com"


@pytest.fixture
def sample_domains() -> list[str]:
    """Return a list of sample domains for testing."""
    return ["example.com", "test.com", "malicious.example"]


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client for testing FastAPI endpoints."""
    from app.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_vt_response() -> dict:
    """Return a mock VirusTotal API response."""
    return {
        "data": {
            "id": "example.com",
            "type": "domain",
            "attributes": {
                "last_dns_records": [
                    {"type": "A", "value": "93.184.216.34"},
                    {"type": "MX", "value": "mail.example.com"},
                ],
                "last_analysis_stats": {
                    "harmless": 80,
                    "malicious": 2,
                    "suspicious": 0,
                    "undetected": 18,
                },
                "reputation": 0,
                "categories": {"Alexa": "reference"},
            },
        }
    }


@pytest.fixture
def mock_crtsh_response() -> list[dict]:
    """Return a mock crt.sh API response."""
    return [
        {"name_value": "example.com"},
        {"name_value": "www.example.com"},
        {"name_value": "api.example.com"},
        {"name_value": "*.example.com"},
    ]


@pytest.fixture
def mock_enrichment_data() -> list[dict]:
    """Return mock enrichment data for database queries."""
    return [
        {
            "domain": "example.com",
            "source": "virustotal",
            "data": {"reputation": 0, "malicious": 2},
            "timestamp": "2024-01-01T00:00:00",
        }
    ]


@pytest.fixture
def mock_graph_data() -> dict:
    """Return mock graph data for Neo4j queries."""
    return {
        "nodes": [
            {"id": "example.com", "type": "domain"},
            {"id": "93.184.216.34", "type": "ip"},
        ],
        "relationships": [{"source": "example.com", "target": "93.184.216.34", "type": "RESOLVES_TO"}],
    }


@pytest.fixture
def mock_related_domains() -> list[dict]:
    """Return mock related domains data."""
    return [
        {"domain": "related.com", "shared_connections": 3},
        {"domain": "similar.com", "shared_connections": 2},
    ]
