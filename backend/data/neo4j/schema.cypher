// ============================================================
// Neo4j Schema: Constraints and Indexes
// Run once during initial setup or migration.
// ============================================================

// ── Uniqueness constraints ──────────────────────────────────
CREATE CONSTRAINT location_id_unique IF NOT EXISTS
FOR (l:Location) REQUIRE l.id IS UNIQUE;

CREATE CONSTRAINT shipment_id_unique IF NOT EXISTS
FOR (s:Shipment) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT supplier_id_unique IF NOT EXISTS
FOR (s:Supplier) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT warehouse_id_unique IF NOT EXISTS
FOR (w:Warehouse) REQUIRE w.id IS UNIQUE;

CREATE CONSTRAINT shop_id_unique IF NOT EXISTS
FOR (s:Shop) REQUIRE s.id IS UNIQUE;

// ── Indexes for query performance ───────────────────────────
CREATE INDEX location_type_idx IF NOT EXISTS
FOR (l:Location) ON (l.type);

CREATE INDEX shipment_status_idx IF NOT EXISTS
FOR (s:Shipment) ON (s.status);

CREATE INDEX shipment_origin_idx IF NOT EXISTS
FOR (s:Shipment) ON (s.origin_id);

CREATE INDEX shipment_destination_idx IF NOT EXISTS
FOR (s:Shipment) ON (s.destination_id);
