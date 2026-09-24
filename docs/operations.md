# Operations & Runbooks

## Health & Diagnostics

Check system health via the standardized endpoint:
```bash
curl -i http://localhost:8000/api/v1/health
```

Expected JSON response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development",
  "dependencies": [
    {
      "name": "graph_database",
      "status": "healthy",
      "message": "Connected"
    },
    {
      "name": "route_provider",
      "status": "healthy",
      "message": "Operational"
    },
    {
      "name": "prediction_model",
      "status": "healthy",
      "message": "model v0.1.0"
    }
  ]
}
```

## Model Retraining Runbook

When new ground-truth shipment logs arrive:

```bash
cd backend
python train_model.py --data data/sample/historical_delays.csv --version 0.2.0 --output-dir models
```

Restart or reload the backend with `MODEL_ARTIFACT_PATH=models/delay_model_v0.2.0.joblib` and `MODEL_VERSION=0.2.0`.
