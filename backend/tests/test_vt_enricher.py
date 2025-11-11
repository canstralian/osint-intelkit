"""Tests for VirusTotal enricher with mocked API responses."""
import pytest
import asyncio
from types import SimpleNamespace
from app.workers import vt_enricher

@pytest.mark.asyncio
async def test_vt_enrich_domain_success(monkeypatch):
    called = {}
    async def fake_fetch(session, url):
        called['url'] = url
        return {
            "data": {
                "attributes": {
                    "reputation": 5,
                    "last_analysis_stats": {"malicious": 0},
                    "categories": {"security": "clean"}
                }
            }
        }

    async def fake_last_enrichment(domain, source):
        return None

    async def fake_add_enrichment(*args, **kwargs):
        pass

    monkeypatch.setattr(vt_enricher, "_fetch", fake_fetch)
    monkeypatch.setattr(vt_enricher, "add_enrichment", fake_add_enrichment)
    monkeypatch.setattr(vt_enricher, "last_enrichment", fake_last_enrichment)
    vt_enricher.VT_API_KEY = "dummy"
    data = await vt_enricher.vt_enrich_domain("example.com")
    assert data["reputation"] == 5
    assert "categories" in data

@pytest.mark.asyncio
async def test_vt_enrich_domain_rate_limit(monkeypatch):
    async def fake_fetch(session, url):
        raise vt_enricher.VTQuota("rate_limited")

    async def fake_last_enrichment(domain, source):
        return None

    async def fake_add_enrichment(*args, **kwargs):
        pass

    monkeypatch.setattr(vt_enricher, "_fetch", fake_fetch)
    monkeypatch.setattr(vt_enricher, "add_enrichment", fake_add_enrichment)
    monkeypatch.setattr(vt_enricher, "last_enrichment", fake_last_enrichment)
    vt_enricher.VT_API_KEY = "dummy"
    out = await vt_enricher.vt_enrich_domain("example.com")
    # Expect None due to fallback failure
    assert out is None
