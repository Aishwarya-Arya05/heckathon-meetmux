"""
Feature builder — prepares input features for the prediction model.

Collects and normalises shipment attributes, route metrics, historical delay
patterns, and sensor readings into a feature vector suitable for model input.

This module does NOT perform inference — it only constructs the feature dict.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.models.schemas import Coordinates, RiskFactor, RouteOption, ShipmentDetail

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sample"


@dataclass
class FeatureVector:
    """Structured feature set for delay prediction."""

    # Route features
    distance_km: float = 0.0
    duration_minutes: float = 0.0

    # Shipment features
    weight_kg: float = 0.0
    cargo_type_encoded: int = 0  # 0=unknown, 1=electronics, 2=auto_parts, 3=raw_materials, 4=chemicals

    # Historical features
    historical_delay_rate: float = 0.0  # Rate of delayed shipments on this corridor
    corridor_shipment_count: int = 0    # Number of past shipments on this corridor

    # Sensor features
    sensor_alert_count: int = 0
    max_temperature: float = 25.0
    max_vibration: float = 0.0

    # Network features
    linked_location_count: int = 0
    has_disrupted_link: bool = False

    # Metadata (not model features)
    contributing_factors: list[RiskFactor] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return only the numeric features for model input."""
        return {
            "distance_km": self.distance_km,
            "duration_minutes": self.duration_minutes,
            "weight_kg": self.weight_kg,
            "cargo_type_encoded": self.cargo_type_encoded,
            "historical_delay_rate": self.historical_delay_rate,
            "corridor_shipment_count": self.corridor_shipment_count,
            "sensor_alert_count": self.sensor_alert_count,
            "max_temperature": self.max_temperature,
            "max_vibration": self.max_vibration,
            "linked_location_count": self.linked_location_count,
            "has_disrupted_link": int(self.has_disrupted_link),
        }

    @property
    def feature_names(self) -> list[str]:
        return list(self.to_dict().keys())


# ── Cargo type encoding ──────────────────────────────────────

CARGO_TYPE_MAP = {
    "electronics": 1,
    "auto_parts": 2,
    "raw_materials": 3,
    "chemicals": 4,
}


class FeatureBuilder:
    """
    Constructs feature vectors from shipment, route, and contextual data.
    Also produces human-readable contributing factors for explainability.
    """

    def __init__(self):
        self._shipment_history: list[dict] = []
        self._sensor_data: list[dict] = []
        self._load_historical_data()

    def _load_historical_data(self):
        """Load sample historical data for feature computation."""
        shp_file = DATA_DIR / "shipments.csv"
        if shp_file.exists():
            with open(shp_file, newline="", encoding="utf-8") as f:
                self._shipment_history = list(csv.DictReader(f))

        sensor_file = DATA_DIR / "sensors.csv"
        if sensor_file.exists():
            with open(sensor_file, newline="", encoding="utf-8") as f:
                self._sensor_data = list(csv.DictReader(f))

        logger.info(
            "FeatureBuilder loaded %d historical shipments, %d sensor readings",
            len(self._shipment_history),
            len(self._sensor_data),
        )

    def build_features(
        self,
        route: RouteOption,
        shipment: Optional[ShipmentDetail] = None,
        origin: Optional[Coordinates] = None,
        destination: Optional[Coordinates] = None,
    ) -> FeatureVector:
        """Build a complete feature vector for a route + shipment combination."""
        fv = FeatureVector()
        factors: list[RiskFactor] = []

        # ── Route features ───────────────────────────────────
        fv.distance_km = route.distance_km
        fv.duration_minutes = route.duration_minutes

        if route.distance_km > 1000:
            factors.append(RiskFactor(
                name="long_distance",
                label="Long-distance route",
                value=f"{route.distance_km:.0f} km",
                impact="increases_risk",
            ))
        elif route.distance_km < 200:
            factors.append(RiskFactor(
                name="short_distance",
                label="Short-distance route",
                value=f"{route.distance_km:.0f} km",
                impact="decreases_risk",
            ))

        # ── Shipment features ────────────────────────────────
        if shipment:
            fv.weight_kg = shipment.weight_kg or 0.0
            fv.cargo_type_encoded = CARGO_TYPE_MAP.get(shipment.cargo_type or "", 0)
            fv.linked_location_count = len(shipment.linked_locations)

            if fv.weight_kg > 5000:
                factors.append(RiskFactor(
                    name="heavy_cargo",
                    label="Heavy cargo load",
                    value=f"{fv.weight_kg:.0f} kg",
                    impact="increases_risk",
                ))

            # ── Historical delay analysis ────────────────────
            origin_id = shipment.origin.id
            dest_id = shipment.destination.id
            corridor_shipments = [
                s for s in self._shipment_history
                if s.get("origin_id") == origin_id and s.get("destination_id") == dest_id
            ]
            fv.corridor_shipment_count = len(corridor_shipments)

            if corridor_shipments:
                delayed = sum(1 for s in corridor_shipments if s.get("is_delayed") == "true")
                fv.historical_delay_rate = delayed / len(corridor_shipments)

                if fv.historical_delay_rate > 0.3:
                    factors.append(RiskFactor(
                        name="historical_delay_rate",
                        label="Historical delay rate on this corridor",
                        value=f"{fv.historical_delay_rate:.0%}",
                        impact="increases_risk",
                    ))
                elif fv.historical_delay_rate == 0 and fv.corridor_shipment_count >= 3:
                    factors.append(RiskFactor(
                        name="clean_history",
                        label="No delays recorded on this corridor",
                        value=f"0 delays in {fv.corridor_shipment_count} shipments",
                        impact="decreases_risk",
                    ))
            else:
                factors.append(RiskFactor(
                    name="no_history",
                    label="No historical data for this corridor",
                    value="Insufficient data",
                    impact="neutral",
                ))

            # ── Sensor analysis ──────────────────────────────
            relevant_locations = {shipment.origin.id, shipment.destination.id}
            relevant_locations.update(loc.id for loc in shipment.linked_locations)

            relevant_sensors = [
                s for s in self._sensor_data
                if s.get("location_id") in relevant_locations
            ]

            alerts = [s for s in relevant_sensors if s.get("alert") != "none"]
            fv.sensor_alert_count = len(alerts)

            if relevant_sensors:
                temps = [float(s["temperature_c"]) for s in relevant_sensors if s.get("temperature_c")]
                vibs = [float(s["vibration_g"]) for s in relevant_sensors if s.get("vibration_g")]
                fv.max_temperature = max(temps) if temps else 25.0
                fv.max_vibration = max(vibs) if vibs else 0.0

            if fv.sensor_alert_count > 0:
                alert_types = set(s.get("alert") for s in alerts)
                factors.append(RiskFactor(
                    name="sensor_alerts",
                    label="Active sensor alerts",
                    value=f"{fv.sensor_alert_count} alert(s): {', '.join(alert_types)}",
                    impact="increases_risk",
                ))

            if fv.max_temperature > 35:
                factors.append(RiskFactor(
                    name="high_temperature",
                    label="High temperature recorded",
                    value=f"{fv.max_temperature:.1f}°C",
                    impact="increases_risk",
                ))

            # ── Network disruption ───────────────────────────
            if fv.linked_location_count > 3:
                factors.append(RiskFactor(
                    name="complex_network",
                    label="Complex supply chain network",
                    value=f"{fv.linked_location_count} linked locations",
                    impact="increases_risk",
                ))

        fv.contributing_factors = factors
        return fv
