/**
 * FarmShield AI - SoilObservationCard Component
 * 
 * Detailed display of soil moisture readings, sensor hardware identities,
 * calibration depths, and soil physical properties.
 * 
 * Adheres strictly to the rule: Missing measurements are never treated as zero.
 */

import React from 'react';
import { Droplets, Gauge, Clock, ShieldCheck, Layers, AlertCircle } from 'lucide-react';
import InsufficientDataState from './InsufficientDataState.jsx';

export default function SoilObservationCard({
  observations = [],
  soilType = null,
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';

  // Filter for soil moisture or soil condition observations
  const soilObs = observations.filter(
    (o) => o.observation_type === 'soil_moisture' || (o.unit && o.unit.includes('%'))
  );

  const formatTimestamp = (ts) => {
    if (!ts) return isMarathi ? 'दिनांक अनुपलब्ध' : 'Timestamp missing';
    try {
      const d = new Date(ts);
      return `${d.toLocaleDateString()} at ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } catch (e) {
      return String(ts);
    }
  };

  return (
    <div
      className="glass-card"
      style={{
        padding: '18px',
        background: 'rgba(7, 31, 22, 0.75)',
        border: '1px solid rgba(56, 189, 248, 0.30)',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'rgba(56, 189, 248, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#38BDF8',
            }}
          >
            <Droplets size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#FFFFFF', margin: 0 }}>
              {isMarathi ? 'माती ओलावा व सेन्सर निरीक्षणे' : 'Soil Moisture & Sensor Observations'}
            </h3>
            <div style={{ fontSize: '11px', color: '#93C5FD' }}>
              {isMarathi ? 'मुळांच्या कार्यक्षेत्रातील ओलावा स्थिती' : 'Root-zone water content & sensor probes'}
            </div>
          </div>
        </div>

        {soilObs.length > 0 && (
          <span className="glass-pill" style={{ color: '#38BDF8', fontSize: '11px' }}>
            {soilObs.length} {isMarathi ? 'नोंदी' : 'records'}
          </span>
        )}
      </div>

      {/* Soil Type Info (if available from metadata) */}
      {soilType && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 12px',
            background: 'rgba(255, 255, 255, 0.05)',
            borderRadius: '12px',
            marginBottom: '14px',
            fontSize: '11.5px',
            color: '#D5E3D9',
            border: '1px solid rgba(255, 255, 255, 0.10)',
          }}
        >
          <Layers size={14} color="#C5F36B" />
          <span>
            <strong>{isMarathi ? 'माती प्रकार:' : 'Soil Classification:'}</strong> {soilType}
          </span>
        </div>
      )}

      {/* Observations List or Insufficient Data State */}
      {soilObs.length === 0 ? (
        <InsufficientDataState
          title={isMarathi ? 'माती ओलावा निरीक्षणे उपलब्ध नाहीत' : 'No Soil Moisture Observations'}
          message={isMarathi 
            ? 'या विभागासाठी कोणतीही वैध माती ओलावा निरीक्षणे नोंदवलेली नाहीत. सिंचनाचा अचूक ताण मोजण्यासाठी सेन्सर डेटा जोडणे आवश्यक आहे.' 
            : 'No valid soil moisture observations found for this zone. Field sensor readings or in-situ probe data are required.'}
          reason={isMarathi ? 'शेत ओलावा सेन्सर जोडलेला नाही किंवा डेटा सिंक झालेला नाही' : 'Field probe not linked or synchronization pending'}
          currentLang={currentLang}
          icon={Droplets}
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {soilObs.map((obs, idx) => {
            const hasValue = obs.value !== null && obs.value !== undefined;
            const quality = obs.metadata?.quality_status || 'good';

            return (
              <div
                key={obs.id || `soil-obs-${idx}`}
                className="glass-panel"
                style={{
                  padding: '12px 14px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '12px',
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '2px' }}>
                    <Gauge size={13} color="#38BDF8" />
                    <span style={{ fontSize: '12px', fontWeight: 700, color: '#FFFFFF' }}>
                      {obs.source || (isMarathi ? 'सेन्सर प्रोब' : 'Sensor Probe')}
                    </span>
                    {obs.metadata?.depth_cm && (
                      <span style={{ fontSize: '10px', color: '#93C5FD', background: 'rgba(56, 189, 248, 0.15)', padding: '1px 5px', borderRadius: '6px' }}>
                        {obs.metadata.depth_cm} cm
                      </span>
                    )}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10.5px', color: '#8E9F90' }}>
                    <Clock size={11} />
                    <span>{formatTimestamp(obs.observed_at)}</span>
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div
                    style={{
                      fontSize: '17px',
                      fontWeight: 800,
                      color: hasValue ? '#38BDF8' : '#94A3B8',
                    }}
                  >
                    {hasValue ? (
                      <>
                        {obs.value}
                        <span style={{ fontSize: '12px', marginLeft: '2px' }}>{obs.unit || '%'}</span>
                      </>
                    ) : (
                      '—'
                    )}
                  </div>
                  {!hasValue && (
                    <div style={{ fontSize: '9.5px', color: '#FBBF24' }}>
                      {isMarathi ? 'माहिती गहाळ' : 'Missing Value'}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

