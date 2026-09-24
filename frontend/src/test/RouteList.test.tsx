import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import RouteList from '../components/RouteList';
import type { RouteCandidate } from '../types';

describe('RouteList Component', () => {
  const routes: RouteCandidate[] = [
    {
      id: 'route-1',
      distance_km: 152.4,
      duration_minutes: 180,
      geometry: { type: 'LineString', coordinates: [[73.85, 18.52], [72.87, 19.07]] },
      provider: 'mock',
      risk: {
        probability: 0.18,
        risk_band: 'low',
        prediction_status: 'fallback_estimate',
        factors: [],
        message: 'Fallback',
      },
    },
    {
      id: 'route-2',
      distance_km: 180.2,
      duration_minutes: 210,
      geometry: { type: 'LineString', coordinates: [[73.85, 18.52], [72.87, 19.07]] },
      provider: 'mock',
      risk: {
        probability: 0.45,
        risk_band: 'medium',
        prediction_status: 'fallback_estimate',
        factors: [],
        message: 'Fallback',
      },
    },
  ];

  it('renders list of candidate routes with distance and duration', () => {
    render(
      <RouteList
        routes={routes}
        selectedRouteId="route-1"
        onRouteSelect={() => {}}
        isLoading={false}
        isDemoData={true}
      />
    );

    expect(screen.getByText(/Routes \(2\)/i)).toBeDefined();
    expect(screen.getByText(/152.4 km/i)).toBeDefined();
    expect(screen.getByText(/180.2 km/i)).toBeDefined();
    expect(screen.getByText(/LOW/i)).toBeDefined();
    expect(screen.getByText(/MEDIUM/i)).toBeDefined();
  });

  it('shows demo routes badge when isDemoData is true', () => {
    render(
      <RouteList
        routes={routes}
        selectedRouteId="route-1"
        onRouteSelect={() => {}}
        isLoading={false}
        isDemoData={true}
      />
    );

    expect(screen.getByText(/demo routes/i)).toBeDefined();
  });
});
