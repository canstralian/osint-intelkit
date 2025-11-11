"""Tests for domain collector worker with passive OSINT operations."""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime
from app.workers import collector


@pytest.mark.asyncio
async def test_collect_domain_success(monkeypatch):
    """Test successful domain collection."""
    domain = "example.com"

    async def fake_save_domain(domain, source, metadata=None):
        return 123

    async def fake_link_domain(domain, metadata=None):
        pass

    async def fake_vt_enrich(domain, **kwargs):
        return {"reputation": 5}

    monkeypatch.setattr("app.workers.collector.save_domain", fake_save_domain)
    monkeypatch.setattr("app.workers.collector.link_domain", fake_link_domain)
    monkeypatch.setattr("app.workers.collector.vt_enrich_domain", fake_vt_enrich)

    result = await collector.collect_domain(domain, source="test")

    assert result["status"] == "success"
    assert result["domain"] == domain
    assert result["domain_id"] == 123
    assert result["source"] == "test"
    assert "timestamp" in result


@pytest.mark.asyncio
async def test_collect_domain_error_handling(monkeypatch):
    """Test domain collection error handling."""
    domain = "example.com"

    async def fake_save_domain(domain, source, metadata=None):
        raise Exception("Database connection failed")

    monkeypatch.setattr("app.workers.collector.save_domain", fake_save_domain)

    result = await collector.collect_domain(domain, source="test")

    assert result["status"] == "error"
    assert result["domain"] == domain
    assert "error" in result
    assert "Database connection failed" in result["error"]


@pytest.mark.asyncio
async def test_collect_from_crtsh_success(monkeypatch):
    """Test successful certificate transparency collection."""
    domain = "example.com"

    mock_certs = [
        {"name_value": "example.com", "id": 1},
        {"name_value": "www.example.com", "id": 2},
        {"name_value": "api.example.com", "id": 3}
    ]

    class FakeResponse:
        status = 200
        async def json(self):
            return mock_certs
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass

    class FakeSession:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def get(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("aiohttp.ClientSession", FakeSession)

    result = await collector.collect_from_crtsh(domain)

    assert result is not None
    assert result["source"] == "crt.sh"
    assert result["certificate_count"] == 3
    assert len(result["certificates"]) == 3


@pytest.mark.asyncio
async def test_collect_from_crtsh_http_error(monkeypatch):
    """Test crt.sh collection with HTTP error."""
    domain = "example.com"

    class FakeResponse:
        status = 500
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass

    class FakeSession:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def get(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("aiohttp.ClientSession", FakeSession)

    result = await collector.collect_from_crtsh(domain)

    assert result is None


@pytest.mark.asyncio
async def test_collect_from_crtsh_timeout(monkeypatch):
    """Test crt.sh collection timeout handling."""
    import asyncio

    domain = "example.com"

    class FakeResponse:
        async def __aenter__(self):
            raise asyncio.TimeoutError("Request timed out")
        async def __aexit__(self, *args):
            pass

    class FakeSession:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def get(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("aiohttp.ClientSession", FakeSession)

    result = await collector.collect_from_crtsh(domain)

    assert result is None


@pytest.mark.asyncio
async def test_collect_subdomains_passive_success(monkeypatch):
    """Test successful passive subdomain collection."""
    domain = "example.com"

    mock_certs = [
        {"name_value": "example.com\nwww.example.com"},
        {"name_value": "api.example.com"},
        {"name_value": "mail.example.com\nadmin.example.com"}
    ]

    async def fake_collect_crtsh(domain):
        return {
            "source": "crt.sh",
            "certificate_count": len(mock_certs),
            "certificates": mock_certs
        }

    monkeypatch.setattr("app.workers.collector.collect_from_crtsh", fake_collect_crtsh)

    result = await collector.collect_subdomains_passive(domain)

    assert result["domain"] == domain
    assert result["subdomain_count"] > 0
    assert "subdomains" in result
    assert "www.example.com" in result["subdomains"]
    assert "api.example.com" in result["subdomains"]
    assert "certificate_transparency" in result["sources"]


@pytest.mark.asyncio
async def test_collect_subdomains_passive_no_results(monkeypatch):
    """Test passive subdomain collection with no results."""
    domain = "example.com"

    async def fake_collect_crtsh(domain):
        return None

    monkeypatch.setattr("app.workers.collector.collect_from_crtsh", fake_collect_crtsh)

    result = await collector.collect_subdomains_passive(domain)

    assert result["domain"] == domain
    assert result["subdomain_count"] == 0
    assert len(result["subdomains"]) == 0


@pytest.mark.asyncio
async def test_collect_subdomains_passive_limit(monkeypatch):
    """Test subdomain collection respects 500 result limit."""
    domain = "example.com"

    # Generate 600 subdomains
    many_subdomains = [f"sub{i}.example.com" for i in range(600)]
    mock_certs = [{"name_value": f"{sd}\n"} for sd in many_subdomains]

    async def fake_collect_crtsh(domain):
        return {
            "source": "crt.sh",
            "certificate_count": len(mock_certs),
            "certificates": mock_certs
        }

    monkeypatch.setattr("app.workers.collector.collect_from_crtsh", fake_collect_crtsh)

    result = await collector.collect_subdomains_passive(domain)

    # Should limit to 500 results
    assert len(result["subdomains"]) <= 500


@pytest.mark.asyncio
async def test_collect_subdomains_filters_non_matching(monkeypatch):
    """Test subdomain collection filters domains not matching parent."""
    domain = "example.com"

    mock_certs = [
        {"name_value": "example.com"},
        {"name_value": "sub.example.com"},
        {"name_value": "different.org"},  # Should be filtered out
        {"name_value": "another.example.com"}
    ]

    async def fake_collect_crtsh(domain):
        return {
            "source": "crt.sh",
            "certificates": mock_certs
        }

    monkeypatch.setattr("app.workers.collector.collect_from_crtsh", fake_collect_crtsh)

    result = await collector.collect_subdomains_passive(domain)

    # Should only include domains matching parent
    assert "different.org" not in result["subdomains"]
    assert "sub.example.com" in result["subdomains"]
    assert "another.example.com" in result["subdomains"]


@pytest.mark.asyncio
async def test_collect_domain_metadata_structure(monkeypatch):
    """Test that collected domain includes proper metadata."""
    domain = "example.com"

    saved_metadata = {}

    async def fake_save_domain(domain, source, metadata=None):
        nonlocal saved_metadata
        saved_metadata = metadata
        return 123

    async def fake_link_domain(domain, metadata=None):
        pass

    async def fake_vt_enrich(domain, **kwargs):
        return {"reputation": 5}

    monkeypatch.setattr("app.workers.collector.save_domain", fake_save_domain)
    monkeypatch.setattr("app.workers.collector.link_domain", fake_link_domain)
    monkeypatch.setattr("app.workers.collector.vt_enrich_domain", fake_vt_enrich)

    result = await collector.collect_domain(domain, source="test")

    # Verify metadata structure
    assert "collection_timestamp" in saved_metadata
    assert "collection_method" in saved_metadata
    assert saved_metadata["collection_method"] == "passive"
