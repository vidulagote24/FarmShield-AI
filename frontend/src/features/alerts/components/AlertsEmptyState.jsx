/**
 * FarmShield AI - AlertsEmptyState Component
 * 
 * Accessible empty-state presentations for:
 * 1. Alerts (Honest all-clear message - no artificial alarms)
 * 2. Activity History (No records found)
 * 3. Filtered alerts (No alerts in selected priority)
 */

import React from 'react';
import { CheckCircle2, History, FilterX, RotateCcw } from 'lucide-react';

export default function AlertsEmptyState({
  type = 'alerts',
  currentLang = 'mr',
  onResetFilter,
  onRefresh,
}) {
  const isMarathi = currentLang === 'mr';
  const isHindi = currentLang === 'hi';

  if (type === 'filter_empty') {
    return (
      <div
        role="region"
        aria-label={isMarathi ? 'फिल्टर रिक्त स्थिती' : 'Filter empty state'}
        style={{
          textAlign: 'center',
          padding: '36px 20px',
          background: 'rgba(15, 23, 42, 0.45)',
          border: '1px dashed rgba(255, 255, 255, 0.15)',
          borderRadius: '16px',
          margin: '16px 0',
        }}
      >
        <FilterX size={36} color="rgba(255, 255, 255, 0.4)" style={{ margin: '0 auto 12px auto' }} />
        <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#FFFFFF', margin: '0 0 6px 0' }}>
          {isMarathi ? 'या फिल्टरमध्ये इशारे नाहीत' : isHindi ? 'इस फिल्टर में कोई अलर्ट नहीं है' : 'No alerts in this filter'}
        </h4>
        <p style={{ fontSize: '12.5px', color: 'rgba(255, 255, 255, 0.65)', margin: '0 0 16px 0' }}>
          {isMarathi
            ? 'निवडलेल्या प्राधान्य वर्गात सध्या कोणतेही सक्रिय इशारे आढळले नाहीत.'
            : 'No active alerts currently match the chosen priority category.'}
        </p>
        {onResetFilter && (
          <button
            type="button"
            onClick={onResetFilter}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '10px 18px',
              minHeight: '44px',
              borderRadius: '22px',
              background: 'rgba(197, 243, 107, 0.18)',
              border: '1px solid #C5F36B',
              color: '#C5F36B',
              fontSize: '12px',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            <RotateCcw size={14} />
            <span>{isMarathi ? 'सर्व इशारे दाखवा' : 'Show All Alerts'}</span>
          </button>
        )}
      </div>
    );
  }

  if (type === 'history') {
    return (
      <div
        role="region"
        aria-label={isMarathi ? 'इतिहास रिक्त स्थिती' : 'History empty state'}
        style={{
          textAlign: 'center',
          padding: '40px 20px',
          background: 'rgba(15, 23, 42, 0.45)',
          border: '1px dashed rgba(255, 255, 255, 0.15)',
          borderRadius: '16px',
          margin: '16px 0',
        }}
      >
        <History size={40} color="rgba(255, 255, 255, 0.4)" style={{ margin: '0 auto 12px auto' }} />
        <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#FFFFFF', margin: '0 0 6px 0' }}>
          {isMarathi ? 'मागील शेती नोंदी आढळल्या नाहीत' : isHindi ? 'कोई पिछला रिकॉर्ड नहीं मिला' : 'No activity records found'}
        </h4>
        <p style={{ fontSize: '12.5px', color: 'rgba(255, 255, 255, 0.65)', maxWidth: '380px', margin: '0 auto 16px auto', lineHeight: '1.5' }}>
          {isMarathi
            ? 'शेतातील सिंचन घटना, सल्ला शिफारसी किंवा उपग्रह/सेन्सर निरीक्षणांच्या नोंदी उपलब्ध झाल्यावर येथे कालक्रमानुसार दिसतील.'
            : 'Historical irrigation events, agronomic recommendations, and field observations will appear here once recorded.'}
        </p>
        {onRefresh && (
          <button
            type="button"
            onClick={onRefresh}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '10px 18px',
              minHeight: '44px',
              borderRadius: '22px',
              background: 'rgba(255, 255, 255, 0.08)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              color: '#FFFFFF',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <RotateCcw size={14} />
            <span>{isMarathi ? 'पुन्हा तपासा (Refresh)' : 'Check Again'}</span>
          </button>
        )}
      </div>
    );
  }

  // Default: Alerts Empty (Honest statement based on available recommendations)
  return (
    <div
      role="region"
      aria-label={isMarathi ? 'सक्रिय इशारे आढळले नाहीत' : 'No active alerts state'}
      style={{
        textAlign: 'center',
        padding: '40px 20px',
        background: 'rgba(15, 23, 42, 0.50)',
        border: '1px solid rgba(255, 255, 255, 0.12)',
        borderRadius: '16px',
        margin: '16px 0',
      }}
    >
      <div
        style={{
          width: '52px',
          height: '52px',
          borderRadius: '50%',
          background: 'rgba(197, 243, 107, 0.15)',
          border: '1px solid rgba(197, 243, 107, 0.35)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 14px auto',
        }}
      >
        <CheckCircle2 size={28} color="#C5F36B" />
      </div>
      <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#FFFFFF', margin: '0 0 8px 0' }}>
        {isMarathi 
          ? 'सध्या कोणतेही सक्रिय इशारे आढळले नाहीत' 
          : isHindi 
            ? 'वर्तमान में कोई सक्रिय अलर्ट नहीं मिला' 
            : 'No active alerts were found based on the available recommendations.'}
      </h4>
      <p style={{ fontSize: '12.5px', color: 'rgba(255, 255, 255, 0.70)', maxWidth: '420px', margin: '0 auto 16px auto', lineHeight: '1.5' }}>
        {isMarathi
          ? 'उपलब्ध शिफारशींच्या आधारे सध्या कोणतेही सक्रिय इशारे आढळले नाहीत. नवीन सल्ला किंवा तातडीच्या शिफारशी उपलब्ध झाल्यावर येथे सूचित केले जाईल.'
          : 'No active alerts were found based on current farm recommendations. New advisories or critical recommendations will appear here when generated.'}
      </p>
      {onRefresh && (
        <button
          type="button"
          onClick={onRefresh}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '10px 18px',
            minHeight: '44px',
            borderRadius: '22px',
            background: 'rgba(255, 255, 255, 0.08)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            color: '#FFFFFF',
            fontSize: '12px',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          <RotateCcw size={14} />
          <span>{isMarathi ? 'ताजी माहिती मिळवा' : 'Refresh Feed'}</span>
        </button>
      )}
    </div>
  );
}

