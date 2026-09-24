import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { Location, RouteCandidate, Coordinates } from '../types';

const ROUTE_COLORS = ['#3b82f6', '#8b5cf6', '#06b6d4'];

const LOCATION_ICONS: Record<string, string> = {
  supplier: '🏭',
  warehouse: '🏢',
  distribution_center: '📦',
  shop: '🏪',
  port: '⚓',
};

interface MapViewProps {
  origin?: Coordinates;
  destination?: Coordinates;
  routes: RouteCandidate[];
  locations: Location[];
  selectedRouteId?: string;
  onRouteSelect?: (routeId: string) => void;
}

export default function MapView({
  origin,
  destination,
  routes,
  locations,
  selectedRouteId,
  onRouteSelect,
}: MapViewProps) {
  const mapRef = useRef<L.Map | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const layersRef = useRef<L.LayerGroup>(L.layerGroup());

  // Initialize map
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      center: [20.5937, 78.9629], // Center of India
      zoom: 5,
      zoomControl: true,
      attributionControl: true,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 18,
    }).addTo(map);

    layersRef.current.addTo(map);
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update markers and routes
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const layers = layersRef.current;
    layers.clearLayers();

    const bounds: L.LatLngExpression[] = [];

    // Draw routes
    routes.forEach((route, idx) => {
      if (!route.geometry?.coordinates?.length) return;

      const latlngs: L.LatLngExpression[] = route.geometry.coordinates.map(
        (coord) => [coord[1], coord[0]] as L.LatLngExpression
      );

      const isSelected = route.id === selectedRouteId;
      const color = ROUTE_COLORS[idx % ROUTE_COLORS.length];

      const polyline = L.polyline(latlngs, {
        color,
        weight: isSelected ? 5 : 3,
        opacity: isSelected ? 1 : 0.5,
        dashArray: isSelected ? undefined : '8 4',
      });

      polyline.on('click', () => onRouteSelect?.(route.id));

      const riskLabel = route.risk
        ? `${route.risk.risk_band.toUpperCase()} risk (${(route.risk.probability * 100).toFixed(0)}%)`
        : '';

      polyline.bindPopup(
        `<div class="map-popup__title">Route ${idx + 1}</div>
         <div class="map-popup__detail">${route.distance_km.toFixed(1)} km · ${route.duration_minutes.toFixed(0)} min</div>
         ${riskLabel ? `<div class="map-popup__detail">${riskLabel}</div>` : ''}
         <div class="map-popup__detail">${route.provider === 'mock' ? '⚠️ Demo route' : ''}</div>`
      );

      polyline.addTo(layers);
      bounds.push(...latlngs);
    });

    // Origin marker
    if (origin) {
      const marker = L.circleMarker([origin.lat, origin.lon], {
        radius: 10,
        fillColor: '#22c55e',
        color: '#fff',
        weight: 2,
        fillOpacity: 0.9,
      });
      marker.bindPopup('<div class="map-popup__title">📍 Origin</div>');
      marker.addTo(layers);
      bounds.push([origin.lat, origin.lon]);
    }

    // Destination marker
    if (destination) {
      const marker = L.circleMarker([destination.lat, destination.lon], {
        radius: 10,
        fillColor: '#ef4444',
        color: '#fff',
        weight: 2,
        fillOpacity: 0.9,
      });
      marker.bindPopup('<div class="map-popup__title">🏁 Destination</div>');
      marker.addTo(layers);
      bounds.push([destination.lat, destination.lon]);
    }

    // Supply-chain location markers
    locations.forEach((loc) => {
      if (
        origin && loc.coordinates.lat === origin.lat && loc.coordinates.lon === origin.lon
      ) return;
      if (
        destination && loc.coordinates.lat === destination.lat && loc.coordinates.lon === destination.lon
      ) return;

      const icon = LOCATION_ICONS[loc.type] || '📍';

      const customIcon = L.divIcon({
        html: `<div style="
          background: #1a2235;
          border: 2px solid #3b82f6;
          border-radius: 8px;
          padding: 2px 6px;
          font-size: 14px;
          white-space: nowrap;
          display: flex;
          align-items: center;
          gap: 4px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.4);
        ">${icon}<span style="font-size:10px;color:#94a3b8">${loc.name.split(' ').slice(0, 2).join(' ')}</span></div>`,
        className: '',
        iconSize: [0, 0],
        iconAnchor: [0, 0],
      });

      const marker = L.marker([loc.coordinates.lat, loc.coordinates.lon], {
        icon: customIcon,
      });

      marker.bindPopup(
        `<div class="map-popup__title">${icon} ${loc.name}</div>
         <div class="map-popup__detail">${loc.type.replace('_', ' ')} · ${loc.address || ''}</div>
         ${loc.is_demo_data ? '<div class="map-popup__detail">⚠️ Demo data</div>' : ''}`
      );

      marker.addTo(layers);
      bounds.push([loc.coordinates.lat, loc.coordinates.lon]);
    });

    // Fit bounds
    if (bounds.length > 1) {
      map.fitBounds(L.latLngBounds(bounds), { padding: [50, 50], maxZoom: 12 });
    } else if (bounds.length === 1) {
      map.setView(bounds[0] as L.LatLngExpression, 10);
    }
  }, [origin, destination, routes, locations, selectedRouteId, onRouteSelect]);

  return <div ref={containerRef} className="map-container" style={{ width: '100%', height: '100%' }} />;
}
