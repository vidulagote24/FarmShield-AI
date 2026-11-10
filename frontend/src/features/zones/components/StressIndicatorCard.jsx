/**
 * FarmShield AI - StressIndicatorCard Component
 * 
 * Displays agronomic stress classifications, supporting evidence, and scientific reason codes.
 * 
 * Strict Agronomic Restrictions (per AGENTS.md, AI_SPEC.md):
 * - Displays stress classifications and explanations ONLY when the backend provides them.
 * - Does NOT create a new stress score, threshold, or agronomic formula in the frontend.
 * - If backend stress assessment is missing or incomplete, honestly displays limitations.
 */

import React from 'react';
import { ShieldAlert, CheckCircle2, AlertTriangle, AlertCircle, HelpCircle, FileText, Info } from 'lucide-react';
import InsufficientDataState from './InsufficientDataState.jsx';

const STRESS_CONFIG = {
  healthy: {
    color: '#22C55E',
    label_en: 'Healthy / No Stress',
    label_mr: 'निरोगी / पाण्याचा ताण नाही',
    bg: 'rgba(34, 197, 94, 0.16)',
    border: 'rgba(34, 197, 94, 0.45)',
    icon: CheckCircle2,
  },
  monitor: {
    color: '#F59E0B',
    label_en: 'Mild Stress / Monitor',
    label_mr: 'मध्यम ताण / निरीक्षण ठेवा',
    bg: 'rgba(245, 158, 11, 0.16)',
    border: 'rgba(245, 158, 11, 0.45)',
    icon: AlertTriangle,
  },
  attention: {
    color: '#EF4444',
    label_en: 'Critical Stress / Action Advised',
    label_mr: 'गंभीर ताण / तातडीने लक्ष द्या',
    bg: 'rgba(239, 68, 68, 0.16)',
    border: 'rgba(239, 68, 68, 0.45)',
    icon: AlertCircle,
  },
  high_stress: {
    color: '#DC2626',
    label_en: 'Severe Water Deficit Stress',
    label_mr: 'तीव्र पाण्याचा तुटवडा',
    bg: 'rgba(220, 38, 38, 0.20)',
    border: 'rgba(220, 38, 38, 0.55)',
    icon: AlertCircle,
  },
  insufficient_data: {
    color: '#94A3B8',
    label_en: 'Insufficient Evidence for Stress Assessment',
    label_mr: 'ताण विश्लेषणासाठी अपुरा डेटा',
    bg: 'rgba(148, 163, 184, 0.16)',
    border: 'rgba(148, 163, 184, 0.40)',
    icon: HelpCircle,
  },
};

export default function StressIndicatorCard({
  stressAssessment = null, // { status, data_quality_status, reasons, assessed_at, confidence }
  zoneReasonSummary = null,
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';

  const statusKey = stressAssessment?.status || (zoneReasonSummary ? 'attention' : null);

  if (!statusKey) {
    return (
      <div
        className="glass-card"
        style={{
          padding: '18px',
          background: 'rgba(7, 31, 22, 0.75)',
          border: '1px solid rgba(255, 255, 255, 0.16)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
          <ShieldAlert size={18} color="#94A3B8" />
          <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#FFFFFF', margin: 0 }}>
            {isMarathi ? 'पीक ताण व कृषी बुद्धिमत्ता (Stress Indicators)' : 'Crop Stress Indicators'}
          </h3>
        </div>

        <InsufficientDataState
          compact={true}
          message={isMarathi 
            ? 'बॅकएंड इंटेलिजन्सकडून कोणताही ताण अहवाल प्राप्त झालेला नाही.' 
            : 'No stress assessment returned by backend intelligence system.'}
          currentLang={currentLang}
          icon={ShieldAlert}
        />
      </div>
    );
  }

  const config = STRESS_CONFIG[statusKey] || STRESS_CONFIG.insufficient_data;
  const StatusIcon = config.icon;

  const reasons = stressAssessment?.reasons || (zoneReasonSummary ? [zoneReasonSummary] : []);
  const confidencePct = stressAssessment?.confidence ? Math.round(stressAssessment.confidence * 100) : null;

  return (
    <div
      className="glass-card"
      style={{
        padding: '18px',
        background: 'rgba(7, 31, 22, 0.75)',
        border: `1.5px solid ${config.border}`,
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px', flexWrap: 'wrap', gap: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: config.bg,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: config.color,
            }}
          >
            <StatusIcon size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#FFFFFF', margin: 0 }}>
              {isMarathi ? 'पीक व पाणी ताण विश्लेषण' : 'Crop & Water Stress Intelligence'}
            </h3>
            <div style={{ fontSize: '11px', color: '#B6C8BB' }}>
              {isMarathi ? 'मल्टीमोडल पुरावा व वैज्ञानिक नियम' : 'Multimodal evidence & decision synthesis'}
            </div>
          </div>
        </div>

        {/* Confidence pill if backend returned it */}
        {confidencePct && (
          <span
            style={{
              fontSize: '10.5px',
              fontWeight: 700,
              color: '#C5F36B',
              background: 'rgba(197, 243, 107, 0.15)',
              padding: '2px 8px',
              borderRadius: '12px',
              border: '1px solid rgba(197, 243, 107, 0.35)',
            }}
          >
            {confidencePct}% {isMarathi ? 'विश्वासार्हता' : 'Confidence'}
          </span>
        )}
      </div>

      {/* Main Status Pill Card */}
      <div
        style={{
          padding: '12px 14px',
          background: config.bg,
          border: `1px solid ${config.border}`,
          borderRadius: '14px',
          marginBottom: '14px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <StatusIcon size={18} color={config.color} />
          <span style={{ fontSize: '14px', fontWeight: 800, color: config.color }}>
            {isMarathi ? config.label_mr : config.label_en}
          </span>
        </div>
      </div>

      {/* Evidence & Reason Points */}
      {reasons.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ fontSize: '11.5px', fontWeight: 700, color: '#D5E3D9', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <FileText size={13} color="#C5F36B" />
            <span>{isMarathi ? 'सहाय्यक पुरावे व निकष (Supporting Evidence):' : 'Evidence Factors:'}</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '2px' }}>
            {reasons.map((reason, idx) => (
              <div
                key={`reason-${idx}`}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '8px',
                  padding: '8px 10px',
                  background: 'rgba(255, 255, 255, 0.05)',
                  borderRadius: '10px',
                  fontSize: '12px',
                  color: '#FFFFFF',
                  lineHeight: 1.4,
                }}
              >
                <span style={{ color: config.color, marginTop: '2px' }}>•</span>
                <span>{reason}</span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div style={{ fontSize: '12px', color: '#8E9F90', fontStyle: 'italic' }}>
          {isMarathi ? 'कोणतेही तपशीलवार कारण कोड उपलब्ध नाहीत.' : 'No detailed reason codes provided by backend.'}
        </div>
      )}
    </div>
  );
}

