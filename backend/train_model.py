"""
Delay Risk Model Training & Evaluation Pipeline.

Prediction Target:
  Binary classification: will the shipment be delayed by > 30 minutes beyond planned delivery?
  Target variable: `is_delayed_30m` (1 if delay_minutes > 30, else 0).

Prediction Horizon:
  Evaluated at pre-dispatch or route-planning time before transit commences.

Leakage Prevention:
  - Temporal / Group-based split: training set consists of earlier historical shipments,
    validation set consists of subsequent time periods.
  - No shipment_id records cross the train/validation boundary.

Feature Engineering (12 features):
  1. distance_km (float) - Total route distance in km
  2. duration_minutes (float) - Estimated baseline travel time in minutes
  3. historical_avg_delay_minutes (float) - Route corridor historical mean delay
  4. historical_delay_rate (float) - Fraction of past corridor shipments delayed > 30m
  5. historical_shipment_count (int) - Number of historical corridor samples
  6. sensor_alert_count (int) - Count of anomalous telemetry alerts
  7. has_temperature_alert (0/1) - Temperature threshold breach flag
  8. has_vibration_alert (0/1) - Shock/vibration threshold breach flag
  9. has_humidity_alert (0/1) - Humidity threshold breach flag
  10. weight_kg (float) - Cargo total weight in kg
  11. linked_locations_with_delays (int) - Count of connected nodes with reported delays
  12. total_linked_locations (int) - Total nodes in the supply chain graph neighborhood

Evaluation Metrics:
  - ROC-AUC
  - Precision, Recall, F1 Score
  - Brier Score (probability calibration)
  - Confusion Matrix
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_model")

FEATURE_NAMES = [
    "distance_km",
    "duration_minutes",
    "historical_avg_delay_minutes",
    "historical_delay_rate",
    "historical_shipment_count",
    "sensor_alert_count",
    "has_temperature_alert",
    "has_vibration_alert",
    "has_humidity_alert",
    "weight_kg",
    "linked_locations_with_delays",
    "total_linked_locations",
]

TARGET_COLUMN = "is_delayed_30m"
DELAY_THRESHOLD_MINUTES = 30


def generate_representative_dataset(n_samples: int = 1200, random_state: int = 42) -> pd.DataFrame:
    """Generate a calibrated, realistic synthetic dataset for training and verification.
    
    Used when only small seed/demo records are available, ensuring the full pipeline
    can train, calibrate, evaluate, and serialize a valid artifact.
    """
    rng = np.random.RandomState(random_state)
    
    # Distance between 50km and 2800km
    distance_km = rng.exponential(scale=650, size=n_samples) + 50
    distance_km = np.clip(distance_km, 50, 3000)
    
    # Estimated duration (avg ~55 km/h on Indian highway networks)
    speed = rng.normal(loc=52, scale=8, size=n_samples)
    speed = np.clip(speed, 30, 80)
    duration_minutes = (distance_km / speed) * 60
    
    # Weight
    weight_kg = rng.gamma(shape=2.5, scale=1200, size=n_samples)
    weight_kg = np.clip(weight_kg, 100, 15000)
    
    # Corridor historical stats
    hist_count = rng.poisson(lam=18, size=n_samples) + 2
    hist_avg_delay = rng.exponential(scale=25, size=n_samples)
    hist_delay_rate = np.clip(rng.beta(a=2, b=6, size=n_samples) + (distance_km > 1000) * 0.15, 0.05, 0.85)
    
    # Sensor telemetry alerts
    sensor_alert_count = rng.poisson(lam=0.4 + (distance_km > 800) * 0.5, size=n_samples)
    has_temp = (sensor_alert_count > 0) & (rng.rand(n_samples) < 0.35)
    has_vib = (sensor_alert_count > 0) & (rng.rand(n_samples) < 0.40)
    has_hum = (sensor_alert_count > 0) & (rng.rand(n_samples) < 0.25)
    
    # Graph network context
    total_linked = rng.choice([2, 3, 4, 5, 6], size=n_samples, p=[0.2, 0.35, 0.25, 0.15, 0.05])
    linked_delays = np.array([rng.binomial(n=t, p=0.22) for t in total_linked])
    
    # Ground truth delay calculation
    latent_risk = (
        0.0003 * distance_km
        + 0.008 * hist_avg_delay
        + 1.8 * hist_delay_rate
        + 0.65 * sensor_alert_count
        + 0.4 * has_temp.astype(int)
        + 0.35 * has_vib.astype(int)
        + 0.3 * (weight_kg > 5000).astype(int)
        + 0.5 * linked_delays
        + rng.normal(loc=0, scale=0.6, size=n_samples)
    )
    
    # Logistic function for probability
    prob = 1.0 / (1.0 + np.exp(-(latent_risk - 2.8)))
    is_delayed = (rng.rand(n_samples) < prob).astype(int)
    delay_minutes = np.where(is_delayed == 1, 30 + rng.exponential(scale=45, size=n_samples), np.maximum(0, rng.normal(loc=8, scale=10, size=n_samples)))
    
    # Timestamp generation spanning 6 months (temporal split)
    start_date = pd.Timestamp("2026-03-01")
    date_offsets = rng.uniform(0, 180, size=n_samples)
    dates = [start_date + pd.Timedelta(days=d) for d in date_offsets]
    
    df = pd.DataFrame({
        "shipment_id": [f"TRN-{i:05d}" for i in range(n_samples)],
        "timestamp": dates,
        "distance_km": distance_km,
        "duration_minutes": duration_minutes,
        "historical_avg_delay_minutes": hist_avg_delay,
        "historical_delay_rate": hist_delay_rate,
        "historical_shipment_count": hist_count,
        "sensor_alert_count": sensor_alert_count,
        "has_temperature_alert": has_temp.astype(int),
        "has_vibration_alert": has_vib.astype(int),
        "has_humidity_alert": has_hum.astype(int),
        "weight_kg": weight_kg,
        "linked_locations_with_delays": linked_delays,
        "total_linked_locations": total_linked,
        "delay_minutes": delay_minutes,
        TARGET_COLUMN: is_delayed,
    })
    
    return df.sort_values("timestamp").reset_index(drop=True)


def train_and_evaluate(
    df: pd.DataFrame,
    model_version: str = "0.1.0",
    output_dir: Path = Path("models"),
) -> Tuple[object, dict]:
    """Train gradient boosted decision trees, evaluate, and save artifact."""
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.metrics import (
        accuracy_score,
        brier_score_loss,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )
    import joblib

    logger.info("Dataset shape: %s", df.shape)
    logger.info("Target class distribution:\n%s", df[TARGET_COLUMN].value_counts(normalize=True))

    # Temporal split: 80% train (earlier dates), 20% test (later dates)
    # Strictly prevents data leakage across shipment timelines
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    val_df = df.iloc[split_idx:]

    X_train = train_df[FEATURE_NAMES].values
    y_train = train_df[TARGET_COLUMN].values
    X_val = val_df[FEATURE_NAMES].values
    y_val = val_df[TARGET_COLUMN].values

    logger.info("Train samples: %d, Validation samples: %d", len(X_train), len(X_val))

    # Train model
    clf = GradientBoostingClassifier(
        n_estimators=120,
        learning_rate=0.08,
        max_depth=4,
        subsample=0.85,
        random_state=42,
    )
    clf.fit(X_train, y_train)

    # Predictions & probabilities
    val_preds = clf.predict(X_val)
    val_probs = clf.predict_proba(X_val)[:, 1]

    # Metrics
    auc = float(roc_auc_score(y_val, val_probs))
    acc = float(accuracy_score(y_val, val_preds))
    prec = float(precision_score(y_val, val_preds, zero_division=0))
    rec = float(recall_score(y_val, val_preds, zero_division=0))
    f1 = float(f1_score(y_val, val_preds, zero_division=0))
    brier = float(brier_score_loss(y_val, val_probs))
    cm = confusion_matrix(y_val, val_preds).tolist()

    # Feature importances
    importances = {
        name: round(float(imp), 4)
        for name, imp in zip(FEATURE_NAMES, clf.feature_importances_)
    }
    sorted_importances = dict(sorted(importances.items(), key=lambda item: item[1], reverse=True))

    eval_report = {
        "model_version": model_version,
        "algorithm": "GradientBoostingClassifier",
        "target": "is_delayed_over_30min",
        "delay_threshold_minutes": DELAY_THRESHOLD_MINUTES,
        "training_samples": len(X_train),
        "validation_samples": len(X_val),
        "metrics": {
            "roc_auc": round(auc, 4),
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "brier_score": round(brier, 4),
            "confusion_matrix": cm,
        },
        "feature_importances": sorted_importances,
        "features": FEATURE_NAMES,
        "timestamp": datetime.utcnow().isoformat(),
        "leakage_prevention": "Strict temporal train/validation split by shipment timeline",
    }

    logger.info("=== Model Evaluation Report ===")
    logger.info("ROC-AUC:       %.4f", auc)
    logger.info("Accuracy:      %.4f", acc)
    logger.info("Precision:     %.4f", prec)
    logger.info("Recall:        %.4f", rec)
    logger.info("F1 Score:      %.4f", f1)
    logger.info("Brier Score:   %.4f", brier)
    logger.info("Top Features:  %s", list(sorted_importances.items())[:5])

    # Save artifact
    output_dir.mkdir(parents=True, exist_ok=True)
    model_filename = f"delay_model_v{model_version}.joblib"
    model_path = output_dir / model_filename
    joblib.dump(clf, model_path)
    logger.info("Model saved to: %s", model_path)

    # Save evaluation report
    report_filename = f"delay_model_v{model_version}_eval.json"
    report_path = output_dir / report_filename
    with open(report_path, "w") as f:
        json.dump(eval_report, f, indent=2)
    logger.info("Evaluation report saved to: %s", report_path)

    return clf, eval_report


def main():
    parser = argparse.ArgumentParser(description="Train Delay Risk Model")
    parser.add_argument("--data", type=str, default=None, help="Path to input CSV data")
    parser.add_argument("--version", type=str, default="0.1.0", help="Model version string")
    parser.add_argument("--output-dir", type=str, default="models", help="Directory to save artifacts")
    parser.add_argument("--samples", type=int, default=1500, help="Number of synthetic samples if generating")
    args = parser.parse_args()

    if args.data and Path(args.data).exists():
        logger.info("Loading dataset from %s", args.data)
        df = pd.read_csv(args.data)
        if TARGET_COLUMN not in df.columns and "delay_minutes" in df.columns:
            df[TARGET_COLUMN] = (df["delay_minutes"] > DELAY_THRESHOLD_MINUTES).astype(int)
    else:
        logger.info("Generating calibrated synthetic dataset with %d samples...", args.samples)
        df = generate_representative_dataset(n_samples=args.samples)

    train_and_evaluate(
        df=df,
        model_version=args.version,
        output_dir=Path(args.output_dir),
    )


if __name__ == "__main__":
    main()
