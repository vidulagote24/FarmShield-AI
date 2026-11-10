# FarmShield AI — Frontend Integration Checklist & API Contracts

**Target Audience:** Frontend Feature Lead (**Vidula Gote**)  
**Prepared By:** AI / Geospatial Lead (**Bhavikesh Hedau**)  
**Status:** Verified Working Baseline on `integration/current-system`

This document details all live, verified `/api/v1` backend endpoints, authentication flows, response schemas, and multilingual intelligence integration contracts. Use these exact field names and structures when implementing the feature screens.

---

## 1. Authentication & Session Management

All non-public endpoints require a valid JWT Bearer access token in the `Authorization` header:
```http
Authorization: Bearer <access_token>
```

### Endpoints
- `POST /api/v1/auth/register` (Farmer registration)
- `POST /api/v1/auth/login` (Farmer / admin authentication)
- `GET /api/v1/auth/me` (Current user profile)
- `POST /api/v1/auth/logout` (Stateless token removal)

### Login Payload & Response
**Request (`POST /api/v1/auth/login`):**
```json
{
  "email": "farmer@farmshield.ai",
  "password": "StrongPassword123!"
}
```

**Response (`200 OK`):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "61f8b227-06cf-4251-87ff-92454ab1cd83",
    "email": "farmer@farmshield.ai",
    "full_name": "Ramesh Patil",
    "phone": "+919876543210",
    "role": "farmer",
    "is_active": true,
    "created_at": "2026-11-10T09:26:36.666539Z",
    "profile": {
      "preferred_language": "mr",
      "village": "Baramati",
      "district": "Pune",
      "state": "Maharashtra",
      "country": "India"
    }
  }
}
```

---

## 2. Farm Management

### Endpoints
- `GET /api/v1/farms/` (List all farms owned by authenticated farmer; paginated)
- `POST /api/v1/farms/` (Create new farm with GeoJSON MultiPolygon boundary)
- `GET /api/v1/farms/{id}` (Retrieve specific farm details)
- `GET /api/v1/farms/{id}/boundary` (Retrieve raw GeoJSON boundary for map rendering)
- `PUT /api/v1/farms/{id}` (Update metadata)

### Create Farm Payload (`POST /api/v1/farms/`)
```json
{
  "name": "Baramati Sugarcane Plot #4",
  "crop_type": "sugarcane",
  "crop_variety": "Co 86032",
  "location_name": "Baramati, Pune",
  "sowing_date": "2024-06-01",
  "boundary": {
    "type": "MultiPolygon",
    "coordinates": [
      [
        [
          [74.5800, 18.1500],
          [74.5900, 18.1500],
          [74.5900, 18.1600],
          [74.5800, 18.1600],
          [74.5800, 18.1500]
        ]
      ]
    ]
  }
}
```

### Farm Response Object (`FarmResponse`)
```json
{
  "id": "c039426c-f4e9-48b9-ac55-ab8ffad3755c",
  "owner_id": "61f8b227-06cf-4251-87ff-92454ab1cd83",
  "name": "Baramati Sugarcane Plot #4",
  "crop_type": "sugarcane",
  "crop_variety": "Co 86032",
  "location_name": "Baramati, Pune",
  "sowing_date": "2024-06-01",
  "area_hectares": 116.42,
  "boundary": {
    "type": "MultiPolygon",
    "coordinates": [...]
  },
  "created_at": "2026-11-10T09:29:05.000000Z",
  "updated_at": "2026-11-10T09:29:05.000000Z"
}
```
*Note: Paginated list returns `{"items": [...], "total": 1, "page": 1, "page_size": 20, "total_pages": 1}`.*

---

## 3. Zone Management

Every farm is partitioned into one or more management zones for fine-grained irrigation.

### Endpoints
- `GET /api/v1/farms/{farm_id}/zones` (List zones in farm)
- `POST /api/v1/farms/{farm_id}/zones` (Create zone with GeoJSON Polygon inside farm boundary)
- `GET /api/v1/farms/{farm_id}/zones/{zone_id}` (Retrieve specific zone)

### Create Zone Payload (`POST /api/v1/farms/{farm_id}/zones`)
```json
{
  "zone_name": "Zone A (North Drip Block)",
  "zone_code": "ZA-N",
  "metadata": {
    "irrigation_system": "drip",
    "soil_texture": "clay_loam"
  },
  "boundary": {
    "type": "Polygon",
    "coordinates": [
      [
        [74.5820, 18.1520],
        [74.5850, 18.1520],
        [74.5850, 18.1550],
        [74.5820, 18.1550],
        [74.5820, 18.1520]
      ]
    ]
  }
}
```

### Zone Response Object (`FarmZoneResponse`)
```json
{
  "id": "1b124694-dd32-47b8-aba2-bc22df8957cc",
  "farm_id": "c039426c-f4e9-48b9-ac55-ab8ffad3755c",
  "zone_name": "Zone A (North Drip Block)",
  "zone_code": "ZA-N",
  "area_hectares": 10.55,
  "metadata": {
    "irrigation_system": "drip",
    "soil_texture": "clay_loam"
  },
  "boundary": {
    "type": "Polygon",
    "coordinates": [...]
  },
  "created_at": "2026-11-10T09:29:05.000000Z",
  "updated_at": "2026-11-10T09:29:05.000000Z"
}
```

---

## 4. Observations & Evidence Streams

Observations store normalized physical sensor telemetry, weather forecasts, and satellite statistics.

### Endpoint
`GET /api/v1/farms/{farm_id}/observations`

**Query Parameters:**
- `zone_id`: Filter by specific management zone UUID.
- `observation_type`: Filter by type (`weather`, `soil_moisture`, `vegetation_index`, `temperature`, `rainfall`, `satellite`).
- `start_date` / `end_date`: ISO datetime range.

### Response Data Structure (`ObservationResponse`)
```json
{
  "id": "e4b2d189-9a2c-49f3-8f01-57d6205739cf",
  "farm_id": "c039426c-f4e9-48b9-ac55-ab8ffad3755c",
  "zone_id": "1b124694-dd32-47b8-aba2-bc22df8957cc",
  "observation_type": "soil_moisture",
  "source": "In-situ sensor (PROBE-01)",
  "observed_at": "2026-11-10T09:00:00Z",
  "value": 0.28,
  "unit": "m³/m³",
  "metadata": {
    "depth_min_cm": 0.0,
    "depth_max_cm": 30.0,
    "field_capacity_m3_m3": 0.34,
    "wilting_point_m3_m3": 0.17,
    "provenance": "sensor_measured"
  },
  "created_at": "2026-11-10T09:05:00Z"
}
```

### UI Provenance Badge Requirements
When displaying values on cards:
- `provenance == "sensor_measured"` $\to$ **Live Field Sensor** badge (Green).
- `provenance == "laboratory_analyzed"` $\to$ **Certified Lab Soil Test** badge (Blue).
- `provenance == "provider_modelled"` $\to$ **Regional Model Estimate** badge (Amber). *Never label as field sensor!*
- `provenance == "satellite_derived"` $\to$ **Copernicus Sentinel-2** badge (Purple).

---

## 5. Irrigation Recommendations & Intelligence Explanations

### Endpoint
`GET /api/v1/farms/{farm_id}/recommendations`

### Recommendation Schema Structure (`RecommendationResponse`)
```json
{
  "id": "8f03c4b1-8b01-44de-99c7-2c93881df332",
  "farm_id": "c039426c-f4e9-48b9-ac55-ab8ffad3755c",
  "zone_id": "1b124694-dd32-47b8-aba2-bc22df8957cc",
  "recommendation_type": "irrigation",
  "title": "Irrigation Recommended for Zone A",
  "description": "Root-zone water depletion (120.1 mm) has exceeded readily available water (RAW 110.5 mm).",
  "priority": "high",
  "status": "pending",
  "generated_at": "2026-11-10T09:30:00Z",
  
  "recommended_action": {
    "action_type": "irrigate",
    "priority": "high",
    "net_irrigation_depth_mm": 120.08,
    "gross_irrigation_depth_mm": 133.42,
    "irrigation_volume_m3": 3335.5,
    "application_efficiency": 0.90,
    "application_efficiency_provenance": "assumed_default",
    "is_efficiency_provisional": true,
    "split_application_required": true,
    "split_event_count": 2,
    "split_event_depths_mm": [66.71, 66.71]
  },
  
  "reasoning": {
    "language": "mr",
    "short_summary": "झोन Zone A मध्ये 2 टप्प्यांत विभागून (66.71 mm, 66.71 mm) एकूण 133.42 मिमी सिंचन आवश्यक आहे (निव्वळ तुटवडा: 120.1 मिमी).",
    "why_decision_produced": "मातीतील पाण्याचा तुटवडा (120.1 मिमी) सुरक्षित मर्यादेपलीकडे (RAW 110.5 मिमी) गेला आहे.",
    "action_guidance": "2 टप्प्यांत विभागून (66.71 mm, 66.71 mm) एकूण 133.42 मिमी पाणी द्या. एकाच वेळी संपूर्ण पाणी देणे टाळा.",
    "relevant_measurements": {
      "depletion_dr_mm": 120.08,
      "readily_available_water_raw_mm": 110.50,
      "total_available_water_taw_mm": 170.00,
      "net_irrigation_depth_mm": 120.08,
      "gross_irrigation_depth_mm": 133.42,
      "irrigation_volume_m3": 3335.5,
      "split_event_count": 2,
      "split_event_depths_mm": [66.71, 66.71],
      "satellite_ndvi": 0.65,
      "satellite_ndmi": 0.30
    }
  }
}
```

---

## 6. Critical Display & UI Rules for Frontend Feature Screens

1. **Split-Application Schedule Display:**
   - When `split_application_required == true`:
     - Display `split_event_count` distinct event pills.
     - Render depths with **exact 2-decimal precision** (`split_event_depths_mm.join(" mm, ") + " mm"`). Example: `66.71 mm, 66.71 mm`.
     - **NEVER** display only the total gross depth as a single application event.
2. **Net vs. Gross Distinction:**
   - Always clearly label:
     - **Net Crop Water Deficit ($d_{net}$):** The physical amount required by crop roots (e.g., $120.1\text{ mm}$).
     - **Gross Irrigation Depth ($d_{gross}$):** The volume to pump accounting for application efficiency (e.g., $133.4\text{ mm}$ at $90\%$ efficiency).
3. **Multilingual Language Switching (`en`, `mr`, `hi`):**
   - The UI header contains a language toggle (`mr` default, cycling `mr` $\to$ `hi` $\to$ `en`).
   - Use `reasoning.short_summary` and `reasoning.action_guidance` which are pre-translated deterministically by the Phase 6 explanation service.
   - For UI labels, use `src/data/translations.js`.
4. **Vite Development Proxy Configuration:**
   - In `vite.config.js`, configure proxy so local frontend API requests route to the backend:
   ```javascript
   export default defineConfig({
     plugins: [react()],
     server: {
       port: 5173,
       proxy: {
         '/api': {
           target: 'http://127.0.0.1:8000',
           changeOrigin: true
         }
       }
     }
   });
   ```
