import pytest
from app.security import normalize_domain, pseudo_id, salted_hash, DomainIn

def test_normalize_domain_basic():
    assert normalize_domain("Example.COM") == "example.com"

def test_normalize_domain_idna():
    assert normalize_domain("münich.de") == "xn--mnich-kva.de"

def test_domainin_validation():
    model = DomainIn(domain="test.com")
    assert model.domain == "test.com"
    with pytest.raises(ValueError):
        DomainIn(domain="invalid")

def test_pseudo_id_deterministic():
    d = "example.com"
    pid1 = pseudo_id(d)
    pid2 = pseudo_id(d)
    assert pid1 == pid2 and len(pid1) == 64

def test_pseudo_id_requires_pepper(monkeypatch):
    monkeypatch.delenv("PEPPER_HEX", raising=False)
    from importlib import reload
    import app.security as sec
    reload(sec)
    with pytest.raises(AssertionError):
        sec.pseudo_id("example.com")

def test_salted_hash_unique():
    h1 = salted_hash("secret")
    h2 = salted_hash("secret")
    assert h1 != h2  # unique salt each time
    assert "argon2id" in h1
