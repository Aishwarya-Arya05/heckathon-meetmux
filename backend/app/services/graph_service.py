"""
Supply-chain graph service – abstracts Neo4j behind a repository interface.

When Neo4j is unavailable, falls back to in-memory demo data loaded from CSV.
"""

from __future__ import annotations

import csv
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.models.domain import (
    Coordinates,
    Location,
    LocationType,
    SensorReading,
    Shipment,
    ShipmentStatus,
    SupplyChainLink,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sample"


# ── Abstract interface ───────────────────────────────────


class GraphServiceBase(ABC):
    """Interface for supply-chain graph queries."""

    @abstractmethod
    async def get_shipments(
        self, page: int = 1, page_size: int = 20, status: Optional[str] = None
    ) -> Tuple[List[Shipment], int]:
        """Return paginated shipments and total count."""

    @abstractmethod
    async def get_shipment(self, shipment_id: str) -> Optional[Shipment]:
        """Return a single shipment by ID."""

    @abstractmethod
    async def get_shipment_network(
        self, shipment_id: str
    ) -> Tuple[List[Location], List[SupplyChainLink]]:
        """Return connected locations and links for a shipment."""

    @abstractmethod
    async def get_location(self, location_id: str) -> Optional[Location]:
        """Return a location by ID."""

    @abstractmethod
    async def get_sensor_readings(self, shipment_id: str) -> List[SensorReading]:
        """Return sensor readings for a shipment."""

    @abstractmethod
    async def health_check(self) -> Tuple[bool, str]:
        """Return (is_healthy, message)."""


# ── Neo4j implementation ────────────────────────────────


class Neo4jGraphService(GraphServiceBase):
    """Production implementation using the official Neo4j driver."""

    def __init__(self, driver, database: str = "neo4j"):
        self._driver = driver
        self._database = database

    async def get_shipments(
        self, page: int = 1, page_size: int = 20, status: Optional[str] = None
    ) -> Tuple[List[Shipment], int]:
        query = """
        MATCH (s:Shipment)
        {where_clause}
        WITH count(s) AS total
        MATCH (s:Shipment)
        {where_clause}
        MATCH (o:Location {{id: s.origin_id}}), (d:Location {{id: s.destination_id}})
        RETURN s, o, d, total
        ORDER BY s.planned_delivery DESC
        SKIP $skip LIMIT $limit
        """
        where = "WHERE s.status = $status" if status else ""
        query = query.replace("{where_clause}", where)

        skip = (page - 1) * page_size
        params = {"skip": skip, "limit": page_size}
        if status:
            params["status"] = status

        records = await self._run_query(query, params)
        if not records:
            return [], 0

        total = records[0]["total"]
        shipments = [self._record_to_shipment(r) for r in records]
        return shipments, total

    async def get_shipment(self, shipment_id: str) -> Optional[Shipment]:
        query = """
        MATCH (s:Shipment {id: $id})
        MATCH (o:Location {id: s.origin_id}), (d:Location {id: s.destination_id})
        RETURN s, o, d
        """
        records = await self._run_query(query, {"id": shipment_id})
        if not records:
            return None
        return self._record_to_shipment(records[0])

    async def get_shipment_network(
        self, shipment_id: str
    ) -> Tuple[List[Location], List[SupplyChainLink]]:
        query = """
        MATCH (s:Shipment {id: $id})
        MATCH (o:Location {id: s.origin_id}), (d:Location {id: s.destination_id})
        OPTIONAL MATCH (o)-[r1]-(connected1:Location)
        OPTIONAL MATCH (d)-[r2]-(connected2:Location)
        WITH o, d,
             collect(DISTINCT connected1) + collect(DISTINCT connected2) AS connected,
             collect(DISTINCT {src: o, tgt: connected1, rel: type(r1)}) +
             collect(DISTINCT {src: d, tgt: connected2, rel: type(r2)}) AS rels
        RETURN o, d, connected, rels
        """
        records = await self._run_query(query, {"id": shipment_id})
        if not records:
            return [], []

        r = records[0]
        locations: Dict[str, Location] = {}

        for loc_node in [r["o"], r["d"]] + (r["connected"] or []):
            if loc_node and loc_node.get("id"):
                loc = self._node_to_location(loc_node)
                locations[loc.id] = loc

        links: List[SupplyChainLink] = []
        for rel_dict in r.get("rels") or []:
            if rel_dict.get("src") and rel_dict.get("tgt") and rel_dict.get("rel"):
                src = self._node_to_location(rel_dict["src"])
                tgt = self._node_to_location(rel_dict["tgt"])
                links.append(
                    SupplyChainLink(
                        source=locations.get(src.id, src),
                        target=locations.get(tgt.id, tgt),
                        relationship=rel_dict["rel"].lower(),
                    )
                )

        return list(locations.values()), links

    async def get_location(self, location_id: str) -> Optional[Location]:
        query = "MATCH (l:Location {id: $id}) RETURN l"
        records = await self._run_query(query, {"id": location_id})
        if not records:
            return None
        return self._node_to_location(records[0]["l"])

    async def get_sensor_readings(self, shipment_id: str) -> List[SensorReading]:
        query = """
        MATCH (r:SensorReading {shipment_id: $id})
        RETURN r ORDER BY r.timestamp
        """
        records = await self._run_query(query, {"id": shipment_id})
        return [self._node_to_sensor(r["r"]) for r in records]

    async def health_check(self) -> Tuple[bool, str]:
        try:
            records = await self._run_query("RETURN 1 AS ok", {})
            if records and records[0]["ok"] == 1:
                return True, "connected"
            return False, "unexpected response"
        except Exception as exc:
            return False, str(exc)

    async def _run_query(self, query: str, params: dict) -> list:
        """Execute a Cypher query and return list of record dicts."""
        try:
            async with self._driver.session(database=self._database) as session:
                result = await session.run(query, params)
                return [dict(record) async for record in result]
        except Exception as exc:
            logger.error("Neo4j query failed: %s", exc, exc_info=True)
            raise

    @staticmethod
    def _node_to_location(node) -> Location:
        props = dict(node) if hasattr(node, "items") else node
        return Location(
            id=props["id"],
            name=props.get("name", ""),
            type=LocationType(props.get("type", "warehouse")),
            coordinates=Coordinates(
                lat=float(props.get("lat", 0)),
                lon=float(props.get("lon", 0)),
            ),
            address=props.get("address"),
            is_demo_data=props.get("is_demo", False),
        )

    @staticmethod
    def _record_to_shipment(record) -> Shipment:
        s = dict(record["s"]) if hasattr(record["s"], "items") else record["s"]
        o_loc = Neo4jGraphService._node_to_location(record["o"])
        d_loc = Neo4jGraphService._node_to_location(record["d"])

        planned = s.get("planned_delivery")
        actual = s.get("actual_delivery")

        return Shipment(
            id=s["id"],
            origin=o_loc,
            destination=d_loc,
            status=ShipmentStatus(s.get("status", "planned")),
            planned_delivery=planned if isinstance(planned, datetime) else None,
            actual_delivery=actual if isinstance(actual, datetime) else None,
            cargo_type=s.get("cargo_type", ""),
            weight_kg=float(s.get("weight_kg", 0)),
            is_demo_data=s.get("is_demo", False),
        )

    @staticmethod
    def _node_to_sensor(node) -> SensorReading:
        props = dict(node) if hasattr(node, "items") else node
        ts = props.get("timestamp")
        return SensorReading(
            id=props["id"],
            shipment_id=props.get("shipment_id", ""),
            location_id=props.get("location_id", ""),
            timestamp=ts if isinstance(ts, datetime) else datetime.fromisoformat(str(ts)),
            temperature_c=props.get("temperature_c"),
            humidity_pct=props.get("humidity_pct"),
            vibration_g=props.get("vibration_g"),
            alert=bool(props.get("alert", False)),
            alert_reason=props.get("alert_reason", ""),
            is_demo_data=props.get("is_demo", False),
        )


# ── In-memory fallback (demo mode) ──────────────────────


class InMemoryGraphService(GraphServiceBase):
    """Fallback service that loads demo data from CSV files.

    Used when Neo4j is not available – all data is labelled as demo.
    """

    def __init__(self):
        self._locations: Dict[str, Location] = {}
        self._shipments: Dict[str, Shipment] = {}
        self._sensors: List[SensorReading] = []
        self._links: List[SupplyChainLink] = []
        self._load_data()

    def _load_data(self):
        # Locations
        loc_path = DATA_DIR / "locations.csv"
        if loc_path.exists():
            with open(loc_path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    loc = Location(
                        id=row["id"],
                        name=row["name"],
                        type=LocationType(row["type"]),
                        coordinates=Coordinates(
                            lat=float(row["lat"]), lon=float(row["lon"])
                        ),
                        address=row.get("address", ""),
                        is_demo_data=True,
                    )
                    self._locations[loc.id] = loc

        # Shipments
        shp_path = DATA_DIR / "shipments.csv"
        if shp_path.exists():
            with open(shp_path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    origin = self._locations.get(row["origin_id"])
                    dest = self._locations.get(row["destination_id"])
                    if not origin or not dest:
                        continue

                    planned = None
                    if row.get("planned_delivery"):
                        try:
                            planned = datetime.fromisoformat(row["planned_delivery"])
                        except ValueError:
                            pass

                    actual = None
                    if row.get("actual_delivery"):
                        try:
                            actual = datetime.fromisoformat(row["actual_delivery"])
                        except ValueError:
                            pass

                    shp = Shipment(
                        id=row["id"],
                        origin=origin,
                        destination=dest,
                        status=ShipmentStatus(row["status"]),
                        planned_delivery=planned,
                        actual_delivery=actual,
                        cargo_type=row.get("cargo_type", ""),
                        weight_kg=float(row.get("weight_kg", 0)),
                        is_demo_data=True,
                    )
                    self._shipments[shp.id] = shp

        # Sensors
        sns_path = DATA_DIR / "sensors.csv"
        if sns_path.exists():
            with open(sns_path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    try:
                        ts = datetime.fromisoformat(row["timestamp"])
                    except ValueError:
                        continue
                    reading = SensorReading(
                        id=row["id"],
                        shipment_id=row["shipment_id"],
                        location_id=row["location_id"],
                        timestamp=ts,
                        temperature_c=float(row["temperature_c"]) if row.get("temperature_c") else None,
                        humidity_pct=float(row["humidity_pct"]) if row.get("humidity_pct") else None,
                        vibration_g=float(row["vibration_g"]) if row.get("vibration_g") else None,
                        alert=row.get("alert", "").lower() == "true",
                        alert_reason=row.get("alert_reason", ""),
                        is_demo_data=True,
                    )
                    self._sensors.append(reading)

        # Build supply-chain links from shipment origin/destination
        self._build_links()

        logger.info(
            "InMemoryGraphService loaded: %d locations, %d shipments, %d sensors",
            len(self._locations),
            len(self._shipments),
            len(self._sensors),
        )

    def _build_links(self):
        """Create demo supply-chain relationships."""
        link_defs = [
            ("LOC-001", "LOC-002", "supplies"),
            ("LOC-002", "LOC-003", "ships_to"),
            ("LOC-002", "LOC-007", "ships_to"),
            ("LOC-004", "LOC-003", "supplies"),
            ("LOC-004", "LOC-010", "supplies"),
            ("LOC-005", "LOC-008", "ships_to"),
            ("LOC-011", "LOC-006", "ships_to"),
            ("LOC-012", "LOC-002", "supplies"),
            ("LOC-009", "LOC-007", "supplies"),
            ("LOC-006", "LOC-003", "ships_to"),
            ("LOC-003", "LOC-010", "ships_to"),
        ]
        for src_id, tgt_id, rel in link_defs:
            src = self._locations.get(src_id)
            tgt = self._locations.get(tgt_id)
            if src and tgt:
                self._links.append(
                    SupplyChainLink(source=src, target=tgt, relationship=rel)
                )

    async def get_shipments(
        self, page: int = 1, page_size: int = 20, status: Optional[str] = None
    ) -> Tuple[List[Shipment], int]:
        items = list(self._shipments.values())
        if status:
            items = [s for s in items if s.status.value == status]
        total = len(items)
        start = (page - 1) * page_size
        return items[start : start + page_size], total

    async def get_shipment(self, shipment_id: str) -> Optional[Shipment]:
        return self._shipments.get(shipment_id)

    async def get_shipment_network(
        self, shipment_id: str
    ) -> Tuple[List[Location], List[SupplyChainLink]]:
        shipment = self._shipments.get(shipment_id)
        if not shipment:
            return [], []

        # Find connected locations (1-hop from origin and destination)
        relevant_locs: Dict[str, Location] = {
            shipment.origin.id: shipment.origin,
            shipment.destination.id: shipment.destination,
        }
        relevant_links: List[SupplyChainLink] = []

        for link in self._links:
            if link.source.id in relevant_locs or link.target.id in relevant_locs:
                relevant_locs[link.source.id] = link.source
                relevant_locs[link.target.id] = link.target
                relevant_links.append(link)

        return list(relevant_locs.values()), relevant_links

    async def get_location(self, location_id: str) -> Optional[Location]:
        return self._locations.get(location_id)

    async def get_sensor_readings(self, shipment_id: str) -> List[SensorReading]:
        return [s for s in self._sensors if s.shipment_id == shipment_id]

    async def health_check(self) -> Tuple[bool, str]:
        return True, "in-memory demo mode"
