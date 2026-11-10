/**
 * FarmShield AI - FarmMapView Component
 * 
 * Interactive Leaflet GIS viewport rendering farm cadastral boundaries and
 * selectable management zones with automated bounds fitting and touch pan/zoom.
 */

import React, { useEffect, useRef } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { RotateCcw, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import FarmBoundaryLayer from './FarmBoundaryLayer.jsx';
import ZonePolygonLayer from './ZonePolygonLayer.jsx';

/**
 * Sub-component to fit map bounds to the farm geometry and handle view resets
 */
function MapBoundsController({ boundary, resetTrigger }) {
  const map = useMap();
  const initialFitDone = useRef(false);

  useEffect(() => {
    if (!boundary || !boundary.coordinates) return;

    try {
      const geoJsonLayer = L.geoJSON(boundary);
      const bounds = geoJsonLayer.getBounds();
      if (bounds.isValid()) {
        map.fitBounds(bounds, {
          padding: [25, 25],
          maxZoom: 18,
          animate: initialFitDone.current,
        });
        initialFitDone.current = true;
      }
    } catch (err) {
      console.warn('Unable to fit bounds to boundary:', err);
    }
  }, [boundary, resetTrigger, map]);

  return null;
}

export default function FarmMapView({
  farm,
  zones = [],
  selectedZoneId,
  onSelectZone,
  activeLayer = 'zones',
  resetViewTrigger = 0,
  onResetView,
  currentLang = 'mr',
  height = '360px',
}) {
  const isMarathi = currentLang === 'mr';

  // Calculate default center (defaulting to Baramati Maharashtra if no boundary)
  const defaultCenter = [18.154, 74.581];
  const defaultZoom = 15;

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height,
        borderRadius: '20px',
        overflow: 'hidden',
        border: '1.5px solid rgba(197, 243, 107, 0.35)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.40)',
      }}
    >
      <MapContainer
        center={defaultCenter}
        zoom={defaultZoom}
        scrollWheelZoom={false}
        zoomControl={false}
        attributionControl={false}
        style={{ width: '100%', height: '100%', background: '#071F16' }}
      >
        {/* Dark Field Satellite Base Tiles with Fallback */}
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />

        {/* Bound Controller */}
        <MapBoundsController boundary={farm?.boundary} resetTrigger={resetViewTrigger} />

        {/* Outer Farm Cadastral Boundary */}
        <FarmBoundaryLayer boundaryGeoJson={farm?.boundary} />

        {/* Interactive Zone Polygons */}
        <ZonePolygonLayer
          zones={zones}
          selectedZoneId={selectedZoneId}
          onSelectZone={onSelectZone}
          activeLayer={activeLayer}
          currentLang={currentLang}
        />
      </MapContainer>

      {/* Floating Map Action Controls */}
      <div
        style={{
          position: 'absolute',
          top: '12px',
          right: '12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          zIndex: 1000,
        }}
      >
        <button
          onClick={onResetView}
          title={isMarathi ? 'नकाशा पूर्ववत करा' : 'Reset view to farm bounds'}
          style={{
            width: '36px',
            height: '36px',
            borderRadius: '10px',
            background: 'rgba(7, 31, 22, 0.88)',
            border: '1px solid rgba(197, 243, 107, 0.35)',
            color: '#C5F36B',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
            backdropFilter: 'blur(10px)',
          }}
        >
          <RotateCcw size={16} />
        </button>
      </div>

      {/* Geometry Status Banner (if boundary missing) */}
      {(!farm?.boundary || !farm.boundary.coordinates) && (
        <div
          style={{
            position: 'absolute',
            bottom: '12px',
            left: '12px',
            right: '12px',
            background: 'rgba(181, 71, 62, 0.90)',
            color: '#FFFFFF',
            padding: '8px 12px',
            borderRadius: '10px',
            fontSize: '11px',
            fontWeight: 700,
            textAlign: 'center',
            zIndex: 1000,
          }}
        >
          ⚠️ {isMarathi ? 'या शेतासाठी नकाशा सीमा उपलब्ध नाही.' : 'Cadastral boundary geometry missing for this farm.'}
        </div>
      )}
    </div>
  );
}
