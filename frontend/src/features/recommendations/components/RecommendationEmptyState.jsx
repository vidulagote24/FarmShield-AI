/**
 * FarmShield AI - RecommendationEmptyState Component
 * 
 * Displayed when a recommendation is not found, was deleted,
 * or when an invalid identifier is provided.
 */

import React from 'react';
import { HelpCircle, ArrowLeft, ShieldAlert } from 'lucide-react';

export default function RecommendationEmptyState({
  title,
  message,
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
          width: '54px',
          height: '54px',
          borderRadius: '50%',
          background: 'rgba(197, 243, 107, 0.15)',
          color: '#C5F36B',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 16px auto',
        }}
      >
        <HelpCircle size={28} />
      </div>

      <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#FFFFFF', marginBottom: '8px' }}>
        {title || (isMarathi ? 'सल्ला सापडला नाही' : 'Recommendation Not Found')}
      </h3>

      <p style={{ fontSize: '13px', color: '#B6C8BB', lineHeight: 1.5, marginBottom: '22px' }}>
        {message || (isMarathi 
          ? 'निवडलेला शिफारस क्रमांक डेटाबेसमध्ये उपलब्ध नाही किंवा तो काढून टाकण्यात आला आहे.' 
          : 'The requested recommendation ID does not exist in the database or could not be loaded.')}
      </p>

      {onBack && (
        <button
          onClick={onBack}
          className="btn-glass-primary"
          style={{
            minHeight: '40px',
            padding: '8px 20px',
            fontSize: '13px',
            fontWeight: 700,
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            cursor: 'pointer',
          }}
        >
          <ArrowLeft size={16} />
          <span>{isMarathi ? 'मागे जा (Go Back)' : 'Return to Overview'}</span>
        </button>
      )}
    </div>
  );
}

