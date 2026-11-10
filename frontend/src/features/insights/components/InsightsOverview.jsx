/**
 * FarmShield AI - InsightsOverview Component
 * 
 * Top-level summary header for the Farm Insights dashboard.
 * Displays farm dimensions, active zones, total verified observations,
 * and data source mode toggle (Live API vs Demo Mode).
 */

import React from 'react';
import { TrendingUp, ArrowLeft, Database, Zap, MapPin, Calendar, Clock, Layers } from 'lucide-react';

export default function InsightsOverview({
  farm,
  zones = [],
  totalObservations = 0,
  latestObservedAt,
  isDemoMode = false,
  onToggleMode,
  onBack,
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';

  const formatTimestamp = (d) => {
    if (!d) return isMarathi ? 'नोंद नाही' : 'No records';
    try {
      const date = typeof d === 'string' ? new Date(d) : d;
      return `${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } catch {
      return String(d);
    }
  };

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
      {/* Top Controls: Back Button & Mode Toggle */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        {onBack && (
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
        )}

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
          <span>{isDemoMode ? 'DEMO MODE (SIMULATED)' : 'LIVE REST API'}</span>
        </button>
      </div>

      {/* Title & Farm Overview */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '10px', flexWrap: 'wrap' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
            <span
              style={{
                width: '26px',
                height: '26px',
                borderRadius: '6px',
                background: 'rgba(197, 243, 107, 0.18)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#C5F36B',
              }}
            >
              <TrendingUp size={16} />
            </span>
            <span style={{ fontSize: '11.5px', fontWeight: 800, color: '#C5F36B', textTransform: 'uppercase' }}>
              {farm?.name || (isMarathi ? 'शेत विश्लेषण' : 'Farm Telemetry')}
            </span>
          </div>

          <h2 style={{ fontSize: '19px', fontWeight: 800, color: '#FFFFFF', margin: '0 0 6px 0', letterSpacing: '-0.3px' }}>
            {isMarathi ? 'शेत निरीक्षणे व कल विश्लेषण' : 'Farm Insights & Historical Trends'}
          </h2>

          <p style={{ fontSize: '12.5px', color: '#B6C8BB', margin: 0, lineHeight: 1.45 }}>
            {isMarathi 
              ? 'प्रत्यक्ष सेन्सर नोंदी, मातीतील ओलावा आणि उपग्रहावरून मिळालेला पीक वाढीचा कल.' 
              : 'Direct sensor telemetry, soil moisture depletion, and multispectral vegetation trends.'}
          </p>
        </div>
      </div>

      {/* Metadata Badges Ribbon */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '12px',
          marginTop: '14px',
          paddingTop: '12px',
          borderTop: '1px solid rgba(255, 255, 255, 0.08)',
          fontSize: '11.5px',
          color: '#CBD5E1',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <MapPin size={13} color="#C5F36B" />
          <span>{farm?.total_area_hectares ? `${farm.total_area_hectares} ha (${(farm.total_area_hectares * 2.471).toFixed(1)} एकर)` : (farm?.area ? `${farm.area} एकर` : '3.5 एकर')}</span>
        </span>

        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Layers size={13} color="#38BDF8" />
          <span>{zones.length} {isMarathi ? 'व्यवस्थापन विभाग' : 'Management Zones'}</span>
        </span>

        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Clock size={13} color="#FBBF24" />
          <span>{isMarathi ? 'शेवटची नोंद:' : 'Latest:'} {formatTimestamp(latestObservedAt)}</span>
        </span>
      </div>
    </div>
  );
}

