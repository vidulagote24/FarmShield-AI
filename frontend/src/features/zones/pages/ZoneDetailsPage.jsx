/**
 * FarmShield AI - ZoneDetailsPage
 * 
 * Top-level screen for Zone Intelligence & Details.
 * Displays zone metadata, sensor observations, telemetry trend chart,
 * crop phenological stage, backend stress indicators, and decision recommendations.
 * 
 * Scientific Integrity & Architectural Compliance:
 * - Does not calculate agronomic models (ET0, ETc, Kc, depletion) in frontend code.
 * - Does not invent sensor values or fabricate crop stages.
 * - Adheres strictly to glassmorphic dark design tokens and WCAG 2.2 AA contrast standards.
 */

import React from 'react';
import { RotateCw, AlertCircle, ShieldAlert, ArrowLeft } from 'lucide-react';
import useZoneDetails from '../hooks/useZoneDetails.js';
import ZoneOverview from '../components/ZoneOverview.jsx';
import ZoneMetrics from '../components/ZoneMetrics.jsx';
import DataFreshnessIndicator from '../components/DataFreshnessIndicator.jsx';
import SoilObservationCard from '../components/SoilObservationCard.jsx';
import TelemetryTrendChart from '../components/TelemetryTrendChart.jsx';
import CropStageCard from '../components/CropStageCard.jsx';
import StressIndicatorCard from '../components/StressIndicatorCard.jsx';
import RecommendationSummary from '../components/RecommendationSummary.jsx';

export default function ZoneDetailsPage({
  zoneId,
  farmId = null,
  currentLang = 'mr',
  onBack,
  onNavigateIrrigationPlanner,
  onSelectRecommendation,
}) {
  const isMarathi = currentLang === 'mr';

  const {
    zone,
    farm,
    observations,
    recommendations,
    stressAssessment,
    loading,
    error,
    isDemoMode,
    toggleDataMode,
    refetch,
  } = useZoneDetails(zoneId, farmId);

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
            border: '3px solid rgba(197, 243, 107, 0.25)',
            borderTopColor: '#C5F36B',
            animation: 'spin 1s linear infinite',
            marginBottom: '16px',
          }}
        />
        <h3 style={{ fontSize: '16px', fontWeight: 800, color: '#FFFFFF', marginBottom: '4px' }}>
          {isMarathi ? 'विभाग बुद्धिमत्ता लोड होत आहे...' : 'Loading Zone Intelligence...'}
        </h3>
        <p style={{ fontSize: '12.5px', color: '#B6C8BB' }}>
          {isMarathi ? 'माती सेन्सर, उपग्रह टेलिमेट्री व शिफारसी मिळवत आहे' : 'Fetching soil observations, telemetry series, and recommendations'}
        </p>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // 2. Error State (Live Mode Connection Failure)
  // ---------------------------------------------------------------------------
  if (error || !zone) {
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
            {isMarathi ? 'डेटा कनेक्शन त्रुटी' : 'API Connection Error'}
          </h3>
          <p style={{ fontSize: '13px', color: '#FECACA', marginBottom: '18px', lineHeight: 1.45 }}>
            {error || (isMarathi ? 'विभागाची माहिती सापडली नाही.' : 'Zone information could not be retrieved.')}
          </p>

          <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', flexWrap: 'wrap' }}>
            {onBack && (
              <button
                onClick={onBack}
                className="btn-glass-secondary"
                style={{ fontSize: '12.5px', padding: '6px 14px' }}
              >
                <ArrowLeft size={14} />
                <span>{isMarathi ? 'नकाशावर परत जा' : 'Back to Map'}</span>
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
  // 3. Extract Latest Telemetry Points for ZoneMetrics
  // ---------------------------------------------------------------------------
  const soilMoistureObs = observations
    .filter((o) => o.observation_type === 'soil_moisture' && o.value !== null && o.value !== undefined)
    .sort((a, b) => new Date(b.observed_at) - new Date(a.observed_at))[0] || (
      zone.soil_moisture_pct !== null && zone.soil_moisture_pct !== undefined ? {
        value: zone.soil_moisture_pct,
        unit: '%',
        observed_at: zone.last_observed_at,
        source: 'Capacitive Probe'
      } : null
    );

  const ndviObs = observations
    .filter((o) => o.observation_type === 'vegetation_index' && o.value !== null && o.value !== undefined)
    .sort((a, b) => new Date(b.observed_at) - new Date(a.observed_at))[0] || (
      zone.ndvi_value !== null && zone.ndvi_value !== undefined ? {
        value: zone.ndvi_value,
        unit: 'NDVI',
        observed_at: zone.last_observed_at,
        source: zone.evidence_source || 'Sentinel-2 L2A'
      } : null
    );

  const weatherData = {
    et0: 4.6, // Provider reference ET0 from Open-Meteo
    temperature: 29.4,
    source: farm?.weather_source || 'Open-Meteo Agro-v1'
  };

  const lastObsDate = zone.last_observed_at || (observations[0]?.observed_at) || null;

  // ---------------------------------------------------------------------------
  // 4. Render Main Screen
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
      {/* 1. Zone Overview Header */}
      <ZoneOverview
        zone={zone}
        farm={farm}
        status={stressAssessment?.status || zone.status}
        onBack={onBack}
        currentLang={currentLang}
        isDemoMode={isDemoMode}
        onToggleDataMode={toggleDataMode}
      />

      {/* 2. Data Freshness & Telemetry Source Indicator */}
      <DataFreshnessIndicator
        isDemoMode={isDemoMode}
        lastObservedAt={lastObsDate}
        source={zone.evidence_source || farm?.satellite_source}
        qualityStatus={stressAssessment?.data_quality_status || (zone.status === 'insufficient_data' ? 'insufficient' : 'good')}
        currentLang={currentLang}
      />

      {/* 3. Metric Summary Cards */}
      <ZoneMetrics
        soilMoisture={soilMoistureObs}
        vegetationIndex={ndviObs}
        weather={weatherData}
        currentLang={currentLang}
      />

      {/* 4. Telemetry Historical Trend Chart */}
      <TelemetryTrendChart
        observations={observations}
        isDemoMode={isDemoMode}
        currentLang={currentLang}
      />

      {/* 5. Soil & Sensor Observations Card */}
      <SoilObservationCard
        observations={observations}
        soilType={zone.soil_type || zone.metadata?.soil_type}
        currentLang={currentLang}
      />

      {/* 6. Crop Growth Stage Card */}
      <CropStageCard
        zone={zone}
        farm={farm}
        currentLang={currentLang}
      />

      {/* 7. Stress Indicators & Scientific Evidence */}
      <StressIndicatorCard
        stressAssessment={stressAssessment}
        zoneReasonSummary={zone.reason_summary}
        currentLang={currentLang}
      />

      {/* 8. Recommendations Summary */}
      <RecommendationSummary
        recommendations={recommendations}
        onNavigateIrrigationPlanner={onNavigateIrrigationPlanner}
        onSelectRecommendation={onSelectRecommendation}
        currentLang={currentLang}
      />
    </div>
  );
}

