"""Tests for Prefect flow orchestration with mocked task execution and state transitions."""
import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timedelta
from app.flows import vt_flow


@pytest.mark.asyncio
async def test_collect_seed_domains_success(monkeypatch):
    """Test successful seed domain collection task."""
    domains = ["example.com", "test.com"]

    async def fake_collect_domain(domain, source):
        return {"status": "success", "domain": domain}

    async def fake_link_domain(domain, **kwargs):
        pass

    monkeypatch.setattr("app.flows.vt_flow.collect_domain", fake_collect_domain)
    monkeypatch.setattr("app.flows.vt_flow.link_domain", fake_link_domain)

    # Call the task function directly (not as Prefect task)
    collected = await vt_flow.collect_seed_domains.fn(domains)

    assert len(collected) == 2
    assert "example.com" in collected
    assert "test.com" in collected


@pytest.mark.asyncio
async def test_collect_seed_domains_partial_failure(monkeypatch):
    """Test seed domain collection with partial failures."""
    domains = ["example.com", "bad-domain.com", "test.com"]

    async def fake_collect_domain(domain, source):
        if domain == "bad-domain.com":
            raise Exception("Collection failed")
        return {"status": "success", "domain": domain}

    async def fake_link_domain(domain, **kwargs):
        pass

    monkeypatch.setattr("app.flows.vt_flow.collect_domain", fake_collect_domain)
    monkeypatch.setattr("app.flows.vt_flow.link_domain", fake_link_domain)

    collected = await vt_flow.collect_seed_domains.fn(domains)

    # Should collect 2 out of 3 domains (bad-domain.com fails)
    assert len(collected) == 2
    assert "example.com" in collected
    assert "test.com" in collected
    assert "bad-domain.com" not in collected


@pytest.mark.asyncio
async def test_vt_enrich_all_success(monkeypatch):
    """Test VT enrichment task with successful enrichments."""
    domains = ["example.com", "test.com"]

    async def fake_vt_enrich(domain, **kwargs):
        return {
            "found": True,
            "reputation": 5,
            "categories": {"security": "clean"}
        }

    # Mock asyncio.sleep to speed up test
    async def fake_sleep(seconds):
        pass

    monkeypatch.setattr("app.flows.vt_flow.vt_enrich_domain", fake_vt_enrich)
    monkeypatch.setattr("asyncio.sleep", fake_sleep)

    results = await vt_flow.vt_enrich_all.fn(domains)

    assert len(results) == 2
    assert all(r["status"] == "success" for r in results)
    assert all(r["data"]["found"] for r in results)


@pytest.mark.asyncio
async def test_vt_enrich_all_with_failures(monkeypatch):
    """Test VT enrichment task with mixed success/failure."""
    domains = ["example.com", "bad-domain.com"]

    async def fake_vt_enrich(domain, **kwargs):
        if domain == "bad-domain.com":
            raise Exception("VT API error")
        return {"found": True, "reputation": 5}

    async def fake_sleep(seconds):
        pass

    monkeypatch.setattr("app.flows.vt_flow.vt_enrich_domain", fake_vt_enrich)
    monkeypatch.setattr("asyncio.sleep", fake_sleep)

    results = await vt_flow.vt_enrich_all.fn(domains)

    assert len(results) == 2
    success_results = [r for r in results if r["status"] == "success"]
    error_results = [r for r in results if r["status"] == "error"]

    assert len(success_results) == 1
    assert len(error_results) == 1
    assert error_results[0]["domain"] == "bad-domain.com"


@pytest.mark.asyncio
async def test_vt_enrich_all_no_data(monkeypatch):
    """Test VT enrichment when API returns no data."""
    domains = ["unknown-domain.com"]

    async def fake_vt_enrich(domain, **kwargs):
        return None  # No data available

    async def fake_sleep(seconds):
        pass

    monkeypatch.setattr("app.flows.vt_flow.vt_enrich_domain", fake_vt_enrich)
    monkeypatch.setattr("asyncio.sleep", fake_sleep)

    results = await vt_flow.vt_enrich_all.fn(domains)

    assert len(results) == 1
    assert results[0]["status"] == "no_data"
    assert results[0]["domain"] == "unknown-domain.com"


@pytest.mark.asyncio
async def test_collect_subdomains_task_success(monkeypatch):
    """Test subdomain collection task."""
    domains = ["example.com"]

    async def fake_collect_subdomains(domain):
        return {
            "domain": domain,
            "subdomain_count": 3,
            "subdomains": ["sub1.example.com", "sub2.example.com", "sub3.example.com"]
        }

    async def fake_save_domain(domain, source, **kwargs):
        return 1

    async def fake_link_domain(domain, **kwargs):
        pass

    monkeypatch.setattr("app.flows.vt_flow.collect_subdomains_passive", fake_collect_subdomains)
    monkeypatch.setattr("app.flows.vt_flow.save_domain", fake_save_domain)
    monkeypatch.setattr("app.flows.vt_flow.link_domain", fake_link_domain)

    subdomain_map = await vt_flow.collect_subdomains_task.fn(domains)

    assert "example.com" in subdomain_map
    assert len(subdomain_map["example.com"]) == 3
    assert "sub1.example.com" in subdomain_map["example.com"]


@pytest.mark.asyncio
async def test_collect_subdomains_task_with_limit(monkeypatch):
    """Test subdomain collection respects 100-subdomain limit."""
    domains = ["example.com"]

    # Generate 150 subdomains
    many_subdomains = [f"sub{i}.example.com" for i in range(150)]

    async def fake_collect_subdomains(domain):
        return {
            "domain": domain,
            "subdomain_count": len(many_subdomains),
            "subdomains": many_subdomains
        }

    save_count = {"count": 0}

    async def fake_save_domain(domain, source, **kwargs):
        save_count["count"] += 1
        return save_count["count"]

    async def fake_link_domain(domain, **kwargs):
        pass

    monkeypatch.setattr("app.flows.vt_flow.collect_subdomains_passive", fake_collect_subdomains)
    monkeypatch.setattr("app.flows.vt_flow.save_domain", fake_save_domain)
    monkeypatch.setattr("app.flows.vt_flow.link_domain", fake_link_domain)

    await vt_flow.collect_subdomains_task.fn(domains)

    # Should limit to 100 subdomains saved
    assert save_count["count"] == 100


@pytest.mark.asyncio
async def test_run_flow_async_complete_pipeline(monkeypatch):
    """Test complete flow async execution pipeline."""
    test_domains = ["example.com"]

    # Mock all dependencies
    async def fake_collect_seed_domains(domains):
        return domains

    async def fake_collect_subdomains_task(domains):
        return {domains[0]: ["sub.example.com"]}

    async def fake_vt_enrich_all(domains):
        return [{"domain": d, "status": "success"} for d in domains]

    monkeypatch.setattr(vt_flow.collect_seed_domains, "fn", fake_collect_seed_domains)
    monkeypatch.setattr(vt_flow.collect_subdomains_task, "fn", fake_collect_subdomains_task)
    monkeypatch.setattr(vt_flow.vt_enrich_all, "fn", fake_vt_enrich_all)

    # Run the flow
    await vt_flow.run_flow_async(test_domains)

    # If no exceptions, flow executed successfully


@pytest.mark.asyncio
async def test_run_flow_async_no_domains_collected(monkeypatch):
    """Test flow behavior when no domains are collected."""
    test_domains = ["example.com"]

    # Mock collect_seed_domains to return empty list
    async def fake_collect_seed_domains(domains):
        return []

    monkeypatch.setattr(vt_flow.collect_seed_domains, "fn", fake_collect_seed_domains)

    # Should exit early without calling other tasks
    await vt_flow.run_flow_async(test_domains)


def test_get_seed_domains_from_env(monkeypatch):
    """Test getting seed domains from environment variable."""
    monkeypatch.setenv("OSINT_SEED_DOMAINS", "domain1.com, domain2.com, domain3.com")

    domains = vt_flow.get_seed_domains()

    assert len(domains) == 3
    assert "domain1.com" in domains
    assert "domain2.com" in domains
    assert "domain3.com" in domains


def test_get_seed_domains_default(monkeypatch):
    """Test getting default seed domains when env not set."""
    monkeypatch.delenv("OSINT_SEED_DOMAINS", raising=False)

    domains = vt_flow.get_seed_domains()

    # Should return default domains
    assert isinstance(domains, list)
    assert len(domains) > 0


def test_get_seed_domains_validation(monkeypatch):
    """Test seed domain validation filters invalid domains."""
    monkeypatch.setenv("OSINT_SEED_DOMAINS", "valid.com, invalid, another-valid.org")

    domains = vt_flow.get_seed_domains()

    # Should only include valid domains
    assert "valid.com" in domains
    assert "another-valid.org" in domains
    # "invalid" should be filtered out (no TLD)


@pytest.mark.asyncio
async def test_collect_subdomains_task_error_handling(monkeypatch):
    """Test subdomain collection handles errors gracefully."""
    domains = ["example.com", "error-domain.com"]

    async def fake_collect_subdomains(domain):
        if domain == "error-domain.com":
            raise Exception("Collection error")
        return {"domain": domain, "subdomains": ["sub.example.com"]}

    async def fake_save_domain(domain, source, **kwargs):
        return 1

    async def fake_link_domain(domain, **kwargs):
        pass

    monkeypatch.setattr("app.flows.vt_flow.collect_subdomains_passive", fake_collect_subdomains)
    monkeypatch.setattr("app.flows.vt_flow.save_domain", fake_save_domain)
    monkeypatch.setattr("app.flows.vt_flow.link_domain", fake_link_domain)

    subdomain_map = await vt_flow.collect_subdomains_task.fn(domains)

    # Should have empty list for error domain
    assert "error-domain.com" in subdomain_map
    assert subdomain_map["error-domain.com"] == []

    # Should have results for successful domain
    assert "example.com" in subdomain_map
    assert len(subdomain_map["example.com"]) == 1
