/**
 * FarmShield AI - FarmBoundaryLayer Component
 * 
 * Renders the farm's outer cadastral / PostGIS boundary polygon on the Leaflet map.
 */

import React from 'react';
import { GeoJSON } from 'react-leaflet';

export default function FarmBoundaryLayer({ boundaryGeoJson }) {
  if (!boundaryGeoJson || !boundaryGeoJson.coordinates) {
    return null;
  }

  const boundaryStyle = {
    color: '#C5F36B',
    weight: 3,
    dashArray: '6, 6',
    fillColor: '#C5F36B',
    fillOpacity: 0.08,
  };

  return (
    <GeoJSON
      key={JSON.stringify(boundaryGeoJson)}
      data={boundaryGeoJson}
      style={boundaryStyle}
    />
  );
}
