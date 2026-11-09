# Prototype Demonstration Script

**Purpose:** Demonstrate one complete, reproducible FarmShield workflow to judges.  
**Primary device:** Android smartphone or mobile browser/PWA.  
**Secondary:** Laptop for technical/advanced view if required.

## 1. Demo story

A farmer has a soybean farm divided into management zones. Different zones show different vegetation and environmental evidence. FarmShield combines available observations, evaluates each zone, calculates irrigation needs where inputs permit, explains its assessment and records the farmer's action.

The demonstration must use a real, traceable sample farm/data path or clearly labelled simulated data. Never mix the two without labels.

## 2. Pre-demo checklist

- App deployed or running on the chosen phone.
- English and Marathi switching tested.
- Demo user/farm seeded through a reproducible script.
- Farm boundary and 4–6 zone polygons validated.
- Satellite scene date/ID and cloud-quality summary available.
- Weather source, location and retrieval time available.
- Soil input provenance visible (sensor/model/farmer input/unknown).
- Analysis run completed and stored.
- Recommendations and reason codes generated from stored inputs.
- Action recording works and appears in history.
- Backup screenshots/video and local fallback available.
- No secret credentials or personal farmer data visible.

## 3. Demo flow

### Step 1 — Open and select language

Show FarmShield splash screen and select English or Marathi. Explain that the language applies to the full application.

### Step 2 — Select demonstration farm

Show farm name, location, crop, season, area and boundary. Explain that crop/soil context affects water calculations.

### Step 3 — Dashboard overview

Show farm status, number of zones, priority zones, data freshness and weather summary. Explain that the status is based on available evidence, not a single index.

### Step 4 — Open Digital Twin

Show boundary and management zones. Toggle available layers. Point out legend, observation date and source. Explain if a layer is unavailable due to cloud cover or missing inputs.

### Step 5 — Select a zone

Open one zone and show crop context, vegetation trend, rainfall/ET₀ and soil evidence with provenance. Distinguish measured from modelled/derived values.

### Step 6 — Inspect water calculation

Show ET₀, Kc, ETc, effective rainfall and root-zone water-balance inputs when available. Explain that ETc alone is not the final irrigation amount. If soil/root-zone information is missing, show `insufficient_data` or a limited inspection action instead of a fabricated quantity.

### Step 7 — Review recommendation

Show action, priority, recommended amount/window only if valid, reasons, evidence and assumptions. Explain that the system is advisory and does not automatically switch on a pump.

### Step 8 — Record farmer action

Record irrigation/inspection with time, zone, duration or amount if known. Explain that farmer-recorded data is not a verified sensor measurement.

### Step 9 — Show history

Show the newly recorded event and the previous analysis. Explain how future observations can update the farm representation and allow comparison.

### Step 10 — Show Advanced Analysis

Briefly show the agronomist view: source metadata, indices, timestamps, calculation assumptions and quality flags.

## 4. Suggested presentation narration

"FarmShield does not treat an entire farm as one uniform field. It maintains a zone-level view using the information available from satellite imagery, weather, crop and soil sources. It assesses which zones need attention, uses agronomic calculations to estimate water requirements where the inputs are sufficient, and explains the evidence behind each recommendation. The farmer remains in control and can record the action for future comparison."

## 5. Judge questions to prepare for

### Why is this a digital twin rather than a dashboard?

Because the system maintains a farm-state representation linked to boundary, zones, observations and analysis versions, and updates that representation as new observations/actions arrive. If only a static map is implemented, describe it honestly as a prototype digital representation rather than a fully validated bidirectional digital twin.

### How do you know a zone needs water?

Explain the evidence used: crop stage, screened vegetation trend, weather/ET₀, rainfall and field-specific soil/root-zone evidence where available. Explain which inputs are missing and what confidence limitation follows.

### Does NDVI measure soil moisture?

No. NDVI is a vegetation index derived from red and near-infrared reflectance. It can indicate vegetation condition but does not directly measure root-zone soil moisture.

### What if satellite imagery is cloudy?

The scene is quality-masked or excluded. The system uses other available observations and may return partial/insufficient data. It does not invent a fresh satellite observation.

### How do you calculate water requirement?

Describe ET₀, crop coefficient Kc and ETc, then the root-zone water balance, effective rainfall and irrigation efficiency assumptions. Explain that ETc alone is not irrigation amount.

### Is the irrigation automatic?

No. The MVP is decision support. The farmer reviews and records actions; hardware actuation is future scope.

### What is innovative?

The product's intended value is the integrated, provenance-aware, zone-level decision workflow that combines remote sensing, weather, crop/soil context and agronomic validation, rather than displaying isolated data layers.

## 6. Demo failure fallback

- If live provider access fails, switch to a preprocessed fixture clearly labelled `SIMULATED / DEMO DATA` or `CACHED DATA`.
- If one source is unavailable, show partial data and explain the impact on the recommendation.
- If water-balance inputs are insufficient, demonstrate the `insufficient_data` state rather than inventing irrigation quantity.
- If network drops, show last successful update time and explain that values are cached.
- Do not patch database values manually during the judge demonstration.

## 7. Evidence pack

Keep a folder/manifest with:
- demo farm boundary and zones;
- satellite scene ID/date and processing notes;
- weather query coordinates/time and response fixture;
- crop parameter source and version;
- sample analysis run ID;
- expected API responses;
- expected screenshots;
- test results and known limitations.
