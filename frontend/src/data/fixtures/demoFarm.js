/**
 * FarmShield AI - Demonstration Farm and Management Zones GeoJSON Fixtures
 * 
 * Target: Baramati Demonstration Farm (Plot #4), Pune District, Maharashtra, India
 * Total Area: ~1.42 Hectares (~3.5 Acres)
 * Crop: Cotton (कापूस) · Sowing Date: 2026-10-01 (Vegetative Phase)
 * Coordinate Reference System: WGS84 / EPSG:4326 [Longitude, Latitude]
 * 
 * IMPORTANT: This fixture is strictly labelled as SIMULATED / DEMO DATA per AGENTS.md.
 */

export const DEMO_FARM_FIXTURE = {
  id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
  name: "आनंदराव शिंदे शेत (Plot #4)",
  name_en: "Anandrao Shinde Farm (Plot #4)",
  location_name: "बारामती, पुणे, महाराष्ट्र (Baramati, Pune, MH)",
  crop_type: "cotton",
  crop_variety: "Bt Cotton (अजित-१५५)",
  sowing_date: "2026-10-01",
  area_hectares: 1.42,
  area_acres: 3.5,
  is_simulated: true,
  last_updated: "2026-11-09T06:00:00Z",
  satellite_source: "Copernicus Sentinel-2 L2A (10m Multi-spectral)",
  satellite_date: "2026-11-07T05:30:00Z",
  weather_source: "Open-Meteo High-Resolution Ensemble (Agro-v1)",
  boundary: {
    type: "MultiPolygon",
    coordinates: [
      [
        [
          [74.5780, 18.1500],
          [74.5840, 18.1500],
          [74.5840, 18.1580],
          [74.5780, 18.1580],
          [74.5780, 18.1500]
        ]
      ]
    ]
  }
};

export const DEMO_ZONES_FIXTURE = [
  {
    id: "z1-north-west-001",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_name: "Zone A (उत्तर-पश्चिम विभाग / North-West)",
    zone_code: "ZA-01",
    area_hectares: 0.36,
    area_acres: 0.89,
    status: "healthy", // healthy | monitor | attention | high_stress | insufficient_data
    crop_stage: "शाकीय वाढ (Vegetative)",
    ndvi_value: 0.74,
    ndvi_trend: "stable",
    soil_moisture_pct: 68,
    soil_type: "काळी कसदार माती (Deep Black Soil)",
    irrigation_need: "none",
    action_code: "no_action_indicated",
    last_observed_at: "2026-11-07T05:30:00Z",
    evidence_source: "Sentinel-2 L2A (NDVI)",
    reason_summary: "कॅनॉपी निर्देशांक निरोगी (NDVI: 0.74). मुळांच्या क्षेत्रात ६८% ओलावा शिल्लक असून पाण्याचा कोणताही ताण नाही.",
    boundary: {
      type: "Polygon",
      coordinates: [
        [
          [74.5782, 18.1542],
          [74.5808, 18.1542],
          [74.5808, 18.1578],
          [74.5782, 18.1578],
          [74.5782, 18.1542]
        ]
      ]
    }
  },
  {
    id: "z2-north-east-002",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_name: "Zone B (उत्तर-पूर्व विभाग / North-East)",
    zone_code: "ZB-02",
    area_hectares: 0.34,
    area_acres: 0.84,
    status: "monitor",
    crop_stage: "शाकीय वाढ (Vegetative)",
    ndvi_value: 0.58,
    ndvi_trend: "slight_decline",
    soil_moisture_pct: 56,
    soil_type: "मध्यम काळी माती (Medium Black Loam)",
    irrigation_need: "monitor",
    action_code: "monitor",
    last_observed_at: "2026-11-07T05:30:00Z",
    evidence_source: "Sentinel-2 L2A (NDVI)",
    reason_summary: "ओलावा ५६% पर्यंत उतरला आहे; पुढील २४ ते ३६ तासांत निरीक्षण करून सिंचनाचा निर्णय घ्यावा.",
    boundary: {
      type: "Polygon",
      coordinates: [
        [
          [74.5812, 18.1542],
          [74.5838, 18.1542],
          [74.5838, 18.1578],
          [74.5812, 18.1578],
          [74.5812, 18.1542]
        ]
      ]
    }
  },
  {
    id: "z3-south-west-003",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_name: "Zone C (मध्य-दक्षिण विभाग / Central-South)",
    zone_code: "ZC-03",
    area_hectares: 0.38,
    area_acres: 0.94,
    status: "attention",
    crop_stage: "शाकीय वाढ (Vegetative)",
    ndvi_value: 0.46,
    ndvi_trend: "declining",
    soil_moisture_pct: 46,
    soil_type: "हलकी तांबडी माती (Shallow Sandy Loam)",
    irrigation_need: "urgent_review",
    action_code: "inspect",
    last_observed_at: "2026-11-07T05:30:00Z",
    evidence_source: "Sentinel-2 L2A + FAO-56 Depletion Model",
    reason_summary: "पिकाच्या ताण पातळी (४५%) जवळ ओलावा आला आहे. झाडांची पाने कोमेजण्याची चिन्हे असल्याने प्रत्यक्ष शेतात तपासणी आवश्यक.",
    boundary: {
      type: "Polygon",
      coordinates: [
        [
          [74.5782, 18.1502],
          [74.5808, 18.1502],
          [74.5808, 18.1538],
          [74.5782, 18.1538],
          [74.5782, 18.1502]
        ]
      ]
    }
  },
  {
    id: "z4-south-east-004",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_name: "Zone D (दक्षिण विभाग / South Sector)",
    zone_code: "ZD-04",
    area_hectares: 0.34,
    area_acres: 0.84,
    status: "insufficient_data",
    crop_stage: "शाकीय वाढ (Vegetative)",
    ndvi_value: null,
    ndvi_trend: "unknown",
    soil_moisture_pct: null,
    soil_type: "काळी माती (Black Soil)",
    irrigation_need: "insufficient_data",
    action_code: "insufficient_data",
    last_observed_at: null,
    evidence_source: "Unavailable (Cloud Contamination >60%)",
    reason_summary: "उपग्रह दृश्यात ढगांचे आच्छादन असल्याने दृश्यमान निर्देशांक उपलब्ध नाहीत. सुरक्षिततेसाठी शेतात भेट देऊन ओलावा तपासा.",
    boundary: {
      type: "Polygon",
      coordinates: [
        [
          [74.5812, 18.1502],
          [74.5838, 18.1502],
          [74.5838, 18.1538],
          [74.5812, 18.1538],
          [74.5812, 18.1502]
        ]
      ]
    }
  }
];
