# API Reference

Complete API reference for OSINT IntelKit modules.

```{eval-rst}
.. toctree::
   :maxdepth: 2
   :caption: API Modules:

   main
   security
   routers
   workers
   flows
   database
```

## Overview

OSINT IntelKit is organized into the following modules:

### Core Modules

- **main**: FastAPI application and initialization
- **security**: Domain validation, hashing, and normalization
- **logging_config**: Structured logging with structlog
- **errors**: Error handling middleware

### API Routers

- **tasks**: Task orchestration endpoints
- **domains**: Domain data retrieval
- **graph**: Graph query and relationship analysis

### Workers

- **collector**: Passive OSINT collection from public sources
- **vt_enricher**: VirusTotal enrichment worker

### Flows

- **vt_flow**: Prefect orchestration for automated collection
- **deploy**: Deployment configuration and scheduling

### Database

- **postgres**: PostgreSQL operations
- **neo4j**: Neo4j graph database operations

## Quick API Examples

### Health Check

```bash
curl http://localhost:8000/
```

### Collect Domain

```bash
curl -X POST "http://localhost:8000/tasks/collect" \
  -H "Content-Type: application/json" \
  -d '{"domain": "example.com", "source": "manual", "enrich": true}'
```

### Get Enrichments

```bash
curl "http://localhost:8000/domains/example.com/enrichments"
```

### Query Graph

```bash
curl "http://localhost:8000/graph/example.com?depth=2"
```

## Interactive Documentation

For interactive API documentation, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
