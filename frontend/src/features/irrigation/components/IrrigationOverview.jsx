/**
 * FarmShield AI - IrrigationOverview Component
 * 
 * Header summary card for the Irrigation Planner:
 * displays farm parameters, advisory status, prominent safety disclaimer,
 * and live/demo mode toggle.
 */

import React from 'react';
import { Droplets, Shield, AlertTriangle, Info, MapPin } from 'lucide-react';

export default function IrrigationOverview({
  farm,
  recommendations = [],
  zones = [],
  isDemoMode = false,
  onToggleDataMode,
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';

  const farmName = farm?.name || farm?.name_en || (isMarathi ? 'शेत' : 'Farm');
  const farmLocation = farm?.location_name || (isMarathi ? 'बारामती, पुणे' : 'Baramati, Pune');
  const areaDisplay = farm?.area_acres 
    ? `${farm.area_acres} ${isMarathi ? 'एकर' : 'Acres'}` 
    : (farm?.area_hectares ? `${farm.area_hectares} ha` : '3.5 एकर');

  // Count zones needing action vs adequate
  const urgentCount = recommendations.filter((r) => r.priority === 'high' || r.priority === 'critical').length;
  const monitorCount = recommendations.filter((r) => r.priority === 'medium').length;

  return (
    <div
      className="glass-card"
      style={{
        padding: '18px',
        background: 'rgba(10, 43, 28, 0.75)',
        border: '1.5px solid rgba(56, 189, 248, 0.35)',
        boxShadow: '0 10px 30px rgba(0, 0, 0, 0.35)',
      }}
    >
      {/* Top Header & Mode Toggle */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '10px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '3px' }}>
            <span className="glass-pill" style={{ color: '#38BDF8', fontSize: '11px' }}>
              <Droplets size={12} />
              {isMarathi ? 'स्मार्ट सिंचन सल्लागार' : 'Irrigation Planner'}
            </span>
            <span style={{ fontSize: '11px', color: '#B6C8BB' }}>
              📍 {farmLocation}
            </span>
          </div>

          <h2 style={{ fontSize: '20px', fontWeight: 800, color: '#FFFFFF', letterSpacing: '-0.3px', margin: 0 }}>
            {farmName}
          </h2>
        </div>

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

      {/* Metrics Badges */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '12px' }}>
        <span className="glass-pill" style={{ color: '#FFFFFF' }}>
          📏 {areaDisplay}
        </span>
        <span className="glass-pill" style={{ color: '#FFFFFF' }}>
          🗺️ {zones.length} {isMarathi ? 'व्यवस्थापन विभाग' : 'Zones'}
        </span>
        {urgentCount > 0 && (
          <span className="glass-pill" style={{ color: '#F87171', borderColor: 'rgba(239, 68, 68, 0.4)', background: 'rgba(239, 68, 68, 0.15)' }}>
            ⚠️ {urgentCount} {isMarathi ? 'विभागाला तातडीचे सिंचन हवे' : 'Zone needs urgent watering'}
          </span>
        )}
      </div>

      {/* Prominent Safety Disclaimer */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '8px 12px',
          background: 'rgba(255, 255, 255, 0.05)',
          borderRadius: '12px',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          fontSize: '11.5px',
          color: '#CBD5E1',
          lineHeight: 1.4,
        }}
      >
        <Shield size={16} color="#C5F36B" style={{ flexShrink: 0 }} />
        <span>
          <strong>{isMarathi ? 'सुरक्षा सूचना:' : 'Safety Notice:'}</strong>{' '}
          {isMarathi 
            ? 'हा केवळ कृषी सल्लागार आहे. सिंचन पंप, मोटर किंवा व्हॉल्व्ह स्वयंचलित सुरू होत नाहीत.'
            : 'Advisory recommendations only. Does not control pumps, valves, or irrigation hardware.'}
        </span>
      </div>
    </div>
  );
}

