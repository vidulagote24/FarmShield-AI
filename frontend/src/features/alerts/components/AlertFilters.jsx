/**
 * FarmShield AI - AlertFilters Component
 * 
 * Accessible filter controls allowing farmers to filter active alerts by:
 * - All (सर्व)
 * - Critical (अति तातडीचे)
 * - High (उच्च प्राधान्य)
 * - Independent Agronomic Advisories (इतर कृषी इशारे)
 */

import React from 'react';
import { AlertOctagon, AlertTriangle, Layers, Sprout } from 'lucide-react';

export default function AlertFilters({
  currentFilter = 'all',
  onFilterChange,
  counts = {},
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';
  const isHindi = currentLang === 'hi';

  const filterOptions = [
    {
      id: 'all',
      label: isMarathi ? 'सर्व' : isHindi ? 'सभी' : 'All',
      count: counts.all || 0,
      icon: Layers,
      color: '#FFFFFF',
      activeColor: '#C5F36B',
    },
    {
      id: 'critical',
      label: isMarathi ? 'अति तातडीचे' : isHindi ? 'अति गंभीर' : 'Critical',
      count: counts.critical || 0,
      icon: AlertOctagon,
      color: '#EF4444',
      activeColor: '#EF4444',
    },
    {
      id: 'high',
      label: isMarathi ? 'उच्च' : isHindi ? 'उच्च' : 'High',
      count: counts.high || 0,
      icon: AlertTriangle,
      color: '#F97316',
      activeColor: '#F97316',
    },
    {
      id: 'agronomic',
      label: isMarathi ? 'इतर कृषी' : isHindi ? 'कृषि' : 'Agronomic',
      count: counts.agronomic || 0,
      icon: Sprout,
      color: '#34D399',
      activeColor: '#34D399',
    },
  ];

  return (
    <div
      role="region"
      aria-label={isMarathi ? 'इशारे प्राधान्य फिल्टर्स' : 'Alert priority filters'}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        overflowX: 'auto',
        WebkitOverflowScrolling: 'touch',
        padding: '4px 2px 8px 2px',
        marginBottom: '16px',
        scrollbarWidth: 'none',
        maxWidth: '100%',
      }}
      className="alerts-filter-bar"
    >
      {filterOptions.map((opt) => {
        const isActive = currentFilter === opt.id;
        const IconComponent = opt.icon;

        return (
          <button
            key={opt.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onFilterChange && onFilterChange(opt.id)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              minHeight: '44px',
              minWidth: '44px',
              borderRadius: '22px',
              border: isActive 
                ? `1px solid ${opt.activeColor}` 
                : '1px solid rgba(255, 255, 255, 0.15)',
              background: isActive 
                ? `rgba(255, 255, 255, 0.12)` 
                : 'rgba(255, 255, 255, 0.04)',
              color: isActive ? opt.activeColor : 'rgba(255, 255, 255, 0.75)',
              fontSize: '12px',
              fontWeight: isActive ? 700 : 500,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'all 0.18s ease',
              touchAction: 'manipulation',
            }}
          >
            <IconComponent size={14} color={isActive ? opt.activeColor : 'rgba(255, 255, 255, 0.6)'} />
            <span>{opt.label}</span>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                minWidth: '20px',
                height: '20px',
                padding: '0 5px',
                borderRadius: '10px',
                fontSize: '10.5px',
                fontWeight: 700,
                background: isActive ? opt.activeColor : 'rgba(255, 255, 255, 0.1)',
                color: isActive ? '#0A2B1C' : 'rgba(255, 255, 255, 0.7)',
                marginLeft: '2px',
              }}
            >
              {opt.count}
            </span>
          </button>
        );
      })}
    </div>
  );
}

