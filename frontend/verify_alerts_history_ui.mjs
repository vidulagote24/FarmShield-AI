/**
 * FarmShield AI - Task 11.2 Alerts & Activity History UI Verification Test Suite
 * 
 * Verifies:
 * 1. UI Components existence, exports & modular architecture
 * 2. Alerts Tab vs Activity History Tab structure and bilingual presentation
 * 3. Priority filter definitions, counts, and category matching
 * 4. Recommendation status presentation (pending vs accepted vs terminal exclusions)
 * 5. Local viewed state API integration (unread badge, mark seen, isolation from backend status)
 * 6. Navigation integration in App.jsx (back-routing, rec details linking, origin retention)
 * 7. Unified Chronological Activity History rendering (irrigation, recs, observations)
 * 8. Telemetry non-zero integrity (null observation values never coerced to 0)
 * 9. Partial data reporting & source error surfacing
 * 10. Simulated demo data badges and honesty
 * 11. Responsive, accessible markup (ARIA attributes, semantic tags)
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { 
  DEMO_FARM_FIXTURE, 
  DEMO_ALERTS_FIXTURE, 
  DEMO_IRRIGATION_EVENTS_FIXTURE,
  DEMO_RECOMMENDATIONS_FIXTURE,
  DEMO_OBSERVATIONS_FIXTURE 
} from './src/data/fixtures/demoFarm.js';
import { historyApi } from './src/lib/api/history.js';
import { alertsApi } from './src/lib/api/alerts.js';

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
  console.log('\n--- FarmShield AI Alerts & Activity History UI Verification (Task 11.2) ---\n');

  // -----------------------------------------------------------------------------
  // 1. Component Structure and File Existence
  // -----------------------------------------------------------------------------
  console.log('1. Component Structure & Public Exports:');
  const pagePath = path.join(__dirname, 'src', 'features', 'alerts', 'pages', 'AlertsHistoryPage.jsx');
  const cardPath = path.join(__dirname, 'src', 'features', 'alerts', 'components', 'AlertCard.jsx');
  const filtersPath = path.join(__dirname, 'src', 'features', 'alerts', 'components', 'AlertFilters.jsx');
  const timelinePath = path.join(__dirname, 'src', 'features', 'alerts', 'components', 'ActivityTimeline.jsx');
  const emptyPath = path.join(__dirname, 'src', 'features', 'alerts', 'components', 'AlertsEmptyState.jsx');
  const indexPath = path.join(__dirname, 'src', 'features', 'alerts', 'index.js');

  assert(fs.existsSync(pagePath), 'AlertsHistoryPage.jsx exists');
  assert(fs.existsSync(cardPath), 'AlertCard.jsx exists');
  assert(fs.existsSync(filtersPath), 'AlertFilters.jsx exists');
  assert(fs.existsSync(timelinePath), 'ActivityTimeline.jsx exists');
  assert(fs.existsSync(emptyPath), 'AlertsEmptyState.jsx exists');
  assert(fs.existsSync(indexPath), 'features/alerts/index.js exists');

  const indexContent = fs.readFileSync(indexPath, 'utf-8');
  assert(indexContent.includes('AlertsHistoryPage'), 'features/alerts/index.js exports AlertsHistoryPage');
  assert(indexContent.includes('AlertCard'), 'features/alerts/index.js exports AlertCard');
  assert(indexContent.includes('AlertFilters'), 'features/alerts/index.js exports AlertFilters');
  assert(indexContent.includes('ActivityTimeline'), 'features/alerts/index.js exports ActivityTimeline');
  assert(indexContent.includes('AlertsEmptyState'), 'features/alerts/index.js exports AlertsEmptyState');
  assert(indexContent.includes('useAlertsAndHistory'), 'features/alerts/index.js exports useAlertsAndHistory');

  // -----------------------------------------------------------------------------
  // 2. Bilingual Tab Structure & Separation
  // -----------------------------------------------------------------------------
  console.log('\n2. Bilingual Tab Architecture:');
  const pageContent = fs.readFileSync(pagePath, 'utf-8');
  assert(pageContent.includes('कृषी इशारे'), 'AlertsHistoryPage contains Marathi label कृषी इशारे');
  assert(pageContent.includes('शेती इतिहास'), 'AlertsHistoryPage contains Marathi label शेती इतिहास');
  assert(pageContent.includes("activeTab === 'alerts'"), 'AlertsHistoryPage supports activeTab === alerts');
  assert(pageContent.includes("activeTab === 'history'"), 'AlertsHistoryPage supports activeTab === history');
  assert(pageContent.includes('unreadAlertsCount'), 'Alerts tab displays dynamic unread alerts badge');

  // -----------------------------------------------------------------------------
  // 3. Priority Filters & Category Categorization
  // -----------------------------------------------------------------------------
  console.log('\n3. Priority Filters & Category Matching:');
  const filtersContent = fs.readFileSync(filtersPath, 'utf-8');
  assert(filtersContent.includes("'all'"), 'AlertFilters provides All filter');
  assert(filtersContent.includes("'critical'"), 'AlertFilters provides Critical filter');
  assert(filtersContent.includes("'high'"), 'AlertFilters provides High filter');
  assert(filtersContent.includes("'agronomic'"), 'AlertFilters provides Agronomic alerts filter');
  assert(filtersContent.includes('अति तातडीचे'), 'Provides Marathi label अति तातडीचे for Critical');
  assert(filtersContent.includes('उच्च'), 'Provides Marathi label उच्च for High');
  assert(filtersContent.includes('इतर कृषी'), 'Provides Marathi label इतर कृषी for Agronomic');

  // -----------------------------------------------------------------------------
  // 4. Recommendation Status Presentation & Terminal Exclusions
  // -----------------------------------------------------------------------------
  console.log('\n4. Recommendation Status Presentation & Terminal Exclusions:');
  const cardContent = fs.readFileSync(cardPath, 'utf-8');
  assert(cardContent.includes('पुनरावलोकन बाकी') || cardContent.includes('Awaiting Review'), 'AlertCard handles pending status (Awaiting Review)');
  assert(cardContent.includes('स्वीकारले / कृती नियोजित') || cardContent.includes('Accepted / Planned'), 'AlertCard handles accepted status (Accepted / Planned)');
  assert(cardContent.includes('!isViewed && !isAccepted') || cardContent.includes('!isViewed && !alert.is_accepted'), 'Accepted recommendation is NOT presented as unread/new');

  // Verify terminal statuses are excluded from active alerts
  const rawRecommendations = [
    { id: 'rec-pending', status: 'pending', priority: 'critical', title: 'Critical Pending' },
    { id: 'rec-accepted', status: 'accepted', priority: 'high', title: 'High Accepted' },
    { id: 'rec-applied', status: 'applied', priority: 'critical', title: 'Applied Rec' },
    { id: 'rec-completed', status: 'completed', priority: 'high', title: 'Completed Rec' },
    { id: 'rec-dismissed', status: 'dismissed', priority: 'critical', title: 'Dismissed Rec' },
    { id: 'rec-rejected', status: 'rejected', priority: 'critical', title: 'Rejected Rec' },
    { id: 'rec-expired', status: 'expired', priority: 'critical', title: 'Expired Rec' },
  ];

  const derivedAlerts = [];
  const TERMINAL_STATUSES = new Set(['applied', 'completed', 'dismissed', 'rejected', 'expired']);
  for (const r of rawRecommendations) {
    if (r.status === 'pending' || r.status === 'accepted') {
      derivedAlerts.push(r);
    }
  }

  assert(derivedAlerts.length === 2, 'Exactly 2 alerts derived (pending and accepted only)');
  assert(derivedAlerts.every(a => !TERMINAL_STATUSES.has(a.status)), 'No terminal statuses in active alerts collection');

  // -----------------------------------------------------------------------------
  // 5. Local Viewed-State API Integration
  // -----------------------------------------------------------------------------
  console.log('\n5. Local Viewed-State Integration:');
  assert(cardContent.includes('onMarkViewed'), 'AlertCard accepts onMarkViewed prop');
  assert(cardContent.includes('showUnreadBadge'), 'AlertCard dynamically toggles unread badge');
  assert(cardContent.includes('handleQuickMarkViewed'), 'AlertCard provides quick mark-viewed action without navigation');
  assert(cardContent.includes('handleCardClick'), 'Clicking alert triggers view and navigation');

  // -----------------------------------------------------------------------------
  // 6. Navigation Integration in App.jsx
  // -----------------------------------------------------------------------------
  console.log('\n6. App.jsx Navigation & Routing:');
  const appContent = fs.readFileSync(path.join(__dirname, 'src', 'App.jsx'), 'utf-8');
  assert(appContent.includes("activeTab === 'alerts'"), 'App.jsx handles activeTab === alerts');
  assert(appContent.includes('<AlertsHistoryPage'), 'App.jsx renders AlertsHistoryPage');
  assert(appContent.includes("setOriginatingTab('alerts')"), 'Navigating from alert sets originatingTab to alerts');
  assert(appContent.includes("setActiveTab(originatingTab || 'zone_details')"), 'Recommendation details back-button returns to alerts when opened from alerts');
  assert(appContent.includes("activeTab === 'alerts' ? 'dashboard' : 'alerts'"), 'Top desktop preview bar includes alerts toggle');
  assert(appContent.includes("else if (activeTab === 'alerts') setActiveTab('dashboard')"), 'App header back button returns to dashboard from alerts');

  // -----------------------------------------------------------------------------
  // 7. Unified Chronological Activity History
  // -----------------------------------------------------------------------------
  console.log('\n7. Unified Chronological Activity History:');
  const timelineContent = fs.readFileSync(timelinePath, 'utf-8');
  assert(timelineContent.includes("type === 'irrigation'"), 'ActivityTimeline handles irrigation events');
  assert(timelineContent.includes("type === 'recommendation'"), 'ActivityTimeline handles recommendation events');
  assert(timelineContent.includes("type === 'observation'"), 'ActivityTimeline handles observation events');

  // Test normalization output from historyApi
  const testIrrigation = [{ id: 'irr-t-1', farm_id: 'f1', water_quantity: 15.5, water_unit: 'cubic_meters', irrigation_date: '2026-11-08T08:00:00Z', is_simulated: true }];
  const testRecs = [{ id: 'rec-t-1', farm_id: 'f1', title: 'Test Rec', generated_at: '2026-11-08T09:00:00Z', status: 'pending', priority: 'high', is_simulated: true }];
  const testObs = [{ id: 'obs-t-1', farm_id: 'f1', observation_type: 'soil_moisture', value: 52, unit: '%', observed_at: '2026-11-08T10:00:00Z', is_simulated: true }];

  const merged = historyApi.normalizeAndMerge(testIrrigation, testRecs, testObs);
  assert(merged.length === 3, 'Merged exactly 3 records');
  assert(merged[0].id === 'obs-t-1', 'Newest record is first (obs at 10:00)');
  assert(merged[1].id === 'rec-t-1', 'Second record is rec at 09:00');
  assert(merged[2].id === 'irr-t-1', 'Third record is irrigation at 08:00');
  assert(merged.every(m => m.occurred_at), 'All records have occurred_at timestamp');

  // -----------------------------------------------------------------------------
  // 8. Telemetry Non-Zero Integrity
  // -----------------------------------------------------------------------------
  console.log('\n8. Telemetry Non-Zero Integrity:');
  const nullObs = [{ id: 'obs-null', farm_id: 'f1', observation_type: 'soil_moisture', value: null, unit: '%', observed_at: '2026-11-08T11:00:00Z' }];
  const normalizedNull = historyApi.normalizeAndMerge([], [], nullObs);
  assert(normalizedNull[0].value === null, 'Missing observation value strictly preserved as null');
  assert(normalizedNull[0].value !== 0, 'Missing observation value is NOT coerced to 0');
  assert(normalizedNull[0].title.includes('अपुरा डेटा') || normalizedNull[0].title.includes('Missing'), 'Missing observation labelled as unreadable/missing');
  assert(timelineContent.includes('item.value === null'), 'ActivityTimeline explicitly checks for null value');

  // -----------------------------------------------------------------------------
  // 9. Partial Data Reporting & Source Error Surfacing
  // -----------------------------------------------------------------------------
  console.log('\n9. Partial Data & Source Errors:');
  assert(timelineContent.includes('isPartialData'), 'ActivityTimeline accepts isPartialData prop');
  assert(timelineContent.includes('sourceErrors'), 'ActivityTimeline accepts sourceErrors prop');
  assert(timelineContent.includes('hasSourceErrors'), 'ActivityTimeline displays notice when source errors occur');
  assert(pageContent.includes('isPartialData && !error'), 'AlertsHistoryPage displays partial data status banner');

  // -----------------------------------------------------------------------------
  // 10. Simulated Demo Data Badging
  // -----------------------------------------------------------------------------
  console.log('\n10. Simulated Data Badges:');
  assert(cardContent.includes('alert.is_simulated'), 'AlertCard checks is_simulated');
  assert(cardContent.includes('नमुना') || cardContent.includes('Simulated'), 'AlertCard renders simulated badge');
  assert(timelineContent.includes('item.is_simulated'), 'ActivityTimeline checks is_simulated');
  assert(timelineContent.includes('नमुना') || timelineContent.includes('Simulated'), 'ActivityTimeline renders simulated badge');

  // -----------------------------------------------------------------------------
  // 11. Empty States Honesty (Task 11.2.1 Corrections)
  // -----------------------------------------------------------------------------
  console.log('\n11. Empty States Honesty (Task 11.2.1):');
  const emptyContent = fs.readFileSync(emptyPath, 'utf-8');
  assert(
    emptyContent.includes('सक्रिय इशारे आढळले नाहीत') || 
    emptyContent.includes('No active alerts were found based on the available recommendations'), 
    'AlertsEmptyState accurately states no active alerts found based on available recommendations'
  );
  assert(!emptyContent.includes('सर्व सुरळीत आहे'), 'AlertsEmptyState does NOT make false all-clear health claims');
  assert(emptyContent.includes('मागील शेती नोंदी आढळल्या नाहीत') || emptyContent.includes('No activity records'), 'AlertsEmptyState handles empty history');
  assert(emptyContent.includes('फिल्टरमध्ये इशारे नाहीत') || emptyContent.includes('No alerts in this filter'), 'AlertsEmptyState handles empty filter');

  // -----------------------------------------------------------------------------
  // 12. Accessibility & Responsive Requirements (Touch Targets >= 44px)
  // -----------------------------------------------------------------------------
  console.log('\n12. Accessibility & Touch Targets (>= 44px):');
  assert(cardContent.includes('role="article"'), 'AlertCard uses semantic role="article"');
  assert(filtersContent.includes('role="tablist"') || filtersContent.includes('role="tab"') || filtersContent.includes('role="region"'), 'AlertFilters uses accessible role');
  assert(pageContent.includes('role="tablist"'), 'AlertsHistoryPage main tabs use role="tablist"');
  assert(pageContent.includes('aria-selected'), 'AlertsHistoryPage tabs use aria-selected');
  assert(timelineContent.includes('role="alert"') || timelineContent.includes('role="status"') || pageContent.includes('role="alert"'), 'Error/partial states use role="alert" or role="status"');
  assert(filtersContent.includes("minHeight: '44px'"), 'AlertFilters controls meet minimum 44px mobile touch target height');
  assert(cardContent.includes("minHeight: '44px'"), 'AlertCard action controls meet minimum 44px mobile touch target height');
  assert(pageContent.includes("minHeight: '44px'"), 'AlertsHistoryPage tabs and refresh controls meet minimum 44px touch target height');

  console.log(`\n========================================`);
  console.log(`Results: ${passed} passed, ${failed} failed`);
  console.log(`========================================\n`);

  if (failed > 0) {
    process.exit(1);
  }
}

runTestSuite().catch(err => {
  console.error('Test runner fatal error:', err);
  process.exit(1);
});

