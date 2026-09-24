"""Tests for feature builder, prediction service, and fallback estimation."""

from app.models.domain import PredictionStatus, RiskBand
from app.services.feature_builder import PredictionFeatures
from app.services.prediction_service import FallbackPredictionService, XGBoostPredictionService


def test_fallback_prediction_produces_valid_band():
    service = FallbackPredictionService()
    
    # Low risk features
    low_features = PredictionFeatures(
        distance_km=150.0,
        duration_minutes=180.0,
        historical_avg_delay_minutes=5.0,
        historical_delay_rate=0.05,
        historical_shipment_count=20,
        sensor_alert_count=0,
        has_temperature_alert=False,
        has_vibration_alert=False,
        has_humidity_alert=False,
        weight_kg=800.0,
        linked_locations_with_delays=0,
        total_linked_locations=3,
        contributing_factors=[],
    )
    res = service.predict(low_features)
    assert res.prediction_status == PredictionStatus.FALLBACK_ESTIMATE
    assert res.risk_band in (RiskBand.LOW, RiskBand.MEDIUM)
    assert 0.0 <= res.probability <= 1.0
    assert len(res.factors) > 0


def test_fallback_prediction_high_risk_triggers_elevated_band():
    service = FallbackPredictionService()
    
    # High risk features: long distance, high delay rate, sensor anomalies, disrupted linked locations
    high_features = PredictionFeatures(
        distance_km=2400.0,
        duration_minutes=2500.0,
        historical_avg_delay_minutes=120.0,
        historical_delay_rate=0.85,
        historical_shipment_count=15,
        sensor_alert_count=4,
        has_temperature_alert=True,
        has_vibration_alert=True,
        has_humidity_alert=False,
        weight_kg=12000.0,
        linked_locations_with_delays=3,
        total_linked_locations=4,
        contributing_factors=[],
    )
    res = service.predict(high_features)
    assert res.prediction_status == PredictionStatus.FALLBACK_ESTIMATE
    assert res.risk_band in (RiskBand.HIGH, RiskBand.CRITICAL)
    assert res.probability > 0.5


def test_xgboost_service_falls_back_when_no_artifact():
    # Pass non-existent path
    service = XGBoostPredictionService(model_path="/nonexistent/model.joblib", version="9.9.9")
    assert not service.is_model_loaded()
    
    features = PredictionFeatures(
        distance_km=500.0,
        duration_minutes=600.0,
        historical_avg_delay_minutes=10.0,
        historical_delay_rate=0.1,
        historical_shipment_count=10,
        sensor_alert_count=0,
        has_temperature_alert=False,
        has_vibration_alert=False,
        has_humidity_alert=False,
        weight_kg=1000.0,
        linked_locations_with_delays=0,
        total_linked_locations=2,
        contributing_factors=[],
    )
    res = service.predict(features)
    # Must explicitly fall back to fallback_estimate and NOT claim model prediction
    assert res.prediction_status == PredictionStatus.FALLBACK_ESTIMATE
    assert res.model_version is None or res.model_version == ""
