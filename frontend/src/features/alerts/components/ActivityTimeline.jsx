/**
 * FarmShield AI - ActivityTimeline Component
 * 
 * Chronological timeline aggregating:
 * 1. Irrigation events (water volume/depth applied, method, zone)
 * 2. Recommendations & advisories (status, priority, action planned)
 * 3. Field & satellite observations (soil moisture, NDVI, quality)
 * 
 * Strict Agronomic & Data Integrity:
 * - Missing telemetry values are NEVER coerced to 0; rendered as "अपुरा डेटा (Missing/Unreadable)".
 * - Simulated demo records carry an explicit "नमुना डेटा" badge.
 * - Source-specific errors are surfaced honestly without claiming complete data.
 */

import React from 'react';
import { 
  Droplets, 
  Lightbulb, 
  Activity, 
  MapPin, 
  Calendar, 
  Clock, 
  AlertTriangle, 
  CheckCircle2, 
  ChevronRight,
  Radio,
  Satellite,
  HelpCircle,
  XCircle
} from 'lucide-react';

function formatEventTimestamp(isoString, lang = 'mr') {
  if (!isoString) return '';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return '';
    return new Intl.DateTimeFormat(lang === 'en' ? 'en-IN' : 'mr-IN', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(d);
  } catch {
    return isoString;
  }
}

export default function ActivityTimeline({
  items = [],
  currentLang = 'mr',
  isPartialData = false,
  sourceErrors = {},
  onSelectRecommendation,
}) {
  const isMarathi = currentLang === 'mr';
  const isHindi = currentLang === 'hi';

  const hasSourceErrors = Object.keys(sourceErrors).length > 0;

  return (
    <div className="activity-timeline-container" style={{ position: 'relative' }}>
      {/* Partial Data Notice when any source failed */}
      {(hasSourceErrors || isPartialData) && (
        <div
          role="alert"
          style={{
            background: 'rgba(245, 158, 11, 0.15)',
            border: '1px solid rgba(245, 158, 11, 0.45)',
            borderRadius: '12px',
            padding: '10px 14px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '10px',
            fontSize: '11.5px',
            color: '#FDE68A',
          }}
        >
          <AlertTriangle size={16} color="#F59E0B" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <span style={{ fontWeight: 700, display: 'block', marginBottom: '2px' }}>
              {isMarathi ? 'अपूर्ण इतिहास नोंद (Partial Data Notice)' : 'Partial History Dataset'}
            </span>
            <span>
              {isMarathi
                ? 'काही स्त्रोतांकडील नोंदी तात्पुरत्या अनुपलब्ध आहेत. केवळ यशस्वीरित्या प्राप्त झालेल्या नोंदी खाली दाखवल्या आहेत.'
                : 'Some activity sources were temporarily unreachable. Only successfully retrieved historical records are displayed below.'}
            </span>
            {hasSourceErrors && (
              <ul style={{ margin: '4px 0 0 0', paddingLeft: '16px', color: '#FEF3C7', fontSize: '11px' }}>
                {Object.entries(sourceErrors).map(([src, msg]) => (
                  <li key={src}>
                    <strong>{src}:</strong> {msg}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}

      {/* Timeline List */}
      <div
        style={{
          position: 'relative',
          paddingLeft: '24px',
          borderLeft: '2px solid rgba(197, 243, 107, 0.25)',
          marginLeft: '8px',
        }}
      >
        {items.map((item, index) => {
          const type = item.type; // 'irrigation' | 'recommendation' | 'observation'
          const occurredTime = formatEventTimestamp(item.occurred_at, currentLang);
          const zoneText = item.zone_id ? (item.zone_id.replace('z3-south-west-003', 'Zone C').replace('z2-north-east-002', 'Zone B').replace('z1-north-west-001', 'Zone A').replace('z4-south-east-004', 'Zone D')) : null;

          // Theme config per type
          let typeColor = '#C5F36B';
          let typeBg = 'rgba(197, 243, 107, 0.15)';
          let typeLabel = isMarathi ? 'शेत नोंद' : 'Activity';
          let TypeIcon = Activity;

          if (type === 'irrigation') {
            typeColor = '#38BDF8';
            typeBg = 'rgba(56, 189, 248, 0.18)';
            typeLabel = isMarathi ? 'सिंचन नोंद' : isHindi ? 'सिंचाई रिकॉर्ड' : 'Irrigation';
            TypeIcon = Droplets;
          } else if (type === 'recommendation') {
            typeColor = '#A78BFA';
            typeBg = 'rgba(167, 139, 250, 0.18)';
            typeLabel = isMarathi ? 'सल्ला / शिफारस' : isHindi ? 'सिफारिश' : 'Recommendation';
            TypeIcon = Lightbulb;
          } else if (type === 'observation') {
            typeColor = '#34D399';
            typeBg = 'rgba(52, 211, 153, 0.18)';
            typeLabel = isMarathi ? 'शेत निरीक्षण' : isHindi ? 'खेत अवलोकन' : 'Observation';
            TypeIcon = item.source?.toLowerCase().includes('satellite') || item.source?.toLowerCase().includes('sentinel') 
              ? Satellite 
              : Radio;
          }

          const isClickable = type === 'recommendation' && onSelectRecommendation && item.id;

          return (
            <div
              key={item.composite_id || `${item.type}-${item.id}-${index}`}
              style={{
                position: 'relative',
                marginBottom: '20px',
              }}
            >
              {/* Timeline Marker Pin */}
              <div
                style={{
                  position: 'absolute',
                  left: '-32px',
                  top: '12px',
                  width: '16px',
                  height: '16px',
                  borderRadius: '50%',
                  background: typeColor,
                  border: '3px solid #0A2B1C',
                  boxShadow: `0 0 8px ${typeColor}66`,
                }}
              />

              {/* Item Card */}
              <div
                onClick={() => {
                  if (isClickable) {
                    onSelectRecommendation(item.id);
                  }
                }}
                style={{
                  background: 'rgba(15, 23, 42, 0.55)',
                  backdropFilter: 'blur(10px)',
                  border: '1px solid rgba(255, 255, 255, 0.10)',
                  borderRadius: '14px',
                  padding: '14px',
                  cursor: isClickable ? 'pointer' : 'default',
                  transition: 'all 0.18s ease',
                  boxShadow: '0 4px 14px rgba(0, 0, 0, 0.2)',
                }}
                className={isClickable ? 'timeline-item-interactive' : ''}
              >
                {/* Meta Header */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '6px',
                    marginBottom: '8px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                    {/* Record Type Pill */}
                    <span
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        padding: '2px 8px',
                        borderRadius: '10px',
                        background: typeBg,
                        border: `1px solid ${typeColor}55`,
                        color: typeColor,
                        fontSize: '10.5px',
                        fontWeight: 700,
                      }}
                    >
                      <TypeIcon size={11} />
                      <span>{typeLabel}</span>
                    </span>

                    {/* Status Badge */}
                    {item.status && (
                      <span
                        style={{
                          fontSize: '10px',
                          fontWeight: 600,
                          padding: '2px 6px',
                          borderRadius: '6px',
                          background: item.status === 'completed' || item.status === 'applied' || item.status === 'verified'
                            ? 'rgba(34, 197, 94, 0.15)'
                            : item.status === 'accepted'
                              ? 'rgba(56, 189, 248, 0.15)'
                              : item.status === 'pending'
                                ? 'rgba(251, 191, 36, 0.15)'
                                : item.status === 'dismissed' || item.status === 'rejected'
                                  ? 'rgba(148, 163, 184, 0.15)'
                                  : item.status === 'expired'
                                    ? 'rgba(248, 113, 113, 0.15)'
                                    : item.status === 'superseded'
                                      ? 'rgba(192, 132, 252, 0.15)'
                                      : item.status === 'unreadable'
                                        ? 'rgba(239, 68, 68, 0.15)'
                                        : 'rgba(255, 255, 255, 0.08)',
                          color: item.status === 'completed' || item.status === 'applied' || item.status === 'verified'
                            ? '#4ADE80'
                            : item.status === 'accepted'
                              ? '#38BDF8'
                              : item.status === 'pending'
                                ? '#FBBF24'
                                : item.status === 'dismissed' || item.status === 'rejected'
                                  ? '#94A3B8'
                                  : item.status === 'expired'
                                    ? '#F87171'
                                    : item.status === 'superseded'
                                      ? '#C084FC'
                                      : item.status === 'unreadable'
                                        ? '#FCA5A5'
                                        : 'rgba(255, 255, 255, 0.7)',
                          border: '1px solid rgba(255, 255, 255, 0.1)',
                          textTransform: 'capitalize',
                        }}
                      >
                        {item.status}
                      </span>
                    )}

                    {/* Simulated Indicator */}
                    {item.is_simulated && (
                      <span
                        style={{
                          fontSize: '9.5px',
                          padding: '1px 5px',
                          borderRadius: '4px',
                          background: 'rgba(255, 255, 255, 0.06)',
                          color: 'rgba(255, 255, 255, 0.45)',
                          textTransform: 'uppercase',
                        }}
                      >
                        {isMarathi ? 'नमुना' : 'Simulated'}
                      </span>
                    )}
                  </div>

                  {/* Timestamp */}
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      color: 'rgba(255, 255, 255, 0.55)',
                      fontSize: '10.5px',
                    }}
                  >
                    <Clock size={11} />
                    <span>{occurredTime}</span>
                  </span>
                </div>

                {/* Title */}
                <h4
                  style={{
                    fontSize: '13.5px',
                    fontWeight: 700,
                    color: '#FFFFFF',
                    margin: '0 0 6px 0',
                    lineHeight: '1.4',
                  }}
                >
                  {item.title}
                </h4>

                {/* Description or Details */}
                {item.description && (
                  <p
                    style={{
                      fontSize: '12px',
                      color: 'rgba(255, 255, 255, 0.75)',
                      lineHeight: '1.45',
                      margin: '0 0 8px 0',
                    }}
                  >
                    {item.description}
                  </p>
                )}

                {/* Specific Details based on item type */}
                {type === 'observation' && item.value === null && (
                  <div
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '4px 8px',
                      borderRadius: '8px',
                      background: 'rgba(239, 68, 68, 0.12)',
                      border: '1px solid rgba(239, 68, 68, 0.35)',
                      color: '#FCA5A5',
                      fontSize: '11px',
                      marginBottom: '6px',
                    }}
                  >
                    <HelpCircle size={12} />
                    <span>{isMarathi ? 'अपुरा डेटा: सेन्सर तपासणी आवश्यक' : 'Missing telemetry: Sensor ground check required'}</span>
                  </div>
                )}

                {/* Footer with Zone and Source */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '6px',
                    paddingTop: '6px',
                    borderTop: '1px solid rgba(255, 255, 255, 0.06)',
                    fontSize: '10.5px',
                    color: 'rgba(255, 255, 255, 0.5)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    {zoneText && (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px', color: '#C5F36B' }}>
                        <MapPin size={10} />
                        <span>{zoneText}</span>
                      </span>
                    )}
                    {item.source && (
                      <span>
                        {isMarathi ? 'स्रोत: ' : 'Source: '}
                        {item.source}
                      </span>
                    )}
                  </div>

                  {isClickable && (
                    <span
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '2px',
                        color: '#C5F36B',
                        fontWeight: 600,
                        fontSize: '11px',
                      }}
                    >
                      <span>{isMarathi ? 'तपशील' : 'Details'}</span>
                      <ChevronRight size={12} />
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

