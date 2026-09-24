import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import RiskDetails from '../components/RiskDetails';
import type { DelayRisk } from '../types';

describe('RiskDetails Component', () => {
  it('renders model prediction status banner when status is model_prediction', () => {
    const risk: DelayRisk = {
      probability: 0.72,
      risk_band: 'high',
      prediction_status: 'model_prediction',
      model_version: '0.1.0',
      factors: [
        {
          name: 'Sensor alert',
          description: 'High vibration alert',
          impact: 'increases_risk',
        },
      ],
      message: 'Validated prediction',
    };

    render(<RiskDetails risk={risk} routeLabel="Route 1" />);

    expect(screen.getByText(/Risk Analysis — Route 1/i)).toBeDefined();
    expect(screen.getByText(/Model prediction/i)).toBeDefined();
    expect(screen.getByText(/from trained model v0.1.0/i)).toBeDefined();
    expect(screen.getByText(/72%/i)).toBeDefined();
    expect(screen.getByText(/Delay probability/i)).toBeDefined();
    expect(screen.getByText(/Sensor alert/i)).toBeDefined();
  });

  it('renders fallback estimate warning banner when status is fallback_estimate', () => {
    const risk: DelayRisk = {
      probability: 0.35,
      risk_band: 'medium',
      prediction_status: 'fallback_estimate',
      model_version: undefined,
      factors: [
        {
          name: 'Corridor distance',
          description: 'Long highway transit',
          impact: 'increases_risk',
        },
      ],
      message: 'Rule-based approximation',
    };

    render(<RiskDetails risk={risk} routeLabel="Route 2" />);

    expect(screen.getByText(/Fallback estimate/i)).toBeDefined();
    expect(screen.getByText(/Rule-based approximation/i)).toBeDefined();
    expect(screen.getByText(/35%/i)).toBeDefined();
    expect(screen.getByText(/Corridor distance/i)).toBeDefined();
  });
});
