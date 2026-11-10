/**
 * FarmShield AI - InsightsDateFilter Component
 * 
 * Provides interactive date range and zone filtering controls.
 * Aligns with backend Query parameters: `start_date`, `end_date`, and `zone_id`.
 */

import React from 'react';
import { Calendar, Filter, Layers, Check } from 'lucide-react';

export default function InsightsDateFilter({
  dateRange = '30d',
  onChangeDateRange,
  zones = [],
  selectedZoneFilter = 'all',
  onChangeZoneFilter,
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';

  const dateOptions = [
    { id: '7d', label_mr: '७ दिवस', label_en: '7 Days' },
    { id: '30d', label_mr: '३० दिवस', label_en: '30 Days' },
    { id: '90d', label_mr: '९० दिवस', label_en: '90 Days' },
    { id: 'all', label_mr: 'सर्व नोंदी', label_en: 'All Time' },
  ];

  return (
    <div
      className="glass-card"
      style={{
        padding: '14px 16px',
        marginBottom: '16px',
        background: 'rgba(7, 31, 22, 0.85)',
        border: '1px solid rgba(197, 243, 107, 0.35)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#C5F36B', fontSize: '12px', fontWeight: 700 }}>
          <Filter size={14} />
          <span>{isMarathi ? 'डेटा फिल्टर (Filter Telemetry)' : 'Telemetry Filters'}</span>
        </div>

        <span style={{ fontSize: '10.5px', color: '#8E9F90' }}>
          {isMarathi ? 'बॅकएंड start_date / zone_id सह थेट संलग्न' : 'Integrated with backend date & zone filters'}
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {/* Quick Date Range Pills */}
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          {dateOptions.map((opt) => {
            const isSelected = dateRange === opt.id;
            return (
              <button
                key={opt.id}
                onClick={() => onChangeDateRange && onChangeDateRange(opt.id)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '5px 12px',
                  borderRadius: '16px',
                  fontSize: '11.5px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  border: isSelected ? '1px solid #C5F36B' : '1px solid rgba(255, 255, 255, 0.16)',
                  background: isSelected ? 'rgba(197, 243, 107, 0.22)' : 'rgba(255, 255, 255, 0.05)',
                  color: isSelected ? '#C5F36B' : '#E2E8F0',
                  transition: 'all 0.2s ease',
                }}
              >
                {isSelected && <Check size={11} strokeWidth={3} />}
                <span>{isMarathi ? opt.label_mr : opt.label_en}</span>
              </button>
            );
          })}
        </div>

        {/* Zone Selector Dropdown */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '11.5px', color: '#CBD5E1', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Layers size={13} color="#38BDF8" />
            <span>{isMarathi ? 'विभाग निवडा:' : 'Filter Zone:'}</span>
          </span>

          <select
            value={selectedZoneFilter}
            onChange={(e) => onChangeZoneFilter && onChangeZoneFilter(e.target.value)}
            style={{
              padding: '6px 12px',
              borderRadius: '10px',
              border: '1px solid rgba(197, 243, 107, 0.35)',
              background: 'rgba(7, 31, 22, 0.95)',
              color: '#FFFFFF',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              outline: 'none',
              minWidth: '160px',
            }}
          >
            <option value="all">{isMarathi ? 'सर्व विभाग (All Zones)' : 'All Zones'}</option>
            {zones.map((z) => (
              <option key={z.id} value={z.id}>
                {z.zone_code || 'ZONE'} • {z.zone_name || z.name}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}

