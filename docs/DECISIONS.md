# Architecture Decision Log (ADL)

This file records accepted decisions. Update it when a decision changes; do not silently replace prior choices.

## ADL-001 — Use a single monorepo

- **Status:** Accepted
- **Decision:** One GitHub repository, `farmshield-ai`, contains frontend, backend, data tooling, infrastructure and docs.
- **Reason:** The five members need shared contracts and frequent integration; separate repositories add avoidable coordination overhead.
- **Consequences:** Clear module ownership and branch protection are mandatory.

## ADL-002 — Mobile-first responsive web application/PWA

- **Status:** Accepted for MVP
- **Decision:** Build a responsive React application, optimize the farmer flow for mobile and add PWA installability/selected offline behaviour.
- **Reason:** Farmers may rely on smartphones and not own laptops; a shared codebase allows the team to deliver a usable mobile experience quickly.
- **Consequences:** Test real mobile viewport, touch targets, poor connectivity and Devanagari font rendering. Native Android packaging is deferred.

## ADL-003 — Farmer-first combined experience

- **Status:** Accepted
- **Decision:** One application with a simple default farmer experience and expandable Advanced Analysis for agronomists.
- **Reason:** Avoid maintaining separate dashboards while preserving technical depth.
- **Consequences:** Every screen has summary and detail levels; role permissions may be added without duplicating the app.

## ADL-004 — English and Marathi first; Hindi-ready

- **Status:** Accepted
- **Decision:** Use i18next and translation namespaces. Complete English and Marathi for the first usable release; maintain Hindi locale from the beginning.
- **Reason:** Multilingual usability is core to the intended farmer audience.
- **Consequences:** No hardcoded visible copy; test long translated strings and units.

## ADL-005 — Modular monolith backend

- **Status:** Accepted
- **Decision:** FastAPI application with modular service boundaries, not microservices.
- **Reason:** Appropriate complexity for a hackathon prototype and a five-person team.
- **Consequences:** Keep ingestion, API, persistence and intelligence separated by packages.

## ADL-006 — PostgreSQL + PostGIS

- **Status:** Accepted
- **Decision:** Use PostgreSQL for relational records and PostGIS for farm/zone geometry and spatial queries.
- **Reason:** Farm boundaries, zones and observations are inherently spatial; a single database reduces operational complexity.
- **Consequences:** Geometry validity, SRID, spatial indexes and migrations must be tested.

## ADL-007 — Hybrid agronomic decision engine

- **Status:** Accepted
- **Decision:** Use documented agronomic calculations and deterministic validation rules as the foundation; use ML only when suitable labelled data and evaluation exist.
- **Reason:** Water recommendations need scientific constraints and explainable inputs; a model with arbitrary synthetic labels is not credible.
- **Consequences:** Every recommendation records calculation version, inputs, assumptions, evidence and data sufficiency.

## ADL-008 — Sensor-optional, provenance-aware data

- **Status:** Accepted
- **Decision:** Core experience can operate with satellite, weather, crop and soil-property information, while actual field sensors are optional. Every value is labelled by provenance.
- **Reason:** Avoid making physical hardware a prerequisite, but do not misrepresent coarse/modelled data as local measurement.
- **Consequences:** Insufficient-data state is a valid output; no fabricated root-zone moisture.

## ADL-009 — REST API versioning

- **Status:** Accepted
- **Decision:** Frontend/backend communication uses typed REST APIs under `/api/v1`.
- **Reason:** Allows parallel frontend/backend development and stable mock contracts.
- **Consequences:** API changes require a contract update, compatibility review and tests.

## ADL-010 — Defer distributed infrastructure

- **Status:** Accepted for MVP
- **Decision:** Do not add Redis, Celery, microservices or a vector database until a demonstrated need exists.
- **Reason:** They do not prove the central FarmShield value and increase setup/integration burden.
- **Consequences:** Use a simple repeatable analysis-run mechanism first; revisit durable job processing if runtime requires it.

## ADL-011 — Recommendation is advisory

- **Status:** Accepted
- **Decision:** MVP displays recommendations and records farmer actions; it does not control irrigation equipment.
- **Reason:** Hardware control introduces safety, connectivity and liability concerns beyond the first prototype.
- **Consequences:** Use clear advisory wording; never imply the pump was controlled automatically.

## Open decisions

- **ADL-TBD-01:** Production authentication provider and user sign-in method.
- **ADL-TBD-02:** Selected demonstration farm, crop, boundary and validated crop calendar.
- **ADL-TBD-03:** Whether field soil-moisture sensor data is available.
- **ADL-TBD-04:** Earth Engine access mode, quota and project registration.
- **ADL-TBD-05:** Hosting and object-storage provider.
- **ADL-TBD-06:** Whether Hindi translations are complete in the first demo.
- **ADL-TBD-07:** Durable job queue if actual satellite processing requires it.
