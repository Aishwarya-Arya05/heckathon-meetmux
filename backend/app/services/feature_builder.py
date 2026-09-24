"""
Feature builder – prepares input features for delay-risk prediction.

Extracts features from:
  - Route characteristics (distance, duration)
  - Historical delay patterns for origin→destination pairs
  - Sensor alerts
  - Cargo and weight properties
  - Linked-location disruption signals
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from app.models.domain import (
    CandidateRoute,
    Coordinates,
    RiskFactor,
    SensorReading,
    Shipment,
    SupplyChainLink,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sample"


@dataclass
class PredictionFeatures:
    """Structured feature vector for model input."""

    # Route features
    distance_km: float = 0.0
    duration_minutes: float = 0.0

    # Historical delay features
    historical_avg_delay_minutes: float = 0.0
    historical_delay_rate: float = 0.0  # fraction of past shipments delayed > 30 min
    historical_shipment_count: int = 0

    # Sensor features
    sensor_alert_count: int = 0
    has_temperature_alert: bool = False
    has_vibration_alert: bool = False
    has_humidity_alert: bool = False

    # Cargo features
    cargo_type: str = ""
    weight_kg: float = 0.0

    # Network features
    linked_locations_with_delays: int = 0
    total_linked_locations: int = 0

    # Context
    origin_id: str = ""
    destination_id: str = ""
    season: str = ""

    # Human-readable factors
    contributing_factors: List[RiskFactor] = field(default_factory=list)


class FeatureBuilder:
    """Builds prediction features from available data sources."""

    def __init__(self):
        self._historical_data: List[Dict] = []
        self._load_historical_data()

    def _load_historical_data(self):
        hist_path = DATA_DIR / "historical_delays.csv"
        if hist_path.exists():
            with open(hist_path, newline="", encoding="utf-8") as f:
                self._historical_data = list(csv.DictReader(f))
            logger.info("Loaded %d historical delay records", len(self._historical_data))

    def build_features(
        self,
        route: CandidateRoute,
        shipment: Optional[Shipment] = None,
        sensors: Optional[List[SensorReading]] = None,
        links: Optional[List[SupplyChainLink]] = None,
        origin_id: str = "",
        destination_id: str = "",
    ) -> PredictionFeatures:
        """Build a complete feature set for a route prediction."""
        features = PredictionFeatures(
            distance_km=route.distance_km,
            duration_minutes=route.duration_minutes,
        )
        factors: List[RiskFactor] = []

        # ── Route features ───────────────────────────
        if route.distance_km > 1500:
            factors.append(
                RiskFactor(
                    name="Long distance",
                    description=f"Route covers {route.distance_km:.0f} km – longer routes have higher delay risk",
                    impact="increases_risk",
                    value=f"{route.distance_km:.0f} km",
                )
            )
        elif route.distance_km < 300:
            factors.append(
                RiskFactor(
                    name="Short distance",
                    description=f"Route is only {route.distance_km:.0f} km – shorter routes are less delay-prone",
                    impact="decreases_risk",
                    value=f"{route.distance_km:.0f} km",
                )
            )

        # ── Shipment context ─────────────────────────
        if shipment:
            features.cargo_type = shipment.cargo_type
            features.weight_kg = shipment.weight_kg
            features.origin_id = shipment.origin.id
            features.destination_id = shipment.destination.id
            origin_id = shipment.origin.id
            destination_id = shipment.destination.id

            if shipment.weight_kg > 3000:
                factors.append(
                    RiskFactor(
                        name="Heavy cargo",
                        description=f"Shipment weighs {shipment.weight_kg:.0f} kg – heavy loads take longer to handle",
                        impact="increases_risk",
                        value=f"{shipment.weight_kg:.0f} kg",
                    )
                )
        else:
            features.origin_id = origin_id
            features.destination_id = destination_id

        # ── Historical delays ────────────────────────
        if origin_id and destination_id:
            hist = self._get_historical_stats(origin_id, destination_id)
            features.historical_avg_delay_minutes = hist["avg_delay"]
            features.historical_delay_rate = hist["delay_rate"]
            features.historical_shipment_count = hist["count"]

            if hist["count"] > 0:
                if hist["delay_rate"] > 0.5:
                    factors.append(
                        RiskFactor(
                            name="High historical delay rate",
                            description=f"{hist['delay_rate']:.0%} of past shipments on this route were delayed >30 min",
                            impact="increases_risk",
                            value=f"{hist['delay_rate']:.0%} ({hist['count']} shipments)",
                        )
                    )
                elif hist["delay_rate"] < 0.2:
                    factors.append(
                        RiskFactor(
                            name="Good historical performance",
                            description=f"Only {hist['delay_rate']:.0%} of past shipments on this route were delayed",
                            impact="decreases_risk",
                            value=f"{hist['delay_rate']:.0%} ({hist['count']} shipments)",
                        )
                    )

                if hist["avg_delay"] > 60:
                    factors.append(
                        RiskFactor(
                            name="High average delay",
                            description=f"Average delay on this route is {hist['avg_delay']:.0f} minutes",
                            impact="increases_risk",
                            value=f"{hist['avg_delay']:.0f} min avg",
                        )
                    )

        # ── Sensor alerts ────────────────────────────
        if sensors:
            alert_readings = [s for s in sensors if s.alert]
            features.sensor_alert_count = len(alert_readings)
            features.has_temperature_alert = any(
                s.alert_reason == "temperature_high" for s in alert_readings
            )
            features.has_vibration_alert = any(
                s.alert_reason == "vibration_high" for s in alert_readings
            )
            features.has_humidity_alert = any(
                s.alert_reason == "humidity_high" for s in alert_readings
            )

            if features.sensor_alert_count > 0:
                alert_types = []
                if features.has_temperature_alert:
                    alert_types.append("temperature")
                if features.has_vibration_alert:
                    alert_types.append("vibration")
                if features.has_humidity_alert:
                    alert_types.append("humidity")

                factors.append(
                    RiskFactor(
                        name="Active sensor alerts",
                        description=f"{features.sensor_alert_count} sensor alert(s) detected: {', '.join(alert_types)}",
                        impact="increases_risk",
                        value=f"{features.sensor_alert_count} alerts",
                    )
                )

        # ── Network / linked locations ───────────────
        if links:
            features.total_linked_locations = len(
                set(
                    [l.source.id for l in links] + [l.target.id for l in links]
                )
            )
            # Check if any linked locations have recent delayed shipments
            delayed_locations = set()
            for link in links:
                for loc in [link.source, link.target]:
                    if self._location_has_recent_delays(loc.id):
                        delayed_locations.add(loc.id)

            features.linked_locations_with_delays = len(delayed_locations)

            if delayed_locations:
                factors.append(
                    RiskFactor(
                        name="Linked location disruptions",
                        description=f"{len(delayed_locations)} connected location(s) have recent delay history",
                        impact="increases_risk",
                        value=f"{len(delayed_locations)} affected",
                    )
                )

        # ── Season ───────────────────────────────────
        month = datetime.now().month
        if 6 <= month <= 9:
            features.season = "monsoon"
            factors.append(
                RiskFactor(
                    name="Monsoon season",
                    description="Current monsoon season increases delay probability due to weather disruptions",
                    impact="increases_risk",
                    value="June–September",
                )
            )
        elif 11 <= month <= 2:
            features.season = "winter"
        else:
            features.season = "summer"

        features.contributing_factors = factors
        return features

    def _get_historical_stats(self, origin_id: str, destination_id: str) -> Dict:
        """Compute delay statistics for an origin→destination pair."""
        matching = [
            r
            for r in self._historical_data
            if r.get("origin_id") == origin_id and r.get("destination_id") == destination_id
        ]

        if not matching:
            return {"avg_delay": 0, "delay_rate": 0, "count": 0}

        delays = [float(r.get("delay_minutes", 0)) for r in matching]
        avg_delay = sum(delays) / len(delays)
        delayed_count = sum(1 for d in delays if d > 30)
        delay_rate = delayed_count / len(delays) if delays else 0

        return {
            "avg_delay": round(avg_delay, 1),
            "delay_rate": round(delay_rate, 3),
            "count": len(matching),
        }

    def _location_has_recent_delays(self, location_id: str) -> bool:
        """Check if a location appears in recent delayed shipments."""
        for r in self._historical_data:
            delay = float(r.get("delay_minutes", 0))
            if delay > 30 and (
                r.get("origin_id") == location_id
                or r.get("destination_id") == location_id
            ):
                return True
        return False
