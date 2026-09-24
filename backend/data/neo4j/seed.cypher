// ============================================================
// Neo4j Seed Data — DEMO ONLY
// This data is for local development and demonstration.
// It does NOT represent real supply-chain information.
// Idempotent: uses MERGE to avoid duplicates on re-run.
// ============================================================

// ── Locations (multi-label: Location + specific type) ───────

MERGE (l:Location:Supplier {id: 'LOC-001'})
SET l.name = 'TechParts Mumbai', l.type = 'supplier',
    l.lat = 19.076, l.lng = 72.8777,
    l.city = 'Mumbai', l.country = 'India', l.is_demo = true;

MERGE (l:Location:Supplier {id: 'LOC-002'})
SET l.name = 'AutoComp Pune', l.type = 'supplier',
    l.lat = 18.5204, l.lng = 73.8567,
    l.city = 'Pune', l.country = 'India', l.is_demo = true;

MERGE (l:Location:Warehouse {id: 'LOC-003'})
SET l.name = 'Central Warehouse Delhi', l.type = 'warehouse',
    l.lat = 28.7041, l.lng = 77.1025,
    l.city = 'Delhi', l.country = 'India', l.is_demo = true;

MERGE (l:Location:Warehouse {id: 'LOC-004'})
SET l.name = 'Regional Hub Bangalore', l.type = 'warehouse',
    l.lat = 12.9716, l.lng = 77.5946,
    l.city = 'Bangalore', l.country = 'India', l.is_demo = true;

MERGE (l:Location:Location {id: 'LOC-005'})
SET l.name = 'Distribution Center Chennai', l.type = 'distribution_center',
    l.lat = 13.0827, l.lng = 80.2707,
    l.city = 'Chennai', l.country = 'India', l.is_demo = true;

MERGE (l:Location:Shop {id: 'LOC-006'})
SET l.name = 'MegaMart Delhi', l.type = 'shop',
    l.lat = 28.6139, l.lng = 77.209,
    l.city = 'Delhi', l.country = 'India', l.is_demo = true;

MERGE (l:Location:Shop {id: 'LOC-007'})
SET l.name = 'QuickShop Mumbai', l.type = 'shop',
    l.lat = 19.0176, l.lng = 72.8562,
    l.city = 'Mumbai', l.country = 'India', l.is_demo = true;

MERGE (l:Location:Shop {id: 'LOC-008'})
SET l.name = 'RetailPoint Bangalore', l.type = 'shop',
    l.lat = 12.9352, l.lng = 77.6245,
    l.city = 'Bangalore', l.country = 'India', l.is_demo = true;

MERGE (l:Location:Supplier {id: 'LOC-009'})
SET l.name = 'GreenSupply Hyderabad', l.type = 'supplier',
    l.lat = 17.385, l.lng = 78.4867,
    l.city = 'Hyderabad', l.country = 'India', l.is_demo = true;

MERGE (l:Location:Warehouse {id: 'LOC-010'})
SET l.name = 'Port Warehouse Chennai', l.type = 'warehouse',
    l.lat = 13.0878, l.lng = 80.2785,
    l.city = 'Chennai', l.country = 'India', l.is_demo = true;

MERGE (l:Location:Supplier {id: 'LOC-011'})
SET l.name = 'ElectroParts Kolkata', l.type = 'supplier',
    l.lat = 22.5726, l.lng = 88.3639,
    l.city = 'Kolkata', l.country = 'India', l.is_demo = true;

MERGE (l:Location:Warehouse {id: 'LOC-012'})
SET l.name = 'NorthEast Hub Guwahati', l.type = 'warehouse',
    l.lat = 26.1445, l.lng = 91.7362,
    l.city = 'Guwahati', l.country = 'India', l.is_demo = true;

// ── Supply-chain relationships ──────────────────────────────

MATCH (a:Location {id: 'LOC-001'}), (b:Location {id: 'LOC-003'})
MERGE (a)-[:SUPPLIES {material: 'electronics'}]->(b);

MATCH (a:Location {id: 'LOC-001'}), (b:Location {id: 'LOC-005'})
MERGE (a)-[:SUPPLIES {material: 'electronics'}]->(b);

MATCH (a:Location {id: 'LOC-002'}), (b:Location {id: 'LOC-004'})
MERGE (a)-[:SUPPLIES {material: 'auto_parts'}]->(b);

MATCH (a:Location {id: 'LOC-002'}), (b:Location {id: 'LOC-006'})
MERGE (a)-[:SUPPLIES {material: 'auto_parts'}]->(b);

MATCH (a:Location {id: 'LOC-009'}), (b:Location {id: 'LOC-003'})
MERGE (a)-[:SUPPLIES {material: 'raw_materials'}]->(b);

MATCH (a:Location {id: 'LOC-009'}), (b:Location {id: 'LOC-004'})
MERGE (a)-[:SUPPLIES {material: 'raw_materials'}]->(b);

MATCH (a:Location {id: 'LOC-011'}), (b:Location {id: 'LOC-003'})
MERGE (a)-[:SUPPLIES {material: 'electronics'}]->(b);

MATCH (a:Location {id: 'LOC-011'}), (b:Location {id: 'LOC-012'})
MERGE (a)-[:SUPPLIES {material: 'electronics'}]->(b);

MATCH (a:Location {id: 'LOC-003'}), (b:Location {id: 'LOC-006'})
MERGE (a)-[:SHIPS_TO]->(b);

MATCH (a:Location {id: 'LOC-003'}), (b:Location {id: 'LOC-007'})
MERGE (a)-[:SHIPS_TO]->(b);

MATCH (a:Location {id: 'LOC-004'}), (b:Location {id: 'LOC-008'})
MERGE (a)-[:SHIPS_TO]->(b);

MATCH (a:Location {id: 'LOC-005'}), (b:Location {id: 'LOC-008'})
MERGE (a)-[:SHIPS_TO]->(b);

MATCH (a:Location {id: 'LOC-010'}), (b:Location {id: 'LOC-005'})
MERGE (a)-[:STORES_FOR]->(b);

MATCH (a:Location {id: 'LOC-012'}), (b:Location {id: 'LOC-003'})
MERGE (a)-[:SHIPS_TO]->(b);

// ── Shipments ───────────────────────────────────────────────

MATCH (o:Location {id: 'LOC-001'}), (d:Location {id: 'LOC-003'})
MERGE (s:Shipment {id: 'SHP-001'})
SET s.status = 'delivered', s.cargo_type = 'electronics', s.weight_kg = 2500,
    s.planned_delivery = datetime('2026-09-20T14:00:00'),
    s.actual_delivery = datetime('2026-09-20T16:30:00'),
    s.is_delayed = true, s.is_demo = true
MERGE (s)-[:ORIGINATES_FROM]->(o)
MERGE (s)-[:DESTINED_FOR]->(d);

MATCH (o:Location {id: 'LOC-002'}), (d:Location {id: 'LOC-006'})
MERGE (s:Shipment {id: 'SHP-002'})
SET s.status = 'in_transit', s.cargo_type = 'auto_parts', s.weight_kg = 4200,
    s.planned_delivery = datetime('2026-09-25T10:00:00'),
    s.is_delayed = false, s.is_demo = true
MERGE (s)-[:ORIGINATES_FROM]->(o)
MERGE (s)-[:DESTINED_FOR]->(d);

MATCH (o:Location {id: 'LOC-009'}), (d:Location {id: 'LOC-004'})
MERGE (s:Shipment {id: 'SHP-003'})
SET s.status = 'delivered', s.cargo_type = 'raw_materials', s.weight_kg = 8000,
    s.planned_delivery = datetime('2026-09-18T08:00:00'),
    s.actual_delivery = datetime('2026-09-18T07:45:00'),
    s.is_delayed = false, s.is_demo = true
MERGE (s)-[:ORIGINATES_FROM]->(o)
MERGE (s)-[:DESTINED_FOR]->(d);

MATCH (o:Location {id: 'LOC-011'}), (d:Location {id: 'LOC-012'})
MERGE (s:Shipment {id: 'SHP-004'})
SET s.status = 'pending', s.cargo_type = 'electronics', s.weight_kg = 1500,
    s.planned_delivery = datetime('2026-09-26T12:00:00'),
    s.is_delayed = false, s.is_demo = true
MERGE (s)-[:ORIGINATES_FROM]->(o)
MERGE (s)-[:DESTINED_FOR]->(d);

MATCH (o:Location {id: 'LOC-001'}), (d:Location {id: 'LOC-005'})
MERGE (s:Shipment {id: 'SHP-005'})
SET s.status = 'delayed', s.cargo_type = 'electronics', s.weight_kg = 3200,
    s.planned_delivery = datetime('2026-09-22T09:00:00'),
    s.is_delayed = true, s.is_demo = true
MERGE (s)-[:ORIGINATES_FROM]->(o)
MERGE (s)-[:DESTINED_FOR]->(d);

MATCH (o:Location {id: 'LOC-002'}), (d:Location {id: 'LOC-008'})
MERGE (s:Shipment {id: 'SHP-006'})
SET s.status = 'delivered', s.cargo_type = 'auto_parts', s.weight_kg = 2800,
    s.planned_delivery = datetime('2026-09-19T16:00:00'),
    s.actual_delivery = datetime('2026-09-19T15:30:00'),
    s.is_delayed = false, s.is_demo = true
MERGE (s)-[:ORIGINATES_FROM]->(o)
MERGE (s)-[:DESTINED_FOR]->(d);

MATCH (o:Location {id: 'LOC-009'}), (d:Location {id: 'LOC-003'})
MERGE (s:Shipment {id: 'SHP-007'})
SET s.status = 'in_transit', s.cargo_type = 'chemicals', s.weight_kg = 6500,
    s.planned_delivery = datetime('2026-09-25T18:00:00'),
    s.is_delayed = false, s.is_demo = true
MERGE (s)-[:ORIGINATES_FROM]->(o)
MERGE (s)-[:DESTINED_FOR]->(d);

MATCH (o:Location {id: 'LOC-001'}), (d:Location {id: 'LOC-006'})
MERGE (s:Shipment {id: 'SHP-008'})
SET s.status = 'delivered', s.cargo_type = 'electronics', s.weight_kg = 1800,
    s.planned_delivery = datetime('2026-09-15T11:00:00'),
    s.actual_delivery = datetime('2026-09-15T14:20:00'),
    s.is_delayed = true, s.is_demo = true
MERGE (s)-[:ORIGINATES_FROM]->(o)
MERGE (s)-[:DESTINED_FOR]->(d);

MATCH (o:Location {id: 'LOC-011'}), (d:Location {id: 'LOC-003'})
MERGE (s:Shipment {id: 'SHP-009'})
SET s.status = 'delivered', s.cargo_type = 'electronics', s.weight_kg = 3500,
    s.planned_delivery = datetime('2026-09-17T09:00:00'),
    s.actual_delivery = datetime('2026-09-17T09:10:00'),
    s.is_delayed = false, s.is_demo = true
MERGE (s)-[:ORIGINATES_FROM]->(o)
MERGE (s)-[:DESTINED_FOR]->(d);

MATCH (o:Location {id: 'LOC-002'}), (d:Location {id: 'LOC-004'})
MERGE (s:Shipment {id: 'SHP-010'})
SET s.status = 'pending', s.cargo_type = 'auto_parts', s.weight_kg = 5000,
    s.planned_delivery = datetime('2026-09-27T07:00:00'),
    s.is_delayed = false, s.is_demo = true
MERGE (s)-[:ORIGINATES_FROM]->(o)
MERGE (s)-[:DESTINED_FOR]->(d);
