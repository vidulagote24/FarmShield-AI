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
    success: { bg: 'var(--success-bg)', color: 'var(--success)' },
    warning: { bg: 'var(--warning-bg)', color: '#B45309' },
    info: { bg: 'var(--info-bg)', color: 'var(--info)' },
    danger: { bg: 'var(--danger-bg)', color: 'var(--danger)' }
  };

  const currentBadge = badgeStyles[badgeType] || badgeStyles.success;

  return (
    <div className="farmer-card" style={{ marginBottom: '14px', position: 'relative' }}>
      {/* Top row with badge & icon */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {Icon && (
            <div style={{
              width: '34px',
              height: '34px',
              borderRadius: '10px',
              background: currentBadge.bg,
              color: currentBadge.color,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Icon size={18} />
            </div>
          )}
          <span style={{
            fontSize: '15px',
            fontWeight: 800,
            color: 'var(--text-main)'
          }}>
            {title}
          </span>
        </div>

        {badgeText && (
          <span className="status-pill" style={{
            background: currentBadge.bg,
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
          fontSize: '13.5px',
          color: 'var(--text-muted)',
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
          background: 'var(--bg-main)',
          borderRadius: '12px',
          marginBottom: '12px'
        }}>
          {stats.map((s, idx) => (
            <div key={idx} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>{s.label}</div>
              <div style={{ fontSize: '14px', fontWeight: 800, color: 'var(--text-main)', marginTop: '2px' }}>{s.value}</div>
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
            padding: '10px 14px',
            background: 'var(--primary-light)',
            border: 'none',
            borderRadius: '12px',
            color: 'var(--primary-dark)',
            fontSize: '13px',
            fontWeight: 700,
            cursor: 'pointer',
            transition: 'background 0.15s ease'
          }}
        >
          <span>{actionText}</span>
          <ArrowRight size={16} />
        </button>
      )}

      {footerNote && (
        <div style={{
          fontSize: '11px',
          color: 'var(--text-light)',
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
