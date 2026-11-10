/**
 * FarmShield AI - FarmMetricCards Component
 * 
 * High-level telemetry stat cards summarizing farm observations:
 * - Active Zones Monitored
 * - Total Observation Telemetry Points (with partial data status from Task 10.1)
 * - Verified Soil Moisture Range
 * - Verified Canopy NDVI Range
 * 
 * Strict Agronomic Integrity:
 * - Does not invent metrics or display missing values as zero.
 * - Accurately preserves observation units and ranges.
 * - Excludes failed sensor quality flags (cloud_obscured, probe_disconnected) from numerical ranges.
 */

import React from 'react';
import { Layers, Activity, Droplets, Eye, AlertTriangle } from 'lucide-react';

export default function FarmMetricCards({
  zones = [],
  totalObservations = 0,
  totalMatchingRecords = 0,
  isPartialData = false,
  soilMoistureObs = [],
  vegetationObs = [],
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';

  // Helper to filter out failed sensor readings
  const isValidNumeric = (o) => {
    if (o.value === null || o.value === undefined || typeof o.value !== 'number' || isNaN(o.value)) {
      return false;
    }
    const meta = o.metadata || o.metadata_json || {};
    const quality = meta.quality || meta.quality_status;
    return !['cloud_obscured', 'probe_disconnected', 'error', 'failed', 'invalid'].includes(quality);
  };

  // Compute soil moisture range across valid observations
  const validSmValues = soilMoistureObs
    .filter(isValidNumeric)
    .map((o) => o.value);

  const smMin = validSmValues.length > 0 ? Math.min(...validSmValues) : null;
  const smMax = validSmValues.length > 0 ? Math.max(...validSmValues) : null;

  // Compute vegetation index (NDVI) range
  const validNdviValues = vegetationObs
    .filter(isValidNumeric)
    .map((o) => o.value);

  const ndviMin = validNdviValues.length > 0 ? Math.min(...validNdviValues) : null;
  const ndviMax = validNdviValues.length > 0 ? Math.max(...validNdviValues) : null;

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(135px, 1fr))',
        gap: '10px',
        marginBottom: '16px',
      }}
    >
      {/* Card 1: Monitored Zones */}
      <div
        className="glass-card"
        style={{
          padding: '14px',
          background: 'rgba(7, 31, 22, 0.85)',
          border: '1px solid rgba(197, 243, 107, 0.25)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#C5F36B', fontSize: '11px', fontWeight: 700, marginBottom: '4px' }}>
          <Layers size={13} />
          <span>{isMarathi ? 'विभाग (Zones)' : 'Monitored Zones'}</span>
        </div>
        <div style={{ fontSize: '20px', fontWeight: 800, color: '#FFFFFF' }}>
          {zones.length}
        </div>
        <div style={{ fontSize: '10px', color: '#8E9F90', marginTop: '2px' }}>
          {isMarathi ? 'सक्रिय व्यवस्थापन विभाग' : 'Active farm parcels'}
        </div>
      </div>

      {/* Card 2: Total Observations & Pagination Status */}
      <div
        className="glass-card"
        style={{
          padding: '14px',
          background: 'rgba(7, 31, 22, 0.85)',
          border: isPartialData 
            ? '1.5px solid rgba(245, 158, 11, 0.45)' 
            : '1px solid rgba(56, 189, 248, 0.25)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: isPartialData ? '#F59E0B' : '#38BDF8', fontSize: '11px', fontWeight: 700 }}>
            <Activity size={13} />
            <span>{isMarathi ? 'एकूण नोंदी (Data Points)' : 'Total Data Points'}</span>
          </div>
          {isPartialData && (
            <span title={isMarathi ? 'अपूर्ण डेटा संच' : 'Partial dataset'}>
              <AlertTriangle size={12} color="#F59E0B" />
            </span>
          )}
        </div>
        <div style={{ fontSize: '20px', fontWeight: 800, color: '#FFFFFF' }}>
          {isPartialData && totalMatchingRecords > totalObservations
            ? `${totalObservations} / ${totalMatchingRecords}`
            : totalObservations}
        </div>
        <div style={{ fontSize: '10px', color: isPartialData ? '#FCD34D' : '#8E9F90', marginTop: '2px' }}>
          {isPartialData 
            ? (isMarathi ? 'मर्यादित डेटा संच' : 'Partial dataset loaded') 
            : (isMarathi ? 'नोंदवलेली टेलिमेट्री' : 'Verified observations')}
        </div>
      </div>

      {/* Card 3: Soil Moisture Range */}
      <div
        className="glass-card"
        style={{
          padding: '14px',
          background: 'rgba(7, 31, 22, 0.85)',
          border: '1px solid rgba(56, 189, 248, 0.35)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#38BDF8', fontSize: '11px', fontWeight: 700, marginBottom: '4px' }}>
          <Droplets size={13} />
          <span>{isMarathi ? 'माती ओलावा कक्षा' : 'Moisture Range'}</span>
        </div>
        <div style={{ fontSize: '18px', fontWeight: 800, color: smMin !== null ? '#38BDF8' : '#94A3B8' }}>
          {smMin !== null ? (smMin === smMax ? `${smMin}%` : `${smMin}% – ${smMax}%`) : '—'}
        </div>
        <div style={{ fontSize: '10px', color: '#8E9F90', marginTop: '2px' }}>
          {validSmValues.length > 0 
            ? `${validSmValues.length} ${isMarathi ? 'सेन्सर नोंदी' : 'readings recorded'}` 
            : (isMarathi ? 'नोंदी उपलब्ध नाहीत' : 'No valid readings')}
        </div>
      </div>

      {/* Card 4: NDVI Range */}
      <div
        className="glass-card"
        style={{
          padding: '14px',
          background: 'rgba(7, 31, 22, 0.85)',
          border: '1px solid rgba(197, 243, 107, 0.35)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#C5F36B', fontSize: '11px', fontWeight: 700, marginBottom: '4px' }}>
          <Eye size={13} />
          <span>{isMarathi ? 'कॅनॉपी NDVI कक्षा' : 'Canopy NDVI Range'}</span>
        </div>
        <div style={{ fontSize: '18px', fontWeight: 800, color: ndviMin !== null ? '#C5F36B' : '#94A3B8' }}>
          {ndviMin !== null ? (ndviMin === ndviMax ? ndviMin.toFixed(2) : `${ndviMin.toFixed(2)} – ${ndviMax.toFixed(2)}`) : '—'}
        </div>
        <div style={{ fontSize: '10px', color: '#8E9F90', marginTop: '2px' }}>
          {validNdviValues.length > 0 
            ? `${validNdviValues.length} ${isMarathi ? 'उपग्रह नोंदी' : 'satellite scenes'}` 
            : (isMarathi ? 'नोंदी उपलब्ध नाहीत' : 'No valid scenes')}
        </div>
      </div>
    </div>
  );
}
