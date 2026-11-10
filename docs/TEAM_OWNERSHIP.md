# Team Ownership and Collaboration Contract

**Team:** PentaPrime

## 1. Members and module ownership

### Disha Gudup — UI/UX Lead and Frontend Foundation

Owns:
- `frontend/src/design-system/`
- `frontend/src/components/common/`
- `frontend/src/app/`
- `frontend/src/features/onboarding/`
- `frontend/src/features/dashboard/`
- `frontend/src/i18n/` configuration and common namespace framework
- `docs/DESIGN.md`

Deliverables: visual system, app shell, splash/language selection, farm setup, dashboard and shared components.

### Vidula Gote — Frontend Feature Developer

Owns:
- `frontend/src/features/farm-map/`
- `frontend/src/features/zones/`
- `frontend/src/features/irrigation/`
- `frontend/src/features/recommendations/`
- `frontend/src/features/insights/`
- `frontend/src/features/alerts/`
- `frontend/src/features/history/`
- `frontend/src/features/profile/`
- `frontend/src/features/settings/`

Deliverables: all remaining feature screens, interactions, API integration and UI edge states. Uses Disha's shared tokens/components; requests shared-component changes by PR.

### Chaitanya Hapse — Backend and Database Lead

Owns:
- `backend/app/api/`
- `backend/app/core/`
- `backend/app/db/`
- `backend/app/models/`
- `backend/app/schemas/`
- `backend/app/services/`
- `backend/migrations/`
- `docs/DATA_MODEL.md`
- `docs/API_CONTRACTS.md`

Deliverables: FastAPI API, Postgres/PostGIS models/migrations, farm/zone/observation/recommendation/event services, authorization checks and OpenAPI contracts.

### Harshal Ramteke — Data Engineering and Infrastructure Lead

Owns:
- `backend/app/ingestion/`
- `backend/app/data_quality/`
- `data/` manifests/fixtures coordination
- `scripts/` for ingestion jobs
- `infra/`
- `.github/workflows/`
- `docs/DATA_SOURCES.md`
- `docs/TESTING.md` coordination

Deliverables: weather/satellite adapters, normalization, data-quality rules, source provenance, Docker and CI.

### Bhavikesh Hedau — AI/Geospatial Lead and Technical Integrator

Owns:
- `backend/app/intelligence/`
- `docs/PRD.md`
- `docs/MVP_SCOPE.md`
- `docs/ARCHITECTURE.md`
- `docs/RULES.md`
- `docs/DECISIONS.md`
- `docs/AI_SPEC.md`
- `docs/TASKS.md`
- `docs/DEMO_SCRIPT.md`
- technical integration coordination

Deliverables: geospatial features, agronomic water calculations, zone stress assessment, decision engine, structured explanations, integration and prototype validation coordination.

## 2. Shared-file maintainers

| File/folder | Maintainer | Review required from |
|---|---|---|
| `frontend/package.json` | Disha | Vidula if feature dependency affects her module |
| `frontend/src/app/` | Disha | Vidula for navigation integration |
| `frontend/src/design-system/` | Disha | Vidula for reusable feature needs |
| `frontend/src/i18n/` | Disha | Vidula for feature translations |
| `backend/app/main.py` | Chaitanya | Harshal/Bhavikesh when wiring their services |
| `backend/app/models/` | Chaitanya | Harshal/Bhavikesh for data fields |
| `backend/app/schemas/` | Chaitanya | All consumers |
| `backend/pyproject.toml` | Chaitanya | Harshal/Bhavikesh for dependencies |
| `infra/` and CI | Harshal | Chaitanya for runtime/container needs |
| Intelligence service contract | Bhavikesh | Chaitanya and Harshal |
| API contract | Chaitanya | Disha, Vidula, Harshal and Bhavikesh |

## 3. Cross-module boundaries

- Harshal retrieves and normalizes source data; Bhavikesh interprets normalized evidence.
- Bhavikesh builds calculation/decision services; Chaitanya exposes/persists them through the API.
- Chaitanya owns database schema; all others request schema changes through an issue/PR.
- Disha owns shared UI tokens/components; Vidula builds feature screens on top of them.
- Vidula owns feature-screen interactions; she does not create a competing design system.
- Frontend consumes only documented API contracts; it does not call private data providers or calculate water balance.

## 4. GitHub identity placeholders

Add the actual GitHub usernames before creating `CODEOWNERS`:

| Member | GitHub username |
|---|---|
| Disha Gudup | TBD |
| Vidula Gote | TBD |
| Chaitanya Hapse | TBD |
| Harshal Ramteke | TBD |
| Bhavikesh Hedau | TBD |

Do not guess usernames or assign ownership to similarly named accounts.

## 5. Collaboration protocol

- Work through feature branches and PRs; no direct push to `main`.
- A feature has one owner and linked issue.
- Owners may ask another member for review or contribution, but ownership remains clear.
- Shared contracts are reviewed before implementation changes.
- Raise blockers early; do not silently build around a missing dependency.
- All members keep their own tests and update relevant docs.
- Bhavikesh coordinates technical integration but does not own all implementation work.
