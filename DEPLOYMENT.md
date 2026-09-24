# MeetMux Operations & Production Deployment Guide

This guide describes how to deploy, configure, secure, scale, and maintain the MeetMux Supply Chain Delay Risk and Route Planning platform in production.

---

## 1. Production Architecture Overview

```
                      Internet / Operator Browser
                                  │
                                  ▼ (HTTPS:443)
                      ┌──────────────────────┐
                      │ Cloudflare / AWS WAF │
                      └──────────┬───────────┘
                                 │
                                 ▼
                     ┌────────────────────────┐
                     │ Application Load       │ (TLS Termination)
                     │ Balancer (ALB)         │
                     └──────────┬─────────────┘
                                │
               ┌────────────────┴────────────────┐
               ▼ (Port 80)                       ▼ (Port 8000)
    ┌───────────────────────┐         ┌───────────────────────┐
    │ React Frontend Pods   │         │ FastAPI Backend Pods  │
    │ (Nginx static bundle) │         │ (Uvicorn Async API)   │
    └───────────────────────┘         └──────────┬────────────┘
                                                 │
          ┌──────────────────────┬───────────────┴──────────────┬──────────────────────┐
          ▼                      ▼                              ▼                      ▼
┌──────────────────┐   ┌──────────────────┐           ┌──────────────────┐   ┌──────────────────┐
│   Neo4j AuraDB   │   │ Self-Hosted OSRM │           │ Redis Cache      │   │ Model Registry   │
│ (Managed Cluster)│   │ (EC2 c6i / K8s)  │           │ (Route / Health) │   │ (S3 / MLflow)    │
└──────────────────┘   └──────────────────┘           └──────────────────┘   └──────────────────┘
```

---

## 2. Managed Infrastructure Requirements

| Component | Recommended Production Service | Minimum Sizing | HA / Redundancy |
|---|---|---|---|
| **API Backend** | AWS ECS Fargate or EKS | 2 vCPU, 4 GB RAM per task | Min 3 replicas across 3 AZs |
| **Frontend** | Cloudflare Pages, S3+CloudFront, or ECS | Edge CDN cached | Multi-region CDN |
| **Graph Database** | Neo4j AuraDB Enterprise or Self-Hosted | 8 vCPU, 32 GB RAM, SSD | 3-node cluster with auto-failover |
| **Routing Engine** | Self-Hosted OSRM on EC2 or Kubernetes | c6i.2xlarge (RAM-backed OSM map) | Min 2 replicas behind internal NLB |
| **Model Storage** | AWS S3 or Google Cloud Storage | Standard versioned bucket | S3 bucket versioning & KMS CMK |
| **Secrets Manager** | AWS Secrets Manager / HashiCorp Vault | Managed service | Automatic KMS key rotation |

---

## 3. Configuration & Secrets Management

**Rule:** Never commit secrets, connection strings, or private keys to source control.

### Required Environment Variables in Production:

```bash
# Application Mode
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=<generate-via-openssl-rand-hex-32>

# Networking & CORS
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
BACKEND_CORS_ORIGINS=["https://ops.meetmux.com"]
BACKEND_LOG_LEVEL=info

# Graph Database (Encrypted Bolt over TLS)
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=meetmux_app_user
NEO4J_PASSWORD=<stored-in-secrets-manager>
NEO4J_DATABASE=neo4j

# Routing Provider
ROUTE_PROVIDER=osrm_self_hosted
OSRM_BASE_URL=http://internal-osrm.production.internal:5000
ROUTE_TIMEOUT_SECONDS=5

# Delay Risk ML Model
MODEL_ARTIFACT_PATH=/models/delay_model_v0.1.0.joblib
MODEL_VERSION=0.1.0

# Authentication (OIDC / OAuth2)
AUTH_ENABLED=true
AUTH_JWKS_URL=https://auth.meetmux.com/.well-known/jwks.json
AUTH_AUDIENCE=https://api.meetmux.com
AUTH_ISSUER=https://auth.meetmux.com/

# Rate Limiting
RATE_LIMIT_PER_MINUTE=120
```

---

## 4. Security Hardening & Least Privilege

1. **Database Least Privilege**:
   - Create a dedicated application role in Neo4j with read/write access to business nodes (`Location`, `Shipment`, `SensorReading`) only.
   - Deny administrative capabilities (`DROP DATABASE`, `ALTER SCHEMA`) to the runtime user.
2. **Encrypted Connections**:
   - Use `neo4j+s://` to enforce TLS certificate verification.
   - Reject unencrypted `bolt://` or `http://` in production environments.
3. **CORS & Headers**:
   - Only whitelist exact operational domain names in `BACKEND_CORS_ORIGINS`.
   - Security middleware injects `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security: max-age=31536000`, and `Content-Security-Policy`.
4. **Log Scrubbing**:
   - Structured JSON logs automatically scrub authorization tokens, passwords, and sensitive shipment notes.
   - Correlation IDs (`x-request-id`) propagate through all downstream service calls.

---

## 5. Model Operations, Drift & Governance

1. **Prediction Target**:
   - Binary arrival delay exceeding 30 minutes beyond planned schedule.
2. **Model Retraining Schedule**:
   - Monthly scheduled retraining or triggered when Kolmogorov-Smirnov drift statistics on shipment distance or delay rate exceed $\alpha = 0.05$.
3. **Auditability & Integrity**:
   - Every inference response returns:
     - `prediction_status`: (`model_prediction` vs `fallback_estimate`)
     - `model_version`: Immutable semantic tag (e.g. `0.1.0`)
     - `factors`: Human-readable contributing factors without claiming causation.

---

## 6. Backup & Disaster Recovery (DR)

1. **Neo4j Graph Database**:
   - Automated daily snapshots retained for 30 days.
   - Transaction log archiving enabled for Point-In-Time-Recovery (PITR).
   - RPO (Recovery Point Objective): $\le 1$ hour.
   - RTO (Recovery Time Objective): $\le 15$ minutes.
2. **Model Artifacts**:
   - S3 bucket versioning ensures prior model artifacts are preserved and can be rolled back instantaneously via `MODEL_ARTIFACT_PATH` update.

---

## 7. Monitoring, Metrics & Alerting

- **Readiness / Liveness Probes**:
  - `/api/v1/health` checks live connectivity to Neo4j, OSRM router, and ML model.
  - Returns HTTP 200 with status breakdown for Kubernetes readiness checks.
- **Key Metrics to Track**:
  - `http_requests_total` by status code (Alert if 5xx error rate > 1% over 5m).
  - `route_planning_latency_ms` (Alert if p95 > 2500ms).
  - `graph_query_latency_ms` (Alert if p95 > 500ms).
  - `prediction_fallback_count` (Alert if fallback proportion spikes, indicating missing model or feature schema breach).
