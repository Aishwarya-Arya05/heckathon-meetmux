// ──────────────────────────────────────────────────────────
// Neo4j Schema – Constraints & Indexes
// Run once against a fresh database.
// Idempotent: CREATE ... IF NOT EXISTS
// ──────────────────────────────────────────────────────────

// ── Uniqueness constraints ──────────────────────────────
CREATE CONSTRAINT location_id_unique IF NOT EXISTS
FOR (l:Location) REQUIRE l.id IS UNIQUE;

CREATE CONSTRAINT shipment_id_unique IF NOT EXISTS
FOR (s:Shipment) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT sensor_id_unique IF NOT EXISTS
FOR (r:SensorReading) REQUIRE r.id IS UNIQUE;

// ── Label-specific indexes for fast lookups ─────────────
CREATE INDEX location_type_idx IF NOT EXISTS
FOR (l:Location) ON (l.type);

CREATE INDEX shipment_status_idx IF NOT EXISTS
FOR (s:Shipment) ON (s.status);

CREATE INDEX shipment_origin_idx IF NOT EXISTS
FOR (s:Shipment) ON (s.origin_id);

CREATE INDEX sensor_shipment_idx IF NOT EXISTS
FOR (r:SensorReading) ON (r.shipment_id);

CREATE INDEX sensor_alert_idx IF NOT EXISTS
FOR (r:SensorReading) ON (r.alert);

// ── Composite index for time-range sensor queries ───────
CREATE INDEX sensor_time_idx IF NOT EXISTS
FOR (r:SensorReading) ON (r.shipment_id, r.timestamp);
