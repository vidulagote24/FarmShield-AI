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
  Info
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

  return (
    <div style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      
      {/* Farmer Header Greeting */}
      <div style={{
        background: 'linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%)',
        borderRadius: '20px',
        padding: '20px',
        color: '#FFFFFF',
        boxShadow: 'var(--shadow-md)',
        position: 'relative',
        overflow: 'hidden'
      }}>
        <div style={{
          position: 'absolute',
          top: '-20px',
          right: '-20px',
          width: '120px',
          height: '120px',
          borderRadius: '50%',
          background: 'rgba(255, 255, 255, 0.08)',
          pointerEvents: 'none'
        }} />

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <span style={{
              fontSize: '13px',
              fontWeight: 600,
              color: '#C8E6C9',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              marginBottom: '2px'
            }}>
              <span>🌱</span> {t.dashboard.greeting},
            </span>
            <h2 style={{ fontSize: '22px', fontWeight: 800, letterSpacing: '-0.4px' }}>
              {farmerData.name || 'शेतकरी मित्र'}
            </h2>
          </div>

          <div style={{
            background: 'rgba(255, 255, 255, 0.2)',
            backdropFilter: 'blur(4px)',
            padding: '5px 12px',
            borderRadius: '20px',
            fontSize: '12px',
            fontWeight: 700
          }}>
            📍 {farmerData.village || 'बारामती'}
          </div>
        </div>

        {/* Farm quick tags */}
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '8px',
          marginTop: '14px',
          paddingTop: '12px',
          borderTop: '1px solid rgba(255, 255, 255, 0.15)'
        }}>
          <span style={{
            fontSize: '12px',
            fontWeight: 700,
            background: 'rgba(255, 255, 255, 0.15)',
            padding: '4px 10px',
            borderRadius: '12px'
          }}>
            🌾 {cropName}
          </span>
          <span style={{
            fontSize: '12px',
            fontWeight: 600,
            background: 'rgba(255, 255, 255, 0.15)',
            padding: '4px 10px',
            borderRadius: '12px'
          }}>
            📏 {farmData.area || '3.5'} {currentLang === 'mr' ? 'एकर' : currentLang === 'hi' ? 'एकड़' : 'Acres'}
          </span>
          <span style={{
            fontSize: '12px',
            fontWeight: 600,
            background: 'rgba(255, 255, 255, 0.15)',
            padding: '4px 10px',
            borderRadius: '12px'
          }}>
            📅 दिवस {daysSinceSowing} ({t.dashboard.vegetativeStage})
          </span>
        </div>
      </div>

      {/* TODAY'S SMART IRRIGATION BANNER (High Priority Decision) */}
      <div 
        onClick={() => onNavigateTab('irrigation')}
        style={{
          background: '#FFFFFF',
          borderRadius: '18px',
          padding: '16px',
          border: '2px solid #FCD34D',
          boxShadow: 'var(--shadow-sm)',
          cursor: 'pointer',
          position: 'relative'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '10px',
              background: '#FEF3C7',
              color: '#B45309',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Droplets size={18} />
            </div>
            <span style={{ fontSize: '13px', fontWeight: 800, color: '#B45309' }}>
              {t.dashboard.irrigationStatusTitle}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span className="demo-tag">IoT Sim</span>
            <span className="status-pill" style={{ background: '#FEF3C7', color: '#92400E' }}>
              {t.irrigation.decisionWait}
            </span>
          </div>
        </div>

        <h3 style={{ fontSize: '16px', fontWeight: 800, color: 'var(--text-main)', marginBottom: '4px' }}>
          {t.irrigation.statusWait}
        </h3>
        <p style={{ fontSize: '12.5px', color: 'var(--text-muted)', lineHeight: '1.4' }}>
          {currentLang === 'mr' 
            ? 'जमिनीतील ओलावा ६४% (आदर्श). बाष्पीभवन ३.८ मिमी मध्यम असल्याने आज सिंचन टाळा.'
            : currentLang === 'hi'
            ? 'मिट्टी में ६४% नमी है। वाष्पीकरण ३.८ मिमी मध्यम होने के कारण आज सिंचाई से बचें।'
            : 'Soil moisture is 64% (optimal zone). Moderate ET (3.8mm/day). Postpone watering today.'}
        </p>

        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginTop: '10px',
          paddingTop: '8px',
          borderTop: '1px solid #FEF3C7',
          fontSize: '12px',
          fontWeight: 700,
          color: '#B45309'
        }}>
          <span>{currentLang === 'mr' ? 'तपशीलवार तर्क व गणना पहा' : currentLang === 'hi' ? 'विस्तृत तर्क देखें' : 'View Agronomic Reasoning'}</span>
          <ChevronRight size={16} />
        </div>
      </div>

      {/* Live Weather Card with Clear Demo / Forecast Badging */}
      <div className="farmer-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <span style={{ fontSize: '14px', fontWeight: 800, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <CloudSun size={18} color="#F59E0B" />
            {t.dashboard.liveWeather}
          </span>
          <span className="demo-tag">
            {t.demoBadge}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 0 12px' }}>
          <div>
            <div style={{ fontSize: '32px', fontWeight: 800, color: 'var(--text-main)', lineHeight: 1 }}>
              31°C
            </div>
            <div style={{ fontSize: '12.5px', color: 'var(--text-muted)', marginTop: '4px', fontWeight: 600 }}>
              {currentLang === 'mr' ? 'अंशतः ढगाळ • ऊन पडेल' : currentLang === 'hi' ? 'आंशिक रूप से बादल • धूप' : 'Partly Cloudy • Mild Sun'}
            </div>
          </div>

          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-light)', fontWeight: 600 }}>
              {t.dashboard.rainProb}
            </div>
            <div style={{ fontSize: '17px', fontWeight: 800, color: '#0284C7', marginTop: '2px' }}>
              15% <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)' }}>({currentLang === 'mr' ? 'पाऊस नाही' : 'Dry'})</span>
            </div>
          </div>
        </div>

        {/* Weather sub-metrics */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '8px',
          padding: '10px',
          background: 'var(--bg-main)',
          borderRadius: '14px'
        }}>
          <div style={{ textAlign: 'center' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{t.dashboard.humidity}</span>
            <div style={{ fontSize: '13px', fontWeight: 800, color: 'var(--text-main)', marginTop: '2px' }}>68%</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>वारा / Wind</span>
            <div style={{ fontSize: '13px', fontWeight: 800, color: 'var(--text-main)', marginTop: '2px' }}>12 km/h</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>बाष्पीभवन / ET</span>
            <div style={{ fontSize: '13px', fontWeight: 800, color: 'var(--text-main)', marginTop: '2px' }}>3.8 mm</div>
          </div>
        </div>
      </div>

      {/* Daily AI Advisory Card with Audio Voice Reader */}
      <div className="farmer-card" style={{ borderLeft: '4px solid var(--primary)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '13.5px', fontWeight: 800, color: 'var(--primary-dark)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Sparkles size={16} color="var(--primary)" />
            {t.dashboard.dailyAdvice}
          </span>

          <button
            onClick={handleSpeakAdvice}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 10px',
              borderRadius: '16px',
              background: isPlayingAudio ? '#DC2626' : 'var(--primary-light)',
              color: isPlayingAudio ? '#FFFFFF' : 'var(--primary-dark)',
              border: 'none',
              fontSize: '11px',
              fontWeight: 700,
              cursor: 'pointer'
            }}
          >
            <Volume2 size={13} />
            <span>{isPlayingAudio ? (currentLang === 'mr' ? 'थांबवा' : 'Stop') : t.dashboard.aiVoice}</span>
          </button>
        </div>

        <p style={{ fontSize: '13px', color: 'var(--text-main)', lineHeight: '1.5' }}>
          {t.dashboard.adviceText}
        </p>
      </div>

      {/* Quick Services Grid */}
      <div>
        <h4 style={{ fontSize: '13.5px', fontWeight: 800, color: 'var(--text-main)', marginBottom: '10px' }}>
          ⚡ {t.dashboard.quickActions}
        </h4>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px' }}>
          <button
            onClick={() => onNavigateTab('irrigation')}
            style={{
              background: '#FFFFFF',
              border: '1.5px solid var(--border-color)',
              borderRadius: '16px',
              padding: '12px 14px',
              textAlign: 'left',
              cursor: 'pointer',
              boxShadow: 'var(--shadow-sm)'
            }}
          >
            <div style={{
              width: '34px',
              height: '34px',
              borderRadius: '10px',
              background: '#E0F2FE',
              color: '#0284C7',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '8px'
            }}>
              <Droplets size={19} />
            </div>
            <div style={{ fontSize: '13px', fontWeight: 800, color: 'var(--text-main)' }}>
              {t.dashboard.smartIrrigation}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
              ६४% ओलावा • AI मॉडेल
            </div>
          </button>

          <button
            onClick={() => onNavigateTab('crops')}
            style={{
              background: '#FFFFFF',
              border: '1.5px solid var(--border-color)',
              borderRadius: '16px',
              padding: '12px 14px',
              textAlign: 'left',
              cursor: 'pointer',
              boxShadow: 'var(--shadow-sm)'
            }}
          >
            <div style={{
              width: '34px',
              height: '34px',
              borderRadius: '10px',
              background: '#DCFCE7',
              color: '#16A34A',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '8px'
            }}>
              <ShieldCheck size={19} />
            </div>
            <div style={{ fontSize: '13px', fontWeight: 800, color: 'var(--text-main)' }}>
              {t.dashboard.pestShield}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
              आरोग्य ९४% • नमुना चाचणी
            </div>
          </button>

          <button
            onClick={() => alert(currentLang === 'mr' ? 'कापूस बाजार भाव (APMC बारामती): ₹७,४०० - ₹७,८०० प्रति क्विंटल [नमुना दर]' : 'Cotton APMC Baramati: ₹7,400 - ₹7,800 / Quintal [Sample Rate]')}
            style={{
              background: '#FFFFFF',
              border: '1.5px solid var(--border-color)',
              borderRadius: '16px',
              padding: '12px 14px',
              textAlign: 'left',
              cursor: 'pointer',
              boxShadow: 'var(--shadow-sm)'
            }}
          >
            <div style={{
              width: '34px',
              height: '34px',
              borderRadius: '10px',
              background: '#FEF3C7',
              color: '#D97706',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '8px'
            }}>
              <TrendingUp size={19} />
            </div>
            <div style={{ fontSize: '13px', fontWeight: 800, color: 'var(--text-main)' }}>
              {t.dashboard.mandiBhav}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
              APMC दर [नमुना]
            </div>
          </button>

          <button
            onClick={() => alert(currentLang === 'mr' ? 'व्हॉइस असिस्टंट सक्रिय: आपला शेतीविषयक प्रश्न विचारा!' : 'Voice Assistant Activated: Ask your farming question!')}
            style={{
              background: '#FFFFFF',
              border: '1.5px solid var(--border-color)',
              borderRadius: '16px',
              padding: '12px 14px',
              textAlign: 'left',
              cursor: 'pointer',
              boxShadow: 'var(--shadow-sm)'
            }}
          >
            <div style={{
              width: '34px',
              height: '34px',
              borderRadius: '10px',
              background: '#F3E8FF',
              color: '#9333EA',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '8px'
            }}>
              <Mic size={19} />
            </div>
            <div style={{ fontSize: '13px', fontWeight: 800, color: 'var(--text-main)' }}>
              {t.dashboard.aiVoice}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
              बोलून प्रश्न विचारा
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}
