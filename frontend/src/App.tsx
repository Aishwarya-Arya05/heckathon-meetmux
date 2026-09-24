import { useEffect, useState, useMemo } from 'react';
import type {
  Coordinates,
  HealthResponse,
  Location,
  RouteCandidate,
  ShipmentDetail,
  ShipmentNetworkResponse,
} from './types';
import { getHealth, getShipmentNetwork, planRoutes } from './services/api';
import ShipmentSelector from './components/ShipmentSelector';
import ShipmentInfo from './components/ShipmentInfo';
import RouteList from './components/RouteList';
import RiskDetails from './components/RiskDetails';
import MapView from './components/MapView';
import NetworkLocations from './components/NetworkLocations';

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [selectedShipment, setSelectedShipment] = useState<ShipmentDetail | null>(null);
  const [network, setNetwork] = useState<ShipmentNetworkResponse | null>(null);
  const [manualOrigin, setManualOrigin] = useState<Coordinates | null>(null);
  const [manualDest, setManualDest] = useState<Coordinates | null>(null);

  const [routes, setRoutes] = useState<RouteCandidate[]>([]);
  const [selectedRouteId, setSelectedRouteId] = useState<string | undefined>(undefined);
  const [loadingRoutes, setLoadingRoutes] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    try {
      const data = await getHealth();
      setHealth(data);
    } catch {
      setHealth(null);
    }
  };

  // Load health check on mount
  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  // Handle shipment selection
  async function handleShipmentSelect(shipment: ShipmentDetail) {
    setSelectedShipment(shipment);
    setManualOrigin(null);
    setManualDest(null);
    setError(null);
    setRoutes([]);
    setSelectedRouteId(undefined);

    // Fetch network context in parallel
    getShipmentNetwork(shipment.id)
      .then((net) => setNetwork(net))
      .catch((err) => {
        console.warn('Network context unavailable:', err);
        setNetwork(null);
      });

    // Plan candidate routes
    setLoadingRoutes(true);
    try {
      const plan = await planRoutes({
        origin: shipment.origin.coordinates,
        destination: shipment.destination.coordinates,
        shipment_id: shipment.id,
      });
      setRoutes(plan.routes);
      if (plan.routes.length > 0) {
        setSelectedRouteId(plan.routes[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve route options');
    } finally {
      setLoadingRoutes(false);
    }
  }

  // Handle manual origin/destination route planning
  async function handleManualRoute(origin: Coordinates, destination: Coordinates) {
    setSelectedShipment(null);
    setNetwork(null);
    setManualOrigin(origin);
    setManualDest(destination);
    setError(null);
    setRoutes([]);
    setSelectedRouteId(undefined);

    setLoadingRoutes(true);
    try {
      const plan = await planRoutes({
        origin,
        destination,
      });
      setRoutes(plan.routes);
      if (plan.routes.length > 0) {
        setSelectedRouteId(plan.routes[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to plan route for custom coordinates');
    } finally {
      setLoadingRoutes(false);
    }
  }

  // Current active route and risk
  const selectedRoute = useMemo(
    () => routes.find((r) => r.id === selectedRouteId) || routes[0],
    [routes, selectedRouteId]
  );

  const activeOrigin = selectedShipment ? selectedShipment.origin.coordinates : manualOrigin || undefined;
  const activeDest = selectedShipment ? selectedShipment.destination.coordinates : manualDest || undefined;

  // Map locations list
  const mapLocations: Location[] = useMemo(() => {
    const locs: Location[] = [];
    if (selectedShipment) {
      locs.push(selectedShipment.origin, selectedShipment.destination);
    }
    if (network?.locations) {
      for (const loc of network.locations) {
        if (!locs.some((l) => l.id === loc.id)) {
          locs.push(loc);
        }
      }
    }
    return locs;
  }, [selectedShipment, network]);

  const isDemoData = Boolean(
    selectedShipment?.is_demo_data || routes.some((r) => r.provider === 'mock')
  );

  return (
    <div className="app-layout">
      {/* ── App Header ── */}
      <header className="app-header">
        <div className="app-header__logo">
          <div className="app-header__logo-icon">⚡</div>
          <div>
            <div className="app-header__title">MeetMux Logistics</div>
            <div className="app-header__subtitle">Delay Risk Intelligence & Route Planning</div>
          </div>
        </div>

        <div className="app-header__spacer" />

        {/* System Health Indicators */}
        <div className="app-header__status">
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px',
              borderRadius: 'var(--radius-full)',
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid var(--color-border)',
            }}
          >
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: health?.status === 'healthy' ? '#22c55e' : health ? '#f59e0b' : '#ef4444',
                boxShadow: `0 0 6px ${health?.status === 'healthy' ? '#22c55e' : '#ef4444'}`,
              }}
            />
            <span style={{ fontWeight: 500, color: 'var(--color-text-primary)' }}>
              {health ? health.status.toUpperCase() : 'OFFLINE'}
            </span>
          </div>

          {health && health.dependencies && (
            <div style={{ display: 'flex', gap: '8px', fontSize: '11px', color: 'var(--color-text-muted)' }}>
              {health.dependencies.map((dep) => (
                <span key={dep.name}>
                  {dep.name.replace('_', ' ')}:{' '}
                  <strong
                    style={{
                      color:
                        dep.status === 'healthy'
                          ? 'var(--color-risk-low)'
                          : dep.status === 'degraded'
                          ? 'var(--color-risk-medium)'
                          : 'var(--color-risk-high)',
                    }}
                  >
                    {dep.status}
                  </strong>
                </span>
              ))}
            </div>
          )}
        </div>
      </header>

      {/* ── Main Workspace ── */}
      <div className="app-main">
        {/* Left Sidebar: Controls & Details */}
        <aside className="sidebar">
          <div className="sidebar__scroll">
            {/* Shipment Selection & Filter */}
            <ShipmentSelector
              onShipmentSelect={handleShipmentSelect}
              onManualRoute={handleManualRoute}
              selectedShipmentId={selectedShipment?.id}
            />

            {/* Error Message */}
            {error && (
              <div
                style={{
                  margin: 'var(--space-md) var(--space-lg)',
                  padding: 'var(--space-sm) var(--space-md)',
                  background: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.25)',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--color-risk-high)',
                  fontSize: 'var(--text-xs)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <span>⚠️ {error}</span>
                <button
                  className="btn btn--secondary btn--sm"
                  style={{ padding: '2px 6px', fontSize: '10px' }}
                  onClick={() => setError(null)}
                >
                  Dismiss
                </button>
              </div>
            )}

            {/* Selected Shipment Details */}
            {selectedShipment && <ShipmentInfo shipment={selectedShipment} />}

            {/* Connected Supply Chain Network */}
            {network && network.locations.length > 0 && (
              <NetworkLocations
                locations={network.locations}
                links={network.links}
                isDemoData={network.is_demo_data}
              />
            )}

            {/* Candidate Route Comparison */}
            <RouteList
              routes={routes}
              selectedRouteId={selectedRouteId}
              onRouteSelect={setSelectedRouteId}
              isLoading={loadingRoutes}
              isDemoData={isDemoData}
            />

            {/* Risk Factor Breakdown for Selected Route */}
            {selectedRoute?.risk && (
              <RiskDetails
                risk={selectedRoute.risk}
                routeLabel={`Route ${routes.findIndex((r) => r.id === selectedRoute.id) + 1}`}
              />
            )}
          </div>
        </aside>

        {/* Right Area: Interactive Map & Live HUD */}
        <main className="map-container">
          {/* Quick HUD overlay over the map */}
          {selectedRoute && (
            <div
              style={{
                position: 'absolute',
                top: '16px',
                left: '60px',
                zIndex: 1000,
                background: 'rgba(17, 24, 39, 0.92)',
                backdropFilter: 'blur(10px)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                padding: '12px 18px',
                display: 'flex',
                alignItems: 'center',
                gap: '20px',
                boxShadow: 'var(--shadow-lg)',
                pointerEvents: 'auto',
              }}
            >
              <div>
                <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                  Selected Route
                </div>
                <div style={{ fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                  Route {routes.findIndex((r) => r.id === selectedRoute.id) + 1} of {routes.length}
                </div>
              </div>

              <div style={{ height: 28, width: 1, background: 'var(--color-border)' }} />

              <div>
                <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                  Distance
                </div>
                <div style={{ fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                  {selectedRoute.distance_km.toFixed(1)} km
                </div>
              </div>

              <div style={{ height: 28, width: 1, background: 'var(--color-border)' }} />

              <div>
                <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                  Est. Travel Time
                </div>
                <div style={{ fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--color-text-primary)' }}>
                  {(selectedRoute.duration_minutes / 60).toFixed(1)} hrs
                </div>
              </div>

              {selectedRoute.risk && (
                <>
                  <div style={{ height: 28, width: 1, background: 'var(--color-border)' }} />
                  <div>
                    <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                      Delay Risk
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span className={`badge badge--risk-${selectedRoute.risk.risk_band}`}>
                        {selectedRoute.risk.risk_band}
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
                        ({(selectedRoute.risk.probability * 100).toFixed(0)}%)
                      </span>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Map view component */}
          <MapView
            origin={activeOrigin}
            destination={activeDest}
            routes={routes}
            locations={mapLocations}
            selectedRouteId={selectedRouteId}
            onRouteSelect={setSelectedRouteId}
          />
        </main>
      </div>
    </div>
  );
}
