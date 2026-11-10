/**
 * FarmShield AI - ZoneIrrigationSelector Component
 * 
 * Filter tabs allowing the farmer to filter recommendations and history
 * by specific management zone or view all zones across the farm.
 */

import React from 'react';
import { Layers, CheckCircle2, AlertTriangle, AlertCircle } from 'lucide-react';

export default function ZoneIrrigationSelector({
  zones = [],
  recommendations = [],
  selectedZoneId,
  onSelectZone,
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';

  // Helper to check if a zone has an urgent recommendation
  const getZonePriority = (zoneId) => {
    const rec = recommendations.find((r) => r.zone_id === zoneId);
    return rec ? rec.priority : null;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 4px' }}>
        <span style={{ fontSize: '13px', fontWeight: 800, color: '#FFFFFF', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Layers size={14} color="#38BDF8" />
          {isMarathi ? 'विभाग निवडा (Filter by Zone)' : 'Select Management Zone'}
        </span>
        <span style={{ fontSize: '11px', color: '#8E9F90' }}>
          {selectedZoneId ? (isMarathi ? '१ विभाग निवडला' : '1 Zone Focused') : (isMarathi ? 'सर्व विभाग' : 'All Zones')}
        </span>
      </div>

      <div
        style={{
          display: 'flex',
          gap: '8px',
          overflowX: 'auto',
          paddingBottom: '4px',
          scrollbarWidth: 'none',
        }}
      >
        {/* 'All Zones' Tab */}
        <button
          onClick={() => onSelectZone(null)}
          style={{
            padding: '7px 14px',
            borderRadius: '16px',
            border: selectedZoneId === null ? '1.5px solid #38BDF8' : '1px solid rgba(255, 255, 255, 0.14)',
            background: selectedZoneId === null ? 'rgba(56, 189, 248, 0.20)' : 'rgba(255, 255, 255, 0.06)',
            color: selectedZoneId === null ? '#38BDF8' : '#D5E3D9',
            fontSize: '12px',
            fontWeight: 700,
            cursor: 'pointer',
            whiteSpace: 'nowrap',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            transition: 'all 0.15s ease',
          }}
        >
          <span>{isMarathi ? 'सर्व विभाग (All)' : 'All Zones'}</span>
        </button>

        {/* Individual Zone Tabs */}
        {zones.map((zone) => {
          const isSelected = selectedZoneId === zone.id;
          const priority = getZonePriority(zone.id);
          const isUrgent = priority === 'high' || priority === 'critical';

          return (
            <button
              key={zone.id}
              onClick={() => onSelectZone(zone.id)}
              style={{
                padding: '7px 12px',
                borderRadius: '16px',
                border: isSelected
                  ? '1.5px solid #38BDF8'
                  : isUrgent
                  ? '1px solid rgba(249, 115, 22, 0.4)'
                  : '1px solid rgba(255, 255, 255, 0.14)',
                background: isSelected
                  ? 'rgba(56, 189, 248, 0.20)'
                  : 'rgba(255, 255, 255, 0.06)',
                color: isSelected ? '#38BDF8' : '#FFFFFF',
                fontSize: '12px',
                fontWeight: 700,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 0.15s ease',
              }}
            >
              {isUrgent && <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#F97316' }} />}
              <span>{zone.zone_code || zone.zone_name.split(' ')[0]}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

