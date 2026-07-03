// Tier 2 — Standard (Section 11.1): flat 2D Leaflet map, clustered pins,
// smooth CSS transitions, no WebGL requirement. Pin clustering uses the
// same Section 5.2 rule as the backend (collapse above the density
// threshold, click to expand) via the /api/map/clusters response shape;
// with the synthetic provider it falls back to plain pins.
import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { fetchMapClusters } from '../../api/client.js';

const CATEGORY_COLORS = {
  geopolitics: '#4da3ff', finance: '#ffc857', disaster: '#ff6b57',
  conflict: '#ff4d88', other: '#9aa7bd',
};

export default function Tier2Map({ events, stories, onSelectStory }) {
  const mapRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    const map = L.map(containerRef.current, {
      center: [22, 10], zoom: 2, minZoom: 2, worldCopyJump: true, zoomAnimation: true,
    });
    mapRef.current = map;

    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      className: 'tier2-tiles',
    }).addTo(map);

    const storyByEvent = new Map();
    (stories ?? []).forEach((s) => (s.member_event_ids ?? []).forEach((id) => storyByEvent.set(id, s.id)));

    const layer = L.layerGroup().addTo(map);

    const drawPin = (point) => {
      const color = CATEGORY_COLORS[point.category] ?? CATEGORY_COLORS.other;
      const [lon, lat] = point.location;
      const marker = L.circleMarker([lat, lon], {
        radius: 4 + (point.severity ?? 1) * 1.5,
        color, fillColor: color, fillOpacity: 0.55, weight: 1,
      }).addTo(layer);
      const event = (events ?? []).find((e) => e.id === point.id);
      if (event) marker.bindTooltip(`${event.title}`);
      marker.on('click', () => {
        const storyId = storyByEvent.get(point.id);
        if (storyId && onSelectStory) onSelectStory(storyId);
      });
    };

    const drawCluster = (cluster) => {
      const [lon, lat] = cluster.location;
      const marker = L.marker([lat, lon], {
        icon: L.divIcon({
          className: '',
          html: `<div class="pin-dot" style="width:30px;height:30px;background:#4da3ffcc;
                 display:flex;align-items:center;justify-content:center;
                 font:700 11px system-ui;color:#0a0e17">${cluster.count}</div>`,
          iconSize: [30, 30],
        }),
      }).addTo(layer);
      // Clicking a collapsed cluster expands it (Section 5.2).
      marker.on('click', () => map.setView([lat, lon], Math.min(map.getZoom() + 3, 10), { animate: true }));
    };

    // Prefer server-side Section 5.2 clustering; fall back to raw pins if
    // the endpoint is unavailable (e.g. synthetic/offline mode).
    fetchMapClusters()
      .then((items) => items.forEach((item) => (item.type === 'cluster' ? drawCluster(item) : drawPin(item))))
      .catch(() => {
        (events ?? []).filter((e) => Array.isArray(e.location)).forEach((e) =>
          drawPin({ id: e.id, location: e.location, category: e.category, severity: e.severity }));
      });

    return () => map.remove();
  }, [events, stories, onSelectStory]);

  return <div className="tier2-wrap"><div ref={containerRef} style={{ height: '100%' }} /></div>;
}
