/**
 * FarmShield AI - MapLayerSelector Component
 * 
 * Allows switching between active spatial layers with data provenance and status checks.
 * Enforces strict scientific rules: layers without supporting data are disabled with an explanation.
 */

import React from 'react';
import { Layers, Shield, Sprout, Droplets, CloudRain, Info } from 'lucide-react';

export default function MapLayerSelector({
  activeLayer,
  onSelectLayer,
  hasNdviData = false,
  hasMoistureData = false,
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';

  const layers = [
    {
      id: 'zones',
      label_mr: 'व्यवस्थापन विभाग (Zones)',
      label_en: 'Management Zones',
      icon: Layers,
      color: '#C5F36B',
      enabled: true,
      hint: isMarathi ? 'विभाग पातळीवरील स्थिती' : 'Zone stress assessment',
    },
    {
      id: 'boundary',
      label_mr: 'शेताची सीमा (Boundary)',
      label_en: 'Farm Boundary',
      icon: Shield,
      color: '#65C76A',
      enabled: true,
      hint: isMarathi ? 'अधिकृत जिओ-फेन्स सीमा' : 'Cadastral/PostGIS boundary',
    },
    {
      id: 'ndvi',
      label_mr: 'वनस्पती निर्देशांक (NDVI)',
      label_en: 'Vegetation (NDVI)',
      icon: Sprout,
      color: '#38BDF8',
      enabled: hasNdviData,
      disabledReason: isMarathi ? 'उपग्रह दृश्य अनुपलब्ध / ढगांचे आच्छादन' : 'Satellite NDVI telemetry unavailable',
      hint: isMarathi ? 'सेंटिनेल-२ कॅनॉपी घनता' : 'Sentinel-2 L2A greenness',
    },
    {
      id: 'moisture',
      label_mr: 'माती ओलावा (Soil Moisture)',
      label_en: 'Soil Moisture',
      icon: Droplets,
      color: '#FFC34D',
      enabled: hasMoistureData,
      disabledReason: isMarathi ? 'सेन्सर किंवा मॉडेल ओलावा डेटा उपलब्ध नाही' : 'Field probe telemetry unavailable',
      hint: isMarathi ? 'रूट-झोन उपलब्ध पाणी' : 'Root-zone water evidence',
    },
    {
      id: 'rainfall',
      label_mr: 'पर्जन्यमान (Rainfall)',
      label_en: 'Rainfall Context',
      icon: CloudRain,
      color: '#A855F7',
      enabled: false,
      disabledReason: isMarathi ? 'स्थानिक रडार डेटा उपलब्ध नाही' : 'Gridded rainfall layer unavailable',
      hint: isMarathi ? 'ओपन-मेटिओ पाऊस नकाशा' : 'Precipitation grid',
    },
  ];

  return (
    <div
      className="glass-panel"
      style={{
        padding: '10px 14px',
        border: '1px solid rgba(255, 255, 255, 0.16)',
        borderRadius: '14px',
        background: 'rgba(7, 31, 22, 0.88)',
        backdropFilter: 'blur(16px)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <span style={{ fontSize: '11px', fontWeight: 800, color: '#C5F36B', display: 'flex', alignItems: 'center', gap: '5px' }}>
          <Layers size={13} />
          {isMarathi ? 'नकाशा स्तर निवडा (Layers)' : 'Active Map Layers'}
        </span>
        <span style={{ fontSize: '10px', color: '#D5E3D9', fontStyle: 'italic' }}>
          {isMarathi ? 'पुरावा आधारित' : 'Evidence-based'}
        </span>
      </div>

      <div style={{ display: 'flex', gap: '6px', overflowX: 'auto', paddingBottom: '4px' }}>
        {layers.map((layer) => {
          const Icon = layer.icon;
          const isActive = activeLayer === layer.id;
          const isDisabled = !layer.enabled;

          return (
            <button
              key={layer.id}
              onClick={() => {
                if (layer.enabled) onSelectLayer(layer.id);
              }}
              disabled={isDisabled}
              title={isDisabled ? layer.disabledReason : layer.hint}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                borderRadius: '10px',
                border: isActive
                  ? `1.5px solid ${layer.color}`
                  : '1px solid rgba(255, 255, 255, 0.14)',
                background: isActive
                  ? `${layer.color}25`
                  : isDisabled
                  ? 'rgba(255, 255, 255, 0.04)'
                  : 'rgba(255, 255, 255, 0.08)',
                color: isDisabled ? '#667085' : isActive ? '#FFFFFF' : '#D5E3D9',
                fontSize: '11.5px',
                fontWeight: isActive ? 800 : 600,
                cursor: isDisabled ? 'not-allowed' : 'pointer',
                whiteSpace: 'nowrap',
                opacity: isDisabled ? 0.6 : 1,
                transition: 'all 0.15s ease',
              }}
            >
              <Icon size={14} color={isDisabled ? '#667085' : layer.color} />
              <span>{isMarathi ? layer.label_mr : layer.label_en}</span>
              {isDisabled && (
                <span style={{ fontSize: '9px', background: 'rgba(0,0,0,0.3)', padding: '1px 4px', borderRadius: '4px' }}>
                  N/A
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
