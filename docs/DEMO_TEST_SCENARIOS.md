# FarmShield AI — End-to-End Demonstration Scenarios

This document details 7 representative demonstration scenarios across the FarmShield AI intelligence, data ingestion, and decision-support pipeline. Each scenario specifies exact input evidence, deterministic agronomic calculations, expected decision outcomes, multilingual farmer explanations, and data provenance.

---

## Scenario 1: Healthy Agricultural Zone (Optimal Soil Moisture)

- **Scenario Identifier:** `DEMO-SCENARIO-01-HEALTHY`
- **Objective:** Demonstrate optimal vegetative condition where root-zone soil water is well above the management threshold ($D_r < RAW$).
- **Evidence Source:** Controlled synthetic test fixture (conforming to `AI_SPEC.md`).

### 1. Input Evidence
- **Crop Context:**
  - Crop: Sugarcane (`mid_season`), $Z_r = 1.0\text{ m}$, $p = 0.65$.
  - Farm Area: 2.0 ha, Irrigation Method: Drip ($\eta = 0.90$, assumed default).
- **Soil Evidence:**
  - Soil Texture: Clay Loam ($\theta_{FC} = 0.34\text{ m}^3/\text{m}^3$, $\theta_{WP} = 0.17\text{ m}^3/\text{m}^3$).
  - Measured Volumetric Water Content: $0.32\text{ m}^3/\text{m}^3$ (TDR probe at 0–30 cm).
  - Provenance: `sensor_measured`.
  - Available Water Capacities: $TAW = 170.0\text{ mm}$, $RAW = 110.5\text{ mm}$.
- **Meteorological Evidence:**
  - Daily $ET_0 = 4.2\text{ mm/day}$, $K_c = 1.25 \implies ET_c = 5.25\text{ mm/day}$.
  - Daily Precipitation: $0.0\text{ mm}$.
- **Satellite Evidence:**
  - Sentinel-2 L2A NDVI mean: $0.72$ (dense green canopy), NDMI mean: $0.35$.
  - Cloud cover: $0.0\%$, Quality Status: `GOOD`.
- **Water Balance Accounting:**
  - Current root-zone depletion: $D_r = 25.0\text{ mm}$ ($D_r \ll RAW$).

### 2. Expected Outcomes
- **Stress Assessment Status:** `HEALTHY` (Overall water stress severity: $0.00$, $K_s = 1.0$).
- **Recommended Action:** `NO_ACTION_REQUIRED`
- **Priority:** `LOW`
- **Net Refill Depth:** `0.0 mm`
- **Gross Irrigation Depth:** `0.0 mm`
- **Quality Warnings:** None.

### 3. Expected Multilingual Farmer Explanations
- **English:**
  - *Summary:* Zone Zone A is healthy. Root-zone soil moisture is adequate. No irrigation is needed today.
  - *Why Produced:* Current soil water depletion (25.0 mm) is well within the safe buffer (RAW 110.5 mm).
  - *Action Guidance:* Maintain current monitoring schedule. Next scheduled evaluation will run tomorrow.
- **Marathi (मराठी):**
  - *Summary:* झोन Zone A मधील पिकांची स्थिती समाधानकारक आहे. मातीतील ओलावा पुरेसा असल्याने आज सिंचनाची गरज नाही.
  - *Action Guidance:* नियमित निरीक्षण सुरू ठेवा.
- **Hindi (हिंदी):**
  - *Summary:* ज़ोन Zone A में फसल की स्थिति स्वस्थ है। मिट्टी में पर्याप्त नमी उपलब्ध है, आज सिंचाई की आवश्यकता नहीं है।
  - *Action Guidance:* नियमित निगरानी जारी रखें।

---

## Scenario 2: Active Root-Zone Water Deficit ($D_r \ge RAW$)

- **Scenario Identifier:** `DEMO-SCENARIO-02-DEFICIT-IRRIGATE`
- **Objective:** Trigger an active irrigation recommendation when root-zone depletion crosses readily available water, accounting for drip application efficiency.
- **Evidence Source:** Actual Open-Meteo weather forecast combined with in-situ soil probe evidence.

### 1. Input Evidence
- **Crop Context:**
  - Crop: Sugarcane (`mid_season`), $Z_r = 1.0\text{ m}$, $p = 0.65$.
  - Zone Area: 2.5 ha, Irrigation System: Drip ($\eta = 0.90$, generic FAO-56 default).
- **Soil Evidence:**
  - Soil Texture: Clay Loam ($\theta_{FC} = 0.34$, $\theta_{WP} = 0.17$).
  - In-situ Sensor: $0.21\text{ m}^3/\text{m}^3$ ($D_r = 120.08\text{ mm}$).
  - $TAW = 170.0\text{ mm}$, $RAW = 110.5\text{ mm}$.
- **Meteorological Evidence (Open-Meteo Live API):**
  - Pune/Baramati coordinates (18.15°N, 74.58°E).
  - Mean Temperature: $24.1^\circ\text{C}$, $ET_0 = 4.4\text{ mm/day}$, Rainfall Forecast: $0.0\text{ mm}$.
- **Satellite Evidence (Copernicus Sentinel-2 STAC):**
  - Scene `S2A_43QDA_20241030_0_L2A`, Cloud Fraction: $0.03\%$.
  - Zonal NDVI mean: $0.65$, NDMI mean: $0.30$.

### 2. Expected Outcomes
- **Stress Assessment Status:** `ATTENTION` / Active Water Stress ($D_r = 120.08\text{ mm} > RAW = 110.50\text{ mm}$, $K_s = 0.84$).
- **Recommended Action:** `IRRIGATE`
- **Priority:** `HIGH`
- **Net Irrigation Depth ($d_{net}$):** $120.08\text{ mm}$ (exact root-zone refill requirement).
- **Gross Irrigation Depth ($d_{gross} = d_{net} / \eta$):** $133.42\text{ mm}$.
- **Gross Irrigation Volume ($V = 10 \times A \times d_{gross}$):** $3,335.5\text{ m}^3$ across 2.5 ha.
- **Split Application Required:** `True` (Since $d_{gross} = 133.42\text{ mm} > 100.0\text{ mm}$ maximum single-event limit).
  - Cycle count: $2$ events.
  - Event depths: `66.71 mm`, `66.71 mm` (conserving exact $133.42\text{ mm}$).

### 3. Expected Multilingual Farmer Explanations
- **English:**
  - *Summary:* Zone Zone B needs 133.42 mm gross irrigation across 2 split cycles (66.71 mm, 66.71 mm) (net crop deficit: 120.1 mm).
  - *Why Produced:* Root-zone water depletion (120.1 mm) has reached the management threshold (RAW 110.5 mm).
  - *Action Guidance:* Apply 133.42 mm gross irrigation across 2 split events (66.71 mm, 66.71 mm) to avoid soil runoff.
- **Marathi (मराठी):**
  - *Summary:* झोन Zone B मध्ये 2 टप्प्यांत विभागून (66.71 mm, 66.71 mm) एकूण 133.42 मिमी सिंचन आवश्यक आहे (निव्वळ तुटवडा: 120.1 मिमी).
  - *Action Guidance:* 2 टप्प्यांत विभागून (66.71 mm, 66.71 mm) एकूण 133.42 मिमी पाणी द्या. एकाच वेळी संपूर्ण पाणी देणे टाळा.
- **Hindi (हिंदी):**
  - *Summary:* ज़ोन Zone B में 2 चरणों में विभाजित (66.71 mm, 66.71 mm) कुल 133.42 मिमी सिंचाई आवश्यक है (शुद्ध मांग: 120.1 मिमी).
  - *Action Guidance:* 2 चरणों में विभाजित (66.71 mm, 66.71 mm) कुल 133.42 मिमी पानी लगाएं। एक ही बार में पूरा पानी न दें।

---

## Scenario 3: Missing Weather Data (Fail-Closed Robustness)

- **Scenario Identifier:** `DEMO-SCENARIO-03-MISSING-WEATHER`
- **Objective:** Verify scientific fail-closed behavior when meteorological reanalysis/forecast data is completely unavailable.
- **Evidence Source:** Synthetic offline test fixture simulating network outage.

### 1. Input Evidence
- **Crop Context:** Sugarcane (`mid_season`), $Z_r = 1.0\text{ m}$.
- **Soil Evidence:** In-situ probe reading available ($0.26\text{ m}^3/\text{m}^3$).
- **Satellite Evidence:** Sentinel-2 optical scene available (NDVI: $0.62$).
- **Meteorological Evidence:** Completely absent (`weather_features = None`, HTTP 503 from provider).

### 2. Expected Outcomes
- **Stress Assessment Status:** `INSUFFICIENT_DATA` (Water-balance model requires daily $ET_0$ to calculate crop transpiration).
- **Recommended Action:** `INSUFFICIENT_DATA`
- **Priority:** `UNRANKED`
- **Net Refill Depth:** `null` (Never invent or guess numbers without evidence).
- **Gross Irrigation Depth:** `null`
- **Irrigation Volume:** `null`
- **Quality Caveats:** `"Meteorological evidence is missing or incomplete; FAO-56 Penman-Monteith ET0 cannot be calculated."`

### 3. Expected Multilingual Farmer Explanations
- **English:**
  - *Summary:* Insufficient data to determine irrigation advice for Zone Zone C. Weather data is unavailable.
  - *Why Produced:* Critical weather observations are missing. FarmShield AI will not guess irrigation requirements.
  - *Action Guidance:* Check local weather conditions or inspect soil moisture manually before irrigating.
- **Marathi (मराठी):**
  - *Summary:* झोन Zone C साठी आवश्यक हवामान माहिती उपलब्ध नसल्याने सिंचन सल्ला निश्चित करता आला नाही.
  - *Action Guidance:* स्थानिक हवामान किंवा मातीतील प्रत्यक्ष ओलावा तपासा.
- **Hindi (हिंदी):**
  - *Summary:* ज़ोन Zone C के लिए आवश्यक मौसम डेटा अनुपलब्ध होने के कारण सिंचाई सलाह निर्धारित नहीं की जा सकी।
  - *Action Guidance:* स्थानीय मौसम या मिट्टी की नमी की प्रत्यक्ष जांच करें।

---

## Scenario 4: Stale Satellite Evidence (Optical Cloud Occlusion)

- **Scenario Identifier:** `DEMO-SCENARIO-04-STALE-SATELLITE`
- **Objective:** Demonstrate that monsoon cloud cover or stale optical satellite passes are transparently flagged as quality caveats without halting deterministic water-balance irrigation decisions.
- **Evidence Source:** Element84 STAC query returning heavy monsoon cloud cover ($85\%$ cloud fraction).

### 1. Input Evidence
- **Crop Context:** Cotton (`flowering_boll_formation`), $Z_r = 0.8\text{ m}$.
- **Soil Evidence:** In-situ probe reading available ($0.20\text{ m}^3/\text{m}^3$, $D_r \ge RAW$).
- **Meteorological Evidence:** Live Open-Meteo weather available (Daily $ET_0 = 4.8\text{ mm/day}$).
- **Satellite Evidence:**
  - Acquisition age: 24 days old (freshness limit is 14 days).
  - SCL Breakdown: $85\%$ cloud/cirrus cover.
  - Quality Status: `CLOUD_CONTAMINATED` / `STALE`.

### 2. Expected Outcomes
- **Stress Assessment Status:** `ATTENTION` (Governed by active water-balance deficit, not blinded by cloudy satellite).
- **Recommended Action:** `IRRIGATE`
- **Priority:** `HIGH`
- **Quality Caveats Recorded:**
  - `"Satellite optical pass exceeds freshness policy (24 days old)."`
  - `"Satellite pass has 85% cloud contamination; canopy vegetation metrics withheld."`
- **Decision Engine Behavior:** Generates legitimate water-balance irrigation advice while explicitly auditing satellite staleness in the explanation output.

### 3. Expected Multilingual Farmer Explanations
- **English:**
  - *Summary:* Zone Zone D requires irrigation based on soil water depletion. Satellite images are currently obscured by clouds.
  - *Why Produced:* Soil moisture measurements indicate critical depletion. Satellite vegetation indices are outdated due to persistent cloud cover.
- **Marathi (मराठी):**
  - *Summary:* ढगाळ वातावरणामुळे उपग्रह छायाचित्रे उपलब्ध नसली, तरी मातीतील ओलावा संपल्याने झोन Zone D ला सिंचन देणे आवश्यक आहे.

---

## Scenario 5: Emergency Irrigation with Split Application ($d_{gross} > 100\text{ mm}$)

- **Scenario Identifier:** `DEMO-SCENARIO-05-EMERGENCY-SPLIT`
- **Objective:** Verify emergency irrigation handling during critical flowering stage with severe deficit, strictly enforcing split-application depth limits ($100.0\text{ mm}$ max event depth) with exact 2-decimal conservation.
- **Evidence Source:** Controlled agronomic stress fixture.

### 1. Input Evidence
- **Crop Context:** Sugarcane, Zone Area: 3.0 ha.
- **Soil Context:** Deep Black Clay, $TAW = 250.0\text{ mm}$, $RAW = 125.0\text{ mm}$.
- **Water Balance Deficit:** $D_r = 198.0\text{ mm}$ (Approaching Permanent Wilting Point).
- **Irrigation System:** Furrow Surface ($\eta = 0.90$).
- **Calculated Gross Depth:** $d_{gross} = 198.0 / 0.90 = 220.00\text{ mm}$.
- **Maximum Permissible Single Event:** $100.0\text{ mm}$.

### 2. Expected Outcomes
- **Recommended Action:** `IRRIGATE`
- **Priority:** `CRITICAL` (Emergency Wilting Point Precedence)
- **Split Application Required:** `True`
- **Event Count:** `3` cycles.
- **Event Depths Schedule:** `[73.33 mm, 73.33 mm, 73.34 mm]` (Exact sum = $220.00\text{ mm}$).
- **Single-Event Prohibition:** Explicit warning never to apply 220 mm at once.

### 3. Expected Multilingual Farmer Explanations
- **English:**
  - *Summary:* EMERGENCY: Zone Zone E needs 220.00 mm gross irrigation across 3 split cycles (73.33 mm, 73.33 mm, 73.34 mm) (net crop deficit: 198.0 mm).
  - *Action Guidance:* Apply 220.00 mm gross irrigation across 3 split cycles (73.33 mm, 73.33 mm, 73.34 mm). Critical: do not apply the entire 220.00 mm in a single event to prevent massive runoff and crop root hypoxia.
- **Marathi (मराठी):**
  - *Summary:* तातडीचे: झोन Zone E मध्ये 3 टप्प्यांत विभागून (73.33 mm, 73.33 mm, 73.34 mm) एकूण 220.00 मिमी सिंचन आवश्यक आहे (निव्वळ तुटवडा: 198.0 मिमी).
  - *Action Guidance:* 3 टप्प्यांत विभागून (73.33 mm, 73.33 mm, 73.34 mm) एकूण 220.00 मिमी पाणी द्या. एकाच वेळी संपूर्ण 220.00 मिमी पाणी देणे टाळा.
- **Hindi (हिंदी):**
  - *Summary:* आपातकालीन: ज़ोन Zone E में 3 चरणों में विभाजित (73.33 mm, 73.33 mm, 73.34 mm) कुल 220.00 मिमी सिंचाई आवश्यक है (शुद्ध मांग: 198.0 मिमी).
  - *Action Guidance:* 3 चरणों में विभाजित (73.33 mm, 73.33 mm, 73.34 mm) कुल 220.00 मिमी पानी लगाएं। एक ही बार में पूरा 220.00 मिमी पानी न दें।

---

## Scenario 6: Modelled Soil Moisture (Reanalysis Provenance Isolation)

- **Scenario Identifier:** `DEMO-SCENARIO-06-MODELLED-SOIL`
- **Objective:** Verify that gridded soil moisture from weather NWP models (Open-Meteo 0–7 cm layer) is strictly classified as `provider_modelled` and never misrepresented as an in-situ probe reading.
- **Evidence Source:** Actual Open-Meteo reanalysis payload.

### 1. Input Evidence
- **Weather Payload:** Open-Meteo hourly reanalysis for Baramati.
- **Modelled Moisture Reading:** `soil_moisture_0_to_7cm = 0.274 m³/m³`.
- **In-Situ Sensor:** None present.

### 2. Expected Outcomes
- **Ingestion Normalization:** Tagged as `ProvenanceType.PROVIDER_MODELLED`.
- **Database Persistence Metadata:**
  ```json
  {
    "depth_min_cm": 0.0,
    "depth_max_cm": 7.0,
    "provenance": "provider_modelled",
    "note": "Modelled reanalysis soil layer, NOT an in-situ field sensor measurement"
  }
  ```
- **Scientific Audit:** Explanations explicitly list: `"Soil moisture is derived from regional gridded reanalysis models, not an in-situ probe."`

---

## Scenario 7: Multilingual Integrity and Dialect Verification

- **Scenario Identifier:** `DEMO-SCENARIO-07-MULTILINGUAL-INTEGRITY`
- **Objective:** Verify 100% linguistic fidelity across Marathi, Hindi, and English across all 5 decision actions, verifying that no corrupted characters (e.g. `पुराSubवा`) exist and agricultural terminology is accurate.
- **Evidence Source:** Multi-action execution matrix.

### Verified Terminology Standards
| Concept | English | Marathi (मराठी) | Hindi (हिंदी) |
| :--- | :--- | :--- | :--- |
| **Gross Irrigation Depth** | Gross Irrigation Depth | एकूण सिंचन खोली | कुल सिंचाई गहराई |
| **Net Soil Water Deficit** | Net Soil Water Deficit | निव्वळ मातीतील पाण्याचा तुटवडा | शुद्ध मिट्टी जल कमी |
| **Split Application** | Split Application | टप्प्यांत विभागून सिंचन | चरणों में विभाजित सिंचाई |
| **Runoff Prevention** | Prevent Runoff Loss | पाण्याचा अपव्यय व निचरा टाळण्यासाठी | जल अपवाह रोकने हेतु |
| **Readily Available Water** | Readily Available Water (RAW) | सहज उपलब्ध पाणी मर्यादा (RAW) | सुलभ उपलब्ध जल सीमा (RAW) |
| **Soil Field Capacity** | Field Capacity | शेत धारणा क्षमता (Field Capacity) | खेत जलधारण क्षमता |
