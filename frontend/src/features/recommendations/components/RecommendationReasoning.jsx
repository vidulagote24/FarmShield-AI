/**
 * FarmShield AI - RecommendationReasoning Component
 * 
 * Displays the qualitative contributing factors and decision rules
 * provided by the backend intelligence service.
 */

import React from 'react';
import { HelpCircle, CheckCircle2, ListOrdered } from 'lucide-react';

export default function RecommendationReasoning({
  reasoning = {},
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';
  const factors = Array.isArray(reasoning.factors) ? reasoning.factors : [];

  return (
    <div
      className="glass-card"
      style={{
        padding: '18px',
        marginBottom: '16px',
        background: 'rgba(7, 31, 22, 0.85)',
        border: '1px solid rgba(197, 243, 107, 0.35)',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '8px',
            background: 'rgba(197, 243, 107, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#C5F36B',
          }}
        >
          <HelpCircle size={18} />
        </div>
        <div>
          <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#FFFFFF', margin: 0 }}>
            {isMarathi ? 'सल्ल्यामागील वैज्ञानिक निकष (Decision Rationale)' : 'Decision Engine Reasoning'}
          </h3>
          <div style={{ fontSize: '11px', color: '#B6C8BB' }}>
            {isMarathi ? 'डिसिजन इंजिनने विचारात घेतलेले घटक' : 'Key inputs and rule evaluations from backend'}
          </div>
        </div>
      </div>

      {/* Factors List */}
      {factors.length === 0 ? (
        <div
          style={{
            padding: '12px',
            background: 'rgba(255, 255, 255, 0.03)',
            borderRadius: '10px',
            border: '1px dashed rgba(255, 255, 255, 0.15)',
            fontSize: '12px',
            color: '#94A3B8',
          }}
        >
          {isMarathi 
            ? 'या सल्ल्यासाठी विशिष्ट वैज्ञानिक निकष यादी बॅकएंडकडून प्राप्त झालेली नाही.' 
            : 'No qualitative reasoning factors returned in the backend response.'}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {factors.map((factor, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '10px',
                padding: '10px 12px',
                background: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '12px',
              }}
            >
              <div
                style={{
                  width: '20px',
                  height: '20px',
                  borderRadius: '50%',
                  background: 'rgba(197, 243, 107, 0.2)',
                  color: '#C5F36B',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '11px',
                  fontWeight: 800,
                  flexShrink: 0,
                  marginTop: '1px',
                }}
              >
                {idx + 1}
              </div>
              <div style={{ fontSize: '12.5px', color: '#E2E8F0', lineHeight: 1.45 }}>
                {factor}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

