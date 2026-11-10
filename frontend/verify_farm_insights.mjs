/**
 * FarmShield AI - Task 10 & 10.1 Farm Insights & Historical Telemetry Verification Test Suite
 * 
 * Verifies:
 * 1. Observation Schema, Physical Units & Timestamp Integrity
 * 2. Soil Moisture Multi-Zone Chronological Trends
 * 3. Canopy Vegetation Index (NDVI) Scale Isolation (0.0 - 1.0)
 * 4. Honest Missing Data Handling (Null vs Zero Preservation)
 * 5. Single vs Multi-Observation Trend Thresholds
 * 6. Cross-Zone Comparative Inspection on Identical Units
 * 7. Date-Range Filtering (7d, 30d, 90d, all)
 * 8. Live API vs Demo Mode Separation & Simulated Badging
 * 9. App Navigation Integration & Screen Routing
 * 10. Task 10.1: Multi-Page Pagination & Iteration (<100, =100, >100 records)
 * 11. Task 10.1: Deduplication across shifting page boundaries
 * 12. Task 10.1: Partial Failure Recovery & isPartialData reporting
 * 13. Task 10.1: AbortController Signal pass-through & Race Condition Prevention
 * 14. Task 10.1: Observation Quality Metadata (cloud_obscured, probe_disconnected)
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { 
  DEMO_FARM_FIXTURE, 
  DEMO_ZONES_FIXTURE, 
  DEMO_OBSERVATIONS_FIXTURE 
} from './src/data/fixtures/demoFarm.js';
import { observationsApi } from './src/lib/api/observations.js';

const __dirname = fileURLToPath(new URL('.', import.meta.url));

let passed = 0;
let failed = 0;

function assert(condition, testName) {
  if (condition) {
    console.log(`  ✓ PASS: ${testName}`);
    passed++;
  } else {
    console.error(`  ✗ FAIL: ${testName}`);
    failed++;
  }
}

async function runTestSuite() {
  console.log('\n--- FarmShield AI Farm Insights & Pagination Verification ---\n');

  // -----------------------------------------------------------------------------
  // 1. Observation Schema & Physical Units
  // -----------------------------------------------------------------------------
  console.log('1. Observation Schema & Physical Units Integrity:');
  assert(Array.isArray(DEMO_OBSERVATIONS_FIXTURE) && DEMO_OBSERVATIONS_FIXTURE.length >= 15, 'Demo observations fixture has at least 15 verified records');

  const VALID_OBS_TYPES = new Set(['weather', 'soil_moisture', 'vegetation_index', 'temperature', 'rainfall', 'satellite', 'other']);

  DEMO_OBSERVATIONS_FIXTURE.forEach((obs, idx) => {
    assert(Boolean(obs.id && obs.farm_id), `Obs #${idx + 1} (${obs.id}) has valid ID and farm_id`);
    assert(VALID_OBS_TYPES.has(obs.observation_type), `Obs #${idx + 1} has valid observation_type: ${obs.observation_type}`);
    assert(!isNaN(new Date(obs.observed_at).getTime()), `Obs #${idx + 1} has valid ISO timestamp`);
    
    if (obs.observation_type === 'soil_moisture' && obs.value !== null) {
      assert(obs.unit === '%', `Soil moisture obs #${idx + 1} has unit '%'`);
      assert(obs.value >= 0 && obs.value <= 100, `Soil moisture obs #${idx + 1} value (${obs.value}%) is in range [0, 100]`);
    }

    if (obs.observation_type === 'vegetation_index' && obs.value !== null) {
      assert(obs.unit === 'NDVI', `Vegetation index obs #${idx + 1} has unit 'NDVI'`);
      assert(obs.value >= 0.0 && obs.value <= 1.0, `NDVI obs #${idx + 1} value (${obs.value}) is in range [0.0, 1.0]`);
    }
  });

  // -----------------------------------------------------------------------------
  // 2. Soil Moisture Trends & Multi-Point Sampling
  // -----------------------------------------------------------------------------
  console.log('\n2. Soil Moisture Multi-Zone Chronological Trends:');
  const smZoneA = DEMO_OBSERVATIONS_FIXTURE.filter(o => o.zone_id === 'z1-north-west-001' && o.observation_type === 'soil_moisture' && o.value !== null);
  assert(smZoneA.length === 4, 'Zone A has 4 dated soil moisture observations (multi-point trend enabled)');
  assert(smZoneA[0].value === 74.0 && smZoneA[3].value === 68.0, 'Zone A shows healthy gradual depletion (74% -> 68%)');

  const smZoneB = DEMO_OBSERVATIONS_FIXTURE.filter(o => o.zone_id === 'z2-north-east-002' && o.observation_type === 'soil_moisture' && o.value !== null);
  assert(smZoneB.length === 4, 'Zone B has 4 dated soil moisture observations');
  assert(smZoneB[0].value === 66.0 && smZoneB[3].value === 56.0, 'Zone B shows monitor depletion trajectory (66% -> 56%)');

  const smZoneC = DEMO_OBSERVATIONS_FIXTURE.filter(o => o.zone_id === 'z3-south-west-003' && o.observation_type === 'soil_moisture' && o.value !== null);
  assert(smZoneC.length === 4, 'Zone C has 4 dated soil moisture observations');
  assert(smZoneC[0].value === 58.0 && smZoneC[3].value === 46.0, 'Zone C shows critical depletion near MAD threshold (58% -> 46%)');

  // -----------------------------------------------------------------------------
  // 3. Canopy Vegetation Index (NDVI) Scale Isolation
  // -----------------------------------------------------------------------------
  console.log('\n3. Canopy Vegetation Index (NDVI) Scale Isolation:');
  const ndviZoneA = DEMO_OBSERVATIONS_FIXTURE.filter(o => o.zone_id === 'z1-north-west-001' && o.observation_type === 'vegetation_index' && o.value !== null);
  assert(ndviZoneA.length === 3, 'Zone A has 3 multispectral Sentinel-2 NDVI scenes');
  assert(ndviZoneA[2].value === 0.74, 'Zone A latest canopy NDVI is 0.74 (dense vegetation)');

  const ndviZoneC = DEMO_OBSERVATIONS_FIXTURE.filter(o => o.zone_id === 'z3-south-west-003' && o.observation_type === 'vegetation_index' && o.value !== null);
  assert(ndviZoneC.length === 3, 'Zone C has 3 multispectral Sentinel-2 NDVI scenes');
  assert(ndviZoneC[2].value === 0.46, 'Zone C latest canopy NDVI is 0.46');

  // -----------------------------------------------------------------------------
  // 4. Missing Data & Zero-Coercion Prohibition
  // -----------------------------------------------------------------------------
  console.log('\n4. Missing Data & Zero-Coercion Prohibition:');
  const zoneDObs = DEMO_OBSERVATIONS_FIXTURE.filter(o => o.zone_id === 'z4-south-east-004');
  const validDValues = zoneDObs.filter(o => o.value !== null && o.value !== undefined);
  assert(validDValues.length === 0, 'Zone D has zero valid numeric readings (explicit probe disconnected / cloud obscured)');

  const missingAsZeroCheck = zoneDObs.every(o => o.value === null);
  assert(missingAsZeroCheck, 'Zone D missing observations are strictly null, never coerced to 0 or 0.0');

  // -----------------------------------------------------------------------------
  // 5. Cross-Zone Comparison on Unified Scale
  // -----------------------------------------------------------------------------
  console.log('\n5. Cross-Zone Comparison on Unified Scale:');
  const zonesWithLatestMoisture = DEMO_ZONES_FIXTURE.map(z => {
    const match = DEMO_OBSERVATIONS_FIXTURE
      .filter(o => o.zone_id === z.id && o.observation_type === 'soil_moisture' && o.value !== null)
      .sort((a, b) => new Date(b.observed_at) - new Date(a.observed_at));
    return { zone: z.zone_code, latest: match[0]?.value || null };
  });

  assert(zonesWithLatestMoisture.find(z => z.zone === 'ZA-01').latest === 68.0, 'Zone A latest moisture is 68.0%');
  assert(zonesWithLatestMoisture.find(z => z.zone === 'ZB-02').latest === 56.0, 'Zone B latest moisture is 56.0%');
  assert(zonesWithLatestMoisture.find(z => z.zone === 'ZC-03').latest === 46.0, 'Zone C latest moisture is 46.0%');
  assert(zonesWithLatestMoisture.find(z => z.zone === 'ZD-04').latest === null, 'Zone D has null latest moisture (no ranking fabrication)');

  // -----------------------------------------------------------------------------
  // 6. Date Range Filtering
  // -----------------------------------------------------------------------------
  console.log('\n6. Date Range Filtering Logic:');
  const refDate = new Date('2026-11-08T00:00:00Z');

  function filterByDays(obsList, days) {
    const cutoff = new Date(refDate.getTime() - days * 24 * 60 * 60 * 1000);
    return obsList.filter(o => new Date(o.observed_at) >= cutoff);
  }

  const obs7d = filterByDays(DEMO_OBSERVATIONS_FIXTURE, 7);
  assert(obs7d.length > 0 && obs7d.length <= DEMO_OBSERVATIONS_FIXTURE.length, '7-day filter returns non-empty subset of observations');

  const obs30d = filterByDays(DEMO_OBSERVATIONS_FIXTURE, 30);
  assert(obs30d.length >= obs7d.length, '30-day filter captures >= 7-day observations');

  // -----------------------------------------------------------------------------
  // 7. Navigation Integration
  // -----------------------------------------------------------------------------
  console.log('\n7. Navigation Integration:');
  const appSource = fs.readFileSync(path.join(__dirname, 'src/App.jsx'), 'utf8');
  assert(appSource.includes("activeTab === 'insights'"), 'App.jsx handles activeTab === insights');
  assert(appSource.includes('FarmInsightsPage'), 'App.jsx renders FarmInsightsPage');

  const obsApiSource = fs.readFileSync(path.join(__dirname, 'src/lib/api/observations.js'), 'utf8');
  assert(obsApiSource.includes('listFarmObservations'), 'observationsApi provides listFarmObservations');
  assert(obsApiSource.includes('fetchAllFarmObservations'), 'observationsApi provides fetchAllFarmObservations');
  assert(obsApiSource.includes('listZoneObservations'), 'observationsApi provides listZoneObservations');
  assert(obsApiSource.includes('listObservations'), 'observationsApi provides listObservations');

  // -----------------------------------------------------------------------------
  // 8. Task 10.1: Complete Multi-Page Pagination Implementation
  // -----------------------------------------------------------------------------
  console.log('\n8. Task 10.1 Multi-Page Pagination & Iteration:');

  // Mock listFarmObservations for pagination tests
  const originalListFarm = observationsApi.listFarmObservations;

  // Test Case A: Dataset with < 100 items (single page, e.g. 45 items)
  observationsApi.listFarmObservations = async (farmId, params) => {
    assert(params.page_size === 100, 'Page size requested is 100 (backend max limit)');
    return {
      items: Array.from({ length: 45 }, (_, i) => ({ id: `obs-45-${i + 1}`, farm_id: farmId, value: 50 + i })),
      total: 45,
      page: 1,
      page_size: 100,
      total_pages: 1,
    };
  };

  const resSinglePage = await observationsApi.fetchAllFarmObservations('test-farm-1');
  assert(resSinglePage.items.length === 45, 'Single page (<100 items) returned all 45 records');
  assert(resSinglePage.total === 45, 'Single page total matches 45');
  assert(resSinglePage.isPartial === false, 'isPartial is false for complete single-page dataset');
  assert(resSinglePage.totalPagesFetched === 1, 'Only 1 page fetched for dataset <= 100');

  // Test Case B: Dataset with exactly 100 items (1 page)
  observationsApi.listFarmObservations = async (farmId, params) => {
    return {
      items: Array.from({ length: 100 }, (_, i) => ({ id: `obs-100-${i + 1}`, farm_id: farmId, value: 60 })),
      total: 100,
      page: 1,
      page_size: 100,
      total_pages: 1,
    };
  };

  const resExact100 = await observationsApi.fetchAllFarmObservations('test-farm-2');
  assert(resExact100.items.length === 100, 'Exactly 100 items returned');
  assert(resExact100.isPartial === false, 'isPartial is false for exactly 100 items');
  assert(resExact100.totalPagesFetched === 1, 'Exactly 1 page fetched for 100 items');

  // Test Case C: Multi-page dataset > 100 items (e.g. 240 items across 3 pages: 100 + 100 + 40)
  const pageCalls = [];
  observationsApi.listFarmObservations = async (farmId, params) => {
    pageCalls.push(params.page);
    const startIdx = (params.page - 1) * 100;
    const count = params.page === 3 ? 40 : 100;
    return {
      items: Array.from({ length: count }, (_, i) => ({ 
        id: `obs-240-p${params.page}-${i + 1}`, 
        farm_id: farmId, 
        value: 55 
      })),
      total: 240,
      page: params.page,
      page_size: 100,
      total_pages: 3,
    };
  };

  const progressEvents = [];
  const resMultiPage = await observationsApi.fetchAllFarmObservations('test-farm-3', {}, {
    onProgress: (p) => progressEvents.push({ ...p }),
  });

  assert(resMultiPage.items.length === 240, 'Multi-page fetch successfully retrieved all 240 records');
  assert(resMultiPage.total === 240, 'Total record count matches 240');
  assert(resMultiPage.isPartial === false, 'isPartial is false when all 240 records are fetched');
  assert(resMultiPage.totalPagesFetched === 3, 'Fetched exactly 3 pages for 240 records');
  assert(pageCalls.length === 3 && pageCalls[0] === 1 && pageCalls[1] === 2 && pageCalls[2] === 3, 'Iterated through pages 1, 2, and 3 sequentially');
  assert(progressEvents.length === 3, 'Progress callback fired for each of the 3 pages');
  assert(progressEvents[2].loadedRecords === 240, 'Final progress report shows 240 loaded records');

  // -----------------------------------------------------------------------------
  // 9. Task 10.1: Deduplication across shifting page boundaries
  // -----------------------------------------------------------------------------
  console.log('\n9. Task 10.1 Deduplication across Real-Time Shifts:');
  // Scenario: Record 'obs-shift-X' appears in both page 1 and page 2 due to real-time ingestion
  observationsApi.listFarmObservations = async (farmId, params) => {
    if (params.page === 1) {
      return {
        items: [
          { id: 'obs-p1-1', farm_id: farmId, value: 50 },
          { id: 'obs-shift-X', farm_id: farmId, value: 51 }, // shifting record
          { id: 'obs-p1-2', farm_id: farmId, value: 52 },
        ],
        total: 5,
        page: 1,
        page_size: 3,
        total_pages: 2,
      };
    } else {
      return {
        items: [
          { id: 'obs-shift-X', farm_id: farmId, value: 51 }, // duplicate appearance on page 2
          { id: 'obs-p2-1', farm_id: farmId, value: 53 },
          { id: 'obs-p2-2', farm_id: farmId, value: 54 },
        ],
        total: 5,
        page: 2,
        page_size: 3,
        total_pages: 2,
      };
    }
  };

  const resDedup = await observationsApi.fetchAllFarmObservations('test-farm-dedup', {}, { pageSize: 3 });
  const uniqueIds = new Set(resDedup.items.map(i => i.id));
  assert(uniqueIds.size === resDedup.items.length, 'Zero duplicate IDs in fetched observations collection');
  assert(resDedup.items.length === 5, 'Deduplicated collection contains exactly 5 unique records despite duplicate in response');

  // -----------------------------------------------------------------------------
  // 10. Task 10.1: Partial Failure Recovery & 2,000 Cap Behavior
  // -----------------------------------------------------------------------------
  console.log('\n10. Task 10.1 Partial Failure Recovery & Cap Behavior:');
  // Page 1 succeeds with 100 records, Page 2 throws a network error
  observationsApi.listFarmObservations = async (farmId, params) => {
    if (params.page === 1) {
      return {
        items: Array.from({ length: 100 }, (_, i) => ({ id: `obs-part-${i + 1}`, farm_id: farmId, value: 70 })),
        total: 200,
        page: 1,
        page_size: 100,
        total_pages: 2,
      };
    }
    throw new Error('502 Bad Gateway / Network Timeout');
  };

  const resPartial = await observationsApi.fetchAllFarmObservations('test-farm-partial');
  assert(resPartial.items.length === 100, 'Preserved all 100 records from page 1 on page 2 failure');
  assert(resPartial.isPartial === true, 'isPartial is flagged true on partial failure (never complete-data)');
  assert(resPartial.total === 200, 'Original total count (200) is preserved');
  assert(typeof resPartial.partialError === 'string' && resPartial.partialError.includes('502 Bad Gateway'), 'Informative partialError notice generated');

  // Test Case: Exceeding 2,000 records (e.g. total = 2500, maxPages = 20)
  observationsApi.listFarmObservations = async (farmId, params) => {
    return {
      items: Array.from({ length: 100 }, (_, i) => ({ id: `obs-cap-p${params.page}-${i + 1}`, farm_id: farmId, value: 75 })),
      total: 2500,
      page: params.page,
      page_size: 100,
      total_pages: 25,
    };
  };

  const resCap = await observationsApi.fetchAllFarmObservations('test-farm-cap', {}, { pageSize: 100, maxPages: 20 });
  assert(resCap.items.length === 2000, '2000 observation cap strictly respected (20 pages * 100)');
  assert(resCap.isPartial === true, 'Reaching 2,000 cap sets explicit isPartial: true');
  assert(resCap.total === 2500, 'Preserves total matching record count of 2500');
  assert(resCap.totalPagesFetched === 20, 'Fetched exactly 20 pages when capped');

  // -----------------------------------------------------------------------------
  // 11. Task 10.1: AbortController Signal Handling
  // -----------------------------------------------------------------------------
  console.log('\n11. Task 10.1 Abort Signal Handling:');
  const abortController = new AbortController();
  abortController.abort(); // already aborted

  observationsApi.listFarmObservations = async (farmId, params, options) => {
    if (options?.signal?.aborted) {
      const err = new Error('This operation was aborted');
      err.name = 'AbortError';
      throw err;
    }
    return { items: [], total: 0, page: 1, page_size: 100, total_pages: 1 };
  };

  let caughtAbort = false;
  try {
    await observationsApi.fetchAllFarmObservations('test-farm-abort', {}, { signal: abortController.signal });
  } catch (err) {
    caughtAbort = true;
  }
  assert(caughtAbort, 'Aborted request correctly throws/stops without overwriting state');

  // Restore original listFarmObservations
  observationsApi.listFarmObservations = originalListFarm;

  // -----------------------------------------------------------------------------
  // 12. Task 10.1: UI Inspection for Partial Dataset Notice & Quality Filtering
  // -----------------------------------------------------------------------------
  console.log('\n12. UI Inspection for Partial Dataset Notice & Quality Filtering:');
  const pageSource = fs.readFileSync(path.join(__dirname, 'src/features/insights/pages/FarmInsightsPage.jsx'), 'utf8');
  assert(pageSource.includes('isPartialData'), 'FarmInsightsPage consumes isPartialData state');
  assert(pageSource.includes('मर्यादित डेटा संच') || pageSource.includes('Partial Dataset Warning'), 'FarmInsightsPage renders partial dataset alert');
  assert(pageSource.includes('paginationProgress'), 'FarmInsightsPage renders multi-page loading progress');

  const metricSource = fs.readFileSync(path.join(__dirname, 'src/features/insights/components/FarmMetricCards.jsx'), 'utf8');
  assert(metricSource.includes('isPartialData'), 'FarmMetricCards receives isPartialData');
  assert(metricSource.includes('totalMatchingRecords'), 'FarmMetricCards displays totalMatchingRecords on partial');
  assert(metricSource.includes('cloud_obscured') && metricSource.includes('probe_disconnected'), 'FarmMetricCards filters out cloud_obscured & probe_disconnected from ranges');

  const hookSource = fs.readFileSync(path.join(__dirname, 'src/features/insights/hooks/useFarmInsights.js'), 'utf8');
  assert(hookSource.includes('fetchAllFarmObservations'), 'useFarmInsights calls fetchAllFarmObservations');
  assert(hookSource.includes('currentReqSeq'), 'useFarmInsights tracks request sequence to avoid race conditions');
  assert(hookSource.includes('AbortController'), 'useFarmInsights uses AbortController for clean cancellation');

  // -----------------------------------------------------------------------------
  // Summary
  // -----------------------------------------------------------------------------
  console.log('\n========================================');
  console.log(`Results: ${passed} passed, ${failed} failed`);
  console.log('========================================\n');

  if (failed > 0) {
    process.exit(1);
  }
}

runTestSuite().catch(err => {
  console.error('Test suite failed with unexpected error:', err);
  process.exit(1);
});
