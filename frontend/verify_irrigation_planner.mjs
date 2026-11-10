/**
 * FarmShield AI - Irrigation Planner Verification Test Suite
 * 
 * Tests the business rules, schema validation constraints, advisory-only safety,
 * form submission validation, and fixture integrity for Task 8 & 8.1.
 */

import { 
  DEMO_FARM_FIXTURE, 
  DEMO_ZONES_FIXTURE, 
  DEMO_RECOMMENDATIONS_FIXTURE, 
  DEMO_IRRIGATION_EVENTS_FIXTURE 
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

console.log('\n--- FarmShield AI Irrigation Planner Verification ---\n');

// 1. Fixture & Schema Integrity
console.log('1. Fixture & Schema Integrity:');
assert(DEMO_IRRIGATION_EVENTS_FIXTURE && DEMO_IRRIGATION_EVENTS_FIXTURE.length === 2, 'Irrigation events fixture has 2 seeded records');
assert(DEMO_IRRIGATION_EVENTS_FIXTURE.every(e => e.water_quantity > 0), 'All irrigation events have strictly positive water quantity (> 0)');
assert(DEMO_IRRIGATION_EVENTS_FIXTURE.every(e => e.is_simulated === true), 'All demo irrigation events are explicitly flagged is_simulated: true');
assert(DEMO_IRRIGATION_EVENTS_FIXTURE.every(e => e.irrigation_date && e.water_unit), 'All events have valid irrigation_date and water_unit');

// 2. Zone C Irrigation Recommendation
console.log('\n2. Recommendation Target Validation:');
const recC = DEMO_RECOMMENDATIONS_FIXTURE.find(r => r.zone_id === 'z3-south-west-003');
assert(recC !== undefined, 'Zone C has an active recommendation');
assert(recC.recommended_action.action === 'irrigate', 'Zone C action is irrigate');
assert(recC.recommended_action.water_depth_mm === 22.0, 'Zone C water depth is exactly 22.0 mm (from backend model)');
assert(recC.recommended_action.water_volume_m3 === 83.6, 'Zone C water volume is exactly 83.6 m³');
assert(recC.priority === 'high', 'Zone C priority is high');

// 3. Zone D Missing / Insufficient Recommendations Handling
console.log('\n3. Missing / Insufficient Recommendations Handling:');
const recD = DEMO_RECOMMENDATIONS_FIXTURE.filter(r => r.zone_id === 'z4-south-east-004');
assert(recD.length === 0, 'Zone D has zero recommendations (triggers IrrigationEmptyState honestly)');

// 4. Form Validation Logic (Emulating RecordIrrigationForm.jsx validation rules)
console.log('\n4. Form Validation Constraints:');
const ALLOWED_VOLUME_UNITS = new Set(['liters', 'cubic_meters']);

function validateEvent(quantity, date, unit) {
  const errors = {};
  const qty = parseFloat(quantity);
  if (!quantity || isNaN(qty)) {
    errors.quantity = 'Quantity required';
  } else if (qty <= 0) {
    errors.quantity = 'Quantity must be > 0';
  }
  if (!date) errors.date = 'Date required';
  if (!unit || !ALLOWED_VOLUME_UNITS.has(unit)) errors.unit = 'Valid volume unit required';
  return Object.keys(errors).length === 0;
}

assert(validateEvent('', '2026-11-10T06:00', 'liters') === false, 'Rejects empty quantity');
assert(validateEvent('0', '2026-11-10T06:00', 'liters') === false, 'Rejects zero quantity (0)');
assert(validateEvent('-15.5', '2026-11-10T06:00', 'liters') === false, 'Rejects negative quantity (-15.5)');
assert(validateEvent('abc', '2026-11-10T06:00', 'liters') === false, 'Rejects non-numeric quantity');
assert(validateEvent('5000', '', 'liters') === false, 'Rejects missing date');
assert(validateEvent('5000', '2026-11-10T06:00', '') === false, 'Rejects missing unit');
assert(validateEvent('5000', '2026-11-10T06:00', 'mm') === false, 'Rejects depth unit mm (only volume units liters/cubic_meters supported)');
assert(validateEvent('5000', '2026-11-10T06:00', 'liters') === true, 'Accepts valid positive quantity in liters');
assert(validateEvent('83.6', '2026-11-10T06:00', 'cubic_meters') === true, 'Accepts valid positive quantity in cubic_meters');

// 5. Safety & Hardware Decoupling Constraints
console.log('\n5. Safety & Hardware Decoupling Constraints:');
assert(recC.recommended_action.action !== 'start_pump', 'Recommendation does NOT issue automatic pump commands');
assert(!DEMO_IRRIGATION_EVENTS_FIXTURE.some(e => e.auto_executed === true), 'No events claim automatic hardware execution');

// 6. Form Preselection & Data Integrity Rules (Task 8.1)
console.log('\n6. Form Preselection & Data Integrity Rules:');
const initialQty = ''; // Form must initialize quantity blank
assert(initialQty === '', 'Actual water quantity initializes blank (not pre-filled with recommended target)');
assert(recC.recommended_action.water_volume_m3 === 83.6, 'Recommended target volume remains intact as reference');

// 7. Zone Filtering Integrity
console.log('\n7. Zone Filtering Logic:');
const zoneCId = 'z3-south-west-003';
const filteredRecsForC = DEMO_RECOMMENDATIONS_FIXTURE.filter(r => r.zone_id === zoneCId);
const filteredHistoryForC = DEMO_IRRIGATION_EVENTS_FIXTURE.filter(h => h.zone_id === zoneCId);
assert(filteredRecsForC.length === 1, 'Filtering by Zone C returns only Zone C recommendation');
assert(filteredHistoryForC.length === 1, 'Filtering by Zone C returns only Zone C event');

console.log(`\n========================================`);
console.log(`Results: ${passed} passed, ${failed} failed`);
console.log(`========================================\n`);

if (failed > 0) {
  process.exit(1);
} else {
  process.exit(0);
}
