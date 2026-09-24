import type { RouteCandidate } from '../types';

const ROUTE_COLORS = ['#3b82f6', '#8b5cf6', '#06b6d4'];

interface RouteListProps {
  routes: RouteCandidate[];
  selectedRouteId?: string;
  onRouteSelect: (routeId: string) => void;
  isLoading: boolean;
  isDemoData: boolean;
}

export default function RouteList({
  routes,
  selectedRouteId,
  onRouteSelect,
  isLoading,
  isDemoData,
}: RouteListProps) {
  if (isLoading) {
    return (
      <div className="sidebar__section">
        <div className="sidebar__section-title">Routes</div>
        <div className="loading-spinner">
          <div className="loading-spinner__ring" />
        </div>
      </div>
    );
  }

  if (routes.length === 0) {
    return null;
  }

  return (
    <div className="sidebar__section">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-sm)' }}>
        <div className="sidebar__section-title" style={{ margin: 0 }}>
          Routes ({routes.length})
        </div>
        {isDemoData && <span className="badge badge--demo">demo routes</span>}
      </div>

      {routes.length === 1 && (
        <div style={{
          fontSize: 'var(--text-xs)',
          color: 'var(--color-text-muted)',
          padding: 'var(--space-xs) var(--space-sm)',
          background: 'rgba(245, 158, 11, 0.08)',
          borderRadius: 'var(--radius-sm)',
          marginBottom: 'var(--space-sm)',
        }}>
          ℹ️ Only one route available for this origin–destination pair.
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
        {routes.map((route, idx) => {
          const isSelected = route.id === selectedRouteId;
          const color = ROUTE_COLORS[idx % ROUTE_COLORS.length];
          const risk = route.risk;
          const riskBadgeClass = risk
            ? `badge--risk-${risk.risk_band}`
            : '';

          return (
            <div
              key={route.id}
              className={`card card--clickable ${isSelected ? 'card--selected' : ''} animate-fade-in`}
              style={{ animationDelay: `${idx * 80}ms`, borderLeft: `3px solid ${color}` }}
              onClick={() => onRouteSelect(route.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') onRouteSelect(route.id);
              }}
              aria-label={`Route ${idx + 1}: ${route.distance_km} km, ${route.duration_minutes} minutes`}
              aria-selected={isSelected}
            >
              {/* Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontWeight: 600, fontSize: 'var(--text-sm)', color }}>
                  Route {idx + 1}
                </span>
                <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                  {risk && (
                    <span className={`badge ${riskBadgeClass}`}>
                      {risk.risk_band}
                    </span>
                  )}
                  {route.provider === 'mock' && (
                    <span className="badge badge--demo" title="Route geometry is approximate">mock</span>
                  )}
                </div>
              </div>

              {/* Metrics */}
              <div style={{ display: 'flex', gap: 'var(--space-lg)', marginBottom: '8px' }}>
                <div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Distance</div>
                  <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600 }}>
                    {route.distance_km.toFixed(1)} km
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Duration</div>
                  <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600 }}>
                    {route.duration_minutes >= 60
                      ? `${Math.floor(route.duration_minutes / 60)}h ${Math.round(route.duration_minutes % 60)}m`
                      : `${Math.round(route.duration_minutes)} min`
                    }
                  </div>
                </div>
                {risk && (
                  <div>
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Delay prob.</div>
                    <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600 }}>
                      {(risk.probability * 100).toFixed(0)}%
                    </div>
                  </div>
                )}
              </div>

              {/* Risk meter */}
              {risk && (
                <div className="risk-meter" style={{ marginBottom: '6px' }}>
                  <div
                    className={`risk-meter__fill risk-meter__fill--${risk.risk_band}`}
                    style={{ width: `${Math.max(risk.probability * 100, 4)}%` }}
                  />
                </div>
              )}

              {/* Prediction status */}
              {risk && (
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
                  {risk.prediction_status === 'model_prediction'
                    ? `✅ Model v${risk.model_version}`
                    : risk.prediction_status === 'fallback_estimate'
                    ? '⚠️ Fallback estimate (no trained model)'
                    : '❌ Prediction unavailable'
                  }
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
