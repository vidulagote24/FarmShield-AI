import React, { useState } from 'react';
import { 
  Droplets, 
  Clock, 
  Zap, 
  RotateCw, 
  Power, 
  CalendarCheck, 
  Waves,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Activity,
  Layers,
  HelpCircle,
  Eye,
  Info,
  Sparkles,
  Quote
} from 'lucide-react';

export default function Irrigation({ 
  farmData, 
  t, 
  currentLang 
}) {
  // Scenario state: 'wait' | 'irrigate' | 'check'
  const [activeScenario, setActiveScenario] = useState('wait');
  const [motorRunning, setMotorRunning] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const [showLogicDetails, setShowLogicDetails] = useState(true);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleToggleMotor = () => {
    if (motorRunning) {
      setMotorRunning(false);
      showToast(currentLang === 'mr' ? 'सिंचन मोटर बंद केली.' : 'Irrigation motor stopped.');
    } else {
      setMotorRunning(true);
      showToast(currentLang === 'mr' ? 'सिंचन मोटर सुरू झाली! (नमुना ४५ मिनिटे सायकल)' : 'Pump started! (Simulated 45m cycle)');
    }
  };

  // Agronomically reviewed scenarios with exact scientific nuances
  const scenarios = {
    wait: {
      decision: t.irrigation.decisionWait,
      title: t.irrigation.statusWait,
      badgeBg: 'rgba(255, 195, 77, 0.22)',
      badgeColor: '#FFC34D',
      borderColor: 'rgba(255, 195, 77, 0.45)',
      cardGlow: '0 0 24px rgba(255, 195, 77, 0.20)',
      bgGradient: 'rgba(255, 195, 77, 0.08)',
      moisture: 64,
      moistureStatus: currentLang === 'mr' 
        ? '६४% (काळी कसदार माती - शाकीय वाढीसाठी अनुकूल)' 
        : currentLang === 'hi'
        ? '६४% (काली मिट्टी - वानस्पतिक विकास हेतु अनुकूल)'
        : '64% (Black Soil • Vegetative Stage Suitable)',
      threshold: 45,
      fieldCapacity: 72,
      evapotranspiration: '3.8 mm/day',
      cropWaterNeed: '4.2 mm/day',
      availableWaterStorage: '~18 mm in root zone',
      hoursRemaining: '३६-४८ तास (पुढील तपासणी)',
      waterVolumeRecommendation: currentLang === 'mr' ? '० लिटर (सिंचन स्थगित)' : '0 Liters (Postponed)',
      quickSummary: currentLang === 'mr'
        ? 'मुळांच्या ३० सेमी क्षेत्रात सुमारे १८ मिमी सहज उपलब्ध पाणी शिल्लक आहे. ४.२ मिमी दैनंदिन गरजेनुसार सुमारे ४ दिवस पाणी पुरू शकते; हवामानातील बदल लक्षात घेऊन मॉडेलने ३६-४८ तासांचा सुरक्षित फेर-तपासणी अवधी निश्चित केला आहे.'
        : 'Root zone (30cm) retains ~18mm of Readily Available Water (RAW). Under 4.2mm/day ET, theoretical depletion is ~4.3 days; the model applies a conservative 36-48 hour next-check interval.',
      logicPoints: [
        {
          title: currentLang === 'mr' 
            ? '१. मुळांच्या क्षेत्रातील जलसाठा (Root-Zone Water Balance)' 
            : '1. Root-Zone Water Balance & 36–48h Monitoring Interval',
          desc: currentLang === 'mr' 
            ? 'जमिनीतील ओलावा ६४% असून तो पिकाच्या निर्धारित ताण पातळी (४५%) पेक्षा १९ टक्के गुणांनी (percentage points) वर आहे. काळ्या मातीत ३० सेमी मुळांच्या क्षेत्रात सुमारे १८ मिमी सहज उपलब्ध पाणी (RAW) शिल्लक आहे. ४.२ मिमी/दिवस बाष्पीभवनानुसार संपूर्ण जलतूट होण्यास सुमारे ४.३ दिवस लागतील; परंतु अनपेक्षित तापमान वाढ लक्षात घेऊन मॉडेल ३६ ते ४८ तासांचा सुरक्षित फेर-तपासणी अवधी (conservative re-check interval) निश्चित करते.' 
            : 'Soil moisture is 64%, which is 19 percentage points above the configured crop-stress threshold of 45%. With ~18mm Readily Available Water (RAW) and 4.2mm/day crop ET, theoretical depletion is ~4.3 days (18 ÷ 4.2). The model sets a conservative 36–48 hour interval for the next field telemetry check to capture weather shifts early.'
        },
        {
          title: currentLang === 'mr' 
            ? '२. पिकाची पाण्याची गरज विरुद्ध उपलब्ध साठा' 
            : '2. Crop Requirement Covered by Soil Storage',
          desc: currentLang === 'mr' 
            ? 'पिकाला दररोज ४.२ मिमी पाणी लागत असले तरी मातीतील विद्यमान जलसाठा ते सहज पुरवतो. यामुळे आज पाणी देण्याची कोणतीही तात्काळ गरज नाही.' 
            : 'Although crop water requirement is 4.2 mm/day, existing root-zone storage readily buffers transpiration without creating physiological stress.'
        },
        {
          title: currentLang === 'mr' 
            ? '३. पाणथळ स्थिती व ऊर्जा अपव्यय टाळणे' 
            : '3. Minimizing Waterlogging Risk & Energy Waste',
          desc: currentLang === 'mr' 
            ? 'ओलावा आधीच ६४% असताना अनावश्यक पाणी दिल्यास जमिनीत दलदल/पाणथळ स्थिती निर्माण होण्याचा धोका वाढतो, खते खोल वाहून जाऊ शकतात आणि पंपिंग वीज वाया जाते.' 
            : 'Unnecessary irrigation at this moisture level increases waterlogging risk, leaches nutrients beyond the root zone, and wastes pumping electricity.'
        }
      ],
      nextAction: currentLang === 'mr' 
        ? 'आज सिंचन पूर्णपणे टाळा. ३६-४८ तासांनी (उद्या सायंकाळी ०५:३० वाजता) सेन्सरची स्थिती पुन्हा तपासा.' 
        : 'Do NOT irrigate today. Model scheduled next conservative check in 36-48 hours (tomorrow at 05:30 PM).'
    },
    irrigate: {
      decision: t.irrigation.decisionIrrigate,
      title: t.irrigation.statusIrrigate,
      badgeBg: 'rgba(105, 217, 138, 0.22)',
      badgeColor: '#69D98A',
      borderColor: 'rgba(105, 217, 138, 0.45)',
      cardGlow: '0 0 24px rgba(105, 217, 138, 0.20)',
      bgGradient: 'rgba(105, 217, 138, 0.08)',
      moisture: 38,
      moistureStatus: currentLang === 'mr' 
        ? '३८% (ताण पातळी ४५% पेक्षा ७ टक्के गुणांनी खाली)' 
        : currentLang === 'hi'
        ? '३८% (तनाव सीमा ४५% से ७ प्रतिशत अंक नीचे)'
        : '38% (7 percentage points below 45% threshold)',
      threshold: 45,
      fieldCapacity: 72,
      evapotranspiration: '5.2 mm/day',
      cropWaterNeed: '5.6 mm/day',
      availableWaterStorage: '३.२ मिमी (गंभीर जलतूट)',
      hoursRemaining: 'त्वरित / आज संध्याकाळी',
      waterVolumeRecommendation: currentLang === 'mr' ? 'नमुना अंदाज: ४५ मिनिटे ठिबक सायकल' : 'Simulated Target: 45m Drip Cycle',
      quickSummary: currentLang === 'mr'
        ? 'ओलावा ३८% पर्यंत घसरल्याने पिकावर पाण्याचा ताण सुरू झाला आहे. पाने कोमेजण्यापूर्वी ठिबक सिंचन सुरू करा.'
        : 'Soil moisture has fallen to 38%, breaching the 45% stress threshold. Root suction tension is elevated; irrigation cycle recommended.',
      logicPoints: [
        {
          title: currentLang === 'mr' 
            ? '१. ताण पातळी ओलांडली (Stress Threshold Breached)' 
            : '1. Stress Threshold Breached',
          desc: currentLang === 'mr' 
            ? 'ओलावा ३८% आहे, जो किमान आवश्यक ४५% पातळीपेक्षा ७ टक्के गुणांनी खाली आहे. मुळांना पाणी शोषण्यासाठी अतिरिक्त ऊर्जा खर्च करावी लागत असून वाढ खुंटू शकते.' 
            : 'Current moisture of 38% is 7 percentage points below the 45% crop-stress threshold. Capillary matric potential is approaching the stress boundary.'
        },
        {
          title: currentLang === 'mr' 
            ? '२. उष्ण हवामान व बाष्पीभवन तूट' 
            : '2. High Atmospheric Evaporative Deficit',
          desc: currentLang === 'mr' 
            ? 'उष्णतेमुळे बाष्पीभवन दर ५.२ मिमी/दिवस झाला असून उपलब्ध पाणी अवघे ३.२ मिमी उरले आहे.' 
            : 'Atmospheric ET has surged to 5.2 mm/day while remaining soil storage is reduced to ~3.2mm, indicating an acute water deficit.'
        },
        {
          title: currentLang === 'mr' 
            ? '३. सिंचन वेळ (नमुना आधारित गणना)' 
            : '3. Irrigation Cycle Calibration (Simulated Model)',
          desc: currentLang === 'mr' 
            ? '३.५ एकर क्षेत्र व २ लिटर/तास ड्रिपर्सच्या नमुना गृहितकानुसार सुमारे ४५ मिनिटांची सायकल ओलावा पुन्हा ६८% पर्यंत आणण्यासाठी पुरेशी आहे (प्रत्यक्ष डिस्चार्ज दरानुसार वेळ निश्चित करावी).' 
            : 'Based on simulated baseline parameters (3.5 acres, standard 2 LPH emitters), an illustrative 45-minute cycle restores root moisture back toward 68%. Adjust for actual measured line discharge and emitter spacing.'
        }
      ],
      nextAction: currentLang === 'mr' 
        ? 'ठिबक सिंचन मोटर सुरू करा. ४५ मिनिटांच्या नमुना सायकल नंतर ओलावा पुन्हा मोजा.' 
        : 'Start drip pump. Run simulated 45-minute cycle (calibrated to default emitter discharge) and re-verify moisture.'
    },
    check: {
      decision: t.irrigation.decisionCheck,
      title: t.irrigation.statusCheck,
      badgeBg: 'rgba(255, 154, 97, 0.22)',
      badgeColor: '#FF9A61',
      borderColor: 'rgba(255, 154, 97, 0.45)',
      cardGlow: '0 0 24px rgba(255, 154, 97, 0.20)',
      bgGradient: 'rgba(255, 154, 97, 0.08)',
      moisture: 51,
      moistureStatus: currentLang === 'mr' 
        ? '५१% (सीमावर्ती ओलावा - तपासणी आवश्यक)' 
        : currentLang === 'hi'
        ? '५१% (सीमावर्ती नमी - खेत निरीक्षण आवश्यक)'
        : '51% (Near Threshold • Sensor Uncertainty)',
      threshold: 45,
      fieldCapacity: 72,
      evapotranspiration: '4.1 mm/day',
      cropWaterNeed: '4.5 mm/day',
      availableWaterStorage: '८.५ मिमी (अनिश्चित साठा)',
      hoursRemaining: '१२-१८ तास',
      waterVolumeRecommendation: currentLang === 'mr' ? 'तपासणीनंतर ठरवा' : 'Pending Field Verification',
      quickSummary: currentLang === 'mr'
        ? 'ओलावा ५१% असून ताण पातळीच्या (४५%) जवळ आहे. सेन्सर डेटा अनिश्चितता किंवा मातीच्या स्थानिक फरकामुळे थेट पाणी देण्याऐवजी प्रत्यक्ष शेतात पाहणी करण्याचा सल्ला दिला आहे.'
        : 'Moisture reading is 51%, close to the 45% threshold. Because sensor uncertainty or contact gaps may exist, physical inspection is recommended before committing to pump.',
      logicPoints: [
        {
          title: currentLang === 'mr' 
            ? '१. सेन्सर अनिश्चितता व डेटा विसंगती (Data Confidence Check)' 
            : '1. Reading Near Threshold & Sensor Uncertainty',
          desc: currentLang === 'mr' 
            ? 'वाचन ५१% असून ते ताण पातळीच्या (४५%) जवळ आहे. काळ्या चिकण मातीत ओलावा कमी होताना सेन्सर आणि मातीच्या संपर्कात स्थानिक तफावत (contact gap/spatial variance) निर्माण होऊ शकते. डेटा पूर्ण खात्रीशीर नसल्याने प्रत्यक्ष पाहणी आवश्यक आहे.' 
            : 'The reading is near the configured 45% stress boundary. Capacitive probes in shrinking clay soils can encounter contact gaps or spatial variation. The recommendation to CHECK is driven by data uncertainty near the threshold rather than moisture alone.'
        },
        {
          title: currentLang === 'mr' 
            ? '२. काळ्या मातीची पाणी धरून ठेवण्याची क्षमता' 
            : '2. Clay Soil Moisture Retention Buffer',
          desc: currentLang === 'mr' 
            ? 'काळी कसदार माती ५१% ओलाव्यावरही काही पिकांसाठी पाणी उपलब्ध ठेवू शकते, त्यामुळे झाडांची दुपारची स्थिती पाहणे महत्त्वाचे आहे.' 
            : 'Black clay soils buffer tension differently; physical leaf turgor inspection at peak sun (1-2 PM) avoids unwarranted pumping.'
        },
        {
          title: currentLang === 'mr' 
            ? '३. प्रत्यक्ष पाहणीचे मुद्दे' 
            : '3. Actionable Inspection Checklist',
          desc: currentLang === 'mr' 
            ? 'शेतातील २-३ जागांवर १५-२० सेमी खोलीवर माती हातात घेऊन गोळा होतो का ते पहा आणि ड्रिपर्स चोक आहेत का ते तपासा.' 
            : 'Inspect soil by hand at 15-20cm depth in 2-3 spots across the plot (ball squeeze test) and verify that lateral drip lines are not clogged.'
        }
      ],
      nextAction: currentLang === 'mr' 
        ? 'दुपारी १ ते २ वाजता प्रत्यक्ष शेतात जाऊन पानांचा तजेलदारपणा व मुळांजवळील माती तपासा.' 
        : 'Physically inspect root zone soil and leaf turgor at 1-2 PM before activating irrigation pump.'
    }
  };

  const current = scenarios[activeScenario];

  return (
    <div style={{ 
      padding: '16px 18px', 
      display: 'flex', 
      flexDirection: 'column', 
      gap: '16px', 
      paddingBottom: '120px',
      position: 'relative',
      zIndex: 10 
    }}>
      
      {/* Toast Notification */}
      {toastMessage && (
        <div style={{
          position: 'fixed',
          top: '20px',
          left: '50%',
          transform: 'translateX(-50%)',
          background: 'rgba(7, 31, 22, 0.92)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          color: '#FFFFFF',
          border: '1px solid rgba(197, 243, 107, 0.4)',
          padding: '12px 22px',
          borderRadius: '30px',
          fontSize: '13px',
          fontWeight: 700,
          zIndex: 9999,
          boxShadow: '0 8px 30px rgba(0,0,0,0.5), 0 0 15px rgba(197, 243, 107, 0.3)',
          textAlign: 'center',
          maxWidth: '90%'
        }}>
          {toastMessage}
        </div>
      )}

      {/* HACKATHON PITCH HIGHLIGHT (Judges Key Takeaway) */}
      <div className="glass-card" style={{
        padding: '14px 16px',
        background: 'rgba(10, 43, 28, 0.65)',
        border: '1px solid rgba(197, 243, 107, 0.35)',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px'
      }}>
        <Sparkles size={22} color="#C5F36B" style={{ flexShrink: 0, marginTop: '2px' }} />
        <div style={{ fontSize: '12px', lineHeight: '1.45' }}>
          <strong style={{ color: '#C5F36B', display: 'block', marginBottom: '3px', fontSize: '12.5px' }}>
            {currentLang === 'mr' ? '💡 फार्मशील्ड एआय निर्णय तत्त्व (Core Innovation)' : '💡 FarmShield Decision Philosophy'}
          </strong>
          <span style={{ color: '#D5E3D9' }}>
            {currentLang === 'mr' 
              ? '“फार्मशील्ड एआय केवळ पाणी देण्यास सांगत नाही, तर जमिनीतील जलसाठा, पिकाची खरी गरज आणि सेन्सर डेटाची विश्वासार्हता तपासून थांबणे, पाणी देणे किंवा प्रत्यक्ष पाहणीचा सल्ला देते.”'
              : '“FarmShield AI doesn’t blindly trigger irrigation. It evaluates root-zone storage, atmospheric demand, and sensor confidence — recommending WAIT, IRRIGATE, or CHECK when data is uncertain.”'}
          </span>
        </div>
      </div>

      {/* Demo Scenario Switcher for Hackathon Judges */}
      <div className="glass-card" style={{ padding: '14px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <span style={{ fontSize: '12px', fontWeight: 800, color: '#FFFFFF', display: 'flex', alignItems: 'center', gap: '5px' }}>
            <Activity size={15} color="#C5F36B" />
            हॅकाथॉन सिम्युलेटर (Test Scenarios)
          </span>
          <span className="demo-tag">
            Simulated IoT Probe
          </span>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setActiveScenario('wait')}
            style={{
              flex: 1,
              padding: '10px 4px',
              borderRadius: '12px',
              border: activeScenario === 'wait' ? '2px solid #FFC34D' : '1px solid rgba(255, 255, 255, 0.16)',
              fontSize: '11.5px',
              fontWeight: 800,
              cursor: 'pointer',
              background: activeScenario === 'wait' ? 'rgba(255, 195, 77, 0.22)' : 'rgba(255, 255, 255, 0.08)',
              backdropFilter: 'blur(12px)',
              color: activeScenario === 'wait' ? '#FFC34D' : '#D5E3D9',
              boxShadow: activeScenario === 'wait' ? '0 0 16px rgba(255, 195, 77, 0.25)' : 'none',
              transition: 'all 0.2s ease'
            }}
          >
            🟡 WAIT
          </button>

          <button
            onClick={() => setActiveScenario('irrigate')}
            style={{
              flex: 1,
              padding: '10px 4px',
              borderRadius: '12px',
              border: activeScenario === 'irrigate' ? '2px solid #69D98A' : '1px solid rgba(255, 255, 255, 0.16)',
              fontSize: '11.5px',
              fontWeight: 800,
              cursor: 'pointer',
              background: activeScenario === 'irrigate' ? 'rgba(105, 217, 138, 0.22)' : 'rgba(255, 255, 255, 0.08)',
              backdropFilter: 'blur(12px)',
              color: activeScenario === 'irrigate' ? '#69D98A' : '#D5E3D9',
              boxShadow: activeScenario === 'irrigate' ? '0 0 16px rgba(105, 217, 138, 0.25)' : 'none',
              transition: 'all 0.2s ease'
            }}
          >
            🟢 IRRIGATE
          </button>

          <button
            onClick={() => setActiveScenario('check')}
            style={{
              flex: 1,
              padding: '10px 4px',
              borderRadius: '12px',
              border: activeScenario === 'check' ? '2px solid #FF9A61' : '1px solid rgba(255, 255, 255, 0.16)',
              fontSize: '11.5px',
              fontWeight: 800,
              cursor: 'pointer',
              background: activeScenario === 'check' ? 'rgba(255, 154, 97, 0.22)' : 'rgba(255, 255, 255, 0.08)',
              backdropFilter: 'blur(12px)',
              color: activeScenario === 'check' ? '#FF9A61' : '#D5E3D9',
              boxShadow: activeScenario === 'check' ? '0 0 16px rgba(255, 154, 97, 0.25)' : 'none',
              transition: 'all 0.2s ease'
            }}
          >
            🟠 CHECK
          </button>
        </div>
      </div>

      {/* MAIN DECISION HERO CARD - Dynamic Translucent Glass Surface */}
      <div className="glass-card" style={{
        background: current.bgGradient,
        borderRadius: '24px',
        padding: '20px',
        border: `1.5px solid ${current.borderColor}`,
        boxShadow: `0 12px 36px rgba(0, 0, 0, 0.35), ${current.cardGlow}`,
        position: 'relative',
        transition: 'all 0.25s ease'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
          <span className="status-pill" style={{
            background: current.badgeBg,
            border: `1px solid ${current.borderColor}`,
            color: current.badgeColor,
            fontSize: '12.5px',
            padding: '5px 14px'
          }}>
            <Droplets size={15} />
            {current.decision}
          </span>

          <span className="demo-tag">
            IoT Probe #A-102 (Simulated)
          </span>
        </div>

        <h2 style={{
          fontSize: '19px',
          fontWeight: 800,
          color: '#FFFFFF',
          lineHeight: '1.3',
          marginBottom: '8px',
          textShadow: '0 2px 8px rgba(0, 0, 0, 0.4)'
        }}>
          {current.title}
        </h2>

        {/* Quick Agronomic Context */}
        <p style={{ fontSize: '13px', color: '#D5E3D9', lineHeight: '1.5', marginBottom: '14px' }}>
          {current.quickSummary}
        </p>

        {/* Dynamic Moisture Gauge */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.08)',
          backdropFilter: 'blur(12px)',
          borderRadius: '16px',
          padding: '14px',
          border: '1px solid rgba(255, 255, 255, 0.14)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '12.5px', fontWeight: 700, color: '#FFFFFF' }}>
              {t.irrigation.soilMoisture}
            </span>
            <span style={{ fontSize: '13px', fontWeight: 800, color: current.badgeColor }}>
              {current.moistureStatus}
            </span>
          </div>

          {/* Bar track */}
          <div style={{
            height: '14px',
            background: 'rgba(255, 255, 255, 0.12)',
            borderRadius: '7px',
            overflow: 'hidden',
            position: 'relative',
            boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.3)'
          }}>
            <div style={{
              width: `${current.moisture}%`,
              height: '100%',
              background: current.badgeColor,
              borderRadius: '7px',
              boxShadow: `0 0 12px ${current.badgeColor}`,
              transition: 'all 0.4s ease'
            }} />
          </div>

          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: '10.5px',
            color: '#D5E3D9',
            marginTop: '8px'
          }}>
            <span>कोरडी (0%)</span>
            <span style={{ color: '#F87171', fontWeight: 700 }}>ताण पातळी (४५%)</span>
            <span style={{ color: '#69D98A', fontWeight: 700 }}>क्षेत्र क्षमता (७२%)</span>
          </div>
        </div>

        {/* Agronomic Key Parameters Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '8px',
          marginTop: '12px'
        }}>
          <div className="glass-panel" style={{ padding: '9px 6px', textAlign: 'center' }}>
            <div style={{ fontSize: '10.5px', color: '#B6C8BB' }}>बाष्पीभवन (ET₀)</div>
            <div style={{ fontSize: '13px', fontWeight: 800, color: '#FFFFFF', marginTop: '3px' }}>{current.evapotranspiration}</div>
          </div>
          <div className="glass-panel" style={{ padding: '9px 6px', textAlign: 'center' }}>
            <div style={{ fontSize: '10.5px', color: '#B6C8BB' }}>पिकाची गरज</div>
            <div style={{ fontSize: '13px', fontWeight: 800, color: '#FFFFFF', marginTop: '3px' }}>{current.cropWaterNeed}</div>
          </div>
          <div className="glass-panel" style={{ padding: '9px 6px', textAlign: 'center' }}>
            <div style={{ fontSize: '10.5px', color: '#B6C8BB' }}>पुढील वेळ</div>
            <div style={{ fontSize: '11.5px', fontWeight: 800, color: current.badgeColor, marginTop: '3px' }}>{current.hoursRemaining}</div>
          </div>
        </div>
      </div>

      {/* TRANSPARENT SCIENTIFIC REASONING CARD (Explainable Agronomic Logic) */}
      <div className="glass-card" style={{ borderLeft: '4px solid #C5F36B' }}>
        <div 
          onClick={() => setShowLogicDetails(!showLogicDetails)}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
            userSelect: 'none'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              width: '34px',
              height: '34px',
              borderRadius: '10px',
              background: 'rgba(197, 243, 107, 0.18)',
              border: '1px solid rgba(197, 243, 107, 0.35)',
              color: '#C5F36B',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <FileText size={18} />
            </div>
            <div>
              <div style={{ fontSize: '13.5px', fontWeight: 800, color: '#FFFFFF' }}>
                {t.irrigation.logicTitle}
              </div>
              <div style={{ fontSize: '11px', color: '#D5E3D9' }}>
                {currentLang === 'mr' ? 'कापूस पीक • काळी माती • ३० सेमी मुळांचे क्षेत्र' : 'Cotton • Black Soil • 30cm Root Zone'}
              </div>
            </div>
          </div>

          <span style={{ fontSize: '12px', color: '#C5F36B', fontWeight: 800 }}>
            {showLogicDetails ? 'कमी करा' : 'सर्व पहा'}
          </span>
        </div>

        {/* Detailed Points (First point always visible, rest toggleable) */}
        <div style={{ marginTop: '14px', display: 'flex', flexDirection: 'column', gap: '10px', paddingTop: '12px', borderTop: '1px solid rgba(255, 255, 255, 0.12)' }}>
          {/* Point 1: Always visible */}
          <div className="glass-panel" style={{ padding: '12px 14px' }}>
            <div style={{ fontSize: '13px', fontWeight: 800, color: '#C5F36B', marginBottom: '4px' }}>
              {current.logicPoints[0].title}
            </div>
            <div style={{ fontSize: '12px', color: '#D5E3D9', lineHeight: '1.5' }}>
              {current.logicPoints[0].desc}
            </div>
          </div>

          {/* Points 2 & 3: Visible when expanded */}
          {showLogicDetails && current.logicPoints.slice(1).map((pt, idx) => (
            <div key={idx} className="glass-panel" style={{ padding: '12px 14px' }}>
              <div style={{ fontSize: '13px', fontWeight: 800, color: '#C5F36B', marginBottom: '4px' }}>
                {pt.title}
              </div>
              <div style={{ fontSize: '12px', color: '#D5E3D9', lineHeight: '1.5' }}>
                {pt.desc}
              </div>
            </div>
          ))}

          {/* Explicit Farmer Action Plan */}
          <div style={{
            background: 'rgba(105, 217, 138, 0.15)',
            border: '1.5px solid rgba(105, 217, 138, 0.4)',
            borderRadius: '14px',
            padding: '12px 14px',
            marginTop: '4px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: 800, color: '#69D98A', marginBottom: '4px' }}>
              <CheckCircle2 size={17} />
              <span>{t.irrigation.nextActionTitle}</span>
            </div>
            <p style={{ fontSize: '12.5px', color: '#FFFFFF', lineHeight: '1.45', fontWeight: 600 }}>
              👉 {current.nextAction}
            </p>
          </div>
        </div>
      </div>

      {/* Water & Electricity Resource Card */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, 1fr)',
        gap: '12px'
      }}>
        <div className="glass-card" style={{
          background: 'rgba(105, 217, 138, 0.12)',
          border: '1px solid rgba(105, 217, 138, 0.35)'
        }}>
          <div style={{ color: '#69D98A', marginBottom: '4px' }}>
            <Waves size={22} />
          </div>
          <div style={{ fontSize: '11px', color: '#B6C8BB', fontWeight: 600 }}>
            {t.irrigation.waterSaved}
          </div>
          <div style={{ fontSize: '18px', fontWeight: 800, color: '#69D98A', marginTop: '2px' }}>
            {t.irrigation.litres}
          </div>
          <div style={{ fontSize: '10px', color: '#A8D94A', marginTop: '2px' }}>
            [मॉडेल अंदाज / Model Estimate]
          </div>
        </div>

        <div className="glass-card" style={{
          background: 'rgba(255, 195, 77, 0.12)',
          border: '1px solid rgba(255, 195, 77, 0.35)'
        }}>
          <div style={{ color: '#FFC34D', marginBottom: '4px' }}>
            <Zap size={22} />
          </div>
          <div style={{ fontSize: '11px', color: '#B6C8BB', fontWeight: 600 }}>
            {currentLang === 'mr' ? 'वीज बचत' : 'Electricity Saved'}
          </div>
          <div style={{ fontSize: '18px', fontWeight: 800, color: '#FFC34D', marginTop: '2px' }}>
            ₹680 (१४ युनिट्स)
          </div>
          <div style={{ fontSize: '10px', color: '#FFC34D', marginTop: '2px' }}>
            [मॉडेल अंदाज / Model Estimate]
          </div>
        </div>
      </div>

      {/* Direct Farmer Action Controls */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <button
          onClick={handleToggleMotor}
          className="btn-glass-primary"
          style={{
            background: motorRunning 
              ? 'linear-gradient(135deg, rgba(220, 38, 38, 0.95) 0%, rgba(153, 27, 27, 0.95) 100%)' 
              : activeScenario === 'irrigate'
              ? 'linear-gradient(135deg, rgba(22, 163, 74, 0.95) 0%, rgba(21, 128, 61, 0.95) 100%)'
              : 'linear-gradient(135deg, rgba(101, 199, 106, 0.95) 0%, rgba(27, 94, 32, 0.95) 100%)',
            borderColor: motorRunning ? 'rgba(239, 68, 68, 0.5)' : 'rgba(197, 243, 107, 0.45)',
            boxShadow: motorRunning ? '0 0 20px rgba(220, 38, 38, 0.5)' : undefined
          }}
        >
          <Power size={18} />
          <span>
            {motorRunning 
              ? (currentLang === 'mr' ? 'सिंचन मोटर बंद करा (चालू आहे)' : 'Stop Drip Pump (Active)')
              : activeScenario === 'irrigate'
              ? (currentLang === 'mr' ? 'नमुना ठिबक सिंचन सुरू करा (४५ मि.)' : 'Start Simulated Drip Cycle (45 mins)')
              : t.irrigation.startMotor}
          </span>
        </button>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px' }}>
          <button
            onClick={() => showToast(currentLang === 'mr' ? 'स्मार्ट अलर्ट सेट केला! सिंचनाआधी अर्धा तास मेसेज येईल.' : 'Smart alert scheduled for next cycle.')}
            className="btn-glass-secondary"
            style={{ fontSize: '12px' }}
          >
            <CalendarCheck size={15} color="#C5F36B" />
            <span>{t.irrigation.setReminder}</span>
          </button>

          <button
            onClick={() => showToast(currentLang === 'mr' ? 'माती सेन्सर डेटा रिफ्रेश झाला (IoT Probe #A-102)' : 'Sensor probe #A-102 telemetry refreshed.')}
            className="btn-glass-secondary"
            style={{ fontSize: '12px' }}
          >
            <RotateCw size={15} color="#C5F36B" />
            <span>{t.irrigation.testMoisture}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
