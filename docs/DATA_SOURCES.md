# Data Sources, Provenance and Integration Notes

**Owner:** Harshal Ramteke  
**Consumers:** Bhavikesh (intelligence), Chaitanya (persistence/API), Disha/Vidula (UI provenance).

## 1. Source principles

- Use official/provider documentation and check current terms before implementation/deployment.
- Record provider, dataset/product, acquisition/forecast time, retrieval time, spatial/temporal resolution, units, model/run where supplied and quality flags.
- Distinguish field measurements from gridded/model estimates and satellite-derived indices.
- Respect attribution, quotas, rate limits, registration and commercial/noncommercial eligibility.
- Never put API credentials in the frontend or Git repository.

## 2. Source inventory

| Data need | Preferred source | MVP role | Important limitation |
|---|---|---|---|
| Optical crop/vegetation observations | Copernicus Sentinel-2 / Earth Engine catalogue | NDVI and vegetation trend | Cloud/shadow; nominal revisit is not guaranteed usable observation; not direct soil moisture |
| Radar observations | Sentinel-1 | Optional/later supporting feature | Requires radar preprocessing/interpretation; not a direct root-zone moisture sensor |
| Weather forecast | Open-Meteo Forecast API | Precipitation, temperature, humidity, ET₀ where available | Forecast uncertainty and model/provider resolution; retain retrieval/model metadata |
| Historical weather | Open-Meteo Historical Weather API | Baseline and past conditions | Reanalysis/modelled historical data, not a local rain-gauge record |
| Historical forecast verification | Open-Meteo Historical Forecast API | Optional compare forecasts with later observations | Understand forecast-run semantics and endpoint availability |
| Soil properties | SoilGrids or local soil data | Static soil-property context | Not real-time soil moisture; grid predictions have uncertainty/resolution |
| Soil moisture | Field sensor, approved local source or explicitly labelled model estimate | Water-balance evidence | Depth, calibration, location and resolution matter |
| Crop coefficients/parameters | FAO-56 and locally validated agronomy references | Water calculation | Kc/root depth vary by crop, stage, climate and management |

## 3. Sentinel-2

- Use a documented Sentinel-2 surface-reflectance product/collection.
- Common NDVI inputs: red B4 and near-infrared B8 for Sentinel-2 MSI.
- B4 and B8 are nominally 10 m; other spectral bands have different resolutions.
- Apply cloud and cloud-shadow masking and retain quality statistics.
- Keep scene/product ID, acquisition time, processing level, bands, resolution, CRS and processing version.
- Use only scenes with sufficient valid pixels intersecting the zone.
- A nominal revisit interval is not a guarantee of a cloud-free usable observation for a specific field.
- Do not claim daily or real-time satellite updates.

Official references:
- ESA Sentinel-2 mission: https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-2
- Earth Engine Sentinel-2 Harmonized Surface Reflectance: https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED

## 4. Google Earth Engine access

Earth Engine access requires a Google Cloud project with the Earth Engine API enabled, registration for commercial/noncommercial use and correct permissions. The team must:

1. Create/select a controlled Google Cloud project.
2. Register it for the intended access category.
3. Confirm the project has appropriate permissions.
4. Configure server-side credentials securely.
5. Verify quota, usage and terms before processing the demo farm.

Official guide: https://developers.google.com/earth-engine/guides/access

If Earth Engine access is unavailable in time, use an alternative documented data acquisition route or a small clearly labelled prepared scene/fixture. Do not claim live ingestion if using a stored sample.

## 5. Open-Meteo

Potential useful variables include precipitation, temperature, relative humidity, wind, radiation and FAO reference evapotranspiration (`et0_fao_evapotranspiration`). Some endpoints expose soil-moisture estimates at model grid/depth levels; such outputs must remain `provider_modelled`, not `sensor_measured`.

- Forecast documentation: https://open-meteo.com/en/docs
- Historical Weather API: https://open-meteo.com/en/docs/historical-weather-api
- Historical Forecast API: https://open-meteo.com/en/docs/historical-forecast-api

Implementation requirements:

- Use farm coordinate/appropriate representative location and retain coordinates used.
- Request only required variables.
- Store units and timezone returned; normalize timestamps to UTC while retaining source timezone if relevant.
- Separate historical/reanalysis from forecast data.
- Retain forecast valid time and retrieval/model run time.
- Handle missing fields, rate limits, timeouts and provider errors.
- Review current pricing, terms, attribution and commercial-use requirements before public deployment.

## 6. Soil data and field sensors

SoilGrids provides mapped soil property estimates, not live farm moisture. It may be used as background soil context only after checking variable, depth interval, spatial resolution and uncertainty.

Field sensor data should include:

- sensor ID and calibration status;
- location/zone;
- depth;
- unit and measurement time;
- device/provider;
- quality flags and missing periods.

A farmer-entered moisture value should be labelled farmer-entered and not sensor-measured.

## 7. Crop and agronomy references

Use FAO-56 for the reference ET₀/Kc/ETc framework and root-zone scheduling concepts. Crop coefficients, rooting depth and allowable depletion must be selected for the actual demo crop and growth stage and reviewed by an agronomy mentor/credible local reference.

FAO-56: https://www.fao.org/4/X0490E/X0490E00.htm

## 8. Canonical variable naming

Examples:

| Code | Meaning | Unit | Provenance examples |
|---|---|---|---|
| `ndvi` | Normalized Difference Vegetation Index | dimensionless | `satellite_derived` |
| `ndmi` | Normalized Difference Moisture Index (if selected formula is documented) | dimensionless | `satellite_derived` |
| `precipitation_mm` | Precipitation amount | mm | `provider_modelled` or gauge measured |
| `temperature_2m_c` | Air temperature at 2 m | °C | `provider_modelled` / station measured |
| `et0_mm_day` | Reference evapotranspiration | mm/day | `provider_modelled` / calculated |
| `soil_moisture_m3_m3` | Volumetric water content | m³/m³ | sensor or modelled, clearly distinguished |
| `etc_mm_day` | Crop evapotranspiration | mm/day | `calculated` |
| `net_irrigation_mm` | Net irrigation depth | mm | `calculated` |

Do not use `ndwi` without defining which NDWI formulation is meant. Several formulas use different bands and represent different water/vegetation properties.

## 9. Provider adapter output

Every provider adapter should return a normalized object containing:

- provider and dataset/product;
- canonical variable code and value;
- unit;
- coordinates/geometry or asset bounds;
- observed/valid time and retrieved time;
- source reference/model run/scene ID;
- spatial/temporal resolution where known;
- provenance type;
- quality state and raw metadata reference.

## 10. Data quality states

- `good`: usable for intended calculation.
- `suspect`: present but questionable; may be excluded or shown with warning.
- `cloud_contaminated`: optical observation invalid/partially invalid due to cloud/shadow.
- `stale`: older than configured freshness policy for that variable/use.
- `missing`: unavailable.
- `simulated`: development/demo fixture only.

Freshness policy must vary by variable. Satellite observations are not expected to refresh as frequently as weather forecasts.

## 11. Attribution and licensing checklist

Before using a source in a public demo or deployment, record:

- terms/licence and whether commercial use is permitted;
- attribution text/requirements;
- quotas/rate limits;
- caching and redistribution conditions;
- data retention requirements;
- access/authentication method;
- date checked and person responsible.

Source terms can change. Recheck them at implementation and release time.
