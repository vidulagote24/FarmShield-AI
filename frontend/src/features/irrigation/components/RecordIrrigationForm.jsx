/**
 * FarmShield AI - RecordIrrigationForm Component
 * 
 * Form for farmers to record actual completed irrigation activities.
 * Strictly adheres to backend Pydantic schema: `IrrigationEventCreate`.
 * 
 * Safety & Data Integrity Corrections (Task 8.1):
 * - Keeps actual water quantity field blank; does NOT prefill with recommended amount.
 * - Displays recommended quantity separately as an advisory reference only.
 * - Restricts unit selection strictly to supported volume units (liters, cubic_meters); removes mm depth.
 * - Validates positive numeric quantity before dispatch.
 * - Confirms save only after backend returns a valid event identifier.
 * - Preserves entered values after failures.
 */

import React, { useState } from 'react';
import { CheckCircle2, AlertCircle, X, Droplets, Calendar, Layers, FileText, RotateCw, Info } from 'lucide-react';

export default function RecordIrrigationForm({
  zones = [],
  prefillRecommendation = null,
  initialZoneId = null,
  onSubmit,
  onClose,
  submitting = false,
  submissionError = null,
  lastSavedEvent = null,
  currentLang = 'mr',
  isDemoMode = false,
}) {
  const isMarathi = currentLang === 'mr';

  // Format current local datetime as YYYY-MM-DDTHH:MM for input[type="datetime-local"]
  const getNowLocalDateTime = () => {
    const now = new Date();
    const offset = now.getTimezoneOffset() * 60000;
    return new Date(now.getTime() - offset).toISOString().slice(0, 16);
  };

  // Form states: preselects relevant zone, but keeps actual water quantity BLANK
  const [zoneId, setZoneId] = useState(() => {
    return prefillRecommendation?.zone_id || initialZoneId || (zones[0]?.id || '');
  });
  const [irrigationDate, setIrrigationDate] = useState(getNowLocalDateTime);
  const [waterQuantity, setWaterQuantity] = useState(''); // Kept strictly blank until farmer enters it
  const [waterUnit, setWaterUnit] = useState('liters'); // Backend default unit
  const [irrigationMethod, setIrrigationMethod] = useState(() => {
    return prefillRecommendation?.recommended_action?.irrigation_method || 'drip';
  });
  const [notes, setNotes] = useState('');

  // Field validation errors
  const [fieldErrors, setFieldErrors] = useState({});

  const validate = () => {
    const errors = {};
    const qty = parseFloat(waterQuantity);

    if (!waterQuantity || isNaN(qty)) {
      errors.waterQuantity = isMarathi 
        ? 'कृपया प्रत्यक्ष दिलेले पाण्याचे प्रमाण प्रविष्ट करा.' 
        : 'Please enter actual applied water quantity.';
    } else if (qty <= 0) {
      errors.waterQuantity = isMarathi 
        ? 'पाण्याचे प्रमाण शून्यापेक्षा जास्त (धन संख्या) असणे आवश्यक आहे.' 
        : 'Water quantity must be a positive number greater than 0.';
    }

    if (!irrigationDate) {
      errors.irrigationDate = isMarathi 
        ? 'कृपया सिंचन दिनांक व वेळ निवडा.' 
        : 'Irrigation date and time is required.';
    }

    if (!waterUnit) {
      errors.waterUnit = isMarathi 
        ? 'कृपया पाण्याचे एकक निवडा.' 
        : 'Water unit is required.';
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    const payload = {
      zone_id: zoneId || null,
      irrigation_date: irrigationDate,
      water_quantity: parseFloat(waterQuantity),
      water_unit: waterUnit,
      irrigation_method: irrigationMethod,
      notes: notes.trim() || undefined,
    };

    await onSubmit(payload);
  };

  return (
    <div
      className="glass-card"
      style={{
        padding: '20px 18px',
        background: 'rgba(7, 31, 22, 0.95)',
        border: '1.5px solid rgba(56, 189, 248, 0.45)',
        borderRadius: '20px',
        boxShadow: '0 12px 36px rgba(0, 0, 0, 0.55), 0 0 24px rgba(56, 189, 248, 0.15)',
        position: 'relative',
        zIndex: 30,
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '34px',
              height: '34px',
              borderRadius: '10px',
              background: 'rgba(56, 189, 248, 0.18)',
              color: '#38BDF8',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Droplets size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: 800, color: '#FFFFFF', margin: 0 }}>
              {isMarathi ? 'प्रत्यक्ष सिंचनाची नोंद करा' : 'Record Completed Irrigation'}
            </h3>
            <div style={{ fontSize: '11px', color: '#93C5FD' }}>
              {isMarathi ? 'झालेल्या सिंचनाची खरी माहिती डेटाबेसमध्ये नोंदवा' : 'Log actual water delivered to the zone'}
            </div>
          </div>
        </div>

        {onClose && (
          <button
            onClick={onClose}
            style={{
              background: 'rgba(255, 255, 255, 0.10)',
              border: '1px solid rgba(255, 255, 255, 0.18)',
              borderRadius: '50%',
              width: '28px',
              height: '28px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#FFFFFF',
              cursor: 'pointer',
            }}
            aria-label="Close"
          >
            <X size={15} />
          </button>
        )}
      </div>

      {/* Advisory Reference Box (Only if triggered from a recommendation) */}
      {prefillRecommendation?.recommended_action && (
        <div
          style={{
            padding: '10px 12px',
            background: 'rgba(56, 189, 248, 0.08)',
            border: '1px dashed rgba(56, 189, 248, 0.35)',
            borderRadius: '12px',
            marginBottom: '14px',
            fontSize: '11.5px',
            color: '#BAE6FD',
            lineHeight: 1.45,
          }}
        >
          <div style={{ fontWeight: 700, color: '#38BDF8', marginBottom: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Info size={13} />
            <span>{isMarathi ? 'बॅकएंड शिफारस संदर्भ (Advisory Reference):' : 'Backend Advisory Reference:'}</span>
          </div>
          <div>
            {isMarathi ? 'शिफारस केलेले प्रमाण: ' : 'Recommended target: '}
            <strong>
              {prefillRecommendation.recommended_action.water_volume_m3 ? `${prefillRecommendation.recommended_action.water_volume_m3} m³` : ''}
              {prefillRecommendation.recommended_action.water_depth_mm ? ` (${prefillRecommendation.recommended_action.water_depth_mm} mm depth)` : ''}
            </strong>
            {' • '}
            <span style={{ color: '#E2E8F0' }}>
              {isMarathi ? 'कृपया प्रत्यक्ष दिलेले पाणी खाली मॅन्युअली प्रविष्ट करा' : 'Please enter actual delivered water below'}
            </span>
          </div>
        </div>
      )}

      {/* Success Banner (Displayed ONLY after backend confirms save with event ID) */}
      {lastSavedEvent && lastSavedEvent.id && (
        <div
          style={{
            padding: '12px 14px',
            background: 'rgba(34, 197, 94, 0.18)',
            border: '1.5px solid rgba(34, 197, 94, 0.5)',
            borderRadius: '14px',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '10px',
          }}
        >
          <CheckCircle2 size={20} color="#22C55E" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <div style={{ fontSize: '13.5px', fontWeight: 800, color: '#22C55E' }}>
              {isMarathi ? 'सिंचन नोंद यशस्वीरीत्या सेव्ह झाली!' : 'Irrigation activity confirmed & saved!'}
            </div>
            <div style={{ fontSize: '11.5px', color: '#E2E8F0', marginTop: '2px' }}>
              {lastSavedEvent.water_quantity}{' '}
              {lastSavedEvent.water_unit === 'cubic_meters' ? 'm³' : lastSavedEvent.water_unit}{' '}
              • ID: {String(lastSavedEvent.id).slice(0, 8)}...
            </div>
            {isDemoMode && (
              <span
                style={{
                  display: 'inline-block',
                  fontSize: '9.5px',
                  fontWeight: 800,
                  color: '#FBBF24',
                  background: 'rgba(245, 158, 11, 0.2)',
                  border: '1px solid rgba(245, 158, 11, 0.4)',
                  padding: '1px 6px',
                  borderRadius: '6px',
                  marginTop: '4px',
                }}
              >
                🌾 DEMO DATA / SIMULATED
              </span>
            )}
          </div>
        </div>
      )}

      {/* Error Banner */}
      {submissionError && (
        <div
          style={{
            padding: '10px 12px',
            background: 'rgba(239, 68, 68, 0.18)',
            border: '1px solid rgba(239, 68, 68, 0.5)',
            borderRadius: '12px',
            marginBottom: '14px',
            fontSize: '12px',
            color: '#FECACA',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <AlertCircle size={16} color="#F87171" style={{ flexShrink: 0 }} />
          <span>{submissionError}</span>
        </div>
      )}

      {/* Form Fields */}
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {/* Zone Selector Field */}
        <div>
          <label style={{ fontSize: '11.5px', fontWeight: 700, color: '#D5E3D9', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px' }}>
            <Layers size={13} color="#C5F36B" />
            <span>{isMarathi ? 'सिंचन केलेला विभाग (Zone):' : 'Select Zone:'}</span>
          </label>
          <select
            value={zoneId}
            onChange={(e) => setZoneId(e.target.value)}
            disabled={submitting}
            className="glass-input"
            style={{
              padding: '10px 12px',
              fontSize: '13px',
              color: '#FFFFFF',
              background: 'rgba(255, 255, 255, 0.10)',
              border: '1px solid rgba(255, 255, 255, 0.20)',
              borderRadius: '12px',
              width: '100%',
              cursor: 'pointer',
            }}
          >
            {zones.map((z) => (
              <option key={z.id} value={z.id} style={{ background: '#0D3826', color: '#FFFFFF' }}>
                {z.zone_code || z.zone_name} • {z.zone_name}
              </option>
            ))}
          </select>
        </div>

        {/* Irrigation Date & Time */}
        <div>
          <label style={{ fontSize: '11.5px', fontWeight: 700, color: '#D5E3D9', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px' }}>
            <Calendar size={13} color="#C5F36B" />
            <span>{isMarathi ? 'सिंचन दिनांक व वेळ:' : 'Irrigation Date & Time:'}</span>
          </label>
          <input
            type="datetime-local"
            value={irrigationDate}
            onChange={(e) => setIrrigationDate(e.target.value)}
            disabled={submitting}
            className="glass-input"
            style={{
              padding: '10px 12px',
              fontSize: '13px',
              color: '#FFFFFF',
              background: 'rgba(255, 255, 255, 0.10)',
              border: fieldErrors.irrigationDate ? '1.5px solid #EF4444' : '1px solid rgba(255, 255, 255, 0.20)',
              borderRadius: '12px',
              width: '100%',
            }}
          />
          {fieldErrors.irrigationDate && (
            <div style={{ fontSize: '11px', color: '#F87171', marginTop: '3px' }}>
              {fieldErrors.irrigationDate}
            </div>
          )}
        </div>

        {/* Quantity & Unit Row */}
        <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '8px' }}>
          <div>
            <label style={{ fontSize: '11.5px', fontWeight: 700, color: '#D5E3D9', display: 'block', marginBottom: '4px' }}>
              {isMarathi ? 'प्रत्यक्ष दिलेले पाणी (Actual Quantity):' : 'Actual Water Applied:'}
            </label>
            <input
              type="number"
              step="any"
              min="0.1"
              placeholder={isMarathi ? 'उदा. ५०००' : 'e.g., 5000'}
              value={waterQuantity}
              onChange={(e) => setWaterQuantity(e.target.value)}
              disabled={submitting}
              className="glass-input"
              style={{
                padding: '10px 12px',
                fontSize: '13.5px',
                fontWeight: 700,
                color: '#38BDF8',
                background: 'rgba(255, 255, 255, 0.10)',
                border: fieldErrors.waterQuantity ? '1.5px solid #EF4444' : '1px solid rgba(255, 255, 255, 0.20)',
                borderRadius: '12px',
                width: '100%',
              }}
            />
            {fieldErrors.waterQuantity && (
              <div style={{ fontSize: '11px', color: '#F87171', marginTop: '3px' }}>
                {fieldErrors.waterQuantity}
              </div>
            )}
          </div>

          <div>
            <label style={{ fontSize: '11.5px', fontWeight: 700, color: '#D5E3D9', display: 'block', marginBottom: '4px' }}>
              {isMarathi ? 'एकक (Volume Unit):' : 'Volume Unit:'}
            </label>
            <select
              value={waterUnit}
              onChange={(e) => setWaterUnit(e.target.value)}
              disabled={submitting}
              className="glass-input"
              style={{
                padding: '10px 12px',
                fontSize: '13px',
                color: '#FFFFFF',
                background: 'rgba(255, 255, 255, 0.10)',
                border: '1px solid rgba(255, 255, 255, 0.20)',
                borderRadius: '12px',
                width: '100%',
                cursor: 'pointer',
              }}
            >
              <option value="liters" style={{ background: '#0D3826', color: '#FFFFFF' }}>
                Liters (लिटर)
              </option>
              <option value="cubic_meters" style={{ background: '#0D3826', color: '#FFFFFF' }}>
                m³ (घनमीटर)
              </option>
            </select>
          </div>
        </div>

        {/* Irrigation Method */}
        <div>
          <label style={{ fontSize: '11.5px', fontWeight: 700, color: '#D5E3D9', display: 'block', marginBottom: '4px' }}>
            {isMarathi ? 'सिंचन पद्धत (Method):' : 'Application Method:'}
          </label>
          <select
            value={irrigationMethod}
            onChange={(e) => setIrrigationMethod(e.target.value)}
            disabled={submitting}
            className="glass-input"
            style={{
              padding: '10px 12px',
              fontSize: '13px',
              color: '#FFFFFF',
              background: 'rgba(255, 255, 255, 0.10)',
              border: '1px solid rgba(255, 255, 255, 0.20)',
              borderRadius: '12px',
              width: '100%',
              cursor: 'pointer',
            }}
          >
            <option value="drip" style={{ background: '#0D3826', color: '#FFFFFF' }}>
              {isMarathi ? 'ठिबक सिंचन (Drip)' : 'Drip System'}
            </option>
            <option value="sprinkler" style={{ background: '#0D3826', color: '#FFFFFF' }}>
              {isMarathi ? 'तुषार सिंचन (Sprinkler)' : 'Sprinkler'}
            </option>
            <option value="furrow" style={{ background: '#0D3826', color: '#FFFFFF' }}>
              {isMarathi ? 'सरी वरंबा / पाट पाणी (Furrow)' : 'Furrow'}
            </option>
            <option value="flood" style={{ background: '#0D3826', color: '#FFFFFF' }}>
              {isMarathi ? 'मोकाट पाणी (Flood)' : 'Flood'}
            </option>
          </select>
        </div>

        {/* Farmer Remarks / Notes */}
        <div>
          <label style={{ fontSize: '11.5px', fontWeight: 700, color: '#D5E3D9', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px' }}>
            <FileText size={13} color="#C5F36B" />
            <span>{isMarathi ? 'नोंद व शेरे (Remarks - Optional):' : 'Notes / Remarks (Optional):'}</span>
          </label>
          <input
            type="text"
            placeholder={isMarathi ? 'उदा. ठिबक सिंचन पूर्ण, विद्राव्य खत दिले' : 'e.g. Completed drip watering, applied fertigation'}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            disabled={submitting}
            className="glass-input"
            style={{
              padding: '10px 12px',
              fontSize: '12.5px',
              color: '#FFFFFF',
              background: 'rgba(255, 255, 255, 0.10)',
              border: '1px solid rgba(255, 255, 255, 0.20)',
              borderRadius: '12px',
              width: '100%',
            }}
          />
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={submitting}
          className="btn-glass-primary"
          style={{
            marginTop: '8px',
            minHeight: '44px',
            fontSize: '13.5px',
            fontWeight: 800,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            cursor: submitting ? 'not-allowed' : 'pointer',
            opacity: submitting ? 0.7 : 1,
          }}
        >
          {submitting ? (
            <>
              <RotateCw size={16} className="spin" />
              <span>{isMarathi ? 'डेटाबेसमध्ये सेव्ह होत आहे...' : 'Saving Event to Database...'}</span>
            </>
          ) : (
            <>
              <CheckCircle2 size={16} />
              <span>{isMarathi ? 'प्रत्यक्ष सिंचन नोंद सेव्ह करा' : 'Save Actual Irrigation Record'}</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
}
