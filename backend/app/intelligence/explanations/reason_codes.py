"""Deterministic registry and multilingual resolver for intelligence reason codes.

Covers:
1. Phase 5 DecisionReasonCode (evidence validation, action determination, forecast policies,
   efficiency provenance, split applications, priority classifications, non-watering flags).
2. Phase 4 StressReasonCode (water, vegetation, weather, and soil domains).
3. Fallback for unrecognized codes preserving traceability without data fabrication.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from backend.app.intelligence.decision.types import DecisionReasonCode
from backend.app.intelligence.explanations.types import ExplanationLanguage, ReasonCodeExplanation
from backend.app.intelligence.stress.scoring import StressReasonCode


class AgronomyReasonCode(str, Enum):
    """Agronomic and water-balance diagnostic limitation codes from Phase 3."""

    AGRONOMY_ET0_MISSING = "AGRONOMY_ET0_MISSING"
    AGRONOMY_CROP_COEFFICIENT_MISSING = "AGRONOMY_CROP_COEFFICIENT_MISSING"
    AGRONOMY_INITIAL_SOIL_MOISTURE_MISSING = "AGRONOMY_INITIAL_SOIL_MOISTURE_MISSING"
    AGRONOMY_EFFECTIVE_RAINFALL_MISSING = "AGRONOMY_EFFECTIVE_RAINFALL_MISSING"
    AGRONOMY_INVALID_SOIL_PROPERTIES = "AGRONOMY_INVALID_SOIL_PROPERTIES"
    AGRONOMY_PROVISIONAL_EMPIRICAL_RAINFALL = "AGRONOMY_PROVISIONAL_EMPIRICAL_RAINFALL"
    AGRONOMY_INSUFFICIENT_WATER_BALANCE = "AGRONOMY_INSUFFICIENT_WATER_BALANCE"
    AGRONOMY_INVALID_IRRIGATION_REQUIREMENT = "AGRONOMY_INVALID_IRRIGATION_REQUIREMENT"


# ==============================================================================
# REASON CODE REGISTRY
# ==============================================================================

_REASON_CODE_REGISTRY: Dict[str, Dict[str, Any]] = {
    # --------------------------------------------------------------------------
    # 1. Phase 5: Evidence Validation & Gating
    # --------------------------------------------------------------------------
    DecisionReasonCode.EVIDENCE_WATER_BALANCE_INSUFFICIENT.value: {
        "en": "Soil water balance data is missing or incomplete; an irrigation recommendation cannot be determined safely.",
        "mr": "मातीतील पाण्याचे संतुलन विषयक डेटा अपुरा किंवा उपलब्ध नाही; सिंचनाची शिफारस सुरक्षितपणे निश्चित करता येत नाही.",
        "hi": "मृदा जल संतुलन डेटा अपर्याप्त या उपलब्ध नहीं है; सिंचाई की सिफारिश सुरक्षित रूप से तय नहीं की जा सकती.",
        "tech": "Water balance computation missing required soil capacities, initial depletion, or daily ETc/precipitation inputs.",
        "refs": ["Dr", "RAW", "TAW"],
        "limits": ["Root-zone moisture deficit cannot be reliably computed without baseline soil hydraulic properties."],
    },
    DecisionReasonCode.EVIDENCE_WATER_BALANCE_STALE.value: {
        "en": "Soil water balance calculation exceeds the allowable freshness threshold (stale evidence).",
        "mr": "मातीतील पाण्याचे संतुलन जुने झाले असून मान्य कालमर्यादा ओलांडली आहे (कालबाह्य माहिती).",
        "hi": "मृदा जल संतुलन गणना स्वीकार्य समय सीमा से पुरानी हो गई है (कालातीत डेटा).",
        "tech": "Elapsed time since last water balance accounting cycle exceeds max_water_balance_age_days threshold.",
        "refs": ["as_of_time", "max_water_balance_age_days"],
        "limits": ["Stale soil water estimates do not reflect recent crop transpiration or unrecorded rain."],
    },
    DecisionReasonCode.EVIDENCE_WATER_BALANCE_SUSPECT.value: {
        "en": "Soil water balance evidence shows physical anomalies or measurement contradictions.",
        "mr": "मातीतील पाण्याच्या संतुलनात विसंगती किंवा मापनातील त्रुटी आढळल्या आहेत.",
        "hi": "मृदा जल संतुलन डेटा में भौतिक विसंगतियाँ या माप में विरोधाभास देखा गया है.",
        "tech": "Quality status is SUSPECT or internal physical bounds violated (e.g. Dr > TAW, negative runoff).",
        "refs": ["quality_status", "Dr", "TAW"],
        "limits": ["Requires instrument inspection or recalibration before making volumetric commitments."],
    },
    DecisionReasonCode.EVIDENCE_SOIL_CAPACITY_MISSING.value: {
        "en": "Soil hydraulic capacity properties (Field Capacity, Wilting Point) are missing for this zone.",
        "mr": "या झोनसाठी मातीची जलधारण क्षमता (शेत क्षमता, म्लानी बिंदू) उपलब्ध नाही.",
        "hi": "इस ज़ोन के लिए मृदा जल धारण क्षमता (खेत क्षमता, म्लानि बिंदु) उपलब्ध नहीं है.",
        "tech": "SoilWaterCapacities missing field_capacity_m3_m3 or wilting_point_m3_m3; TAW and RAW cannot be derived.",
        "refs": ["theta_FC", "theta_WP", "TAW", "RAW"],
        "limits": ["Default soil moisture assumptions are strictly prohibited per scientific rules."],
    },
    DecisionReasonCode.EVIDENCE_PROVISIONAL_RAINFALL_BLOCKED.value: {
        "en": "Provisional empirical rainfall mode is blocked without explicit operator opt-in.",
        "mr": "स्पष्ट संमतीशिवाय तात्पुरती अनुभवजन्य पाऊस पद्धती अवरोधित केली आहे.",
        "hi": "स्पष्ट ऑपरेटर सहमति के बिना अनंतिम अनुभवजन्य वर्षा पद्धति अवरुद्ध है.",
        "tech": "Water balance used empirical effective rainfall without allow_provisional_empirical_rainfall opt-in flag.",
        "refs": ["is_provisional_empirical", "allow_provisional_empirical_rainfall"],
        "limits": ["Empirical USDA/FAO effective rainfall formulas require local calibration before automated use."],
    },
    DecisionReasonCode.EVIDENCE_INPUTS_VALID.value: {
        "en": "All required physical and agronomic inputs are valid and verified.",
        "mr": "सर्व आवश्यक भौतिक व कृषी विषयक माहिती वैध आणि सत्यापित आहे.",
        "hi": "सभी आवश्यक भौतिक और कृषि संबंधी इनपुट मान्य और सत्यापित हैं.",
        "tech": "Water balance, crop parameters, and soil hydraulic properties passed all gating validation tests.",
        "refs": ["Dr", "RAW", "TAW", "Ks"],
        "limits": [],
    },

    # --------------------------------------------------------------------------
    # 2. Phase 5: Action Determination
    # --------------------------------------------------------------------------
    DecisionReasonCode.ACTION_IRRIGATE_DEPLETION_EXCEEDS_RAW.value: {
        "en": "Root-zone water depletion has reached or exceeded the Readily Available Water (RAW) management limit.",
        "mr": "मुळांच्या भागातील पाण्याचा तुटवडा सुलभ उपलब्ध पाण्याच्या (RAW) मर्यादेपर्यंत किंवा त्याहून पुढे पोहोचला आहे.",
        "hi": "जड़ क्षेत्र में पानी की कमी सुलभ उपलब्ध जल (RAW) सीमा तक या उससे अधिक हो गई है.",
        "tech": "Dr >= RAW (FAO-56 Eq. 84). Soil water has depleted past the non-stress threshold; refill required.",
        "refs": ["Dr", "RAW"],
        "limits": ["Timing assumes uniform root extraction across the active rooting depth."],
    },
    DecisionReasonCode.ACTION_IRRIGATE_KS_STRESS_ACTIVE.value: {
        "en": "Crop is experiencing water stress; transpiration is reduced below potential (Ks < 1.00).",
        "mr": "पिकावर पाण्याचा ताण आला असून बाष्पोत्सर्जन सामान्य क्षमतेपेक्षा कमी झाले आहे (Ks < १.००).",
        "hi": "फसल पर जल तनाव सक्रिय है; वाष्पोत्सर्जन सामान्य क्षमता से कम हो गया है (Ks < 1.00).",
        "tech": "Transpiration reduction coefficient Ks = (TAW - Dr) / (TAW - RAW) < 1.00, reducing actual ETc,adj.",
        "refs": ["Ks", "ETc", "ETc_adj"],
        "limits": ["Prolonged Ks < 1.0 reduces stomatal conductance and biomass accumulation."],
    },
    DecisionReasonCode.ACTION_IRRIGATE_WILTING_POINT_HAZARD.value: {
        "en": "Severe moisture depletion approaching or at the permanent wilting point; acute risk of irreversible crop damage.",
        "mr": "पाण्याची अत्यंत तीव्र कमतरता पिकाच्या कायमस्वरूपी मुरझण्याच्या उंबरठ्यावर आहे; पिकाचे अपरिवर्तनीय नुकसान होण्याचा धोका आहे.",
        "hi": "अत्यधिक जल संकट जो स्थायी म्लानि बिंदु तक पहुँच गया है; फसल के स्थायी नुकसान का गंभीर खतरा है.",
        "tech": "Dr >= TAW or Ks <= 0.20, indicating plant available soil water is virtually exhausted in the active root zone.",
        "refs": ["Dr", "TAW", "Ks"],
        "limits": ["Plant survival requires immediate wetting; yield loss has likely initiated."],
    },
    DecisionReasonCode.ACTION_IRRIGATE_EMERGENCY_OVERRIDE.value: {
        "en": "Emergency irrigation override triggered due to severe root-zone deficit, taking precedence over weather delays.",
        "mr": "गंभीर पाणी टंचाईमुळे तातडीचे सिंचन लागू करण्यात आले आहे, जे हवामानाच्या विलंबावर प्राधान्य घेते.",
        "hi": "गंभीर जल संकट के कारण आपातकालीन सिंचाई लागू की गई है, जो मौसम के पूर्वानुमान से अधिक प्राथमिकता रखती है.",
        "tech": "Precedence 2 emergency override fired; bypasses weather forecast delay and redistribution deferral.",
        "refs": ["Dr", "TAW", "Ks"],
        "limits": ["Applied only under acute wilting point threat to preserve canopy viability."],
    },
    DecisionReasonCode.ACTION_MONITOR_APPROACHING_RAW.value: {
        "en": "Root-zone water depletion is approaching the management threshold; continue monitoring.",
        "mr": "मुळांच्या भागातील पाण्याचा तुटवडा निर्धारित मर्यादेजवळ पोहोचत आहे; नियमित निरीक्षण सुरू ठेवा.",
        "hi": "जड़ क्षेत्र में पानी की कमी प्रबंधन सीमा के निकट पहुँच रही है; निगरानी जारी रखें.",
        "tech": "Dr >= raw_approach_threshold_fraction * RAW (default 80% RAW). Soil water remains readily available (Ks = 1.0).",
        "refs": ["Dr", "RAW"],
        "limits": ["No immediate irrigation necessary; depletion should be checked daily."],
    },
    DecisionReasonCode.ACTION_MONITOR_SENSITIVE_STAGE.value: {
        "en": "Crop is in a moisture-sensitive growth stage; active monitoring triggered at an earlier threshold.",
        "mr": "पीक पाणी-संवेदनशील वाढीच्या अवस्थेत आहे; कमी पाण्याच्या तुटवड्यावरच सक्रिय निरीक्षण सुरू केले आहे.",
        "hi": "फसल पानी के प्रति संवेदनशील वृद्धि चरण में है; कम जल स्तर पर ही सक्रिय निगरानी शुरू की गई है.",
        "tech": "Crop growth stage matches sensitive phenology list; monitoring threshold lowered to 70% RAW.",
        "refs": ["growth_stage", "Dr", "RAW"],
        "limits": ["Drought stress during flowering/pod-fill causes permanent flower abortion."],
    },
    DecisionReasonCode.ACTION_MONITOR_DEFICIT_BELOW_MIN_DEPTH.value: {
        "en": "Root-zone deficit is below the minimum economical application depth; irrigation is deferred under monitoring.",
        "mr": "पाण्याची कमतरता किमान किफायतशीर सिंचन खोलीपेक्षा कमी आहे; निरीक्षणाखाली पाणी देणे पुढे ढकलले आहे.",
        "hi": "पानी की कमी न्यूनतम किफायती सिंचाई गहराई से कम है; निगरानी के तहत सिंचाई स्थगित की गई है.",
        "tech": "Dr >= RAW but Dr < min_economical_depth_mm (e.g. 5.0 mm). Wetting losses would exceed agronomic benefit.",
        "refs": ["Dr", "min_economical_depth_mm"],
        "limits": ["Operational rule prevents frequent shallow wetting events with excessive surface evaporation."],
    },
    DecisionReasonCode.ACTION_DELAY_FORECAST_RAIN.value: {
        "en": "Irrigation is delayed due to an actionable rainfall forecast expected to relieve the root-zone deficit.",
        "mr": "पाण्याचा तुटवडा भरून काढणारा अंदाज वर्तवण्यात आल्यामुळे सिंचन पुढे ढकलण्यात आले आहे.",
        "hi": "पर्याप्त वर्षा के पूर्वानुमान के कारण सिंचाई स्थगित की गई है जो जड़ क्षेत्र की कमी को पूरा करेगी.",
        "tech": "Forecast precipitation meets probability, depth, and onset timing criteria before crop stress onset.",
        "refs": ["forecast_precipitation_mm", "forecast_probability", "expected_rainfall_start"],
        "limits": ["Based on numerical weather prediction; reassessment mandatory at scheduled timestamp."],
    },
    DecisionReasonCode.ACTION_DELAY_RECENT_IRRIGATION.value: {
        "en": "Irrigation is delayed because the zone was recently irrigated and soil moisture is currently redistributing.",
        "mr": "या झोनमध्ये नुकतेच सिंचन करण्यात आल्याने आणि जमिनीत पाणी पाझरण्याची क्रिया सुरू असल्याने सिंचन पुढे ढकलले आहे.",
        "hi": "हाल ही में सिंचाई किए जाने और मिट्टी में जल पुनर्वितरण जारी रहने के कारण सिंचाई स्थगित की गई है.",
        "tech": "Elapsed time since last irrigation < redistribution_hours (typically 24h). Gravitational water is still moving.",
        "refs": ["last_irrigated_at", "redistribution_hours"],
        "limits": ["Sensor readings during redistribution do not reflect stable field capacity matric potential."],
    },
    DecisionReasonCode.ACTION_NO_ACTION_ROOT_ZONE_HEALTHY.value: {
        "en": "Root-zone moisture is optimal and well within readily available limits; no irrigation is needed.",
        "mr": "मुळांच्या भागात पुरेसा ओलावा असून पाणी सुलभ उपलब्ध मर्यादेत आहे; सिंचनाची आवश्यकता नाही.",
        "hi": "जड़ क्षेत्र में पर्याप्त नमी है और जल स्तर सुलभ सीमा के भीतर है; सिंचाई की आवश्यकता नहीं है.",
        "tech": "Dr < 0.80 * RAW and Ks = 1.00. Transpiration is completely unconstrained; soil profile is well-watered.",
        "refs": ["Dr", "RAW", "Ks"],
        "limits": ["Healthy state verified from physical soil-water evidence."],
    },

    # --------------------------------------------------------------------------
    # 3. Phase 5: Forecast Policies
    # --------------------------------------------------------------------------
    DecisionReasonCode.FORECAST_PROBABILITY_BELOW_THRESHOLD.value: {
        "en": "Forecast precipitation probability is below the confidence threshold for delaying irrigation.",
        "mr": "पाऊस पडण्याची अंदाजित शक्यता सिंचन पुढे ढकलण्यासाठी आवश्यक असलेल्या मर्यादेपेक्षा कमी आहे.",
        "hi": "वर्षा के पूर्वानुमान की संभावना सिंचाई स्थगित करने के लिए आवश्यक सीमा से कम है.",
        "tech": "forecast_probability < config.forecast_probability_threshold (e.g. 70%). Risk of missing rain too high.",
        "refs": ["forecast_probability", "probability_threshold"],
        "limits": ["Provisional rain cannot justify withholding irrigation when precipitation confidence is low."],
    },
    DecisionReasonCode.FORECAST_EVIDENCE_STALE.value: {
        "en": "Weather forecast model run exceeds freshness threshold; forecast delay cannot be applied.",
        "mr": "हवामान अंदाज जुना झाला आहे; सिंचन पुढे ढकलण्यासाठी हा अंदाज वापरता येत नाही.",
        "hi": "मौसम पूर्वानुमान डेटा पुराना हो गया है; पूर्वानुमानित स्थगन लागू नहीं किया जा सकता.",
        "tech": "Forecast issue age exceeds max_forecast_age_hours (default 24h). Stale NWP guidance cannot be trusted.",
        "refs": ["issue_time", "max_forecast_age_hours"],
        "limits": ["Fresh NWP model run required to evaluate rainfall timing."],
    },
    DecisionReasonCode.FORECAST_EVIDENCE_INVALID.value: {
        "en": "Forecast weather evidence is structurally invalid or contains out-of-bound values.",
        "mr": "हवामान अंदाजाची माहिती अवैध आहे किंवा त्यामध्ये विसंगत मूल्ये आहेत.",
        "hi": "मौसम पूर्वानुमान डेटा अमान्य है या इसमें असंगत मान शामिल हैं.",
        "tech": "Negative precipitation, invalid probability > 1.0, or negative forecast period encountered.",
        "refs": ["forecast_precipitation_mm", "forecast_period_hours"],
        "limits": ["Corrupt forecast records are rejected by evidence validation."],
    },
    DecisionReasonCode.FORECAST_EFFECTIVE_RAINFALL_EVALUATED.value: {
        "en": "Forecast rainfall was evaluated using verified infiltration and runoff models.",
        "mr": "सत्यापित जिरप आणि वाहून जाण्याच्या पद्धतींद्वारे अंदाजित पावसाचे मूल्यांकन केले गेले.",
        "hi": "सत्यापित अंतःस्रवण और अपवाह मॉडल का उपयोग करके पूर्वानुमानित वर्षा का मूल्यांकन किया गया.",
        "tech": "forecast_effective_rainfall_mm derived using documented infiltration method and compared against Dr.",
        "refs": ["forecast_effective_rainfall_mm", "effective_rainfall_method"],
        "limits": [],
    },
    DecisionReasonCode.FORECAST_INSUFFICIENT_DEFICIT_RELIEF.value: {
        "en": "Forecast effective rainfall is insufficient to relieve the root-zone deficit below the management limit.",
        "mr": "अंदाजित पाऊस पाण्याचा तुटवडा सुरक्षित मर्यादेच्या खाली आणण्यासाठी अपुरा आहे.",
        "hi": "पूर्वानुमानित प्रभावी वर्षा जड़ क्षेत्र की कमी को प्रबंधन सीमा से नीचे लाने के लिए अपर्याप्त है.",
        "tech": "Projected depletion after rainfall (Dr - Peff) >= RAW; zone would remain in stress zone without irrigation.",
        "refs": ["Dr", "forecast_effective_rainfall_mm", "RAW"],
        "limits": ["Irrigation cannot be deferred when expected precipitation leaves the root zone in active deficit."],
    },
    DecisionReasonCode.FORECAST_DEFERRAL_PROVISIONAL_POLICY.value: {
        "en": "Provisional forecast-deferral policy applied based on raw precipitation; reassessment scheduled.",
        "mr": "कच्च्या पावसाच्या अंदाजावर आधारित तात्पुरते सिंचन पुढे ढकलण्याचे धोरण लागू; पुनर्परीक्षण निर्धारित.",
        "hi": "अनुमानित कुल वर्षा के आधार पर अनंतिम स्थगन नीति लागू की गई; पुनर्मूल्यांकन निर्धारित.",
        "tech": "Provisional deferral applied with Dr < RAW, verified onset < stress onset, and explicit opt-in.",
        "refs": ["forecast_precipitation_mm", "forecast_reassessment_timestamp"],
        "limits": ["In-situ infiltration uncalibrated; requires mandatory 12-hour reassessment."],
    },
    DecisionReasonCode.FORECAST_RAINFALL_AFTER_STRESS.value: {
        "en": "Forecast rainfall arrives after projected crop stress onset; deferral denied to protect the crop.",
        "mr": "पिकावर ताण येण्यानंतर पाऊस पडण्याचा अंदाज असल्याने पिकाचे रक्षण करण्यासाठी सिंचन पुढे ढकलणे नाकारले.",
        "hi": "फसल पर तनाव आने के बाद वर्षा का पूर्वानुमान है; फसल की सुरक्षा के लिए सिंचाई स्थगन अस्वीकार किया गया.",
        "tech": "Rainfall onset (t_rain) >= stress onset (t_stress) where t_stress = (RAW - Dr) / r_ETc. Deferral blocked.",
        "refs": ["rainfall_onset_hours", "stress_onset_hours", "dr_at_rainfall_onset_mm"],
        "limits": ["Withholding water would induce crop water stress before atmospheric precipitation arrives."],
    },
    DecisionReasonCode.FORECAST_ETC_EVALUATED.value: {
        "en": "Forecast crop evapotranspiration (ETc) was evaluated over the lookahead horizon.",
        "mr": "पुढील कालावधीसाठी पिकाच्या बाष्पोत्सर्जनाचा (ETc) अंदाज तपासला गेला आहे.",
        "hi": "आगामी अवधि के लिए फसल वाष्पोत्सर्जन (ETc) का मूल्यांकन किया गया.",
        "tech": "Cumulative forecast ETc used to compute hourly water consumption rate r_ETc over valid window.",
        "refs": ["forecast_etc_mm", "forecast_etc_period_hours", "forecast_etc_rate_mm_per_hour"],
        "limits": ["Uniform rate is an operational approximation; diurnal solar variation is not resolved."],
    },
    DecisionReasonCode.FORECAST_ETC_MISSING.value: {
        "en": "Forecast crop evapotranspiration (ETc) is missing; stress onset projection cannot be determined.",
        "mr": "पिकाच्या बाष्पोत्सर्जनाचा (ETc) अंदाज उपलब्ध नाही; ताण येण्याची वेळ निश्चित करता येत नाही.",
        "hi": "फसल वाष्पोत्सर्जन (ETc) पूर्वानुमान उपलब्ध नहीं है; तनाव प्रारंभ समय का अनुमान नहीं लगाया जा सकता.",
        "tech": "forecast_etc_mm is None. Rate cannot be assumed 0.0; safe deferral cannot be mathematically proven.",
        "refs": ["forecast_etc_mm"],
        "limits": ["Provisional forecast deferral is strictly blocked without valid ETc evidence."],
    },
    DecisionReasonCode.FORECAST_ETC_WINDOW_INSUFFICIENT.value: {
        "en": "Forecast ETc validity window does not cover the interval until rainfall onset; extrapolation is prohibited.",
        "mr": "बाष्पोत्सर्जनाची वैधता खिडकी पावसाच्या वेळेपर्यंत पुरेशी नाही; मर्यादेपलीकडे अंदाज बांधणे प्रतिबंधित आहे.",
        "hi": "वाष्पोत्सर्जन वैधता खिड़की वर्षा के समय तक पूरी नहीं है; सीमा से परे अनुमान लगाना प्रतिबंधित है.",
        "tech": "ETc valid_to < rainfall onset or valid_from > decision time. Extrapolating uniform rate is mathematically invalid.",
        "refs": ["forecast_etc_valid_from", "forecast_etc_valid_to", "expected_rainfall_start"],
        "limits": ["Uniform ETc rate cannot be extended beyond the provider-reported validity window."],
    },
    DecisionReasonCode.FORECAST_PREVENTS_STRESS.value: {
        "en": "Forecast rainfall will arrive before stress onset and replenish root-zone water content.",
        "mr": "पिकावर ताण येण्यापूर्वीच पाऊस पडेल आणि मुळांमधील ओलावा पूर्ववत होईल.",
        "hi": "तनाव आने से पहले वर्षा होगी और जड़ क्षेत्र की नमी बहाल हो जाएगी.",
        "tech": "Verified that t_rain < t_stress and Dr at rain onset < RAW, ensuring safe zero-stress deferral.",
        "refs": ["dr_at_rainfall_onset_mm", "RAW"],
        "limits": [],
    },
    DecisionReasonCode.FORECAST_PROVISIONAL_BLOCKED_ACTIVE_DEFICIT.value: {
        "en": "Provisional forecast deferral is blocked because root-zone depletion is already at or beyond RAW.",
        "mr": "मुळांमधील पाण्याचा तुटवडा आधीच मर्यादेपलीकडे गेल्याने कच्च्या अंदाजावर सिंचन पुढे ढकलणे अवरोधित केले आहे.",
        "hi": "जड़ क्षेत्र में पानी की कमी पहले से ही सीमा पार होने के कारण अनंतिम स्थगन अवरुद्ध कर दिया गया है.",
        "tech": "Dr >= RAW during provisional evaluation. Unverified gross precipitation cannot defer active deficit irrigation.",
        "refs": ["Dr", "RAW"],
        "limits": ["Active plant water stress must be alleviated immediately unless verified effective rainfall is guaranteed."],
    },
    DecisionReasonCode.FORECAST_PROVISIONAL_OPT_IN_REQUIRED.value: {
        "en": "Provisional forecast deferral based on raw precipitation requires explicit operator opt-in.",
        "mr": "कच्च्या पावसाच्या अंदाजावर आधारित तात्पुरते सिंचन पुढे ढकलण्यासाठी ऑपरेटरची स्पष्ट संमती आवश्यक आहे.",
        "hi": "कच्चे वर्षा पूर्वानुमान पर अनंतिम स्थगन के लिए ऑपरेटर की स्पष्ट सहमति आवश्यक है.",
        "tech": "allow_provisional_forecast_deferral is False (default). Conservative policy disallows raw precipitation delays.",
        "refs": ["allow_provisional_forecast_deferral"],
        "limits": ["Opt-in must be configured explicitly in decision engine configuration."],
    },

    # --------------------------------------------------------------------------
    # 4. Phase 5: Efficiency Provenance & Split Application
    # --------------------------------------------------------------------------
    DecisionReasonCode.EFFICIENCY_MEASURED.value: {
        "en": "Application efficiency was empirically verified through an in-situ field measurement or distribution audit.",
        "mr": "सिंचन कार्यक्षमता प्रत्यक्ष शेतातील मापन किंवा वितरण ऑडिटद्वारे सत्यापित केली आहे.",
        "hi": "सिंचाई दक्षता को प्रत्यक्ष इन-सीटू फील्ड माप या वितरण ऑडिट के माध्यम से सत्यापित किया गया है.",
        "tech": "Efficiency backed by EfficiencyVerificationRecord with verified status and supporting audit reference.",
        "refs": ["application_efficiency", "efficiency_verification"],
        "limits": [],
    },
    DecisionReasonCode.EFFICIENCY_PROVISIONAL_ASSUMPTION.value: {
        "en": "Application efficiency is an uncalibrated default assumption based on irrigation system type.",
        "mr": "सिंचन कार्यक्षमता ही सिंचन प्रकारावर आधारित केवळ अंदाजित गृहीतक आहे.",
        "hi": "सिंचाई दक्षता सिंचाई प्रणाली के प्रकार पर आधारित केवल एक अनंतिम डिफ़ॉल्ट अनुमान है.",
        "tech": "application_efficiency_provenance is ASSUMED_DEFAULT (e.g. drip=0.90, sprinkler=0.75, surface=0.60).",
        "refs": ["application_efficiency", "irrigation_system_type"],
        "limits": ["Actual hardware wear, pressure variation, or clogged emitters may cause real efficiency to deviate."],
    },
    DecisionReasonCode.EFFICIENCY_PROVIDER_SOURCED.value: {
        "en": "Application efficiency was sourced from manufacturer equipment specifications without field audit.",
        "mr": "सिंचन कार्यक्षमता शेतातील तपासणीशिवाय उपकरण निर्मात्याच्या तपशीलावरून घेतली आहे.",
        "hi": "सिंचाई दक्षता इन-सीटू ऑडिट के बिना उपकरण निर्माता के विनिर्देशों से प्राप्त की गई है.",
        "tech": "Efficiency reported in equipment hardware catalog; in-field distribution uniformity was not tested.",
        "refs": ["application_efficiency", "PROVIDER_SOURCED"],
        "limits": ["Manufacturer specifications represent ideal new equipment performance."],
    },
    DecisionReasonCode.EFFICIENCY_OPERATOR_UNVERIFIED.value: {
        "en": "Application efficiency was entered by the operator without a supporting structured audit certificate.",
        "mr": "सिंचन कार्यक्षमता ऑपरेटरने प्रविष्ट केली आहे परंतु त्याचे अधिकृत ऑडिट प्रमाणपत्र नाही.",
        "hi": "सिंचाई दक्षता ऑपरेटर द्वारा दर्ज की गई है लेकिन इसका कोई ऑडिट प्रमाणपत्र संलग्न नहीं है.",
        "tech": "Efficiency entered manually by user; lacks formal in-situ test report reference.",
        "refs": ["application_efficiency", "OPERATOR_ENTERED"],
        "limits": ["Treated as provisional until verified by distribution uniformity test."],
    },
    DecisionReasonCode.EFFICIENCY_UNKNOWN_WITHHELD.value: {
        "en": "Application efficiency is unknown; gross application depth and volume cannot be calculated.",
        "mr": "सिंचन कार्यक्षमता माहित नाही; एकूण सिंचन खोली आणि पाण्याचे प्रमाण मोजता येत नाही.",
        "hi": "सिंचाई दक्षता अज्ञात है; कुल सिंचाई गहराई और मात्रा की गणना नहीं की जा सकती.",
        "tech": "application_efficiency is None; gross depth d_gross = d_net / eta cannot be evaluated without inventing eta.",
        "refs": ["net_irrigation_depth_mm", "application_efficiency"],
        "limits": ["Net refill depth d_net is reported independently to preserve soil moisture truth."],
    },
    DecisionReasonCode.ACTION_IRRIGATE_SPLIT_APPLICATION_REQUIRED.value: {
        "en": "Gross depth exceeds the maximum single-application intake threshold; split irrigation cycles are required.",
        "mr": "एकूण खोली एका वेळेच्या कमाल मर्यादेपेक्षा जास्त आहे; विभागून सिंचन करणे आवश्यक आहे.",
        "hi": "कुल गहराई एकल अनुप्रयोग की अधिकतम सीमा से अधिक है; विभाजित सिंचाई चक्र की आवश्यकता है.",
        "tech": "Gross depth > max_single_event_depth_mm. Scheduled into integer cycles conserving total mass exactly.",
        "refs": ["gross_irrigation_depth_mm", "split_event_count", "split_event_depths_mm"],
        "limits": ["Prevents surface ponding, excessive runoff, and deep percolation beyond root zone."],
    },
    DecisionReasonCode.WARNING_CONTRADICTORY_RECENT_IRRIGATION.value: {
        "en": "Warning: Zone was recorded as irrigated recently, but physical soil water balance indicates severe depletion. Potential emitter clog or sensor error.",
        "mr": "इशारा: झोनमध्ये नुकतेच सिंचन नोंदवले गेले आहे, तरीही मातीतील ओलावा तीव्र तुटवडा दर्शवतो. ड्रिपर चोक किंवा सेन्सर त्रुटी असण्याची शक्यता.",
        "hi": "चेतावनी: ज़ोन में हाल ही में सिंचाई दर्ज की गई थी, फिर भी मृदा जल संतुलन गंभीर कमी दर्शाता है. ड्रिपर रुकावट या सेंसर त्रुटि की संभावना.",
        "tech": "Contradiction detected: last_irrigated_at < 24h ago yet Dr >= TAW and Ks <= 0.20. Hardware audit recommended.",
        "refs": ["last_irrigated_at", "Dr", "TAW"],
        "limits": ["Physical soil moisture deficit takes emergency priority; immediate field inspection required."],
    },

    # --------------------------------------------------------------------------
    # 5. Phase 5: Priorities
    # --------------------------------------------------------------------------
    DecisionReasonCode.PRIORITY_CRITICAL_WILTING_POINT.value: {
        "en": "Priority CRITICAL: Active wilting point hazard requires immediate intervention.",
        "mr": "प्राधान्य अत्यंत तातडीचे: पीक मुरझण्याचा गंभीर धोका असल्याने त्वरित सिंचन आवश्यक.",
        "hi": "प्राथमिकता अत्यंत गंभीर: फसल मुरझाने का खतरा होने के कारण तुरंत सिंचाई आवश्यक.",
        "tech": "Assigned CRITICAL priority: permanent wilting hazard active (Dr >= TAW or Ks <= 0.20).",
        "refs": ["priority", "Ks"],
        "limits": [],
    },
    DecisionReasonCode.PRIORITY_CRITICAL_FLOWERING_DEFICIT.value: {
        "en": "Priority CRITICAL: Water deficit during flowering or critical yield formation stage.",
        "mr": "प्राधान्य अत्यंत तातडीचे: फुलधारणा किंवा दाणे भरण्याच्या संवेदनशील टप्प्यात पाण्याचा ताण.",
        "hi": "प्राथमिकता अत्यंत गंभीर: फूल आने या दाना भरने के संवेदनशील चरण में पानी की कमी.",
        "tech": "Assigned CRITICAL priority: active depletion during drought-sensitive phenological stage.",
        "refs": ["priority", "growth_stage"],
        "limits": [],
    },
    DecisionReasonCode.PRIORITY_HIGH_RAW_EXCEEDED.value: {
        "en": "Priority HIGH: Water depletion exceeds readily available limits with active transpiration reduction.",
        "mr": "प्राधान्य उच्च: पाण्याचा तुटवडा सुलभ मर्यादेबाहेर गेला असून बाष्पोत्सर्जनावर परिणाम झाला आहे.",
        "hi": "प्राथमिकता उच्च: पानी की कमी सुलभ सीमा से अधिक हो गई है और वाष्पोत्सर्जन प्रभावित है.",
        "tech": "Assigned HIGH priority: Dr >= RAW with Ks < 1.00.",
        "refs": ["priority", "Dr", "RAW"],
        "limits": [],
    },
    DecisionReasonCode.PRIORITY_HIGH_SENSITIVE_STAGE.value: {
        "en": "Priority HIGH: Moisture stress in a drought-sensitive phenological stage.",
        "mr": "प्राधान्य उच्च: दुष्काळ-संवेदनशील अवस्थेत पाण्याचा ताण.",
        "hi": "प्राथमिकता उच्च: सूखा-संवेदनशील चरण में जल तनाव.",
        "tech": "Assigned HIGH priority: depletion approaching RAW in sensitive crop stage.",
        "refs": ["priority", "growth_stage"],
        "limits": [],
    },
    DecisionReasonCode.PRIORITY_MEDIUM_MONITORING.value: {
        "en": "Priority MEDIUM: Scheduled monitoring for depletion approaching management limits.",
        "mr": "प्राधान्य मध्यम: मर्यादेजवळ पोहोचणाऱ्या पाण्याच्या तुटवड्यासाठी नियमित निरीक्षण.",
        "hi": "प्राथमिकता मध्यम: सीमा के निकट पहुँच रही पानी की कमी की नियमित निगरानी.",
        "tech": "Assigned MEDIUM priority: Dr approaching RAW under normal crop stages.",
        "refs": ["priority", "Dr"],
        "limits": [],
    },
    DecisionReasonCode.PRIORITY_LOW_HEALTHY.value: {
        "en": "Priority LOW: Well-watered healthy root zone.",
        "mr": "प्राधान्य कमी: मुळांच्या भागात चांगला ओलावा असलेले निरोगी पीक.",
        "hi": "प्राथमिकता निम्न: पर्याप्त नमी और स्वस्थ जड़ क्षेत्र.",
        "tech": "Assigned LOW priority: zone has adequate soil moisture.",
        "refs": ["priority"],
        "limits": [],
    },
    DecisionReasonCode.PRIORITY_UNRANKED_INSUFFICIENT_DATA.value: {
        "en": "Priority UNRANKED: Zone cannot be prioritized due to insufficient evidence.",
        "mr": "प्राधान्य अनिर्धारित: अपुऱ्या माहितीमुळे झोनचे प्राधान्य ठरवता येत नाही.",
        "hi": "प्राथमिकता अनिर्धारित: अपर्याप्त डेटा के कारण ज़ोन की प्राथमिकता तय नहीं की जा सकती.",
        "tech": "Assigned UNRANKED priority: incomplete evidence prevents ranking against other zones.",
        "refs": ["priority"],
        "limits": ["Data acquisition needed before scheduling."],
    },

    # --------------------------------------------------------------------------
    # 6. Phase 5: Non-Watering Agronomic Flags
    # --------------------------------------------------------------------------
    DecisionReasonCode.AGRONOMIC_FLAG_VEGETATION_ANOMALY_NON_WATERING.value: {
        "en": "Agronomic alert: Satellite vegetation index decline detected, but root zone is well-watered. Inspect for pests, disease, or nutrient deficiency.",
        "mr": "कृषी इशारा: उपग्रहाद्वारे पिकाच्या निर्देशांकात घट आढळली आहे, परंतु जमिनीत पाणी मुबलक आहे. कीड, रोग किंवा खतांची कमतरता तपासा.",
        "hi": "कृषि अलर्ट: उपग्रह वनस्पति सूचकांक में गिरावट देखी गई है, लेकिन जड़ क्षेत्र में पर्याप्त पानी है. कीट, रोग या पोषक तत्वों की कमी की जांच करें.",
        "tech": "Vegetation anomaly flag isolated: NDVI decline with Dr < RAW. Non-watering stress indicated.",
        "refs": ["ndvi", "Dr", "RAW"],
        "limits": ["Optical vegetation changes can stem from fungal blight, root rot, or nitrogen deficiency."],
    },
    DecisionReasonCode.AGRONOMIC_FLAG_SOIL_SALINITY_NON_WATERING.value: {
        "en": "Soil condition alert: Elevated soil salinity detected. Do not apply light deficit irrigation; consult agronomic leaching guidelines.",
        "mr": "माती आरोग्य इशारा: मातीत क्षारांचे प्रमाण वाढले आहे. हलके सिंचन टाळा; क्षार निचरा मार्गदर्शक तत्त्वे पाळा.",
        "hi": "मृदा स्वास्थ्य अलर्ट: मिट्टी में लवणता बढ़ी हुई है. हल्की सिंचाई से बचें; लीचिंग दिशानिर्देशों का पालन करें.",
        "tech": "Soil ECe exceeds salinity threshold. Does not inflate standard irrigation depth without leaching fraction plan.",
        "refs": ["electrical_conductivity_e_ce"],
        "limits": ["Standard deficit irrigation in saline soil concentrates salt ions near the root surface."],
    },
    DecisionReasonCode.AGRONOMIC_FLAG_SOIL_ALKALINE_NON_WATERING.value: {
        "en": "Soil condition alert: Alkaline soil pH detected, which may restrict micronutrient availability.",
        "mr": "माती आरोग्य इशारा: मातीचा सामू (pH) अल्कधर्मी आहे, ज्यामुळे सूक्ष्मअन्नद्रव्ये मिळण्यात अडचण येऊ शकते.",
        "hi": "मृदा स्वास्थ्य अलर्ट: मिट्टी का pH क्षारीय है, जिससे सूक्ष्म पोषक तत्वों की उपलब्धता बाधित हो सकती है.",
        "tech": "Soil pH > 8.5. Edaphic chemical condition requiring soil amendment; not an irrigation trigger.",
        "refs": ["ph"],
        "limits": ["Iron, zinc, and phosphorus uptake are restricted at elevated pH."],
    },
    DecisionReasonCode.AGRONOMIC_FLAG_WEATHER_HEAT_NON_WATERING.value: {
        "en": "Weather advisory: High temperatures and elevated atmospheric vapor pressure deficit active.",
        "mr": "हवामान सल्ला: उच्च तापमान आणि हवेतील उच्च बाष्प दाब तूट सक्रिय आहे.",
        "hi": "मौसम सलाह: अत्यधिक तापमान और उच्च वाष्प दाब घाटा सक्रिय है.",
        "tech": "High VPD (> 2.5 kPa) or heatwave conditions elevate reference ET0.",
        "refs": ["vpd_kpa", "temperature_max_c"],
        "limits": ["Elevated atmospheric demand increases daily depletion rate; monitor root-zone decline."],
    },
    DecisionReasonCode.AGRONOMIC_FLAG_WEATHER_FROST_WARNING.value: {
        "en": "Weather warning: Minimum temperatures near freezing; risk of frost injury to sensitive foliage.",
        "mr": "हवामान इशारा: तापमान गोठणबिंदूजवळ पोहोचत असून पिकाला दंव/थंडीचा धोका आहे.",
        "hi": "मौसम चेतावनी: तापमान हिमांक के निकट पहुँच रहा है; पाले से फसल को नुकसान का खतरा है.",
        "tech": "Temperature minimum <= 2.0 °C. Frost risk warning; independent of water-balance accounting.",
        "refs": ["temperature_min_c"],
        "limits": [],
    },

    # --------------------------------------------------------------------------
    # 7. Phase 4: StressReasonCode (Water, Vegetation, Weather, Soil)
    # --------------------------------------------------------------------------
    StressReasonCode.WATER_DEPLETION_NORMAL.value: {
        "en": "Water balance indicates root-zone depletion is within normal limits.",
        "mr": "मुळांच्या भागातील पाण्याचे प्रमाण सामान्य मर्यादेत आहे.",
        "hi": "मृदा जल संतुलन दर्शाता है कि जड़ क्षेत्र में नमी सामान्य सीमा के भीतर है.",
        "tech": "Water domain evaluation: Dr < 0.80 * RAW, Ks = 1.00.",
        "refs": ["Dr", "RAW"],
        "limits": [],
    },
    StressReasonCode.WATER_DEPLETION_APPROACHING_RAW.value: {
        "en": "Root-zone water depletion is approaching the readily available limit.",
        "mr": "मुळांमधील पाण्याचा तुटवडा सुलभ मर्यादेजवळ पोहोचत आहे.",
        "hi": "जड़ क्षेत्र में पानी की कमी सुलभ सीमा के करीब पहुँच रही है.",
        "tech": "Water domain evaluation: 0.80 * RAW <= Dr < RAW.",
        "refs": ["Dr", "RAW"],
        "limits": [],
    },
    StressReasonCode.WATER_DEPLETION_EXCEEDS_RAW.value: {
        "en": "Water depletion exceeds the readily available limit (Dr >= RAW).",
        "mr": "पाण्याचा तुटवडा सुलभ उपलब्ध पाण्याच्या मर्यादेपेक्षा जास्त आहे.",
        "hi": "पानी की कमी सुलभ उपलब्ध सीमा से अधिक हो गई है.",
        "tech": "Water domain evaluation: Dr >= RAW, Ks < 1.00.",
        "refs": ["Dr", "RAW", "Ks"],
        "limits": [],
    },
    StressReasonCode.SEVERE_DEPLETION_AT_WILTING_POINT.value: {
        "en": "Severe moisture deficit at the permanent wilting point.",
        "mr": "कायमस्वरूपी मुरझण्याच्या उंबरठ्यावर तीव्र पाणी टंचाई.",
        "hi": "स्थायी म्लानि बिंदु पर गंभीर जल संकट.",
        "tech": "Water domain evaluation: Dr >= TAW or Ks <= 0.20.",
        "refs": ["Dr", "TAW", "Ks"],
        "limits": [],
    },
    StressReasonCode.WATER_STRESS_KS_REDUCED.value: {
        "en": "Active water stress with reduced crop transpiration (Ks < 1.0).",
        "mr": "सक्रिय पाणी ताण आणि पिकाचे बाष्पोत्सर्जन कमी झाले आहे.",
        "hi": "सक्रिय जल तनाव और फसल का वाष्पोत्सर्जन कम हुआ है.",
        "tech": "Water domain evaluation: Ks reduced below 1.0.",
        "refs": ["Ks"],
        "limits": [],
    },
    StressReasonCode.WATER_BALANCE_INSUFFICIENT.value: {
        "en": "Water balance evidence is insufficient or unavailable.",
        "mr": "पाण्याच्या संतुलनाची माहिती अपुरी किंवा अनुपलब्ध आहे.",
        "hi": "जल संतुलन संबंधी डेटा अपर्याप्त या अनुपलब्ध है.",
        "tech": "Water domain evaluation: missing critical water-balance inputs.",
        "refs": ["water_balance"],
        "limits": [],
    },
    StressReasonCode.WATER_BALANCE_STALE.value: {
        "en": "Water balance evidence is stale.",
        "mr": "पाण्याच्या संतुलनाची माहिती कालबाह्य झाली आहे.",
        "hi": "जल संतुलन संबंधी डेटा पुराना हो गया है.",
        "tech": "Water domain evaluation: water-balance exceeds age limit.",
        "refs": ["as_of_time"],
        "limits": [],
    },
    StressReasonCode.VEGETATION_CANOPY_HEALTHY.value: {
        "en": "Satellite canopy vigor indices indicate healthy vegetation.",
        "mr": "उपग्रह निर्देशांकांनुसार पिकाची वाढ निरोगी आणि जोमदार आहे.",
        "hi": "उपग्रह सूचकांकों के अनुसार फसल की स्थिति स्वस्थ है.",
        "tech": "Vegetation domain evaluation: NDVI and NDMI in healthy range.",
        "refs": ["ndvi", "ndmi"],
        "limits": [],
    },
    StressReasonCode.VEGETATION_ANOMALY_NEGATIVE.value: {
        "en": "Satellite observation indicates a negative vegetation index anomaly compared to baseline.",
        "mr": "उपग्रह निरीक्षणात पिकाच्या निर्देशांकात सरासरीपेक्षा घट आढळली आहे.",
        "hi": "उपग्रह अवलोकन में फसल सूचकांक में सामान्य से गिरावट देखी गई है.",
        "tech": "Vegetation domain evaluation: delta_ndvi < -0.10 relative to baseline.",
        "refs": ["delta_ndvi"],
        "limits": [],
    },
    StressReasonCode.VEGETATION_ANOMALY_POSITIVE.value: {
        "en": "Satellite observation indicates above-average canopy development.",
        "mr": "उपग्रह निरीक्षणात सरासरीपेक्षा अधिक चांगली पिकाची वाढ आढळली आहे.",
        "hi": "उपग्रह अवलोकन में औसत से बेहतर फसल वृद्धि देखी गई है.",
        "tech": "Vegetation domain evaluation: delta_ndvi > +0.10 relative to baseline.",
        "refs": ["delta_ndvi"],
        "limits": [],
    },
    StressReasonCode.VEGETATION_MATERIAL_DECLINE.value: {
        "en": "Material negative decline detected in satellite vegetation trend.",
        "mr": "उपग्रह निरीक्षणात पिकाच्या निर्देशांकात तीव्र घट दिसून आली आहे.",
        "hi": "उपग्रह अवलोकन में फसल सूचकांक में तीव्र गिरावट पाई गई है.",
        "tech": "Vegetation domain evaluation: material decline exceeding historical variance.",
        "refs": ["ndvi_trend"],
        "limits": [],
    },
    StressReasonCode.VEGETATION_MOISTURE_INDEX_LOW.value: {
        "en": "Satellite canopy moisture index (NDMI) is low, indicating canopy moisture deficit.",
        "mr": "उपग्रह पिकातील ओलावा निर्देशांक (NDMI) कमी असून पानांमधील ओलावा कमी असल्याचे दर्शवतो.",
        "hi": "उपग्रह फसल नमी सूचकांक (NDMI) कम है, जो पत्तियों में नमी की कमी दर्शाता है.",
        "tech": "Vegetation domain evaluation: NDMI < moisture stress threshold.",
        "refs": ["ndmi"],
        "limits": [],
    },
    StressReasonCode.VEGETATION_SCL_CONTAMINATED.value: {
        "en": "Satellite optical pass affected by cloud or shadow contamination.",
        "mr": "उपग्रह निरीक्षण ढग किंवा सावलीच्या अडथळ्याने बाधित झाले आहे.",
        "hi": "उपग्रह अवलोकन बादलों या छाया के प्रभाव से दूषित हुआ है.",
        "tech": "Vegetation domain evaluation: SCL indicates cloud, cirrus, or shadow pixels.",
        "refs": ["scl_quality"],
        "limits": [],
    },
    StressReasonCode.WEATHER_CONDITIONS_FAVORABLE.value: {
        "en": "Weather conditions are favorable with normal atmospheric evaporative demand.",
        "mr": "हवामान अनुकूल असून बाष्पीभवनाचा ताण सामान्य आहे.",
        "hi": "मौसम अनुकूल है और वायुमंडलीय वाष्पीकरण मांग सामान्य है.",
        "tech": "Weather domain evaluation: normal VPD and temperatures.",
        "refs": ["vpd_kpa", "temperature_max_c"],
        "limits": [],
    },
    StressReasonCode.WEATHER_HEAT_STRESS_PROLONGED.value: {
        "en": "Prolonged high atmospheric heat stress active over the management zone.",
        "mr": "झोनवर दीर्घकाळ उच्च तापमान आणि उष्णतेचा ताण सक्रिय आहे.",
        "hi": "ज़ोन पर लंबे समय से अत्यधिक तापमान और गर्मी का तनाव बना हुआ है.",
        "tech": "Weather domain evaluation: continuous heatwave conditions.",
        "refs": ["temperature_max_c"],
        "limits": [],
    },
    StressReasonCode.WEATHER_HIGH_VAPOR_PRESSURE_DEFICIT.value: {
        "en": "Atmospheric vapor pressure deficit (VPD) is elevated, accelerating transpirational demand.",
        "mr": "हवेतील बाष्प दाब तूट (VPD) जास्त असल्याने बाष्पोत्सर्जनाचा वेग वाढला आहे.",
        "hi": "वायुमंडलीय वाष्प दाब घाटा (VPD) अधिक है, जिससे वाष्पोत्सर्जन की गति बढ़ गई है.",
        "tech": "Weather domain evaluation: VPD > 2.5 kPa.",
        "refs": ["vpd_kpa"],
        "limits": [],
    },
    StressReasonCode.SOIL_CONDITIONS_OPTIMAL.value: {
        "en": "Soil chemical and hydraulic conditions are optimal.",
        "mr": "मातीची रासायनिक व भौतिक स्थिती उत्तम आहे.",
        "hi": "मृदा की रासायनिक और भौतिक स्थिति उत्तम है.",
        "tech": "Soil domain evaluation: salinity and pH in optimal range.",
        "refs": ["ph", "electrical_conductivity_e_ce"],
        "limits": [],
    },
    StressReasonCode.SOIL_SALINITY_ELEVATED.value: {
        "en": "Elevated soil salinity detected in the root zone.",
        "mr": "मुळांच्या भागात मातीतील क्षारांचे प्रमाण वाढले आहे.",
        "hi": "जड़ क्षेत्र में मिट्टी में लवणता का स्तर बढ़ा हुआ पाया गया है.",
        "tech": "Soil domain evaluation: ECe > 4.0 dS/m.",
        "refs": ["electrical_conductivity_e_ce"],
        "limits": [],
    },
    StressReasonCode.SOIL_SALINITY_SEVERE.value: {
        "en": "Severe soil salinity detected (ECe > 8.0 dS/m), imposing severe osmotic stress on root water uptake.",
        "mr": "मातीत क्षारांचे अत्यंत तीव्र प्रमाण (ECe > ८.० dS/m) आढळले असून पिकावर तीव्र ऑस्मोटिक ताण आहे.",
        "hi": "अत्यधिक मृदा लवणता (ECe > 8.0 dS/m) पाई गई है, जो गंभीर परासरणी तनाव उत्पन्न करती है.",
        "tech": "Soil electrical conductivity ECe > 8.0 dS/m. High osmotic potential restricts water uptake.",
        "refs": ["electrical_conductivity_e_ce"],
        "limits": ["Requires structured leaching fraction; deficit irrigation will exacerbate salt buildup."],
    },
    StressReasonCode.SOIL_PH_ALKALINE.value: {
        "en": "Soil pH is alkaline (> 8.5), which can restrict micronutrient availability and root development.",
        "mr": "मातीचा सामू (pH) अल्कधर्मी (> ८.५) आहे, ज्यामुळे सूक्ष्मअन्नद्रव्ये मिळण्यात अडचण येऊ शकते.",
        "hi": "मिट्टी का pH क्षारीय (> 8.5) है, जो सूक्ष्म पोषक तत्वों के अवशोषण को बाधित कर सकता है.",
        "tech": "Soil pH > 8.5. Chemical edaphic hazard requiring agronomic amendment.",
        "refs": ["soil_ph"],
        "limits": ["Iron, zinc, and phosphorus availability restricted at elevated pH."],
    },
    StressReasonCode.SOIL_PH_ACIDIC.value: {
        "en": "Soil pH is strongly acidic (< 5.5), which may cause aluminum toxicity or phosphorus fixation.",
        "mr": "मातीचा सामू (pH) तीव्र आम्लधर्मी (< ५.५) आहे, ज्यामुळे पिकाच्या मुळांवर विपरीत परिणाम होऊ शकतो.",
        "hi": "मिट्टी का pH अत्यधिक अम्लीय (< 5.5) है, जिससे एल्युमिनियम विषाक्तता हो सकती है.",
        "tech": "Soil pH < 5.5. Edaphic acidity constraint.",
        "refs": ["soil_ph"],
        "limits": ["Acidic soils require liming; moisture addition does not correct acidity."],
    },
    StressReasonCode.SOIL_SODIC_HAZARD.value: {
        "en": "Soil sodicity hazard detected (high SAR/ESP), which can destroy soil aggregate structure and impede infiltration.",
        "mr": "मातीत सोडियमचे प्रमाण जास्त असल्याने (सोडिक धोका) जमिनीची रचना खराब होण्याचा आणि पाणी न जिरण्याचा धोका आहे.",
        "hi": "मिट्टी में सोडियम का स्तर अधिक होने से (सोडिक खतरा) मिट्टी की संरचना बिगड़ने और अंतःस्रवण बाधित होने का जोखिम है.",
        "tech": "Sodium Adsorption Ratio (SAR) or Exchangeable Sodium Percentage (ESP) exceeds sodicity limit.",
        "refs": ["sar", "esp"],
        "limits": ["Water infiltration may be severely impeded due to dispersion of clay particles."],
    },
    StressReasonCode.SOIL_METHOD_NOT_STANDARDIZED.value: {
        "en": "Soil analysis methodology is not standardized or lacks calibration metadata.",
        "mr": "माती परीक्षण पद्धती प्रमाणीकृत नाही किंवा तिच्यात कॅलिब्रेशन माहितीचा अभाव आहे.",
        "hi": "मृदा विश्लेषण पद्धति मानकीकृत नहीं है या इसमें अंशांकन डेटा का अभाव है.",
        "tech": "Soil measurement laboratory method not recognized under ISO/USDA standards.",
        "refs": ["soil_method"],
        "limits": ["Values treated as provisional guidance until verified by standard laboratory audit."],
    },
    StressReasonCode.SOIL_AWC_LOW.value: {
        "en": "Soil available water capacity (AWC) is very low, indicating poor water retention.",
        "mr": "मातीची जलधारण क्षमता (AWC) अत्यंत कमी असून जमीन पाणी धरून ठेवू शकत नाही.",
        "hi": "मिट्टी की जल धारण क्षमता (AWC) बहुत कम है, जो खराब जल प्रतिधारण को दर्शाती है.",
        "tech": "AWC < 0.08 m³/m³ (coarse sand/gravelly texture). Profile depletes rapidly.",
        "refs": ["available_water_capacity_m3_m3"],
        "limits": ["Requires frequent, smaller irrigation events to avoid deep drainage losses."],
    },
    StressReasonCode.SOIL_EVIDENCE_INSUFFICIENT.value: {
        "en": "Soil property evidence is insufficient or missing.",
        "mr": "मातीचे गुणधर्म विषयक माहिती अपुरी किंवा अनुपलब्ध आहे.",
        "hi": "मृदा गुणधर्म डेटा अपर्याप्त या अनुपलब्ध है.",
        "tech": "Missing soil texture, bulk density, or hydraulic parameters.",
        "refs": ["soil"],
        "limits": ["Hydraulic capacities cannot be determined reliably without soil profile data."],
    },
    StressReasonCode.SOIL_EVIDENCE_STALE.value: {
        "en": "Soil observation evidence exceeds freshness threshold.",
        "mr": "माती परीक्षण माहिती कालबाह्य झाली आहे.",
        "hi": "मृदा परीक्षण डेटा पुराना हो गया है.",
        "tech": "Soil moisture or chemical properties exceed maximum allowable age.",
        "refs": ["soil_observation_timestamp"],
        "limits": ["Dynamic moisture content changes rapidly; stale soil data cannot represent current root zone."],
    },
    StressReasonCode.VEGETATION_STATISTICAL_ANOMALY.value: {
        "en": "Canopy reflectance anomaly is statistically significant relative to baseline distribution.",
        "mr": "पिकाच्या परावर्तनातील बदल ऐतिहासिक सरासरीच्या तुलनेत सांख्यिकीयदृष्ट्या लक्षणीय आहे.",
        "hi": "फसल परावर्तन विसंगति ऐतिहासिक वितरण के सापेक्ष सांख्यिकीय रूप से महत्वपूर्ण है.",
        "tech": "Student's t-test or z-score rejects null hypothesis of normal canopy development (p < 0.05).",
        "refs": ["t_statistic", "p_value"],
        "limits": ["Statistical significance indicates an anomaly, but does not identify the specific biological cause."],
    },
    StressReasonCode.VEGETATION_STATISTICAL_DECLINE.value: {
        "en": "Significant downward trend in vegetation vigor confirmed by statistical test.",
        "mr": "पिकाच्या जोमात लक्षणीय घट झाल्याची सांख्यिकीय चाचणीद्वारे पुष्टी झाली आहे.",
        "hi": "सांख्यिकीय परीक्षण द्वारा वनस्पति की स्थिति में महत्वपूर्ण गिरावट की पुष्टि हुई है.",
        "tech": "Negative NDVI trend confirmed by hypothesis test against historical baseline.",
        "refs": ["delta_ndvi", "trend_slope"],
        "limits": [],
    },
    StressReasonCode.VEGETATION_BASELINE_MISSING.value: {
        "en": "Historical vegetation baseline is unavailable for comparison.",
        "mr": "तुलनेसाठी पिकाचा ऐतिहासिक आधारभूत डेटा उपलब्ध नाही.",
        "hi": "तुलना के लिए ऐतिहासिक वनस्पति बेसलाइन डेटा उपलब्ध नहीं है.",
        "tech": "No multi-year or reference NDVI baseline established for this zone and crop.",
        "refs": ["baseline_ndvi"],
        "limits": ["Relative anomaly cannot be computed; only absolute thresholding applies."],
    },
    StressReasonCode.VEGETATION_PHENOLOGY_MISMATCH.value: {
        "en": "Satellite vegetation index does not match expected phenological growth stage.",
        "mr": "उपग्रह वनस्पती निर्देशांक पिकाच्या अपेक्षित वाढीच्या अवस्थेशी जुळत नाही.",
        "hi": "उपग्रह वनस्पति सूचकांक फसल के अपेक्षित विकास चरण से मेल नहीं खाता है.",
        "tech": "Observed canopy cover deviates significantly from expected GDD growth curve.",
        "refs": ["ndvi", "growth_stage"],
        "limits": ["Could indicate delayed emergence, stunting, or incorrect planting metadata."],
    },
    StressReasonCode.VEGETATION_CLOUD_SHADOW_CONTAMINATED.value: {
        "en": "Sentinel-2 optical pass contaminated by cloud shadow (SCL Class 3).",
        "mr": "सेंटिनेल-२ उपग्रह निरीक्षण ढगांच्या सावलीमुळे बाधित झाले आहे (SCL वर्ग ३).",
        "hi": "सेंटिनल-2 उपग्रह अवलोकन बादलों की छाया से दूषित हुआ है (SCL वर्ग 3).",
        "tech": "Sentinel-2 SCL Class 3 indicates cloud shadow contamination.",
        "refs": ["scl_3_cloud_shadow_pixels"],
        "limits": ["Cloud shadow pixels are excluded from valid canopy aggregation."],
    },
    StressReasonCode.VEGETATION_CAST_SHADOW_CONTAMINATED.value: {
        "en": "Sentinel-2 optical pass contaminated by topographic or cast shadow (SCL Class 2).",
        "mr": "सेंटिनेल-२ उपग्रह निरीक्षण भूभागाच्या किंवा ढगांच्या सावलीमुळे बाधित झाले आहे (SCL वर्ग २).",
        "hi": "सेंटिनल-2 उपग्रह अवलोकन स्थलाकृतिक या बादलों की छाया से दूषित हुआ है (SCL वर्ग 2).",
        "tech": "Sentinel-2 SCL Class 2 indicates cast shadow contamination.",
        "refs": ["scl_2_cast_shadow_pixels", "scl_quality"],
        "limits": ["Shadow pixels reduce apparent reflectance; indices suppressed to prevent false anomalies."],
    },
    StressReasonCode.VEGETATION_COVERAGE_INSUFFICIENT.value: {
        "en": "Valid pixel coverage over the management zone is below the minimum threshold.",
        "mr": "व्यवस्थापन झोनमधील वैध पिक्सेल कव्हरेज किमान मर्यादेपेक्षा कमी आहे.",
        "hi": "प्रबंधन ज़ोन में मान्य पिक्सेल कवरेज न्यूनतम सीमा से कम है.",
        "tech": "Valid pixel fraction < valid_pixel_threshold (default 0.70).",
        "refs": ["valid_pixel_fraction"],
        "limits": ["Insufficient optical spatial overlap prevents reliable zone-level canopy aggregation."],
    },
    StressReasonCode.VEGETATION_EVIDENCE_INSUFFICIENT.value: {
        "en": "Satellite vegetation evidence is insufficient or missing.",
        "mr": "उपग्रह वनस्पती विषयक माहिती अपुरी किंवा उपलब्ध नाही.",
        "hi": "उपग्रह वनस्पति डेटा अपर्याप्त या अनुपलब्ध है.",
        "tech": "No valid cloud-free optical scenes available for the zone.",
        "refs": ["vegetation"],
        "limits": ["Vegetation canopy vigor cannot be assessed without screened optical imagery."],
    },
    StressReasonCode.VEGETATION_EVIDENCE_STALE.value: {
        "en": "Satellite vegetation pass exceeds maximum allowable age.",
        "mr": "उपग्रह वनस्पती निरीक्षण कालबाह्य झाले आहे.",
        "hi": "उपग्रह वनस्पति अवलोकन अधिकतम स्वीकार्य समय से पुराना हो गया है.",
        "tech": "Elapsed time since last valid Sentinel-2 pass exceeds max_vegetation_age_days.",
        "refs": ["vegetation_observation_timestamp"],
        "limits": ["Canopy indices may not reflect rapid phenological changes or recent defoliation."],
    },
    StressReasonCode.WEATHER_EXTENDED_DRY_SPELL.value: {
        "en": "Extended dry spell active with prolonged absence of effective precipitation.",
        "mr": "दीर्घकाळ पावसाचा खंड पडला असून कोरडा दुष्काळ सदृश स्थिती आहे.",
        "hi": "लंबे समय से वर्षा का अभाव है और शुष्क स्थिति बनी हुई है.",
        "tech": "Consecutive rain-free days exceed regional dry-spell threshold.",
        "refs": ["consecutive_dry_days"],
        "limits": [],
    },
    StressReasonCode.WEATHER_FROST_RISK.value: {
        "en": "Risk of freezing temperatures and frost injury to crop foliage.",
        "mr": "तापमान गोठणबिंदूजवळ पोहोचल्याने पिकाला दंवाचा आणि थंडीचा धोका आहे.",
        "hi": "तापमान हिमांक के निकट पहुँचने से फसल को पाले का खतरा है.",
        "tech": "Minimum temperature <= 2.0 °C. Cold stress condition.",
        "refs": ["temperature_min_c"],
        "limits": [],
    },
    StressReasonCode.WEATHER_EVIDENCE_INSUFFICIENT.value: {
        "en": "Weather observation evidence is insufficient or missing.",
        "mr": "हवामान विषयक माहिती अपुरी किंवा अनुपलब्ध आहे.",
        "hi": "मौसम संबंधी डेटा अपर्याप्त या अनुपलब्ध है.",
        "tech": "Weather domain missing required temperature, radiation, wind, or humidity observations.",
        "refs": ["weather"],
        "limits": ["Reference ET0 cannot be calculated without meteorological inputs."],
    },
    StressReasonCode.WEATHER_EVIDENCE_STALE.value: {
        "en": "Weather evidence exceeds allowable freshness threshold.",
        "mr": "हवामान निरीक्षणे कालबाह्य झाली आहेत.",
        "hi": "मौसम डेटा स्वीकार्य समय सीमा से पुराना हो गया है.",
        "tech": "Elapsed time since weather observation exceeds weather freshness threshold.",
        "refs": ["weather", "as_of_time"],
        "limits": ["Current transpirational demand cannot be established from stale meteorological data."],
    },

    # --------------------------------------------------------------------------
    # 3. Phase 3: Agronomic Diagnostics & Water Balance Limitations
    # --------------------------------------------------------------------------
    AgronomyReasonCode.AGRONOMY_ET0_MISSING.value: {
        "en": "Reference evapotranspiration (ET₀) evidence is missing; atmospheric evaporative demand cannot be determined.",
        "mr": "संदर्भ बाष्पोत्सर्जन (ET₀) माहिती उपलब्ध नाही; वातावरणातील पाण्याची मागणी मोजता येत नाही.",
        "hi": "संदर्भ वाष्पोत्सर्जन (ET₀) डेटा अनुपलब्ध है; वायुमंडलीय जल वाष्पीकरण मांग निर्धारित नहीं की जा सकती.",
        "tech": "FAO-56 Penman-Monteith ET₀ missing temperature, humidity, wind, or solar radiation meteorological inputs.",
        "refs": ["ET0", "temperature_max", "temperature_min", "relative_humidity", "solar_radiation"],
        "limits": ["Crop water requirement cannot be estimated without baseline atmospheric evaporative demand."],
    },
    AgronomyReasonCode.AGRONOMY_CROP_COEFFICIENT_MISSING.value: {
        "en": "Crop coefficient (Kc) is missing or uncalibrated; crop-specific transpiration demand cannot be calculated.",
        "mr": "पीक गुणांक (Kc) उपलब्ध किंवा कॅलिब्रेट केलेला नाही; पिकाची विशिष्ट पाण्याची मागणी मोजता येत नाही.",
        "hi": "फसल गुणांक (Kc) अनुपलब्ध या कैलिब्रेट नहीं है; फसल-विशिष्ट जल मांग की गणना नहीं की जा सकती.",
        "tech": "Single crop coefficient Kc table lookup or phenological stage mapping failed; crop type unknown.",
        "refs": ["Kc", "crop_type", "growth_stage", "days_after_sowing"],
        "limits": ["Cannot scale reference ET₀ to actual crop canopy evapotranspiration without verified Kc."],
    },
    AgronomyReasonCode.AGRONOMY_INITIAL_SOIL_MOISTURE_MISSING.value: {
        "en": "Initial soil moisture or root-zone depletion is missing; daily water-balance tracking cannot be initialized.",
        "mr": "सुरुवातीचा मातीतील ओलावा किंवा मुळांमधील पाण्याचा तुटवडा उपलब्ध नाही; दैनंदिन जल संतुलन सुरू करता येत नाही.",
        "hi": "प्रारंभिक मृदा नमी या जड़ क्षेत्र की कमी अनुपलब्ध है; दैनिक जल संतुलन आरंभ नहीं किया जा सकता.",
        "tech": "Initial root-zone depletion Dr_prev or initial volumetric soil moisture theta_init is null.",
        "refs": ["Dr_init", "theta_init", "rooting_depth_zr"],
        "limits": ["Water-balance integration requires an established initial storage condition; default 0 is unphysical."],
    },
    AgronomyReasonCode.AGRONOMY_EFFECTIVE_RAINFALL_MISSING.value: {
        "en": "Effective rainfall evidence is missing; crop-usable precipitation cannot be determined.",
        "mr": "प्रभावी पावसाची माहिती उपलब्ध नाही; पिकासाठी वापरण्यायोग्य पावसाचे प्रमाण निश्चित करता येत नाही.",
        "hi": "प्रभावी वर्षा डेटा अनुपलब्ध है; फसल-उपयोगी वर्षा की मात्रा निर्धारित नहीं की जा सकती.",
        "tech": "Precipitation input missing or effective rainfall calculation returned null due to missing consumptive use.",
        "refs": ["P_gross", "P_effective", "runoff_mm"],
        "limits": ["Missing rainfall evidence cannot be coerced to zero without violating mass conservation rules."],
    },
    AgronomyReasonCode.AGRONOMY_INVALID_SOIL_PROPERTIES.value: {
        "en": "Soil hydraulic properties are invalid or contradictory (e.g., Field Capacity <= Wilting Point or non-positive TAW).",
        "mr": "मातीचे जलसंधारण गुणधर्म अवैध किंवा परस्परविरोधी आहेत (उदा. शेत क्षमता <= म्लानी बिंदू किंवा अमान्य TAW).",
        "hi": "मृदा जल गुणधर्म अमान्य या विरोधाभासी हैं (उदा. खेत क्षमता <= म्लानि बिंदु या गैर-धनात्मक TAW).",
        "tech": "Soil capacities violated physical invariants: theta_FC <= theta_WP or TAW <= 0 or RAW <= 0.",
        "refs": ["theta_FC", "theta_WP", "TAW", "RAW", "rooting_depth_zr"],
        "limits": ["Soil profile storage boundaries are undefined; plant-available water cannot be determined."],
    },
    AgronomyReasonCode.AGRONOMY_PROVISIONAL_EMPIRICAL_RAINFALL.value: {
        "en": "Water-balance accounting relies on provisional empirical effective rainfall without verified infiltration/runoff data.",
        "mr": "जल संतुलन नोंदी पडताळणी न केलेल्या तात्पुरत्या अनुभवजन्य प्रभावी पावसाच्या पद्धतीवर आधारित आहेत.",
        "hi": "जल संतुलन लेखांकन असत्यापित अनंतिम अनुभवजन्य प्रभावी वर्षा पद्धति पर निर्भर करता है.",
        "tech": "WaterBalanceResult marked is_provisional_empirical=True using monthly FAO/USDA-SCS empirical equations.",
        "refs": ["is_provisional_empirical", "effective_rainfall_method"],
        "limits": ["Empirical rainfall formulas approximate monthly averages and do not model single-event infiltration."],
    },
    AgronomyReasonCode.AGRONOMY_INSUFFICIENT_WATER_BALANCE.value: {
        "en": "Root-zone soil water-balance evidence is insufficient to support an irrigation decision.",
        "mr": "सिंचन निर्णयासाठी मुळांच्या भागातील माती-पाणी संतुलनाचा पुरावा अपुरा आहे.",
        "hi": "सिंचाई निर्णय का समर्थन करने के लिए जड़ क्षेत्र मृदा जल-संतुलन साक्ष्य अपर्याप्त है.",
        "tech": "WaterBalanceResult object is missing, has INSUFFICIENT quality status, or violates required physical ranges.",
        "refs": ["quality_status", "Dr", "RAW", "TAW"],
        "limits": ["Automated decision support strictly halted to prevent catastrophic over- or under-irrigation."],
    },
    AgronomyReasonCode.AGRONOMY_INVALID_IRRIGATION_REQUIREMENT.value: {
        "en": "Irrigation requirement is invalid or outside physical bounds (negative depth or excessive deficit).",
        "mr": "सिंचनाची आवश्यक खोली अवैध किंवा भौतिक मर्यादेबाहेर आहे (ऋण खोली किंवा अत्यधिक तुटवडा).",
        "hi": "सिंचाई की आवश्यकता अमान्य या भौतिक सीमाओं से बाहर है (ऋणात्मक गहराई या अत्यधिक कमी).",
        "tech": "Calculated net or gross irrigation depth violated physical constraints (d_net < 0 or d_gross < d_net).",
        "refs": ["net_irrigation_depth_mm", "gross_irrigation_depth_mm", "application_efficiency"],
        "limits": ["Gross irrigation must strictly exceed net deficit by application efficiency factor (d_gross = d_net / eta)."],
    },
}


# ==============================================================================
# RESOLUTION FUNCTION
# ==============================================================================

def resolve_reason_code(
    code: Any,
    language: ExplanationLanguage = ExplanationLanguage.EN,
) -> ReasonCodeExplanation:
    """Resolve an intelligence reason code into an audience-adapted, traceable explanation.

    Args:
        code: Reason code string or Enum instance (from DecisionReasonCode or StressReasonCode).
        language: Target human language for farmer-facing text (EN, MR, HI).

    Returns:
        Structured ReasonCodeExplanation with farmer text, technical note, references, and limitations.
    """
    raw_code = code.value if hasattr(code, "value") else str(code).strip()

    entry = _REASON_CODE_REGISTRY.get(raw_code)

    if entry is not None:
        lang_key = language.value if hasattr(language, "value") else str(language).lower()
        farmer_text = entry.get(lang_key, entry.get("en", raw_code))
        tech_text = entry.get("tech", raw_code)
        refs = list(entry.get("refs", []))
        limits = list(entry.get("limits", []))

        return ReasonCodeExplanation(
            code=raw_code,
            farmer_explanation=farmer_text,
            agronomist_technical_note=tech_text,
            measurement_references=refs,
            limitations=limits,
            is_unresolved=False,
        )

    # Deterministic fallback for unmapped reason code
    if language == ExplanationLanguage.MR:
        farmer_fallback = f"अपरिचित कारण कोड: {raw_code}"
    elif language == ExplanationLanguage.HI:
        farmer_fallback = f"अपरिचित कारण कोड: {raw_code}"
    else:
        farmer_fallback = f"Unresolved reason code: {raw_code}"

    tech_fallback = f"Unmapped reason code '{raw_code}' encountered during explanation resolution."

    return ReasonCodeExplanation(
        code=raw_code,
        farmer_explanation=farmer_fallback,
        agronomist_technical_note=tech_fallback,
        measurement_references=[],
        limitations=["Reason code is not registered in the explanation lookup registry."],
        is_unresolved=True,
    )

