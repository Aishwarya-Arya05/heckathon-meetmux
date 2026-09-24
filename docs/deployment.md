# Deployment Guide

For the full production deployment guide, see [DEPLOYMENT.md](../DEPLOYMENT.md).

## Quick Docker Compose Deployment

To run the entire platform locally with Neo4j, backend, and frontend:

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Launch full multi-container stack
docker compose up -d

# 3. View running services
docker compose ps
```

- Frontend: http://localhost:5173
- Backend API Docs: http://localhost:8000/docs
- Neo4j Browser: http://localhost:7474
