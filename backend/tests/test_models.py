"""Tests for Pydantic models and data validation."""

import pytest
from pydantic import ValidationError


class TestCollectionRequest:
    """Test CollectionRequest model."""

    def test_valid_collection_request(self):
        """Test creating a valid collection request."""
        from app.routers.tasks import CollectionRequest

        request = CollectionRequest(domain="example.com", source="manual", enrich=True)
        assert request.domain == "example.com"
        assert request.source == "manual"
        assert request.enrich is True

    def test_collection_request_defaults(self):
        """Test default values for collection request."""
        from app.routers.tasks import CollectionRequest

        request = CollectionRequest(domain="example.com")
        assert request.source == "manual"
        assert request.enrich is False

    def test_invalid_domain_in_collection_request(self):
        """Test that invalid domains are rejected."""
        from app.routers.tasks import CollectionRequest

        with pytest.raises(ValidationError):
            CollectionRequest(domain="invalid")


class TestEnrichmentRequest:
    """Test EnrichmentRequest model."""

    def test_valid_enrichment_request(self):
        """Test creating a valid enrichment request."""
        from app.routers.tasks import EnrichmentRequest

        request = EnrichmentRequest(domain="example.com", sources=["virustotal"])
        assert request.domain == "example.com"
        assert "virustotal" in request.sources

    def test_enrichment_request_defaults(self):
        """Test default enrichment sources."""
        from app.routers.tasks import EnrichmentRequest

        request = EnrichmentRequest(domain="example.com")
        assert request.sources == ["virustotal"]

    def test_multiple_sources(self):
        """Test enrichment with multiple sources."""
        from app.routers.tasks import EnrichmentRequest

        request = EnrichmentRequest(domain="example.com", sources=["virustotal", "shodan"])
        assert len(request.sources) == 2


class TestDomainIn:
    """Test DomainIn security model."""

    def test_domain_in_validation(self):
        """Test DomainIn validates and normalizes domains."""
        from app.security import DomainIn

        domain = DomainIn(domain="  EXAMPLE.COM  ")
        assert domain.domain == "example.com"

    def test_domain_in_rejects_invalid(self):
        """Test DomainIn rejects invalid formats."""
        from app.security import DomainIn

        with pytest.raises(ValidationError):
            DomainIn(domain="not_a_domain")
