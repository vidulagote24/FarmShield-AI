# Instructions for AI Coding Agents

You are contributing to **FarmShield AI**, a five-person team project. Follow these instructions before editing any file.

## 1. Mandatory reading

Before making changes, read:

1. `README.md`
2. `docs/PRD.md`
3. `docs/MVP_SCOPE.md`
4. `docs/ARCHITECTURE.md`
5. `docs/RULES.md`
6. `docs/TEAM_OWNERSHIP.md`
7. The relevant module specification (`DESIGN.md`, `API_CONTRACTS.md`, `DATA_MODEL.md`, `AI_SPEC.md` or `DATA_SOURCES.md`).

Do not assume a feature exists merely because it appears in a proposed architecture or presentation.

## 2. Product truth

FarmShield is a **decision-support system**, not an autonomous irrigation controller. Its MVP combines farm and crop metadata with available satellite, weather and soil evidence to assess zones and support irrigation decisions.

Never:

- Claim real-time satellite monitoring.
- Treat NDVI/NDMI as a direct measurement of root-zone soil moisture.
- Present gridded/modelled soil moisture as a field sensor observation.
- Infer a precise irrigation volume when required crop, soil, root-zone, rainfall or efficiency inputs are absent.
- Claim measured water savings, yield improvement, model accuracy or drought probability without a defined experiment and supporting evidence.
- Let an LLM calculate water requirements or override deterministic validation rules.
- Present simulated data as live farm data.

## 3. Module ownership

- Disha: frontend design system, app shell, onboarding, dashboard and i18n foundation.
- Vidula: map, zone, irrigation, recommendation, insights, alerts, history and settings feature screens.
- Chaitanya: backend API, persistence, models, schemas, migrations and backend services.
- Harshal: data provider integrations, ingestion, normalization, data quality, Docker and CI.
- Bhavikesh: geospatial feature analysis, agronomic calculations, stress assessment, decision engine, explanations and technical integration.

Do not edit another member's owned module without coordinating with its owner and recording the agreed change in the pull request. Shared contracts may be changed only through a reviewed pull request.

## 4. Architecture boundaries

- Frontend communicates with the backend through versioned REST APIs under `/api/v1`.
- Frontend must not call external satellite/weather providers directly using secret credentials.
- Backend API routes validate inputs and call services; they must not contain duplicated domain calculations.
- Ingestion adapters retrieve and normalize source data; they must not implement crop-irrigation decisions.
- Intelligence services consume normalized observations and farm/crop/soil context; they must not retrieve provider data independently.
- Database models and migrations are owned by Chaitanya. Discuss required schema changes before implementing them in another module.
- Provider-specific code belongs under `backend/app/ingestion/providers/`.
- Agronomic and decision logic belongs under `backend/app/intelligence/`.
- UI presentation and translation belong under `frontend/src/`.

## 5. Contract-first work

Before implementing a cross-module feature:

1. Identify the API request/response contract in `docs/API_CONTRACTS.md`.
2. Identify the data model in `docs/DATA_MODEL.md`.
3. Identify required source fields and their provenance in `docs/DATA_SOURCES.md`.
4. Update the relevant spec through a reviewed change if the contract is incomplete.
5. Use mock fixtures that conform exactly to the contract while another module is in progress.

Do not invent response properties locally and later ask another member to support them.

## 6. Code quality

- Use TypeScript strict mode for frontend code.
- Use Python type hints and Pydantic validation for backend boundaries.
- Keep functions small and domain-focused.
- Avoid duplicate business logic.
- Use UTC timestamps in APIs; preserve source timezone metadata where relevant.
- Use explicit units in names and payloads, such as `rainfall_mm`, `et0_mm_day` and `area_ha`.
- Use stable enum values, not translated display labels, in stored data.
- Add tests for new calculations, API behaviour, parsing and edge cases.
- Never commit secrets, access tokens, personal farmer data or large raw satellite files.
- Keep small synthetic fixtures in `data/fixtures/` and label them as synthetic.

## 7. UI rules

- Design mobile-first and adapt to larger screens.
- Use shared tokens and components; do not invent a new palette for an individual page.
- Default farmer experience uses plain language. Technical indices and calculations belong in expandable Advanced Analysis sections.
- Include loading, empty, stale-data, partial-data, offline and error states.
- Every map layer must have a legend and observation timestamp.
- Colour must never be the only way to communicate risk; also show a text label/icon.
- English, Marathi and Hindi strings must use translation keys; do not hardcode user-facing copy in components.

## 8. Pull requests and Git

- Never push directly to `main`.
- Use a feature branch named `feat/<member>/<short-feature>` or `fix/<member>/<short-description>`.
- Keep pull requests focused and small enough to review.
- Include tests and screenshots for UI changes.
- Do not silently alter a shared API or database contract.
- Ensure CI passes before requesting merge.
- Do not merge failing or unreviewed work merely to make a demo appear complete.

## 9. When information is missing

Do not guess. Mark the item as `TBD`, return a validation error, set a value to `null`, or return `insufficient_data` according to the relevant contract. Ask the module owner for clarification when the missing information affects a shared interface or scientific validity.

## 10. Completion checklist

A task is complete only when:

- The implementation matches the relevant spec.
- Inputs and outputs are validated.
- Appropriate unit/integration tests are added.
- Error and missing-data behaviour is handled.
- Documentation is updated if the contract or behaviour changed.
- The owner can demonstrate the feature independently.
