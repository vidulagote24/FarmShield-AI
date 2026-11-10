/**
 * FarmShield AI - ObservationHistoryChart Component
 * 
 * Tabular inspection list of all recorded observations across farm zones.
 * Displays physical metrics, observation dates, sources, and sensor quality flags.
 */

import React, { useState } from 'react';
import { ListFilter, Clock, CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react';

export default function ObservationHistoryChart({
  observations = [],
  zones = [],
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';
  const [typeFilter, setTypeFilter] = useState('all');

  const zoneMap = new Map();
  zones.forEach((z) => zoneMap.set(z.id, z));

  const sortedObs = [...observations]
    .filter((o) => {
      if (typeFilter === 'all') return true;
      return o.observation_type === typeFilter || o.metric_type === typeFilter;
    })
    .sort((a, b) => new Date(b.observed_at) - new Date(a.observed_at));

  const formatTimestamp = (ts) => {
    if (!ts) return null;
    try {
      const d = new Date(ts);
      return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } catch {
      return ts;
    }
  };

  const getMetricBadge = (type) => {
    switch (type) {
      case 'soil_moisture':
        return { label_mr: 'माती ओलावा', label_en: 'Soil Moisture', color: '#38BDF8', bg: 'rgba(56, 189, 248, 0.15)' };
      case 'vegetation_index':
        return { label_mr: 'NDVI इंडेक्स', label_en: 'Canopy NDVI', color: '#C5F36B', bg: 'rgba(197, 243, 107, 0.15)' };
      case 'weather':
      case 'temperature':
      case 'rainfall':
        return { label_mr: 'हवामान', label_en: 'Weather', color: '#FBBF24', bg: 'rgba(251, 191, 36, 0.15)' };
      default:
        return { label_mr: type, label_en: type, color: '#CBD5E1', bg: 'rgba(255, 255, 255, 0.1)' };
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
      {/* Header and Type Filter */}
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
            <ListFilter size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#FFFFFF', margin: 0 }}>
              {isMarathi ? 'नोंदवलेली टेलिमेट्री सूची (Verified Telemetry Log)' : 'Observation Log & Metadata'}
            </h3>
            <div style={{ fontSize: '11px', color: '#B6C8BB' }}>
              {isMarathi ? 'प्रत्येक नोंदीचा वेळ, स्रोत आणि सेन्सर गुणवत्ता' : 'Chronological observation telemetry table'}
            </div>
          </div>
        </div>

        {/* Filter Pills */}
        <div style={{ display: 'flex', gap: '4px' }}>
          {['all', 'soil_moisture', 'vegetation_index'].map((t) => {
            const isSelected = typeFilter === t;
            const label = t === 'all' 
              ? (isMarathi ? 'सर्व' : 'All') 
              : t === 'soil_moisture' 
                ? (isMarathi ? 'ओलावा' : 'Moisture') 
                : (isMarathi ? 'NDVI' : 'NDVI');

            return (
              <button
                key={t}
                onClick={() => setTypeFilter(t)}
                style={{
                  padding: '3px 8px',
                  borderRadius: '12px',
                  fontSize: '10.5px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  border: isSelected ? '1px solid #C5F36B' : '1px solid rgba(255, 255, 255, 0.14)',
                  background: isSelected ? 'rgba(197, 243, 107, 0.2)' : 'transparent',
                  color: isSelected ? '#C5F36B' : '#94A3B8',
                }}
              >
                {label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Observation List Items */}
      {sortedObs.length === 0 ? (
        <div style={{ padding: '16px', textAlign: 'center', color: '#94A3B8', fontSize: '12px' }}>
          {isMarathi ? 'या प्रकारासाठी कोणतीही नोंद आढळली नाही.' : 'No observations found for this filter.'}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '320px', overflowY: 'auto' }}>
          {sortedObs.slice(0, 30).map((obs) => {
            const z = zoneMap.get(obs.zone_id);
            const badge = getMetricBadge(obs.observation_type || obs.metric_type);
            const meta = obs.metadata || obs.metadata_json || {};
            const quality = meta.quality || meta.quality_status || (obs.value === null ? 'insufficient' : 'good');
            const isGood = quality === 'good';

            return (
              <div
                key={obs.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 12px',
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.07)',
                  borderRadius: '10px',
                  gap: '10px',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '2px' }}>
                    <span
                      style={{
                        padding: '2px 6px',
                        borderRadius: '6px',
                        background: badge.bg,
                        color: badge.color,
                        fontSize: '10px',
                        fontWeight: 800,
                        textTransform: 'uppercase',
                      }}
                    >
                      {isMarathi ? badge.label_mr : badge.label_en}
                    </span>

                    <span style={{ fontSize: '11px', fontWeight: 700, color: '#FFFFFF' }}>
                      {z?.zone_code || 'ZONE'}
                    </span>
                  </div>

                  <div style={{ fontSize: '10px', color: '#8E9F90', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Clock size={10} />
                    <span>{formatTimestamp(obs.observed_at)}</span>
                    {obs.source && <span>• {obs.source}</span>}
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '15px', fontWeight: 800, color: obs.value !== null ? '#FFFFFF' : '#F87171' }}>
                    {obs.value !== null && obs.value !== undefined ? (
                      obs.unit === '%' ? `${obs.value}%` : `${obs.value} ${obs.unit || ''}`
                    ) : (
                      <span style={{ fontSize: '11px', color: '#F87171' }}>{isMarathi ? 'अपुरा डेटा' : 'Unavailable'}</span>
                    )}
                  </div>
                  <div style={{ fontSize: '9px', color: isGood ? '#4ADE80' : '#FCA5A5' }}>
                    {quality}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

