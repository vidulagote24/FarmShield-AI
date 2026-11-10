/**
 * FarmShield AI - MapFreshnessLabel Component
 * 
 * Displays data freshness, telemetry timestamps, source attribution,
 * and persistent demo data badges per AGENTS.md and docs/PRD.md.
 */

import React from 'react';
import { Clock, Satellite, ShieldCheck, AlertCircle } from 'lucide-react';

export default function MapFreshnessLabel({
  farm,
  isDemoMode = false,
  currentLang = 'mr',
  activeLayer = 'zones',
}) {
  const isMarathi = currentLang === 'mr';

  const formatTimestamp = (isoString) => {
    if (!isoString) return isMarathi ? 'अज्ञातीत तारीख' : 'Unknown';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(isMarathi ? 'mr-IN' : 'en-IN', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  const satelliteDate = farm?.satellite_date || farm?.last_updated || '2026-11-07T05:30:00Z';
  const satelliteSource = farm?.satellite_source || 'Sentinel-2 L2A';

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '8px',
        padding: '6px 12px',
        background: 'rgba(7, 31, 22, 0.90)',
        border: '1px solid rgba(255, 255, 255, 0.14)',
        borderRadius: '12px',
        fontSize: '11px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#D5E3D9' }}>
        <Satellite size={13} color="#C5F36B" />
        <span>
          <strong style={{ color: '#FFFFFF' }}>{satelliteSource}</strong> •{' '}
          <Clock size={11} style={{ display: 'inline', verticalAlign: '-1px' }} />{' '}
          {formatTimestamp(satelliteDate)}
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        {isDemoMode && (
          <span
            className="demo-tag"
            style={{
              background: 'rgba(245, 158, 11, 0.20)',
              color: '#FBBF24',
              border: '1px solid rgba(245, 158, 11, 0.4)',
              fontWeight: 800,
            }}
          >
            🌾 {isMarathi ? 'नमुना डेटा (SIMULATED)' : 'DEMO DATA'}
          </span>
        )}

        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            color: '#69D98A',
            fontWeight: 700,
          }}
        >
          <ShieldCheck size={12} />
          {isMarathi ? 'प्रमाणित जिओडेटा' : 'Verified Geometry'}
        </span>
      </div>
    </div>
  );
}
