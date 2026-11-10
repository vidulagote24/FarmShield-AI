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

export const DEMO_OBSERVATIONS_FIXTURE = [
  // --- Zone A Observations (Healthy) ---
  {
    id: "obs-a-sm-1",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z1-north-west-001",
    observation_type: "soil_moisture",
    source: "In-situ Capacitive Probe A1 (Depth 30cm)",
    observed_at: "2026-11-01T04:30:00Z",
    value: 74.0,
    unit: "%",
    metadata: { depth_cm: 30, sensor_id: "probe-a-01", quality_status: "good" }
  },
  {
    id: "obs-a-sm-2",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z1-north-west-001",
    observation_type: "soil_moisture",
    source: "In-situ Capacitive Probe A1 (Depth 30cm)",
    observed_at: "2026-11-03T04:30:00Z",
    value: 71.5,
    unit: "%",
    metadata: { depth_cm: 30, sensor_id: "probe-a-01", quality_status: "good" }
  },
  {
    id: "obs-a-sm-3",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z1-north-west-001",
    observation_type: "soil_moisture",
    source: "In-situ Capacitive Probe A1 (Depth 30cm)",
    observed_at: "2026-11-05T04:30:00Z",
    value: 69.2,
    unit: "%",
    metadata: { depth_cm: 30, sensor_id: "probe-a-01", quality_status: "good" }
  },
  {
    id: "obs-a-sm-4",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z1-north-west-001",
    observation_type: "soil_moisture",
    source: "In-situ Capacitive Probe A1 (Depth 30cm)",
    observed_at: "2026-11-07T04:30:00Z",
    value: 68.0,
    unit: "%",
    metadata: { depth_cm: 30, sensor_id: "probe-a-01", quality_status: "good" }
  },
  {
    id: "obs-a-vi-1",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z1-north-west-001",
    observation_type: "vegetation_index",
    source: "Copernicus Sentinel-2 L2A (10m)",
    observed_at: "2026-10-28T05:30:00Z",
    value: 0.72,
    unit: "NDVI",
    metadata: { cloud_cover_pct: 2.1, sensor: "MSI", quality_status: "good" }
  },
  {
    id: "obs-a-vi-2",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z1-north-west-001",
    observation_type: "vegetation_index",
    source: "Copernicus Sentinel-2 L2A (10m)",
    observed_at: "2026-11-02T05:30:00Z",
    value: 0.74,
    unit: "NDVI",
    metadata: { cloud_cover_pct: 1.5, sensor: "MSI", quality_status: "good" }
  },
  {
    id: "obs-a-vi-3",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z1-north-west-001",
    observation_type: "vegetation_index",
    source: "Copernicus Sentinel-2 L2A (10m)",
    observed_at: "2026-11-07T05:30:00Z",
    value: 0.74,
    unit: "NDVI",
    metadata: { cloud_cover_pct: 0.8, sensor: "MSI", quality_status: "good" }
  },

  // --- Zone B Observations (Monitor) ---
  {
    id: "obs-b-sm-1",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z2-north-east-002",
    observation_type: "soil_moisture",
    source: "In-situ Capacitive Probe B2 (Depth 30cm)",
    observed_at: "2026-11-01T04:30:00Z",
    value: 66.0,
    unit: "%",
    metadata: { depth_cm: 30, sensor_id: "probe-b-02", quality_status: "good" }
  },
  {
    id: "obs-b-sm-2",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z2-north-east-002",
    observation_type: "soil_moisture",
    source: "In-situ Capacitive Probe B2 (Depth 30cm)",
    observed_at: "2026-11-03T04:30:00Z",
    value: 62.4,
    unit: "%",
    metadata: { depth_cm: 30, sensor_id: "probe-b-02", quality_status: "good" }
  },
  {
    id: "obs-b-sm-3",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z2-north-east-002",
    observation_type: "soil_moisture",
    source: "In-situ Capacitive Probe B2 (Depth 30cm)",
    observed_at: "2026-11-05T04:30:00Z",
    value: 59.1,
    unit: "%",
    metadata: { depth_cm: 30, sensor_id: "probe-b-02", quality_status: "good" }
  },
  {
    id: "obs-b-sm-4",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z2-north-east-002",
    observation_type: "soil_moisture",
    source: "In-situ Capacitive Probe B2 (Depth 30cm)",
    observed_at: "2026-11-07T04:30:00Z",
    value: 56.0,
    unit: "%",
    metadata: { depth_cm: 30, sensor_id: "probe-b-02", quality_status: "good" }
  },
  {
    id: "obs-b-vi-1",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z2-north-east-002",
    observation_type: "vegetation_index",
    source: "Copernicus Sentinel-2 L2A (10m)",
    observed_at: "2026-10-28T05:30:00Z",
    value: 0.63,
    unit: "NDVI",
    metadata: { cloud_cover_pct: 3.2, sensor: "MSI", quality_status: "good" }
  },
  {
    id: "obs-b-vi-2",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z2-north-east-002",
    observation_type: "vegetation_index",
    source: "Copernicus Sentinel-2 L2A (10m)",
    observed_at: "2026-11-02T05:30:00Z",
    value: 0.61,
    unit: "NDVI",
    metadata: { cloud_cover_pct: 2.0, sensor: "MSI", quality_status: "good" }
  },
  {
    id: "obs-b-vi-3",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z2-north-east-002",
    observation_type: "vegetation_index",
    source: "Copernicus Sentinel-2 L2A (10m)",
    observed_at: "2026-11-07T05:30:00Z",
    value: 0.58,
    unit: "NDVI",
    metadata: { cloud_cover_pct: 1.1, sensor: "MSI", quality_status: "good" }
  },

  // --- Zone C Observations (Attention) ---
  {
    id: "obs-c-sm-1",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z3-south-west-003",
    observation_type: "soil_moisture",
    source: "In-situ Capacitive Probe C3 (Depth 30cm)",
    observed_at: "2026-11-01T04:30:00Z",
    value: 58.0,
    unit: "%",
    metadata: { depth_cm: 30, sensor_id: "probe-c-03", quality_status: "good" }
  },
  {
    id: "obs-c-sm-2",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z3-south-west-003",
    observation_type: "soil_moisture",
    source: "In-situ Capacitive Probe C3 (Depth 30cm)",
    observed_at: "2026-11-03T04:30:00Z",
    value: 52.5,
    unit: "%",
    metadata: { depth_cm: 30, sensor_id: "probe-c-03", quality_status: "good" }
  },
  {
    id: "obs-c-sm-3",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z3-south-west-003",
    observation_type: "soil_moisture",
    source: "In-situ Capacitive Probe C3 (Depth 30cm)",
    observed_at: "2026-11-05T04:30:00Z",
    value: 48.2,
    unit: "%",
    metadata: { depth_cm: 30, sensor_id: "probe-c-03", quality_status: "good" }
  },
  {
    id: "obs-c-sm-4",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z3-south-west-003",
    observation_type: "soil_moisture",
    source: "In-situ Capacitive Probe C3 (Depth 30cm)",
    observed_at: "2026-11-07T04:30:00Z",
    value: 46.0,
    unit: "%",
    metadata: { depth_cm: 30, sensor_id: "probe-c-03", quality_status: "good" }
  },
  {
    id: "obs-c-vi-1",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z3-south-west-003",
    observation_type: "vegetation_index",
    source: "Copernicus Sentinel-2 L2A (10m)",
    observed_at: "2026-10-28T05:30:00Z",
    value: 0.56,
    unit: "NDVI",
    metadata: { cloud_cover_pct: 2.8, sensor: "MSI", quality_status: "good" }
  },
  {
    id: "obs-c-vi-2",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z3-south-west-003",
    observation_type: "vegetation_index",
    source: "Copernicus Sentinel-2 L2A (10m)",
    observed_at: "2026-11-02T05:30:00Z",
    value: 0.50,
    unit: "NDVI",
    metadata: { cloud_cover_pct: 1.8, sensor: "MSI", quality_status: "good" }
  },
  {
    id: "obs-c-vi-3",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z3-south-west-003",
    observation_type: "vegetation_index",
    source: "Copernicus Sentinel-2 L2A (10m)",
    observed_at: "2026-11-07T05:30:00Z",
    value: 0.46,
    unit: "NDVI",
    metadata: { cloud_cover_pct: 1.0, sensor: "MSI", quality_status: "good" }
  },

  // --- Zone D Observations (Insufficient Data / Cloud Obscured) ---
  {
    id: "obs-d-vi-1",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z4-south-east-004",
    observation_type: "satellite",
    source: "Copernicus Sentinel-2 L2A (10m)",
    observed_at: "2026-11-07T05:30:00Z",
    value: null,
    unit: null,
    metadata: {
      cloud_cover_pct: 78.4,
      quality_status: "insufficient",
      note: "Scene rejected due to dense cloud obscuration (>60% threshold per AGENTS.md)"
    }
  }
];

export const DEMO_RECOMMENDATIONS_FIXTURE = [
  // --- Zone A Recommendation ---
  {
    id: "rec-a-01",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z1-north-west-001",
    recommendation_type: "irrigation",
    title: "सिंचनाची तातडीने गरज नाही (Adequate Soil Moisture)",
    title_en: "No Immediate Irrigation Required",
    description: "पिकाच्या मुळांच्या कार्यक्षेत्रात ६८% ओलावा शिल्लक असून पिकाची वाढ समाधानकारक आहे. पुढील ४८ तास सिंचन स्थगित ठेवावे.",
    description_en: "Root-zone soil moisture is adequate at 68% (well above 45% stress threshold). Defer irrigation for next 48 hours.",
    priority: "low",
    status: "pending",
    recommended_action: {
      action: "wait",
      recommended_window: "Next review on 2026-11-09"
    },
    reasoning: {
      factors: [
        "Soil moisture 68% (well above 45% critical management depletion)",
        "Canopy NDVI 0.74 indicates healthy vegetative biomass",
        "Forecast rainfall: 0 mm, Evapotranspiration: 4.2 mm/day"
      ],
      stress_status: "healthy",
      confidence: 0.94
    },
    generated_at: "2026-11-07T06:00:00Z",
    valid_until: "2026-11-09T06:00:00Z",
    created_at: "2026-11-07T06:00:00Z"
  },

  // --- Zone B Recommendation ---
  {
    id: "rec-b-02",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z2-north-east-002",
    recommendation_type: "irrigation",
    title: "सिंचन निरीक्षण सुरू ठेवा (Monitor Depletion Rate)",
    title_en: "Monitor Zone Soil Moisture Depletion",
    description: "मातीतील ओलावा ५६% पर्यंत खालावला आहे. ताण पातळी (४५%) जवळ येत असल्याने पुढील २४ ते ३६ तासांत निरीक्षण ठेवा.",
    description_en: "Soil moisture has declined to 56%. Monitor zone over next 24-36h as it approaches the 45% management threshold.",
    priority: "medium",
    status: "pending",
    recommended_action: {
      action: "monitor",
      recommended_window: "Check soil probe within 24 hours"
    },
    reasoning: {
      factors: [
        "Soil moisture declining (-10% in 6 days from 66% to 56%)",
        "NDVI slight decline 0.63 -> 0.58",
        "Reference ET0 4.6 mm/day"
      ],
      stress_status: "monitor",
      confidence: 0.88
    },
    generated_at: "2026-11-07T06:00:00Z",
    valid_until: "2026-11-08T18:00:00Z",
    created_at: "2026-11-07T06:00:00Z"
  },

  // --- Zone C Recommendation ---
  {
    id: "rec-c-03",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z3-south-west-003",
    recommendation_type: "irrigation",
    title: "तातडीने ठिबक सिंचन सुरू करा (Urgent Drip Irrigation Required)",
    title_en: "Urgent Drip Irrigation Recommended",
    description: "ओलावा ४६% वर पोहोचला असून गंभीर ताण पातळी (४५%) अगदी जवळ आहे. पिकाचे नुकसान टाळण्यासाठी सकाळी २२ मिमी (८३.६ घनमीटर) सिंचन द्यावे.",
    description_en: "Soil moisture has dropped to 46%, critical 45% threshold imminent. Apply 22mm (83.6 m³) via drip irrigation in morning hours.",
    priority: "high",
    status: "pending",
    recommended_action: {
      action: "irrigate",
      water_depth_mm: 22.0,
      water_volume_m3: 83.6,
      recommended_window: "सकाळी ०६:०० ते ०९:०० (Morning 06:00 - 09:00 AM)",
      irrigation_method: "Drip (ठिबक सिंचन)"
    },
    reasoning: {
      factors: [
        "Soil moisture 46% near 45% critical management depletion (MAD)",
        "NDVI declining trend (-18% from 0.56 to 0.46)",
        "High crop evapotranspiration (ETc = 4.8 mm/day)",
        "Zero rainfall recorded in the past 7 days"
      ],
      stress_status: "attention",
      stress_reasons: [
        "vegetation_trend_declining",
        "root_zone_depletion_approaching_threshold"
      ],
      confidence: 0.93
    },
    generated_at: "2026-11-07T06:00:00Z",
    valid_until: "2026-11-08T12:00:00Z",
    created_at: "2026-11-07T06:00:00Z"
  }
  // Note: Zone D intentionally has NO recommendations to test the honest "no recommendations" state!
];

export const DEMO_IRRIGATION_EVENTS_FIXTURE = [
  {
    id: "irrig-evt-001",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z3-south-west-003",
    zone_name: "Zone C (मध्य-दक्षिण विभाग)",
    irrigation_date: "2026-10-31T06:30:00Z",
    water_quantity: 75.0,
    water_unit: "cubic_meters",
    irrigation_method: "drip",
    notes: "सकाळच्या सत्रात ठिबक सिंचन २ तास चालवले (Morning drip cycle 2 hours)",
    created_at: "2026-10-31T08:45:00Z",
    is_simulated: true,
  },
  {
    id: "irrig-evt-002",
    farm_id: "f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b",
    zone_id: "z1-north-west-001",
    zone_name: "Zone A (उत्तर-पश्चिम विभाग)",
    irrigation_date: "2026-10-28T07:00:00Z",
    water_quantity: 65.0,
    water_unit: "cubic_meters",
    irrigation_method: "drip",
    notes: "नियमित साप्ताहिक पाणी पाळी (Routine scheduled watering)",
    created_at: "2026-10-28T09:15:00Z",
    is_simulated: true,
  }
];



