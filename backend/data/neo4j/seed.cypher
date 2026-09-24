// ──────────────────────────────────────────────────────────
// Neo4j Seed Data – Demo / Sample records
// Idempotent: uses MERGE to avoid duplicates on re-run.
// All records are flagged is_demo: true.
// ──────────────────────────────────────────────────────────

// ── Locations ───────────────────────────────────────────

MERGE (l:Location {id: "LOC-001"})
SET l.name = "Chennai Auto Parts Supplier",
    l.type = "supplier",
    l.lat  = 13.0827, l.lon = 80.2707,
    l.address = "45 Industrial Estate, Chennai",
    l.is_demo = true;

MERGE (l:Location {id: "LOC-002"})
SET l.name = "Mumbai Central Warehouse",
    l.type = "warehouse",
    l.lat  = 19.0760, l.lon = 72.8777,
    l.address = "12 Dock Road, Mumbai",
    l.is_demo = true;

MERGE (l:Location {id: "LOC-003"})
SET l.name = "Delhi Distribution Center",
    l.type = "distribution_center",
    l.lat  = 28.7041, l.lon = 77.1025,
    l.address = "88 Logistics Park, Delhi",
    l.is_demo = true;

MERGE (l:Location {id: "LOC-004"})
SET l.name = "Bangalore Electronics Hub",
    l.type = "supplier",
    l.lat  = 12.9716, l.lon = 77.5946,
    l.address = "7 IT Corridor, Bangalore",
    l.is_demo = true;

MERGE (l:Location {id: "LOC-005"})
SET l.name = "Hyderabad Pharma Warehouse",
    l.type = "warehouse",
    l.lat  = 17.3850, l.lon = 78.4867,
    l.address = "23 Pharma City, Hyderabad",
    l.is_demo = true;

MERGE (l:Location {id: "LOC-006"})
SET l.name = "Kolkata Port Terminal",
    l.type = "port",
    l.lat  = 22.5726, l.lon = 88.3639,
    l.address = "1 Port Trust Road, Kolkata",
    l.is_demo = true;

MERGE (l:Location {id: "LOC-007"})
SET l.name = "Pune Retail Shop",
    l.type = "shop",
    l.lat  = 18.5204, l.lon = 73.8567,
    l.address = "56 MG Road, Pune",
    l.is_demo = true;

MERGE (l:Location {id: "LOC-008"})
SET l.name = "Jaipur Distribution Hub",
    l.type = "distribution_center",
    l.lat  = 26.9124, l.lon = 75.7873,
    l.address = "34 Transport Nagar, Jaipur",
    l.is_demo = true;

MERGE (l:Location {id: "LOC-009"})
SET l.name = "Ahmedabad Textile Supplier",
    l.type = "supplier",
    l.lat  = 23.0225, l.lon = 72.5714,
    l.address = "78 Textile Market, Ahmedabad",
    l.is_demo = true;

MERGE (l:Location {id: "LOC-010"})
SET l.name = "Lucknow Regional Shop",
    l.type = "shop",
    l.lat  = 26.8467, l.lon = 80.9462,
    l.address = "12 Hazratganj, Lucknow",
    l.is_demo = true;

MERGE (l:Location {id: "LOC-011"})
SET l.name = "Kochi Spice Warehouse",
    l.type = "warehouse",
    l.lat  = 9.9312, l.lon = 76.2673,
    l.address = "5 Spice Terminal, Kochi",
    l.is_demo = true;

MERGE (l:Location {id: "LOC-012"})
SET l.name = "Vizag Steel Supplier",
    l.type = "supplier",
    l.lat  = 17.6868, l.lon = 83.2185,
    l.address = "90 Steel Plant Rd, Visakhapatnam",
    l.is_demo = true;

// ── Supply-chain relationships ──────────────────────────

// Chennai supplier → Mumbai warehouse
MATCH (a:Location {id: "LOC-001"}), (b:Location {id: "LOC-002"})
MERGE (a)-[:SUPPLIES {active: true}]->(b);

// Mumbai warehouse → Delhi DC
MATCH (a:Location {id: "LOC-002"}), (b:Location {id: "LOC-003"})
MERGE (a)-[:SHIPS_TO {active: true}]->(b);

// Mumbai warehouse → Pune shop
MATCH (a:Location {id: "LOC-002"}), (b:Location {id: "LOC-007"})
MERGE (a)-[:SHIPS_TO {active: true}]->(b);

// Bangalore supplier → Delhi DC
MATCH (a:Location {id: "LOC-004"}), (b:Location {id: "LOC-003"})
MERGE (a)-[:SUPPLIES {active: true}]->(b);

// Bangalore supplier → Lucknow shop
MATCH (a:Location {id: "LOC-004"}), (b:Location {id: "LOC-010"})
MERGE (a)-[:SUPPLIES {active: true}]->(b);

// Hyderabad warehouse → Jaipur DC
MATCH (a:Location {id: "LOC-005"}), (b:Location {id: "LOC-008"})
MERGE (a)-[:SHIPS_TO {active: true}]->(b);

// Kochi warehouse → Kolkata port
MATCH (a:Location {id: "LOC-011"}), (b:Location {id: "LOC-006"})
MERGE (a)-[:SHIPS_TO {active: true}]->(b);

// Vizag supplier → Mumbai warehouse
MATCH (a:Location {id: "LOC-012"}), (b:Location {id: "LOC-002"})
MERGE (a)-[:SUPPLIES {active: true}]->(b);

// Ahmedabad supplier → Pune shop
MATCH (a:Location {id: "LOC-009"}), (b:Location {id: "LOC-007"})
MERGE (a)-[:SUPPLIES {active: true}]->(b);

// Kolkata port → Delhi DC
MATCH (a:Location {id: "LOC-006"}), (b:Location {id: "LOC-003"})
MERGE (a)-[:SHIPS_TO {active: true}]->(b);

// Delhi DC → Lucknow shop
MATCH (a:Location {id: "LOC-003"}), (b:Location {id: "LOC-010"})
MERGE (a)-[:SHIPS_TO {active: true}]->(b);

// ── Shipments ───────────────────────────────────────────

MERGE (s:Shipment {id: "SHP-001"})
SET s.origin_id = "LOC-001", s.destination_id = "LOC-002",
    s.status = "in_transit",
    s.planned_delivery = datetime("2026-09-25T14:00:00"),
    s.cargo_type = "auto_parts", s.weight_kg = 2500,
    s.is_demo = true;

MERGE (s:Shipment {id: "SHP-002"})
SET s.origin_id = "LOC-004", s.destination_id = "LOC-003",
    s.status = "planned",
    s.planned_delivery = datetime("2026-09-26T10:00:00"),
    s.cargo_type = "electronics", s.weight_kg = 800,
    s.is_demo = true;

MERGE (s:Shipment {id: "SHP-003"})
SET s.origin_id = "LOC-009", s.destination_id = "LOC-007",
    s.status = "delivered",
    s.planned_delivery = datetime("2026-09-22T16:00:00"),
    s.actual_delivery = datetime("2026-09-22T17:30:00"),
    s.cargo_type = "textiles", s.weight_kg = 1200,
    s.is_demo = true;

MERGE (s:Shipment {id: "SHP-004"})
SET s.origin_id = "LOC-001", s.destination_id = "LOC-003",
    s.status = "delayed",
    s.planned_delivery = datetime("2026-09-23T08:00:00"),
    s.cargo_type = "auto_parts", s.weight_kg = 3000,
    s.is_demo = true;

MERGE (s:Shipment {id: "SHP-005"})
SET s.origin_id = "LOC-011", s.destination_id = "LOC-006",
    s.status = "in_transit",
    s.planned_delivery = datetime("2026-09-25T20:00:00"),
    s.cargo_type = "spices", s.weight_kg = 600,
    s.is_demo = true;

MERGE (s:Shipment {id: "SHP-006"})
SET s.origin_id = "LOC-012", s.destination_id = "LOC-002",
    s.status = "planned",
    s.planned_delivery = datetime("2026-09-27T06:00:00"),
    s.cargo_type = "steel", s.weight_kg = 5000,
    s.is_demo = true;

MERGE (s:Shipment {id: "SHP-007"})
SET s.origin_id = "LOC-004", s.destination_id = "LOC-010",
    s.status = "in_transit",
    s.planned_delivery = datetime("2026-09-25T18:00:00"),
    s.cargo_type = "electronics", s.weight_kg = 450,
    s.is_demo = true;

MERGE (s:Shipment {id: "SHP-008"})
SET s.origin_id = "LOC-005", s.destination_id = "LOC-008",
    s.status = "planned",
    s.planned_delivery = datetime("2026-09-28T12:00:00"),
    s.cargo_type = "pharmaceuticals", s.weight_kg = 300,
    s.is_demo = true;

MERGE (s:Shipment {id: "SHP-009"})
SET s.origin_id = "LOC-002", s.destination_id = "LOC-007",
    s.status = "delivered",
    s.planned_delivery = datetime("2026-09-20T09:00:00"),
    s.actual_delivery = datetime("2026-09-20T08:45:00"),
    s.cargo_type = "mixed", s.weight_kg = 1800,
    s.is_demo = true;

MERGE (s:Shipment {id: "SHP-010"})
SET s.origin_id = "LOC-006", s.destination_id = "LOC-003",
    s.status = "delayed",
    s.planned_delivery = datetime("2026-09-24T11:00:00"),
    s.cargo_type = "machinery", s.weight_kg = 4200,
    s.is_demo = true;

// ── Link shipments to origin/destination locations ──────

MATCH (s:Shipment), (o:Location {id: s.origin_id}), (d:Location {id: s.destination_id})
MERGE (s)-[:ORIGINATES_AT]->(o)
MERGE (s)-[:DESTINED_FOR]->(d);

// ── Sensor readings ─────────────────────────────────────

MERGE (r:SensorReading {id: "SNS-001"})
SET r.shipment_id = "SHP-001", r.location_id = "LOC-001",
    r.timestamp = datetime("2026-09-24T08:00:00"),
    r.temperature_c = 32.5, r.humidity_pct = 65.0, r.vibration_g = 0.2,
    r.alert = false, r.alert_reason = "", r.is_demo = true;

MERGE (r:SensorReading {id: "SNS-002"})
SET r.shipment_id = "SHP-001", r.location_id = "LOC-001",
    r.timestamp = datetime("2026-09-24T12:00:00"),
    r.temperature_c = 38.1, r.humidity_pct = 72.0, r.vibration_g = 0.8,
    r.alert = true, r.alert_reason = "temperature_high", r.is_demo = true;

MERGE (r:SensorReading {id: "SNS-003"})
SET r.shipment_id = "SHP-001", r.location_id = "LOC-002",
    r.timestamp = datetime("2026-09-24T16:00:00"),
    r.temperature_c = 29.0, r.humidity_pct = 58.0, r.vibration_g = 0.3,
    r.alert = false, r.alert_reason = "", r.is_demo = true;

MERGE (r:SensorReading {id: "SNS-004"})
SET r.shipment_id = "SHP-004", r.location_id = "LOC-001",
    r.timestamp = datetime("2026-09-22T06:00:00"),
    r.temperature_c = 31.0, r.humidity_pct = 60.0, r.vibration_g = 1.5,
    r.alert = true, r.alert_reason = "vibration_high", r.is_demo = true;

MERGE (r:SensorReading {id: "SNS-009"})
SET r.shipment_id = "SHP-010", r.location_id = "LOC-006",
    r.timestamp = datetime("2026-09-23T07:00:00"),
    r.temperature_c = 30.0, r.humidity_pct = 70.0, r.vibration_g = 2.1,
    r.alert = true, r.alert_reason = "vibration_high", r.is_demo = true;

MERGE (r:SensorReading {id: "SNS-010"})
SET r.shipment_id = "SHP-010", r.location_id = "LOC-006",
    r.timestamp = datetime("2026-09-23T15:00:00"),
    r.temperature_c = 35.0, r.humidity_pct = 68.0, r.vibration_g = 0.5,
    r.alert = true, r.alert_reason = "temperature_high", r.is_demo = true;

// ── Link sensors to shipments ───────────────────────────

MATCH (r:SensorReading), (s:Shipment {id: r.shipment_id})
MERGE (r)-[:READING_FOR]->(s);

MATCH (r:SensorReading), (l:Location {id: r.location_id})
MERGE (r)-[:RECORDED_AT]->(l);
