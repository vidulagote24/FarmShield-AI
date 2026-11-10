/**
 * FarmShield AI - ZoneComparison Component
 * 
 * Comparative telemetry inspection across all farm management zones.
 * Allows comparing latest verified Soil Moisture (%) or Canopy NDVI.
 * 
 * Strict Agronomic Rules:
 * - Compares zones using the identical metric type and physical unit.
 * - Displays observation timestamps so freshness disparities are transparent.
 * - Handles zones with missing or unreadable telemetry honestly.
 * - Does not rank, grade, or score zones using frontend-invented thresholds.
 */

import React, { useState } from 'react';
import { Layers, Droplets, Eye, Clock, AlertCircle, CheckCircle2, ShieldAlert } from 'lucide-react';

export default function ZoneComparison({
  zones = [],
  observations = [],
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';
  const [compareMetric, setCompareMetric] = useState('soil_moisture'); // 'soil_moisture' | 'vegetation_index'

  const isMoisture = compareMetric === 'soil_moisture';

  // Find latest observation per zone for the active metric
  const zoneComparisonData = zones.map((zone) => {
    const matchingObs = observations
      .filter(
        (o) =>
          o.zone_id === zone.id &&
          (isMoisture
            ? o.observation_type === 'soil_moisture' || o.metric_type === 'soil_moisture'
            : o.observation_type === 'vegetation_index' || o.metric_type === 'ndvi')
      )
      .sort((a, b) => new Date(b.observed_at) - new Date(a.observed_at));

    const latest = matchingObs[0] || null;

    return {
      zone,
      latestObs: latest,
      hasValidReading: latest && latest.value !== null && latest.value !== undefined,
    };
  });

  const formatTimestamp = (ts) => {
    if (!ts) return null;
    try {
      const d = new Date(ts);
      return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } catch {
      return ts;
    }
  };

  return (
    <div
      className="glass-card"
      style={{
        padding: '18px',
        marginBottom: '16px',
        background: 'rgba(7, 31, 22, 0.85)',
        border: '1px solid rgba(197, 243, 107, 0.35)',
      }}
    >
      {/* Header and Metric Toggle */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'rgba(197, 243, 107, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#C5F36B',
            }}
          >
            <Layers size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#FFFFFF', margin: 0 }}>
              {isMarathi ? 'विभाग तुलना (Cross-Zone Comparison)' : 'Cross-Zone Telemetry Comparison'}
            </h3>
            <div style={{ fontSize: '11px', color: '#B6C8BB' }}>
              {isMarathi ? 'समान निकषावर सर्व विभागांची तुलना' : 'Comparing latest verified observations on a unified scale'}
            </div>
          </div>
        </div>

        {/* Metric Switcher Pills */}
        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            onClick={() => setCompareMetric('soil_moisture')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 10px',
              borderRadius: '14px',
              fontSize: '11px',
              fontWeight: 700,
              cursor: 'pointer',
              border: isMoisture ? '1px solid #38BDF8' : '1px solid rgba(255, 255, 255, 0.16)',
              background: isMoisture ? 'rgba(56, 189, 248, 0.22)' : 'rgba(255, 255, 255, 0.05)',
              color: isMoisture ? '#38BDF8' : '#CBD5E1',
            }}
          >
            <Droplets size={12} />
            <span>{isMarathi ? 'माती ओलावा' : 'Soil Moisture'}</span>
          </button>

          <button
            onClick={() => setCompareMetric('vegetation_index')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 10px',
              borderRadius: '14px',
              fontSize: '11px',
              fontWeight: 700,
              cursor: 'pointer',
              border: !isMoisture ? '1px solid #C5F36B' : '1px solid rgba(255, 255, 255, 0.16)',
              background: !isMoisture ? 'rgba(197, 243, 107, 0.22)' : 'rgba(255, 255, 255, 0.05)',
              color: !isMoisture ? '#C5F36B' : '#CBD5E1',
            }}
          >
            <Eye size={12} />
            <span>{isMarathi ? 'NDVI इंडेक्स' : 'Canopy NDVI'}</span>
          </button>
        </div>
      </div>

      {/* Comparison Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '10px' }}>
        {zoneComparisonData.map(({ zone, latestObs, hasValidReading }) => {
          return (
            <div
              key={zone.id}
              className="glass-panel"
              style={{
                padding: '12px 14px',
                background: hasValidReading ? 'rgba(10, 43, 28, 0.70)' : 'rgba(30, 20, 20, 0.65)',
                border: hasValidReading ? '1px solid rgba(197, 243, 107, 0.25)' : '1px dashed rgba(244, 63, 94, 0.35)',
                borderRadius: '14px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span style={{ fontSize: '12px', fontWeight: 800, color: '#C5F36B' }}>
                  {zone.zone_code || 'ZONE'}
                </span>
                <span style={{ fontSize: '10px', color: '#8E9F90' }}>
                  {zone.area_hectares ? `${zone.area_hectares} ha` : ''}
                </span>
              </div>

              <div style={{ fontSize: '11.5px', fontWeight: 600, color: '#FFFFFF', marginBottom: '8px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {zone.zone_name || zone.name}
              </div>

              {/* Verified Value or Insufficient Data Alert */}
              {hasValidReading ? (
                <div>
                  <div
                    style={{
                      fontSize: '22px',
                      fontWeight: 800,
                      color: isMoisture ? '#38BDF8' : '#C5F36B',
                      marginBottom: '2px',
                    }}
                  >
                    {isMoisture 
                      ? `${latestObs.value}%` 
                      : latestObs.value.toFixed(2)}
                  </div>
                  <div style={{ fontSize: '9.5px', color: '#8E9F90', display: 'flex', alignItems: 'center', gap: '3px' }}>
                    <Clock size={10} />
                    <span>{formatTimestamp(latestObs.observed_at)}</span>
                  </div>
                  {latestObs.source && (
                    <div style={{ fontSize: '9px', color: '#64748B', marginTop: '2px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {latestObs.source}
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ padding: '6px 0' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#F87171', fontSize: '11px', fontWeight: 700 }}>
                    <AlertCircle size={13} />
                    <span>{isMarathi ? 'डेटा अपुरा' : 'No Reading'}</span>
                  </div>
                  <div style={{ fontSize: '9.5px', color: '#94A3B8', marginTop: '2px' }}>
                    {isMarathi ? 'नोंद अनुपलब्ध / ढगाळ' : 'Telemetry unavailable'}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

