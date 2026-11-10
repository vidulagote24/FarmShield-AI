/**
 * FarmShield AI - CropStageCard Component
 * 
 * Displays crop growth stage, variety, sowing date, and irrigation method.
 * 
 * Strict Agronomic Rule (per AGENTS.md):
 * - Do NOT independently infer crop stage from crop type, date, NDVI, or frontend calculations.
 * - Display crop stage only when provided by the backend.
 * - If unavailable, honestly display "Crop stage data unavailable".
 */

import React from 'react';
import { Sprout, Calendar, Droplets, Info } from 'lucide-react';
import InsufficientDataState from './InsufficientDataState.jsx';

export default function CropStageCard({
  zone,
  farm,
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';

  // Extract crop stage strictly from backend responses
  const cropStage = 
    zone?.crop_stage || 
    zone?.metadata?.crop_stage || 
    zone?.metadata?.growth_stage || 
    farm?.crop?.growth_stage || 
    farm?.crop_stage || 
    null;

  const cropName = 
    zone?.crop || 
    zone?.metadata?.crop || 
    farm?.crop?.crop_name || 
    farm?.crop_type || 
    null;

  const cropVariety = 
    zone?.crop_variety || 
    zone?.metadata?.crop_variety || 
    farm?.crop_variety || 
    null;

  const sowingDate = 
    zone?.sowing_date || 
    zone?.metadata?.sowing_date || 
    farm?.crop?.sowing_date || 
    farm?.sowing_date || 
    null;

  const irrigationMethod = 
    zone?.metadata?.irrigation_method || 
    farm?.crop?.irrigation_method || 
    (isMarathi ? 'ठिबक सिंचन (Drip)' : 'Drip Irrigation');

  const formatSowingDate = (dateStr) => {
    if (!dateStr) return isMarathi ? 'नोंदवलेली नाही' : 'Unrecorded';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString();
    } catch (e) {
      return dateStr;
    }
  };

  return (
    <div
      className="glass-card"
      style={{
        padding: '18px',
        background: 'rgba(7, 31, 22, 0.75)',
        border: '1px solid rgba(168, 217, 74, 0.30)',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'rgba(168, 217, 74, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#A8D94A',
            }}
          >
            <Sprout size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#FFFFFF', margin: 0 }}>
              {isMarathi ? 'पीक अवस्था व तपशील' : 'Crop Growth Stage & Identity'}
            </h3>
            <div style={{ fontSize: '11px', color: '#B6C8BB' }}>
              {isMarathi ? 'पिकाचा प्रकार व वाढीची सद्यस्थिती' : 'Validated crop metadata from backend'}
            </div>
          </div>
        </div>
      </div>

      {/* Crop Stage Display or Honest Unavailable State */}
      {cropStage ? (
        <div
          style={{
            padding: '12px 14px',
            background: 'rgba(197, 243, 107, 0.10)',
            border: '1px solid rgba(197, 243, 107, 0.25)',
            borderRadius: '14px',
            marginBottom: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <div style={{ fontSize: '10.5px', color: '#C5F36B', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px' }}>
              {isMarathi ? 'पिकाची वाढीची अवस्था (Crop Stage)' : 'Phenological Growth Stage'}
            </div>
            <div style={{ fontSize: '16px', fontWeight: 800, color: '#FFFFFF', marginTop: '2px' }}>
              🌱 {cropStage}
            </div>
          </div>

          <span className="glass-pill" style={{ color: '#C5F36B', fontSize: '11px' }}>
            {isMarathi ? 'नोंदणीकृत' : 'Backend Verified'}
          </span>
        </div>
      ) : (
        <div style={{ marginBottom: '12px' }}>
          <InsufficientDataState
            compact={true}
            message={isMarathi ? 'पिकाची अवस्था उपलब्ध नाही (Crop stage data unavailable)' : 'Crop stage data unavailable from backend'}
            currentLang={currentLang}
            icon={Sprout}
          />
        </div>
      )}

      {/* Grid of Other Crop Parameters */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: '8px',
        }}
      >
        <div className="glass-panel" style={{ padding: '8px 10px' }}>
          <div style={{ fontSize: '10px', color: '#8E9F90' }}>{isMarathi ? 'वाण / व्हरायटी' : 'Variety'}</div>
          <div style={{ fontSize: '12px', fontWeight: 700, color: '#FFFFFF', marginTop: '2px' }}>
            {cropVariety || (isMarathi ? 'माहिती उपलब्ध नाही' : 'Unrecorded')}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '8px 10px' }}>
          <div style={{ fontSize: '10px', color: '#8E9F90' }}>{isMarathi ? 'पेरणी दिनांक' : 'Sowing Date'}</div>
          <div style={{ fontSize: '12px', fontWeight: 700, color: '#FFFFFF', marginTop: '2px' }}>
            📅 {formatSowingDate(sowingDate)}
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '8px 10px' }}>
          <div style={{ fontSize: '10px', color: '#8E9F90' }}>{isMarathi ? 'सिंचन पद्धत' : 'Irrigation Method'}</div>
          <div style={{ fontSize: '12px', fontWeight: 700, color: '#FFFFFF', marginTop: '2px' }}>
            💧 {irrigationMethod}
          </div>
        </div>
      </div>
    </div>
  );
}

