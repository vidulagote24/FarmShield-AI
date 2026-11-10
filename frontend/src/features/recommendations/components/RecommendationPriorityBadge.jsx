/**
 * FarmShield AI - RecommendationPriorityBadge Component
 * 
 * Accessible, WCAG 2.2 AA compliant badge pairing priority level with color, icon, and text.
 * Supports: critical, high, medium, low.
 */

import React from 'react';
import { AlertOctagon, AlertTriangle, Info, CheckCircle2, ShieldAlert } from 'lucide-react';

export const PRIORITY_CONFIG = {
  critical: {
    color: '#EF4444',
    bg: 'rgba(239, 68, 68, 0.20)',
    border: 'rgba(239, 68, 68, 0.65)',
    icon: AlertOctagon,
    label_en: 'Critical Priority',
    label_mr: 'अति तातडीचे (Critical)',
    label_hi: 'अति गंभीर (Critical)',
  },
  high: {
    color: '#F97316',
    bg: 'rgba(249, 115, 22, 0.20)',
    border: 'rgba(249, 115, 22, 0.65)',
    icon: AlertTriangle,
    label_en: 'High Priority',
    label_mr: 'उच्च प्राधान्य (High)',
    label_hi: 'उच्च प्राथमिकता (High)',
  },
  medium: {
    color: '#F59E0B',
    bg: 'rgba(245, 158, 11, 0.20)',
    border: 'rgba(245, 158, 11, 0.65)',
    icon: Info,
    label_en: 'Medium Priority',
    label_mr: 'मध्यम प्राधान्य (Medium)',
    label_hi: 'मध्यम प्राथमिकता (Medium)',
  },
  low: {
    color: '#22C55E',
    bg: 'rgba(34, 197, 94, 0.20)',
    border: 'rgba(34, 197, 94, 0.65)',
    icon: CheckCircle2,
    label_en: 'Low Priority / Routine',
    label_mr: 'कमी / नियमित (Routine)',
    label_hi: 'कम / सामान्य (Routine)',
  },
};

export default function RecommendationPriorityBadge({
  priority = 'medium',
  currentLang = 'mr',
  size = 'md',
}) {
  const normPriority = (priority || 'medium').toLowerCase();
  const config = PRIORITY_CONFIG[normPriority] || PRIORITY_CONFIG.medium;
  const IconComponent = config.icon;

  const isSmall = size === 'sm';
  const isLarge = size === 'lg';

  const label = currentLang === 'mr' 
    ? config.label_mr 
    : currentLang === 'hi' 
      ? config.label_hi 
      : config.label_en;

  return (
    <span
      className="inline-flex items-center"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: isSmall ? '4px' : '6px',
        padding: isSmall ? '2px 8px' : isLarge ? '6px 14px' : '4px 10px',
        borderRadius: '20px',
        background: config.bg,
        border: `1px solid ${config.border}`,
        color: config.color,
        fontSize: isSmall ? '10.5px' : isLarge ? '13px' : '11.5px',
        fontWeight: 800,
        letterSpacing: '0.2px',
        textTransform: 'uppercase',
        boxShadow: `0 2px 8px ${config.bg}`,
      }}
      role="status"
      aria-label={`Priority level: ${label}`}
    >
      <IconComponent size={isSmall ? 11 : isLarge ? 15 : 13} color={config.color} />
      <span>{label}</span>
    </span>
  );
}

