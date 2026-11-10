# Product Requirements Document (PRD)

**Product:** FarmShield AI  
**Version:** 0.1 — MVP baseline  
**Team:** PentaPrime

## 1. Product summary

FarmShield AI is a mobile-first, sensor-optional agricultural decision-support platform. It creates a maintained digital representation of a farm from its boundary, crop details and available environmental observations. It evaluates conditions across management zones and helps farmers understand where to inspect and whether irrigation may be required.

The product's core loop is:

**Sense → Fuse → Assess/Predict → Validate → Explain → Act → Observe again**

The platform is advisory in the MVP. It does not directly control pumps or irrigation valves.

## 2. Problem statement

Agricultural water requirements vary with crop, growth stage, weather, soil and field conditions. A farm may not be spatially uniform: different parts of the same field can have different vegetation condition, soil properties, water availability or microclimate. A whole-farm or fixed-schedule decision can therefore miss local differences, potentially leading to unnecessary irrigation in some areas and insufficient water in others.

FarmShield addresses the gap between scattered observations and actionable, zone-level decisions. It combines available satellite, weather, soil and crop information, then uses agronomic calculations and explicit validation rules to produce recommendations with supporting evidence.

This is the product framing in the submitted IndraDhanu presentation. It is not a claim that every farmer currently uses fixed schedules or that all existing commercial tools lack integrated analytics.

## 3. Goals

### MVP goals

1. Allow a farmer to register/select a farm and provide crop context.
2. Store a farm boundary and four to six management zones for the demonstration.
3. Retrieve and normalize weather information and at least one usable satellite-derived observation.
4. Display the farm and zones on a mobile-friendly map.
5. Present vegetation and environmental evidence with source and observation time.
6. Calculate crop water demand and water balance where sufficient inputs exist.
7. Produce zone-level statuses and irrigation decision support.
8. Explain recommendations using traceable evidence and assumptions.
9. Record farmer-reported irrigation actions.
10. Support English and Marathi in the first usable release; keep Hindi in the same translation framework.

### Product quality goals

- Farmer can understand the primary dashboard and find priority zones without reading technical documentation.
- Technical information remains accessible to an agronomist through expanded analysis.
- Missing, stale, estimated and simulated data are clearly distinguished.
- The interface works on a typical smartphone viewport and adapts to desktop.
- Backend and intelligence logic are testable independently of the UI.

## 4. Personas

### Primary — Farmer / Farm Manager

Needs a simple view of farm condition, zones needing attention, irrigation guidance and an understandable reason. Likely to use a smartphone in the field, possibly with intermittent connectivity. The interface must not require knowledge of NDVI, SAR, ET₀ or model terminology.

### Secondary — Agronomist / Field Officer

Needs access to zone evidence, crop stage, source timestamps, indices, water-balance assumptions, historical observations and recommendation rationale. Uses the same application with Advanced Analysis expanded.

### Future — Administrator / Programme Manager

May need aggregated farm, cluster or district views for planning. This is explicitly outside the first prototype.

## 5. Main user journeys

### Journey A — First-time farm setup

1. Select language.
2. Create/select farmer profile.
3. Add farm name and location.
4. Draw or upload farm boundary.
5. Enter farm area (calculated from boundary where possible; user may confirm).
6. Add crop, sowing/planting date, growth stage and irrigation method.
7. Add known soil information; mark unknown fields rather than guessing.
8. Save farm and define/import management zones.
9. Run initial analysis when data is available.

### Journey B — Daily farm review

1. Open Home dashboard.
2. Check overall status and data freshness.
3. Identify zones marked attention/high stress/insufficient data.
4. Open a zone.
5. Review short recommendation and supporting evidence.
6. Expand Advanced Analysis if needed.
7. Decide and record an irrigation or inspection action.

### Journey C — Agronomist review

1. Select a farm and zone.
2. Inspect source observations, dates, data quality and indices.
3. Review crop-water calculation assumptions.
4. Review recommendation and uncertainty.
5. Record a note or provide an advisory action.

## 6. Product requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | User can create and view a farm | Must |
| FR-02 | Farm boundary is stored as valid geospatial geometry | Must |
| FR-03 | Farm has crop and growth-stage context | Must |
| FR-04 | Farm contains explicitly defined management zones | Must |
| FR-05 | System ingests weather observations/forecasts with provenance | Must |
| FR-06 | System stores satellite-derived vegetation observations with date and quality | Must |
| FR-07 | Dashboard shows farm status, data freshness and priority zones | Must |
| FR-08 | User can open zone details and see evidence | Must |
| FR-09 | Water-balance calculation uses documented agronomic inputs | Must |
| FR-10 | Decision engine can return insufficient-data state | Must |
| FR-11 | Recommendation includes reason codes and assumptions | Must |
| FR-12 | User can record irrigation action | Must |
| FR-13 | UI supports English and Marathi; Hindi uses same i18n framework | Must |
| FR-14 | Interface handles loading, errors, stale and offline states | Must |
| FR-15 | User can inspect historical analysis/action records | Should |
| FR-16 | User can add IoT sensor readings | Later |
| FR-17 | Automatic zone generation | Later |
| FR-18 | Regional admin analytics | Later |

## 7. Non-functional requirements

- **Mobile-first:** Design and test narrow phone viewports before desktop expansion.
- **Accessibility:** Aim for WCAG 2.2 AA contrast, scalable text, accessible controls and non-colour status labels.
- **Performance:** Avoid downloading full-resolution rasters to the phone; deliver zone summaries and appropriately rendered map layers.
- **Reliability:** Provider failures must not crash the dashboard; show last successful update and data availability.
- **Security:** Secrets remain server-side; enforce authorization for farm data; avoid personal data in logs.
- **Traceability:** Every observation and recommendation can be traced to inputs, timestamps, calculation version and source.
- **Maintainability:** Modular monolith with clear boundaries, versioned API and automated tests.

## 8. Product metrics to collect

Do not set outcome claims before measurement. The prototype should collect:

- Time to complete farm setup.
- Number of zones with sufficient versus insufficient evidence.
- Percentage of recommendations with complete provenance.
- Number of irrigation actions recorded.
- Agreement between calculated recommendation and agronomist review (after evaluation protocol exists).
- Water applied per area where actual irrigation quantities are recorded.
- Change in zone condition across comparable observations.

Water savings, yield improvement and model accuracy must be reported only after a defined field validation or reproducible evaluation. Dashboard counts alone are not impact evidence.

## 9. Assumptions and open questions

- Initial demo will use one selected farm and four to six management zones.
- Crop and location for the actual demo farm must be selected by the team.
- Farm boundary source (farmer-drawn, uploaded GeoJSON or approved sample geometry) is TBD.
- Crop calendar and locally appropriate Kc/root-depth values must be sourced and reviewed.
- The availability and legal/operational access to Earth Engine must be confirmed.
- Whether a real soil-moisture sensor is available is TBD. If unavailable, the UI must show estimates/unknowns honestly.
- Production-grade authentication is not part of the initial demo unless required by the competition; access control must still be considered in backend design.
