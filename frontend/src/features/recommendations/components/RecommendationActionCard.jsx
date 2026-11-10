/**
 * FarmShield AI - RecommendationActionCard Component
 * 
 * Displays the recommended agronomic action, depth (mm), volume (m³),
 * application window, method, and link to Irrigation Planner when applicable.
 * 
 * Agronomic Safety Rules:
 * - Does not calculate water depth or volume in frontend code.
 * - Displays water quantities ONLY when returned by the backend.
 * - Strictly advisory: displays no pump/valve triggers.
 */

import React from 'react';
import { Droplet, Clock, Compass, ShieldAlert, ArrowRight, CheckCircle2 } from 'lucide-react';

export default function RecommendationActionCard({
  action = {},
  description,
  descriptionEn,
  currentLang = 'mr',
  onOpenIrrigationPlanner,
}) {
  const isMarathi = currentLang === 'mr';

  const actionType = action.action || action.action_type || 'advisory';
  const isIrrigate = actionType.toLowerCase().includes('irrigate');

  const getActionLabel = (act) => {
    switch (act.toLowerCase()) {
      case 'irrigate':
        return { mr: 'सिंचन करा (Irrigate)', en: 'Apply Irrigation', color: '#38BDF8' };
      case 'monitor':
        return { mr: 'निरीक्षण सुरू ठेवा (Monitor)', en: 'Monitor Conditions', color: '#F59E0B' };
      case 'wait':
        return { mr: 'सिंचन पुढे ढकला (Wait)', en: 'Hold / Defer Irrigation', color: '#22C55E' };
      case 'emergency_cooling':
        return { mr: 'तातडीचे कूलिंग सिंचन (Emergency Cooling)', en: 'Emergency Cooling Irrigation', color: '#EF4444' };
      default:
        return { mr: act, en: act, color: '#C5F36B' };
    }
  };

  const actionLabel = getActionLabel(actionType);
  const hasWaterMetrics = action.water_depth_mm !== undefined || action.water_volume_m3 !== undefined;

  return (
    <div
      className="glass-card"
      style={{
        padding: '18px',
        marginBottom: '16px',
        background: 'rgba(7, 31, 22, 0.85)',
        border: isIrrigate ? '1.5px solid rgba(56, 189, 248, 0.45)' : '1px solid rgba(197, 243, 107, 0.35)',
        boxShadow: isIrrigate ? '0 8px 24px rgba(0, 0, 0, 0.4), 0 0 16px rgba(56, 189, 248, 0.12)' : 'none',
      }}
    >
      {/* Action Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: isIrrigate ? 'rgba(56, 189, 248, 0.20)' : 'rgba(197, 243, 107, 0.20)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: isIrrigate ? '#38BDF8' : '#C5F36B',
            }}
          >
            <Droplet size={18} />
          </div>
          <div>
            <span style={{ fontSize: '10.5px', color: '#8E9F90', textTransform: 'uppercase', fontWeight: 700 }}>
              {isMarathi ? 'शिफारस कृती (Recommended Action)' : 'Prescribed Action'}
            </span>
            <h3 style={{ fontSize: '16px', fontWeight: 800, color: actionLabel.color, margin: 0 }}>
              {isMarathi ? actionLabel.mr : actionLabel.en}
            </h3>
          </div>
        </div>
      </div>

      {/* Description */}
      {(description || descriptionEn) && (
        <p style={{ fontSize: '13px', color: '#D5E3D9', lineHeight: 1.5, marginBottom: '14px' }}>
          {isMarathi ? (description || descriptionEn) : (descriptionEn || description)}
        </p>
      )}

      {/* Backend-Computed Water Metrics (Only when provided) */}
      {hasWaterMetrics && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))',
            gap: '10px',
            padding: '12px',
            background: 'rgba(56, 189, 248, 0.08)',
            border: '1px solid rgba(56, 189, 248, 0.25)',
            borderRadius: '12px',
            marginBottom: '14px',
          }}
        >
          {action.water_depth_mm !== undefined && action.water_depth_mm !== null && (
            <div>
              <div style={{ fontSize: '10px', color: '#93C5FD', fontWeight: 600 }}>
                {isMarathi ? 'शिफारस पाणी खोली' : 'Prescribed Depth'}
              </div>
              <div style={{ fontSize: '18px', fontWeight: 800, color: '#38BDF8', marginTop: '2px' }}>
                {action.water_depth_mm} <span style={{ fontSize: '12px' }}>mm</span>
              </div>
            </div>
          )}

          {action.water_volume_m3 !== undefined && action.water_volume_m3 !== null && (
            <div>
              <div style={{ fontSize: '10px', color: '#93C5FD', fontWeight: 600 }}>
                {isMarathi ? 'पाणी घनफळ (Volume)' : 'Prescribed Volume'}
              </div>
              <div style={{ fontSize: '18px', fontWeight: 800, color: '#38BDF8', marginTop: '2px' }}>
                {action.water_volume_m3} <span style={{ fontSize: '12px' }}>m³</span>
              </div>
              <div style={{ fontSize: '9.5px', color: '#8E9F90' }}>
                (~{(action.water_volume_m3 * 1000).toLocaleString()} L)
              </div>
            </div>
          )}

          {action.recommended_window && (
            <div>
              <div style={{ fontSize: '10px', color: '#C5F36B', fontWeight: 600 }}>
                {isMarathi ? 'योग्य वेळ (Window)' : 'Optimal Window'}
              </div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: '#FFFFFF', marginTop: '2px' }}>
                {action.recommended_window}
              </div>
            </div>
          )}

          {action.irrigation_method && (
            <div>
              <div style={{ fontSize: '10px', color: '#94A3B8', fontWeight: 600 }}>
                {isMarathi ? 'सिंचन पद्धत' : 'Method'}
              </div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: '#FFFFFF', marginTop: '2px' }}>
                {action.irrigation_method}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Button to jump to Irrigation Planner if action is irrigate */}
      {isIrrigate && onOpenIrrigationPlanner && (
        <button
          onClick={onOpenIrrigationPlanner}
          className="btn-glass-primary"
          style={{
            width: '100%',
            minHeight: '40px',
            fontSize: '12.5px',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            marginBottom: '10px',
            cursor: 'pointer',
          }}
        >
          <span>{isMarathi ? 'सिंचन नियोजक उघडा (Open Irrigation Planner)' : 'Go to Irrigation Planner'}</span>
          <ArrowRight size={14} />
        </button>
      )}

      {/* Advisory Notice */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '6px 10px',
          background: 'rgba(255, 255, 255, 0.04)',
          borderRadius: '8px',
          fontSize: '10px',
          color: '#8E9F90',
        }}
      >
        <ShieldAlert size={12} color="#F59E0B" style={{ flexShrink: 0 }} />
        <span>
          {isMarathi 
            ? 'केवळ मार्गदर्शक सल्ला — प्रत्यक्ष शेतात पाणी देण्याचे निर्णय स्वतःच्या अनुभवानुसार व परिस्थिती पाहून घ्यावेत.' 
            : 'Advisory guidance only. Always confirm soil conditions on-site before applying water.'}
        </span>
      </div>
    </div>
  );
}

