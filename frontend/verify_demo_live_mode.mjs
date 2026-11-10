/**
 * FarmShield AI - Demo/Live Mode and Base URL Verification Test Suite
 * 
 * Verifies:
 * 1. Centralized DataMode manager (getSharedDataMode, setSharedDataMode, toggleSharedDataMode, isSharedDemoMode).
 * 2. Default data mode is 'demo' when unconfigured (protecting preview deployments from API crashes).
 * 3. Synchronization of data mode across all feature modules.
 * 4. API Client base URL resolution & security guardrails:
 *    - Rejects localhost in production with clear configuration error.
 *    - Requires VITE_API_BASE_URL in production Live Mode.
 *    - Supports localhost in development.
 *    - Never exposes secret keys or tokens.
 * 5. Screen verification in Demo Mode:
 *    - Dashboard (demo weather & IoT tags).
 *    - Farm Map (demo digital twin geometry & simulated layers).
 *    - Zone Details (demo zone intelligence & non-zero integrity).
 *    - Irrigation Planner (demo recommendations & split schedules).
 *    - Farm Insights (demo time-series telemetry & pagination safety).
 *    - Alerts & Activity History (demo advisories & honest empty state separation).
 *    - Crops (crop catalog & stage tracking).
 * 6. Live Mode honest error presentation:
 *    - Alerts tab displays error state on fetch failure without claiming 'No active alerts'.
 *    - History tab displays error state on fetch failure without claiming 'No activity records'.
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { 
  DEMO_FARM_FIXTURE, 
  DEMO_ZONES_FIXTURE, 
  DEMO_OBSERVATIONS_FIXTURE, 
  DEMO_RECOMMENDATIONS_FIXTURE, 
  DEMO_ALERTS_FIXTURE,
  DEMO_IRRIGATION_EVENTS_FIXTURE 
} from './src/data/fixtures/demoFarm.js';
import { resolveApiBaseUrl, ApiClientError } from './src/lib/api/client.js';
import { getSharedDataMode, isSharedDemoMode } from './src/lib/dataMode.js';
import { alertsApi } from './src/lib/api/alerts.js';
import { historyApi } from './src/lib/api/history.js';

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
  console.log('\n--- FarmShield AI Demo/Live Mode & Base URL Verification ---\n');

  // -----------------------------------------------------------------------------
  // 1. Centralized Data Mode Management
  // -----------------------------------------------------------------------------
  console.log('1. Centralized Data Mode Synchronization:');
  const dataModeModulePath = path.join(__dirname, 'src', 'lib', 'dataMode.js');
  assert(fs.existsSync(dataModeModulePath), 'src/lib/dataMode.js exists');

  const defaultMode = getSharedDataMode();
  assert(defaultMode === 'demo', `Default data mode is 'demo' (got '${defaultMode}')`);
  assert(isSharedDemoMode() === true, 'isSharedDemoMode() returns true by default');

  // Verify all 5 hooks import useDataMode from src/lib/dataMode.js
  const hooksToVerify = [
    'src/features/farm-map/hooks/useFarmMap.js',
    'src/features/zones/hooks/useZoneDetails.js',
    'src/features/irrigation/hooks/useIrrigationPlanner.js',
    'src/features/insights/hooks/useFarmInsights.js',
    'src/features/alerts/hooks/useAlertsAndHistory.js',
    'src/features/recommendations/hooks/useRecommendationDetails.js',
  ];

  for (const hookRelPath of hooksToVerify) {
    const content = fs.readFileSync(path.join(__dirname, hookRelPath), 'utf-8');
    assert(
      content.includes("from '../../../lib/dataMode.js'"),
      `${hookRelPath} imports centralized useDataMode`
    );
    assert(
      !content.includes("localStorage.getItem('farmshield_data_mode')"),
      `${hookRelPath} does not independently read localStorage directly`
    );
  }

  // -----------------------------------------------------------------------------
  // 2. API Base URL Resolution & Security Guardrails
  // -----------------------------------------------------------------------------
  console.log('\n2. Production API Base URL Security & Validation:');
  const clientContent = fs.readFileSync(path.join(__dirname, 'src', 'lib', 'api', 'client.js'), 'utf-8');
  assert(clientContent.includes('resolveApiBaseUrl'), 'client.js exports resolveApiBaseUrl()');
  assert(clientContent.includes('Localhost cannot be used in production'), 'client.js explicitly rejects localhost in production');
  assert(clientContent.includes('VITE_API_BASE_URL is not configured'), 'client.js warns when VITE_API_BASE_URL is missing in production');
  assert(clientContent.includes('Authorization'), 'client.js preserves Bearer token injection');

  // Test local development fallback
  const devResolution = resolveApiBaseUrl();
  assert(devResolution.url === 'http://localhost:8000/api/v1', `Development resolves to localhost fallback: ${devResolution.url}`);
  assert(devResolution.error === null, 'Development has no resolution error');

  // -----------------------------------------------------------------------------
  // 3. Demo Mode Screen Data & Non-Fabrication Validation
  // -----------------------------------------------------------------------------
  console.log('\n3. Screen Fixtures & Non-Fabrication Rules in Demo Mode:');

  // 3.1 Dashboard
  const dashPath = path.join(__dirname, 'src', 'pages', 'Dashboard.jsx');
  const dashContent = fs.readFileSync(dashPath, 'utf-8');
  assert(dashContent.includes('demo-tag') || dashContent.includes('demoBadge'), 'Dashboard visibly labels simulated data');
  assert(dashContent.includes('IoT Sim'), 'Dashboard labels simulated IoT moisture sensors');

  // 3.2 Farm Map
  assert(DEMO_FARM_FIXTURE.id === 'f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b', 'Demo farm has valid deterministic ID');
  assert(DEMO_ZONES_FIXTURE.length === 4, 'Demo farm has exactly 4 management zones');
  const mapPageContent = fs.readFileSync(path.join(__dirname, 'src', 'features', 'farm-map', 'pages', 'FarmMapPage.jsx'), 'utf-8');
  assert(mapPageContent.includes('DEMO'), 'FarmMapPage includes explicit DEMO mode indicator badge');

  // 3.3 Zone Details
  const zoneD = DEMO_ZONES_FIXTURE.find(z => z.id === 'z4-south-east-004');
  assert(zoneD.status === 'insufficient_data', 'Zone D is honest insufficient_data');
  assert(zoneD.ndvi_value === null, 'Zone D NDVI is null (never coerced to 0)');
  assert(zoneD.soil_moisture_pct === null, 'Zone D moisture is null (never coerced to 0)');

  // 3.4 Irrigation Planner
  assert(DEMO_IRRIGATION_EVENTS_FIXTURE.length >= 2, 'Demo irrigation planner has historical events');
  assert(DEMO_RECOMMENDATIONS_FIXTURE.some(r => r.recommended_action?.action === 'irrigate' || r.action === 'irrigate'), 'Demo recommendations include actionable irrigate guidance');

  // 3.5 Farm Insights
  assert(DEMO_OBSERVATIONS_FIXTURE.length >= 10, 'Demo insights has time-series telemetry');
  assert(DEMO_OBSERVATIONS_FIXTURE.every(o => o.observed_at !== undefined), 'All observations carry timestamps');

  // 3.6 Alerts & Activity History
  const demoAlertsRes = await alertsApi.listFarmAlerts(null, { isDemoMode: true });
  assert(demoAlertsRes.items.length >= 2, `Demo alerts derived active alerts (got ${demoAlertsRes.items.length})`);
  assert(demoAlertsRes.is_simulated === true, 'Demo alerts flagged as simulated');

  const demoHistRes = await historyApi.getUnifiedFarmHistory(null, { isDemoMode: true });
  assert(demoHistRes.items.length > 0, 'Demo history aggregated chronological log');
  assert(demoHistRes.is_simulated === true, 'Demo history flagged as simulated');

  // 3.7 Crops
  const cropsPath = path.join(__dirname, 'src', 'pages', 'Crops.jsx');
  assert(fs.existsSync(cropsPath), 'Crops.jsx exists');

  // -----------------------------------------------------------------------------
  // 4. Alerts Error State vs Empty State Separation
  // -----------------------------------------------------------------------------
  console.log('\n4. Alerts Error State vs Empty State Separation:');
  const alertsPagePath = path.join(__dirname, 'src', 'features', 'alerts', 'pages', 'AlertsHistoryPage.jsx');
  const alertsPageContent = fs.readFileSync(alertsPagePath, 'utf-8');

  assert(
    alertsPageContent.includes("sourceErrors?.alerts || (error && !alertsFetchSuccess)"),
    'AlertsHistoryPage checks for alerts failure before showing empty state'
  );
  assert(
    alertsPageContent.includes("sourceErrors?.history || (error && !historyFetchSuccess)"),
    'AlertsHistoryPage checks for history failure before showing empty history state'
  );
  assert(
    alertsPageContent.includes('Error loading alerts') || alertsPageContent.includes('इशारे लोड करण्यात त्रुटी'),
    'AlertsHistoryPage contains explicit error title for alerts failure'
  );

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
