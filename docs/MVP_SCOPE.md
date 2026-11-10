# MVP Scope and Acceptance Boundary

## 1. MVP statement

The first prototype proves one complete scenario:

> A farmer selects one farm. FarmShield displays its zones and available satellite/weather/soil evidence, assesses zone conditions, calculates irrigation need where the required inputs exist, explains the result and records the farmer's action.

The team must prioritize a trustworthy, end-to-end flow over a large number of disconnected features.

## 2. Included in the MVP

### Farm setup
- Create/select farm.
- Store name, location, boundary, area, crop, sowing date/growth stage, soil information where known and irrigation method.
- Support manual zone definitions or pre-prepared zone polygons.

### Data
- Weather API adapter for historical and forecast information.
- Satellite processing for at least one usable Sentinel-2 observation and vegetation index.
- Provider/source identifiers, observation timestamps, spatial resolution and quality fields.
- Optional farmer-entered or sensor moisture reading.

### Digital twin
- Farm boundary and zone polygons displayed on an interactive map.
- Layer switcher for available evidence (health/vegetation, weather or moisture evidence only when data exists).
- Zone-level summary and freshness indicator.

### Intelligence
- Vegetation index calculation/aggregation.
- FAO-56-aligned crop evapotranspiration calculation where inputs exist.
- Root-zone water-balance approach with explicit soil and crop assumptions.
- Rule-based zone assessment, recommendation and validation.
- Reason codes, evidence list, calculation inputs and uncertainty/data sufficiency.

### Farmer experience
- Mobile-first dashboard.
- Zone detail and recommendation screens.
- Irrigation plan and action recording.
- Insights/history.
- English and Marathi translation; Hindi translation structure established.
- Loading, error, offline and stale-data states.

## 3. Not included in the MVP

- Automatic irrigation actuation or pump/valve control.
- Guaranteed real-time satellite observation.
- Precision root-zone soil moisture inferred from Sentinel-2 alone.
- Validated crop-yield prediction.
- Trained drought/crop-stress ML prediction without labelled training and evaluation data.
- Flood forecasting and emergency response.
- Drone integration.
- District/state administration dashboard.
- Marketplace, market prices, equipment management or farm accounting.
- Multi-agent AI, model retraining pipeline or complex orchestration.
- Redis/Celery unless a measured requirement is accepted.

## 4. Prototype data modes

The system must support these modes explicitly:

1. **Live/source-backed:** Retrieved from a named provider with actual retrieval/observation time.
2. **Farmer-entered:** Entered by a user, with entry time and optional measurement method.
3. **Derived:** Calculated from documented inputs and a versioned formula.
4. **Modelled/estimated:** Produced by an external model or internal estimate; label as estimated.
5. **Simulated:** Used only for a demo or development fixture; show a visible demo/simulated label.
6. **Unavailable:** Required information is absent or unusable; show unavailable/insufficient data.

Do not mix these modes without retaining provenance.

## 5. Minimum demo acceptance criteria

The MVP is accepted only when all critical checks below pass:

- A farm can be created and retrieved through the backend.
- Boundary geometry is valid and renders on a phone.
- Four to six zones can be selected independently.
- Each zone has an assessment state and data-quality state.
- Satellite-derived vegetation data is traceable to a scene/date and quality check.
- Weather data contains source, location, units and timestamps.
- Water calculation records its inputs and formula version.
- Missing essential inputs lead to `insufficient_data`, not a fabricated irrigation amount.
- A recommendation includes action, reason codes, confidence/quality information and evidence references.
- UI can render the recommendation in English and Marathi.
- Farmer can record an irrigation event and view it in history.
- The demonstration can be repeated from a documented seed dataset without manual database edits.

## 6. MVP release blockers

- Any hardcoded recommendation presented as a live calculation.
- Any missing measurement presented as a real sensor reading.
- Invalid or self-intersecting farm geometry without validation feedback.
- Unlabelled stale observations.
- Recommendation with no evidence or calculation trace.
- Broken mobile navigation or unreadable Devanagari text.
- A failed core flow that requires a developer to edit the database manually during demo.

## 7. Later release candidates

- Sentinel-1 radar feature integration.
- Automated management zone generation.
- Field sensor integrations and calibration.
- Crop-specific stress models with validated datasets.
- Closed-loop recommendation evaluation.
- Regional portfolio and resource allocation views.
- Offline-first action queue with robust conflict handling.
