import type { DelayRisk } from '../types';

interface RiskDetailsProps {
  risk: DelayRisk;
  routeLabel: string;
}

export default function RiskDetails({ risk, routeLabel }: RiskDetailsProps) {
  const impactIcons = {
    increases_risk: '🔺',
    decreases_risk: '🔻',
    neutral: '➖',
  };

  const impactColors = {
    increases_risk: 'var(--color-risk-high)',
    decreases_risk: 'var(--color-risk-low)',
    neutral: 'var(--color-text-muted)',
  };

  return (
    <div className="sidebar__section animate-fade-in">
      <div className="sidebar__section-title">
        Risk Analysis — {routeLabel}
      </div>

      {/* Prediction status banner */}
      <div
        style={{
          padding: 'var(--space-sm) var(--space-md)',
          borderRadius: 'var(--radius-sm)',
          marginBottom: 'var(--space-md)',
          fontSize: 'var(--text-xs)',
          lineHeight: 1.5,
          background:
            risk.prediction_status === 'model_prediction'
              ? 'rgba(34, 197, 94, 0.08)'
              : risk.prediction_status === 'fallback_estimate'
              ? 'rgba(245, 158, 11, 0.08)'
              : 'rgba(239, 68, 68, 0.08)',
          border: `1px solid ${
            risk.prediction_status === 'model_prediction'
              ? 'rgba(34, 197, 94, 0.2)'
              : risk.prediction_status === 'fallback_estimate'
              ? 'rgba(245, 158, 11, 0.2)'
              : 'rgba(239, 68, 68, 0.2)'
          }`,
          color:
            risk.prediction_status === 'model_prediction'
              ? 'var(--color-risk-low)'
              : risk.prediction_status === 'fallback_estimate'
              ? 'var(--color-risk-medium)'
              : 'var(--color-risk-high)',
        }}
      >
        {risk.prediction_status === 'model_prediction' && (
          <>✅ <strong>Model prediction</strong> — from trained model v{risk.model_version}</>
        )}
        {risk.prediction_status === 'fallback_estimate' && (
          <>⚠️ <strong>Fallback estimate</strong> — {risk.message}</>
        )}
        {risk.prediction_status === 'unavailable' && (
          <>❌ <strong>Unavailable</strong> — {risk.message || 'Prediction could not be produced'}</>
        )}
      </div>

      {/* Risk score overview */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-lg)',
          marginBottom: 'var(--space-md)',
          padding: 'var(--space-md)',
          background: 'var(--color-bg-elevated)',
          borderRadius: 'var(--radius-md)',
        }}
      >
        <div style={{ textAlign: 'center' }}>
          <div
            style={{
              fontSize: 'var(--text-2xl)',
              fontWeight: 700,
              color: `var(--color-risk-${risk.risk_band})`,
            }}
          >
            {(risk.probability * 100).toFixed(0)}%
          </div>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
            Delay probability
          </div>
        </div>
        <div style={{ flex: 1 }}>
          <div className="risk-meter" style={{ height: '10px', marginBottom: '8px' }}>
            <div
              className={`risk-meter__fill risk-meter__fill--${risk.risk_band}`}
              style={{ width: `${Math.max(risk.probability * 100, 4)}%` }}
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--color-text-muted)' }}>
            <span>Low</span>
            <span>Medium</span>
            <span>High</span>
            <span>Critical</span>
          </div>
        </div>
      </div>

      {/* Contributing factors */}
      {risk.factors.length > 0 && (
        <div>
          <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: 'var(--space-sm)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Contributing Factors
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
            {risk.factors.map((factor, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 'var(--space-sm)',
                  padding: 'var(--space-sm)',
                  background: 'var(--color-bg-input)',
                  borderRadius: 'var(--radius-sm)',
                  borderLeft: `2px solid ${impactColors[factor.impact] || 'var(--color-border)'}`,
                }}
              >
                <span style={{ fontSize: 'var(--text-sm)', flexShrink: 0 }}>
                  {impactIcons[factor.impact] || '➖'}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 'var(--text-sm)', fontWeight: 500 }}>
                    {factor.name}
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', lineHeight: 1.4 }}>
                    {factor.description}
                  </div>
                  {factor.value && (
                    <div style={{
                      fontSize: 'var(--text-xs)',
                      fontFamily: 'var(--font-mono)',
                      color: impactColors[factor.impact] || 'var(--color-text-secondary)',
                      marginTop: '2px',
                    }}>
                      {factor.value}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {risk.factors.length === 0 && (
        <div className="empty-state" style={{ padding: 'var(--space-md)' }}>
          <div className="empty-state__text">
            No specific risk factors identified for this route.
          </div>
        </div>
      )}
    </div>
  );
}
