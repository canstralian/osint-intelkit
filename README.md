# OSINT IntelKit

**Automated OSINT Pipeline for Authorized Reconnaissance and Threat Intelligence**

A production-ready, scalable OSINT automation system built with FastAPI, Prefect, PostgreSQL, and Neo4j. Designed for ethical security research, defensive security operations, and threat intelligence gathering.

## ⚠️ Ethical Use Requirements

**This tool is designed exclusively for:**
- ✅ Authorized security testing and penetration testing engagements
- ✅ Defensive security operations and threat intelligence
- ✅ CTF competitions and security research
- ✅ Educational purposes in controlled environments
- ✅ Monitoring your own organization's external attack surface

**Prohibited Uses:**
- ❌ Unauthorized scanning or reconnaissance
- ❌ Mass targeting or indiscriminate data collection
- ❌ Detection evasion for malicious purposes
- ❌ Any illegal or unethical activities

**Legal Notice:** Always obtain explicit written authorization before conducting reconnaissance on any systems or domains you do not own or have permission to test.

---

## 🎯 Features

### Core Capabilities
- **Passive Intelligence Collection**: Certificate transparency, public DNS, WHOIS data
- **Threat Intelligence Enrichment**: VirusTotal, Shodan, AbuseIPDB integration
- **Subdomain Discovery**: Passive enumeration from public sources
- **Graph-Based Analysis**: Relationship mapping using Neo4j
- **Automated Workflows**: Scheduled collection via Prefect orchestration
- **API-First Design**: RESTful API for integration with existing tools
- **Audit Logging**: Complete provenance tracking for compliance
- **GitHub Repository Search**: Search across repositories for code snippets, documentation, and similar implementations

### Architecture Highlights
- **Microservices**: Decoupled collectors and enrichers
- **Async Processing**: High-performance asyncio-based workers
- **Rate Limiting**: Built-in API quota management
- **Observability**: Comprehensive logging and metrics
- **Scalable**: Queue-based architecture ready for horizontal scaling

---

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   FastAPI   │────▶│   Prefect    │────▶│  Collectors │
│     API     │     │ Orchestrator │     │   Workers   │
└─────────────┘     └──────────────┘     └─────────────┘
       │                    │                     │
       │                    ▼                     ▼
       │            ┌──────────────┐     ┌─────────────┐
       │            │  PostgreSQL  │     │   Neo4j     │
       │            │  (Entities)  │     │   (Graph)   │
       │            └──────────────┘     └─────────────┘
       │                    ▲                     ▲
       ▼                    │                     │
┌─────────────┐     ┌──────────────┐             │
│  Enrichers  │────▶│  VirusTotal  │─────────────┘
│   Workers   │     │   Shodan     │
└─────────────┘     └──────────────┘
```

### Data Flow
1. **Ingest**: Collect domains from seeds, APIs, or manual input
2. **Normalize**: Canonicalize and deduplicate entities
3. **Enrich**: Query threat intelligence APIs (VirusTotal, etc.)
4. **Correlate**: Build relationship graph in Neo4j
5. **Surface**: API endpoints and dashboards for analysis

---

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Git
- (Optional) VirusTotal API key for enrichment

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/canstralian/osint-intelkit.git
cd osint-intelkit
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env and add your API keys
nano .env
```

**IMPORTANT**: Add your VirusTotal API key to `.env`:
```bash
API_KEY_VT=your_actual_virustotal_api_key
```

Get a free API key at: https://www.virustotal.com/gui/my-apikey

3. **Start the services:**
```bash
docker compose up --build
```

4. **Verify services are running:**

The system starts 6 services:
- **FastAPI**: http://localhost:8000 (REST API)
- **Prefect UI**: http://localhost:4200 (Flow orchestration dashboard)
- **Neo4j Browser**: http://localhost:7474 (Graph database, login: neo4j/testpass)
- **PostgreSQL**: localhost:5432 (Relational database)
- **Prefect Agent**: Background worker for flow execution
- **Deployment Service**: Registers scheduled flows (runs once)

```bash
# Check API health
curl http://localhost:8000/

# Open Prefect dashboard
open http://localhost:4200

# Open Neo4j browser
open http://localhost:7474
# Login: neo4j / testpass

# View all running services
docker compose ps
```

**🎉 That's it!** The OSINT pipeline is now running and will automatically collect and enrich intelligence every 4 hours (or according to your configured schedule).

---

## 📖 Usage

### API Endpoints

#### 1. Collect Domain Intelligence
```bash
curl -X POST "http://localhost:8000/tasks/collect" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "source": "manual",
    "enrich": true
  }'
```

#### 2. Enrich with VirusTotal
```bash
curl -X POST "http://localhost:8000/tasks/enrich" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "sources": ["virustotal"]
  }'
```

#### 3. Get Domain Enrichments
```bash
curl "http://localhost:8000/domains/example.com/enrichments"
```

#### 4. Get Domain Summary
```bash
curl "http://localhost:8000/domains/example.com/summary"
```

#### 5. Explore Graph Relationships
```bash
curl "http://localhost:8000/graph/example.com?depth=2"
```

#### 6. Find Related Domains
```bash
curl "http://localhost:8000/graph/example.com/related?min_connections=2"
```

#### 7. Search GitHub for Code Snippets
```bash
# Search for authentication implementations in Python
curl "http://localhost:8000/github/search/code?query=authentication&language=python"

# Search in a specific repository
curl "http://localhost:8000/github/search/code?query=api&repo=owner/repository"
```

#### 8. Search GitHub Repositories
```bash
# Find OSINT-related repositories
curl "http://localhost:8000/github/search/repositories?query=osint&language=python&sort=stars"

# Search for FastAPI projects
curl "http://localhost:8000/github/search/repositories?query=fastapi&sort=stars&order=desc"
```

#### 9. Search Documentation
```bash
# Find installation documentation
curl "http://localhost:8000/github/search/documentation?query=installation+guide"

# Search docs in specific repository
curl "http://localhost:8000/github/search/documentation?query=api+authentication&repo=owner/repo"
```

#### 10. Find Similar Implementations
```bash
# Find JWT authentication implementations
curl "http://localhost:8000/github/search/similar-implementations?feature=jwt+authentication&language=python"

# Search for rate limiting patterns
curl "http://localhost:8000/github/search/similar-implementations?feature=rate+limiting+fastapi"
```

### Interactive API Documentation

Visit the auto-generated Swagger UI:
```
http://localhost:8000/docs
```

### Automated Scheduled Collection with Prefect

The system includes **fully automated** Prefect orchestration that runs collection and enrichment flows on a schedule without any manual intervention.

#### How It Works

When you start the system with `docker compose up`, the following happens automatically:

1. **Prefect Server** starts and provides the orchestration UI at http://localhost:4200
2. **Prefect Agent** starts listening for scheduled flow runs
3. **Deployment Service** registers the OSINT flow with your configured schedule
4. **Automatic Execution** begins - the flow runs every N hours (default: 4 hours)

#### Configuration

Configure scheduling in your `.env` file:

```bash
# Schedule type: "interval" or "cron"
OSINT_SCHEDULE_TYPE=interval

# For interval scheduling: hours between runs
OSINT_SCHEDULE_INTERVAL_HOURS=4

# For cron scheduling: cron expression
OSINT_SCHEDULE_CRON=0 2 * * *  # Daily at 2 AM UTC
OSINT_SCHEDULE_TIMEZONE=UTC

# Seed domains (comma-separated, authorized targets only)
OSINT_SEED_DOMAINS=example.com,yourdomain.com
```

#### Schedule Types

**Interval-based** (runs every N hours):
```bash
OSINT_SCHEDULE_TYPE=interval
OSINT_SCHEDULE_INTERVAL_HOURS=6  # Every 6 hours
```

**Cron-based** (runs at specific times):
```bash
OSINT_SCHEDULE_TYPE=cron
OSINT_SCHEDULE_CRON=0 2 * * *    # Daily at 2 AM UTC
OSINT_SCHEDULE_CRON=0 */6 * * *  # Every 6 hours
OSINT_SCHEDULE_CRON=0 9,17 * * MON-FRI  # 9 AM and 5 PM on weekdays
```

#### Prefect UI Dashboard

Access the Prefect dashboard to monitor your flows:

```
http://localhost:4200
```

Features:
- **Flow Runs**: View all past and scheduled runs
- **Deployments**: Manage and configure deployments
- **Logs**: Real-time logs for each flow run
- **Task Details**: Per-task execution status and timing
- **Manual Triggers**: Run flows on-demand

#### Manual Operations

**Trigger a manual flow run:**
```bash
docker exec -it prefect_agent prefect deployment run 'vt-osint-flow/osint-automated-collection'
```

**View deployment status:**
```bash
docker exec -it prefect_agent prefect deployment ls
```

**View recent flow runs:**
```bash
docker exec -it prefect_agent prefect flow-run ls --limit 10
```

**Check agent status:**
```bash
docker exec -it prefect_agent prefect agent ls
```

#### Monitoring Flow Execution

**View live logs:**
```bash
docker compose logs -f deployment
docker compose logs -f prefect-agent
```

**Check Prefect UI:**
1. Open http://localhost:4200
2. Navigate to "Flow Runs" to see all executions
3. Click on any run to see detailed logs and task breakdowns

#### Advanced: Multiple Schedules

Enable additional deployment schedules in `.env`:

```bash
# Hourly quick scans (high-priority targets)
ENABLE_HOURLY_SCAN=true

# Daily comprehensive scans (full target list)
ENABLE_DAILY_SCAN=true
```

---

## 🗄️ Database Operations

### PostgreSQL

**Connect to database:**
```bash
docker compose exec postgres psql -U osint -d osintdb
```

**Useful queries:**
```sql
-- View collected domains
SELECT * FROM domains ORDER BY last_seen DESC LIMIT 10;

-- View enrichments
SELECT d.name, e.source, e.confidence_score, e.timestamp
FROM domains d
JOIN enrichments e ON d.id = e.domain_id
ORDER BY e.timestamp DESC;

-- API usage tracking
SELECT * FROM api_usage ORDER BY last_request DESC;

-- Audit log
SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 20;
```

### Neo4j

**Access Neo4j Browser:**
```
http://localhost:7474
Login: neo4j / testpass
```

**Cypher queries:**
```cypher
// View all domains
MATCH (d:Domain) RETURN d LIMIT 25;

// Find domains with threat tags
MATCH (d:Domain)-[r:TAGGED_AS]->(t:ThreatTag)
RETURN d.name, t.name, r.confidence
ORDER BY r.confidence DESC;

// Find related infrastructure
MATCH (d1:Domain {name: "example.com"})-[]->(shared)<-[]-(d2:Domain)
RETURN d1, shared, d2 LIMIT 50;

// Analyze domain relationships
MATCH path = (d:Domain)-[*1..3]-(n)
WHERE d.name = "example.com"
RETURN path LIMIT 100;
```

---

## 🔧 Configuration

### Environment Variables

See `.env.example` for all configuration options:

**Database:**
- `POSTGRES_URL`: PostgreSQL connection string
- `NEO4J_URI`: Neo4j Bolt protocol URI
- `NEO4J_USER`, `NEO4J_PASSWORD`: Neo4j credentials

**API Keys:**
- `API_KEY_VT`: VirusTotal API key
- `API_KEY_SHODAN`: Shodan API key (optional)
- `GITHUB_TOKEN`: GitHub personal access token (optional, but recommended for higher rate limits)
  - Get a token at: https://github.com/settings/tokens
  - Recommended scopes: `public_repo` (for public repository search)
  - Unauthenticated requests: 10 requests/minute
  - Authenticated requests: 30 requests/minute

**Rate Limits:**
- `VT_RATE_LIMIT`: VirusTotal requests per minute (default: 4)
- `SHODAN_RATE_LIMIT`: Shodan requests per second (default: 1)

**Application:**
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `ENABLE_AUDIT_LOG`: Enable audit trail (true/false)
- `MAX_CONCURRENT_ENRICHMENTS`: Parallel enrichment limit

### Authorization Scope

**Define authorized targets** in `.env`:
```bash
AUTHORIZED_DOMAINS=yourdomain.com,yourcompany.net
```

---

## 🔒 Security & Compliance

### Best Practices

1. **API Key Management**
   - Never commit API keys to version control
   - Use environment variables or secrets management (Vault)
   - Rotate keys regularly
   - Use separate keys for dev/staging/prod

2. **Rate Limiting**
   - Respect API provider terms of service
   - Configure appropriate rate limits
   - Monitor API usage metrics

3. **Data Retention**
   - Implement retention policies for collected data
   - Mask or redact PII where appropriate
   - Comply with GDPR and local privacy laws

4. **Access Control**
   - Restrict API access via authentication (add JWT/OAuth in production)
   - Use network segmentation for database access
   - Enable audit logging for compliance

5. **Authorization**
   - Maintain written authorization for all targets
   - Document scope and boundaries
   - Implement kill-switch for emergency shutdown

### Audit Trail

All operations are logged to the `audit_log` table:
```sql
SELECT operation, entity_type, entity_value, user_context, timestamp
FROM audit_log
WHERE timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;
```

---

## 🧪 Development

### Project Structure
```
osint-intelkit/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── routers/             # API endpoints
│   │   │   ├── tasks.py         # Task orchestration
│   │   │   ├── domains.py       # Domain queries
│   │   │   └── graph.py         # Graph analysis
│   │   ├── workers/             # Background workers
│   │   │   ├── collector.py    # Passive collection
│   │   │   └── vt_enricher.py  # VirusTotal enrichment
│   │   ├── flows/               # Prefect workflows
│   │   │   └── vt_flow.py       # Scheduled OSINT flow
│   │   └── db/                  # Database modules
│   │       ├── postgres.py      # PostgreSQL operations
│   │       └── neo4j.py         # Neo4j graph operations
│   ├── requirements.txt         # Python dependencies
│   └── Dockerfile               # Container image
├── sql/
│   └── schema.sql               # Database schema
├── docker-compose.yml           # Service orchestration
└── .env.example                 # Configuration template
```

### Adding New Enrichment Sources

1. **Create enricher module:**
```python
# backend/app/workers/shodan_enricher.py
async def shodan_enrich_domain(domain: str):
    # Implementation
    pass
```

2. **Update task router:**
```python
# backend/app/routers/tasks.py
if "shodan" in request.sources:
    background_tasks.add_task(shodan_enrich_domain, request.domain)
```

3. **Add to Prefect flow:**
```python
# backend/app/flows/vt_flow.py
@task
async def shodan_enrich_all(domains: List[str]):
    # Implementation
    pass
```

### Running Tests

**Comprehensive pytest suite with 43 tests covering security, enrichment, orchestration, and workers.**

```bash
# Install test dependencies
pip install -r backend/requirements-dev.txt

# Run all tests
PEPPER_HEX=$(openssl rand -hex 32) PYTHONPATH=backend pytest -v

# Run with coverage report
pytest --cov=app --cov-report=html --cov-report=term

# Run specific test modules
pytest backend/tests/test_security.py -v
pytest backend/tests/test_prefect_flows.py -v
```

**Test Coverage:**
- ✅ Security primitives (domain normalization, HMAC pseudo-IDs, Argon2 hashing)
- ✅ VirusTotal enrichment (API mocking, rate limiting, cache fallback)
- ✅ PostgreSQL operations (domain persistence, enrichment recording)
- ✅ Prefect flow orchestration (task execution, state transitions, error handling)
- ✅ Collector workers (passive OSINT, crt.sh integration, subdomain enumeration)
- ⏭️ Deployment configuration (11 tests skipped - Prefect 3.x API migration)

**Results:** 33 passing, 11 skipped

See [backend/tests/README.md](backend/tests/README.md) for detailed testing documentation.

---

## 🐛 Troubleshooting

### Common Issues

**1. PostgreSQL connection errors:**
```bash
# Check if PostgreSQL is running
docker compose ps postgres

# View logs
docker compose logs postgres

# Wait for database initialization
docker compose exec postgres pg_isready -U osint
```

**2. Neo4j connection errors:**
```bash
# Check Neo4j status
docker compose ps neo4j

# View logs
docker compose logs neo4j

# Test connection
docker compose exec neo4j cypher-shell -u neo4j -p testpass
```

**3. VirusTotal rate limiting:**
```
[VT] Rate limit reached, waiting 60s
```
**Solution**: This is expected behavior for free tier (4 req/min). Upgrade to premium for higher limits.

**4. Worker not starting:**
```bash
# Check worker logs
docker compose logs worker

# Restart worker
docker compose restart worker
```

### Logs

**View all logs:**
```bash
docker compose logs -f
```

**Service-specific logs:**
```bash
docker compose logs -f api
docker compose logs -f scheduler
docker compose logs -f worker
```

---

## 📊 Monitoring & Observability

### Metrics to Track

- **Collection Rate**: Domains collected per hour
- **Enrichment Coverage**: % of domains with enrichment data
- **API Usage**: Requests per source, rate limit status
- **Error Rate**: Failed collections/enrichments
- **Data Freshness**: Time since last update per domain

### Integration with Monitoring Tools

**Prometheus metrics (TODO):**
```python
from prometheus_client import Counter, Gauge

domains_collected = Counter('domains_collected_total', 'Total domains collected')
enrichments_added = Counter('enrichments_added_total', 'Total enrichments added', ['source'])
api_requests = Counter('api_requests_total', 'API requests', ['service', 'status'])
```

**Grafana dashboards:**
- Collection pipeline throughput
- API quota utilization
- Graph database growth
- Error rates and alerts

---

## 🗺️ Roadmap

### Planned Features
- [ ] Additional enrichment sources (Shodan, Censys, SecurityTrails)
- [ ] Advanced subdomain discovery techniques
- [ ] Email/username OSINT modules
- [ ] Automated reporting and alerting (Slack, email)
- [ ] Web UI dashboard for visualization
- [ ] Redis queue for better task distribution
- [ ] Authentication and RBAC for API
- [ ] Export formats (CSV, JSON, STIX/TAXII)
- [ ] Machine learning for threat scoring
- [ ] Integration with SOAR platforms (TheHive, Cortex)

### Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**Code Standards:**
- Follow PEP 8 style guide
- Add docstrings to all functions
- Include type hints
- Write tests for new features
- Update documentation

---

## 📚 Resources

### Documentation
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Prefect Documentation](https://docs.prefect.io/)
- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/current/)
- [VirusTotal API](https://developers.virustotal.com/reference/overview)

### OSINT Tools
- [SpiderFoot](https://github.com/smicallef/spiderfoot)
- [Recon-ng](https://github.com/lanmaster53/recon-ng)
- [Amass](https://github.com/OWASP/Amass)
- [theHarvester](https://github.com/laramies/theHarvester)

### Security Research
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [PTES Technical Guidelines](http://www.pentest-standard.org/index.php/Main_Page)
- [MITRE ATT&CK Framework](https://attack.mitre.org/)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Disclaimer**: The authors and contributors are not responsible for misuse or damage caused by this software. Users are solely responsible for ensuring compliance with all applicable laws and regulations.

---

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Prefect](https://www.prefect.io/) - Workflow orchestration
- [PostgreSQL](https://www.postgresql.org/) - Relational database
- [Neo4j](https://neo4j.com/) - Graph database
- [VirusTotal](https://www.virustotal.com/) - Threat intelligence

---

## 📧 Contact

For questions, issues, or collaboration:
- GitHub Issues: https://github.com/canstralian/osint-intelkit/issues
- Email: security@yourdomain.com

**Remember**: With great power comes great responsibility. Use ethically. 🛡️
