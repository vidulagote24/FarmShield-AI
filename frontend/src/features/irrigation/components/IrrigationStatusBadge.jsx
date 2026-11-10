/**
 * FarmShield AI - IrrigationStatusBadge Component
 * 
 * Reusable accessible status badge for irrigation priorities, action codes,
 * and event confirmation states.
 * 
 * Adheres strictly to WCAG 2.2 AA: Never conveys meaning through color alone.
 */

import React from 'react';
import { 
  CheckCircle2, 
  AlertTriangle, 
  AlertCircle, 
  Clock, 
  Droplets, 
  PauseCircle, 
  Eye, 
  HelpCircle,
  ShieldCheck
} from 'lucide-react';

export const PRIORITY_CONFIG = {
  critical: {
    color: '#EF4444',
    bg: 'rgba(239, 68, 68, 0.18)',
    border: 'rgba(239, 68, 68, 0.45)',
    icon: AlertCircle,
    label_en: 'Critical',
    label_mr: 'अति तातडीचे',
  },
  high: {
    color: '#F97316',
    bg: 'rgba(249, 115, 22, 0.18)',
    border: 'rgba(249, 115, 22, 0.45)',
    icon: AlertTriangle,
    label_en: 'High Priority',
    label_mr: 'उच्च प्राधान्य',
  },
  medium: {
    color: '#F59E0B',
    bg: 'rgba(245, 158, 11, 0.18)',
    border: 'rgba(245, 158, 11, 0.45)',
    icon: Clock,
    label_en: 'Medium Priority',
    label_mr: 'मध्यम प्राधान्य',
  },
  low: {
    color: '#22C55E',
    bg: 'rgba(34, 197, 94, 0.18)',
    border: 'rgba(34, 197, 94, 0.45)',
    icon: CheckCircle2,
    label_en: 'Low / Optimal',
    label_mr: 'कमी / पुरेसा ओलावा',
  },
};

export const ACTION_CONFIG = {
  irrigate: {
    color: '#38BDF8',
    bg: 'rgba(56, 189, 248, 0.18)',
    border: 'rgba(56, 189, 248, 0.45)',
    icon: Droplets,
    label_en: 'Irrigate Now',
    label_mr: 'पाणी द्या (Irrigate)',
  },
  wait: {
    color: '#FFC34D',
    bg: 'rgba(255, 195, 77, 0.18)',
    border: 'rgba(255, 195, 77, 0.45)',
    icon: PauseCircle,
    label_en: 'Wait / Postpone',
    label_mr: 'थांबा (Wait)',
  },
  monitor: {
    color: '#38BDF8',
    bg: 'rgba(56, 189, 248, 0.15)',
    border: 'rgba(56, 189, 248, 0.40)',
    icon: Eye,
    label_en: 'Monitor Soil Probe',
    label_mr: 'निरीक्षण करा',
  },
  inspect: {
    color: '#F87171',
    bg: 'rgba(248, 113, 113, 0.18)',
    border: 'rgba(248, 113, 113, 0.45)',
    icon: AlertTriangle,
    label_en: 'Field Inspection Required',
    label_mr: 'प्रत्यक्ष शेतात तपासणी',
  },
  insufficient_data: {
    color: '#94A3B8',
    bg: 'rgba(148, 163, 184, 0.18)',
    border: 'rgba(148, 163, 184, 0.40)',
    icon: HelpCircle,
    label_en: 'Insufficient Telemetry',
    label_mr: 'अपुरा डेटा',
  },
};

export default function IrrigationStatusBadge({
  type = 'priority', // 'priority' | 'action' | 'confirmation'
  value,
  currentLang = 'mr',
  size = 'medium',
}) {
  const isMarathi = currentLang === 'mr';

  if (type === 'action') {
    const config = ACTION_CONFIG[value] || ACTION_CONFIG.wait;
    const Icon = config.icon;
    return (
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '5px',
          padding: size === 'small' ? '2px 7px' : '4px 10px',
          borderRadius: '12px',
          fontSize: size === 'small' ? '10px' : '11.5px',
          fontWeight: 800,
          color: config.color,
          background: config.bg,
          border: `1px solid ${config.border}`,
          textTransform: 'none',
        }}
      >
        <Icon size={size === 'small' ? 11 : 13} />
        <span>{isMarathi ? config.label_mr : config.label_en}</span>
      </span>
    );
  }

  if (type === 'confirmation') {
    const isSimulated = value === 'simulated';
    return (
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '5px',
          padding: '2px 8px',
          borderRadius: '10px',
          fontSize: '10.5px',
          fontWeight: 800,
          color: isSimulated ? '#FBBF24' : '#22C55E',
          background: isSimulated ? 'rgba(245, 158, 11, 0.18)' : 'rgba(34, 197, 94, 0.18)',
          border: isSimulated ? '1px solid rgba(245, 158, 11, 0.45)' : '1px solid rgba(34, 197, 94, 0.45)',
        }}
      >
        <CheckCircle2 size={12} />
        <span>{isSimulated ? (isMarathi ? 'नमुना नोंद' : 'Simulated Record') : (isMarathi ? 'नोंद सेव्ह झाली' : 'Saved to Backend')}</span>
      </span>
    );
  }

  // Default: Priority
  const config = PRIORITY_CONFIG[value] || PRIORITY_CONFIG.medium;
  const Icon = config.icon;

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '5px',
        padding: size === 'small' ? '2px 7px' : '3px 9px',
        borderRadius: '12px',
        fontSize: size === 'small' ? '10px' : '11px',
        fontWeight: 800,
        color: config.color,
        background: config.bg,
        border: `1px solid ${config.border}`,
        textTransform: 'uppercase',
      }}
    >
      <Icon size={size === 'small' ? 10 : 12} />
      <span>{isMarathi ? config.label_mr : config.label_en}</span>
    </span>
  );
}

