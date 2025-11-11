import os
import hmac
import binascii
import idna
from hashlib import sha256
from argon2 import PasswordHasher
from pydantic import BaseModel, field_validator

PEPPER = binascii.unhexlify(os.getenv("PEPPER_HEX", "").encode()) if os.getenv("PEPPER_HEX") else None
argon = PasswordHasher(time_cost=2, memory_cost=51200, parallelism=2)


def normalize_domain(value: str) -> str:
    """
    Normalize domain name for consistent hashing and comparison.
    - Lowercase
    - IDNA encoding (punycode) for international domains
    """
    value = value.strip().lower()
    try:
        value = idna.encode(value).decode()
    except idna.IDNAError:
        pass
    return value


def pseudo_id(value: str) -> str:
    """
    Stable pseudonymous ID via HMAC(pepper, normalized_value).
    Allows correlation across runs without storing PII/plaintext.
    """
    assert PEPPER, "PEPPER_HEX must be set in environment"
    v = normalize_domain(value).encode()
    return hmac.new(PEPPER, v, sha256).hexdigest()


def salted_hash(value: str) -> str:
    """
    Strong salted hash for at-rest storage (Argon2id).
    Not reversible; use for integrity verification only.
    """
    return argon.hash(value)


class DomainIn(BaseModel):
    """Pydantic model for domain input validation."""
    domain: str

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v):
        """Validate and normalize domain input."""
        nv = normalize_domain(v)
        if "." not in nv or len(nv) > 253:
            raise ValueError("invalid domain format")
        return nv
