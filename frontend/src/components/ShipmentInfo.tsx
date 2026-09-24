import type { ShipmentDetail } from '../types';

interface ShipmentInfoProps {
  shipment: ShipmentDetail;
}

const statusColors: Record<string, string> = {
  planned: 'badge--status-planned',
  in_transit: 'badge--status-in_transit',
  delivered: 'badge--status-delivered',
  delayed: 'badge--status-delayed',
  cancelled: 'badge--status-cancelled',
};

const locationIcons: Record<string, string> = {
  supplier: '🏭',
  warehouse: '🏢',
  distribution_center: '📦',
  shop: '🏪',
  port: '⚓',
};

export default function ShipmentInfo({ shipment }: ShipmentInfoProps) {
  return (
    <div className="sidebar__section animate-slide-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-sm)' }}>
        <div className="sidebar__section-title" style={{ margin: 0 }}>Shipment Details</div>
        <div style={{ display: 'flex', gap: '4px' }}>
          <span className={`badge ${statusColors[shipment.status] || ''}`}>
            {shipment.status.replace('_', ' ')}
          </span>
          {shipment.is_demo_data && <span className="badge badge--demo">demo</span>}
        </div>
      </div>

      <div
        style={{
          background: 'var(--color-bg-elevated)',
          borderRadius: 'var(--radius-md)',
          padding: 'var(--space-md)',
        }}
      >
        {/* ID */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-sm)' }}>
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>ID</span>
          <span style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', color: 'var(--color-accent)' }}>
            {shipment.id}
          </span>
        </div>

        {/* Origin */}
        <div style={{ marginBottom: 'var(--space-sm)' }}>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginBottom: '2px' }}>Origin</div>
          <div style={{ fontSize: 'var(--text-sm)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span>{locationIcons[shipment.origin.type] || '📍'}</span>
            <span style={{ fontWeight: 500 }}>{shipment.origin.name}</span>
          </div>
          {shipment.origin.address && (
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', paddingLeft: '20px' }}>
              {shipment.origin.address}
            </div>
          )}
        </div>

        {/* Arrow */}
        <div style={{ textAlign: 'center', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', margin: '4px 0' }}>
          ↓
        </div>

        {/* Destination */}
        <div style={{ marginBottom: 'var(--space-sm)' }}>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginBottom: '2px' }}>Destination</div>
          <div style={{ fontSize: 'var(--text-sm)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span>{locationIcons[shipment.destination.type] || '📍'}</span>
            <span style={{ fontWeight: 500 }}>{shipment.destination.name}</span>
          </div>
          {shipment.destination.address && (
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', paddingLeft: '20px' }}>
              {shipment.destination.address}
            </div>
          )}
        </div>

        {/* Details grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 'var(--space-sm)',
            marginTop: 'var(--space-sm)',
            paddingTop: 'var(--space-sm)',
            borderTop: '1px solid var(--color-border)',
          }}
        >
          {shipment.planned_delivery && (
            <div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Planned</div>
              <div style={{ fontSize: 'var(--text-xs)', fontWeight: 500 }}>
                {new Date(shipment.planned_delivery).toLocaleString()}
              </div>
            </div>
          )}
          {shipment.actual_delivery && (
            <div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Actual</div>
              <div style={{ fontSize: 'var(--text-xs)', fontWeight: 500 }}>
                {new Date(shipment.actual_delivery).toLocaleString()}
              </div>
            </div>
          )}
          {shipment.cargo_type && (
            <div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Cargo</div>
              <div style={{ fontSize: 'var(--text-xs)', fontWeight: 500 }}>
                {shipment.cargo_type.replace('_', ' ')}
              </div>
            </div>
          )}
          {shipment.weight_kg > 0 && (
            <div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Weight</div>
              <div style={{ fontSize: 'var(--text-xs)', fontWeight: 500 }}>
                {shipment.weight_kg.toLocaleString()} kg
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
