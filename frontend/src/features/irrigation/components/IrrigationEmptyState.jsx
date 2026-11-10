/**
 * FarmShield AI - IrrigationEmptyState Component
 * 
 * Reusable placeholder for empty recommendations, empty history,
 * or zones without actionable water deficits.
 */

import React from 'react';
import { DropletOff, Calendar, ShieldCheck, Info } from 'lucide-react';

export default function IrrigationEmptyState({
  title,
  message,
  reason,
  icon: CustomIcon,
  currentLang = 'mr',
  compact = false,
}) {
  const isMarathi = currentLang === 'mr';
  const IconComponent = CustomIcon || DropletOff;

  if (compact) {
    return (
      <div
        className="glass-panel"
        style={{
          padding: '12px 14px',
          border: '1px dashed rgba(255, 255, 255, 0.20)',
          background: 'rgba(255, 255, 255, 0.04)',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          borderRadius: '14px',
        }}
      >
        <div style={{ color: '#94A3B8', flexShrink: 0 }}>
          <IconComponent size={20} />
        </div>
        <div style={{ fontSize: '12px', color: '#CBD5E1', lineHeight: 1.4 }}>
          {message || (isMarathi ? 'माहिती उपलब्ध नाही' : 'No records available')}
        </div>
      </div>
    );
  }

  return (
    <div
      className="glass-card"
      style={{
        padding: '22px 18px',
        border: '1.5px dashed rgba(148, 163, 184, 0.35)',
        background: 'rgba(10, 43, 28, 0.55)',
        borderRadius: '18px',
        textAlign: 'center',
      }}
    >
      <div
        style={{
          width: '44px',
          height: '44px',
          borderRadius: '50%',
          background: 'rgba(148, 163, 184, 0.15)',
          color: '#94A3B8',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 10px',
        }}
      >
        <IconComponent size={24} />
      </div>

      <h4 style={{ fontSize: '15px', fontWeight: 800, color: '#E2E8F0', marginBottom: '4px' }}>
        {title || (isMarathi ? 'कोणतीही नोंद नाही' : 'No Records Found')}
      </h4>

      <p style={{ fontSize: '12.5px', color: '#94A3B8', lineHeight: 1.45, maxWidth: '360px', margin: '0 auto' }}>
        {message || (isMarathi 
          ? 'या निवडीसाठी कोणतीही सक्रिय सिंचन शिफारस किंवा इतिहास सापडला नाही.' 
          : 'No active recommendations or recorded events found for this selection.')}
      </p>

      {reason && (
        <div
          style={{
            marginTop: '12px',
            padding: '8px 12px',
            background: 'rgba(255, 255, 255, 0.05)',
            borderRadius: '10px',
            fontSize: '11px',
            color: '#CBD5E1',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            border: '1px solid rgba(255, 255, 255, 0.10)',
          }}
        >
          <Info size={13} color="#C5F36B" />
          <span>{reason}</span>
        </div>
      )}
    </div>
  );
}

