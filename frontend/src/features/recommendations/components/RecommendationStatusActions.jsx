/**
 * FarmShield AI - RecommendationStatusActions Component
 * 
 * Provides interactive status workflow transitions for recommendations:
 * - Acknowledge (accepted)
 * - Apply (applied / completed)
 * - Dismiss (dismissed / rejected)
 * 
 * Rules:
 * - In Live Mode: Sends PATCH /api/v1/recommendations/{id}/status to FastAPI backend.
 * - In Demo Mode: Performs isolated simulated state update with clear demo banner.
 * - Requires explicit confirmation step before executing status changes.
 * - Does not claim irrigation or pump activation occurred.
 * - Preserves state on failure.
 */

import React, { useState } from 'react';
import { CheckCircle2, XCircle, AlertCircle, Loader2, RotateCcw, ShieldCheck, Check } from 'lucide-react';

export default function RecommendationStatusActions({
  currentStatus = 'pending',
  onUpdateStatus,
  isUpdating = false,
  error = null,
  isDemoMode = false,
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';
  const normStatus = (currentStatus || 'pending').toLowerCase();

  // Confirmation state modal / inline sheet
  const [confirmingTarget, setConfirmingTarget] = useState(null); // 'accepted' | 'applied' | 'dismissed' | 'pending' | null

  const isPending = normStatus === 'pending';
  const isAcknowledged = normStatus === 'accepted' || normStatus === 'acknowledged';
  const isApplied = normStatus === 'applied' || normStatus === 'completed';
  const isDismissed = normStatus === 'dismissed' || normStatus === 'rejected';

  const handleExecuteStatusChange = async (target) => {
    if (!onUpdateStatus) return;
    try {
      await onUpdateStatus(target);
      setConfirmingTarget(null);
    } catch {
      // Error handled by parent hook, dialog can stay or close
    }
  };

  const getTargetDetails = (target) => {
    switch (target) {
      case 'accepted':
        return {
          title_mr: 'सल्ला मान्य (Acknowledge) करायचा आहे का?',
          title_en: 'Acknowledge this recommendation?',
          desc_mr: 'हा सल्ला आपण वाचला असून विचारात घेतला आहे याची नोंद होईल. प्रत्यक्ष शेतात पाणी देण्यापूर्वी परिस्थिती तपासा.',
          desc_en: 'Marks this advisory as acknowledged and under review by the farmer.',
          btn_mr: 'होय, मान्य करा (Acknowledge)',
          btn_en: 'Confirm Acknowledgment',
          color: '#38BDF8',
        };
      case 'applied':
        return {
          title_mr: 'सल्ल्यानुसार कृती पूर्ण (Applied) झाल्याची नोंद करायची?',
          title_en: 'Mark recommendation as applied?',
          desc_mr: 'शेतकऱ्याने स्वतः शेतात प्रत्यक्ष ही कृती पूर्ण केली आहे याची नोंद होईल. याने कोणतीही स्वयंचलित मशिनरी सुरू होत नाही.',
          desc_en: 'Confirms that the farmer has manually carried out this recommendation on the field. Does not control hardware.',
          btn_mr: 'होय, कृती पूर्ण झाली (Applied)',
          btn_en: 'Confirm Applied',
          color: '#4ADE80',
        };
      case 'dismissed':
        return {
          title_mr: 'सल्ला रद्द / फेटाळायचा (Dismiss) आहे का?',
          title_en: 'Dismiss this recommendation?',
          desc_mr: 'स्थानिक परिस्थितीनुसार हा सल्ला लागू करणे योग्य नसल्यास आपण तो रद्द करू शकता.',
          desc_en: 'Dismisses this recommendation. The system will record that this advisory was deferred or rejected by the farmer.',
          btn_mr: 'होय, रद्द करा (Dismiss)',
          btn_en: 'Confirm Dismissal',
          color: '#94A3B8',
        };
      case 'pending':
        return {
          title_mr: 'स्थिती पुन्हा प्रलंबित (Pending) करायची का?',
          title_en: 'Reset status to Pending (Demo)?',
          desc_mr: 'केवळ नमुना चाचणीसाठी ही स्थिती पुन्हा बदलण्यात येईल.',
          desc_en: 'Resets the workflow status back to pending for simulation purposes.',
          btn_mr: 'रीसेट करा (Reset)',
          btn_en: 'Reset Status',
          color: '#FBBF24',
        };
      default:
        return { title_mr: target, title_en: target, btn_mr: target, btn_en: target, color: '#C5F36B' };
    }
  };

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
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
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
            <ShieldCheck size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#FFFFFF', margin: 0 }}>
              {isMarathi ? 'सल्ला स्थिती व्यवस्थापन (Workflow Actions)' : 'Status Workflow Actions'}
            </h3>
            <div style={{ fontSize: '11px', color: '#B6C8BB' }}>
              {isDemoMode 
                ? (isMarathi ? 'नमुना मोड: सिम्युलेटेड स्थिती बदल' : 'Demo Mode: Simulated workflow transitions') 
                : (isMarathi ? 'लाइव्ह API: बॅकएंड डेटाबेस अपडेट' : 'Live API: Synchronized with backend')}
            </div>
          </div>
        </div>

        <span
          className="glass-pill"
          style={{
            fontSize: '10.5px',
            color: isDemoMode ? '#C5F36B' : '#38BDF8',
            border: isDemoMode ? '1px solid rgba(197, 243, 107, 0.3)' : '1px solid rgba(56, 189, 248, 0.3)',
          }}
        >
          {isDemoMode ? 'SIMULATION' : 'LIVE REST API'}
        </span>
      </div>

      {/* Error Message if update failed */}
      {error && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 12px',
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.45)',
            borderRadius: '10px',
            color: '#FCA5A5',
            fontSize: '12px',
            marginBottom: '14px',
          }}
        >
          <AlertCircle size={16} color="#EF4444" style={{ flexShrink: 0 }} />
          <span>{error}</span>
        </div>
      )}

      {/* Confirmation Step View */}
      {confirmingTarget ? (
        (() => {
          const details = getTargetDetails(confirmingTarget);
          return (
            <div
              style={{
                padding: '14px',
                background: 'rgba(255, 255, 255, 0.05)',
                border: `1.5px solid ${details.color}`,
                borderRadius: '14px',
                boxShadow: '0 6px 20px rgba(0, 0, 0, 0.4)',
              }}
            >
              <h4 style={{ fontSize: '14px', fontWeight: 800, color: details.color, margin: '0 0 6px 0' }}>
                {isMarathi ? details.title_mr : details.title_en}
              </h4>
              <p style={{ fontSize: '12px', color: '#CBD5E1', lineHeight: 1.45, marginBottom: '14px' }}>
                {isMarathi ? details.desc_mr : details.desc_en}
              </p>

              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={() => setConfirmingTarget(null)}
                  disabled={isUpdating}
                  className="btn-glass-secondary"
                  style={{
                    flex: 1,
                    minHeight: '38px',
                    fontSize: '12px',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  {isMarathi ? 'रद्द करा (Cancel)' : 'Cancel'}
                </button>

                <button
                  onClick={() => handleExecuteStatusChange(confirmingTarget)}
                  disabled={isUpdating}
                  style={{
                    flex: 1.5,
                    minHeight: '38px',
                    padding: '8px 12px',
                    borderRadius: '12px',
                    border: 'none',
                    background: details.color,
                    color: '#071F16',
                    fontSize: '12.5px',
                    fontWeight: 800,
                    cursor: isUpdating ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px',
                  }}
                >
                  {isUpdating ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      <span>{isMarathi ? 'नोंद होत आहे...' : 'Saving...'}</span>
                    </>
                  ) : (
                    <>
                      <Check size={14} strokeWidth={3} />
                      <span>{isMarathi ? details.btn_mr : details.btn_en}</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          );
        })()
      ) : (
        /* Action Buttons Grid based on Current Status */
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {/* Pending Status Options */}
          {isPending && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px' }}>
              <button
                onClick={() => setConfirmingTarget('accepted')}
                className="btn-glass-primary"
                style={{
                  minHeight: '40px',
                  fontSize: '12px',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  cursor: 'pointer',
                }}
              >
                <CheckCircle2 size={15} color="#071F16" />
                <span>{isMarathi ? 'सल्ला स्वीकारा (Acknowledge)' : 'Acknowledge'}</span>
              </button>

              <button
                onClick={() => setConfirmingTarget('dismissed')}
                className="btn-glass-secondary"
                style={{
                  minHeight: '40px',
                  fontSize: '12px',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  color: '#94A3B8',
                  cursor: 'pointer',
                }}
              >
                <XCircle size={15} color="#94A3B8" />
                <span>{isMarathi ? 'सल्ला रद्द करा (Dismiss)' : 'Dismiss'}</span>
              </button>
            </div>
          )}

          {/* Acknowledged Status Options */}
          {isAcknowledged && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px' }}>
              <button
                onClick={() => setConfirmingTarget('applied')}
                className="btn-glass-primary"
                style={{
                  minHeight: '40px',
                  fontSize: '12px',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  background: 'linear-gradient(135deg, #4ADE80 0%, #22C55E 100%)',
                  cursor: 'pointer',
                }}
              >
                <CheckCircle2 size={15} color="#071F16" />
                <span>{isMarathi ? 'अंमलबजावणी झाली (Mark Applied)' : 'Mark as Applied'}</span>
              </button>

              <button
                onClick={() => setConfirmingTarget('dismissed')}
                className="btn-glass-secondary"
                style={{
                  minHeight: '40px',
                  fontSize: '12px',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  color: '#94A3B8',
                  cursor: 'pointer',
                }}
              >
                <XCircle size={15} color="#94A3B8" />
                <span>{isMarathi ? 'सल्ला रद्द करा (Dismiss)' : 'Dismiss'}</span>
              </button>
            </div>
          )}

          {/* Applied Status View */}
          {isApplied && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 14px',
                background: 'rgba(74, 222, 128, 0.12)',
                border: '1px solid rgba(74, 222, 128, 0.35)',
                borderRadius: '12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle2 size={18} color="#4ADE80" />
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 800, color: '#4ADE80' }}>
                    {isMarathi ? 'सल्ला यशस्वीरीत्या पूर्ण झाला आहे' : 'Recommendation Fulfilled'}
                  </div>
                  <div style={{ fontSize: '11px', color: '#B6C8BB' }}>
                    {isMarathi ? 'शेतकऱ्याने प्रत्यक्ष कृतीची नोंद केली आहे.' : 'Action marked as applied on field.'}
                  </div>
                </div>
              </div>

              {isDemoMode && (
                <button
                  onClick={() => setConfirmingTarget('pending')}
                  className="glass-pill"
                  style={{
                    fontSize: '11px',
                    color: '#FBBF24',
                    border: '1px solid rgba(251, 191, 36, 0.4)',
                    cursor: 'pointer',
                  }}
                  title={isMarathi ? 'पुन्हा प्रलंबित करा' : 'Reset to Pending'}
                >
                  <RotateCcw size={11} />
                  <span>{isMarathi ? 'रीसेट' : 'Reset'}</span>
                </button>
              )}
            </div>
          )}

          {/* Dismissed Status View */}
          {isDismissed && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px 14px',
                background: 'rgba(148, 163, 184, 0.12)',
                border: '1px solid rgba(148, 163, 184, 0.35)',
                borderRadius: '12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <XCircle size={18} color="#94A3B8" />
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 800, color: '#CBD5E1' }}>
                    {isMarathi ? 'सल्ला रद्द करण्यात आला आहे' : 'Recommendation Dismissed'}
                  </div>
                  <div style={{ fontSize: '11px', color: '#94A3B8' }}>
                    {isMarathi ? 'शेतकऱ्याने हा सल्ला न राबवण्याचा निर्णय घेतला.' : 'Farmer chose not to apply this advisory.'}
                  </div>
                </div>
              </div>

              {isDemoMode && (
                <button
                  onClick={() => setConfirmingTarget('pending')}
                  className="glass-pill"
                  style={{
                    fontSize: '11px',
                    color: '#FBBF24',
                    border: '1px solid rgba(251, 191, 36, 0.4)',
                    cursor: 'pointer',
                  }}
                  title={isMarathi ? 'पुन्हा प्रलंबित करा' : 'Reset to Pending'}
                >
                  <RotateCcw size={11} />
                  <span>{isMarathi ? 'रीसेट' : 'Reset'}</span>
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

