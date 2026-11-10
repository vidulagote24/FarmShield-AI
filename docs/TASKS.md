# Work Breakdown and Task Board

**Team:** PentaPrime  
**Rule:** Each task has one directly responsible owner. Contributors may review, but ownership remains explicit.

Status vocabulary: `TODO`, `IN_PROGRESS`, `BLOCKED`, `IN_REVIEW`, `DONE`.

## Milestone 0 — Foundation and contracts

| ID | Task | Owner | Output | Dependency |
|---|---|---|---|---|
| FND-01 | Create monorepo and target folders | Chaitanya | Repository skeleton | None |
| FND-02 | Add README and AI agent rules | Bhavikesh | Root documentation | Product baseline |
| FND-03 | Finalize mobile design tokens and component rules | Disha | `DESIGN.md`, token definitions | Product baseline |
| FND-04 | Review screen inventory and interaction flows | Vidula | Screen flow review | DESIGN.md |
| FND-05 | Confirm provider access, dataset feasibility and terms | Harshal | `DATA_SOURCES.md` updates | Demo location/crop TBD |
| FND-06 | Agree core entities and API contracts | Chaitanya | `DATA_MODEL.md`, `API_CONTRACTS.md` | Architecture draft |
| FND-07 | Agree normalized observation and intelligence service contracts | Harshal + Bhavikesh | Shared schemas/spec | DATA_MODEL draft |
| FND-08 | Protect main, add PR template and CI skeleton | Harshal | GitHub settings/workflow | Repo skeleton |

## Milestone 1 — Independent implementation

### Disha — UI foundation

| ID | Task | Output / acceptance |
|---|---|---|
| DIS-01 | App shell and routing | Mobile navigation and responsive shell work |
| DIS-02 | Design tokens and common components | Tokens, buttons, cards, badges, inputs, skeletons |
| DIS-03 | i18n framework | English/Marathi complete for owned screens; Hindi namespace ready |
| DIS-04 | Splash/language selection | Language persists and applies |
| DIS-05 | Farm setup screens | Form validation and API/mock integration |
| DIS-06 | Dashboard | Summary, zone map preview, priority actions and data freshness |

### Vidula — feature screens

| ID | Task | Output / acceptance |
|---|---|---|
| VID-01 | Farm digital twin screen | GeoJSON zones, layer switcher, legend and zone selection |
| VID-02 | Zone detail screen | Summary/evidence/advanced tabs or sections |
| VID-03 | Irrigation planner | Zone priorities and schedule from API contract |
| VID-04 | Recommendation details | Action, amount if valid, evidence, assumptions and record action |
| VID-05 | Insights | Crop/weather/water trend views with data provenance |
| VID-06 | Alerts and history | Alert list, irrigation events and analysis history |
| VID-07 | Profile/settings/language | Farm preferences and language selection |
| VID-08 | Mobile UI quality pass | Responsive, accessible, loading/error/offline states |

### Chaitanya — backend/database

| ID | Task | Output / acceptance |
|---|---|---|
| CHA-01 | FastAPI application foundation | Health endpoint and OpenAPI docs |
| CHA-02 | PostgreSQL/PostGIS setup | Repeatable local database |
| CHA-03 | SQLAlchemy models and migrations | Core entities from DATA_MODEL.md |
| CHA-04 | Farm APIs | Create/list/get/update and boundary validation |
| CHA-05 | Zone APIs | Create/list/get GeoJSON and containment checks |
| CHA-06 | Observation APIs | Persist/list provenance-aware observations |
| CHA-07 | Dashboard/analysis APIs | Stable contracts for frontend |
| CHA-08 | Recommendation/action/history APIs | Persist and retrieve decisions/events |
| CHA-09 | Authorization foundation | Farm membership enforced; auth choice documented |

### Harshal — data/infrastructure

| ID | Task | Output / acceptance |
|---|---|---|
| HAR-01 | Provider feasibility and access setup | Working access path or documented fallback |
| HAR-02 | Open-Meteo adapter | Normalized historical/forecast variables |
| HAR-03 | Sentinel-2 acquisition adapter | Scene metadata and usable surface reflectance |
| HAR-04 | Cloud/quality preprocessing | Mask and valid-pixel metadata |
| HAR-05 | Observation normalizer | Canonical units, timestamps and provenance |
| HAR-06 | Data quality/freshness checks | Good/suspect/stale/missing states |
| HAR-07 | Docker development setup | Repeatable local services |
| HAR-08 | GitHub Actions CI | Frontend/backend checks run on PR |

### Bhavikesh — intelligence/integration

| ID | Task | Output / acceptance |
|---|---|---|
| BHA-01 | Define intelligence input/output schemas | Reviewed service contract |
| BHA-02 | NDVI and zone aggregation | Tested calculations and quality metadata |
| BHA-03 | Crop parameter configuration | Source/version for crop/stage Kc and rooting parameters |
| BHA-04 | ET₀/ETc water calculation | Units, assumptions and tests |
| BHA-05 | Root-zone water balance | Missing-input and uncertainty handling |
| BHA-06 | Zone stress assessment | Explicit evidence/rule configuration |
| BHA-07 | Recommendation decision engine | Deterministic action and reason codes |
| BHA-08 | Structured explanation service | Evidence-grounded summary; no invented values |
| BHA-09 | End-to-end integration coordination | Full demo flow and integration issues resolved |

## Milestone 2 — Integration

| ID | Task | Owner | Acceptance |
|---|---|---|---|
| INT-01 | Persist normalized provider observations | Harshal + Chaitanya | Observation query returns source/time/quality |
| INT-02 | Connect intelligence service to observations | Bhavikesh + Chaitanya | Analysis run consumes persisted inputs |
| INT-03 | Return zone GeoJSON and analysis | Chaitanya + Bhavikesh | API contracts match docs |
| INT-04 | Replace frontend mocks with APIs | Disha + Vidula | Screens use actual endpoints |
| INT-05 | End-to-end farm analysis | All; Bhavikesh coordinates | Farm → data → analysis → recommendation works |
| INT-06 | Irrigation action/history | Vidula + Chaitanya | Saved event appears in history |

## Milestone 3 — Hardening and demo

| ID | Task | Owner | Acceptance |
|---|---|---|---|
| QA-01 | Agronomy review of demo crop parameters | Bhavikesh + mentor | Inputs/assumptions reviewed |
| QA-02 | Data provenance/freshness review | Harshal | All values traceable |
| QA-03 | API and database test pass | Chaitanya | Tests and migrations pass |
| QA-04 | Mobile and localization test pass | Disha + Vidula | Main flow usable on phone |
| QA-05 | Missing/stale/offline scenarios | All module owners | Graceful and honest states |
| QA-06 | Reproducible seed/demo setup | Chaitanya + Harshal | No manual SQL edits during demo |
| QA-07 | Final demo rehearsal | All | Demo script runs end-to-end |

## Working agreement

- Tasks should be created as GitHub Issues using these IDs.
- A task is assigned to one person only.
- Dependencies must be linked in the issue.
- Update status in the issue/Project board, not by editing unrelated code.
- No task is `DONE` until its acceptance criteria and tests pass.
- Add due dates only after the competition deadline and team availability are confirmed.
