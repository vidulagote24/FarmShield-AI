/**
 * FarmShield AI - Zone Intelligence Verification Test Suite
 * 
 * Tests the business rules, data schemas, edge cases, and fixture integrity
 * for Task 7: Zone Intelligence Screen.
 */

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

console.log('\n--- FarmShield AI Zone Intelligence Verification ---\n');

// 1. Fixture & Topology Integrity
console.log('1. Fixture & Schema Integrity:');
assert(DEMO_FARM_FIXTURE && DEMO_FARM_FIXTURE.id, 'Demo farm has valid ID');
assert(DEMO_ZONES_FIXTURE.length === 4, 'Demo farm contains exactly 4 agronomic zones');
assert(DEMO_OBSERVATIONS_FIXTURE.length > 0, 'Observations fixture is populated');
assert(DEMO_RECOMMENDATIONS_FIXTURE.length > 0, 'Recommendations fixture is populated');

// 2. Zone A (Healthy Baseline) Verification
console.log('\n2. Zone A (Healthy Baseline) Tests:');
const zoneA = DEMO_ZONES_FIXTURE.find(z => z.id === 'z1-north-west-001');
assert(zoneA !== undefined, 'Zone A exists');
assert(zoneA.status === 'healthy', 'Zone A status is healthy');
assert(zoneA.ndvi_value === 0.74, 'Zone A NDVI is 0.74');
assert(zoneA.soil_moisture_pct === 68, 'Zone A soil moisture is 68%');

const obsA = DEMO_OBSERVATIONS_FIXTURE.filter(o => o.zone_id === zoneA.id);
const smObsA = obsA.filter(o => o.observation_type === 'soil_moisture');
assert(smObsA.length === 4, 'Zone A has 4 dated soil moisture observations (multi-point trend enabled)');
assert(smObsA.every(o => o.unit === '%' && typeof o.value === 'number'), 'All Zone A soil moisture observations have valid % unit and numeric value');

const recA = DEMO_RECOMMENDATIONS_FIXTURE.filter(r => r.zone_id === zoneA.id);
assert(recA.length === 1, 'Zone A has 1 active recommendation');
assert(recA[0].priority === 'low', 'Zone A recommendation priority is low');
assert(recA[0].recommended_action.action === 'wait', 'Zone A recommended action is wait');

// 3. Zone B (Monitor Scenario) Verification
console.log('\n3. Zone B (Monitor Scenario) Tests:');
const zoneB = DEMO_ZONES_FIXTURE.find(z => z.id === 'z2-north-east-002');
assert(zoneB !== undefined, 'Zone B exists');
assert(zoneB.status === 'monitor', 'Zone B status is monitor');
const obsB = DEMO_OBSERVATIONS_FIXTURE.filter(o => o.zone_id === zoneB.id);
const smObsB = obsB.filter(o => o.observation_type === 'soil_moisture');
assert(smObsB.length >= 2, 'Zone B has >= 2 observations to calculate trend');
const recB = DEMO_RECOMMENDATIONS_FIXTURE.filter(r => r.zone_id === zoneB.id);
assert(recB.length === 1 && recB[0].priority === 'medium', 'Zone B recommendation is medium priority');

// 4. Zone C (Attention / Urgent Drip Irrigation) Verification
console.log('\n4. Zone C (Attention / Urgent Drip) Tests:');
const zoneC = DEMO_ZONES_FIXTURE.find(z => z.id === 'z3-south-west-003');
assert(zoneC !== undefined, 'Zone C exists');
assert(zoneC.status === 'attention', 'Zone C status is attention');
const obsC = DEMO_OBSERVATIONS_FIXTURE.filter(o => o.zone_id === zoneC.id);
const recC = DEMO_RECOMMENDATIONS_FIXTURE.filter(r => r.zone_id === zoneC.id);
assert(recC.length === 1, 'Zone C has 1 recommendation');
assert(recC[0].priority === 'high', 'Zone C priority is high');
assert(recC[0].recommended_action.action === 'irrigate', 'Zone C action is irrigate');
assert(recC[0].recommended_action.water_depth_mm === 22.0, 'Zone C water depth is 22.0 mm');
assert(recC[0].recommended_action.water_volume_m3 === 83.6, 'Zone C water volume is 83.6 m³');

// 5. Zone D (Insufficient Data Scenario) Verification
console.log('\n5. Zone D (Honest Insufficient Data State) Tests:');
const zoneD = DEMO_ZONES_FIXTURE.find(z => z.id === 'z4-south-east-004');
assert(zoneD !== undefined, 'Zone D exists');
assert(zoneD.status === 'insufficient_data', 'Zone D status is insufficient_data');
assert(zoneD.ndvi_value === null, 'Zone D NDVI is null (not fabricated as 0)');
assert(zoneD.soil_moisture_pct === null, 'Zone D moisture is null (not fabricated as 0)');

const obsD = DEMO_OBSERVATIONS_FIXTURE.filter(o => o.zone_id === zoneD.id);
const validObsD = obsD.filter(o => o.value !== null && o.value !== undefined);
assert(validObsD.length === 0, 'Zone D has zero valid numerical observations (triggers InsufficientDataState)');

const recD = DEMO_RECOMMENDATIONS_FIXTURE.filter(r => r.zone_id === zoneD.id);
assert(recD.length === 0, 'Zone D has 0 recommendations (honestly empty, no fabricated advice)');

// 6. Scientific Constraint Verifications (per AGENTS.md)
console.log('\n6. Scientific Constraint & Non-zero Integrity Tests:');
assert(!obsA.some(o => o.value === 0 && o.observation_type === 'soil_moisture'), 'No missing soil moisture readings are represented as 0 in Zone A');
assert(!obsB.some(o => o.value === 0 && o.observation_type === 'soil_moisture'), 'No missing soil moisture readings are represented as 0 in Zone B');
assert(!obsC.some(o => o.value === 0 && o.observation_type === 'soil_moisture'), 'No missing soil moisture readings are represented as 0 in Zone C');

// Check trend threshold requirements (<2 observations must not render misleading trend)
const trendAllowedForA = smObsA.length >= 2;
const trendAllowedForD = validObsD.length >= 2;
assert(trendAllowedForA === true, 'Zone A passes trend threshold (>1 observation)');
assert(trendAllowedForD === false, 'Zone D correctly prevented from plotting trend (0 observations)');

console.log(`\n========================================`);
console.log(`Results: ${passed} passed, ${failed} failed`);
console.log(`========================================\n`);

if (failed > 0) {
  process.exit(1);
} else {
  process.exit(0);
}
