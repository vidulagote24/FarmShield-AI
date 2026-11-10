# Engineering, Collaboration and Repository Rules

## 1. Team ownership

| Member | Owns |
|---|---|
| Disha | Design system, app shell, onboarding, dashboard, i18n foundation |
| Vidula | Farm map, zones, irrigation, recommendation, insights, alerts, history, profile/settings screens |
| Chaitanya | Backend API, database, models, schemas, migrations, backend services |
| Harshal | Data ingestion/providers/normalizers, data quality, Docker, CI |
| Bhavikesh | Geospatial features, agronomy, stress assessment, decision engine, explanations, technical integration |

Do not modify another member's module without agreement. Cross-module changes should be made through a reviewed pull request and recorded in the relevant spec.

## 2. Branch and merge rules

- `main` is protected; no direct pushes.
- Branch format: `feat/<member>/<feature>` or `fix/<member>/<issue>`.
- One logical feature per branch/pull request.
- PR must link a GitHub issue.
- Require at least one review by a relevant module owner.
- CI must pass before merge.
- Avoid large unrelated formatting changes.
- Rebase or merge current `main` before final review; resolve conflicts with the owner of the affected files.

## 3. Commit convention

Use Conventional Commit-style prefixes:

- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `test:` tests
- `refactor:` behaviour-preserving restructuring
- `chore:` tooling/build/dependency work
- `data:` fixtures or data manifests

Example: `feat(ai): add FAO-56 ETc calculation service`.

## 4. Code standards

### Frontend

- TypeScript strict mode.
- Reusable components and feature-based folders.
- API calls through shared typed client.
- Translation keys for all user-visible text.
- No hardcoded farm or recommendation data in production components.
- Components must handle loading/error/empty/stale states.
- Keep map interaction accessible and provide a list view alternative.

### Backend

- Python type hints.
- Pydantic at API and external-data boundaries.
- SQLAlchemy models and Alembic migrations.
- Thin routers; business logic in services.
- Explicit units in field names.
- UTC timestamps at API boundary.
- Stable enum values; do not store translated labels.

### Data and intelligence

- Every variable must have a definition, unit, source and provenance type.
- Retain source/provider, observed time, retrieval time, processing version and quality flag.
- Reject or quarantine invalid records; do not silently coerce invalid values to zero.
- All calculation functions must document inputs, units, equations and assumptions.
- Decision rules must be configurable and versioned.
- Synthetic demo data must be clearly marked.

## 5. API rules

- Prefix routes with `/api/v1`.
- Use plural resource names where appropriate.
- Return typed, documented response schemas.
- Return consistent error envelopes.
- Use pagination for collections that may grow.
- Use GeoJSON for farm/zone geometry.
- Use `null` for missing numeric observations, not zero.
- Distinguish observed, forecast, derived, modelled, user-entered and simulated values.
- Do not expose provider-specific raw payloads as the normal frontend contract; keep raw payload references for audit/debug.

## 6. Data and privacy rules

- No API keys, credentials, `.env` files or private datasets in Git.
- No identifiable farmer data in fixtures or screenshots.
- Do not commit large raw imagery; store externally and commit a manifest/metadata.
- Respect provider licence, terms, attribution, quota and access restrictions.
- Record dataset version/scene ID and processing version.

## 7. Testing rules

- New domain calculations require unit tests, including edge cases and unit checks.
- New API endpoints require success, validation, not-found and permission tests where applicable.
- New ingestion adapters require parser/normalizer tests using small fixtures and provider-failure tests.
- New UI features require component or interaction tests; critical flows require end-to-end coverage.
- A bug fix should include a regression test when practical.

## 8. Shared-file change procedure

For `package.json`, `pyproject.toml`, root configs, `main.py`, database schema, API contracts or design tokens:

1. Open an issue or explain the need in the PR.
2. Notify the designated file owner.
3. State compatibility impact.
4. Get owner review before merge.
5. Update relevant documentation and tests.

## 9. Definition of done

A task is done only when implementation, tests, error states, documentation and integration expectations are met. A page that only renders static content is not a completed data-driven feature unless explicitly labelled as a design prototype.
