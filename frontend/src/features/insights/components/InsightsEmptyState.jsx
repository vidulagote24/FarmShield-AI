/**
 * FarmShield AI - InsightsEmptyState Component
 * 
 * Displayed when no observation telemetry points exist for a farm,
 * or when selected date/zone filters yield zero matches.
 */

import React from 'react';
import { Activity, RotateCcw, ArrowLeft } from 'lucide-react';

export default function InsightsEmptyState({
  title,
  message,
  onResetFilters,
  onBack,
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';

  return (
    <div
      className="glass-card"
      style={{
        padding: '36px 20px',
        textAlign: 'center',
        background: 'rgba(7, 31, 22, 0.85)',
        border: '1px solid rgba(197, 243, 107, 0.35)',
        borderRadius: '20px',
        maxWidth: '460px',
        margin: '20px auto',
      }}
    >
      <div
        style={{
          width: '52px',
          height: '52px',
          borderRadius: '50%',
          background: 'rgba(197, 243, 107, 0.15)',
          color: '#C5F36B',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 16px auto',
        }}
      >
        <Activity size={26} />
      </div>

      <h3 style={{ fontSize: '17px', fontWeight: 800, color: '#FFFFFF', marginBottom: '8px' }}>
        {title || (isMarathi ? 'कोणतीही निरीक्षणे उपलब्ध नाहीत' : 'No Observations Recorded')}
      </h3>

      <p style={{ fontSize: '12.5px', color: '#B6C8BB', lineHeight: 1.5, marginBottom: '20px' }}>
        {message || (isMarathi 
          ? 'निवडलेल्या कालावधीत किंवा विभागात कोणतीही सेन्सर किंवा उपग्रह नोंद आढळली नाही.' 
          : 'No sensor or satellite observations found for the selected farm criteria.')}
      </p>

      <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
        {onResetFilters && (
          <button
            onClick={onResetFilters}
            className="btn-glass-primary"
            style={{
              padding: '8px 16px',
              fontSize: '12.5px',
              fontWeight: 700,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              cursor: 'pointer',
            }}
          >
            <RotateCcw size={14} />
            <span>{isMarathi ? 'फिल्टर रीसेट करा' : 'Reset Filters'}</span>
          </button>
        )}

        {onBack && (
          <button
            onClick={onBack}
            className="btn-glass-secondary"
            style={{
              padding: '8px 16px',
              fontSize: '12.5px',
              fontWeight: 700,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              cursor: 'pointer',
            }}
          >
            <ArrowLeft size={14} />
            <span>{isMarathi ? 'मागे जा' : 'Back'}</span>
          </button>
        )}
      </div>
    </div>
  );
}

