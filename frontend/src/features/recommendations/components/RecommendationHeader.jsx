/**
 * FarmShield AI - RecommendationHeader Component
 * 
 * Header displaying recommendation title, zone context, priority badge,
 * workflow status, and mode switcher (Live API vs Demo Mode).
 */

import React from 'react';
import { ArrowLeft, Clock, MapPin, Zap, Database, Calendar } from 'lucide-react';
import RecommendationPriorityBadge from './RecommendationPriorityBadge.jsx';

export default function RecommendationHeader({
  recommendation,
  zone,
  farm,
  onBack,
  currentLang = 'mr',
  isDemoMode = false,
  onToggleMode,
}) {
  const isMarathi = currentLang === 'mr';

  const formatTimestamp = (ts) => {
    if (!ts) return isMarathi ? 'अज्ञात' : 'Unknown';
    try {
      const d = new Date(ts);
      return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } catch {
      return ts;
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'accepted':
      case 'acknowledged':
        return { text_mr: 'मान्य (Acknowledged)', text_en: 'Acknowledged', color: '#38BDF8', bg: 'rgba(56, 189, 248, 0.18)' };
      case 'applied':
      case 'completed':
        return { text_mr: 'पूर्ण (Applied)', text_en: 'Applied', color: '#4ADE80', bg: 'rgba(74, 222, 128, 0.18)' };
      case 'dismissed':
      case 'rejected':
        return { text_mr: 'रद्द (Dismissed)', text_en: 'Dismissed', color: '#94A3B8', bg: 'rgba(148, 163, 184, 0.18)' };
      case 'expired':
        return { text_mr: 'कालबाह्य (Expired)', text_en: 'Expired', color: '#F87171', bg: 'rgba(248, 113, 113, 0.18)' };
      case 'pending':
      default:
        return { text_mr: 'प्रलंबित (Pending)', text_en: 'Pending Review', color: '#FBBF24', bg: 'rgba(251, 191, 36, 0.18)' };
    }
  };

  const statusInfo = getStatusLabel(recommendation?.status);

  return (
    <div
      className="glass-card"
      style={{
        padding: '16px 18px',
        marginBottom: '16px',
        background: 'rgba(7, 31, 22, 0.85)',
        border: '1px solid rgba(197, 243, 107, 0.35)',
      }}
    >
      {/* Top Controls: Back Button & Mode Indicator */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <button
          onClick={onBack}
          className="btn-glass-secondary"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 12px',
            fontSize: '12px',
            fontWeight: 700,
            color: '#FFFFFF',
            cursor: 'pointer',
          }}
          aria-label={isMarathi ? 'मागे जा' : 'Go back'}
        >
          <ArrowLeft size={14} color="#C5F36B" />
          <span>{isMarathi ? 'मागे जा' : 'Back'}</span>
        </button>

        {/* Live / Demo Mode Badge */}
        <button
          onClick={onToggleMode}
          className="glass-pill"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '5px',
            fontSize: '11px',
            fontWeight: 800,
            cursor: 'pointer',
            padding: '4px 10px',
            border: isDemoMode ? '1px solid rgba(197, 243, 107, 0.5)' : '1px solid rgba(56, 189, 248, 0.5)',
            color: isDemoMode ? '#C5F36B' : '#38BDF8',
            background: isDemoMode ? 'rgba(197, 243, 107, 0.15)' : 'rgba(56, 189, 248, 0.15)',
          }}
          title={isMarathi ? 'डेटा मोड बदला' : 'Toggle Live API / Demo Mode'}
        >
          {isDemoMode ? <Database size={12} /> : <Zap size={12} />}
          <span>{isDemoMode ? 'DEMO MODE' : 'LIVE API'}</span>
        </button>
      </div>

      {/* Zone Context & Metadata */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '11px', fontWeight: 800, color: '#C5F36B', display: 'flex', alignItems: 'center', gap: '3px' }}>
          <MapPin size={12} />
          {zone ? `${zone.zone_code || 'ZONE'} • ${zone.zone_name || zone.name}` : (isMarathi ? 'शेत पातळीवरील सल्ला' : 'Farm-wide Advisory')}
        </span>
        {farm && (
          <span style={{ fontSize: '11px', color: '#8E9F90' }}>
            ({farm.name})
          </span>
        )}
      </div>

      {/* Main Title */}
      <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#FFFFFF', margin: '0 0 10px 0', lineHeight: 1.35 }}>
        {isMarathi ? (recommendation?.title || recommendation?.title_en) : (recommendation?.title_en || recommendation?.title)}
      </h2>

      {/* Badges Row: Priority & Status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '10px' }}>
        <RecommendationPriorityBadge priority={recommendation?.priority} currentLang={currentLang} size="md" />

        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '5px',
            padding: '4px 10px',
            borderRadius: '20px',
            background: statusInfo.bg,
            border: `1px solid ${statusInfo.color}`,
            color: statusInfo.color,
            fontSize: '11.5px',
            fontWeight: 800,
            textTransform: 'uppercase',
          }}
        >
          <span>{isMarathi ? statusInfo.text_mr : statusInfo.text_en}</span>
        </span>
      </div>

      {/* Timestamp Row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '11px', color: '#94A3B8', flexWrap: 'wrap' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Clock size={12} />
          <span>{isMarathi ? 'निर्मिती:' : 'Generated:'} {formatTimestamp(recommendation?.generated_at)}</span>
        </span>
        {recommendation?.valid_until && (
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Calendar size={12} />
            <span>{isMarathi ? 'वैधता:' : 'Valid until:'} {formatTimestamp(recommendation.valid_until)}</span>
          </span>
        )}
      </div>
    </div>
  );
}

