/**
 * FarmShield AI - InsightsDataFreshness Component
 * 
 * Displays telemetry audit and cadence status for ground capacitive probes
 * and Copernicus Sentinel-2 multispectral satellite passes.
 */

import React from 'react';
import { Clock, ShieldCheck, Satellite, Gauge, CheckCircle2 } from 'lucide-react';

export default function InsightsDataFreshness({
  latestObservedAt,
  totalObservations = 0,
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';

  const formatTimestamp = (d) => {
    if (!d) return isMarathi ? 'माहिती उपलब्ध नाही' : 'No records';
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
        border: '1px solid rgba(197, 243, 107, 0.25)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
        <div
          style={{
            width: '28px',
            height: '28px',
            borderRadius: '6px',
            background: 'rgba(197, 243, 107, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#C5F36B',
          }}
        >
          <ShieldCheck size={16} />
        </div>
        <div>
          <h4 style={{ fontSize: '14px', fontWeight: 800, color: '#FFFFFF', margin: 0 }}>
            {isMarathi ? 'डेटा स्त्रोत व ताजेपणा (Telemetry Sources & Cadence)' : 'Telemetry Sources & Quality'}
          </h4>
          <div style={{ fontSize: '11px', color: '#B6C8BB' }}>
            {isMarathi ? 'माती सेन्सर व उपग्रह निरीक्षण चक्र' : 'Ground sensors and satellite revisit frequency'}
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px' }}>
        {/* Source 1: Ground Soil Probes */}
        <div
          style={{
            padding: '10px 12px',
            background: 'rgba(56, 189, 248, 0.08)',
            border: '1px solid rgba(56, 189, 248, 0.25)',
            borderRadius: '10px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#38BDF8', fontSize: '11px', fontWeight: 700, marginBottom: '4px' }}>
            <Gauge size={13} />
            <span>{isMarathi ? 'जमिनीतील कॅपॅसिटिव्ह सेन्सर' : 'In-Situ Capacitive Probes'}</span>
          </div>
          <div style={{ fontSize: '11.5px', color: '#E2E8F0', lineHeight: 1.4 }}>
            {isMarathi ? '३० सेमी खोलीवर दर २४-४८ तासांनी प्रत्यक्ष ओलावा नोंदणी.' : 'Root-zone moisture measured at 30cm depth.'}
          </div>
        </div>

        {/* Source 2: Sentinel-2 Satellite */}
        <div
          style={{
            padding: '10px 12px',
            background: 'rgba(197, 243, 107, 0.08)',
            border: '1px solid rgba(197, 243, 107, 0.25)',
            borderRadius: '10px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#C5F36B', fontSize: '11px', fontWeight: 700, marginBottom: '4px' }}>
            <Satellite size={13} />
            <span>{isMarathi ? 'कोपरनिकस सेंटिनेल-२ उपग्रह' : 'Copernicus Sentinel-2 (ESA)'}</span>
          </div>
          <div style={{ fontSize: '11.5px', color: '#E2E8F0', lineHeight: 1.4 }}>
            {isMarathi ? '१० मीटर रिझोल्यूशन, दर ५ दिवसांनी निरभ्र आकाशात NDVI नोंद.' : '10m resolution canopy index with 5-day revisit.'}
          </div>
        </div>
      </div>
    </div>
  );
}

