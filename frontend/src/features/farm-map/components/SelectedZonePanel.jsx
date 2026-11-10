/**
 * FarmShield AI - SelectedZonePanel Component
 * 
 * Progressive disclosure inspection panel for the actively focused zone polygon.
 * Surfaces evidence trace, vegetation indices, root-zone moisture, and decision rule reasons.
 */

import React from 'react';
import { 
  X, 
  Layers, 
  Activity, 
  Droplets, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  Satellite, 
  ArrowRight,
  ShieldAlert,
  Info
} from 'lucide-react';
import { STATUS_CONFIG } from './MapLegend.jsx';

export default function SelectedZonePanel({
  zone,
  onClose,
  onViewZoneDetails,
  currentLang = 'mr',
}) {
  if (!zone) return null;

  const isMarathi = currentLang === 'mr';
  const statusConfig = STATUS_CONFIG[zone.status] || STATUS_CONFIG.insufficient_data;
  const StatusIcon = statusConfig.icon;

  return (
    <div
      className="glass-card"
      style={{
        padding: '16px 18px',
        border: '1.5px solid rgba(197, 243, 107, 0.4)',
        background: 'rgba(7, 31, 22, 0.94)',
        boxShadow: '0 12px 32px rgba(0, 0, 0, 0.45), 0 0 20px rgba(197, 243, 107, 0.15)',
        borderRadius: '20px',
        position: 'relative',
        zIndex: 20,
      }}
    >
      {/* Header with Title, Status & Close Button */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: 800, color: '#C5F36B' }}>
              📍 {zone.zone_code || 'ZONE'}
            </span>
            <span
              className="status-pill"
              style={{
                fontSize: '11px',
                padding: '2px 8px',
                color: statusConfig.color,
                background: statusConfig.badgeBg,
                border: `1px solid ${statusConfig.badgeBorder}60`,
              }}
            >
              <StatusIcon size={12} />
              <span>{isMarathi ? statusConfig.label_mr : statusConfig.label_en}</span>
            </span>
          </div>
          <h3 style={{ fontSize: '17px', fontWeight: 800, color: '#FFFFFF', marginTop: '3px' }}>
            {zone.zone_name}
          </h3>
        </div>

        <button
          onClick={onClose}
          style={{
            background: 'rgba(255, 255, 255, 0.10)',
            border: '1px solid rgba(255, 255, 255, 0.18)',
            borderRadius: '50%',
            width: '30px',
            height: '30px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#FFFFFF',
            cursor: 'pointer',
          }}
          aria-label="Close"
        >
          <X size={16} />
        </button>
      </div>

      {/* Grid of Key Metrics */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '8px',
          marginBottom: '12px',
        }}
      >
        <div className="glass-panel" style={{ padding: '8px 10px', textAlign: 'center' }}>
          <div style={{ fontSize: '10.5px', color: '#B6C8BB' }}>{isMarathi ? 'क्षेत्रफळ' : 'Area'}</div>
          <div style={{ fontSize: '13.5px', fontWeight: 800, color: '#FFFFFF', marginTop: '2px' }}>
            {zone.area_acres || (zone.area_hectares ? +(zone.area_hectares * 2.471).toFixed(2) : '—')}
            <span style={{ fontSize: '10px', color: '#C5F36B', marginLeft: '2px' }}>
              {isMarathi ? 'एकर' : 'Ac'}
            </span>
          </div>
          {zone.area_hectares && (
            <div style={{ fontSize: '9px', color: '#8A97A5' }}>({zone.area_hectares} ha)</div>
          )}
        </div>

        <div className="glass-panel" style={{ padding: '8px 10px', textAlign: 'center' }}>
          <div style={{ fontSize: '10.5px', color: '#B6C8BB' }}>NDVI {isMarathi ? 'इंडेक्स' : 'Index'}</div>
          <div
            style={{
              fontSize: '13.5px',
              fontWeight: 800,
              color: zone.ndvi_value !== null ? '#65C76A' : '#8A97A5',
              marginTop: '2px',
            }}
          >
            {zone.ndvi_value !== null ? zone.ndvi_value : '—'}
          </div>
          <div style={{ fontSize: '9px', color: '#8A97A5' }}>
            {zone.ndvi_trend ? (isMarathi ? 'ट्रेंड: ' + zone.ndvi_trend : zone.ndvi_trend) : 'Sentinel-2'}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '8px 10px', textAlign: 'center' }}>
          <div style={{ fontSize: '10.5px', color: '#B6C8BB' }}>{isMarathi ? 'माती ओलावा' : 'Soil Moisture'}</div>
          <div
            style={{
              fontSize: '13.5px',
              fontWeight: 800,
              color: zone.soil_moisture_pct !== null ? '#38BDF8' : '#8A97A5',
              marginTop: '2px',
            }}
          >
            {zone.soil_moisture_pct !== null ? `${zone.soil_moisture_pct}%` : '—'}
          </div>
          <div style={{ fontSize: '9px', color: '#8A97A5' }}>
            {isMarathi ? 'ताण मर्यादा: ४५%' : 'Threshold: 45%'}
          </div>
        </div>
      </div>

      {/* Agronomic Summary / Reason Box */}
      {zone.reason_summary && (
        <div
          style={{
            padding: '10px 12px',
            background: 'rgba(255, 255, 255, 0.06)',
            borderRadius: '12px',
            border: '1px solid rgba(255, 255, 255, 0.10)',
            marginBottom: '12px',
            fontSize: '12px',
            color: '#D5E3D9',
            lineHeight: 1.45,
          }}
        >
          <div style={{ fontWeight: 700, color: '#C5F36B', marginBottom: '3px', display: 'flex', alignItems: 'center', gap: '5px' }}>
            <Info size={13} />
            {isMarathi ? 'कृषी सल्ला व निरीक्षण (Agronomic Summary):' : 'Agronomic Assessment:'}
          </div>
          <p style={{ margin: 0 }}>{zone.reason_summary}</p>
        </div>
      )}

      {/* Telemetry Provenance */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '10.5px',
          color: '#A3B8A8',
          marginBottom: '12px',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Satellite size={12} />
          {zone.evidence_source || 'Sentinel-2 L2A'}
        </span>
        {zone.last_observed_at && (
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Clock size={11} />
            {new Date(zone.last_observed_at).toLocaleDateString()}
          </span>
        )}
      </div>

      {/* Action Button */}
      {onViewZoneDetails && (
        <button
          onClick={() => onViewZoneDetails(zone)}
          className="btn-glass-secondary"
          style={{
            fontSize: '12.5px',
            minHeight: '40px',
            color: '#C5F36B',
            borderColor: 'rgba(197, 243, 107, 0.35)',
          }}
        >
          <span>{isMarathi ? 'या विभागाचे संपूर्ण विश्लेषण पहा' : 'View Full Zone Intelligence'}</span>
          <ArrowRight size={14} />
        </button>
      )}
    </div>
  );
}
