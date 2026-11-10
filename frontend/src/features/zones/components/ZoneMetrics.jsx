/**
 * FarmShield AI - ZoneMetrics Component
 * 
 * Displays key telemetry metric cards (Latest Soil Moisture, Latest NDVI, Weather summary).
 * Adheres strictly to the rule: Never infer soil moisture from NDVI, and never treat missing measurements as zero.
 */

import React from 'react';
import { Droplets, Activity, Thermometer, Wind, CloudRain, Clock } from 'lucide-react';

export default function ZoneMetrics({
  soilMoisture = null, // { value, unit, observed_at, source }
  vegetationIndex = null, // { value, unit, observed_at, source }
  weather = null, // { temperature, rainfall, et0 }
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';

  const formatTime = (ts) => {
    if (!ts) return null;
    try {
      const d = new Date(ts);
      return d.toLocaleDateString();
    } catch (e) {
      return null;
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '10px' }}>
      {/* 1. Soil Moisture Card */}
      <div
        className="glass-card"
        style={{
          padding: '14px',
          background: 'rgba(7, 31, 22, 0.70)',
          border: '1px solid rgba(56, 189, 248, 0.35)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
          <span style={{ fontSize: '11px', color: '#93C5FD', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Droplets size={13} color="#38BDF8" />
            {isMarathi ? 'माती ओलावा' : 'Soil Moisture'}
          </span>
          {soilMoisture?.observed_at && (
            <span style={{ fontSize: '9.5px', color: '#8E9F90' }}>
              {formatTime(soilMoisture.observed_at)}
            </span>
          )}
        </div>

        <div style={{ fontSize: '22px', fontWeight: 800, color: soilMoisture?.value !== null && soilMoisture?.value !== undefined ? '#38BDF8' : '#94A3B8' }}>
          {soilMoisture?.value !== null && soilMoisture?.value !== undefined ? (
            <>
              {soilMoisture.value}
              <span style={{ fontSize: '13px', marginLeft: '2px' }}>{soilMoisture.unit || '%'}</span>
            </>
          ) : (
            '—'
          )}
        </div>

        <div style={{ fontSize: '10px', color: '#8E9F90', marginTop: '4px' }}>
          {soilMoisture?.value !== null && soilMoisture?.value !== undefined ? (
            <span>{soilMoisture.source || (isMarathi ? 'सेन्सर प्रोब (३० सेंमी)' : 'Capacitive Probe')}</span>
          ) : (
            <span style={{ color: '#FBBF24' }}>{isMarathi ? 'नोंद अनुपलब्ध' : 'Unrecorded'}</span>
          )}
        </div>
      </div>

      {/* 2. NDVI Canopy Card */}
      <div
        className="glass-card"
        style={{
          padding: '14px',
          background: 'rgba(7, 31, 22, 0.70)',
          border: '1px solid rgba(101, 199, 106, 0.35)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
          <span style={{ fontSize: '11px', color: '#86EFAC', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Activity size={13} color="#65C76A" />
            NDVI {isMarathi ? 'इंडेक्स' : 'Canopy'}
          </span>
          {vegetationIndex?.observed_at && (
            <span style={{ fontSize: '9.5px', color: '#8E9F90' }}>
              {formatTime(vegetationIndex.observed_at)}
            </span>
          )}
        </div>

        <div style={{ fontSize: '22px', fontWeight: 800, color: vegetationIndex?.value !== null && vegetationIndex?.value !== undefined ? '#65C76A' : '#94A3B8' }}>
          {vegetationIndex?.value !== null && vegetationIndex?.value !== undefined ? (
            vegetationIndex.value
          ) : (
            '—'
          )}
        </div>

        <div style={{ fontSize: '10px', color: '#8E9F90', marginTop: '4px' }}>
          {vegetationIndex?.value !== null && vegetationIndex?.value !== undefined ? (
            <span>{vegetationIndex.source || 'Sentinel-2 L2A (10m)'}</span>
          ) : (
            <span style={{ color: '#FBBF24' }}>{isMarathi ? 'ढगाळ दृश्य / अनुपलब्ध' : 'Cloud Cover / None'}</span>
          )}
        </div>
      </div>

      {/* 3. Weather / Evapotranspiration Card */}
      <div
        className="glass-card"
        style={{
          padding: '14px',
          background: 'rgba(7, 31, 22, 0.70)',
          border: '1px solid rgba(251, 191, 36, 0.35)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
          <span style={{ fontSize: '11px', color: '#FDE68A', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Thermometer size={13} color="#FBBF24" />
            {isMarathi ? 'हवामान / बाष्पीभवन' : 'ET₀ / Weather'}
          </span>
        </div>

        <div style={{ fontSize: '18px', fontWeight: 800, color: '#FFFFFF' }}>
          {weather?.et0 !== undefined && weather?.et0 !== null ? (
            <>
              {weather.et0} <span style={{ fontSize: '11px', color: '#FBBF24' }}>mm/day</span>
            </>
          ) : (
            <span>{weather?.temperature ? `${weather.temperature}°C` : '—'}</span>
          )}
        </div>

        <div style={{ fontSize: '10px', color: '#8E9F90', marginTop: '4px' }}>
          {weather?.source || 'Open-Meteo Agro-v1'}
        </div>
      </div>
    </div>
  );
}

