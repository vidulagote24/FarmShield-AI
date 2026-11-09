# FarmShield AI — Backend Foundation, Geospatial Services & Security Architecture (Part 3)

Welcome to the **FarmShield AI** backend service, an AI-powered precision agriculture, geospatial farm management, and agronomic risk intelligence platform.

This production-grade backend is built with **Python 3.13 / 3.12**, **FastAPI**, **PostgreSQL 16**, **PostGIS 3.4**, **SQLAlchemy 2.x**, **GeoAlchemy2**, **Pydantic v2**, **Argon2id (RFC 9106)**, and **PyJWT (RFC 7519)**.

---

## 1. System Architecture Overview

The backend uses a modular, domain-driven structure optimized for scalable geospatial computation, multi-tenant farmer isolation, IoT sensor monitoring, and machine-learning advisory ingestion:

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI initialization, lifespan & CORS
│   ├── cli.py                   # Administrative user provisioning CLI
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py              # DB session, JWT Bearer validation & ownership guards
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py        # Central API v1 router mounting all domain routers
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── health.py    # Health check & PostGIS diagnostics
│   │           ├── auth.py      # Registration, login, /me identity, logout
│   │           ├── users.py     # Farmer profiles & account management (self/admin)
│   │           ├── farms.py     # Farms & nested sub-resources with ownership protection
│   │           ├── zones.py     # Farm management zones CRUD with parent farm checks
│   │           ├── observations.py   # IoT sensor, weather, and satellite observations
│   │           ├── recommendations.py# Agronomic advisories & lifecycle state engine
│   │           └── irrigation.py     # Irrigation event logging and history
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Pydantic-settings configuration & .env loader
│   │   ├── security.py          # Argon2id hashing, PBKDF2 migration, JWT claims
│   │   ├── spatial.py           # Geodesic area, GeoJSON validation & containment
│   │   ├── exceptions.py        # Custom exceptions and RFC-compliant error handlers
│   │   └── logging.py           # Structured logging with credential redaction
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py              # DeclarativeBase with GeoAlchemy2 spatial types
│   │   └── session.py           # Engine & SessionLocal using psycopg 3
│   ├── models/
│   │   ├── __init__.py          # Model registry for Base.metadata
│   │   ├── user.py              # User & FarmerProfile models
│   │   ├── farm.py              # Farm (MultiPolygon) & FarmZone (Polygon)
│   │   ├── observation.py       # Sensor/Satellite observations (JSONB)
│   │   ├── recommendation.py    # Advisory recommendations (JSONB)
│   │   └── irrigation.py        # Irrigation events
│   ├── schemas/
│   │   ├── __init__.py          # Pydantic schema exports
│   │   ├── common.py            # BaseSchema and PaginatedResponse[T]
│   │   ├── auth.py              # UserRegisterRequest, LoginRequest, TokenResponse
│   │   ├── user.py              # User & FarmerProfile schemas
│   │   ├── farm.py              # Farm, FarmBoundary & FarmZone schemas
│   │   ├── observation.py       # Observation schemas & type validation
│   │   ├── recommendation.py    # Recommendation & status update schemas
│   │   └── irrigation.py        # Irrigation event schemas
│   ├── services/
│   │   ├── __init__.py          # Service layer registry
│   │   ├── user_service.py      # User management & profile business logic
│   │   ├── farm_service.py      # Farm spatial boundaries & geodesic area calculation
│   │   ├── zone_service.py      # Zone containment checks & code uniqueness
│   │   ├── observation_service.py # Observation filtering & cross-farm checks
│   │   ├── recommendation_service.py # Advisory lifecycle management
│   │   └── irrigation_service.py # Irrigation event tracking
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py          # Pytest fixtures, TestClient & DB cleanup
│       ├── test_config.py       # Configuration and CORS parsing tests
│       ├── test_health.py       # Health check & PostGIS diagnostics tests
│       ├── test_auth_api.py     # Registration, login, legacy migration, logout tests
│       ├── test_jwt_security.py # Cryptographic signature, expiry & malformed token tests
│       ├── test_authorization_ownership.py # Multi-tenant farmer isolation & admin access tests
│       ├── test_cli_admin.py    # Admin provisioning CLI tests
│       ├── test_auth_guard.py   # Fail-closed authentication & override tests
│       ├── test_users_api.py    # User & FarmerProfile CRUD tests
│       ├── test_farms_spatial_api.py # Spatial validation, geodesic area & farm CRUD
│       ├── test_zones_api.py    # Zone containment & code conflict tests
│       ├── test_observations_api.py # Observation CRUD & cross-farm mismatch tests
│       ├── test_recommendations_api.py # Recommendation filtering & status update tests
│       └── test_irrigation_api.py # Irrigation tracking & deletion tests
├── docker/
│   └── init-postgis.sql         # Automatic PostGIS extension bootstrap
├── migrations/
│   ├── versions/
│   │   └── 8c02fcee9d21_create_farmshield_core_tables.py # Initial core schema
│   ├── env.py                   # Alembic environment with PostGIS schema filtering
│   └── script.py.mako           # Migration template
├── alembic.ini                  # Alembic CLI configuration
├── docker-compose.yml           # Local PostgreSQL 16 + PostGIS container
├── Dockerfile                   # Production-ready Python 3.12 container
├── requirements.txt             # Locked Python dependencies
├── .env.example                 # Environment variable template
└── README.md                    # Backend setup and developer guide
```

---

## 2. Authentication, Authorization & Security Architecture

### A. Password Security with Argon2id
- **Algorithm**: Argon2id (`Type.ID`, RFC 9106), the OWASP gold standard for password hashing.
- **Parameters**: `time_cost=3`, `memory_cost=65536` (64 MB), `parallelism=4`, `salt_length=16`, `hash_length=32`.
- **Complexity Validation**: Enforced via regex prior to hashing:
  - Minimum 8 characters, maximum 128 characters.
  - At least one letter (`a-z` or `A-Z`).
  - At least one digit (`0-9`) or special character.
- **Backward Compatibility & Transparent Migration**: Legacy `pbkdf2_sha256$` hashes are verified seamlessly on login and automatically upgraded in-place to Argon2id without disrupting user sessions or resetting passwords.
- **Credential Hygiene**: Password hashes are never returned in API payloads (`hashed_password` excluded from all schemas) and are never logged.

### B. JWT Token Specification (RFC 7519)
JWT access tokens are cryptographically signed using HMAC-SHA256 (`HS256`) and include the following validated claims:

| Claim | Key | Description | Example |
|---|---|---|---|
| Subject | `sub` | Primary Key UUID of the user | `"5bfb0edd-8d25-40bf-907d-f279242a950b"` |
| Role | `role` | User role (`"farmer"` or `"admin"`) | `"farmer"` |
| Token Type | `type` | Token category | `"access"` |
| Email | `email` | User's registered email | `"ramesh@farmshield.ai"` |
| Issuer | `iss` | Originating identity authority | `"farmshield-ai"` |
| Audience | `aud` | Intended client application | `"farmshield-app"` |
| Issued At | `iat` | Epoch seconds when issued | `1731144000` |
| Not Before | `nbf` | Token not valid before this time | `1731144000` |
| Expiration | `exp` | Epoch seconds when expired | `1731230400` |

### C. Multi-Tenant Farm Ownership Protection
Every farm-scoped resource (farms, zones, observations, recommendations, irrigation events) is protected by the `check_farm_ownership` authorization guard:
1. **Farmer Scoping**: A farmer can **only** view, create, edit, or delete resources belonging to farms where `farm.owner_id == current_user.id`.
2. **Strict Isolation**: When listing farms (`GET /farms`), farmers automatically receive only their owned farms. Attempting to filter by another farmer's `owner_id` returns `HTTP 403 Forbidden`.
3. **Cross-Tenant Attack Rejection**: An authenticated farmer attempting to query or modify another farmer's farm, zone, observation, recommendation, irrigation event, or user profile receives an immediate `HTTP 403 Forbidden`.
4. **Admin Access**: Users with `role == "admin"` are authorized to inspect and manage resources across all tenants for auditing and agricultural extension support.

### D. Privilege Escalation Prevention
Public registration (`POST /api/v1/auth/register`) strictly forces `role = "farmer"`. Any client payload attempting to specify `role = "admin"` is ignored/rejected, preventing unauthorized privilege escalation.

### E. Administrative User Provisioning CLI
Administrative accounts cannot be registered publicly. They must be provisioned via the secure CLI:

```powershell
# From the backend root:
cd backend
..\.venv\Scripts\python.exe -m app.cli create-admin --email "admin@farmshield.ai" --name "Lead Agronomist" --password "StrongAdminPass123!" --phone "+919876543210"
```

---

## 3. Mobile & Frontend Integration Guide

This guide describes how React Native, Flutter, and web frontend applications interact with the FarmShield AI authentication layer.

### A. Authentication Flow Diagram

```
+---------------+           +-----------------------------+          +------------------------+
| Mobile / Web  |           |     FarmShield AI API       |          |  PostgreSQL / PostGIS  |
+---------------+           +-----------------------------+          +------------------------+
        |                                  |                                      |
        | 1. POST /api/v1/auth/register    |                                      |
        |--------------------------------->| Validate complexity & email          |
        |                                  | Hash password (Argon2id)             |
        |                                  | Create User & FarmerProfile -------->|
        | 2. 201 Created (UserResponse)    |                                      |
        |<---------------------------------|                                      |
        |                                  |                                      |
        | 3. POST /api/v1/auth/login       |                                      |
        |--------------------------------->| Verify Argon2id (or PBKDF2)          |
        |                                  | Rehash if legacy PBKDF2 ------------>|
        |                                  | Sign JWT access token                |
        | 4. 200 OK (access_token, user)   |                                      |
        |<---------------------------------|                                      |
        |                                  |                                      |
        | [Store JWT in SecureStorage]     |                                      |
        |                                  |                                      |
        | 5. GET /api/v1/farms             |                                      |
        |    Header: Bearer <token>        |                                      |
        |--------------------------------->| Decode & verify JWT (exp, iss, aud)  |
        |                                  | Filter farms by current_user.id ---->|
        | 6. 200 OK (Farmer's Farms)       |                                      |
        |<---------------------------------|                                      |
        |                                  |                                      |
        | 7. POST /api/v1/auth/logout      |                                      |
        |--------------------------------->| Return 200 confirmation              |
        | 8. [Delete token from device]    |                                      |
        v                                  v                                      v
```

### B. Example Requests & Responses

#### 1. Public Farmer Registration
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Ramesh Patil",
    "email": "ramesh@farmshield.ai",
    "password": "SecurePassword123!",
    "phone": "+919876543210",
    "preferred_language": "mr",
    "village": "Baramati",
    "district": "Pune",
    "state": "Maharashtra",
    "country": "India"
  }'
```
**Response (`201 Created`):**
```json
{
  "id": "5bfb0edd-8d25-40bf-907d-f279242a950b",
  "full_name": "Ramesh Patil",
  "email": "ramesh@farmshield.ai",
  "phone": "+919876543210",
  "role": "farmer",
  "is_active": true,
  "created_at": "2026-11-09T09:30:00Z",
  "updated_at": "2026-11-09T09:30:00Z"
}
```

#### 2. Farmer Login (JSON Payload)
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "ramesh@farmshield.ai",
    "password": "SecurePassword123!"
  }'
```
**Response (`200 OK`):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "5bfb0edd-8d25-40bf-907d-f279242a950b",
    "full_name": "Ramesh Patil",
    "email": "ramesh@farmshield.ai",
    "phone": "+919876543210",
    "role": "farmer",
    "is_active": true,
    "created_at": "2026-11-09T09:30:00Z",
    "updated_at": "2026-11-09T09:30:00Z"
  }
}
```

#### 3. Retrieve Authenticated Identity (`/auth/me`)
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 4. Accessing Protected Endpoints (e.g. List Farms)
All protected endpoints require the `Authorization` header with the Bearer prefix:
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/farms" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### 5. Interactive Swagger UI Authorization
1. Open `http://127.0.0.1:8000/docs` in your browser.
2. Click the green **Authorize** (lock icon) button in the top right.
3. In the OAuth2 modal, enter your farmer email into the **username** field and your password into the **password** field.
4. Click **Authorize**. Swagger UI will call `/api/v1/auth/login` and automatically attach the returned Bearer token to all subsequent interactive requests.

---

## 4. AI & Machine Learning Recommendation Ingestion Flow

FarmShield AI provides automated advisory and agronomic recommendation ingestion for satellite analytics providers, weather forecasting engines, and ML models.

### Recommendation Workflow

```
+-----------------------------------+
| Satellite / Weather / ML Engines  |
+-----------------------------------+
                  |
                  | 1. POST /api/v1/farms/{farm_id}/recommendations
                  |    or POST /api/v1/recommendations
                  |    Header: Bearer <service_token>
                  v
+-----------------------------------+
|      FarmShield AI Backend        |
|  Status: "pending"                |
+-----------------------------------+
                  |
                  | 2. Mobile notification sent to farmer
                  v
+-----------------------------------+
|       Farmer Mobile App           |
|  Farmer reviews AI recommendation |
+-----------------------------------+
                  |
                  | 3. PATCH /api/v1/recommendations/{id}/status
                  |    Body: {"status": "applied"} or {"status": "dismissed"}
                  v
+-----------------------------------+
|   Advisory Lifecycle Updated      |
|   (pending -> applied/dismissed)  |
+-----------------------------------+
```

### Recommendation JSON Schema

```json
{
  "farm_id": "YOUR_FARM_UUID",
  "zone_id": "OPTIONAL_ZONE_UUID",
  "recommendation_type": "irrigation",
  "title": "Irrigate Zone A with 25mm water",
  "description": "Satellite Sentinel-2 NDWI indicates root-zone moisture deficit.",
  "priority": "high",
  "status": "pending",
  "reasoning": {
    "model_name": "crop_water_stress_v2",
    "ndwi_value": -0.15,
    "soil_moisture_percentage": 28.2,
    "threshold_percentage": 35.0,
    "forecast_rain_next_48h_mm": 0.0
  },
  "recommended_action": {
    "action_type": "irrigate",
    "quantity_mm": 25.0,
    "recommended_time": "early_morning",
    "method": "drip"
  },
  "valid_until": "2026-11-11T12:00:00Z"
}
```

---

## 5. REST API Endpoint Reference

| Method | Path | Summary | Auth & Scoping |
|---|---|---|---|
| `POST`| `/api/v1/auth/register` | Register a new farmer account | Public (enforces role="farmer") |
| `POST`| `/api/v1/auth/login` | Authenticate user & issue JWT | Public (JSON or OAuth2 form) |
| `GET` | `/api/v1/auth/me` | Current authenticated profile | Bearer Token |
| `POST`| `/api/v1/auth/logout` | Client token logout confirmation | Bearer Token / Public |
| `GET` | `/health` | Top-level orchestrator health check | Public |
| `GET` | `/api/v1/health` | Deep health check (DB & PostGIS) | Public |
| `GET` | `/api/v1/users/me` | Retrieve active user profile | Bearer Token |
| `GET` | `/api/v1/users/{id}` | Retrieve user by UUID | Self or Admin |
| `PUT` | `/api/v1/users/{id}` | Update user details | Self or Admin |
| `GET` | `/api/v1/farmers/{user_id}/profile` | Retrieve farmer geographic profile | Self or Admin |
| `PUT` | `/api/v1/farmers/{user_id}/profile` | Create or update farmer profile | Self or Admin |
| `POST`| `/api/v1/farms` | Create a farm (assigns owner_id) | Farmer / Admin |
| `GET` | `/api/v1/farms` | List farms (scoped to current farmer) | Farmer / Admin |
| `GET` | `/api/v1/farms/{id}` | Get farm details | Farm Owner / Admin |
| `PUT` | `/api/v1/farms/{id}` | Update farm descriptive details | Farm Owner / Admin |
| `DELETE`| `/api/v1/farms/{id}`| Delete farm and dependent zones | Farm Owner / Admin |
| `GET` | `/api/v1/farms/{id}/boundary` | Get GeoJSON boundary & geodesic ha | Farm Owner / Admin |
| `PUT` | `/api/v1/farms/{id}/boundary` | Update spatial boundary (containment) | Farm Owner / Admin |
| `POST`| `/api/v1/farms/{id}/zones` | Create zone within farm | Farm Owner / Admin |
| `GET` | `/api/v1/farms/{id}/zones` | List zones within farm | Farm Owner / Admin |
| `GET` | `/api/v1/zones/{id}` | Get individual zone details | Farm Owner / Admin |
| `PUT` | `/api/v1/zones/{id}` | Update zone boundary or metadata | Farm Owner / Admin |
| `DELETE`| `/api/v1/zones/{id}`| Remove zone from farm | Farm Owner / Admin |
| `POST`| `/api/v1/farms/{id}/observations` | Record observation for farm | Farm Owner / Admin |
| `GET` | `/api/v1/farms/{id}/observations` | List observations with filters | Farm Owner / Admin |
| `GET` | `/api/v1/observations/{id}` | Get observation by UUID | Farm Owner / Admin |
| `DELETE`| `/api/v1/observations/{id}`| Delete observation | Farm Owner / Admin |
| `POST`| `/api/v1/farms/{id}/recommendations` | Create advisory recommendation | Farm Owner / Admin |
| `GET` | `/api/v1/farms/{id}/recommendations` | List recommendations with filters | Farm Owner / Admin |
| `GET` | `/api/v1/recommendations/{id}` | Get recommendation by UUID | Farm Owner / Admin |
| `PATCH`| `/api/v1/recommendations/{id}/status` | Update recommendation lifecycle | Farm Owner / Admin |
| `POST`| `/api/v1/farms/{id}/irrigation-events`| Record an irrigation event | Farm Owner / Admin |
| `GET` | `/api/v1/farms/{id}/irrigation-events` | Query irrigation history | Farm Owner / Admin |
| `GET` | `/api/v1/irrigation/{id}` | Get irrigation event by UUID | Farm Owner / Admin |
| `PUT` | `/api/v1/irrigation/{id}` | Update irrigation event | Farm Owner / Admin |
| `DELETE`| `/api/v1/irrigation/{id}`| Delete irrigation event | Farm Owner / Admin |

---

## 6. Testing & Quality Verification

Run the comprehensive automated test suite against the PostgreSQL + PostGIS instance:

```powershell
# Run the complete test suite (61 tests):
.venv\Scripts\pytest.exe backend/app/tests -v

# Run authentication and security tests:
.venv\Scripts\pytest.exe backend/app/tests/test_auth_api.py -v
.venv\Scripts\pytest.exe backend/app/tests/test_jwt_security.py -v
.venv\Scripts\pytest.exe backend/app/tests/test_authorization_ownership.py -v
.venv\Scripts\pytest.exe backend/app/tests/test_cli_admin.py -v
```

### Complete Test Breakdown:
- **Health Check & Diagnostics** (`test_health.py`): 4 tests
- **Configuration & CORS Parsing** (`test_config.py`): 3 tests
- **Fail-Closed Auth Guards** (`test_auth_guard.py`): 2 tests
- **Authentication Endpoints** (`test_auth_api.py`): 13 tests
  - Registration, password complexity validation, role escalation prevention, conflict handling, JSON login, OAuth2 form login, inactive account rejection, legacy PBKDF2 verification & transparent Argon2id rehash, `/auth/me`, logout.
- **JWT Cryptographic Security** (`test_jwt_security.py`): 6 tests
  - Expired token, signature forgery, invalid issuer, invalid audience, malformed string, non-existent user.
- **Resource Ownership & Multi-Tenant Isolation** (`test_authorization_ownership.py`): 5 tests
  - Farm isolation, farm listing isolation, zone isolation, observations/recommendations/irrigation isolation, user profile protection, admin multi-tenant access.
- **Admin CLI Provisioning** (`test_cli_admin.py`): 1 test
- **User & Farmer Profile CRUD** (`test_users_api.py`): 6 tests
- **Spatial Boundaries & Geodesic Area** (`test_farms_spatial_api.py`): 7 tests
- **Farm Management Zones** (`test_zones_api.py`): 4 tests
- **Observations API** (`test_observations_api.py`): 4 tests
- **Recommendations API** (`test_recommendations_api.py`): 3 tests
- **Irrigation Tracking API** (`test_irrigation_api.py`): 3 tests
- **Total Passing Tests**: **61 passed**
