# Security Features

This document outlines the comprehensive security features implemented in OSINT IntelKit.

## Overview

OSINT IntelKit implements defense-in-depth security with multiple layers of protection:

1. **Structured Logging** - JSON-formatted logs with automatic sanitization
2. **Request Tracking** - Correlation IDs for distributed tracing
3. **Input Validation** - Comprehensive input sanitization
4. **Rate Limiting** - API abuse prevention
5. **Security Headers** - Protection against common web vulnerabilities
6. **Security Monitoring** - Real-time threat detection
7. **Audit Logging** - Complete security event tracking

---

## 1. Structured Logging

### Features

- **JSON-formatted logs** for easy parsing and analysis
- **Automatic sanitization** of sensitive data (API keys, passwords, tokens)
- **Correlation ID tracking** for request tracing across services
- **Security event flagging** for important security-related events
- **Development and production modes** (pretty console vs JSON)

### Configuration

```bash
# .env configuration
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
ENVIRONMENT=production      # production (JSON) or development (console)
LOG_FORMAT=json            # json or console
SERVICE_NAME=api           # Service identifier in logs
```

### Log Format

Production logs (JSON):
```json
{
  "timestamp": "2025-11-11T10:30:45.123456Z",
  "level": "INFO",
  "logger": "app.routers.tasks",
  "event": "collection_started",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "domain": "example.com",
  "source": "api",
  "security_event": true,
  "app": "osint-intelkit",
  "environment": "production",
  "service": "api"
}
```

### Sanitization

The following data is automatically redacted from logs:
- API keys (any field containing "key", "token", "secret", "password")
- Email addresses (partially masked: u***r@domain.com)
- Long alphanumeric strings in sensitive contexts
- Authorization headers
- API responses containing credentials

### Location

- Configuration: `backend/app/config/logging.py`
- Sanitization: `backend/app/middleware/security.py`

---

## 2. Request Correlation IDs

### Features

- **Unique ID per request** for distributed tracing
- **Header propagation** - Accepts and returns `X-Correlation-ID`
- **Automatic generation** if not provided
- **Context-aware logging** - All logs include correlation ID

### Usage

Client can provide correlation ID:
```bash
curl -H "X-Correlation-ID: my-custom-id-123" http://localhost:8000/tasks/collect
```

Response includes correlation ID:
```
X-Correlation-ID: my-custom-id-123
```

All logs for this request will include `correlation_id: "my-custom-id-123"`.

### Implementation

- Middleware: `backend/app/middleware/correlation_id.py`
- Automatic context binding via `structlog.contextvars`

---

## 3. Input Validation & Sanitization

### Domain Validation

All domain inputs are validated using:

1. **Format validation** - Must match valid domain format (RFC compliant)
2. **Character filtering** - Blocks injection characters: `< > " ' \ ; | & $ \``
3. **Length limits** - Maximum 253 characters (DNS spec)
4. **Private domain blocking** - Rejects `.local`, `.internal`, `.localhost`

### Source Validation

Source identifiers must be:
- Alphanumeric with underscores and hyphens only
- Maximum 100 characters
- No special characters

### Bulk Request Limits

- **Maximum 100 domains** per bulk request
- **Duplicate removal** automatically
- **Per-domain validation** for entire list

### Examples

**Valid domains:**
```
example.com
subdomain.example.com
test-site.co.uk
```

**Rejected domains:**
```
example.com; DROP TABLE domains--  (SQL injection attempt)
<script>alert('xss')</script>.com  (XSS attempt)
test.local                         (Private domain)
```

### Implementation

- Validation: `backend/app/routers/tasks.py` (Pydantic validators)
- Pattern detection: `backend/app/middleware/security.py`

---

## 4. API Rate Limiting

### Features

- **Per-endpoint rate limits** configured individually
- **Smart identification** - API key > Auth header > IP address
- **Distributed support** - Redis backend for multi-instance deployments
- **Automatic retry headers** - `Retry-After` header on 429 responses
- **Security event logging** - All rate limit violations logged

### Rate Limits

| Endpoint | Limit | Reason |
|----------|-------|--------|
| `/tasks/collect` | 10/minute | Standard collection |
| `/tasks/enrich` | 10/minute | Standard enrichment |
| `/tasks/collect/bulk` | 2/minute | Resource-intensive bulk operations |
| Global default | 100/minute | API-wide fallback |

### Configuration

```bash
# .env configuration
API_RATE_LIMIT=100/minute          # Global default
API_STRICT_RATE_LIMIT=10/minute    # Sensitive endpoints
REDIS_URL=memory://                # memory:// or redis://host:port
```

### Rate Limit Response

```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Limit: 10/minute",
  "retry_after": "60 seconds"
}
```

Headers:
```
HTTP/1.1 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 10/minute
```

### Implementation

- Middleware: `backend/app/middleware/rate_limit.py`
- Library: `slowapi` (built on `limits`)

---

## 5. Security Headers

### Implemented Headers

All responses include comprehensive security headers:

| Header | Value | Purpose |
|--------|-------|---------|
| `Content-Security-Policy` | `default-src 'self'; ...` | Prevent XSS and injection attacks |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `X-Content-Type-Options` | `nosniff` | Prevent MIME-type sniffing |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Enforce HTTPS |
| `X-XSS-Protection` | `1; mode=block` | Legacy XSS protection |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Control referrer information |
| `Permissions-Policy` | `geolocation=(), camera=(), ...` | Disable unnecessary browser features |

### Content Security Policy (CSP)

```
default-src 'self';
script-src 'self' 'unsafe-inline';
style-src 'self' 'unsafe-inline';
img-src 'self' data: https:;
font-src 'self' data:;
connect-src 'self';
frame-ancestors 'none';
```

### Server Header Removal

The `Server` header is removed to avoid information disclosure.

### Implementation

- Middleware: `backend/app/middleware/security.py` (`SecurityHeadersMiddleware`)

---

## 6. Security Monitoring

### Threat Detection

The security monitoring middleware automatically detects:

1. **SQL Injection patterns**
   - `UNION SELECT`, `OR 1=1`, `DROP TABLE`, `--`, `/* */`

2. **Cross-Site Scripting (XSS)**
   - `<script>`, `javascript:`, `onerror=`, `onload=`

3. **Command Injection**
   - Pipe characters, semicolons, backticks, command substitution

4. **Directory Traversal**
   - `../`, `..%2f`

5. **Buffer Overflow attempts**
   - Excessively long parameters (>2000 chars)

### Security Event Logging

All security events are logged with `security_event: true` flag:

```json
{
  "event": "suspicious_request_detected",
  "path": "/tasks/collect",
  "suspicious_patterns": ["sql_injection", "xss"],
  "security_event": true,
  "client_ip": "192.168.1.100",
  "user_agent": "...",
  "timestamp": "..."
}
```

### Authentication Monitoring

- All authentication attempts logged
- Failed authentication (401/403) tracked
- Unusual patterns flagged

### Implementation

- Middleware: `backend/app/middleware/security.py` (`SecurityMonitoringMiddleware`)

---

## 7. CORS Configuration

### Features

- **Configurable origins** via environment variable
- **Security warnings** when wildcard (`*`) is used
- **Method restrictions** - Only necessary HTTP methods allowed
- **Preflight caching** - 10-minute cache for OPTIONS requests

### Configuration

```bash
# .env configuration
# Production - specific origins only
CORS_ORIGINS=https://dashboard.example.com,https://app.example.com

# Development - allow all (NOT for production!)
CORS_ORIGINS=*
```

### Security Warning

If `CORS_ORIGINS=*`, the application logs a warning:

```json
{
  "event": "cors_insecure_configuration",
  "message": "CORS is configured to allow all origins. Set CORS_ORIGINS environment variable in production.",
  "security_event": true
}
```

### Allowed Methods

- `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`

### Implementation

- Configuration: `backend/app/main.py`

---

## 8. Health Checks

### Endpoint: `/health`

Returns comprehensive health status with actual database connectivity checks.

**Response (healthy):**
```json
{
  "status": "healthy",
  "checks": {
    "postgres": {
      "status": "healthy",
      "message": "Connected"
    },
    "neo4j": {
      "status": "healthy",
      "message": "Connected"
    }
  }
}
```

**Response (degraded):**
```json
{
  "status": "degraded",
  "checks": {
    "postgres": {
      "status": "unhealthy",
      "error": "connection timeout"
    },
    "neo4j": {
      "status": "healthy",
      "message": "Connected"
    }
  }
}
```

### Monitoring Integration

Use `/health` for:
- Kubernetes liveness/readiness probes
- Load balancer health checks
- Monitoring systems (Prometheus, Datadog, etc.)

### Implementation

- Endpoint: `backend/app/main.py` (`health_check()`)

---

## 9. Audit Logging

### Security Events

All security-relevant events are logged with `security_event: true`:

- **Collection operations** - Domain collection initiated
- **Enrichment operations** - Threat intelligence queries
- **Bulk operations** - Mass collection requests
- **Authentication attempts** - Login attempts (when auth is added)
- **Rate limit violations** - API abuse attempts
- **Suspicious requests** - Injection attempts detected
- **Database health** - Connection failures
- **Application lifecycle** - Startup/shutdown events

### Database Audit Log

The PostgreSQL `audit_log` table tracks:

```sql
SELECT operation, entity_type, entity_value, user_context, timestamp
FROM audit_log
WHERE security_event = true
ORDER BY timestamp DESC;
```

### Log Retention

Configure log retention based on compliance requirements:
- **GDPR**: Typically 30-90 days for security logs
- **PCI-DSS**: Minimum 90 days, recommended 1 year
- **HIPAA**: 6 years

### Implementation

- Application logs: Throughout codebase with `security_event: true`
- Database audit: `backend/app/db/postgres.py` (`log_audit()`)

---

## 10. Error Handling

### Secure Error Messages

- **Production errors** do not leak internal details
- **Generic messages** returned to clients
- **Detailed errors** logged server-side with correlation IDs

### Example

**Client receives:**
```json
{
  "error": "Internal server error",
  "message": "An unexpected error occurred"
}
```

**Server logs:**
```json
{
  "event": "unhandled_exception",
  "error": "database connection failed: timeout",
  "error_type": "TimeoutError",
  "correlation_id": "abc-123",
  "security_event": true,
  "stack_trace": "..."
}
```

### Implementation

- Global handler: `backend/app/main.py` (`global_exception_handler()`)

---

## Security Best Practices

### For Developers

1. **Never log sensitive data** - API keys, passwords, tokens
2. **Use correlation IDs** - Include in all log statements
3. **Flag security events** - Add `security_event: true` to important logs
4. **Validate all inputs** - Use Pydantic validators
5. **Test error paths** - Ensure errors don't leak information

### For Operators

1. **Set CORS_ORIGINS** - Never use `*` in production
2. **Configure rate limits** - Adjust based on expected traffic
3. **Use Redis for rate limiting** - Required for multi-instance deployments
4. **Monitor security logs** - Alert on `security_event: true` logs
5. **Rotate API keys** - Regularly rotate external service keys
6. **Review audit logs** - Regular security audits

### For Security Teams

1. **Log aggregation** - Centralize logs (ELK, Splunk, Datadog)
2. **Alerting rules** - Alert on suspicious patterns
3. **Incident response** - Use correlation IDs for investigation
4. **Compliance checks** - Verify audit log retention
5. **Penetration testing** - Regular security assessments

---

## Compliance Mapping

### OWASP Top 10 (2021)

| Vulnerability | Mitigation |
|--------------|------------|
| A01 - Broken Access Control | Rate limiting, input validation, audit logging |
| A02 - Cryptographic Failures | HSTS, secure headers, credential sanitization |
| A03 - Injection | Input validation, pattern detection, parameterized queries |
| A04 - Insecure Design | Defense in depth, security by default |
| A05 - Security Misconfiguration | Security headers, CORS configuration, secure defaults |
| A06 - Vulnerable Components | Regular dependency updates, security scanning |
| A07 - Auth Failures | Rate limiting, authentication monitoring (when auth added) |
| A08 - Software & Data Integrity | Audit logging, provenance tracking |
| A09 - Logging Failures | Comprehensive structured logging, security events |
| A10 - SSRF | Input validation, domain filtering |

### CIS Controls

- **Control 8: Audit Log Management** - Comprehensive audit logging
- **Control 11: Data Protection** - Log sanitization, encryption in transit (HSTS)
- **Control 14: Security Monitoring** - Real-time threat detection
- **Control 16: App Security** - Input validation, security headers, rate limiting

---

## Incident Response

### Investigation Steps

1. **Identify correlation ID** from incident
2. **Search logs** for correlation ID: `correlation_id: "abc-123"`
3. **Review security events**: `security_event: true`
4. **Check audit log**: Database audit trail
5. **Analyze patterns**: Look for related suspicious activity

### Log Search Examples

**Find all security events:**
```bash
cat logs/app.log | jq 'select(.security_event == true)'
```

**Find specific request:**
```bash
cat logs/app.log | jq 'select(.correlation_id == "abc-123")'
```

**Find rate limit violations:**
```bash
cat logs/app.log | jq 'select(.event == "rate_limit_exceeded")'
```

**Find suspicious requests:**
```bash
cat logs/app.log | jq 'select(.event == "suspicious_request_detected")'
```

---

## Future Security Enhancements

Planned security improvements:

1. **Authentication & Authorization**
   - JWT token-based authentication
   - Role-based access control (RBAC)
   - API key management

2. **Advanced Threat Detection**
   - ML-based anomaly detection
   - IP reputation checking
   - Threat intelligence integration

3. **Encryption**
   - Database encryption at rest
   - Secret management (HashiCorp Vault)
   - Certificate pinning

4. **Compliance**
   - GDPR compliance tools
   - PCI-DSS alignment
   - SOC 2 readiness

5. **Monitoring**
   - Prometheus metrics export
   - Grafana dashboards
   - Automated alerting

---

## Security Contacts

- **Security issues**: Report via GitHub Issues (mark as security)
- **Vulnerability disclosure**: Follow responsible disclosure practices
- **General questions**: See main README.md for contact info

---

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [CIS Controls](https://www.cisecurity.org/controls)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Content Security Policy](https://content-security-policy.com/)

---

**Last Updated:** 2025-11-11
**Version:** 1.0.0
