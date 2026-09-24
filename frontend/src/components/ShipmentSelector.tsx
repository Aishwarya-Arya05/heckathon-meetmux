import { useCallback, useEffect, useState } from 'react';
import type { Coordinates, ShipmentDetail, ShipmentSummary } from '../types';
import { getShipments, getShipment } from '../services/api';

interface ShipmentSelectorProps {
  onShipmentSelect: (shipment: ShipmentDetail) => void;
  onManualRoute: (origin: Coordinates, destination: Coordinates) => void;
  selectedShipmentId?: string;
}

export default function ShipmentSelector({
  onShipmentSelect,
  onManualRoute,
  selectedShipmentId,
}: ShipmentSelectorProps) {
  const [shipments, setShipments] = useState<ShipmentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<'shipment' | 'manual'>('shipment');
  const [statusFilter, setStatusFilter] = useState('');

  // Manual mode inputs
  const [originLat, setOriginLat] = useState('');
  const [originLon, setOriginLon] = useState('');
  const [destLat, setDestLat] = useState('');
  const [destLon, setDestLon] = useState('');

  const loadShipments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getShipments(1, 20, statusFilter || undefined);
      setShipments(result.data);
    } catch (err: any) {
      setError(err.message || 'Failed to load shipments');
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadShipments();
  }, [loadShipments]);

  async function handleShipmentClick(id: string) {
    try {
      const detail = await getShipment(id);
      onShipmentSelect(detail);
    } catch (err: any) {
      setError(err.message || 'Failed to load shipment details');
    }
  }

  function handleManualSubmit(e: React.FormEvent) {
    e.preventDefault();
    const oLat = parseFloat(originLat);
    const oLon = parseFloat(originLon);
    const dLat = parseFloat(destLat);
    const dLon = parseFloat(destLon);

    if ([oLat, oLon, dLat, dLon].some(isNaN)) {
      setError('Please enter valid coordinates');
      return;
    }

    if (oLat < -90 || oLat > 90 || dLat < -90 || dLat > 90) {
      setError('Latitude must be between -90 and 90');
      return;
    }

    if (oLon < -180 || oLon > 180 || dLon < -180 || dLon > 180) {
      setError('Longitude must be between -180 and 180');
      return;
    }

    setError(null);
    onManualRoute({ lat: oLat, lon: oLon }, { lat: dLat, lon: dLon });
  }

  const statusColors: Record<string, string> = {
    planned: 'badge--status-planned',
    in_transit: 'badge--status-in_transit',
    delivered: 'badge--status-delivered',
    delayed: 'badge--status-delayed',
    cancelled: 'badge--status-cancelled',
  };

  return (
    <>
      {/* Mode Toggle */}
      <div className="sidebar__section">
        <div style={{ display: 'flex', gap: 'var(--space-xs)' }}>
          <button
            className={`btn btn--sm ${mode === 'shipment' ? 'btn--primary' : 'btn--secondary'}`}
            onClick={() => setMode('shipment')}
          >
            📦 Shipments
          </button>
          <button
            className={`btn btn--sm ${mode === 'manual' ? 'btn--primary' : 'btn--secondary'}`}
            onClick={() => setMode('manual')}
          >
            📍 Manual Route
          </button>
        </div>
      </div>

      {mode === 'shipment' ? (
        <>
          {/* Status Filter */}
          <div className="sidebar__section">
            <select
              className="select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              aria-label="Filter by status"
            >
              <option value="">All statuses</option>
              <option value="planned">Planned</option>
              <option value="in_transit">In Transit</option>
              <option value="delivered">Delivered</option>
              <option value="delayed">Delayed</option>
            </select>
          </div>

          {/* Shipment List */}
          <div className="sidebar__scroll">
            {loading && (
              <div className="loading-spinner">
                <div className="loading-spinner__ring" />
              </div>
            )}

            {error && (
              <div className="error-state">
                <div className="error-state__message">⚠️ {error}</div>
                <button className="btn btn--sm btn--secondary" onClick={loadShipments}>
                  Retry
                </button>
              </div>
            )}

            {!loading && !error && shipments.length === 0 && (
              <div className="empty-state">
                <div className="empty-state__icon">📦</div>
                <div className="empty-state__title">No shipments found</div>
                <div className="empty-state__text">
                  {statusFilter
                    ? 'Try clearing the status filter'
                    : 'No shipments available in the system'}
                </div>
              </div>
            )}

            {shipments.map((s, idx) => (
              <div
                key={s.id}
                className={`card card--clickable ${s.id === selectedShipmentId ? 'card--selected' : ''}`}
                style={{
                  margin: '0 var(--space-md) var(--space-sm)',
                  animationDelay: `${idx * 50}ms`,
                }}
                onClick={() => handleShipmentClick(s.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') handleShipmentClick(s.id);
                }}
                aria-label={`Shipment ${s.id} from ${s.origin_name} to ${s.destination_name}`}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '6px' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
                    {s.id}
                  </span>
                  <div style={{ display: 'flex', gap: '4px' }}>
                    <span className={`badge ${statusColors[s.status] || ''}`}>
                      {s.status.replace('_', ' ')}
                    </span>
                    {s.is_demo_data && <span className="badge badge--demo">demo</span>}
                  </div>
                </div>
                <div style={{ fontSize: 'var(--text-sm)', fontWeight: 500 }}>
                  {s.origin_name}
                </div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', margin: '2px 0' }}>
                  ↓
                </div>
                <div style={{ fontSize: 'var(--text-sm)', fontWeight: 500 }}>
                  {s.destination_name}
                </div>
                {s.planned_delivery && (
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginTop: '6px' }}>
                    🕐 {new Date(s.planned_delivery).toLocaleString()}
                  </div>
                )}
                {s.cargo_type && (
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
                    📦 {s.cargo_type.replace('_', ' ')}
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      ) : (
        /* Manual Route Form */
        <div className="sidebar__section">
          <form onSubmit={handleManualSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
            <div>
              <div className="sidebar__section-title" style={{ marginBottom: 'var(--space-sm)' }}>Origin</div>
              <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
                <div className="form-group" style={{ flex: 1 }}>
                  <label className="form-label" htmlFor="origin-lat">Lat</label>
                  <input
                    id="origin-lat"
                    className="input"
                    type="number"
                    step="any"
                    placeholder="e.g. 13.0827"
                    value={originLat}
                    onChange={(e) => setOriginLat(e.target.value)}
                    required
                  />
                </div>
                <div className="form-group" style={{ flex: 1 }}>
                  <label className="form-label" htmlFor="origin-lon">Lon</label>
                  <input
                    id="origin-lon"
                    className="input"
                    type="number"
                    step="any"
                    placeholder="e.g. 80.2707"
                    value={originLon}
                    onChange={(e) => setOriginLon(e.target.value)}
                    required
                  />
                </div>
              </div>
            </div>

            <div>
              <div className="sidebar__section-title" style={{ marginBottom: 'var(--space-sm)' }}>Destination</div>
              <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
                <div className="form-group" style={{ flex: 1 }}>
                  <label className="form-label" htmlFor="dest-lat">Lat</label>
                  <input
                    id="dest-lat"
                    className="input"
                    type="number"
                    step="any"
                    placeholder="e.g. 19.0760"
                    value={destLat}
                    onChange={(e) => setDestLat(e.target.value)}
                    required
                  />
                </div>
                <div className="form-group" style={{ flex: 1 }}>
                  <label className="form-label" htmlFor="dest-lon">Lon</label>
                  <input
                    id="dest-lon"
                    className="input"
                    type="number"
                    step="any"
                    placeholder="e.g. 72.8777"
                    value={destLon}
                    onChange={(e) => setDestLon(e.target.value)}
                    required
                  />
                </div>
              </div>
            </div>

            {error && (
              <div className="error-state" style={{ padding: 'var(--space-sm)' }}>
                <div className="error-state__message">{error}</div>
              </div>
            )}

            <button type="submit" className="btn btn--primary" style={{ width: '100%' }}>
              🔍 Find Routes
            </button>
          </form>
        </div>
      )}
    </>
  );
}
