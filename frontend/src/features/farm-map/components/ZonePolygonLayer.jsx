/**
 * FarmShield AI - ZonePolygonLayer Component
 * 
 * Renders interactive management zone polygons with risk status styling,
 * dynamic layer color mapping (status, NDVI, or soil moisture), and selection highlighting.
 */

import React from 'react';
import { GeoJSON, Tooltip } from 'react-leaflet';
import { STATUS_CONFIG } from './MapLegend.jsx';

export default function ZonePolygonLayer({
  zones = [],
  selectedZoneId,
  onSelectZone,
  activeLayer = 'zones',
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';

  const getStyleForZone = (zone) => {
    const isSelected = zone.id === selectedZoneId;
    const baseConfig = STATUS_CONFIG[zone.status] || STATUS_CONFIG.insufficient_data;

    let fillColor = baseConfig.fillColor;
    let fillOpacity = isSelected ? 0.65 : 0.40;

    // Layer-specific overrides
    if (activeLayer === 'ndvi') {
      if (zone.ndvi_value === null || zone.ndvi_value === undefined) {
        fillColor = '#667085';
      } else if (zone.ndvi_value >= 0.70) {
        fillColor = '#15803D'; // Deep healthy green
      } else if (zone.ndvi_value >= 0.55) {
        fillColor = '#65A30D'; // Moderate green
      } else if (zone.ndvi_value >= 0.45) {
        fillColor = '#EAB308'; // Warning yellow
      } else {
        fillColor = '#EF4444'; // Red stress
      }
    } else if (activeLayer === 'moisture') {
      if (zone.soil_moisture_pct === null || zone.soil_moisture_pct === undefined) {
        fillColor = '#667085';
      } else if (zone.soil_moisture_pct >= 65) {
        fillColor = '#0284C7'; // Optimal blue
      } else if (zone.soil_moisture_pct >= 50) {
        fillColor = '#38BDF8'; // Moderate blue
      } else if (zone.soil_moisture_pct >= 45) {
        fillColor = '#F59E0B'; // Approaching stress amber
      } else {
        fillColor = '#DC2626'; // Below threshold critical
      }
    }

    return {
      color: isSelected ? '#FFFFFF' : baseConfig.color,
      weight: isSelected ? 3.5 : 2,
      dashArray: zone.status === 'insufficient_data' ? '4, 4' : null,
      fillColor,
      fillOpacity,
    };
  };

  return (
    <>
      {zones.map((zone) => {
        if (!zone.boundary || !zone.boundary.coordinates) return null;

        const style = getStyleForZone(zone);
        const isSelected = zone.id === selectedZoneId;
        const statusConfig = STATUS_CONFIG[zone.status] || STATUS_CONFIG.insufficient_data;

        return (
          <GeoJSON
            key={`${zone.id}-${activeLayer}-${isSelected}`}
            data={zone.boundary}
            style={style}
            eventHandlers={{
              click: () => {
                onSelectZone(zone.id);
              },
            }}
          >
            <Tooltip direction="top" offset={[0, -10]} opacity={0.95}>
              <div style={{ textAlign: 'left', minWidth: '110px', padding: '2px' }}>
                <div style={{ fontWeight: 800, fontSize: '12px', color: '#071F16' }}>
                  {zone.zone_code || zone.zone_name}
                </div>
                <div style={{ fontSize: '11px', color: statusConfig.color, fontWeight: 700 }}>
                  {isMarathi ? statusConfig.label_mr : statusConfig.label_en}
                </div>
                {zone.area_acres && (
                  <div style={{ fontSize: '10px', color: '#4B5563' }}>
                    {zone.area_acres} {isMarathi ? 'एकर' : 'Acres'}
                  </div>
                )}
                {zone.ndvi_value !== null && (
                  <div style={{ fontSize: '10px', color: '#16A34A', fontWeight: 600 }}>
                    NDVI: {zone.ndvi_value}
                  </div>
                )}
              </div>
            </Tooltip>
          </GeoJSON>
        );
      })}
    </>
  );
}
