/**
 * FarmShield AI - IrrigationRecommendationCard Component
 * 
 * Displays actionable irrigation recommendations for a zone,
 * including depth (mm), volume (m³), recommended application window,
 * scientific evidence reasons, and a button to record completed irrigation.
 * 
 * Strict Agronomic Integrity:
 * - Does not calculate water depth or volume in frontend code.
 * - Does not treat missing values as zero.
 * - Clearly distinguishes recommendations from completed events.
 */

import React from 'react';
import { Droplets, Clock, Calendar, FileText, ArrowRight, CheckCircle2, ChevronDown, ChevronUp } from 'lucide-react';
import IrrigationStatusBadge from './IrrigationStatusBadge.jsx';

export default function IrrigationRecommendationCard({
  recommendation,
  zone,
  onOpenRecordForm,
  onToggleDetails,
  onSelectRecommendation,
  showDetails = false,
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';

  if (!recommendation) return null;

  const action = recommendation.recommended_action || {};
  const hasWaterAmounts = action.water_depth_mm !== undefined || action.water_volume_m3 !== undefined;
  const isIrrigateAction = action.action === 'irrigate';

  const formatTimestamp = (ts) => {
    if (!ts) return null;
    try {
      const d = new Date(ts);
      return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } catch (e) {
      return ts;
    }
  };

  return (
    <div
      className="glass-card"
      style={{
        padding: '18px',
        background: 'rgba(7, 31, 22, 0.85)',
        border: isIrrigateAction ? '1.5px solid rgba(56, 189, 248, 0.45)' : '1px solid rgba(255, 255, 255, 0.16)',
        boxShadow: isIrrigateAction ? '0 10px 28px rgba(0, 0, 0, 0.4), 0 0 16px rgba(56, 189, 248, 0.15)' : 'none',
      }}
    >
      {/* Top Header: Zone & Badges */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '10px', gap: '8px', flexWrap: 'wrap' }}>
        <div>
          <span style={{ fontSize: '11.5px', fontWeight: 800, color: '#C5F36B' }}>
            📍 {zone?.zone_code || 'ZONE'} • {zone?.zone_name || (isMarathi ? 'व्यवस्थापन विभाग' : 'Zone')}
          </span>
          <h3 style={{ fontSize: '16.5px', fontWeight: 800, color: '#FFFFFF', marginTop: '2px', letterSpacing: '-0.2px' }}>
            {isMarathi ? (recommendation.title || recommendation.title_en) : (recommendation.title_en || recommendation.title)}
          </h3>
        </div>

        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <IrrigationStatusBadge type="priority" value={recommendation.priority} currentLang={currentLang} />
          {action.action && (
            <IrrigationStatusBadge type="action" value={action.action} currentLang={currentLang} />
          )}
        </div>
      </div>

      {/* Description */}
      <p style={{ fontSize: '13px', color: '#D5E3D9', lineHeight: 1.45, marginBottom: '14px' }}>
        {isMarathi ? (recommendation.description || recommendation.description_en) : (recommendation.description_en || recommendation.description)}
      </p>

      {/* Water Application Parameters Grid (Only if provided by backend) */}
      {hasWaterAmounts && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))',
            gap: '8px',
            padding: '12px',
            background: 'rgba(56, 189, 248, 0.08)',
            border: '1px solid rgba(56, 189, 248, 0.25)',
            borderRadius: '14px',
            marginBottom: '14px',
          }}
        >
          {action.water_depth_mm !== undefined && action.water_depth_mm !== null && (
            <div>
              <div style={{ fontSize: '10px', color: '#93C5FD', fontWeight: 600 }}>
                {isMarathi ? 'शिफारस पाणी खोली' : 'Required Depth'}
              </div>
              <div style={{ fontSize: '18px', fontWeight: 800, color: '#38BDF8', marginTop: '1px' }}>
                {action.water_depth_mm} <span style={{ fontSize: '11.5px' }}>mm</span>
              </div>
            </div>
          )}

          {action.water_volume_m3 !== undefined && action.water_volume_m3 !== null && (
            <div>
              <div style={{ fontSize: '10px', color: '#93C5FD', fontWeight: 600 }}>
                {isMarathi ? 'एकूण घनफळ (Volume)' : 'Total Volume'}
              </div>
              <div style={{ fontSize: '18px', fontWeight: 800, color: '#38BDF8', marginTop: '1px' }}>
                {action.water_volume_m3} <span style={{ fontSize: '11.5px' }}>m³</span>
              </div>
              <div style={{ fontSize: '9px', color: '#8E9F90' }}>
                (~{(action.water_volume_m3 * 1000).toLocaleString()} L)
              </div>
            </div>
          )}

          {action.recommended_window && (
            <div>
              <div style={{ fontSize: '10px', color: '#C5F36B', fontWeight: 600 }}>
                {isMarathi ? 'योग्य वेळ (Window)' : 'Optimal Timing'}
              </div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: '#FFFFFF', marginTop: '2px' }}>
                {action.recommended_window}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Reasoning Factors List */}
      {recommendation.reasoning?.factors && recommendation.reasoning.factors.length > 0 && (
        <div style={{ marginBottom: '14px' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#C5F36B', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <FileText size={12} />
            <span>{isMarathi ? 'कारणे व वैज्ञानिक निकष:' : 'Contributing Decision Factors:'}</span>
          </div>
          <ul style={{ paddingLeft: '18px', margin: 0, fontSize: '11.5px', color: '#CBD5E1', lineHeight: 1.45 }}>
            {recommendation.reasoning.factors.map((factor, idx) => (
              <li key={`factor-${idx}`}>{factor}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Timestamp and Expiry */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '10.5px', color: '#8E9F90', marginBottom: '14px', flexWrap: 'wrap', gap: '4px' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Clock size={11} />
          <span>{isMarathi ? 'सल्ला वेळ:' : 'Generated:'} {formatTimestamp(recommendation.generated_at)}</span>
        </span>
        {recommendation.valid_until && (
          <span>
            {isMarathi ? 'वैधता:' : 'Valid until:'} {formatTimestamp(recommendation.valid_until)}
          </span>
        )}
      </div>

      {/* Actions Row */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        {onOpenRecordForm && (
          <button
            onClick={() => onOpenRecordForm(recommendation)}
            className="btn-glass-primary"
            style={{
              flex: 1,
              minHeight: '40px',
              fontSize: '12.5px',
              fontWeight: 700,
              gap: '6px',
            }}
          >
            <CheckCircle2 size={15} />
            <span>{isMarathi ? 'सिंचन पूर्ण केल्याची नोंद करा' : 'Record Completed Irrigation'}</span>
          </button>
        )}

        {onSelectRecommendation && (
          <button
            onClick={() => onSelectRecommendation(recommendation.id)}
            className="btn-glass-secondary"
            style={{
              minHeight: '40px',
              padding: '0 12px',
              fontSize: '12px',
              color: '#38BDF8',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              cursor: 'pointer',
            }}
            title={isMarathi ? 'सल्ला विश्लेषण' : 'Evidence Details'}
          >
            <span>{isMarathi ? 'सल्ला विश्लेषण' : 'Evidence'}</span>
            <ArrowRight size={14} />
          </button>
        )}

        {onToggleDetails && (
          <button
            onClick={onToggleDetails}
            className="btn-glass-secondary"
            style={{
              minHeight: '40px',
              padding: '0 12px',
              fontSize: '12px',
              color: '#C5F36B',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
            }}
            title={isMarathi ? 'तपशील' : 'Details'}
          >
            <span>{isMarathi ? 'तपशील' : 'Details'}</span>
            {showDetails ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        )}
      </div>
    </div>
  );
}

