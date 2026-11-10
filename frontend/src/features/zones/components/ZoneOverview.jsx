/**
 * FarmShield AI - ZoneOverview Component
 * 
 * Header summary of the focused zone: name, stable UUID, crop identity,
 * cadastral area, parent farm association, and machine-classified status.
 */

import React from 'react';
import { ArrowLeft, MapPin, Layers, Calendar, CheckCircle2, AlertTriangle, AlertCircle, HelpCircle } from 'lucide-react';

const STATUS_TOKENS = {
  healthy: {
    color: '#22C55E',
    label_en: 'Healthy / Adequate',
    label_mr: 'उत्तम / पुरेसा ओलावा',
    bg: 'rgba(34, 197, 94, 0.18)',
    border: 'rgba(34, 197, 94, 0.50)',
    icon: CheckCircle2,
  },
  monitor: {
    color: '#F59E0B',
    label_en: 'Monitor / Watch',
    label_mr: 'निरीक्षण आवश्यक',
    bg: 'rgba(245, 158, 11, 0.18)',
    border: 'rgba(245, 158, 11, 0.50)',
    icon: AlertTriangle,
  },
  attention: {
    color: '#EF4444',
    label_en: 'Action Required',
    label_mr: 'तातडीने लक्ष द्या',
    bg: 'rgba(239, 68, 68, 0.18)',
    border: 'rgba(239, 68, 68, 0.50)',
    icon: AlertCircle,
  },
  high_stress: {
    color: '#DC2626',
    label_en: 'High Stress',
    label_mr: 'गंभीर ताण',
    bg: 'rgba(220, 38, 38, 0.22)',
    border: 'rgba(220, 38, 38, 0.60)',
    icon: AlertCircle,
  },
  insufficient_data: {
    color: '#94A3B8',
    label_en: 'Insufficient Data',
    label_mr: 'अपुरा डेटा',
    bg: 'rgba(148, 163, 184, 0.18)',
    border: 'rgba(148, 163, 184, 0.45)',
    icon: HelpCircle,
  },
};

export default function ZoneOverview({
  zone,
  farm,
  status = null,
  onBack,
  currentLang = 'mr',
  isDemoMode = false,
  onToggleDataMode,
}) {
  const isMarathi = currentLang === 'mr';
  if (!zone) return null;

  const effectiveStatus = status || zone.status || 'insufficient_data';
  const token = STATUS_TOKENS[effectiveStatus] || STATUS_TOKENS.insufficient_data;
  const StatusIcon = token.icon;

  const cropName = zone.crop || zone.metadata?.crop || farm?.crop_type || farm?.crop || (isMarathi ? 'माहिती उपलब्ध नाही' : 'Crop unrecorded');
  const areaAcres = zone.area_acres || (zone.area_hectares ? +(zone.area_hectares * 2.471).toFixed(2) : null);
  const areaHa = zone.area_hectares || (zone.area_acres ? +(zone.area_acres / 2.471).toFixed(2) : null);

  const farmName = farm?.name || farm?.name_en || (isMarathi ? 'शेत' : 'Farm');
  const farmLocation = farm?.location_name || (isMarathi ? 'बारामती, पुणे' : 'Baramati, Pune');

  return (
    <div
      className="glass-card"
      style={{
        padding: '18px',
        background: 'rgba(10, 43, 28, 0.75)',
        border: '1.5px solid rgba(197, 243, 107, 0.35)',
        boxShadow: '0 10px 30px rgba(0, 0, 0, 0.35)',
      }}
    >
      {/* Top Navigation Row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        {onBack && (
          <button
            onClick={onBack}
            className="btn-glass-secondary"
            style={{
              padding: '6px 12px',
              fontSize: '12px',
              minHeight: '34px',
              color: '#FFFFFF',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <ArrowLeft size={15} />
            <span>{isMarathi ? 'नकाशावर परत जा' : 'Back to Farm Map'}</span>
          </button>
        )}

        {/* Live / Demo Mode Toggle */}
        {onToggleDataMode && (
          <button
            onClick={onToggleDataMode}
            title={isMarathi ? 'डेटा मोड बदला' : 'Toggle Data Mode'}
            style={{
              padding: '4px 10px',
              borderRadius: '20px',
              border: isDemoMode ? '1px solid #F59E0B' : '1px solid #65C76A',
              background: isDemoMode ? 'rgba(245, 158, 11, 0.20)' : 'rgba(101, 199, 106, 0.20)',
              color: isDemoMode ? '#FBBF24' : '#C5F36B',
              fontSize: '11px',
              fontWeight: 800,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
            }}
          >
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: isDemoMode ? '#FBBF24' : '#65C76A' }} />
            <span>{isDemoMode ? 'DEMO MODE' : 'LIVE API'}</span>
          </button>
        )}
      </div>

      {/* Main Title & Status Badge */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '10px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span style={{ fontSize: '12px', fontWeight: 800, color: '#C5F36B', letterSpacing: '0.3px' }}>
              📍 {zone.zone_code || 'ZONE'}
            </span>
            <span
              className="status-pill"
              style={{
                fontSize: '11px',
                padding: '3px 9px',
                color: token.color,
                background: token.bg,
                border: `1px solid ${token.border}`,
              }}
            >
              <StatusIcon size={12} />
              <span>{isMarathi ? token.label_mr : token.label_en}</span>
            </span>
          </div>

          <h2 style={{ fontSize: '20px', fontWeight: 800, color: '#FFFFFF', letterSpacing: '-0.3px', margin: 0 }}>
            {zone.zone_name}
          </h2>

          <div style={{ fontSize: '11px', color: '#8E9F90', marginTop: '4px', fontFamily: 'monospace' }}>
            ID: {zone.id}
          </div>
        </div>
      </div>

      {/* Meta Properties Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: '8px',
          marginTop: '14px',
        }}
      >
        <div className="glass-panel" style={{ padding: '8px 10px' }}>
          <div style={{ fontSize: '10.5px', color: '#B6C8BB' }}>{isMarathi ? 'पीक' : 'Crop'}</div>
          <div style={{ fontSize: '13px', fontWeight: 700, color: '#FFFFFF', marginTop: '2px' }}>
            🌾 {cropName}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '8px 10px' }}>
          <div style={{ fontSize: '10.5px', color: '#B6C8BB' }}>{isMarathi ? 'क्षेत्रफळ' : 'Area'}</div>
          <div style={{ fontSize: '13px', fontWeight: 700, color: '#FFFFFF', marginTop: '2px' }}>
            📏 {areaAcres ? `${areaAcres} ${isMarathi ? 'एकर' : 'Ac'}` : (areaHa ? `${areaHa} ha` : '—')}
            {areaHa && areaAcres && (
              <span style={{ fontSize: '10px', color: '#8E9F90', marginLeft: '4px' }}>({areaHa} ha)</span>
            )}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '8px 10px' }}>
          <div style={{ fontSize: '10.5px', color: '#B6C8BB' }}>{isMarathi ? 'शेत व स्थान' : 'Parent Farm'}</div>
          <div style={{ fontSize: '12px', fontWeight: 700, color: '#FFFFFF', marginTop: '2px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            🏡 {farmName}
          </div>
          <div style={{ fontSize: '9.5px', color: '#8E9F90' }}>
            {farmLocation}
          </div>
        </div>
      </div>
    </div>
  );
}

