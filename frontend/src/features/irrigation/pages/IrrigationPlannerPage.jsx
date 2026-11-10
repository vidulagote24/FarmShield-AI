/**
 * FarmShield AI - IrrigationPlannerPage
 * 
 * Top-level screen for Irrigation Planning and Activity Recording.
 * Enables farmers to review backend recommendations, inspect water requirements,
 * log actual irrigation events with validation, and view confirmed history.
 * 
 * Safety & Agronomic Restrictions (per AGENTS.md):
 * - Purely advisory: does not control pumps, valves, or relays.
 * - Does not invent recommendations or schedule hardware operations.
 * - Confirms save only after backend response.
 */

import React, { useState } from 'react';
import { RotateCw, AlertCircle, PlusCircle, ArrowLeft, Droplets, CheckCircle2 } from 'lucide-react';
import useIrrigationPlanner from '../hooks/useIrrigationPlanner.js';
import IrrigationOverview from '../components/IrrigationOverview.jsx';
import ZoneIrrigationSelector from '../components/ZoneIrrigationSelector.jsx';
import IrrigationRecommendationCard from '../components/IrrigationRecommendationCard.jsx';
import IrrigationDetails from '../components/IrrigationDetails.jsx';
import RecordIrrigationForm from '../components/RecordIrrigationForm.jsx';
import IrrigationHistoryList from '../components/IrrigationHistoryList.jsx';
import IrrigationEmptyState from '../components/IrrigationEmptyState.jsx';

export default function IrrigationPlannerPage({
  farmId = null,
  initialZoneId = null,
  currentLang = 'mr',
  onBack,
  onSelectRecommendation,
}) {
  const isMarathi = currentLang === 'mr';

  const {
    farm,
    zones,
    recommendations,
    allRecommendations,
    history,
    selectedZoneId,
    selectZone,
    loading,
    error,
    submitting,
    submissionError,
    lastSavedEvent,
    recordIrrigation,
    clearSubmissionStatus,
    isDemoMode,
    toggleDataMode,
    refetch,
  } = useIrrigationPlanner(farmId, initialZoneId);

  // UI interaction states
  const [showRecordForm, setShowRecordForm] = useState(false);
  const [prefillRec, setPrefillRec] = useState(null);
  const [expandedDetailsZoneId, setExpandedDetailsZoneId] = useState(null);

  // Handler to open recording form with pre-filled recommendation details
  const handleOpenRecordForm = (rec = null) => {
    setPrefillRec(rec);
    setShowRecordForm(true);
    clearSubmissionStatus();
  };

  const handleToggleDetails = (zoneId) => {
    setExpandedDetailsZoneId((prev) => (prev === zoneId ? null : zoneId));
  };

  const handleFormSubmit = async (payload) => {
    const success = await recordIrrigation(payload);
    if (success) {
      // Keep form open briefly or let user see confirmation banner
    }
  };

  // ---------------------------------------------------------------------------
  // 1. Loading State
  // ---------------------------------------------------------------------------
  if (loading) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '380px',
          padding: '24px',
          textAlign: 'center',
        }}
      >
        <div
          style={{
            width: '50px',
            height: '50px',
            borderRadius: '50%',
            border: '3px solid rgba(56, 189, 248, 0.25)',
            borderTopColor: '#38BDF8',
            animation: 'spin 1s linear infinite',
            marginBottom: '16px',
          }}
        />
        <h3 style={{ fontSize: '16px', fontWeight: 800, color: '#FFFFFF', marginBottom: '4px' }}>
          {isMarathi ? 'सिंचन नियोजन लोड होत आहे...' : 'Loading Irrigation Planner...'}
        </h3>
        <p style={{ fontSize: '12.5px', color: '#B6C8BB' }}>
          {isMarathi ? 'बॅकएंड शिफारसी व मागील इतिहास मिळवत आहे' : 'Fetching advisory decisions and activity history'}
        </p>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // 2. Error State
  // ---------------------------------------------------------------------------
  if (error) {
    return (
      <div style={{ padding: '20px 18px', textAlign: 'center' }}>
        <div
          className="glass-card"
          style={{
            padding: '24px 18px',
            border: '1.5px solid rgba(239, 68, 68, 0.45)',
            background: 'rgba(50, 15, 15, 0.75)',
          }}
        >
          <div style={{ color: '#F87171', marginBottom: '12px', display: 'flex', justifyContent: 'center' }}>
            <AlertCircle size={42} />
          </div>
          <h3 style={{ fontSize: '17px', fontWeight: 800, color: '#FFFFFF', marginBottom: '6px' }}>
            {isMarathi ? 'सिंचन डेटा कनेक्शन त्रुटी' : 'API Connection Error'}
          </h3>
          <p style={{ fontSize: '13px', color: '#FECACA', marginBottom: '18px', lineHeight: 1.45 }}>
            {error}
          </p>

          <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', flexWrap: 'wrap' }}>
            {onBack && (
              <button
                onClick={onBack}
                className="btn-glass-secondary"
                style={{ fontSize: '12.5px', padding: '6px 14px' }}
              >
                <ArrowLeft size={14} />
                <span>{isMarathi ? 'मागे जा' : 'Go Back'}</span>
              </button>
            )}

            <button
              onClick={refetch}
              className="btn-glass-primary"
              style={{ fontSize: '12.5px', padding: '6px 14px' }}
            >
              <RotateCw size={14} />
              <span>{isMarathi ? 'पुन्हा प्रयत्न करा' : 'Retry'}</span>
            </button>

            <button
              onClick={toggleDataMode}
              className="btn-glass-secondary"
              style={{ fontSize: '12.5px', padding: '6px 14px', color: '#C5F36B' }}
            >
              <span>{isMarathi ? 'नमुना मोड पहा' : 'Switch to Demo'}</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // 3. Render Main Planner View
  // ---------------------------------------------------------------------------
  return (
    <div
      style={{
        padding: '16px 18px',
        display: 'flex',
        flexDirection: 'column',
        gap: '14px',
        position: 'relative',
        zIndex: 10,
      }}
    >
      {/* 1. Irrigation Overview & Safety Notice */}
      <IrrigationOverview
        farm={farm}
        recommendations={allRecommendations}
        zones={zones}
        isDemoMode={isDemoMode}
        onToggleDataMode={toggleDataMode}
        currentLang={currentLang}
      />

      {/* 2. Zone Filter Selector */}
      <ZoneIrrigationSelector
        zones={zones}
        recommendations={allRecommendations}
        selectedZoneId={selectedZoneId}
        onSelectZone={selectZone}
        currentLang={currentLang}
      />

      {/* Quick Action: Log Irrigation Activity Button */}
      {!showRecordForm && (
        <button
          onClick={() => handleOpenRecordForm(null)}
          className="btn-glass-primary"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            minHeight: '44px',
            fontSize: '13px',
            fontWeight: 800,
            background: 'rgba(56, 189, 248, 0.22)',
            borderColor: 'rgba(56, 189, 248, 0.45)',
            color: '#FFFFFF',
          }}
        >
          <PlusCircle size={16} color="#38BDF8" />
          <span>{isMarathi ? '+ नवीन सिंचन झाल्याची नोंद करा' : '+ Log Completed Irrigation'}</span>
        </button>
      )}

      {/* 3. Record Irrigation Form (Conditional Modal / Inline View) */}
      {showRecordForm && (
        <RecordIrrigationForm
          zones={zones}
          prefillRecommendation={prefillRec}
          initialZoneId={selectedZoneId}
          onSubmit={handleFormSubmit}
          onClose={() => {
            setShowRecordForm(false);
            setPrefillRec(null);
            clearSubmissionStatus();
          }}
          submitting={submitting}
          submissionError={submissionError}
          lastSavedEvent={lastSavedEvent}
          currentLang={currentLang}
          isDemoMode={isDemoMode}
        />
      )}

      {/* 4. Active Recommendations Section */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 4px' }}>
          <span style={{ fontSize: '14px', fontWeight: 800, color: '#FFFFFF', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Droplets size={16} color="#38BDF8" />
            {isMarathi ? 'सक्रिय सिंचन शिफारसी' : 'Active Recommendations'} ({recommendations.length})
          </span>
          <span style={{ fontSize: '11px', color: '#8E9F90' }}>
            {isMarathi ? 'डिसिजन इंजिन सल्ला' : 'Backend Decision Engine'}
          </span>
        </div>

        {recommendations.length === 0 ? (
          <IrrigationEmptyState
            title={isMarathi ? 'कोणतीही सिंचन शिफारस प्रलंबित नाही' : 'No Irrigation Required'}
            message={isMarathi
              ? 'निवडलेल्या विभागातील मातीत पुरेसा ओलावा उपलब्ध असून पाणी देण्याची तात्काळ गरज नाही.'
              : 'Soil moisture is adequate for the selected zone(s). No irrigation advisory is currently active.'}
            currentLang={currentLang}
          />
        ) : (
          recommendations.map((rec) => {
            const matchingZone = zones.find((z) => z.id === rec.zone_id);
            const isDetailsExpanded = expandedDetailsZoneId === rec.zone_id;

            return (
              <div key={rec.id} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <IrrigationRecommendationCard
                  recommendation={rec}
                  zone={matchingZone}
                  onOpenRecordForm={handleOpenRecordForm}
                  onToggleDetails={() => handleToggleDetails(rec.zone_id)}
                  onSelectRecommendation={onSelectRecommendation}
                  showDetails={isDetailsExpanded}
                  currentLang={currentLang}
                />

                {isDetailsExpanded && (
                  <IrrigationDetails
                    recommendation={rec}
                    zone={matchingZone}
                    currentLang={currentLang}
                  />
                )}
              </div>
            );
          })
        )}
      </div>

      {/* 5. Irrigation History List */}
      <IrrigationHistoryList
        history={history}
        zones={zones}
        currentLang={currentLang}
        isDemoMode={isDemoMode}
      />
    </div>
  );
}

