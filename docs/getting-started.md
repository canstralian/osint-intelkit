# Getting Started

This guide will help you get OSINT IntelKit up and running quickly.

## Prerequisites

- Docker and Docker Compose
- Git
- (Optional) VirusTotal API key for enrichment

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/canstralian/osint-intelkit.git
cd osint-intelkit
```

### 2. Configure environment

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

### 3. Start the services

```bash
docker compose up --build
```

### 4. Verify services

The system starts 6 services:
- **FastAPI**: http://localhost:8000 (REST API)
- **Prefect UI**: http://localhost:4200 (Flow orchestration)
- **Neo4j Browser**: http://localhost:7474 (Graph database)
- **PostgreSQL**: localhost:5432 (Relational database)

```bash
# Check API health
curl http://localhost:8000/

# Open Prefect dashboard
open http://localhost:4200

# Open Neo4j browser
open http://localhost:7474
# Login: neo4j / testpass
```

## Quick Start Examples

### Collect Domain Intelligence

```bash
curl -X POST "http://localhost:8000/tasks/collect" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "source": "manual",
    "enrich": true
  }'
```

### Enrich with VirusTotal

```bash
curl -X POST "http://localhost:8000/tasks/enrich" \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "example.com",
    "sources": ["virustotal"]
  }'
```

### Get Domain Enrichments

```bash
curl "http://localhost:8000/domains/example.com/enrichments"
```

## Interactive API Documentation

Visit the auto-generated Swagger UI:
```
http://localhost:8000/docs
```

## Next Steps

- Read the [API Reference](api/index) for detailed endpoint documentation
- Check out the [Development Guide](development) to contribute
- Review [Security Best Practices](security) for ethical use
