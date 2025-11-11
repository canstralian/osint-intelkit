-- OSINT Pipeline Database Schema
-- Stores domains, enrichments, and provenance metadata

CREATE TABLE IF NOT EXISTS domains (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    source TEXT,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_domains_name ON domains(name);
CREATE INDEX idx_domains_source ON domains(source);

CREATE TABLE IF NOT EXISTS enrichments (
    id SERIAL PRIMARY KEY,
    domain_id INT REFERENCES domains(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    data JSONB NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confidence_score FLOAT DEFAULT 0.0
);

CREATE INDEX idx_enrichments_domain_id ON enrichments(domain_id);
CREATE INDEX idx_enrichments_source ON enrichments(source);
CREATE INDEX idx_enrichments_timestamp ON enrichments(timestamp DESC);

-- Store API usage and rate limiting metadata
CREATE TABLE IF NOT EXISTS api_usage (
    id SERIAL PRIMARY KEY,
    api_name TEXT NOT NULL,
    endpoint TEXT,
    request_count INT DEFAULT 1,
    last_request TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    rate_limit_remaining INT,
    reset_time TIMESTAMP
);

CREATE INDEX idx_api_usage_api_name ON api_usage(api_name);

-- Audit log for all OSINT operations
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    operation TEXT NOT NULL,
    entity_type TEXT,
    entity_value TEXT,
    user_context TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_log_operation ON audit_log(operation);
