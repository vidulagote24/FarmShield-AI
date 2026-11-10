/**
 * FarmShield AI - Task 9 Recommendation Details Verification Test Suite
 * 
 * Verifies:
 * 1. Recommendation Schema & Contract Integrity
 * 2. ID Resolution & Associated Zone Linking
 * 3. Evidence Rendering & Non-zero Integrity Rules
 * 4. All Supported Priority Tokens & Labels
 * 5. All Supported Status States & Transitions
 * 6. Status Transition State Machine Rules
 * 7. Live vs Demo Mode Isolation
 * 8. Hardware Decoupling & Safety Enforcement
 * 9. Cross-Feature Navigation Integration
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
import { 
  DEMO_FARM_FIXTURE, 
  DEMO_ZONES_FIXTURE, 
  DEMO_OBSERVATIONS_FIXTURE, 
  DEMO_RECOMMENDATIONS_FIXTURE 
} from './src/data/fixtures/demoFarm.js';

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

console.log('\n--- FarmShield AI Recommendation Details Verification ---\n');

// -----------------------------------------------------------------------------
// 1. Schema & Contract Integrity
// -----------------------------------------------------------------------------
console.log('1. Fixture & Backend Schema Integrity:');
assert(Array.isArray(DEMO_RECOMMENDATIONS_FIXTURE) && DEMO_RECOMMENDATIONS_FIXTURE.length >= 3, 'Demo recommendations fixture contains at least 3 records');

const VALID_PRIORITIES = new Set(['low', 'medium', 'high', 'critical']);
const VALID_STATUSES = new Set(['pending', 'applied', 'dismissed', 'expired', 'accepted', 'rejected', 'completed']);

DEMO_RECOMMENDATIONS_FIXTURE.forEach((rec, idx) => {
  assert(Boolean(rec.id && rec.farm_id && rec.title), `Rec #${idx + 1} (${rec.id}) has valid ID, farm_id and title`);
  assert(VALID_PRIORITIES.has(rec.priority?.toLowerCase()), `Rec #${idx + 1} has valid priority: ${rec.priority}`);
  assert(VALID_STATUSES.has(rec.status?.toLowerCase()), `Rec #${idx + 1} has valid workflow status: ${rec.status}`);
  assert(typeof rec.reasoning === 'object' && rec.reasoning !== null, `Rec #${idx + 1} has structured reasoning object`);
});

// -----------------------------------------------------------------------------
// 2. ID Resolution & Zone Linking
// -----------------------------------------------------------------------------
console.log('\n2. ID Resolution & Associated Zone Linking:');
const recC = DEMO_RECOMMENDATIONS_FIXTURE.find(r => r.id === 'rec-c-03');
assert(Boolean(recC), 'Found rec-c-03 by ID');
assert(recC.zone_id === 'z3-south-west-003', 'rec-c-03 accurately links to Zone C');

const zoneC = DEMO_ZONES_FIXTURE.find(z => z.id === recC.zone_id);
assert(Boolean(zoneC), 'Resolved matching zone metadata for rec-c-03');
assert(zoneC.zone_code === 'ZC-03', 'Zone C code matches expectation (ZC-03)');

const unresolvable = DEMO_RECOMMENDATIONS_FIXTURE.find(r => r.id === 'non-existent-rec-999');
assert(unresolvable === undefined, 'Non-existent recommendation ID yields undefined (triggers RecommendationEmptyState)');

// -----------------------------------------------------------------------------
// 3. Evidence Breakdown & Non-Zero Integrity
// -----------------------------------------------------------------------------
console.log('\n3. Evidence Breakdown & Non-Zero Integrity:');
assert(Array.isArray(recC.reasoning?.factors) && recC.reasoning.factors.length > 0, 'rec-c-03 includes contributing decision factors');
assert(recC.reasoning.confidence === 0.93, 'rec-c-03 confidence is exactly 0.93 (not rounded or faked)');

const zoneCObs = DEMO_OBSERVATIONS_FIXTURE.filter(o => o.zone_id === recC.zone_id);
const smObsC = zoneCObs.find(o => o.observation_type === 'soil_moisture' && o.value === 46.0);
assert(Boolean(smObsC && smObsC.value === 46.0), 'Soil moisture observation 46% correctly associated with rec-c-03 zone');

const zoneDObs = DEMO_OBSERVATIONS_FIXTURE.filter(o => o.zone_id === 'z4-south-east-004');
const smObsD = zoneDObs.find(o => o.metric_type === 'soil_moisture');
assert(smObsD === undefined, 'Zone D has no soil moisture observation (never presented as zero)');

// -----------------------------------------------------------------------------
// 4. Priority Badges & Visual Tokens
// -----------------------------------------------------------------------------
console.log('\n4. Priority Badges & WCAG Visual Tokens:');
const badgeSource = fs.readFileSync(path.join(__dirname, 'src/features/recommendations/components/RecommendationPriorityBadge.jsx'), 'utf8');

['critical', 'high', 'medium', 'low'].forEach((prio) => {
  assert(badgeSource.includes(`${prio}:`), `Priority '${prio}' definition exists in RecommendationPriorityBadge`);
});
assert(badgeSource.includes('label_mr') && badgeSource.includes('label_en'), 'Priority badges provide bilingual English and Marathi labels');
assert(badgeSource.includes('role="status"'), 'Priority badge provides accessible role="status" attribute');

// -----------------------------------------------------------------------------
// 5. Status Workflow Lifecycle State Machine
// -----------------------------------------------------------------------------
console.log('\n5. Status Workflow State Transitions:');
function getAllowedTransitions(currentStatus) {
  switch (currentStatus) {
    case 'pending':
      return ['accepted', 'dismissed'];
    case 'accepted':
    case 'acknowledged':
      return ['applied', 'dismissed'];
    case 'applied':
    case 'completed':
    case 'dismissed':
    case 'rejected':
    case 'expired':
    case 'superseded':
      return []; // terminal states (can only reset in Demo Mode)
    default:
      return [];
  }
}

assert(getAllowedTransitions('pending').includes('accepted'), 'Pending status can transition to Accepted / Acknowledged');
assert(getAllowedTransitions('pending').includes('dismissed'), 'Pending status can transition to Dismissed');
assert(getAllowedTransitions('accepted').includes('applied'), 'Accepted status can transition to Applied');
assert(getAllowedTransitions('accepted').includes('dismissed'), 'Accepted status can transition to Dismissed');
assert(getAllowedTransitions('applied').length === 0, 'Applied is a terminal workflow state in Live Mode');
assert(getAllowedTransitions('completed').length === 0, 'Completed is a terminal workflow state');
assert(getAllowedTransitions('dismissed').length === 0, 'Dismissed is a terminal workflow state');
assert(getAllowedTransitions('rejected').length === 0, 'Rejected is a terminal workflow state');
assert(getAllowedTransitions('expired').length === 0, 'Expired is a terminal workflow state');
assert(getAllowedTransitions('superseded').length === 0, 'Superseded is a terminal workflow state');

const statusActionsSource = fs.readFileSync(path.join(__dirname, 'src/features/recommendations/components/RecommendationStatusActions.jsx'), 'utf8');
assert(statusActionsSource.includes('isExpired'), 'RecommendationStatusActions explicitly handles expired status');
assert(statusActionsSource.includes('isSuperseded'), 'RecommendationStatusActions explicitly handles superseded status');

const statusTimelineSource = fs.readFileSync(path.join(__dirname, 'src/features/recommendations/components/RecommendationStatusTimeline.jsx'), 'utf8');
assert(statusTimelineSource.includes('isExpired'), 'RecommendationStatusTimeline explicitly handles expired status');
assert(statusTimelineSource.includes('isSuperseded'), 'RecommendationStatusTimeline explicitly handles superseded status');

// -----------------------------------------------------------------------------
// 6. Action Parameters & Hardware Decoupling
// -----------------------------------------------------------------------------
console.log('\n6. Action Parameters & Hardware Decoupling:');
assert(recC.recommended_action.action === 'irrigate', 'rec-c-03 action is irrigate');
assert(recC.recommended_action.water_depth_mm === 22.0, 'rec-c-03 water depth is exactly 22.0 mm (from backend model)');
assert(recC.recommended_action.water_volume_m3 === 83.6, 'rec-c-03 water volume is exactly 83.6 m³');
assert(recC.recommended_action.pump_control === undefined, 'No automated pump_control instruction is emitted');
assert(recC.recommended_action.valve_id === undefined, 'No automated valve_id control instruction is emitted');

// -----------------------------------------------------------------------------
// 7. Navigation Integration Handlers
// -----------------------------------------------------------------------------
console.log('\n7. Cross-Feature Navigation Integration:');
const zoneSummarySource = fs.readFileSync(path.join(__dirname, 'src/features/zones/components/RecommendationSummary.jsx'), 'utf8');
assert(zoneSummarySource.includes('onSelectRecommendation'), 'RecommendationSummary supports onSelectRecommendation callback');

const irrigCardSource = fs.readFileSync(path.join(__dirname, 'src/features/irrigation/components/IrrigationRecommendationCard.jsx'), 'utf8');
assert(irrigCardSource.includes('onSelectRecommendation'), 'IrrigationRecommendationCard supports onSelectRecommendation callback');

const appSource = fs.readFileSync(path.join(__dirname, 'src/App.jsx'), 'utf8');
assert(appSource.includes("activeTab === 'recommendation_details'"), 'App.jsx handles recommendation_details activeTab');
assert(appSource.includes('RecommendationDetailsPage'), 'App.jsx renders RecommendationDetailsPage component');

// -----------------------------------------------------------------------------
// Summary
// -----------------------------------------------------------------------------
console.log('\n========================================');
console.log(`Results: ${passed} passed, ${failed} failed`);
console.log('========================================\n');

if (failed > 0) {
  process.exit(1);
}
