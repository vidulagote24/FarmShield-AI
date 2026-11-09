# API Contracts

**API prefix:** `/api/v1`  
**Owner:** Chaitanya Hapse  
**Consumers:** Disha and Vidula; intelligence/data services are orchestrated by the backend.

## 1. API conventions

- JSON for normal resources; GeoJSON for spatial features.
- UTC timestamps using RFC 3339, e.g. `2026-11-07T10:30:00Z`.
- Distance/area/water/temperature units must be explicit.
- Stable machine enums are stored and returned; frontend translates labels.
- Use UUID identifiers.
- Return `null` when a value is unknown or unavailable; never replace missing numeric data with zero.
- Use `/api/v1` for all application APIs.
- Paginate growing collections using `limit` and `cursor` or a consistently chosen alternative; document it before implementation.
- All farm-scoped requests must verify user membership/authorization.

## 2. Standard error envelope

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Farm boundary is invalid.",
    "details": [
      {"field": "boundary", "reason": "self_intersection"}
    ],
    "request_id": "uuid"
  }
}
```

Do not return raw stack traces or provider credentials.

## 3. Core endpoints

| Method | Path | Purpose | Primary frontend owner |
|---|---|---|---|
| POST | `/farms` | Create farm | Disha |
| GET | `/farms` | List farms user can access | Disha |
| GET | `/farms/{farm_id}` | Farm detail | Disha |
| PATCH | `/farms/{farm_id}` | Update farm metadata | Disha |
| POST | `/farms/{farm_id}/zones` | Create zone | Vidula |
| GET | `/farms/{farm_id}/zones` | List zones/GeoJSON | Vidula |
| GET | `/zones/{zone_id}` | Zone detail | Vidula |
| GET | `/zones/{zone_id}/analysis` | Latest zone assessment/evidence | Vidula |
| GET | `/farms/{farm_id}/dashboard` | Dashboard summary | Disha |
| GET | `/farms/{farm_id}/observations` | Observation list/trends | Vidula |
| POST | `/farms/{farm_id}/analysis-runs` | Request analysis | Disha/Vidula |
| GET | `/analysis-runs/{run_id}` | Analysis status/result metadata | Disha/Vidula |
| GET | `/farms/{farm_id}/recommendations` | Recommendations list | Vidula |
| GET | `/recommendations/{recommendation_id}` | Recommendation detail | Vidula |
| POST | `/irrigation-events` | Record completed irrigation | Vidula |
| GET | `/farms/{farm_id}/irrigation-events` | Irrigation history | Vidula |
| GET | `/farms/{farm_id}/history` | Farm activity/history | Vidula |
| GET | `/farms/{farm_id}/alerts` | Alert list | Vidula |

Authentication endpoints/provider are TBD. During local development a seeded test identity may be used, but it must not be mistaken for production authentication.

## 4. Farm creation contract

### Request

```json
{
  "name": "Green Valley Farm",
  "location_name": "Pune, Maharashtra, India",
  "timezone": "Asia/Kolkata",
  "boundary": {
    "type": "Polygon",
    "coordinates": [[[73.8, 18.5], [73.801, 18.5], [73.801, 18.501], [73.8, 18.5]]]
  },
  "crop": {
    "crop_name": "soybean",
    "sowing_date": "2026-06-15",
    "growth_stage": "vegetative",
    "irrigation_method": "drip"
  }
}
```

Coordinates above are illustrative only and must not be used as a real farm boundary. Production implementation must validate polygon closure, area, CRS and self-intersection.

### Response

```json
{
  "id": "farm-uuid",
  "name": "Green Valley Farm",
  "location_name": "Pune, Maharashtra, India",
  "timezone": "Asia/Kolkata",
  "area_ha": null,
  "boundary": {"type": "Polygon", "coordinates": []},
  "crop": {
    "crop_name": "soybean",
    "sowing_date": "2026-06-15",
    "growth_stage": "vegetative",
    "irrigation_method": "drip"
  },
  "created_at": "2026-11-07T10:30:00Z"
}
```

Example response values/geometry are illustrative. API must return actual validated values.

## 5. Dashboard response contract

```json
{
  "farm": {
    "id": "farm-uuid",
    "name": "Green Valley Farm",
    "location_name": "Pune, Maharashtra, India",
    "area_ha": null,
    "crop_name": "soybean",
    "growth_stage": "vegetative"
  },
  "overall_status": "attention",
  "zone_counts": {
    "total": 6,
    "healthy": 3,
    "monitor": 1,
    "attention": 2,
    "high_stress": 0,
    "insufficient_data": 0
  },
  "priority_zones": [
    {
      "zone_id": "zone-uuid",
      "zone_name": "Zone C",
      "status": "attention",
      "action_code": "inspect",
      "reason_codes": ["vegetation_trend_declining"]
    }
  ],
  "data_freshness": {
    "satellite_observed_at": null,
    "weather_retrieved_at": null,
    "soil_observed_at": null,
    "status": "partial"
  },
  "generated_at": "2026-11-07T10:30:00Z"
}
```

The endpoint must not calculate a `zone_counts` value from zones that are missing/archived or silently discard insufficient-data zones.

## 6. Zone GeoJSON response

Return a GeoJSON `FeatureCollection` with a stable `zone_id` and machine status in properties. Do not encode status only by fill colour.

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "id": "zone-uuid",
      "geometry": {"type": "Polygon", "coordinates": []},
      "properties": {
        "zone_id": "zone-uuid",
        "name": "Zone C",
        "area_ha": null,
        "status": "insufficient_data",
        "last_assessed_at": null
      }
    }
  ]
}
```

## 7. Zone analysis response

```json
{
  "zone_id": "zone-uuid",
  "zone_name": "Zone C",
  "status": "insufficient_data",
  "data_quality_status": "partial",
  "crop": {"name": "soybean", "growth_stage": "vegetative"},
  "vegetation": {
    "index": "NDVI",
    "current_value": null,
    "previous_value": null,
    "trend": "unknown",
    "observed_at": null,
    "source": null
  },
  "weather": {
    "rainfall_mm_period": null,
    "et0_mm_day": null,
    "forecast_summary": null,
    "retrieved_at": null,
    "source": null
  },
  "soil_evidence": {
    "value": null,
    "unit": null,
    "provenance_type": null,
    "depth_cm": null,
    "observed_at": null
  },
  "water_balance": {
    "etc_mm_day": null,
    "effective_rainfall_mm": null,
    "root_zone_depletion_mm": null,
    "net_irrigation_mm": null,
    "gross_irrigation_mm": null,
    "calculation_status": "insufficient_data",
    "assumptions": []
  },
  "recommendation": {
    "action_code": "insufficient_data",
    "priority": "low",
    "water_depth_mm": null,
    "water_volume_m3": null,
    "reason_codes": ["missing_required_soil_water_inputs"],
    "explanation": "There is not enough field-specific information to calculate a reliable irrigation quantity.",
    "uncertainty_note": "Add a field moisture observation or validated soil-water estimate and confirm crop parameters."
  },
  "evidence": [],
  "analysis_version": "0.1.0",
  "assessed_at": "2026-11-07T10:30:00Z"
}
```

This is a safe example of an insufficient-data response, not a live analysis.

## 8. Observation shape

```json
{
  "id": "observation-uuid",
  "farm_id": "farm-uuid",
  "zone_id": null,
  "variable_code": "et0_mm_day",
  "value": 4.2,
  "unit": "mm/day",
  "provenance_type": "provider_modelled",
  "source_provider": "open_meteo",
  "source_reference": null,
  "observed_at": "2026-11-07T00:00:00Z",
  "retrieved_at": "2026-11-07T01:00:00Z",
  "valid_from": null,
  "valid_to": null,
  "quality_status": "good"
}
```

Numbers/dates are examples only. Preserve provider model/run information when available.

## 9. Recommendation response

Required fields:

- `id`, `farm_id`, `zone_id`, `analysis_run_id`;
- `action_code`, `priority`;
- optional water depth/volume and recommended window;
- `reason_codes`;
- `evidence_observation_ids`;
- `assumptions` and `uncertainty_note`;
- `calculation_version`, `created_at`.

The action code must allow `insufficient_data`. It is not acceptable to force every zone into irrigate/monitor/no-action.

## 10. Irrigation event request

```json
{
  "farm_id": "farm-uuid",
  "zone_id": "zone-uuid",
  "occurred_at": "2026-11-07T06:00:00Z",
  "water_depth_mm": null,
  "water_volume_m3": null,
  "duration_minutes": 35,
  "method": "drip",
  "source": "farmer_recorded",
  "notes": null
}
```

At least one useful action detail should be recorded, but the API should support approximate or unknown amounts without inventing them. Distinguish farmer-recorded from sensor-recorded.

## 11. Analysis run lifecycle

`queued` → `running` → `succeeded` / `partial` / `failed`.

A `partial` result is valid when some sources are unavailable but remaining evidence supports a limited assessment. A failed provider must be included in the run's data-quality report.

## 12. Contract change process

Chaitanya owns the API schema. Any change must:

1. Update this document.
2. Update Pydantic schemas and OpenAPI.
3. Add/update API tests.
4. Notify Disha/Vidula and Bhavikesh/Harshal if their modules consume the field.
5. Preserve backward compatibility within a version where practical; otherwise document migration.
