import React from 'react';
import { ArrowRight, Sparkles } from 'lucide-react';

export default function RecommendationCard({
  icon: Icon,
  badgeText,
  badgeType = 'success', // success | warning | info | danger
  title,
  description,
  actionText,
  onAction,
  stats,
  footerNote
}) {
  const badgeStyles = {
    success: { 
      bg: 'rgba(105, 217, 138, 0.18)', 
      color: '#69D98A', 
      border: 'rgba(105, 217, 138, 0.35)' 
    },
    warning: { 
      bg: 'rgba(255, 195, 77, 0.18)', 
      color: '#FFC34D', 
      border: 'rgba(255, 195, 77, 0.35)' 
    },
    info: { 
      bg: 'rgba(56, 189, 248, 0.18)', 
      color: '#38BDF8', 
      border: 'rgba(56, 189, 248, 0.35)' 
    },
    danger: { 
      bg: 'rgba(239, 68, 68, 0.18)', 
      color: '#F87171', 
      border: 'rgba(239, 68, 68, 0.35)' 
    }
  };

  const currentBadge = badgeStyles[badgeType] || badgeStyles.success;

  return (
    <div className="glass-card" style={{ marginBottom: '14px', position: 'relative' }}>
      {/* Top row with badge & icon */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {Icon && (
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '12px',
              background: currentBadge.bg,
              border: `1px solid ${currentBadge.border}`,
              color: currentBadge.color,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: `0 0 10px ${currentBadge.bg}`
            }}>
              <Icon size={18} />
            </div>
          )}
          <span style={{
            fontSize: '15px',
            fontWeight: 800,
            color: '#FFFFFF',
            letterSpacing: '-0.2px'
          }}>
            {title}
          </span>
        </div>

        {badgeText && (
          <span className="status-pill" style={{
            background: currentBadge.bg,
            border: `1px solid ${currentBadge.border}`,
            color: currentBadge.color
          }}>
            <Sparkles size={12} />
            {badgeText}
          </span>
        )}
      </div>

      {/* Description text */}
      {description && (
        <p style={{
          fontSize: '13px',
          color: '#D5E3D9',
          lineHeight: '1.5',
          marginBottom: stats ? '12px' : (actionText ? '12px' : '4px')
        }}>
          {description}
        </p>
      )}

      {/* Optional Stats row */}
      {stats && stats.length > 0 && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${stats.length}, 1fr)`,
          gap: '8px',
          padding: '10px',
          background: 'rgba(255, 255, 255, 0.08)',
          backdropFilter: 'blur(10px)',
          borderRadius: '14px',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          marginBottom: '12px'
        }}>
          {stats.map((s, idx) => (
            <div key={idx} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: '#B6C8BB', fontWeight: 600 }}>{s.label}</div>
              <div style={{ fontSize: '14px', fontWeight: 800, color: '#FFFFFF', marginTop: '2px' }}>{s.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Action button */}
      {actionText && (
        <button
          onClick={onAction}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            width: '100%',
            padding: '11px 16px',
            background: 'rgba(255, 255, 255, 0.10)',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(255, 255, 255, 0.18)',
            borderRadius: '14px',
            color: '#C5F36B',
            fontSize: '13px',
            fontWeight: 800,
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
        >
          <span>{actionText}</span>
          <ArrowRight size={16} />
        </button>
      )}

      {footerNote && (
        <div style={{
          fontSize: '11px',
          color: '#A3B8A8',
          marginTop: '8px',
          display: 'flex',
          alignItems: 'center',
          gap: '4px'
        }}>
          {footerNote}
        </div>
      )}
    </div>
  );
}
