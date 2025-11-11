"""Tests for PostgreSQL database operations with mocked connections."""
import pytest
from unittest.mock import AsyncMock, patch
from app.db import postgres

@pytest.mark.asyncio
async def test_save_domain_calls_execute(monkeypatch):
    conn = AsyncMock()
    monkeypatch.setattr(postgres, "get_conn", AsyncMock(return_value=conn))
    await postgres.save_domain("example.com", "test_source")
    conn.execute.assert_called()
    conn.close.assert_called()

@pytest.mark.asyncio
async def test_add_enrichment(monkeypatch):
    conn = AsyncMock()
    monkeypatch.setattr(postgres, "get_conn", AsyncMock(return_value=conn))
    await postgres.add_enrichment("example.com", "vt", "success", {"k":"v"})
    conn.execute.assert_called()
    conn.close.assert_called()
