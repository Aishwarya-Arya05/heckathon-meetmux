# Supply Chain Shipment Delay Risk & Route Planning System

> An operations dashboard for supply-chain teams to track shipments, compare road routes, and assess delay risk with transparent contributing factors.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green)
![React](https://img.shields.io/badge/React-18+-61DAFB)
![Neo4j](https://img.shields.io/badge/Neo4j-5+-008CC1)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)               │
│  Shipment Selector │ Map (Leaflet) │ Route & Risk Panels │
└──────────────────────────┬──────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────┐
│                  Backend (FastAPI)                        │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌───────────┐  │
│  │ Graph    │ │ Route    │ │ Feature   │ │ Prediction│  │
│  │ Service  │ │ Service  │ │ Builder   │ │ Service   │  │
│  └────┬─────┘ └────┬─────┘ └─────┬─────┘ └─────┬─────┘  │
└───────┼────────────┼─────────────┼─────────────┼────────┘
        │            │             │             │
   ┌────▼────┐  ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
   │ Neo4j   │  │  OSRM   │  │  CSV /  │  │ XGBoost │
   │ Graph   │  │ Router  │  │  Neo4j  │  │ Model   │
   └─────────┘  └─────────┘  └─────────┘  └─────────┘
```

## Quick Start (Local Demo)

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (for Neo4j)

### 1. Clone and configure
```bash
git clone https://github.com/royabhishek2003/heckathon-meetmux.git
cd heckathon-meetmux
cp .env.example .env
```

### 2. Start infrastructure
```bash
docker compose up -d neo4j
```

### 3. Start the backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.seed           # Load demo data into Neo4j
uvicorn app.main:app --reload --port 8000
```

### 4. Start the frontend
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

> **Demo Mode**: The application runs with sample data and fallback risk estimates by default. All demo data is clearly labelled. See [Production Deployment](#production-deployment) for real integration setup.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health and dependency readiness |
| GET | `/api/v1/shipments` | List shipments (paginated) |
| GET | `/api/v1/shipments/{id}` | Shipment details |
| GET | `/api/v1/shipments/{id}/network` | Connected supply-chain locations |
| POST | `/api/v1/routes/plan` | Plan routes between two points |

Full OpenAPI docs available at `http://localhost:8000/docs` when the backend is running.

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI application entry
│   │   ├── config.py               # Settings from environment
│   │   ├── dependencies.py         # Dependency injection
│   │   ├── middleware.py           # CORS, logging, error handling
│   │   ├── models/
│   │   │   ├── domain.py           # Domain entities
│   │   │   └── schemas.py          # API request/response schemas
│   │   ├── routers/
│   │   │   ├── health.py           # Health checks
│   │   │   └── shipments.py        # Shipment & route endpoints
│   │   └── services/
│   │       ├── graph_service.py    # Neo4j graph queries
│   │       ├── route_service.py    # OSRM / mock routing
│   │       ├── feature_builder.py  # Feature engineering
│   │       └── prediction_service.py # Model inference / fallback
│   ├── data/
│   │   ├── sample/                 # Demo CSV data
│   │   └── neo4j/                  # Cypher schema & seed scripts
│   ├── models/                     # Trained model artifacts
│   ├── tests/                      # pytest test suite
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/             # React UI components
│   │   ├── services/               # API client
│   │   └── types/                  # TypeScript interfaces
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
├── .github/workflows/ci.yml
└── docs/
    ├── architecture.md
    ├── data-model.md
    ├── deployment.md
    └── operations.md
```

---

## Data Model

See [docs/data-model.md](docs/data-model.md) for full Neo4j schema, entity definitions, and example Cypher queries.

### Design Decision: Neo4j as Primary Store

All supply-chain entities (suppliers, warehouses, shops, shipments, sensors) live in Neo4j. This choice avoids data duplication between a relational DB and a graph DB. Neo4j handles both the graph traversal queries (connected locations, supply paths) and the tabular lookups (shipment by ID, sensor readings by shipment). If query patterns diverge significantly at scale (e.g., high-throughput sensor ingestion), PostgreSQL can be introduced for time-series sensor data with Neo4j retaining the graph relationships.

---

## Delay Risk Prediction

### Prediction Target
- **Binary classification**: Will the shipment arrive more than 30 minutes after its planned delivery time?
- **Horizon**: Prediction is made at route-planning time, before the shipment departs.

### Status Labels
| Label | Meaning |
|-------|---------|
| `model_prediction` | Trained model loaded; result from XGBoost inference |
| `fallback_estimate` | No valid model; rule-based estimate from route distance + historical averages |
| `unavailable` | Prediction cannot be produced |

See [docs/architecture.md](docs/architecture.md) for training pipeline requirements and evaluation criteria.

---

## Production Deployment

See [docs/deployment.md](docs/deployment.md) for the full guide. Key requirements:

| Service | What's needed |
|---------|--------------|
| Neo4j | Managed instance (Aura) or self-hosted with TLS |
| OSRM | Self-hosted instance with regional OSM data |
| Map tiles | Mapbox, Stadia, or self-hosted tile server |
| Model | Trained `.joblib` artifact at `MODEL_ARTIFACT_PATH` |
| Auth | OIDC/JWT provider (Auth0, Keycloak, etc.) |
| Secrets | Vault, cloud secret manager, or secure env injection |

---

## Development

```bash
# Run all tests
cd backend && pytest -v

# Type check frontend
cd frontend && npx tsc --noEmit

# Lint
cd backend && ruff check .
cd frontend && npm run lint
```

---

## License

MIT – See [LICENSE](LICENSE) for details.
