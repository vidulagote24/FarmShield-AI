/**
 * FarmShield AI - RecommendationDataFreshness Component
 * 
 * Displays telemetry freshness and advisory expiry information.
 * Highlights stale or expired advisories so farmers do not act on outdated guidance.
 */

import React from 'react';
import { Clock, AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react';

export default function RecommendationDataFreshness({
  generatedAt,
  validUntil,
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';

  const now = new Date();
  const genDate = generatedAt ? new Date(generatedAt) : null;
  const expDate = validUntil ? new Date(validUntil) : null;

  const isExpired = expDate ? now > expDate : false;
  
  // Hours since generation
  const hoursSinceGen = genDate ? Math.max(0, Math.round((now - genDate) / (1000 * 60 * 60))) : null;

  // Freshness status
  let freshnessStatus = 'fresh'; // 'fresh' | 'aging' | 'stale' | 'expired'
  if (isExpired) {
    freshnessStatus = 'expired';
  } else if (hoursSinceGen !== null) {
    if (hoursSinceGen > 48) freshnessStatus = 'stale';
    else if (hoursSinceGen > 24) freshnessStatus = 'aging';
    else freshnessStatus = 'fresh';
  }

  const formatTimestamp = (d) => {
    if (!d) return null;
    return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  };

  const getStatusDisplay = () => {
    switch (freshnessStatus) {
      case 'expired':
        return {
          color: '#EF4444',
          bg: 'rgba(239, 68, 68, 0.15)',
          border: 'rgba(239, 68, 68, 0.45)',
          icon: AlertTriangle,
          label_mr: 'कालबाह्य (Expired)',
          label_en: 'Expired Advisory',
          desc_mr: 'या सल्ल्याची मुदत संपली आहे. शेतातील हवामान व मातीतील ओलावा बदलला असण्याची शक्यता आहे. नवीन डेटाची वाट पहा.',
          desc_en: 'This recommendation has expired. Field conditions may have changed significantly.',
        };
      case 'stale':
        return {
          color: '#F59E0B',
          bg: 'rgba(245, 158, 11, 0.15)',
          border: 'rgba(245, 158, 11, 0.45)',
          icon: ShieldAlert,
          label_mr: 'जुना सल्ला (> ४८ तास)',
          label_en: 'Aging Advisory (> 48h)',
          desc_mr: 'हा सल्ला ४८ तासांपेक्षा जास्त जुना आहे. प्रत्यक्ष शेतात जाऊन ओलावा तपासणे आवश्यक आहे.',
          desc_en: 'Advisory was generated over 48 hours ago. Re-verify soil conditions before acting.',
        };
      case 'aging':
        return {
          color: '#FBBF24',
          bg: 'rgba(251, 191, 36, 0.15)',
          border: 'rgba(251, 191, 36, 0.45)',
          icon: Clock,
          label_mr: 'मध्यम ताजेपणा (२४-४८ तास)',
          label_en: 'Valid (24-48h old)',
          desc_mr: 'सल्ला वैध आहे, परंतु मुदत संपण्यापूर्वी अंमलबजावणी करा.',
          desc_en: 'Advisory remains valid, but act within the active window.',
        };
      case 'fresh':
      default:
        return {
          color: '#22C55E',
          bg: 'rgba(34, 197, 94, 0.15)',
          border: 'rgba(34, 197, 94, 0.45)',
          icon: CheckCircle2,
          label_mr: 'अतिशय ताजा डेटा (< २४ तास)',
          label_en: 'Fresh & Active (< 24h)',
          desc_mr: 'सल्ला नुकताच मिळालेल्या सेन्सर व उपग्रह डेटावर आधारित असून पूर्णपणे अद्ययावत आहे.',
          desc_en: 'Advisory is based on recent telemetry and remains highly relevant.',
        };
    }
  };

  const statusConfig = getStatusDisplay();
  const IconComp = statusConfig.icon;

  return (
    <div
      className="glass-card"
      style={{
        padding: '16px 18px',
        marginBottom: '16px',
        background: 'rgba(7, 31, 22, 0.85)',
        border: `1px solid ${statusConfig.border}`,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '10px', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '8px',
              background: statusConfig.bg,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: statusConfig.color,
            }}
          >
            <IconComp size={16} />
          </div>
          <div>
            <h4 style={{ fontSize: '14px', fontWeight: 800, color: '#FFFFFF', margin: 0 }}>
              {isMarathi ? 'माहितीचा ताजेपणा (Data Freshness)' : 'Data Freshness & Validity'}
            </h4>
            <div style={{ fontSize: '11px', color: statusConfig.color, fontWeight: 700, marginTop: '1px' }}>
              {isMarathi ? statusConfig.label_mr : statusConfig.label_en}
            </div>
          </div>
        </div>

        {hoursSinceGen !== null && (
          <span style={{ fontSize: '11px', color: '#94A3B8' }}>
            {hoursSinceGen} {isMarathi ? 'तासांपूर्वी' : 'hrs ago'}
          </span>
        )}
      </div>

      <p style={{ fontSize: '12px', color: '#CBD5E1', lineHeight: 1.45, margin: '0 0 10px 0' }}>
        {isMarathi ? statusConfig.desc_mr : statusConfig.desc_en}
      </p>

      {/* Timestamp details */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', fontSize: '11px', color: '#8E9F90', paddingTop: '8px', borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
        {genDate && (
          <span>
            {isMarathi ? 'सल्ला निर्मिती:' : 'Generated:'} <strong style={{ color: '#FFFFFF' }}>{formatTimestamp(genDate)}</strong>
          </span>
        )}
        {expDate && (
          <span>
            {isMarathi ? 'वैधता समाप्ती:' : 'Valid until:'} <strong style={{ color: isExpired ? '#EF4444' : '#C5F36B' }}>{formatTimestamp(expDate)}</strong>
          </span>
        )}
      </div>
    </div>
  );
}

