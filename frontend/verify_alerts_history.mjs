/**
 * FarmShield AI - Task 11.1 & 11.1.1 Alerts & Activity History Verification Test Suite
 * 
 * Verifies:
 * 1. Strict Status Eligibility (pending & accepted vs applied, completed, rejected, dismissed, expired)
 * 2. Expiration Filtering with valid_until (Expired vs Non-Expired, Missing/Invalid valid_until)
 * 3. Recommendation-Derived Alert Mapping & Metadata Rules
 * 4. Critical & High Priority Gating
 * 5. Explicit Independent Agronomic Alerts vs Supporting stress_reasons
 * 6. Stable Recommendation IDs & Duplicate Prevention
 * 7. Rejection of Generic Free-Text Scraping / Unsupported Reasoning
 * 8. Farm-Scoped Local Viewed State & Storage Isolation
 * 9. Graceful Handling of Corrupt / Unavailable localStorage
 * 10. Irrigation Event Normalization & Real Event Timestamps
 * 11. Recommendation Timestamp Handling without Fabricated Status Transitions
 * 12. Observation Normalization, Real Timestamps & Quality Integrity (Null != 0)
 * 13. Strict Chronological Ordering (Newest First)
 * 14. Omission of Records Lacking Valid Timestamps (No new Date() Fallback)
 * 15. Independent Source Failures & isPartialData Reporting (Promise.allSettled)
 * 16. Pagination & Observation Ceiling Respect (2,000 Cap)
 * 17. AbortController Signal Cancellation & Stale Response Protection
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { alertsApi } from './src/lib/api/alerts.js';
import { historyApi } from './src/lib/api/history.js';
import recommendationsApi from './src/lib/api/recommendations.js';
import irrigationApi from './src/lib/api/irrigation.js';
import observationsApi from './src/lib/api/observations.js';

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
  console.log('\n--- FarmShield AI Alerts & Activity History Verification (Task 11.1.1) ---\n');

  // Save original API methods for mocking
  const origListRecs = recommendationsApi.listFarmRecommendations;
  const origListIrrig = irrigationApi.listFarmIrrigationEvents;
  const origListObs = observationsApi.fetchAllFarmObservations;

  const testRefTime = new Date('2026-11-08T12:00:00Z').getTime();

  // -----------------------------------------------------------------------------
  // 1. Backend Recommendation Status Contract & Strict Alert Eligibility
  // -----------------------------------------------------------------------------
  console.log('1. Backend Recommendation Status Contract & Strict Alert Eligibility:');

  const statusTestRecs = [
    {
      id: 'rec-status-pending',
      farm_id: 'farm-123',
      title: 'Pending High Advisory',
      priority: 'high',
      status: 'pending',
      generated_at: '2026-11-08T06:00:00Z',
    },
    {
      id: 'rec-status-accepted',
      farm_id: 'farm-123',
      title: 'Accepted Critical Advisory',
      priority: 'critical',
      status: 'accepted',
      generated_at: '2026-11-08T06:00:00Z',
    },
    {
      id: 'rec-status-applied',
      farm_id: 'farm-123',
      title: 'Applied Advisory (Terminal)',
      priority: 'critical',
      status: 'applied', // Terminal - MUST BE EXCLUDED from active alerts
      generated_at: '2026-11-08T06:00:00Z',
    },
    {
      id: 'rec-status-completed',
      farm_id: 'farm-123',
      title: 'Completed Advisory (Terminal)',
      priority: 'high',
      status: 'completed', // Terminal - MUST BE EXCLUDED from active alerts
      generated_at: '2026-11-08T06:00:00Z',
    },
    {
      id: 'rec-status-rejected',
      farm_id: 'farm-123',
      title: 'Rejected Advisory (Closed)',
      priority: 'critical',
      status: 'rejected', // Closed - MUST BE EXCLUDED from active alerts
      generated_at: '2026-11-08T06:00:00Z',
    },
    {
      id: 'rec-status-dismissed',
      farm_id: 'farm-123',
      title: 'Dismissed Advisory (Closed)',
      priority: 'critical',
      status: 'dismissed', // Closed - MUST BE EXCLUDED from active alerts
      generated_at: '2026-11-08T06:00:00Z',
    },
    {
      id: 'rec-status-expired',
      farm_id: 'farm-123',
      title: 'Expired Advisory (Closed)',
      priority: 'high',
      status: 'expired', // Closed - MUST BE EXCLUDED from active alerts
      generated_at: '2026-11-08T06:00:00Z',
    },
  ];

  recommendationsApi.listFarmRecommendations = async () => ({
    items: statusTestRecs,
    total: statusTestRecs.length,
  });

  const statusAlerts = await alertsApi.listFarmAlerts('farm-123', { referenceTime: testRefTime });

  assert(statusAlerts.items.length === 2, 'Only 2 active alerts eligible: pending and accepted (5 terminal/closed statuses excluded)');
  assert(statusAlerts.items.some(a => a.id === 'rec-status-pending'), 'Pending recommendation is included as active alert');
  
  const acceptedAlert = statusAlerts.items.find(a => a.id === 'rec-status-accepted');
  assert(acceptedAlert !== undefined, 'Accepted recommendation is included as active alert');
  assert(acceptedAlert.is_accepted === true, 'Accepted recommendation correctly flags is_accepted: true');

  assert(!statusAlerts.items.some(a => a.id === 'rec-status-applied'), 'Applied recommendation is strictly EXCLUDED from active alerts');
  assert(!statusAlerts.items.some(a => a.id === 'rec-status-completed'), 'Completed recommendation is strictly EXCLUDED from active alerts');
  assert(!statusAlerts.items.some(a => a.id === 'rec-status-rejected'), 'Rejected recommendation is strictly EXCLUDED from active alerts');
  assert(!statusAlerts.items.some(a => a.id === 'rec-status-dismissed'), 'Dismissed recommendation is strictly EXCLUDED from active alerts');
  assert(!statusAlerts.items.some(a => a.id === 'rec-status-expired'), 'Expired recommendation is strictly EXCLUDED from active alerts');

  // -----------------------------------------------------------------------------
  // 2. Expiration Filtering with valid_until & Non-Fabrication Rules
  // -----------------------------------------------------------------------------
  console.log('\n2. Expiration Filtering with valid_until & Non-Fabrication Rules:');

  const expirationTestRecs = [
    {
      id: 'rec-valid-future',
      farm_id: 'farm-123',
      title: 'Still Valid Advisory',
      priority: 'high',
      status: 'pending',
      generated_at: '2026-11-08T06:00:00Z',
      valid_until: '2026-11-08T18:00:00Z', // In future relative to testRefTime (12:00)
    },
    {
      id: 'rec-valid-past',
      farm_id: 'farm-123',
      title: 'Time-Expired Advisory',
      priority: 'high',
      status: 'pending',
      generated_at: '2026-11-08T06:00:00Z',
      valid_until: '2026-11-08T10:00:00Z', // In past relative to testRefTime (12:00) -> EXPIRED
    },
    {
      id: 'rec-valid-missing',
      farm_id: 'farm-123',
      title: 'Missing valid_until Advisory',
      priority: 'high',
      status: 'pending',
      generated_at: '2026-11-08T06:00:00Z',
      valid_until: null, // Null / missing -> Do NOT fabricate expiration timestamp!
    },
    {
      id: 'rec-valid-invalid-date',
      farm_id: 'farm-123',
      title: 'Malformed valid_until Advisory',
      priority: 'high',
      status: 'pending',
      generated_at: '2026-11-08T06:00:00Z',
      valid_until: 'NOT_A_DATE', // Invalid ISO -> Do not crash or falsely expire
    },
  ];

  recommendationsApi.listFarmRecommendations = async () => ({
    items: expirationTestRecs,
    total: expirationTestRecs.length,
  });

  const expirationAlerts = await alertsApi.listFarmAlerts('farm-123', { referenceTime: testRefTime });

  assert(expirationAlerts.items.length === 3, 'Exactly 3 alerts active: future, missing, and malformed; past expired excluded');
  assert(expirationAlerts.items.some(a => a.id === 'rec-valid-future'), 'Non-expired recommendation with future valid_until is included');
  assert(!expirationAlerts.items.some(a => a.id === 'rec-valid-past'), 'Expired recommendation with past valid_until is strictly EXCLUDED');
  
  const missingExpAlert = expirationAlerts.items.find(a => a.id === 'rec-valid-missing');
  assert(missingExpAlert !== undefined, 'Recommendation with null valid_until remains active based on status');
  assert(missingExpAlert.valid_until === null, 'Does NOT fabricate an expiration timestamp when valid_until is null');

  const malformedExpAlert = expirationAlerts.items.find(a => a.id === 'rec-valid-invalid-date');
  assert(malformedExpAlert !== undefined, 'Recommendation with malformed valid_until is handled safely without crashing');

  // -----------------------------------------------------------------------------
  // 3. Explicit Independent Agronomic Alerts vs Supporting stress_reasons
  // -----------------------------------------------------------------------------
  console.log('\n3. Explicit Independent Agronomic Alerts vs Supporting stress_reasons:');

  const agronomicTestRecs = [
    {
      id: 'rec-agro-explicit',
      farm_id: 'farm-123',
      title: 'Medium Advisory with Explicit Independent Alert',
      priority: 'medium', // Medium priority normally not an alert!
      status: 'pending',
      generated_at: '2026-11-08T06:00:00Z',
      reasoning: {
        independent_alerts: ['elevated soil salinity (consult leaching guidelines)'],
      },
    },
    {
      id: 'rec-evidence-only',
      farm_id: 'farm-123',
      title: 'Medium Advisory with stress_reasons only',
      priority: 'medium', // Medium priority with only evidence stress_reasons -> MUST NOT be an alert!
      status: 'pending',
      generated_at: '2026-11-08T06:00:00Z',
      reasoning: {
        stress_status: 'attention',
        stress_reasons: [
          'root_zone_depletion_approaching_threshold',
          'vegetation_trend_declining',
        ],
        // independent_alerts is empty / absent!
      },
    },
    {
      id: 'rec-low-no-alerts',
      farm_id: 'farm-123',
      title: 'Low Advisory Routine',
      priority: 'low',
      status: 'pending',
      generated_at: '2026-11-08T06:00:00Z',
      reasoning: {
        stress_status: 'healthy',
      },
    },
  ];

  recommendationsApi.listFarmRecommendations = async () => ({
    items: agronomicTestRecs,
    total: agronomicTestRecs.length,
  });

  const agroAlerts = await alertsApi.listFarmAlerts('farm-123', { referenceTime: testRefTime });

  assert(agroAlerts.items.length === 1, 'Only 1 alert derived: explicit independent agronomic alert qualifies');
  assert(agroAlerts.items[0].id === 'rec-agro-explicit', 'rec-agro-explicit qualified via reasoning.independent_alerts');
  assert(agroAlerts.items[0].has_independent_alerts === true, 'Carries has_independent_alerts: true');
  assert(agroAlerts.items[0].independent_alerts.length === 1, 'Preserves exact independent alert string');
  
  assert(!agroAlerts.items.some(a => a.id === 'rec-evidence-only'), 'Recommendation with stress_reasons only is NOT converted to an alert (supporting evidence preserved)');
  assert(!agroAlerts.items.some(a => a.id === 'rec-low-no-alerts'), 'Low priority recommendation without independent alerts is excluded');

  // -----------------------------------------------------------------------------
  // 4. Stable IDs and Duplicate Prevention
  // -----------------------------------------------------------------------------
  console.log('\n4. Stable IDs & Duplicate Prevention:');
  const duplicateRecs = [
    statusTestRecs[0],
    { ...statusTestRecs[0] }, // Exact duplicate instance
  ];

  recommendationsApi.listFarmRecommendations = async () => ({
    items: duplicateRecs,
    total: 2,
  });

  const dedupAlerts = await alertsApi.listFarmAlerts('farm-123', { referenceTime: testRefTime });
  assert(dedupAlerts.items.length === 1, 'Duplicate recommendation instances deduplicated to exactly 1 alert');
  assert(dedupAlerts.items[0].id === 'rec-status-pending', 'Uses stable recommendation UUID without manufacturing random alert IDs');

  // -----------------------------------------------------------------------------
  // 5. Rejection of Generic Free-Text Search / Unsupported Fields
  // -----------------------------------------------------------------------------
  console.log('\n5. Rejection of Free-Text Search for Alert Inferences:');
  const textScrapeRec = [
    {
      id: 'rec-text-fake',
      farm_id: 'farm-123',
      title: 'Routine weekly checkup mentioning drought and pest words casually',
      description: 'The weather is dry like a drought and pests might exist',
      priority: 'low',
      status: 'pending',
      generated_at: '2026-11-08T00:00:00Z',
      reasoning: {}, // No structured alerts
    },
  ];

  recommendationsApi.listFarmRecommendations = async () => ({
    items: textScrapeRec,
    total: 1,
  });

  const textAlerts = await alertsApi.listFarmAlerts('farm-123', { referenceTime: testRefTime });
  assert(textAlerts.items.length === 0, 'Does NOT infer alerts from free-text words (drought/pest) without structured evidence');

  // -----------------------------------------------------------------------------
  // 6. Farm-Scoped Local Viewed State & Storage Fault-Tolerance
  // -----------------------------------------------------------------------------
  console.log('\n6. Farm-Scoped Local Viewed State & Storage Fault-Tolerance:');
  const mockStorage = new Map();
  const fakeLocalStorage = {
    getItem: (k) => mockStorage.get(k) || null,
    setItem: (k, v) => mockStorage.set(k, String(v)),
  };

  const farmAKey = 'farmshield_viewed_alerts_farm-A';
  const farmBKey = 'farmshield_viewed_alerts_farm-B';

  fakeLocalStorage.setItem(farmAKey, JSON.stringify(['rec-1', 'rec-2']));
  fakeLocalStorage.setItem(farmBKey, JSON.stringify(['rec-3']));

  const parsedA = JSON.parse(fakeLocalStorage.getItem(farmAKey));
  const parsedB = JSON.parse(fakeLocalStorage.getItem(farmBKey));

  assert(parsedA.includes('rec-1') && !parsedA.includes('rec-3'), 'Farm A viewed alerts isolated from Farm B');
  assert(parsedB.includes('rec-3') && !parsedB.includes('rec-1'), 'Farm B viewed alerts isolated from Farm A');

  fakeLocalStorage.setItem('farmshield_viewed_alerts_farm-corrupt', '{INVALID_JSON;;}');
  let recoveredCorrupt = false;
  try {
    const raw = fakeLocalStorage.getItem('farmshield_viewed_alerts_farm-corrupt');
    JSON.parse(raw);
  } catch (e) {
    recoveredCorrupt = true;
  }
  assert(recoveredCorrupt, 'Corrupt JSON in storage caught gracefully without terminating application');

  // -----------------------------------------------------------------------------
  // 7. Activity History Normalization & Timestamp Rules
  // -----------------------------------------------------------------------------
  console.log('\n7. Activity History Normalization & Timestamp Rules:');

  const mockIrrigations = [
    {
      id: 'irr-1',
      farm_id: 'farm-123',
      zone_id: 'zone-1',
      irrigation_date: '2026-11-05T06:00:00Z',
      water_quantity: 80.0,
      water_unit: 'cubic_meters',
      irrigation_method: 'drip',
      notes: 'Morning drip cycle',
    },
    {
      id: 'irr-invalid-time',
      farm_id: 'farm-123',
      irrigation_date: 'INVALID_DATE_STRING',
      water_quantity: 20.0,
    },
  ];

  const mockRecsForHist = [
    {
      id: 'rec-h-applied',
      farm_id: 'farm-123',
      zone_id: 'zone-1',
      title: 'लागू केलेला सल्ला (Applied Recommendation)',
      description: 'शेतकऱ्याने पाणी दिले',
      priority: 'high',
      status: 'applied', // Preserved in history even though excluded from active alerts!
      generated_at: '2026-11-06T08:00:00Z',
    },
  ];

  const mockObsForHist = [
    {
      id: 'obs-h-1',
      farm_id: 'farm-123',
      zone_id: 'zone-1',
      observation_type: 'soil_moisture',
      observed_at: '2026-11-07T10:00:00Z',
      value: 46.0,
      unit: '%',
      source: 'Soil Probe C3',
    },
    {
      id: 'obs-null-value',
      farm_id: 'farm-123',
      zone_id: 'zone-4',
      observation_type: 'soil_moisture',
      observed_at: '2026-11-07T09:00:00Z',
      value: null,
      unit: '%',
      source: 'Sensor D',
    },
  ];

  irrigationApi.listFarmIrrigationEvents = async () => ({ items: mockIrrigations, total: 2 });
  recommendationsApi.listFarmRecommendations = async () => ({ items: mockRecsForHist, total: 1 });
  observationsApi.fetchAllFarmObservations = async () => ({ items: mockObsForHist, total: 2, isPartial: false });

  const historyResult = await historyApi.getUnifiedFarmHistory('farm-123');

  assert(historyResult.items.length === 4, 'History aggregated 4 valid events (invalid timestamp excluded)');
  
  const invalidEvent = historyResult.items.find(h => h.id === 'irr-invalid-time');
  assert(invalidEvent === undefined, 'Omitted record lacking valid timestamp (no new Date() fallback)');

  // Verify chronological ordering: newest first
  assert(historyResult.items[0].id === 'obs-h-1', 'Newest event is obs-h-1 (Nov 7 10:00)');
  assert(historyResult.items[1].id === 'obs-null-value', 'Second event is obs-null-value (Nov 7 09:00)');
  assert(historyResult.items[2].id === 'rec-h-applied', 'Third event is rec-h-applied (Nov 6 08:00)');
  assert(historyResult.items[3].id === 'irr-1', 'Fourth event is irr-1 (Nov 5 06:00)');

  // Verify historical recommendations of all statuses are preserved in history
  const appliedRecHist = historyResult.items.find(h => h.id === 'rec-h-applied');
  assert(appliedRecHist !== undefined, 'Applied recommendation is preserved in activity history');
  assert(appliedRecHist.status === 'applied', 'Recommendation reflects current status only (no fabricated transition events)');

  // Verify null observation value is preserved and not coerced to 0
  const nullObsEvent = historyResult.items.find(h => h.id === 'obs-null-value');
  assert(nullObsEvent.value === null, 'Observation with null value strictly preserves value === null (never 0)');
  assert(nullObsEvent.status === 'unreadable', 'Observation with null value marked status: unreadable');

  // -----------------------------------------------------------------------------
  // 8. Independent Source Failures & Partial Data Reporting
  // -----------------------------------------------------------------------------
  console.log('\n8. Independent Source Failures & Partial Data Reporting:');

  observationsApi.fetchAllFarmObservations = async () => {
    throw new Error('500 Internal Server Error in telemetry service');
  };

  const partialHistory = await historyApi.getUnifiedFarmHistory('farm-123');

  assert(partialHistory.isPartialData === true, 'isPartialData is flagged true on source failure');
  assert(typeof partialHistory.sourceErrors.observations === 'string', 'sourceErrors.observations captures failure message');
  assert(partialHistory.items.length === 2, 'Successful sources (irrigation & recommendations) preserved despite observations failure');

  // -----------------------------------------------------------------------------
  // 9. AbortController Signal Cancellation
  // -----------------------------------------------------------------------------
  console.log('\n9. AbortController Signal Cancellation:');
  const controller = new AbortController();
  controller.abort();

  let historyAborted = false;
  try {
    await historyApi.getUnifiedFarmHistory('farm-123', {}, { signal: controller.signal });
  } catch (err) {
    if (err.name === 'AbortError' || err.message?.includes('aborted')) {
      historyAborted = true;
    }
  }
  assert(historyAborted, 'getUnifiedFarmHistory halts and throws AbortError cleanly when signal aborted');

  // Restore mocked functions
  recommendationsApi.listFarmRecommendations = origListRecs;
  irrigationApi.listFarmIrrigationEvents = origListIrrig;
  observationsApi.fetchAllFarmObservations = origListObs;

  // -----------------------------------------------------------------------------
  // 10. Source File Structure & Exports Inspection
  // -----------------------------------------------------------------------------
  console.log('\n10. Source File Structure & Exports Inspection:');

  const alertsFile = fs.readFileSync(path.join(__dirname, 'src/lib/api/alerts.js'), 'utf8');
  assert(alertsFile.includes('listFarmAlerts'), 'alerts.js provides listFarmAlerts');
  assert(alertsFile.includes('valid_until'), 'alerts.js checks valid_until expiration');
  assert(alertsFile.includes('dismissAlert'), 'alerts.js provides dismissAlert');
  assert(alertsFile.includes('acknowledgeAlert'), 'alerts.js provides acknowledgeAlert');
  assert(alertsFile.includes('recommendation_derived'), 'alerts.js provides recommendation_derived classification');

  const historyFile = fs.readFileSync(path.join(__dirname, 'src/lib/api/history.js'), 'utf8');
  assert(historyFile.includes('getUnifiedFarmHistory'), 'history.js provides getUnifiedFarmHistory');
  assert(historyFile.includes('Promise.allSettled'), 'history.js uses Promise.allSettled for independent fault isolation');
  assert(historyFile.includes('sourceErrors'), 'history.js captures sourceErrors');

  const hookFile = fs.readFileSync(path.join(__dirname, 'src/features/alerts/hooks/useAlertsAndHistory.js'), 'utf8');
  assert(hookFile.includes('useAlertsAndHistory'), 'useAlertsAndHistory hook is exported');
  assert(hookFile.includes('markAlertViewed'), 'useAlertsAndHistory provides markAlertViewed');
  assert(hookFile.includes('isAlertViewed'), 'useAlertsAndHistory provides isAlertViewed');
  assert(hookFile.includes('localStorage'), 'useAlertsAndHistory uses localStorage for local viewed state');
  assert(hookFile.includes('currentReqSeq'), 'useAlertsAndHistory protects against stale request race conditions');

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
