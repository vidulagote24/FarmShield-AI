/**
 * FarmShield AI - IrrigationDetails Component
 * 
 * Displays the backend-grounded agronomic recommendation details,
 * water balance factors, and decision evidence.
 * 
 * Safety & Scientific Integrity:
 * - Does not generate pump runtime estimates or assume delivery flow rates.
 * - Does not calculate water depth or volume in frontend code.
 * - Strictly displays backend-provided recommendation quantities and reasons.
 */

import React from 'react';
import { Info, Droplets, Clock, FileText, ShieldCheck, CheckCircle2 } from 'lucide-react';

export default function IrrigationDetails({
  recommendation,
  zone,
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';
  if (!recommendation) return null;

  const action = recommendation.recommended_action || {};
  const reasoning = recommendation.reasoning || {};

  return (
    <div
      className="glass-panel"
      style={{
        padding: '16px',
        border: '1px solid rgba(56, 189, 248, 0.25)',
        background: 'rgba(7, 31, 22, 0.90)',
        borderRadius: '16px',
      }}
    >
      {/* Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
        <Info size={16} color="#38BDF8" />
        <h4 style={{ fontSize: '13.5px', fontWeight: 800, color: '#FFFFFF', margin: 0 }}>
          {isMarathi ? 'कृषी जल ताळेबंद व शिफारस तपशील' : 'Agronomic Water Balance & Recommendation Basis'}
        </h4>
      </div>

      {/* Backend-provided parameters */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: '8px',
          marginBottom: '14px',
        }}
      >
        {action.water_depth_mm !== undefined && action.water_depth_mm !== null && (
          <div
            style={{
              padding: '10px',
              background: 'rgba(255, 255, 255, 0.05)',
              borderRadius: '12px',
              border: '1px solid rgba(255, 255, 255, 0.10)',
            }}
          >
            <div style={{ fontSize: '10.5px', color: '#93C5FD' }}>
              {isMarathi ? 'पाणी खोली (Net Depth)' : 'Recommended Depth'}
            </div>
            <div style={{ fontSize: '15px', fontWeight: 800, color: '#38BDF8', marginTop: '2px' }}>
              {action.water_depth_mm} mm
            </div>
            <div style={{ fontSize: '9.5px', color: '#8E9F90' }}>
              FAO-56 Water Balance
            </div>
          </div>
        )}

        {action.water_volume_m3 !== undefined && action.water_volume_m3 !== null && (
          <div
            style={{
              padding: '10px',
              background: 'rgba(255, 255, 255, 0.05)',
              borderRadius: '12px',
              border: '1px solid rgba(255, 255, 255, 0.10)',
            }}
          >
            <div style={{ fontSize: '10.5px', color: '#93C5FD' }}>
              {isMarathi ? 'एकूण घनफळ (Volume)' : 'Recommended Volume'}
            </div>
            <div style={{ fontSize: '15px', fontWeight: 800, color: '#38BDF8', marginTop: '2px' }}>
              {action.water_volume_m3} m³
            </div>
            <div style={{ fontSize: '9.5px', color: '#8E9F90' }}>
              Backend Model Output
            </div>
          </div>
        )}

        {action.recommended_window && (
          <div
            style={{
              padding: '10px',
              background: 'rgba(255, 255, 255, 0.05)',
              borderRadius: '12px',
              border: '1px solid rgba(255, 255, 255, 0.10)',
            }}
          >
            <div style={{ fontSize: '10.5px', color: '#C5F36B' }}>
              {isMarathi ? 'शिफारस वेळ (Window)' : 'Advisory Window'}
            </div>
            <div style={{ fontSize: '12px', fontWeight: 700, color: '#FFFFFF', marginTop: '2px' }}>
              {action.recommended_window}
            </div>
            <div style={{ fontSize: '9.5px', color: '#8E9F90' }}>
              Evaporation Minimization
            </div>
          </div>
        )}
      </div>

      {/* Decision Factors */}
      {reasoning.factors && reasoning.factors.length > 0 && (
        <div style={{ marginBottom: '12px' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#C5F36B', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <FileText size={12} />
            <span>{isMarathi ? 'निर्णय कारणे व पुरावा (Evidence Factors):' : 'Decision Factors & Evidence:'}</span>
          </div>
          <ul style={{ paddingLeft: '18px', margin: 0, fontSize: '11.5px', color: '#CBD5E1', lineHeight: 1.45 }}>
            {reasoning.factors.map((factor, idx) => (
              <li key={`detail-factor-${idx}`}>{factor}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Safety Notice */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '8px 10px',
          background: 'rgba(255, 255, 255, 0.04)',
          borderRadius: '10px',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          fontSize: '10.5px',
          color: '#A3B8A8',
        }}
      >
        <ShieldCheck size={14} color="#65C76A" style={{ flexShrink: 0 }} />
        <span>
          {isMarathi 
            ? 'ही केवळ कृषी शिफारस आहे. शेतकऱ्याने प्रत्यक्ष शेतातील माती ओलावा तपासून मॅन्युअली पाणी द्यावे.' 
            : 'Advisory guidance only. Always confirm actual soil moisture before manually delivering irrigation.'}
        </span>
      </div>
    </div>
  );
}
