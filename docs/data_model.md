# Supply Chain Data & Graph Model Specification

## 1. Domain Entities & Graph Schema

The MeetMux platform uses Neo4j to model supply-chain topology, interconnected facilities, transport corridors, and active shipments.

### Node Labels

| Label | Description | Key Properties |
|---|---|---|
| `:Location` | Base label for all physical nodes | `id`, `name`, `type`, `lat`, `lon`, `address`, `is_demo_data` |
| `:Supplier` | Upstream component/goods manufacturer | `id`, `name`, `capabilities`, `reliability_score` |
| `:Warehouse` | Regional storage & inventory hub | `id`, `name`, `capacity_sqft`, `utilization_pct` |
| `:DistributionCenter` | Last-mile cross-dock facility | `id`, `name`, `throughput_units_day` |
| `:Shop` | Retail / delivery destination point | `id`, `name`, `store_format` |
| `:Port` | Intermodal maritime/air transit point | `id`, `name`, `customs_clearance_avg_hrs` |
| `:Shipment` | Physical transport consignment | `id`, `status`, `cargo_type`, `weight_kg`, `planned_delivery`, `is_demo_data` |
| `:SensorReading` | Telemetry event record | `id`, `sensor_type`, `reading_value`, `threshold`, `timestamp`, `is_breached` |

### Relationship Types

| Relationship | Source Node | Target Node | Properties |
|---|---|---|---|
| `[:SUPPLIES]` | `:Supplier` | `:Warehouse` | `lead_time_days`, `frequency` |
| `[:SHIPS_TO]` | `:Warehouse` | `:DistributionCenter` or `:Shop` | `corridor_distance_km`, `avg_transit_hours` |
| `[:STORES]` | `:Warehouse` | `:InventoryItem` | `quantity`, `reorder_threshold` |
| `[:ORIGINATES_AT]` | `:Shipment` | `:Location` | `dispatched_at` |
| `[:DESTINED_FOR]` | `:Shipment` | `:Location` | `eta_target` |
| `[:FOLLOWS_ROUTE]` | `:Shipment` | `:Corridor` | `distance_km`, `toll_count` |
| `[:TRIGGERED_ALERT]` | `:Shipment` | `:SensorReading` | `severity`, `alert_category` |

---

## 2. Operational Persistence Architecture

### Why Neo4j vs. PostgreSQL Decision Matrix

```
                      ┌────────────────────────────────────────┐
                      │    Supply Chain Operations Ingestion   │
                      └──────────────────┬─────────────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
     ┌────────────────────────┐                     ┌────────────────────────┐
     │      Neo4j Graph       │                     │ PostgreSQL + Timescale │
     │  (Topological Network) │                     │ (High-Frequency Telemetry)│
     ├────────────────────────┤                     ├────────────────────────┤
     │ • Facilities & Nodes   │                     │ • 1-sec IoT Telemetry  │
     │ • Supply Relationships │                     │ • Temperature Logs     │
     │ • Corridor Disruptions │                     │ • GPS Breadcrumbs      │
     │ • Downstream Delays    │                     │ • Auditing & Invoices  │
     └────────────────────────┘                     └────────────────────────┘
```

- **Graph Topology in Neo4j**: Complex multi-echelon network traversals (e.g. "If Warehouse A experiences a flooding bottleneck, which downstream retail shops and active shipments will face stockouts?") require recursive joins that relational databases struggle to execute at sub-50ms latency.
- **Time-Series Telemetry in PostgreSQL/TimescaleDB (Recommended for High Scale)**: For millions of sub-minute vibration and temperature sensor pings, standard graph storage can become fragmented. The recommended production pattern stores the entity state and active disruption status in Neo4j, while raw append-only sensor telemetry streams into PostgreSQL/TimescaleDB.
- **Zero Duplicate State**: Shipment status and current link coordinates are mastered in Neo4j; sensor alerts that breach thresholds are projected into Neo4j as `:SensorReading` relationships only when actionable.

---

## 3. Neo4j Constraints & Indexes

To ensure idempotency and rapid indexed lookups:

```cypher
// Ensure unique identifiers across nodes
CREATE CONSTRAINT location_id_unique IF NOT EXISTS
FOR (l:Location) REQUIRE l.id IS UNIQUE;

CREATE CONSTRAINT shipment_id_unique IF NOT EXISTS
FOR (s:Shipment) REQUIRE s.id IS UNIQUE;

// Indexes for spatial and status queries
CREATE INDEX location_type_idx IF NOT EXISTS
FOR (l:Location) ON (l.type);

CREATE INDEX shipment_status_idx IF NOT EXISTS
FOR (s:Shipment) ON (s.status);

CREATE INDEX shipment_planned_delivery_idx IF NOT EXISTS
FOR (s:Shipment) ON (s.planned_delivery);
```

---

## 4. Production Cypher Query Patterns

### Query 1: Retrieve Shipment with Endpoints and Upstream/Downstream Facilities
```cypher
MATCH (s:Shipment {id: $shipment_id})
MATCH (s)-[:ORIGINATES_AT]->(origin:Location)
MATCH (s)-[:DESTINED_FOR]->(dest:Location)
OPTIONAL MATCH path = (origin)<-[:SUPPLIES*1..2]-(upstream:Location)
OPTIONAL MATCH path2 = (dest)-[:SHIPS_TO*1..2]->(downstream:Location)
RETURN s, origin, dest,
       collect(DISTINCT upstream) AS upstream_nodes,
       collect(DISTINCT downstream) AS downstream_nodes;
```

### Query 2: Find Network Corridors with Active Disruptions
```cypher
MATCH (s:Shipment {id: $shipment_id})-[:ORIGINATES_AT]->(o:Location)
MATCH (s)-[:DESTINED_FOR]->(d:Location)
MATCH (l:Location)
WHERE (l)-[:SUPPLIES|SHIPS_TO*1..3]-(o) OR (l)-[:SUPPLIES|SHIPS_TO*1..3]-(d)
OPTIONAL MATCH (l)<-[:TRIGGERED_ALERT]-(alert:SensorReading {is_breached: true})
RETURN l.id AS location_id, l.name AS facility_name, l.type AS facility_type,
       count(alert) AS active_alerts;
```

---

## 5. Sample Data & Seeding

The repository contains:
- `backend/data/neo4j/schema.cypher`: Constraints and schema setup.
- `backend/data/neo4j/seed.cypher`: Idempotent Cypher script populating suppliers, manufacturing plants, distribution centers, and nationwide corridors across India.
- `backend/app/seed.py`: Automated CLI script to execute the migration:
  ```bash
  python -m app.seed
  ```
All sample records are flagged with `is_demo_data = true` to guarantee clear runtime delineation from live operational records.
