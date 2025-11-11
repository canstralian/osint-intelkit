# Security Best Practices

This document outlines security best practices for using and developing OSINT IntelKit.

## Ethical Use Requirements

### Authorization First

**Always obtain written authorization before:**
- Scanning or enumerating any domains/systems you don't own
- Collecting intelligence on third-party infrastructure
- Using OSINT data for security assessments

### Legal Compliance

Ensure compliance with:
- Computer Fraud and Abuse Act (CFAA) in the US
- Computer Misuse Act in the UK
- GDPR for EU data subjects
- Local privacy and cybersecurity laws

### Authorized Use Cases

✅ **Permitted:**
- Your own domains and infrastructure
- Client domains with written authorization
- Bug bounty programs with scope defined
- CTF competitions and security training
- Academic research with IRB approval

❌ **Prohibited:**
- Unauthorized reconnaissance or scanning
- Mass targeting or indiscriminate data collection
- Detection evasion for malicious purposes
- Any illegal or unethical activities

## API Key Management

### Never Commit Secrets

**Bad:**
```python
# DON'T DO THIS!
API_KEY = "abc123secret"
```

**Good:**
```python
# Use environment variables
API_KEY = os.getenv("API_KEY_VT")
```

### Best Practices

1. **Use .env files** (gitignored)
2. **Rotate keys regularly**
3. **Use separate keys** for dev/staging/prod
4. **Implement rate limiting**
5. **Monitor API usage**

## Rate Limiting

Respect API provider terms of service:

```python
# Configure in .env
VT_RATE_LIMIT=4  # VirusTotal free tier: 4 req/min
SHODAN_RATE_LIMIT=1  # Shodan free tier: 1 req/sec
```

Built-in rate limiting prevents quota exhaustion.

## Data Security

### At-Rest Encryption

Sensitive data is protected:

```python
# Domain hashing with HMAC
def pseudo_id(value: str) -> str:
    """Stable pseudonymous ID via HMAC(pepper, normalized_value)."""
    assert PEPPER, "PEPPER_HEX must be set in environment"
    v = normalize_domain(value).encode()
    return hmac.new(PEPPER, v, sha256).hexdigest()

# Password hashing with Argon2
def salted_hash(value: str) -> str:
    """Strong salted hash for at-rest storage (Argon2id)."""
    return argon.hash(value)
```

### In-Transit Encryption

- Use HTTPS for all API calls
- Configure TLS for database connections
- Never log sensitive data in plaintext

## Input Validation

All user input is validated with Pydantic:

```python
from pydantic import BaseModel, field_validator

class DomainIn(BaseModel):
    """Domain input validation."""
    domain: str

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v):
        """Validate and normalize domain input."""
        nv = normalize_domain(v)
        if "." not in nv or len(nv) > 253:
            raise ValueError("invalid domain format")
        return nv
```

## Database Security

### PostgreSQL

Use parameterized queries to prevent SQL injection:

```python
# Good: Parameterized query
async with conn.transaction():
    await conn.execute(
        "INSERT INTO domains (name, source) VALUES ($1, $2)",
        domain, source
    )
```

### Neo4j

Use query parameters:

```python
# Good: Parameterized Cypher
query = """
MATCH (d:Domain {name: $domain})
RETURN d
"""
result = session.run(query, domain=domain_name)
```

## Audit Logging

All operations are logged for compliance:

```python
await audit_log(
    operation="domain_collect",
    entity_type="domain",
    entity_value=domain,
    user_context=user_id,
    status="success"
)
```

Query audit logs:
```sql
SELECT operation, entity_value, timestamp
FROM audit_log
WHERE timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;
```

## Access Control

### Production Deployment

Add authentication to FastAPI:

```python
from fastapi import Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != os.getenv("API_SECRET_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

@app.get("/protected", dependencies=[Depends(verify_api_key)])
async def protected_route():
    return {"message": "Access granted"}
```

### Network Segmentation

```yaml
# docker-compose.yml
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # No external access
```

## Vulnerability Disclosure

### Reporting Security Issues

**DO NOT** create public issues for vulnerabilities.

**Email:** security@yourdomain.com

Include:
- Vulnerability description
- Steps to reproduce
- Potential impact
- Suggested fix (optional)

### Response Timeline

- **24 hours:** Acknowledgment
- **7 days:** Initial assessment
- **30 days:** Patch development
- **90 days:** Public disclosure (coordinated)

## Security Scanning

### Automated Scanning

Pre-commit hook runs bandit:

```bash
# Scan for security issues
make security

# Or manually
bandit -r backend/app -c pyproject.toml
```

### Dependency Scanning

```bash
# Check for known vulnerabilities
pip install safety
safety check -r backend/requirements.txt
```

## Incident Response

### Kill Switch

Emergency shutdown:

```bash
# Stop all services immediately
docker compose down

# Clear sensitive data
docker volume prune -f
```

### Data Breach Response

1. **Contain:** Shutdown affected services
2. **Assess:** Identify compromised data
3. **Notify:** Inform affected parties
4. **Remediate:** Patch vulnerabilities
5. **Document:** Create incident report

## Compliance Checklist

- [ ] Written authorization for all targets
- [ ] API keys in environment variables (not code)
- [ ] Rate limiting configured
- [ ] Audit logging enabled
- [ ] Input validation on all endpoints
- [ ] Parameterized database queries
- [ ] TLS/HTTPS for all connections
- [ ] Regular security scans (bandit, safety)
- [ ] Incident response plan documented
- [ ] GDPR compliance for EU data subjects

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [PTES Technical Guidelines](http://www.pentest-standard.org/)
- [GDPR Compliance](https://gdpr.eu/)
- [CIS Security Benchmarks](https://www.cisecurity.org/cis-benchmarks/)
