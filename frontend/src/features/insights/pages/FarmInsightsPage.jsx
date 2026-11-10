/**
 * FarmShield AI - FarmInsightsPage
 * 
 * Master screen for Farm Insights & Historical Telemetry Trends.
 * Features:
 * - Farm-level verified telemetry overview
 * - Multi-page observation retrieval & deduplication (Task 10.1)
 * - Transparent partial-data indication & pagination progress
 * - Multi-zone soil moisture and canopy NDVI line trends
 * - Cross-zone comparison table on unified metrics
 * - Chronological observation history log
 * - Date and zone filtering aligned with backend API queries
 * 
 * Strict Agronomic Integrity:
 * - Does not calculate stress scores in frontend code.
 * - Does not fabricate data points or treat missing values as zero.
 */

import React from 'react';
import useFarmInsights from '../hooks/useFarmInsights.js';
import InsightsOverview from '../components/InsightsOverview.jsx';
import FarmMetricCards from '../components/FarmMetricCards.jsx';
import InsightsDateFilter from '../components/InsightsDateFilter.jsx';
import SoilMoistureTrend from '../components/SoilMoistureTrend.jsx';
import VegetationTrend from '../components/VegetationTrend.jsx';
import ZoneComparison from '../components/ZoneComparison.jsx';
import ObservationHistoryChart from '../components/ObservationHistoryChart.jsx';
import InsightsDataFreshness from '../components/InsightsDataFreshness.jsx';
import InsightsEmptyState from '../components/InsightsEmptyState.jsx';
import { Loader2, ShieldCheck, AlertTriangle } from 'lucide-react';

export default function FarmInsightsPage({
  farmId = null,
  onBack,
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';

  const {
    farm,
    zones,
    allObservations,
    filteredObservations,
    soilMoistureObservations,
    vegetationIndexObservations,
    latestObservationTimestamp,
    loading,
    error,
    dateRange,
    setDateRange,
    selectedZoneFilter,
    setSelectedZoneFilter,
    isDemoMode,
    setIsDemoMode,
    // Task 10.1 fields
    isPartialData,
    partialDataNotice,
    totalMatchingRecords,
    paginationProgress,
  } = useFarmInsights(farmId);

  // Loading State
  if (loading) {
    return (
      <div style={{ padding: '24px 16px', maxWidth: '680px', margin: '0 auto', textAlign: 'center' }}>
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
            {isMarathi ? 'शेत विश्लेषण व कल लोड होत आहेत...' : 'Loading Farm Insights & Trends...'}
          </h3>
          <p style={{ fontSize: '12px', color: '#8E9F90', margin: 0 }}>
            {paginationProgress 
              ? (isMarathi 
                  ? `पृष्ठ ${paginationProgress.loadedPages}/${paginationProgress.totalPages} डाउनलोड होत आहे (${paginationProgress.loadedRecords} नोंदी)...` 
                  : `Loading page ${paginationProgress.loadedPages} of ${paginationProgress.totalPages} (${paginationProgress.loadedRecords} records)...`)
              : (isMarathi ? 'प्रत्यक्ष सेन्सर नोंदी व उपग्रह मोजमापे तपासत आहे' : 'Fetching ground sensor observations and Sentinel-2 acquisitions')}
          </p>
        </div>
      </div>
    );
  }

  // Error State
  if (error && !farm) {
    return (
      <div style={{ padding: '20px 16px', maxWidth: '680px', margin: '0 auto' }}>
        <InsightsEmptyState
          title={isMarathi ? 'डेटा लोड करण्यात त्रुटी' : 'Error Loading Insights'}
          message={error}
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
        maxWidth: '720px',
        margin: '0 auto',
        paddingBottom: '90px', // Spacing above bottom floating nav
      }}
    >
      {/* 1. Insights Header Overview */}
      <InsightsOverview
        farm={farm}
        zones={zones}
        totalObservations={allObservations.length}
        latestObservedAt={latestObservationTimestamp}
        isDemoMode={isDemoMode}
        onToggleMode={() => setIsDemoMode(!isDemoMode)}
        onBack={onBack}
        currentLang={currentLang}
      />

      {/* Task 10.1: Partial Data Warning Banner */}
      {isPartialData && (
        <div
          className="glass-card"
          style={{
            padding: '12px 16px',
            marginBottom: '16px',
            background: 'rgba(245, 158, 11, 0.14)',
            border: '1.5px solid rgba(245, 158, 11, 0.5)',
            borderRadius: '14px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '12px',
          }}
        >
          <AlertTriangle size={20} color="#F59E0B" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div style={{ flex: 1, fontSize: '12px', color: '#FDE68A', lineHeight: 1.5 }}>
            <div style={{ fontWeight: 800, marginBottom: '2px', color: '#FBBF24' }}>
              {isMarathi ? 'मर्यादित डेटा संच (Partial Historical Telemetry)' : 'Partial Dataset Warning'}
            </div>
            <div>
              {partialDataNotice || (isMarathi
                ? `एकूण ${totalMatchingRecords} पैकी केवळ ${allObservations.length} नोंदी प्राप्त झाल्या आहेत. नेटवर्क मर्यादा किंवा त्रुटीमुळे काही ऐतिहासिक नोंदी वगळल्या गेल्या असण्याची शक्यता आहे.`
                : `Showing ${allObservations.length} of ${totalMatchingRecords} total observations. Some historical records could not be fetched due to network pagination limits.`)}
            </div>
          </div>
        </div>
      )}

      {/* 2. Farm High-Level Stat Cards */}
      <FarmMetricCards
        zones={zones}
        totalObservations={filteredObservations.length}
        totalMatchingRecords={totalMatchingRecords}
        isPartialData={isPartialData}
        soilMoistureObs={soilMoistureObservations}
        vegetationObs={vegetationIndexObservations}
        currentLang={currentLang}
      />

      {/* 3. Interactive Date & Zone Filters */}
      <InsightsDateFilter
        dateRange={dateRange}
        onChangeDateRange={setDateRange}
        zones={zones}
        selectedZoneFilter={selectedZoneFilter}
        onChangeZoneFilter={setSelectedZoneFilter}
        currentLang={currentLang}
      />

      {/* Empty State if Filter has no observations */}
      {filteredObservations.length === 0 ? (
        <InsightsEmptyState
          title={isMarathi ? 'निवडलेल्या फिल्टरसाठी नोंदी नाहीत' : 'No Data for Selected Filters'}
          message={isMarathi 
            ? 'या कालावधीत किंवा विभागात कोणतीही नोंद आढळली नाही. कृपया फिल्टर बदला.' 
            : 'No telemetry observations matched the specified date range or zone filter.'}
          onResetFilters={() => {
            setDateRange('all');
            setSelectedZoneFilter('all');
          }}
          currentLang={currentLang}
        />
      ) : (
        <>
          {/* 4. Soil Moisture Historical Trend Chart */}
          <SoilMoistureTrend
            observations={filteredObservations}
            zones={zones}
            isDemoMode={isDemoMode}
            currentLang={currentLang}
          />

          {/* 5. Canopy Vegetation Index (NDVI) Historical Trend Chart */}
          <VegetationTrend
            observations={filteredObservations}
            zones={zones}
            isDemoMode={isDemoMode}
            currentLang={currentLang}
          />

          {/* 6. Unified Metric Cross-Zone Comparison */}
          <ZoneComparison
            zones={zones}
            observations={allObservations}
            currentLang={currentLang}
          />

          {/* 7. Detailed Observation History Log */}
          <ObservationHistoryChart
            observations={filteredObservations}
            zones={zones}
            currentLang={currentLang}
          />

          {/* 8. Telemetry Cadence & Freshness Audit */}
          <InsightsDataFreshness
            latestObservedAt={latestObservationTimestamp}
            totalObservations={allObservations.length}
            currentLang={currentLang}
          />
        </>
      )}

      {/* Safety Notice Footer */}
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
            ? 'FarmShield AI — ऐतिहासिक कल केवळ संदर्भासाठी आहेत • नवीन शिफारसी स्वतंत्रपणे निर्माण होतात' 
            : 'Historical observations are displayed for reference. The frontend does not calculate stress scores.'}
        </span>
      </div>
    </div>
  );
}
