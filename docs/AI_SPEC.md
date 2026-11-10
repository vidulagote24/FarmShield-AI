# AI, Geospatial and Agronomic Intelligence Specification

**Owner:** Bhavikesh Hedau  
**Purpose:** Convert normalized evidence into traceable zone-level assessments and irrigation decision support.

## 1. Intelligence principles

- Use multiple evidence types; a single vegetation index is not a drought diagnosis.
- Keep observed, estimated and derived values distinct.
- Use documented agronomic equations for crop-water calculations.
- Use machine learning only where training labels, validation data and evaluation method exist.
- Decision engine must be deterministic for the same inputs/configuration/version.
- Missing or poor-quality inputs must produce `insufficient_data` or a limited assessment.
- No autonomous pump/valve control in the MVP.
- Every assessment stores input IDs, calculation version, assumptions, evidence and quality.

## 2. Input contract

The intelligence layer consumes normalized objects, not provider raw payloads.

Minimum context:

- Farm ID, boundary, timezone and area.
- Zone ID and geometry.
- Crop name, sowing date/growth stage and relevant crop parameters.
- Soil information: texture/available water capacity/field capacity/wilting point/root-zone properties where available.
- Weather: precipitation, temperature and ET₀ with source/time.
- Satellite observations: red/NIR (or derived index) with cloud/quality mask and acquisition date.
- Soil moisture observation/estimate when available, with depth, resolution and provenance.
- Irrigation method and efficiency if supplied or supported by a documented assumption.

## 3. Satellite feature processing

### Sentinel-2 NDVI

For surface-reflectance red and near-infrared bands:

`NDVI = (NIR - Red) / (NIR + Red)`

For Sentinel-2 MSI, common bands are B4 (red) and B8 (near infrared), both nominally 10 m. Apply appropriate cloud/shadow masking, scale factors and quality screening. Do not treat a cloudy/unusable observation as a healthy or zero-value observation.

### Moisture-related indices

Do not use the ambiguous label `NDWI` without specifying the formula. If using a vegetation moisture index such as NDMI, document the exact bands and formula (commonly NIR and SWIR1, subject to product/band definitions). The index is a spectral indicator, not a direct soil moisture measurement.

### Zone aggregation

For each usable scene:

- Intersect raster pixels with zone geometry.
- Apply cloud/quality mask.
- Calculate robust summary (median/mean plus valid-pixel count and valid-pixel fraction).
- Store acquisition date, scene reference, processing version, band/index, resolution and quality metadata.
- Compare only temporally comparable observations and display observation dates.

If there are too few valid pixels, return unavailable/insufficient evidence rather than a fabricated summary.

## 4. Weather features

Canonical variables should include where available:

- `precipitation_mm`
- `temperature_2m_c`
- `relative_humidity_pct`
- `wind_speed_10m_kmh` or canonical m/s (choose one and convert consistently)
- `shortwave_radiation_mj_m2_day` or provider-native variable with conversion documented
- `et0_mm_day`
- forecast precipitation and valid period

Keep historical observations, forecast values and forecast probabilities separate. Record provider model/run and retrieval time where available. Do not describe modelled soil-moisture grid values as field readings.

## 5. Agronomic water calculation

### Reference evapotranspiration

Use FAO-56 Penman–Monteith ET₀ when inputs or a documented provider calculation are available. A provider's `et0_fao_evapotranspiration` can be used as an input if its source and method are retained; do not recalculate it from incomplete weather variables without documenting assumptions.

### Crop evapotranspiration

`ETc = Kc × ET0`

Where:
- `ETc` = crop evapotranspiration (mm/day)
- `Kc` = crop coefficient appropriate to crop and stage
- `ET0` = reference evapotranspiration (mm/day)

Crop coefficient values must come from a documented, crop/region/stage-appropriate reference or an explicitly labelled assumption reviewed by an agronomist. Do not invent Kc values.

### Root-zone water balance

A final irrigation recommendation needs more than ETc. Model the root-zone water balance using available water capacity, root depth, current depletion/soil moisture, effective rainfall, crop stage and any irrigation already applied. Use a documented FAO-56-compatible depletion/irrigation scheduling approach appropriate to the crop and available inputs.

Net irrigation requirement should be derived from the water-balance deficit and allowable depletion/management objective, not simply equated to ETc. Gross irrigation requirement may account for application efficiency:

`Gross irrigation depth = Net irrigation depth / application efficiency`

Use efficiency as a fraction between 0 and 1, with source/assumption recorded. Convert depth to volume consistently:

`Volume (m³) = depth (mm) × area (m²) / 1000`

Check units and avoid double-counting rainfall or irrigation already included in the balance.

### Missing-input policy

If root-zone moisture/depletion, soil water characteristics, root depth, crop coefficient or other essential inputs are unavailable, the engine may:

- Provide a qualitative review/inspection recommendation supported by evidence; or
- Provide a clearly labelled estimate/range only if a documented approved method and sufficient inputs exist.

It must not output a precise irrigation volume by substituting arbitrary defaults.

## 6. Crop/water stress assessment

For the MVP, implement an evidence-based rule/score framework only after agronomist review of input definitions and thresholds.

Potential evidence:

- Vegetation index level and trend across comparable observations.
- Recent rainfall and forecast rainfall.
- ET₀ / evaporative demand.
- Soil moisture evidence with provenance/depth/resolution.
- Crop type, growth stage and sensitivity.
- Root-zone water depletion where calculable.

Do not equate NDVI decrease to drought automatically. Alternative causes include crop stage, nutrient/pest/disease stress, management changes, image noise and cloud contamination. Explanations must say `possible water stress` unless corroborating evidence supports a stronger assessment.

Status enum:

- `healthy`
- `monitor`
- `attention`
- `high_stress`
- `insufficient_data`

Thresholds are configuration/data decisions, not arbitrary constants. Record threshold-set version and validation source.

## 7. Decision engine

Input: zone context, observations, water-balance output, quality and crop parameters.

Output:

- `action_code`: `irrigate`, `monitor`, `delay_and_reassess`, `inspect`, `no_action_indicated`, `insufficient_data`.
- priority: low/medium/high/urgent.
- water depth/volume only when calculation is valid.
- recommended time window only when forecast and operational inputs support it.
- reason codes and evidence IDs.
- assumptions, quality flags and uncertainty note.

The rules should be explicit, testable and versioned. Never force a decision when evidence conflicts or is insufficient.

## 8. Explanation layer

First generate a structured explanation object from deterministic outputs:

- observed facts;
- derived indicators;
- calculation summary;
- reason codes;
- missing inputs;
- uncertainty and limitations;
- recommended next step.

A template renderer is sufficient for the MVP. An LLM may later rewrite this structured object in farmer-friendly language, but it must not add unsupported facts, change quantities, invent evidence or override the action code. Store the structured source separately from rendered text.

## 9. Validation and evaluation

### Unit tests

- NDVI calculation and zero denominator.
- Cloud/invalid-pixel handling.
- Zone aggregation and valid-pixel thresholds.
- ETc calculation and unit conversions.
- Effective rainfall/water balance edge cases.
- Efficiency validation (must be >0 and <=1).
- mm × m² to m³ conversion.
- Missing inputs → insufficient data.
- Conflicting evidence → review/uncertainty state.
- Reproducibility with fixed input and method version.

### Evaluation plan

- Compare crop parameters and water calculation with agronomist-reviewed examples.
- Compare any soil moisture estimate with field sensor data when available; do not validate against itself.
- Validate vegetation trend against screened imagery and known field observations.
- If ML model is introduced, separate train/validation/test by time and/or farm to avoid leakage; report metrics and dataset limitations.
- Do not publish accuracy claims without sample counts, labels, split method and baseline.

## 10. Outputs

The intelligence engine should expose a service-level result that Chaitanya can persist and publish using the API contract. It should not own database migrations or FastAPI route definitions.
