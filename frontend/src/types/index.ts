// ── API Response Types ──────────────────────────────────

export interface Coordinates {
  lat: number;
  lon: number;
}

export interface Location {
  id: string;
  name: string;
  type: 'supplier' | 'warehouse' | 'distribution_center' | 'shop' | 'port';
  coordinates: Coordinates;
  address?: string;
  is_demo_data: boolean;
}

export type ShipmentStatus = 'planned' | 'in_transit' | 'delivered' | 'delayed' | 'cancelled';

export interface ShipmentSummary {
  id: string;
  origin_name: string;
  destination_name: string;
  status: ShipmentStatus;
  planned_delivery?: string;
  cargo_type: string;
  is_demo_data: boolean;
}

export interface ShipmentDetail {
  id: string;
  origin: Location;
  destination: Location;
  status: ShipmentStatus;
  planned_delivery?: string;
  actual_delivery?: string;
  cargo_type: string;
  weight_kg: number;
  is_demo_data: boolean;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

export interface ShipmentListResponse {
  data: ShipmentSummary[];
  meta: PaginationMeta;
}

// ── Supply-chain network ────────────────────────────────

export interface SupplyChainLink {
  source: Location;
  target: Location;
  relationship: string;
  active: boolean;
}

export interface ShipmentNetworkResponse {
  shipment_id: string;
  locations: Location[];
  links: SupplyChainLink[];
  is_demo_data: boolean;
}

// ── Route & Risk ────────────────────────────────────────

export type PredictionStatus = 'model_prediction' | 'fallback_estimate' | 'unavailable';
export type RiskBand = 'low' | 'medium' | 'high' | 'critical';

export interface RiskFactor {
  name: string;
  description: string;
  impact: 'increases_risk' | 'decreases_risk' | 'neutral';
  value?: string;
}

export interface DelayRisk {
  probability: number;
  risk_band: RiskBand;
  prediction_status: PredictionStatus;
  model_version?: string;
  factors: RiskFactor[];
  message: string;
}

export interface RouteCandidate {
  id: string;
  distance_km: number;
  duration_minutes: number;
  geometry: GeoJSON.LineString;
  provider: string;
  risk?: DelayRisk;
}

export interface RoutePlanResponse {
  routes: RouteCandidate[];
  origin: Coordinates;
  destination: Coordinates;
  shipment_id?: string;
  is_demo_data: boolean;
}

export interface RoutePlanRequest {
  origin: Coordinates;
  destination: Coordinates;
  shipment_id?: string;
}

// ── Health ──────────────────────────────────────────────

export interface DependencyHealth {
  name: string;
  status: 'healthy' | 'degraded' | 'unavailable';
  latency_ms?: number;
  message: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  environment: string;
  dependencies: DependencyHealth[];
}

// ── UI State ────────────────────────────────────────────

export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

export interface AppError {
  message: string;
  code?: string;
  requestId?: string;
}
