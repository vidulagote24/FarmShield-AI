/**
 * FarmShield AI - MapLegend Component
 * 
 * Accessible, WCAG-compliant legend describing zone status colors and symbols.
 * Conforms to docs/DESIGN.md token specifications.
 */

import React from 'react';
import { CheckCircle2, AlertTriangle, AlertOctagon, HelpCircle, Eye } from 'lucide-react';

export const STATUS_CONFIG = {
  healthy: {
    label_mr: 'निरोगी (Healthy)',
    label_en: 'Healthy',
    color: '#2E7D4F',
    fillColor: '#2E7D4F',
    badgeBg: 'rgba(46, 125, 79, 0.20)',
    badgeBorder: '#2E7D4F',
    icon: CheckCircle2,
    dashArray: null,
  },
  monitor: {
    label_mr: 'निरीक्षण (Monitor)',
    label_en: 'Monitor',
    color: '#3576A8',
    fillColor: '#3576A8',
    badgeBg: 'rgba(53, 118, 168, 0.20)',
    badgeBorder: '#3576A8',
    icon: Eye,
    dashArray: null,
  },
  attention: {
    label_mr: 'दक्षता (Attention)',
    label_en: 'Attention',
    color: '#D97706',
    fillColor: '#D97706',
    badgeBg: 'rgba(217, 119, 6, 0.20)',
    badgeBorder: '#D97706',
    icon: AlertTriangle,
    dashArray: null,
  },
  high_stress: {
    label_mr: 'तीव्र ताण (High Stress)',
    label_en: 'High Stress',
    color: '#B5473E',
    fillColor: '#B5473E',
    badgeBg: 'rgba(181, 71, 62, 0.20)',
    badgeBorder: '#B5473E',
    icon: AlertOctagon,
    dashArray: null,
  },
  insufficient_data: {
    label_mr: 'माहिती अपुरी (Insufficient Data)',
    label_en: 'Insufficient Data',
    color: '#8A97A5',
    fillColor: '#667085',
    badgeBg: 'rgba(102, 112, 133, 0.20)',
    badgeBorder: '#8A97A5',
    icon: HelpCircle,
    dashArray: '4, 4',
  },
};

export default function MapLegend({ currentLang = 'mr', activeLayer = 'zones' }) {
  const isMarathi = currentLang === 'mr';

  return (
    <div
      className="glass-panel"
      style={{
        padding: '10px 14px',
        border: '1px solid rgba(255, 255, 255, 0.16)',
        borderRadius: '14px',
        background: 'rgba(7, 31, 22, 0.88)',
        backdropFilter: 'blur(16px)',
        boxShadow: '0 4px 16px rgba(0, 0, 0, 0.35)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <span style={{ fontSize: '11px', fontWeight: 800, color: '#C5F36B', letterSpacing: '0.2px' }}>
          🗺️ {isMarathi ? 'नकाशा संकेत (Legend)' : 'Map Legend'}
        </span>
        <span style={{ fontSize: '10px', color: '#A3B8A8', fontWeight: 600 }}>
          {isMarathi ? 'विभाग स्थिती' : 'Zone Condition'}
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '6px' }}>
        {Object.entries(STATUS_CONFIG).map(([key, cfg]) => {
          const Icon = cfg.icon;
          return (
            <div
              key={key}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 8px',
                background: cfg.badgeBg,
                border: `1px solid ${cfg.badgeBorder}40`,
                borderRadius: '8px',
              }}
            >
              <div
                style={{
                  width: '12px',
                  height: '12px',
                  borderRadius: '3px',
                  backgroundColor: cfg.color,
                  border: `1px solid ${cfg.color}`,
                  flexShrink: 0,
                }}
              />
              <span style={{ fontSize: '10.5px', color: '#FFFFFF', fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {isMarathi ? cfg.label_mr : cfg.label_en}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
