/**
 * FarmShield AI - EvidenceBreakdown Component
 * 
 * Displays transparent evidence telemetry and backend decision factors.
 * 
 * Scientific Integrity Rules:
 * - Do NOT calculate agronomic formulas in frontend code.
 * - Do NOT create stress thresholds.
 * - Do NOT infer drought from NDVI alone.
 * - Do NOT present missing data as zero.
 * - Clearly distinguish measured evidence (sensors/satellites) from backend interpretation (decision rules).
 * - If evidence is unavailable, state honestly that it was not returned.
 */

import React from 'react';
import { Activity, Gauge, Eye, CloudSun, AlertCircle, CheckCircle, ShieldCheck } from 'lucide-react';

export default function EvidenceBreakdown({
  recommendation,
  observations = [],
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';
  const reasoning = recommendation?.reasoning || {};

  // Extract latest soil moisture and NDVI observations if provided
  const smObs = observations.find((o) => o.observation_type === 'soil_moisture' || o.metric_type === 'soil_moisture' || o.metric === 'soil_moisture');
  const ndviObs = observations.find((o) => o.observation_type === 'vegetation_index' || o.metric_type === 'ndvi' || o.metric === 'ndvi');
  const etObs = observations.find((o) => o.observation_type === 'evapotranspiration' || o.metric_type === 'et0' || o.metric_type === 'evapotranspiration');

  // Backend reasoning fields
  const stressStatus = reasoning.stress_status;
  const stressReasons = Array.isArray(reasoning.stress_reasons) ? reasoning.stress_reasons : [];
  const confidence = typeof reasoning.confidence === 'number' ? reasoning.confidence : null;

  const hasMeasuredEvidence = Boolean(smObs || ndviObs || etObs);
  const hasReasoningEvidence = Boolean(stressStatus || stressReasons.length > 0 || confidence !== null);

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
      {/* Section Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
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
            <Activity size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#FFFFFF', margin: 0 }}>
              {isMarathi ? 'पुरावा व निरीक्षणे (Evidence Breakdown)' : 'Evidence & Observations'}
            </h3>
            <div style={{ fontSize: '11px', color: '#B6C8BB' }}>
              {isMarathi ? 'माती सेन्सर, उपग्रह व बॅकएंड विश्लेषणाचा पुरावा' : 'Measured telemetry and model classification'}
            </div>
          </div>
        </div>

        {confidence !== null && (
          <span
            className="glass-pill"
            style={{
              color: '#C5F36B',
              border: '1px solid rgba(197, 243, 107, 0.4)',
              fontSize: '11px',
              fontWeight: 800,
            }}
          >
            {isMarathi ? 'विश्वासार्हता:' : 'Confidence:'} {Math.round(confidence * 100)}%
          </span>
        )}
      </div>

      {/* Part 1: Measured Ground Telemetry (Direct Measurements) */}
      <div style={{ marginBottom: '14px' }}>
        <div style={{ fontSize: '11px', fontWeight: 800, color: '#8E9F90', textTransform: 'uppercase', marginBottom: '8px' }}>
          {isMarathi ? '१. प्रत्यक्ष मोजमापे (Measured Telemetry)' : '1. Measured Telemetry (Ground & Satellite)'}
        </div>

        {!hasMeasuredEvidence ? (
          <div
            style={{
              padding: '10px 12px',
              background: 'rgba(255, 255, 255, 0.03)',
              borderRadius: '10px',
              border: '1px dashed rgba(255, 255, 255, 0.15)',
              fontSize: '12px',
              color: '#94A3B8',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <AlertCircle size={14} color="#94A3B8" />
            <span>
              {isMarathi 
                ? 'या सल्ल्यासाठी प्रत्यक्ष सेन्सर मोजमापे बॅकएंडकडून स्वतंत्रपणे पाठवली नाहीत.' 
                : 'Raw telemetry observations were not returned in the backend recommendation payload.'}
            </span>
          </div>
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
              gap: '8px',
            }}
          >
            {/* Soil Moisture */}
            {smObs && (
              <div
                style={{
                  padding: '10px 12px',
                  background: 'rgba(56, 189, 248, 0.08)',
                  border: '1px solid rgba(56, 189, 248, 0.25)',
                  borderRadius: '12px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: '#93C5FD', fontSize: '10.5px', fontWeight: 700 }}>
                  <Gauge size={12} />
                  <span>{isMarathi ? 'मातीतील ओलावा' : 'Soil Moisture'}</span>
                </div>
                <div style={{ fontSize: '18px', fontWeight: 800, color: '#38BDF8', margin: '3px 0' }}>
                  {smObs.value !== null && smObs.value !== undefined ? `${smObs.value}${smObs.unit || '%'}` : '—'}
                </div>
                <div style={{ fontSize: '9px', color: '#8E9F90' }}>
                  {formatTimestamp(smObs.observed_at || smObs.created_at)}
                </div>
              </div>
            )}

            {/* NDVI */}
            {ndviObs && (
              <div
                style={{
                  padding: '10px 12px',
                  background: 'rgba(197, 243, 107, 0.08)',
                  border: '1px solid rgba(197, 243, 107, 0.25)',
                  borderRadius: '12px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: '#C5F36B', fontSize: '10.5px', fontWeight: 700 }}>
                  <Eye size={12} />
                  <span>{isMarathi ? 'कॅनोपी NDVI' : 'Canopy NDVI'}</span>
                </div>
                <div style={{ fontSize: '18px', fontWeight: 800, color: '#C5F36B', margin: '3px 0' }}>
                  {ndviObs.value !== null && ndviObs.value !== undefined ? ndviObs.value : '—'}
                </div>
                <div style={{ fontSize: '9px', color: '#8E9F90' }}>
                  {formatTimestamp(ndviObs.observed_at || ndviObs.created_at)}
                </div>
              </div>
            )}

            {/* ET0 */}
            {etObs && (
              <div
                style={{
                  padding: '10px 12px',
                  background: 'rgba(251, 191, 36, 0.08)',
                  border: '1px solid rgba(251, 191, 36, 0.25)',
                  borderRadius: '12px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: '#FBBF24', fontSize: '10.5px', fontWeight: 700 }}>
                  <CloudSun size={12} />
                  <span>{isMarathi ? 'बाष्पीभवन (ET0)' : 'Evapotranspiration'}</span>
                </div>
                <div style={{ fontSize: '18px', fontWeight: 800, color: '#FBBF24', margin: '3px 0' }}>
                  {etObs.value !== null && etObs.value !== undefined ? `${etObs.value} ${etObs.unit || 'mm/day'}` : '—'}
                </div>
                <div style={{ fontSize: '9px', color: '#8E9F90' }}>
                  {formatTimestamp(etObs.observed_at || etObs.created_at)}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Part 2: Backend AI Model Classification (Algorithmic Interpretation) */}
      <div>
        <div style={{ fontSize: '11px', fontWeight: 800, color: '#8E9F90', textTransform: 'uppercase', marginBottom: '8px' }}>
          {isMarathi ? '२. मॉडेल विश्लेषण (Backend Classification)' : '2. Algorithmic Interpretation & Stress Triggers'}
        </div>

        {!hasReasoningEvidence ? (
          <div
            style={{
              padding: '10px 12px',
              background: 'rgba(255, 255, 255, 0.03)',
              borderRadius: '10px',
              border: '1px dashed rgba(255, 255, 255, 0.15)',
              fontSize: '12px',
              color: '#94A3B8',
            }}
          >
            {isMarathi 
              ? 'बॅकएंडकडून ताण वर्गीकरण तपशील उपलब्ध नाहीत.' 
              : 'Stress classification fields were not provided in backend reasoning.'}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {stressStatus && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '8px 12px',
                  background: 'rgba(255, 255, 255, 0.04)',
                  borderRadius: '10px',
                }}
              >
                <span style={{ fontSize: '12px', color: '#CBD5E1' }}>
                  {isMarathi ? 'पिकावरील ताण स्थिती (Stress Level):' : 'Crop Stress Classification:'}
                </span>
                <span
                  style={{
                    fontSize: '12px',
                    fontWeight: 800,
                    textTransform: 'uppercase',
                    color: stressStatus === 'healthy' ? '#22C55E' : stressStatus === 'monitor' ? '#F59E0B' : '#EF4444',
                  }}
                >
                  {stressStatus}
                </span>
              </div>
            )}

            {stressReasons.length > 0 && (
              <div
                style={{
                  padding: '10px 12px',
                  background: 'rgba(255, 255, 255, 0.04)',
                  borderRadius: '10px',
                }}
              >
                <div style={{ fontSize: '11px', color: '#8E9F90', fontWeight: 700, marginBottom: '6px' }}>
                  {isMarathi ? 'सक्रिय झालेले ताण कोड (Trigger Codes):' : 'Active Model Trigger Codes:'}
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {stressReasons.map((code, idx) => (
                    <span
                      key={idx}
                      style={{
                        padding: '3px 8px',
                        background: 'rgba(239, 68, 68, 0.15)',
                        border: '1px solid rgba(239, 68, 68, 0.35)',
                        borderRadius: '6px',
                        fontSize: '10.5px',
                        color: '#FCA5A5',
                        fontFamily: 'monospace',
                      }}
                    >
                      {code}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
