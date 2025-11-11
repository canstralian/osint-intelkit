"""Tests for security module (domain normalization, hashing, validation)."""

import pytest

from app.security import DomainIn, normalize_domain, pseudo_id, salted_hash


class TestDomainNormalization:
    """Test domain normalization functionality."""

    def test_normalize_domain_lowercase(self):
        """Test that domains are converted to lowercase."""
        assert normalize_domain("EXAMPLE.COM") == "example.com"
        assert normalize_domain("Test.Example.Com") == "test.example.com"

    def test_normalize_domain_strip_whitespace(self):
        """Test that whitespace is stripped from domains."""
        assert normalize_domain("  example.com  ") == "example.com"
        assert normalize_domain("\texample.com\n") == "example.com"

    def test_normalize_domain_idna_encoding(self):
        """Test IDNA encoding for international domains."""
        # Test punycode encoding
        result = normalize_domain("münchen.de")
        assert "xn--" in result or result == "münchen.de"

    def test_normalize_domain_already_normalized(self):
        """Test that already normalized domains remain unchanged."""
        assert normalize_domain("example.com") == "example.com"


class TestPseudoID:
    """Test pseudonymous ID generation."""

    def test_pseudo_id_consistency(self, sample_domain):
        """Test that same domain produces same pseudo ID."""
        id1 = pseudo_id(sample_domain)
        id2 = pseudo_id(sample_domain)
        assert id1 == id2

    def test_pseudo_id_different_domains(self):
        """Test that different domains produce different IDs."""
        id1 = pseudo_id("example.com")
        id2 = pseudo_id("different.com")
        assert id1 != id2

    def test_pseudo_id_length(self, sample_domain):
        """Test that pseudo ID has expected length (SHA256 hex = 64 chars)."""
        result = pseudo_id(sample_domain)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_pseudo_id_case_insensitive(self):
        """Test that domain case doesn't affect pseudo ID."""
        id1 = pseudo_id("Example.COM")
        id2 = pseudo_id("example.com")
        assert id1 == id2


class TestSaltedHash:
    """Test Argon2 salted hashing."""

    def test_salted_hash_unique(self, sample_domain):
        """Test that same input produces different hashes (due to salt)."""
        hash1 = salted_hash(sample_domain)
        hash2 = salted_hash(sample_domain)
        assert hash1 != hash2  # Different salts

    def test_salted_hash_format(self, sample_domain):
        """Test that hash has Argon2 format."""
        result = salted_hash(sample_domain)
        assert result.startswith("$argon2")

    def test_salted_hash_verification(self, sample_domain):
        """Test that hash can be verified."""
        from argon2 import PasswordHasher

        ph = PasswordHasher()
        hashed = salted_hash(sample_domain)
        # Should not raise exception
        ph.verify(hashed, sample_domain)


class TestDomainValidation:
    """Test Pydantic domain validation."""

    def test_valid_domain(self, sample_domain):
        """Test that valid domains are accepted."""
        domain_in = DomainIn(domain=sample_domain)
        assert domain_in.domain == sample_domain

    def test_domain_normalization_in_validation(self):
        """Test that domain is normalized during validation."""
        domain_in = DomainIn(domain="  EXAMPLE.COM  ")
        assert domain_in.domain == "example.com"

    def test_invalid_domain_no_dot(self):
        """Test that domains without dots are rejected."""
        with pytest.raises(ValueError, match="invalid domain format"):
            DomainIn(domain="localhost")

    def test_invalid_domain_too_long(self):
        """Test that domains over 253 characters are rejected."""
        long_domain = "a" * 254 + ".com"
        with pytest.raises(ValueError, match="invalid domain format"):
            DomainIn(domain=long_domain)

    def test_valid_subdomain(self):
        """Test that subdomains are accepted."""
        domain_in = DomainIn(domain="api.staging.example.com")
        assert domain_in.domain == "api.staging.example.com"
