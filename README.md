# FarmShield AI

**AI-powered digital twin for climate-resilient farming**  
Team: **PentaPrime** · Competition: **IndraDhanu**

FarmShield AI is a mobile-first, sensor-optional farm decision-support application. It combines farm boundaries, crop details, satellite-derived vegetation observations, weather information and available soil evidence to maintain a zone-level representation of a farm. It then uses transparent agronomic calculations and validated decision rules to help a farmer understand **where to inspect, whether irrigation may be needed, and why**.

> Core promise: **Right water. Right zone. Right time.**

This repository is the implementation home for the first working prototype. Read `AGENTS.md` before asking an AI coding assistant to modify the codebase.

## Current product boundaries

The first prototype is deliberately narrower than the full vision in the submitted presentation:

- One registered demonstration farm, with support for multiple farms in the data model.
- Four to six explicitly defined management zones for the demonstration.
- A mobile-first responsive web application/PWA.
- English and Marathi first; Hindi is supported by the same translation structure and can be completed in the first release if translations are ready.
- Weather and at least one usable satellite observation source.
- Clear distinction between measured, modelled, satellite-derived, farmer-entered and assumed data.
- Zone-level condition assessment and an agronomically constrained irrigation decision.
- Explainable recommendations and recorded farmer actions.

The first prototype does **not** promise real-time satellite updates, exact field-level soil moisture from optical imagery, autonomous irrigation control, validated yield prediction, flood prediction or regional government analytics.

## Team ownership

| Member | Primary ownership |
|---|---|
| Disha Gudup | Design system, application shell, onboarding, dashboard and i18n foundation |
| Vidula Gote | Farm map, zones, irrigation, recommendation details, insights, alerts, history and settings screens |
| Chaitanya Hapse | FastAPI backend, database, models, schemas, migrations and REST API |
| Harshal Ramteke | External data ingestion, provider adapters, normalization, data quality, Docker and CI |
| Bhavikesh Hedau | Geospatial feature analysis, agronomy calculations, stress assessment, decision engine, explanations and technical integration |

Exact GitHub usernames must be added to `docs/TEAM_OWNERSHIP.md` and `CODEOWNERS` when confirmed. Do not invent usernames.

## Repository map

```text
farmshield-ai/
├── AGENTS.md
├── README.md
├── docs/                     # product and engineering specifications
├── frontend/                 # React + TypeScript + Vite PWA
├── backend/                  # FastAPI modular monolith
├── data/                     # metadata, small fixtures and manifests only
├── scripts/                  # reproducible local jobs and utilities
├── infra/                    # Docker and deployment configuration
└── .github/                  # CI and repository templates
```

The detailed target tree is in `docs/ARCHITECTURE.md`. Create directories when their module begins; empty folders are not deliverables.

## Planned technology baseline

- Frontend: React, TypeScript, Vite, Tailwind CSS, accessible shared components, React Leaflet/Leaflet, Chart.js, i18next and a PWA plugin.
- Backend: Python, FastAPI, Pydantic, SQLAlchemy and Alembic.
- Data: PostgreSQL + PostGIS.
- Geospatial processing: Google Earth Engine where appropriate, GeoPandas, Rasterio and Shapely.
- Weather: Open-Meteo adapter, subject to current terms, attribution and usage limits.
- Intelligence: NumPy/Pandas, transparent rules and FAO-56-based water-balance calculations; Scikit-learn/XGBoost only when suitable labelled data is available.
- Delivery: Docker Compose for local development and GitHub Actions for checks.

The exact dependency versions must be pinned in `package.json` and `pyproject.toml` when implementation starts. Do not add Redis, Celery, a vector database, microservices or an LLM dependency without an accepted decision in `docs/DECISIONS.md`.

## Local development (target workflow)

The commands below describe the intended setup once the corresponding manifests are committed. They are not evidence that the application is already implemented.

```bash
# Clone and enter the repository
git clone <REPOSITORY_URL>
cd farmshield-ai

# Copy local configuration; never commit real secrets
cp .env.example .env

# Start shared services and application containers
docker compose -f infra/docker-compose.yml up --build
```

If the team chooses separate local runs during early development:

```bash
# Frontend
cd frontend
npm install
npm run dev

# Backend, in another terminal
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

Use the platform-appropriate virtual-environment activation command on Windows. The final commands must be reconciled with actual manifests before being treated as release instructions.

## Required reading order

1. `AGENTS.md`
2. `docs/PRD.md`
3. `docs/MVP_SCOPE.md`
4. `docs/ARCHITECTURE.md`
5. The module-specific document relevant to your task
6. `docs/RULES.md` and `docs/TEAM_OWNERSHIP.md`

## Engineering principles

1. Evidence before recommendation.
2. Never confuse a satellite index or gridded model output with a field sensor measurement.
3. Do not output an irrigation quantity if required inputs are missing or unsuitable.
4. Every observation has a source, timestamp, unit and quality status.
5. UI screens consume versioned API contracts; frontend code must not reproduce agronomic logic.
6. Synthetic data is allowed for design and demos only when explicitly labelled as simulated.
7. One module owner, one contract, one pull request at a time.

## Reference material

- Submitted IndraDhanu presentation: problem framing, proposed solution, system architecture, differentiation and intended impact.
- FAO, *Crop Evapotranspiration: Guidelines for Computing Crop Water Requirements*, Irrigation and Drainage Paper 56: https://www.fao.org/4/X0490E/X0490E00.htm
- Sentinel-2 mission: https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-2
- Google Earth Engine access: https://developers.google.com/earth-engine/guides/access
- Sentinel-2 Harmonized Surface Reflectance collection: https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED
- Open-Meteo historical weather API: https://open-meteo.com/en/docs/historical-weather-api
- Open-Meteo historical forecast API: https://open-meteo.com/en/docs/historical-forecast-api
- PostGIS documentation: https://postgis.net/documentation/

Review source terms, attribution and access requirements before deployment. See `docs/DATA_SOURCES.md`.
