/**
 * FarmShield AI - AlertCard Component
 * 
 * Displays an active recommendation-derived alert with:
 * - Priority badge (critical, high, or agronomic)
 * - Recommendation title, zone context, and agronomic reasoning
 * - Recommendation status (pending vs accepted)
 * - Independent non-watering agronomic alerts callout
 * - Generated timestamp and expiration information
 * - Local viewed-state indicator and navigation to Recommendation Details
 */

import React from 'react';
import { 
  Clock, 
  MapPin, 
  ChevronRight, 
  ShieldAlert, 
  CheckCircle2, 
  Eye, 
  Calendar,
  AlertTriangle,
  Sparkles,
  Info
} from 'lucide-react';
import RecommendationPriorityBadge from '../../recommendations/components/RecommendationPriorityBadge.jsx';

function formatDate(isoString, lang = 'mr') {
  if (!isoString) return '';
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return '';
    return new Intl.DateTimeFormat(lang === 'en' ? 'en-IN' : 'mr-IN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  } catch {
    return isoString;
  }
}

export default function AlertCard({
  alert,
  isViewed = false,
  onMarkViewed,
  onSelect,
  currentLang = 'mr',
}) {
  if (!alert) return null;

  const isMarathi = currentLang === 'mr';
  const isHindi = currentLang === 'hi';

  const isAccepted = alert.status === 'accepted' || alert.is_accepted;
  // An accepted recommendation is acknowledged by definition; only unviewed pending alerts show the "New" badge
  const showUnreadBadge = !isViewed && !isAccepted;

  const title = currentLang === 'en' ? (alert.title_en || alert.title) : alert.title;
  const description = currentLang === 'en' ? (alert.description_en || alert.description) : alert.description;

  const zoneLabel = alert.zone_code || alert.zone_id || (isMarathi ? 'शेत विभाग' : 'Farm Zone');
  const formattedGeneratedAt = formatDate(alert.generated_at || alert.created_at, currentLang);
  const formattedValidUntil = alert.valid_until ? formatDate(alert.valid_until, currentLang) : null;

  const handleCardClick = () => {
    if (onMarkViewed && alert.id) {
      onMarkViewed(alert.id);
    }
    if (onSelect && (alert.recommendation_id || alert.id)) {
      onSelect(alert.recommendation_id || alert.id);
    }
  };

  const handleQuickMarkViewed = (e) => {
    e.stopPropagation();
    if (onMarkViewed && alert.id) {
      onMarkViewed(alert.id);
    }
  };

  return (
    <article
      role="article"
      aria-label={`${alert.priority || 'medium'} alert: ${title}`}
      onClick={handleCardClick}
      style={{
        background: isAccepted
          ? 'rgba(10, 30, 20, 0.65)'
          : showUnreadBadge
            ? 'rgba(20, 35, 25, 0.75)'
            : 'rgba(15, 23, 42, 0.60)',
        backdropFilter: 'blur(12px)',
        border: showUnreadBadge
          ? '1px solid rgba(197, 243, 107, 0.45)'
          : isAccepted
            ? '1px solid rgba(34, 197, 94, 0.35)'
            : '1px solid rgba(255, 255, 255, 0.12)',
        borderRadius: '16px',
        padding: '16px',
        marginBottom: '12px',
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        boxShadow: showUnreadBadge 
          ? '0 4px 20px rgba(197, 243, 107, 0.12)' 
          : '0 4px 16px rgba(0, 0, 0, 0.25)',
        position: 'relative',
      }}
      className="alert-card-interactive"
    >
      {/* Top Meta Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', flexWrap: 'wrap', marginBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {/* Priority Badge */}
          <RecommendationPriorityBadge
            priority={alert.priority || 'medium'}
            currentLang={currentLang}
            size="sm"
          />

          {/* Unread / New Indicator */}
          {showUnreadBadge && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                padding: '2px 8px',
                borderRadius: '12px',
                background: 'rgba(56, 189, 248, 0.22)',
                border: '1px solid rgba(56, 189, 248, 0.6)',
                color: '#38BDF8',
                fontSize: '10.5px',
                fontWeight: 700,
              }}
            >
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#38BDF8' }} />
              {isMarathi ? 'नवीन' : isHindi ? 'नया' : 'New'}
            </span>
          )}

          {/* Status Badge: Pending vs Accepted */}
          {isAccepted ? (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                padding: '2px 8px',
                borderRadius: '12px',
                background: 'rgba(34, 197, 94, 0.18)',
                border: '1px solid rgba(34, 197, 94, 0.5)',
                color: '#4ADE80',
                fontSize: '10.5px',
                fontWeight: 600,
              }}
            >
              <CheckCircle2 size={11} />
              {isMarathi ? 'स्वीकारले / कृती नियोजित' : isHindi ? 'स्वीकार किया गया' : 'Accepted / Planned'}
            </span>
          ) : (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                padding: '2px 8px',
                borderRadius: '12px',
                background: 'rgba(245, 158, 11, 0.15)',
                border: '1px solid rgba(245, 158, 11, 0.4)',
                color: '#FBBF24',
                fontSize: '10.5px',
                fontWeight: 600,
              }}
            >
              <Clock size={11} />
              {isMarathi ? 'पुनरावलोकन बाकी' : isHindi ? 'समीक्षा लंबित' : 'Awaiting Review'}
            </span>
          )}

          {/* Simulated / Demo badge */}
          {alert.is_simulated && (
            <span
              style={{
                padding: '2px 6px',
                borderRadius: '6px',
                background: 'rgba(255, 255, 255, 0.08)',
                color: 'rgba(255, 255, 255, 0.55)',
                fontSize: '9.5px',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
              }}
            >
              {isMarathi ? 'नमुना' : 'Simulated'}
            </span>
          )}
        </div>

        {/* Zone Context Tag */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            color: '#C5F36B',
            fontSize: '11px',
            fontWeight: 700,
          }}
        >
          <MapPin size={12} />
          <span>{zoneLabel}</span>
        </div>
      </div>

      {/* Alert Title */}
      <h3
        style={{
          fontSize: '15px',
          fontWeight: 700,
          color: '#FFFFFF',
          margin: '0 0 8px 0',
          lineHeight: '1.4',
        }}
      >
        {title}
      </h3>

      {/* Description / Summary */}
      {description && (
        <p
          style={{
            fontSize: '12.5px',
            color: 'rgba(255, 255, 255, 0.78)',
            lineHeight: '1.5',
            margin: '0 0 10px 0',
          }}
        >
          {description}
        </p>
      )}

      {/* Independent Agronomic Alerts Callout (Distinct Non-Watering Advisory) */}
      {alert.has_independent_alerts && Array.isArray(alert.independent_alerts) && alert.independent_alerts.length > 0 && (
        <div
          style={{
            background: 'rgba(249, 115, 22, 0.15)',
            border: '1px solid rgba(249, 115, 22, 0.45)',
            borderRadius: '10px',
            padding: '8px 12px',
            marginBottom: '10px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '8px',
          }}
        >
          <AlertTriangle size={15} color="#F97316" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#FB923C', display: 'block', marginBottom: '2px' }}>
              {isMarathi ? 'स्वतंत्र कृषी इशारा (Non-Watering Advisory)' : 'Independent Agronomic Advisory'}
            </span>
            <ul style={{ margin: 0, paddingLeft: '14px', fontSize: '11.5px', color: '#FED7AA' }}>
              {alert.independent_alerts.map((item, idx) => (
                <li key={idx} style={{ marginBottom: idx < alert.independent_alerts.length - 1 ? '2px' : 0 }}>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Supporting Evidence / Decision Factors Pills */}
      {alert.stress_reasons && alert.stress_reasons.length > 0 && !alert.has_independent_alerts && (
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '10px' }}>
          {alert.stress_reasons.map((factor, idx) => (
            <span
              key={idx}
              style={{
                fontSize: '10.5px',
                padding: '2px 8px',
                borderRadius: '8px',
                background: 'rgba(255, 255, 255, 0.08)',
                color: 'rgba(255, 255, 255, 0.75)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
              }}
            >
              • {factor.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      )}

      {/* Bottom Footer: Timestamps & Action */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '8px',
          paddingTop: '8px',
          borderTop: '1px solid rgba(255, 255, 255, 0.08)',
          fontSize: '11px',
          color: 'rgba(255, 255, 255, 0.55)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {/* Generation Date */}
          {formattedGeneratedAt && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              <Clock size={11} />
              <span>{formattedGeneratedAt}</span>
            </span>
          )}

          {/* Expiration Date if present */}
          {formattedValidUntil && (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#FCD34D' }}>
              <Calendar size={11} />
              <span>{isMarathi ? `वैधता: ${formattedValidUntil}` : `Valid until: ${formattedValidUntil}`}</span>
            </span>
          )}
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Quick Mark Viewed Action */}
          {showUnreadBadge && (
            <button
              type="button"
              onClick={handleQuickMarkViewed}
              title={isMarathi ? 'पाहिले म्हणून नोंदवा' : 'Mark as viewed'}
              style={{
                background: 'rgba(255, 255, 255, 0.08)',
                border: '1px solid rgba(255, 255, 255, 0.16)',
                color: 'rgba(255, 255, 255, 0.85)',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                fontSize: '11px',
                fontWeight: 600,
                padding: '6px 12px',
                minHeight: '44px',
                borderRadius: '8px',
                transition: 'all 0.15s ease',
              }}
            >
              <Eye size={13} />
              <span>{isMarathi ? 'पाहिले' : 'Mark seen'}</span>
            </button>
          )}

          {/* Details CTA Link */}
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              color: '#C5F36B',
              fontWeight: 700,
              fontSize: '12px',
              minHeight: '44px',
              padding: '0 4px',
            }}
          >
            <span>{isMarathi ? 'सल्ला व पुरावा' : 'View Details'}</span>
            <ChevronRight size={14} />
          </span>
        </div>
      </div>
    </article>
  );
}

