# Architecture Overview & Delay-Risk Integrity

## 1. System Components

The MeetMux Supply Chain Delay Risk and Route Planning platform is built with clear component boundaries:

1. **Frontend**: React 19 + TypeScript + Vite. Uses a custom dark operations dashboard design system and Leaflet for interactive road routing and facility mapping.
2. **Backend**: FastAPI + Pydantic v2. Provides REST API endpoints (`/api/v1/health`, `/api/v1/shipments`, `/api/v1/routes/plan`, `/api/v1/shipments/{id}/network`) with structured logging, CORS validation, and correlation IDs (`X-Request-ID`).
3. **Graph Service**: Abstracted behind `GraphServiceBase`. Connects to Neo4j via official async driver or automatically falls back to an in-memory graph repository for local zero-dependency evaluation.
4. **Route Service**: Abstracted behind `RouteProviderBase`. Supports OSRM (self-hosted or configured) with transparent fallback to geometric corridor routing when the provider is unreachable or rate-limited.
5. **Prediction Service**: Abstracted behind `PredictionServiceBase`. Loads versioned `.joblib` model artifacts. When no model is loaded, it provides a transparent, rule-based fallback estimate.

---

## 2. Delay-Risk Integrity & Transparency

### Prediction Target & Horizon
- **Target**: Binary classification indicating whether a shipment will arrive > 30 minutes after its planned delivery schedule (`delay_minutes > 30`).
- **Horizon**: Evaluated at dispatch or route-planning time prior to departure.

### Status Delineation
The application strictly distinguishes:
1. `model_prediction`: Real inference produced by an authenticated, versioned machine learning artifact (`delay_model_v0.1.0.joblib`).
2. `fallback_estimate`: Heuristic estimate clearly flagged in the UI with a warning icon, explaining the baseline factors used.
3. `unavailable`: External dependency error where no estimate can be responsibly provided.

**Never are synthetic or rule-based demo scores passed off as validated machine learning predictions.**

---

## 3. Data Leakage Prevention in Training

In `backend/train_model.py`:
- **Temporal & Group Separation**: Shipments are ordered chronologically. Training records strictly precede validation records.
- Records for the same shipment ID never cross the train/validation split boundary.
- Evaluation metrics reported: ROC-AUC, Brier score (calibration), Accuracy, Precision, Recall, and Confusion Matrix.
