import React, { useState } from 'react';
import { 
  CloudSun, 
  Droplets, 
  Wind, 
  Sparkles, 
  Volume2, 
  TrendingUp, 
  ShieldCheck, 
  Mic, 
  ChevronRight,
  Sprout,
  Activity,
  Calendar,
  CheckCircle2,
  Clock
} from 'lucide-react';

export default function Dashboard({ 
  farmerData, 
  farmData, 
  onNavigateTab, 
  t, 
  currentLang 
}) {
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);

  // Dynamically calculate days since sowing (Relative to 9 Nov 2026)
  const calculateDaysSinceSowing = () => {
    if (!farmData.sowingDate) return 39;
    try {
      const sowing = new Date(farmData.sowingDate);
      const today = new Date('2026-11-09');
      const diffTime = Math.abs(today - sowing);
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      return isNaN(diffDays) ? 39 : diffDays;
    } catch (e) {
      return 39;
    }
  };

  const daysSinceSowing = calculateDaysSinceSowing();

  const handleSpeakAdvice = () => {
    setIsPlayingAudio(true);
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(t.dashboard.adviceText);
      utterance.lang = currentLang === 'mr' ? 'mr-IN' : currentLang === 'hi' ? 'hi-IN' : 'en-US';
      utterance.onend = () => setIsPlayingAudio(false);
      utterance.onerror = () => setIsPlayingAudio(false);
      window.speechSynthesis.speak(utterance);
    } else {
      setTimeout(() => setIsPlayingAudio(false), 2500);
    }
  };

  const cropName = t.crops[farmData.crop] || farmData.crop;

  // Stages for the crop lifecycle progress
  const stages = [
    { key: 'seeding', label: t.dashboard.lifecycleStages?.seeding || 'पेरणी', done: true },
    { key: 'sprouting', label: t.dashboard.lifecycleStages?.sprouting || 'अंकुरण', done: true },
    { key: 'vegetative', label: t.dashboard.lifecycleStages?.vegetative || 'शाकीय वाढ', active: true },
    { key: 'flowering', label: t.dashboard.lifecycleStages?.flowering || 'फुलोरा', done: false },
    { key: 'maturity', label: t.dashboard.lifecycleStages?.maturity || 'बोंड विकास', done: false },
    { key: 'harvest', label: t.dashboard.lifecycleStages?.harvest || 'काढणी', done: false },
  ];

  return (
    <div style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: '16px', position: 'relative', zIndex: 10 }}>
      
      {/* 1. HERO FARMER INFORMATION CARD */}
      <div className="glass-card" style={{
        padding: '20px',
        background: 'rgba(10, 43, 28, 0.60)',
        border: '1px solid rgba(197, 243, 107, 0.35)',
        boxShadow: '0 12px 36px rgba(0, 0, 0, 0.35), 0 0 24px rgba(197, 243, 107, 0.15)',
        overflow: 'hidden'
      }}>
        {/* Ambient atmospheric glow */}
        <div style={{
          position: 'absolute',
          top: '-40px',
          right: '-40px',
          width: '140px',
          height: '140px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(197, 243, 107, 0.25) 0%, transparent 70%)',
          pointerEvents: 'none'
        }} />

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <span style={{
              fontSize: '13px',
              fontWeight: 700,
              color: '#C5F36B',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              marginBottom: '3px'
            }}>
              <span>🌱</span> {t.dashboard.greeting},
            </span>
            <h2 style={{ fontSize: '23px', fontWeight: 800, color: '#FFFFFF', letterSpacing: '-0.4px', textShadow: '0 2px 6px rgba(0,0,0,0.4)' }}>
              {farmerData.name || 'शेतकरी मित्र'}
            </h2>
          </div>

          <div className="glass-pill" style={{ color: '#FFFFFF', background: 'rgba(255, 255, 255, 0.12)' }}>
            📍 {farmerData.village || 'बारामती'}
          </div>
        </div>

        {/* Farm quick tags */}
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '8px',
          marginTop: '16px',
          paddingTop: '14px',
          borderTop: '1px solid rgba(255, 255, 255, 0.12)'
        }}>
          <span className="glass-pill" style={{ color: '#FFFFFF', background: 'rgba(255, 255, 255, 0.10)' }}>
            🌾 {cropName}
          </span>
          <span className="glass-pill" style={{ color: '#FFFFFF', background: 'rgba(255, 255, 255, 0.10)' }}>
            📏 {farmData.area || '3.5'} {currentLang === 'mr' ? 'एकर' : currentLang === 'hi' ? 'एकड़' : 'Acres'}
          </span>
          <span className="glass-pill" style={{ color: '#C5F36B', background: 'rgba(197, 243, 107, 0.14)', border: '1px solid rgba(197, 243, 107, 0.3)' }}>
            📅 दिवस {daysSinceSowing} ({t.dashboard.vegetativeStage})
          </span>
        </div>
      </div>

      {/* 2. TODAY'S SMART IRRIGATION DECISION PREVIEW (High Priority Centrepiece) */}
      <div 
        onClick={() => onNavigateTab('irrigation')}
        className="glass-card"
        style={{
          padding: '18px',
          background: 'rgba(255, 195, 77, 0.10)',
          border: '1.5px solid rgba(255, 195, 77, 0.45)',
          boxShadow: '0 10px 32px rgba(0, 0, 0, 0.35), 0 0 20px rgba(255, 195, 77, 0.20)',
          cursor: 'pointer',
          transition: 'all 0.2s ease'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '12px',
              background: 'rgba(255, 195, 77, 0.25)',
              color: '#FFC34D',
              border: '1px solid rgba(255, 195, 77, 0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 12px rgba(255, 195, 77, 0.25)'
            }}>
              <Droplets size={20} />
            </div>
            <span style={{ fontSize: '13px', fontWeight: 800, color: '#FFC34D' }}>
              {t.dashboard.irrigationStatusTitle}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span className="demo-tag">IoT Sim</span>
            <span className="status-pill" style={{
              background: 'rgba(255, 195, 77, 0.22)',
              border: '1px solid rgba(255, 195, 77, 0.4)',
              color: '#FFC34D'
            }}>
              {t.irrigation.decisionWait}
            </span>
          </div>
        </div>

        <h3 style={{ fontSize: '16.5px', fontWeight: 800, color: '#FFFFFF', marginBottom: '5px' }}>
          {t.irrigation.statusWait}
        </h3>
        
        <p style={{ fontSize: '12.5px', color: '#D5E3D9', lineHeight: '1.45', marginBottom: '10px' }}>
          {currentLang === 'mr' 
            ? 'जमिनीतील ओलावा ६४% (आदर्श). बाष्पीभवन ३.८ मिमी मध्यम असल्याने आज सिंचन टाळा.'
            : currentLang === 'hi'
            ? 'मिट्टी में ६४% नमी है। वाष्पीकरण ३.८ मिमी मध्यम होने के कारण आज सिंचाई से बचें।'
            : 'Soil moisture is 64% (optimal zone). Moderate ET (3.8mm/day). Postpone watering today.'}
        </p>

        {/* Moisture progress gauge preview */}
        <div style={{
          height: '8px',
          background: 'rgba(255, 255, 255, 0.12)',
          borderRadius: '4px',
          overflow: 'hidden',
          marginBottom: '8px'
        }}>
          <div style={{
            width: '64%',
            height: '100%',
            background: 'linear-gradient(90deg, #FFC34D 0%, #69D98A 100%)',
            borderRadius: '4px'
          }} />
        </div>

        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingTop: '8px',
          borderTop: '1px solid rgba(255, 195, 77, 0.25)',
          fontSize: '12px',
          fontWeight: 800,
          color: '#FFC34D'
        }}>
          <span>{currentLang === 'mr' ? 'तपशीलवार तर्क व गणना पहा' : currentLang === 'hi' ? 'विस्तृत तर्क देखें' : 'View Agronomic Reasoning'}</span>
          <ChevronRight size={16} />
        </div>
      </div>

      {/* 3. LIVE WEATHER CARD WITH HOURLY TREND VISUALIZATION */}
      <div className="glass-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <span style={{ fontSize: '14.5px', fontWeight: 800, color: '#FFFFFF', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CloudSun size={19} color="#FBBF24" />
            {t.dashboard.liveWeather}
          </span>
          <span className="demo-tag">
            {t.demoBadge}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 0 12px' }}>
          <div>
            <div style={{ fontSize: '34px', fontWeight: 800, color: '#FFFFFF', lineHeight: 1 }}>
              31°C
            </div>
            <div style={{ fontSize: '12.5px', color: '#D5E3D9', marginTop: '4px', fontWeight: 600 }}>
              {currentLang === 'mr' ? 'अंशतः ढगाळ • ऊन पडेल' : currentLang === 'hi' ? 'आंशिक रूप से बादल • धूप' : 'Partly Cloudy • Mild Sun'}
            </div>
          </div>

          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '11px', color: '#B6C8BB', fontWeight: 600 }}>
              {t.dashboard.rainProb}
            </div>
            <div style={{ fontSize: '18px', fontWeight: 800, color: '#38BDF8', marginTop: '2px' }}>
              15% <span style={{ fontSize: '11px', fontWeight: 600, color: '#D5E3D9' }}>({currentLang === 'mr' ? 'पाऊस नाही' : 'Dry'})</span>
            </div>
          </div>
        </div>

        {/* Hourly Weather SVG Trend Line */}
        <div style={{
          padding: '10px 12px',
          background: 'rgba(255, 255, 255, 0.06)',
          borderRadius: '14px',
          border: '1px solid rgba(255, 255, 255, 0.10)',
          marginBottom: '12px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10.5px', color: '#B6C8BB', marginBottom: '4px' }}>
            <span>{t.dashboard.todayHourly || 'Hourly Forecast'}</span>
            <span style={{ color: '#C5F36B' }}>३१° से. सरासरी</span>
          </div>

          {/* Clean SVG Temperature Curve */}
          <svg viewBox="0 0 300 45" style={{ width: '100%', height: '42px', overflow: 'visible' }}>
            <defs>
              <linearGradient id="weatherGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#C5F36B" stopOpacity="0.4" />
                <stop offset="100%" stopColor="#C5F36B" stopOpacity="0.0" />
              </linearGradient>
            </defs>
            <path
              d="M 10,32 Q 80,10 150,8 T 290,26 L 290,45 L 10,45 Z"
              fill="url(#weatherGrad)"
            />
            <path
              d="M 10,32 Q 80,10 150,8 T 290,26"
              fill="none"
              stroke="#C5F36B"
              strokeWidth="2.5"
            />
            <circle cx="10" cy="32" r="3" fill="#C5F36B" />
            <circle cx="80" cy="18" r="3" fill="#C5F36B" />
            <circle cx="150" cy="8" r="4" fill="#FFFFFF" stroke="#C5F36B" strokeWidth="2" />
            <circle cx="220" cy="15" r="3" fill="#C5F36B" />
            <circle cx="290" cy="26" r="3" fill="#C5F36B" />
          </svg>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: '#D5E3D9', marginTop: '2px' }}>
            <span>08:00 (26°)</span>
            <span>11:00 (29°)</span>
            <span style={{ fontWeight: 800, color: '#C5F36B' }}>14:00 (33°)</span>
            <span>17:00 (30°)</span>
            <span>20:00 (27°)</span>
          </div>
        </div>

        {/* Weather sub-metrics row */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '8px',
          padding: '10px',
          background: 'rgba(255, 255, 255, 0.08)',
          borderRadius: '14px',
          border: '1px solid rgba(255, 255, 255, 0.12)'
        }}>
          <div style={{ textAlign: 'center' }}>
            <span style={{ fontSize: '11px', color: '#B6C8BB' }}>{t.dashboard.humidity}</span>
            <div style={{ fontSize: '14px', fontWeight: 800, color: '#FFFFFF', marginTop: '2px' }}>68%</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <span style={{ fontSize: '11px', color: '#B6C8BB' }}>वारा / Wind</span>
            <div style={{ fontSize: '14px', fontWeight: 800, color: '#FFFFFF', marginTop: '2px' }}>12 km/h</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <span style={{ fontSize: '11px', color: '#B6C8BB' }}>बाष्पीभवन / ET₀</span>
            <div style={{ fontSize: '14px', fontWeight: 800, color: '#C5F36B', marginTop: '2px' }}>3.8 mm</div>
          </div>
        </div>
      </div>

      {/* 4. DAILY AI ADVISORY CARD (With Audio Voice Assistant) */}
      <div className="glass-card" style={{
        borderLeft: '4px solid #C5F36B',
        background: 'rgba(10, 43, 28, 0.62)',
        boxShadow: '0 8px 30px rgba(0, 0, 0, 0.3)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
          <span style={{ fontSize: '13.5px', fontWeight: 800, color: '#C5F36B', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Sparkles size={17} color="#C5F36B" />
            {t.dashboard.dailyAdvice}
          </span>

          <button
            onClick={handleSpeakAdvice}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              padding: '5px 12px',
              borderRadius: '16px',
              background: isPlayingAudio ? 'rgba(220, 38, 38, 0.85)' : 'rgba(197, 243, 107, 0.18)',
              color: isPlayingAudio ? '#FFFFFF' : '#C5F36B',
              border: `1px solid ${isPlayingAudio ? '#DC2626' : 'rgba(197, 243, 107, 0.4)'}`,
              fontSize: '11.5px',
              fontWeight: 800,
              cursor: 'pointer',
              boxShadow: isPlayingAudio ? '0 0 10px rgba(220, 38, 38, 0.5)' : 'none',
              transition: 'all 0.15s ease'
            }}
          >
            <Volume2 size={14} />
            <span>{isPlayingAudio ? (currentLang === 'mr' ? 'थांबवा' : 'Stop') : t.dashboard.aiVoice}</span>
          </button>
        </div>

        <p style={{ fontSize: '13px', color: '#FFFFFF', lineHeight: '1.55' }}>
          {t.dashboard.adviceText}
        </p>
      </div>

      {/* 5. CROP GROWTH TRACKER CARD */}
      <div className="glass-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <span style={{ fontSize: '14px', fontWeight: 800, color: '#FFFFFF', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Sprout size={18} color="#C5F36B" />
            {t.dashboard.cropGrowthTracker || 'पीक वाढ ट्रॅकर'}
          </span>
          <span className="demo-tag">
            {t.estCropGrowthBadge || 'अंदाजित वाढ'}
          </span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <div>
            <div style={{ fontSize: '16px', fontWeight: 800, color: '#FFFFFF' }}>
              {cropName}
            </div>
            <div style={{ fontSize: '12px', color: '#C5F36B', fontWeight: 700 }}>
              {t.dashboard.vegetativeStage} (दिवस {daysSinceSowing})
            </div>
          </div>

          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '11px', color: '#B6C8BB' }}>{t.dashboard.daysToHarvest || 'काढणीस उर्वरित'}</div>
            <div style={{ fontSize: '16px', fontWeight: 800, color: '#FFFFFF' }}>~११० दिवस</div>
          </div>
        </div>

        {/* 6-Stage Timeline Progress */}
        <div style={{
          padding: '12px 8px',
          background: 'rgba(255, 255, 255, 0.06)',
          borderRadius: '14px',
          border: '1px solid rgba(255, 255, 255, 0.10)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'relative', marginBottom: '8px' }}>
            {/* Background progress bar line */}
            <div style={{
              position: 'absolute',
              top: '50%',
              left: '10px',
              right: '10px',
              height: '3px',
              background: 'rgba(255, 255, 255, 0.15)',
              transform: 'translateY(-50%)',
              zIndex: 0
            }} />
            {/* Active completed line */}
            <div style={{
              position: 'absolute',
              top: '50%',
              left: '10px',
              width: '42%',
              height: '3px',
              background: '#C5F36B',
              transform: 'translateY(-50%)',
              zIndex: 1,
              boxShadow: '0 0 8px #C5F36B'
            }} />

            {stages.map((stage, idx) => {
              const isPast = stage.done;
              const isActive = stage.active;
              return (
                <div key={idx} style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  zIndex: 2
                }}>
                  <div style={{
                    width: isActive ? '18px' : '12px',
                    height: isActive ? '18px' : '12px',
                    borderRadius: '50%',
                    background: isActive ? '#C5F36B' : (isPast ? '#69D98A' : 'rgba(255, 255, 255, 0.25)'),
                    border: isActive ? '3px solid rgba(7, 31, 22, 0.9)' : 'none',
                    boxShadow: isActive ? '0 0 10px #C5F36B' : 'none',
                    transition: 'all 0.2s ease'
                  }} />
                </div>
              );
            })}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9.5px', color: '#B6C8BB' }}>
            <span>पेरणी</span>
            <span>अंकुरण</span>
            <span style={{ color: '#C5F36B', fontWeight: 800 }}>शाकीय (चालू)</span>
            <span>फुलोरा</span>
            <span>बोंड</span>
            <span>काढणी</span>
          </div>
        </div>

        {/* Height and health metrics */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '8px',
          marginTop: '10px'
        }}>
          <div className="glass-panel" style={{ padding: '8px 10px', textAlign: 'center' }}>
            <span style={{ fontSize: '10.5px', color: '#B6C8BB' }}>{t.dashboard.plantHeight || 'रोपांची सरासरी उंची'}</span>
            <div style={{ fontSize: '13px', fontWeight: 800, color: '#FFFFFF', marginTop: '2px' }}>~६५ सेमी</div>
          </div>
          <div className="glass-panel" style={{ padding: '8px 10px', textAlign: 'center' }}>
            <span style={{ fontSize: '10.5px', color: '#B6C8BB' }}>{t.dashboard.healthScore}</span>
            <div style={{ fontSize: '13px', fontWeight: 800, color: '#69D98A', marginTop: '2px' }}>९४% (उत्कृष्ट)</div>
          </div>
        </div>
      </div>

      {/* 6. QUICK SERVICES GRID */}
      <div>
        <h4 style={{ fontSize: '14px', fontWeight: 800, color: '#FFFFFF', marginBottom: '10px', textShadow: '0 1px 3px rgba(0,0,0,0.4)' }}>
          ⚡ {t.dashboard.quickActions}
        </h4>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px' }}>
          <button
            onClick={() => onNavigateTab('irrigation')}
            className="glass-card"
            style={{
              padding: '14px',
              textAlign: 'left',
              cursor: 'pointer'
            }}
          >
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '12px',
              background: 'rgba(56, 189, 248, 0.20)',
              border: '1px solid rgba(56, 189, 248, 0.4)',
              color: '#38BDF8',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '8px',
              boxShadow: '0 0 10px rgba(56, 189, 248, 0.2)'
            }}>
              <Droplets size={20} />
            </div>
            <div style={{ fontSize: '13.5px', fontWeight: 800, color: '#FFFFFF' }}>
              {t.dashboard.smartIrrigation}
            </div>
            <div style={{ fontSize: '11px', color: '#D5E3D9', marginTop: '2px' }}>
              ६४% ओलावा • AI मॉडेल
            </div>
          </button>

          <button
            onClick={() => onNavigateTab('crops')}
            className="glass-card"
            style={{
              padding: '14px',
              textAlign: 'left',
              cursor: 'pointer'
            }}
          >
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '12px',
              background: 'rgba(105, 217, 138, 0.20)',
              border: '1px solid rgba(105, 217, 138, 0.4)',
              color: '#69D98A',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '8px',
              boxShadow: '0 0 10px rgba(105, 217, 138, 0.2)'
            }}>
              <ShieldCheck size={20} />
            </div>
            <div style={{ fontSize: '13.5px', fontWeight: 800, color: '#FFFFFF' }}>
              {t.dashboard.pestShield}
            </div>
            <div style={{ fontSize: '11px', color: '#D5E3D9', marginTop: '2px' }}>
              आरोग्य ९४% • नमुना चाचणी
            </div>
          </button>

          <button
            onClick={() => alert(currentLang === 'mr' ? 'कापूस बाजार भाव (APMC बारामती): ₹७,४०० - ₹७,८०० प्रति क्विंटल [नमुना दर]' : 'Cotton APMC Baramati: ₹7,400 - ₹7,800 / Quintal [Sample Rate]')}
            className="glass-card"
            style={{
              padding: '14px',
              textAlign: 'left',
              cursor: 'pointer'
            }}
          >
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '12px',
              background: 'rgba(255, 195, 77, 0.20)',
              border: '1px solid rgba(255, 195, 77, 0.4)',
              color: '#FFC34D',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '8px',
              boxShadow: '0 0 10px rgba(255, 195, 77, 0.2)'
            }}>
              <TrendingUp size={20} />
            </div>
            <div style={{ fontSize: '13.5px', fontWeight: 800, color: '#FFFFFF' }}>
              {t.dashboard.mandiBhav}
            </div>
            <div style={{ fontSize: '11px', color: '#D5E3D9', marginTop: '2px' }}>
              APMC दर [नमुना]
            </div>
          </button>

          <button
            onClick={() => alert(currentLang === 'mr' ? 'व्हॉइस असिस्टंट सक्रिय: आपला शेतीविषयक प्रश्न विचारा!' : 'Voice Assistant Activated: Ask your farming question!')}
            className="glass-card"
            style={{
              padding: '14px',
              textAlign: 'left',
              cursor: 'pointer'
            }}
          >
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '12px',
              background: 'rgba(192, 132, 252, 0.20)',
              border: '1px solid rgba(192, 132, 252, 0.4)',
              color: '#C084FC',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '8px',
              boxShadow: '0 0 10px rgba(192, 132, 252, 0.2)'
            }}>
              <Mic size={20} />
            </div>
            <div style={{ fontSize: '13.5px', fontWeight: 800, color: '#FFFFFF' }}>
              {t.dashboard.aiVoice}
            </div>
            <div style={{ fontSize: '11px', color: '#D5E3D9', marginTop: '2px' }}>
              बोलून प्रश्न विचारा
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}
