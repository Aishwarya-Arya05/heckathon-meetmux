"""
Delay prediction service.

Provides delay-risk estimates for shipment routes. Supports two modes:

1. **Model mode** — loads a trained, versioned model artifact (.joblib) and
   performs real inference. Results are labelled with prediction_status="model".

2. **Fallback mode** — when no valid model is configured, uses a transparent
   rule-based heuristic. Results are labelled with prediction_status="fallback".

IMPORTANT: Fallback estimates are NOT validated predictions. They exist to
make the UI functional during development and demo. The frontend must clearly
communicate this distinction to users.

Prediction target: Whether a shipment will arrive >30 minutes after its
planned delivery time (binary classification).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from app.models.schemas import (
    PredictionStatus,
    RiskBand,
    RouteOption,
    RouteRiskEstimate,
    ShipmentDetail,
)
from app.services.feature_builder import FeatureBuilder, FeatureVector

logger = logging.getLogger(__name__)


# ── Abstract interface ───────────────────────────────────────


class PredictionServiceBase(ABC):
    """Interface for delay prediction."""

    @abstractmethod
    async def predict(
        self,
        features: FeatureVector,
        route: RouteOption,
        shipment: Optional[ShipmentDetail] = None,
    ) -> RouteRiskEstimate:
        ...

    @abstractmethod
    def get_model_version(self) -> Optional[str]:
        ...

    @abstractmethod
    def get_prediction_status_type(self) -> PredictionStatus:
        ...


# ── Model-based prediction ──────────────────────────────────


class ModelPredictionService(PredictionServiceBase):
    """
    Loads a trained model artifact and performs real inference.
    Model must be a scikit-learn compatible pipeline saved with joblib.
    """

    def __init__(self, model_path: Path, model_version: Optional[str] = None):
        import joblib

        self._model_version = model_version or "unknown"
        try:
            self._model = joblib.load(model_path)
            logger.info("Loaded prediction model v%s from %s", self._model_version, model_path)
        except Exception:
            logger.exception("Failed to load model from %s", model_path)
            raise

    def get_model_version(self) -> Optional[str]:
        return self._model_version

    def get_prediction_status_type(self) -> PredictionStatus:
        return PredictionStatus.MODEL

    async def predict(
        self,
        features: FeatureVector,
        route: RouteOption,
        shipment: Optional[ShipmentDetail] = None,
    ) -> RouteRiskEstimate:
        import numpy as np

        try:
            feature_dict = features.to_dict()
            feature_array = np.array([list(feature_dict.values())])

            # Use predict_proba if available (binary classifier)
            if hasattr(self._model, "predict_proba"):
                proba = self._model.predict_proba(feature_array)[0]
                delay_probability = float(proba[1]) if len(proba) > 1 else float(proba[0])
            else:
                prediction = self._model.predict(feature_array)[0]
                delay_probability = float(prediction)

            delay_probability = max(0.0, min(1.0, delay_probability))
            risk_band = _probability_to_band(delay_probability)

            return RouteRiskEstimate(
                probability=round(delay_probability, 3),
                risk_band=risk_band,
                prediction_status=PredictionStatus.MODEL,
                model_version=self._model_version,
                contributing_factors=features.contributing_factors,
                explanation=_build_explanation(risk_band, features, is_model=True),
            )

        except Exception:
            logger.exception("Model inference failed, returning unavailable")
            return RouteRiskEstimate(
                probability=0.0,
                risk_band=RiskBand.MEDIUM,
                prediction_status=PredictionStatus.UNAVAILABLE,
                model_version=self._model_version,
                contributing_factors=[],
                explanation="Model inference failed. Risk estimate is unavailable.",
            )


# ── Fallback heuristic ──────────────────────────────────────


class FallbackPredictionService(PredictionServiceBase):
    """
    Rule-based fallback estimator used when no trained model is available.
    Produces estimates labelled as "fallback" — NOT validated predictions.
    """

    def get_model_version(self) -> Optional[str]:
        return None

    def get_prediction_status_type(self) -> PredictionStatus:
        return PredictionStatus.FALLBACK

    async def predict(
        self,
        features: FeatureVector,
        route: RouteOption,
        shipment: Optional[ShipmentDetail] = None,
    ) -> RouteRiskEstimate:
        # Simple weighted heuristic — NOT a trained model
        score = 0.2  # Base risk

        # Distance factor
        if features.distance_km > 1500:
            score += 0.15
        elif features.distance_km > 800:
            score += 0.08
        elif features.distance_km < 200:
            score -= 0.05

        # Historical delay factor
        score += features.historical_delay_rate * 0.3

        # Sensor alerts
        score += min(features.sensor_alert_count * 0.05, 0.2)

        # Temperature
        if features.max_temperature > 40:
            score += 0.1
        elif features.max_temperature > 35:
            score += 0.05

        # Weight
        if features.weight_kg > 5000:
            score += 0.05

        # Network complexity
        if features.linked_location_count > 4:
            score += 0.05

        # Clamp
        delay_probability = max(0.05, min(0.95, score))
        risk_band = _probability_to_band(delay_probability)

        return RouteRiskEstimate(
            probability=round(delay_probability, 3),
            risk_band=risk_band,
            prediction_status=PredictionStatus.FALLBACK,
            model_version=None,
            contributing_factors=features.contributing_factors,
            explanation=_build_explanation(risk_band, features, is_model=False),
        )


# ── Helpers ──────────────────────────────────────────────────


def _probability_to_band(p: float) -> RiskBand:
    if p < 0.2:
        return RiskBand.LOW
    elif p < 0.5:
        return RiskBand.MEDIUM
    elif p < 0.75:
        return RiskBand.HIGH
    else:
        return RiskBand.CRITICAL


def _build_explanation(band: RiskBand, features: FeatureVector, is_model: bool) -> str:
    source = "model-based prediction" if is_model else "rule-based fallback estimate (not a validated prediction)"

    increasing = [f.label for f in features.contributing_factors if f.impact == "increases_risk"]
    decreasing = [f.label for f in features.contributing_factors if f.impact == "decreases_risk"]

    parts = [f"This {band.value}-risk assessment is a {source}."]

    if increasing:
        parts.append(f"Factors increasing risk: {'; '.join(increasing)}.")
    if decreasing:
        parts.append(f"Factors decreasing risk: {'; '.join(decreasing)}.")
    if not increasing and not decreasing:
        parts.append("No significant risk factors identified.")

    return " ".join(parts)


# ── Factory ──────────────────────────────────────────────────


def create_prediction_service(
    model_path: Optional[Path] = None,
    model_version: Optional[str] = None,
) -> PredictionServiceBase:
    if model_path and model_path.exists():
        try:
            service = ModelPredictionService(model_path, model_version)
            logger.info("Using model-based prediction service")
            return service
        except Exception:
            logger.warning("Failed to load model, falling back to heuristic", exc_info=True)

    logger.info("Using fallback prediction service (rule-based, NOT a trained model)")
    return FallbackPredictionService()
