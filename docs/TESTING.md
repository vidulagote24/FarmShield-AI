# Testing and Quality Strategy

**Coordinator:** Harshal Ramteke  
**Each module owner writes and maintains tests for their module.**

## 1. Quality goals

The prototype must be repeatable, traceable and safe when data is missing. Test the complete farmer journey as well as scientific calculations and provider failures.

## 2. Test layers

### Frontend unit/component tests

- Design-system components render across mobile widths.
- Farm selector switches active farm.
- Dashboard handles loaded, loading, empty, stale, partial, offline and error states.
- Zone map/list selects the correct zone.
- Recommendation detail renders units, evidence and assumptions.
- Translation switch changes all visible strings.
- Long Marathi/Hindi copy does not clip or overflow.
- Charts expose textual summaries.

Suggested tooling: Vitest and React Testing Library; Playwright for end-to-end tests.

### Backend unit tests

- Pydantic request validation.
- Geometry validation and area calculation.
- Farm/zone authorization checks.
- Service-level recommendation orchestration.
- Data freshness and provenance mapping.
- Error envelope and status codes.

Suggested tooling: pytest, httpx test client and test PostgreSQL/PostGIS where spatial behaviour is important.

### Intelligence tests

- NDVI formula, denominator zero and invalid pixel handling.
- Cloud masking and valid-pixel coverage threshold.
- Zone raster aggregation and geometry overlap.
- ET₀/Kc/ETc units and expected arithmetic.
- Effective rainfall and root-zone balance boundaries.
- Application efficiency range validation.
- mm × m² conversion to m³.
- Missing essential inputs produce `insufficient_data`.
- Conflicting/low-quality evidence triggers review or uncertainty.
- Same inputs + same version produce deterministic outputs.

### Ingestion tests

- Valid provider response normalization.
- Missing variable and unit conversion.
- Timezone parsing.
- Timeout, rate-limit and malformed response handling.
- Cloud/quality flags retained.
- Provider model/run/scene ID preserved.
- No zero substitution for missing values.

### Integration tests

- Create farm → define zones → fetch/attach observations → run analysis → persist assessment/recommendation → return dashboard → record irrigation event → retrieve history.
- Test partial data when one provider fails.
- Test all sources unavailable.
- Test unauthorized farm access.
- Test repeated ingestion does not create uncontrolled duplicates.

### End-to-end test

Use a documented demonstration farm and fixture/source data. Execute the full mobile journey from login/demo identity to irrigation action recording. The test must not require manual SQL edits during execution.

## 3. Data validation checks

- Coordinates within valid WGS84 ranges.
- Geometry valid and within farm boundary.
- Units recognized and converted consistently.
- Observation timestamp not silently treated as retrieval timestamp.
- Forecast valid time separate from forecast issue/retrieval time.
- Values outside expected physical range are quarantined or flagged.
- Raster pixel counts and valid coverage recorded.
- Source provenance present for every displayed analytical value.

## 4. UI acceptance and manual device checks

Test at representative narrow, medium and large mobile viewports. Check:

- one-hand reach for primary actions;
- text scaling;
- status labels without relying on colour alone;
- map zoom/pan and zone selection;
- keyboard overlap on forms;
- offline/stale banners;
- Marathi/Hindi line wrapping;
- minimum touch sizes;
- bottom navigation safe-area spacing.

## 5. CI pipeline

Recommended checks on each pull request:

Frontend:
- install locked dependencies;
- lint;
- TypeScript typecheck;
- unit/component tests;
- production build.

Backend:
- install locked dependencies;
- formatting/lint (tool chosen in `pyproject.toml`);
- type checking if configured;
- pytest;
- migration consistency check.

Optional integration job:
- start PostGIS service;
- run API integration tests.

## 6. Definition of test pass

A feature is not complete merely because a page loads. It must meet its acceptance criteria, cover failure/missing-data cases and pass relevant checks. Any test excluded from CI must be documented with a reason and manual execution instructions.

## 7. Validation claims

Do not report model accuracy, water saved, yield change or drought forecast skill without:
- defined target/label;
- source dataset and sample count;
- train/validation/test method where applicable;
- baseline comparison;
- metric definitions;
- limitations and confidence intervals where appropriate.
