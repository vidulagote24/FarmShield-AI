/**
 * FarmShield AI - RecommendationDetailsPage
 * 
 * Deep-dive advisory inspection screen providing:
 * - Decision evidence breakdown (soil moisture, NDVI, ET0)
 * - Algorithmic stress classification and reasoning factors
 * - Status workflow lifecycle (pending -> accepted -> applied / dismissed)
 * - Data freshness and validity monitoring
 * - Direct link to Irrigation Planner when action is irrigate
 */

import React from 'react';
import { useRecommendationDetails } from '../hooks/useRecommendationDetails.js';
import RecommendationHeader from '../components/RecommendationHeader.jsx';
import RecommendationActionCard from '../components/RecommendationActionCard.jsx';
import EvidenceBreakdown from '../components/EvidenceBreakdown.jsx';
import RecommendationReasoning from '../components/RecommendationReasoning.jsx';
import RecommendationStatusTimeline from '../components/RecommendationStatusTimeline.jsx';
import RecommendationStatusActions from '../components/RecommendationStatusActions.jsx';
import RecommendationDataFreshness from '../components/RecommendationDataFreshness.jsx';
import RecommendationEmptyState from '../components/RecommendationEmptyState.jsx';
import { Loader2, ShieldCheck } from 'lucide-react';

export default function RecommendationDetailsPage({
  recommendationId,
  onBack,
  onNavigateIrrigationPlanner,
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';

  const {
    recommendation,
    zone,
    farm,
    observations,
    loading,
    error,
    isUpdatingStatus,
    statusUpdateError,
    isDemoMode,
    setIsDemoMode,
    updateStatus,
  } = useRecommendationDetails(recommendationId);

  // Loading State
  if (loading) {
    return (
      <div style={{ padding: '24px 16px', maxWidth: '640px', margin: '0 auto', textAlign: 'center' }}>
        <div
          className="glass-card"
          style={{
            padding: '40px 20px',
            background: 'rgba(7, 31, 22, 0.85)',
            border: '1px solid rgba(197, 243, 107, 0.35)',
            borderRadius: '20px',
          }}
        >
          <Loader2 size={36} className="animate-spin" color="#C5F36B" style={{ margin: '0 auto 16px auto' }} />
          <h3 style={{ fontSize: '16px', fontWeight: 800, color: '#FFFFFF', marginBottom: '6px' }}>
            {isMarathi ? 'कृषी सल्ला तपशील लोड होत आहेत...' : 'Loading Recommendation Details...'}
          </h3>
          <p style={{ fontSize: '12px', color: '#8E9F90', margin: 0 }}>
            {isMarathi ? 'डिसिजन इंजिन व पुरावा डेटा तपासत आहे' : 'Fetching evidence telemetry and decision factors'}
          </p>
        </div>
      </div>
    );
  }

  // Error / Not Found State
  if (error || !recommendation) {
    return (
      <div style={{ padding: '20px 16px', maxWidth: '640px', margin: '0 auto' }}>
        <RecommendationEmptyState
          title={isMarathi ? 'सल्ला माहिती उपलब्ध नाही' : 'Advisory Unavailable'}
          message={error || (isMarathi ? 'या शिफारसीची माहिती मिळू शकली नाही.' : 'Unable to locate recommendation record.')}
          onBack={onBack}
          currentLang={currentLang}
        />
      </div>
    );
  }

  return (
    <div
      style={{
        padding: '16px',
        maxWidth: '680px',
        margin: '0 auto',
        paddingBottom: '90px', // Spacing above bottom navigation
      }}
    >
      {/* 1. Header with Metadata, Priority, Status, Mode */}
      <RecommendationHeader
        recommendation={recommendation}
        zone={zone}
        farm={farm}
        onBack={onBack}
        currentLang={currentLang}
        isDemoMode={isDemoMode}
        onToggleMode={() => setIsDemoMode(!isDemoMode)}
      />

      {/* 2. Primary Recommended Action Card */}
      <RecommendationActionCard
        action={recommendation.recommended_action}
        description={recommendation.description}
        descriptionEn={recommendation.description_en}
        currentLang={currentLang}
        onOpenIrrigationPlanner={
          onNavigateIrrigationPlanner 
            ? () => onNavigateIrrigationPlanner(recommendation)
            : null
        }
      />

      {/* 3. Evidence Breakdown: Measured Ground Telemetry vs Algorithmic Classification */}
      <EvidenceBreakdown
        recommendation={recommendation}
        observations={observations}
        currentLang={currentLang}
      />

      {/* 4. Qualitative Decision Reasoning Factors */}
      <RecommendationReasoning
        reasoning={recommendation.reasoning}
        currentLang={currentLang}
      />

      {/* 5. Status Workflow Lifecycle Timeline */}
      <RecommendationStatusTimeline
        status={recommendation.status}
        generatedAt={recommendation.generated_at}
        validUntil={recommendation.valid_until}
        currentLang={currentLang}
      />

      {/* 6. Interactive Status Actions (Acknowledge, Apply, Dismiss) */}
      <RecommendationStatusActions
        currentStatus={recommendation.status}
        onUpdateStatus={updateStatus}
        isUpdating={isUpdatingStatus}
        error={statusUpdateError}
        isDemoMode={isDemoMode}
        currentLang={currentLang}
      />

      {/* 7. Telemetry Freshness & Expiry Guard */}
      <RecommendationDataFreshness
        generatedAt={recommendation.generated_at}
        validUntil={recommendation.valid_until}
        currentLang={currentLang}
      />

      {/* 8. Footer Safety & Hardware Decoupling Notice */}
      <div
        style={{
          textAlign: 'center',
          padding: '12px 16px',
          fontSize: '11px',
          color: '#8E9F90',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '6px',
        }}
      >
        <ShieldCheck size={14} color="#C5F36B" />
        <span>
          {isMarathi 
            ? 'FarmShield AI — कृषी सल्ला प्रणाली • पंप व व्हॉल्व्ह नियंत्रण शेतकरी स्वतः करतात' 
            : 'FarmShield AI Advisory Engine — Farmer retains full physical control of all equipment.'}
        </span>
      </div>
    </div>
  );
}

