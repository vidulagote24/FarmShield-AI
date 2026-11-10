/**
 * FarmShield AI - RecommendationStatusTimeline Component
 * 
 * Visualizes the lifecycle stages of an agronomic recommendation:
 * Generated (Pending) -> Acknowledged (Accepted) -> Applied / Dismissed
 */

import React from 'react';
import { CheckCircle2, Clock, Check, X, AlertOctagon, AlertCircle, ArrowDown } from 'lucide-react';

export default function RecommendationStatusTimeline({
  status = 'pending',
  generatedAt,
  validUntil,
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';
  const normStatus = (status || 'pending').toLowerCase();

  const isPending = normStatus === 'pending';
  const isAcknowledged = normStatus === 'accepted' || normStatus === 'acknowledged';
  const isApplied = normStatus === 'applied' || normStatus === 'completed';
  const isDismissed = normStatus === 'dismissed' || normStatus === 'rejected';
  const isExpired = normStatus === 'expired';
  const isSuperseded = normStatus === 'superseded';

  const formatTimestamp = (ts) => {
    if (!ts) return null;
    try {
      const d = new Date(ts);
      return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } catch {
      return ts;
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
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
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
            <Clock size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#FFFFFF', margin: 0 }}>
              {isMarathi ? 'सल्ला जीवनचक्र (Status Timeline)' : 'Lifecycle Timeline'}
            </h3>
            <div style={{ fontSize: '11px', color: '#B6C8BB' }}>
              {isMarathi ? 'सल्ला निर्मितीपासून अंमलबजावणीपर्यंतचा प्रवास' : 'Workflow from generation to execution'}
            </div>
          </div>
        </div>

        {isExpired && (
          <span
            className="glass-pill"
            style={{
              color: '#F87171',
              border: '1px solid rgba(248, 113, 113, 0.4)',
              background: 'rgba(248, 113, 113, 0.15)',
              fontSize: '11px',
              fontWeight: 800,
            }}
          >
            {isMarathi ? 'कालबाह्य (Expired)' : 'Expired'}
          </span>
        )}
        {isSuperseded && (
          <span
            className="glass-pill"
            style={{
              color: '#C084FC',
              border: '1px solid rgba(192, 132, 252, 0.4)',
              background: 'rgba(192, 132, 252, 0.15)',
              fontSize: '11px',
              fontWeight: 800,
            }}
          >
            {isMarathi ? 'अद्ययावत (Superseded)' : 'Superseded'}
          </span>
        )}
      </div>

      {/* Stepped Timeline */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', position: 'relative', paddingLeft: '8px' }}>
        {/* Step 1: Generated */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
          <div
            style={{
              width: '24px',
              height: '24px',
              borderRadius: '50%',
              background: '#22C55E',
              color: '#071F16',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 800,
              fontSize: '12px',
              flexShrink: 0,
              boxShadow: '0 0 10px rgba(34, 197, 94, 0.4)',
            }}
          >
            <Check size={14} strokeWidth={3} />
          </div>
          <div>
            <div style={{ fontSize: '13px', fontWeight: 800, color: '#FFFFFF' }}>
              {isMarathi ? '१. सल्ला निर्माण झाला (Advisory Generated)' : '1. Advisory Generated'}
            </div>
            <div style={{ fontSize: '11px', color: '#8E9F90', marginTop: '1px' }}>
              {generatedAt ? formatTimestamp(generatedAt) : (isMarathi ? 'वेळ उपलब्ध नाही' : 'Timestamp unavailable')}
            </div>
          </div>
        </div>

        {/* Step 2: Acknowledged / In Review */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
          <div
            style={{
              width: '24px',
              height: '24px',
              borderRadius: '50%',
              background: (isAcknowledged || isApplied) ? '#38BDF8' : 'rgba(255, 255, 255, 0.12)',
              color: (isAcknowledged || isApplied) ? '#071F16' : '#94A3B8',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 800,
              fontSize: '12px',
              flexShrink: 0,
              border: (isAcknowledged || isApplied) ? 'none' : '1px solid rgba(255, 255, 255, 0.2)',
              boxShadow: (isAcknowledged || isApplied) ? '0 0 10px rgba(56, 189, 248, 0.4)' : 'none',
            }}
          >
            {(isAcknowledged || isApplied) ? <Check size={14} strokeWidth={3} /> : '2'}
          </div>
          <div>
            <div style={{ fontSize: '13px', fontWeight: 800, color: (isAcknowledged || isApplied) ? '#38BDF8' : '#94A3B8' }}>
              {isMarathi ? '२. शेतकऱ्याने सल्ला पाहिला व स्वीकारला (Acknowledged)' : '2. Acknowledged by Farmer'}
            </div>
            <div style={{ fontSize: '11px', color: '#8E9F90', marginTop: '1px' }}>
              {isAcknowledged ? (isMarathi ? 'सध्याची स्थिती: मान्य' : 'Current Status: Acknowledged') : isApplied ? (isMarathi ? 'मान्य करण्यात आला होता' : 'Previously Acknowledged') : (isMarathi ? 'प्रलंबित (Pending review)' : 'Awaiting farmer acknowledgment')}
            </div>
          </div>
        </div>

        {/* Step 3: Terminal State (Applied OR Dismissed OR Expired OR Superseded) */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
          <div
            style={{
              width: '24px',
              height: '24px',
              borderRadius: '50%',
              background: isApplied 
                ? '#4ADE80' 
                : isDismissed 
                  ? '#94A3B8' 
                  : isExpired 
                    ? '#F87171' 
                    : isSuperseded
                      ? '#C084FC'
                      : 'rgba(255, 255, 255, 0.12)',
              color: (isApplied || isDismissed || isExpired || isSuperseded) ? '#071F16' : '#94A3B8',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 800,
              fontSize: '12px',
              flexShrink: 0,
              border: (isApplied || isDismissed || isExpired || isSuperseded) ? 'none' : '1px solid rgba(255, 255, 255, 0.2)',
              boxShadow: isApplied ? '0 0 10px rgba(74, 222, 128, 0.4)' : 'none',
            }}
          >
            {isApplied ? <Check size={14} strokeWidth={3} /> : isDismissed ? <X size={14} strokeWidth={3} /> : isExpired ? <AlertOctagon size={14} strokeWidth={3} /> : isSuperseded ? <AlertCircle size={14} strokeWidth={3} /> : '3'}
          </div>
          <div>
            <div
              style={{
                fontSize: '13px',
                fontWeight: 800,
                color: isApplied 
                  ? '#4ADE80' 
                  : isDismissed 
                    ? '#CBD5E1' 
                    : isExpired 
                      ? '#F87171' 
                      : isSuperseded
                        ? '#C084FC'
                        : '#94A3B8',
              }}
            >
              {isApplied 
                ? (isMarathi ? '३. शेतात प्रत्यक्ष पूर्ण (Applied / Completed)' : '3. Applied on Field (Completed)')
                : isDismissed
                  ? (isMarathi ? '३. सल्ला रद्द / नाकारला (Dismissed)' : '3. Advisory Dismissed / Rejected')
                  : isExpired
                    ? (isMarathi ? '३. मुदत संपली (Expired)' : '3. Expired without execution')
                    : isSuperseded
                      ? (isMarathi ? '३. अधिक नवीन सल्ला उपलब्ध (Superseded)' : '3. Superseded by newer advisory')
                      : (isMarathi ? '३. अंमलबजावणी किंवा रद्द (Applied or Dismissed)' : '3. Pending Application on Field')}
            </div>
            <div style={{ fontSize: '11px', color: '#8E9F90', marginTop: '1px' }}>
              {isApplied 
                ? (isMarathi ? 'शेतकऱ्याने प्रत्यक्ष कृती पूर्ण झाल्याची नोंद केली.' : 'Confirmed applied on field by farmer.')
                : isDismissed
                  ? (isMarathi ? 'शेतकऱ्याने हा सल्ला लागू न करण्याचा निर्णय घेतला.' : 'Farmer chose not to apply this recommendation.')
                  : isExpired
                    ? (isMarathi ? 'या सल्ल्याची मुदत संपली आहे.' : 'Advisory reached expiration date.')
                    : isSuperseded
                      ? (isMarathi ? 'नवीन सल्ल्यामुळे हा सल्ला अद्ययावत झाला आहे.' : 'Replaced by newer recommendation.')
                      : (isMarathi ? 'अंतिम टप्पा अद्याप प्रलंबित आहे.' : 'Final outcome not yet recorded.')}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

