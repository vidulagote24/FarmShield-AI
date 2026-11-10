/**
 * FarmShield AI - IrrigationHistoryList Component
 * 
 * Displays historical completed irrigation events retrieved from
 * `GET /api/v1/farms/{farm_id}/irrigation-events`.
 * 
 * Strict Data Integrity:
 * - Does not invent historical activities.
 * - Displays exact recorded values, timestamps, and farmer notes.
 */

import React from 'react';
import { History, Calendar, Droplets, Clock, FileText, CheckCircle2 } from 'lucide-react';
import IrrigationStatusBadge from './IrrigationStatusBadge.jsx';
import IrrigationEmptyState from './IrrigationEmptyState.jsx';

export default function IrrigationHistoryList({
  history = [],
  zones = [],
  currentLang = 'mr',
  isDemoMode = false,
}) {
  const isMarathi = currentLang === 'mr';

  const formatTimestamp = (ts) => {
    if (!ts) return isMarathi ? 'दिनांक अनुपलब्ध' : 'Timestamp missing';
    try {
      const d = new Date(ts);
      return `${d.toLocaleDateString()} at ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } catch (e) {
      return String(ts);
    }
  };

  const getZoneLabel = (zoneId) => {
    if (!zoneId) return isMarathi ? 'सर्व शेत (Whole Farm)' : 'Whole Farm';
    const match = zones.find((z) => z.id === zoneId);
    return match ? (match.zone_code || match.zone_name) : (isMarathi ? 'व्यवस्थापन विभाग' : 'Zone');
  };

  return (
    <div
      className="glass-card"
      style={{
        padding: '18px',
        background: 'rgba(7, 31, 22, 0.75)',
        border: '1px solid rgba(255, 255, 255, 0.16)',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
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
            <History size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#FFFFFF', margin: 0 }}>
              {isMarathi ? 'मागील सिंचन इतिहास (Activity History)' : 'Irrigation Activity History'}
            </h3>
            <div style={{ fontSize: '11px', color: '#B6C8BB' }}>
              {isMarathi ? 'शेतकऱ्याने प्रत्यक्षात नोंदवलेल्या नोंदी' : 'Farmer-verified water applications'}
            </div>
          </div>
        </div>

        {history.length > 0 && (
          <span className="glass-pill" style={{ color: '#C5F36B', fontSize: '11px' }}>
            {history.length} {isMarathi ? 'नोंदी' : 'records'}
          </span>
        )}
      </div>

      {/* History List or Empty State */}
      {history.length === 0 ? (
        <IrrigationEmptyState
          title={isMarathi ? 'कोणताही सिंचन इतिहास उपलब्ध नाही' : 'No Irrigation History Recorded'}
          message={isMarathi
            ? 'या शेतासाठी अद्याप कोणतीही प्रत्यक्ष सिंचन नोंद सेव्ह केलेली नाही. वरील फॉर्म वापरून सिंचनाची नोंद करा.'
            : 'No irrigation events have been logged for this farm yet. Use the record form above to log completed watering.'}
          currentLang={currentLang}
          icon={History}
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {history.map((event, idx) => {
            const zoneLabel = event.zone_name || getZoneLabel(event.zone_id);
            const isSimulated = event.is_simulated || isDemoMode;

            return (
              <div
                key={event.id || `hist-${idx}`}
                className="glass-panel"
                style={{
                  padding: '12px 14px',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  background: 'rgba(10, 43, 28, 0.60)',
                  borderRadius: '14px',
                }}
              >
                {/* Event Header: Zone & Date */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '12.5px', fontWeight: 800, color: '#C5F36B' }}>
                    📍 {zoneLabel}
                  </span>

                  <IrrigationStatusBadge
                    type="confirmation"
                    value={isSimulated ? 'simulated' : 'confirmed'}
                    currentLang={currentLang}
                  />
                </div>

                {/* Metrics Row: Water Quantity & Method */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Droplets size={14} color="#38BDF8" />
                    <span style={{ fontSize: '15px', fontWeight: 800, color: '#38BDF8' }}>
                      {event.water_quantity}{' '}
                      <span style={{ fontSize: '12px', fontWeight: 600 }}>
                        {event.water_unit === 'cubic_meters' ? 'm³' : event.water_unit}
                      </span>
                    </span>
                  </div>

                  {event.irrigation_method && (
                    <span style={{ fontSize: '11px', color: '#D5E3D9', background: 'rgba(255, 255, 255, 0.08)', padding: '2px 8px', borderRadius: '8px' }}>
                      {event.irrigation_method}
                    </span>
                  )}
                </div>

                {/* Farmer Notes if provided */}
                {event.notes && (
                  <div
                    style={{
                      fontSize: '11.5px',
                      color: '#CBD5E1',
                      background: 'rgba(0, 0, 0, 0.20)',
                      padding: '6px 10px',
                      borderRadius: '8px',
                      marginBottom: '6px',
                      fontStyle: 'italic',
                      lineHeight: 1.4,
                    }}
                  >
                    "{event.notes}"
                  </div>
                )}

                {/* Footer Timestamp */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '10px', color: '#8E9F90' }}>
                  <Clock size={11} />
                  <span>
                    {isMarathi ? 'सिंचन दिनांक:' : 'Applied on:'} {formatTimestamp(event.irrigation_date)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

