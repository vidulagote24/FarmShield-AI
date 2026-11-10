/**
 * FarmShield AI - DataFreshnessIndicator Component
 * 
 * Displays telemetry freshness, provenance, satellite source attribution,
 * and prominent demo/simulation status per AGENTS.md.
 */

import React from 'react';
import { Satellite, Clock, CheckCircle2, AlertTriangle, ShieldAlert } from 'lucide-react';

export default function DataFreshnessIndicator({
  isDemoMode = false,
  lastObservedAt = null,
  source = null,
  qualityStatus = 'good',
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';

  const formatTimestamp = (ts) => {
    if (!ts) return isMarathi ? 'निरीक्षण तारीख उपलब्ध नाही' : 'Date unavailable';
    try {
      const d = new Date(ts);
      return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } catch (e) {
      return String(ts);
    }
  };

  const getQualityBadge = () => {
    switch (qualityStatus) {
      case 'good':
        return {
          icon: CheckCircle2,
          color: '#22C55E',
          bg: 'rgba(34, 197, 94, 0.15)',
          border: 'rgba(34, 197, 94, 0.4)',
          text: isMarathi ? 'ताजा डेटा (Good)' : 'Fresh / Validated',
        };
      case 'partial':
      case 'stale':
        return {
          icon: AlertTriangle,
          color: '#F59E0B',
          bg: 'rgba(245, 158, 11, 0.15)',
          border: 'rgba(245, 158, 11, 0.4)',
          text: isMarathi ? 'अंशतः डेटा / जुना (Stale)' : 'Partial / Stale',
        };
      case 'insufficient':
      case 'suspect':
      default:
        return {
          icon: ShieldAlert,
          color: '#94A3B8',
          bg: 'rgba(148, 163, 184, 0.15)',
          border: 'rgba(148, 163, 184, 0.4)',
          text: isMarathi ? 'अपुरा डेटा (Insufficient)' : 'Insufficient Quality',
        };
    }
  };

  const quality = getQualityBadge();
  const QualityIcon = quality.icon;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        padding: '10px 14px',
        background: 'rgba(10, 43, 28, 0.60)',
        border: '1px solid rgba(255, 255, 255, 0.14)',
        borderRadius: '14px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#D5E3D9' }}>
          <Satellite size={14} color="#C5F36B" />
          <span style={{ fontWeight: 600 }}>{source || 'Copernicus Sentinel-2 L2A & In-situ Probes'}</span>
        </div>

        {/* Quality status badge */}
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            fontSize: '10.5px',
            fontWeight: 700,
            color: quality.color,
            background: quality.bg,
            border: `1px solid ${quality.border}`,
            padding: '2px 8px',
            borderRadius: '12px',
          }}
        >
          <QualityIcon size={11} />
          <span>{quality.text}</span>
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '10.5px', color: '#8E9F90', flexWrap: 'wrap', gap: '4px' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Clock size={11} />
          <span>{isMarathi ? 'अंतिम निरीक्षण:' : 'Last observed:'} {formatTimestamp(lastObservedAt)}</span>
        </span>

        {isDemoMode && (
          <span
            style={{
              fontSize: '10px',
              fontWeight: 800,
              color: '#FBBF24',
              background: 'rgba(245, 158, 11, 0.20)',
              border: '1px solid rgba(245, 158, 11, 0.50)',
              padding: '2px 7px',
              borderRadius: '8px',
            }}
          >
            🌾 DEMO DATA / SIMULATED
          </span>
        )}
      </div>
    </div>
  );
}

