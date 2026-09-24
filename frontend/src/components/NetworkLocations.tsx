import type { SupplyChainLink, Location } from '../types';

interface NetworkLocationsProps {
  locations: Location[];
  links: SupplyChainLink[];
  isDemoData: boolean;
  onLocationClick?: (loc: Location) => void;
}

const locationIcons: Record<string, string> = {
  supplier: '🏭',
  warehouse: '🏢',
  distribution_center: '📦',
  shop: '🏪',
  port: '⚓',
};

const locationTypeLabels: Record<string, string> = {
  supplier: 'Supplier',
  warehouse: 'Warehouse',
  distribution_center: 'Distribution Center',
  shop: 'Retail Shop',
  port: 'Port Hub',
};

export default function NetworkLocations({
  locations,
  links,
  isDemoData,
  onLocationClick,
}: NetworkLocationsProps) {
  if (!locations || locations.length === 0) {
    return null;
  }

  return (
    <div className="sidebar__section animate-slide-in">
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 'var(--space-sm)',
        }}
      >
        <div className="sidebar__section-title" style={{ margin: 0 }}>
          Connected Network ({locations.length})
        </div>
        {isDemoData && <span className="badge badge--demo">demo graph</span>}
      </div>

      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginBottom: 'var(--space-sm)' }}>
        Supply chain entities linked upstream/downstream to this shipment:
      </div>

      {/* Network nodes */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)', marginBottom: 'var(--space-md)' }}>
        {locations.map((loc) => (
          <div
            key={loc.id}
            onClick={() => onLocationClick?.(loc)}
            className="card card--clickable"
            style={{
              padding: 'var(--space-xs) var(--space-sm)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: onLocationClick ? 'pointer' : 'default',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)' }}>
              <span>{locationIcons[loc.type] || '📍'}</span>
              <div>
                <div style={{ fontSize: 'var(--text-sm)', fontWeight: 500 }}>{loc.name}</div>
                <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>
                  {locationTypeLabels[loc.type] || loc.type}
                  {loc.address ? ` · ${loc.address}` : ''}
                </div>
              </div>
            </div>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '10px',
                color: 'var(--color-text-muted)',
              }}
            >
              {loc.id}
            </span>
          </div>
        ))}
      </div>

      {/* Network relations if any */}
      {links && links.length > 0 && (
        <div>
          <div style={{ fontSize: '10px', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: 'var(--space-xs)' }}>
            Graph Relationships
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {links.map((link, idx) => (
              <div
                key={idx}
                style={{
                  fontSize: '11px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: 'rgba(255, 255, 255, 0.03)',
                  padding: '4px 8px',
                  borderRadius: 'var(--radius-sm)',
                  color: 'var(--color-text-secondary)',
                }}
              >
                <span>{locationIcons[link.source.type] || '📍'} {link.source.name}</span>
                <span style={{ color: 'var(--color-accent)', fontWeight: 600 }}>
                  —[{link.relationship}]→
                </span>
                <span>{locationIcons[link.target.type] || '📍'} {link.target.name}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
