/**
 * FarmShield AI - ZoneList Component
 * 
 * Accessible, keyboard-navigable list alternative to spatial polygon clicks.
 * Displays all zones with explicit non-color status labels, metrics, and tap-to-select.
 */

import React from 'react';
import { Layers, ChevronRight, Activity, Droplets, Clock } from 'lucide-react';
import { STATUS_CONFIG } from './MapLegend.jsx';

export default function ZoneList({
  zones = [],
  selectedZoneId,
  onSelectZone,
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';

  if (!zones || zones.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: '16px', textAlign: 'center', color: '#D5E3D9' }}>
        {isMarathi ? 'या शेतासाठी कोणतेही विभाग नोंदणीकृत नाहीत.' : 'No management zones registered for this farm.'}
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 4px' }}>
        <span style={{ fontSize: '13px', fontWeight: 800, color: '#FFFFFF', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Layers size={15} color="#C5F36B" />
          {isMarathi ? 'व्यवस्थापन विभाग यादी' : 'Management Zones List'} ({zones.length})
        </span>
        <span style={{ fontSize: '11px', color: '#A3B8A8' }}>
          {isMarathi ? 'निवडीसाठी टॅप करा' : 'Tap to focus on map'}
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {zones.map((zone) => {
          const isSelected = zone.id === selectedZoneId;
          const statusConfig = STATUS_CONFIG[zone.status] || STATUS_CONFIG.insufficient_data;
          const StatusIcon = statusConfig.icon;

          return (
            <button
              key={zone.id}
              onClick={() => onSelectZone(zone.id)}
              className="glass-card"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 14px',
                textAlign: 'left',
                cursor: 'pointer',
                borderRadius: '16px',
                border: isSelected
                  ? '2px solid #C5F36B'
                  : '1px solid rgba(255, 255, 255, 0.14)',
                background: isSelected
                  ? 'rgba(197, 243, 107, 0.15)'
                  : 'rgba(10, 43, 28, 0.65)',
                boxShadow: isSelected ? '0 0 16px rgba(197, 243, 107, 0.25)' : 'none',
                transition: 'all 0.15s ease',
              }}
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', flex: 1, minWidth: 0, marginRight: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '14px', fontWeight: 800, color: '#FFFFFF', letterSpacing: '-0.2px' }}>
                    {zone.zone_code || zone.zone_name}
                  </span>
                  {zone.area_acres && (
                    <span style={{ fontSize: '11px', color: '#B6C8BB', fontWeight: 600 }}>
                      • {zone.area_acres} {isMarathi ? 'एकर' : 'Acres'}
                    </span>
                  )}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11.5px', color: '#D5E3D9', flexWrap: 'wrap' }}>
                  {zone.ndvi_value !== null ? (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '3px', color: '#65C76A' }}>
                      <Activity size={12} />
                      NDVI: <strong>{zone.ndvi_value}</strong>
                    </span>
                  ) : (
                    <span style={{ color: '#8A97A5' }}>NDVI: —</span>
                  )}

                  {zone.soil_moisture_pct !== null ? (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '3px', color: '#38BDF8' }}>
                      <Droplets size={12} />
                      {zone.soil_moisture_pct}% {isMarathi ? 'ओलावा' : 'Moisture'}
                    </span>
                  ) : (
                    <span style={{ color: '#8A97A5' }}>{isMarathi ? 'ओलावा: माहिती अपुरी' : 'Moisture: N/A'}</span>
                  )}
                </div>
              </div>

              {/* Status Badge with Icon & Text */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
                <span
                  className="status-pill"
                  style={{
                    padding: '4px 10px',
                    fontSize: '11px',
                    fontWeight: 800,
                    color: statusConfig.color,
                    background: statusConfig.badgeBg,
                    border: `1px solid ${statusConfig.badgeBorder}60`,
                  }}
                >
                  <StatusIcon size={12} />
                  <span>{isMarathi ? statusConfig.label_mr : statusConfig.label_en}</span>
                </span>
                <ChevronRight size={16} color={isSelected ? '#C5F36B' : '#A3B8A8'} />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
