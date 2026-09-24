"""
Supply-chain graph service.

Abstracts access to the supply-chain graph. In production this talks to Neo4j
via the official driver. When Neo4j is unavailable, it falls back to an
in-memory demo graph built from CSV sample data.

Design: Repository pattern — callers never import neo4j directly.
"""

from __future__ import annotations

import csv
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from app.models.schemas import (
    Coordinates,
    Location,
    LocationType,
    NetworkConnection,
    ShipmentDetail,
    ShipmentStatus,
    ShipmentSummary,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sample"


# ── Abstract interface ───────────────────────────────────────


class GraphServiceBase(ABC):
    """Interface for supply-chain graph operations."""

    @abstractmethod
    async def list_shipments(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[ShipmentSummary], int]:
        ...

    @abstractmethod
    async def get_shipment(self, shipment_id: str) -> Optional[ShipmentDetail]:
        ...

    @abstractmethod
    async def get_shipment_network(
        self, shipment_id: str
    ) -> tuple[list[Location], list[NetworkConnection]]:
        ...

    @abstractmethod
    async def get_location(self, location_id: str) -> Optional[Location]:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...


# ── Neo4j implementation ─────────────────────────────────────


class Neo4jGraphService(GraphServiceBase):
    """Production graph service backed by Neo4j."""

    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        try:
            from neo4j import AsyncGraphDatabase
            self._driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
            self._database = database
            logger.info("Neo4j driver initialized for %s", uri)
        except Exception:
            logger.exception("Failed to create Neo4j driver")
            raise

    async def close(self):
        await self._driver.close()

    async def health_check(self) -> bool:
        try:
            async with self._driver.session(database=self._database) as session:
                result = await session.run("RETURN 1 AS n")
                record = await result.single()
                return record is not None and record["n"] == 1
        except Exception:
            logger.warning("Neo4j health check failed", exc_info=True)
            return False

    async def list_shipments(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[ShipmentSummary], int]:
        skip = (page - 1) * page_size
        query = """
        MATCH (s:Shipment)-[:ORIGINATES_FROM]->(o:Location),
              (s)-[:DESTINED_FOR]->(d:Location)
        RETURN s, o.name AS origin_name, d.name AS dest_name
        ORDER BY s.id
        SKIP $skip LIMIT $limit
        """
        count_query = "MATCH (s:Shipment) RETURN count(s) AS total"

        async with self._driver.session(database=self._database) as session:
            count_result = await session.run(count_query)
            count_record = await count_result.single()
            total = count_record["total"] if count_record else 0

            result = await session.run(query, skip=skip, limit=page_size)
            records = await result.data()

        shipments = []
        for rec in records:
            s = rec["s"]
            shipments.append(
                ShipmentSummary(
                    id=s["id"],
                    status=ShipmentStatus(s.get("status", "pending")),
                    origin_name=rec["origin_name"],
                    destination_name=rec["dest_name"],
                    planned_delivery=s.get("planned_delivery"),
                    is_demo_data=s.get("is_demo", False),
                )
            )
        return shipments, total

    async def get_shipment(self, shipment_id: str) -> Optional[ShipmentDetail]:
        query = """
        MATCH (s:Shipment {id: $sid})-[:ORIGINATES_FROM]->(o:Location),
              (s)-[:DESTINED_FOR]->(d:Location)
        OPTIONAL MATCH (o)-[:SUPPLIES|SHIPS_TO|STORES_FOR*1..2]-(linked:Location)
        WHERE linked.id <> o.id AND linked.id <> d.id
        RETURN s, o, d, collect(DISTINCT linked) AS linked_locations
        """
        async with self._driver.session(database=self._database) as session:
            result = await session.run(query, sid=shipment_id)
            record = await result.single()

        if not record:
            return None

        s, o, d = record["s"], record["o"], record["d"]

        def _to_location(node) -> Location:
            return Location(
                id=node["id"],
                name=node["name"],
                type=LocationType(node.get("type", "warehouse")),
                coordinates=Coordinates(lat=node["lat"], lng=node["lng"]),
                city=node.get("city"),
                country=node.get("country"),
            )

        linked = [_to_location(n) for n in record["linked_locations"] if n.get("lat")]

        return ShipmentDetail(
            id=s["id"],
            status=ShipmentStatus(s.get("status", "pending")),
            origin=_to_location(o),
            destination=_to_location(d),
            planned_delivery=s.get("planned_delivery"),
            actual_delivery=s.get("actual_delivery"),
            cargo_type=s.get("cargo_type"),
            weight_kg=s.get("weight_kg"),
            linked_locations=linked,
            is_demo_data=s.get("is_demo", False),
        )

    async def get_shipment_network(
        self, shipment_id: str
    ) -> tuple[list[Location], list[NetworkConnection]]:
        query = """
        MATCH (s:Shipment {id: $sid})-[:ORIGINATES_FROM]->(o:Location),
              (s)-[:DESTINED_FOR]->(d:Location)
        WITH o, d
        OPTIONAL MATCH path = (o)-[r:SUPPLIES|SHIPS_TO|STORES_FOR*1..3]-(connected:Location)
        WITH o, d, collect(DISTINCT connected) AS connected_nodes,
             collect(DISTINCT r) AS rels
        RETURN o, d, connected_nodes
        """
        async with self._driver.session(database=self._database) as session:
            result = await session.run(query, sid=shipment_id)
            record = await result.single()

        if not record:
            return [], []

        def _to_location(node) -> Location:
            return Location(
                id=node["id"],
                name=node["name"],
                type=LocationType(node.get("type", "warehouse")),
                coordinates=Coordinates(lat=node["lat"], lng=node["lng"]),
                city=node.get("city"),
                country=node.get("country"),
            )

        locations = [_to_location(record["o"]), _to_location(record["d"])]
        for n in record["connected_nodes"]:
            if n and n.get("lat"):
                locations.append(_to_location(n))

        # For connections, re-query relationships
        conn_query = """
        MATCH (s:Shipment {id: $sid})-[:ORIGINATES_FROM]->(o:Location),
              (s)-[:DESTINED_FOR]->(d:Location)
        WITH collect(DISTINCT o) + collect(DISTINCT d) AS endpoints
        UNWIND endpoints AS ep
        MATCH (ep)-[r:SUPPLIES|SHIPS_TO|STORES_FOR]-(other:Location)
        RETURN DISTINCT startNode(r).id AS source_id, endNode(r).id AS target_id,
               type(r) AS relationship
        """
        async with self._driver.session(database=self._database) as session:
            result = await session.run(conn_query, sid=shipment_id)
            conn_records = await result.data()

        connections = [
            NetworkConnection(
                source_id=r["source_id"],
                target_id=r["target_id"],
                relationship=r["relationship"].lower(),
            )
            for r in conn_records
        ]

        return locations, connections

    async def get_location(self, location_id: str) -> Optional[Location]:
        query = "MATCH (l:Location {id: $lid}) RETURN l"
        async with self._driver.session(database=self._database) as session:
            result = await session.run(query, lid=location_id)
            record = await result.single()

        if not record:
            return None

        n = record["l"]
        return Location(
            id=n["id"],
            name=n["name"],
            type=LocationType(n.get("type", "warehouse")),
            coordinates=Coordinates(lat=n["lat"], lng=n["lng"]),
            city=n.get("city"),
            country=n.get("country"),
        )


# ── In-memory demo fallback ─────────────────────────────────


class DemoGraphService(GraphServiceBase):
    """
    In-memory graph service using CSV sample data.
    Used when Neo4j is not configured or unavailable.
    All data is explicitly marked as demo.
    """

    def __init__(self):
        self._locations: dict[str, Location] = {}
        self._shipments: dict[str, dict] = {}
        self._edges: list[tuple[str, str, str]] = []
        self._load_data()
        logger.info("DemoGraphService initialized with %d locations, %d shipments",
                     len(self._locations), len(self._shipments))

    def _load_data(self):
        # Load locations
        loc_file = DATA_DIR / "locations.csv"
        if loc_file.exists():
            with open(loc_file, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    self._locations[row["id"]] = Location(
                        id=row["id"],
                        name=row["name"],
                        type=LocationType(row["type"]),
                        coordinates=Coordinates(lat=float(row["lat"]), lng=float(row["lng"])),
                        city=row.get("city"),
                        country=row.get("country"),
                    )

        # Load shipments
        shp_file = DATA_DIR / "shipments.csv"
        if shp_file.exists():
            with open(shp_file, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    self._shipments[row["id"]] = row

        # Hard-coded demo edges matching seed.cypher
        self._edges = [
            ("LOC-001", "LOC-003", "supplies"),
            ("LOC-001", "LOC-005", "supplies"),
            ("LOC-002", "LOC-004", "supplies"),
            ("LOC-002", "LOC-006", "supplies"),
            ("LOC-009", "LOC-003", "supplies"),
            ("LOC-009", "LOC-004", "supplies"),
            ("LOC-011", "LOC-003", "supplies"),
            ("LOC-011", "LOC-012", "supplies"),
            ("LOC-003", "LOC-006", "ships_to"),
            ("LOC-003", "LOC-007", "ships_to"),
            ("LOC-004", "LOC-008", "ships_to"),
            ("LOC-005", "LOC-008", "ships_to"),
            ("LOC-010", "LOC-005", "stores_for"),
            ("LOC-012", "LOC-003", "ships_to"),
        ]

    async def health_check(self) -> bool:
        return True  # Always healthy — it's in-memory

    async def list_shipments(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[ShipmentSummary], int]:
        all_shipments = sorted(self._shipments.values(), key=lambda s: s["id"])
        total = len(all_shipments)
        start = (page - 1) * page_size
        end = start + page_size
        page_items = all_shipments[start:end]

        summaries = []
        for row in page_items:
            origin = self._locations.get(row["origin_id"])
            dest = self._locations.get(row["destination_id"])
            summaries.append(
                ShipmentSummary(
                    id=row["id"],
                    status=ShipmentStatus(row["status"]),
                    origin_name=origin.name if origin else row["origin_id"],
                    destination_name=dest.name if dest else row["destination_id"],
                    planned_delivery=row.get("planned_delivery"),
                    is_demo_data=True,
                )
            )
        return summaries, total

    async def get_shipment(self, shipment_id: str) -> Optional[ShipmentDetail]:
        row = self._shipments.get(shipment_id)
        if not row:
            return None

        origin = self._locations.get(row["origin_id"])
        dest = self._locations.get(row["destination_id"])
        if not origin or not dest:
            return None

        # Find linked locations (1-hop from origin or destination)
        linked_ids: set[str] = set()
        for src, tgt, _ in self._edges:
            if src == row["origin_id"] or tgt == row["origin_id"]:
                linked_ids.add(src)
                linked_ids.add(tgt)
            if src == row["destination_id"] or tgt == row["destination_id"]:
                linked_ids.add(src)
                linked_ids.add(tgt)
        linked_ids.discard(row["origin_id"])
        linked_ids.discard(row["destination_id"])

        linked = [self._locations[lid] for lid in linked_ids if lid in self._locations]

        return ShipmentDetail(
            id=row["id"],
            status=ShipmentStatus(row["status"]),
            origin=origin,
            destination=dest,
            planned_delivery=row.get("planned_delivery") or None,
            actual_delivery=row.get("actual_delivery") or None,
            cargo_type=row.get("cargo_type"),
            weight_kg=float(row["weight_kg"]) if row.get("weight_kg") else None,
            linked_locations=linked,
            is_demo_data=True,
        )

    async def get_shipment_network(
        self, shipment_id: str
    ) -> tuple[list[Location], list[NetworkConnection]]:
        row = self._shipments.get(shipment_id)
        if not row:
            return [], []

        origin_id = row["origin_id"]
        dest_id = row["destination_id"]

        # Collect relevant location IDs
        relevant_ids: set[str] = {origin_id, dest_id}
        connections: list[NetworkConnection] = []

        for src, tgt, rel in self._edges:
            if src in relevant_ids or tgt in relevant_ids:
                relevant_ids.add(src)
                relevant_ids.add(tgt)
                connections.append(
                    NetworkConnection(source_id=src, target_id=tgt, relationship=rel)
                )

        locations = [self._locations[lid] for lid in relevant_ids if lid in self._locations]
        return locations, connections

    async def get_location(self, location_id: str) -> Optional[Location]:
        return self._locations.get(location_id)


# ── Factory ──────────────────────────────────────────────────


async def create_graph_service(
    neo4j_uri: Optional[str] = None,
    neo4j_user: Optional[str] = None,
    neo4j_password: Optional[str] = None,
    neo4j_database: str = "neo4j",
) -> GraphServiceBase:
    """
    Try to connect to Neo4j. If that fails, fall back to in-memory demo.
    """
    if neo4j_uri and neo4j_user and neo4j_password and neo4j_password != "change-me":
        try:
            service = Neo4jGraphService(neo4j_uri, neo4j_user, neo4j_password, neo4j_database)
            if await service.health_check():
                logger.info("Using Neo4j graph service")
                return service
            else:
                logger.warning("Neo4j health check failed, falling back to demo graph")
                await service.close()
        except Exception:
            logger.warning("Could not connect to Neo4j, using demo graph", exc_info=True)

    logger.info("Using in-memory demo graph service")
    return DemoGraphService()
