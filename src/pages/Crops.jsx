import React, { useState } from 'react';
import { ShieldCheck, Bug, Camera, AlertTriangle, CheckCircle, Search, Sparkles } from 'lucide-react';

export default function Crops({ farmData, t, currentLang }) {
  const [analyzing, setAnalyzing] = useState(false);
  const [scannedResult, setScannedResult] = useState(null);

  const cropName = t.crops[farmData.crop] || farmData.crop;

  const handleSimulateScan = () => {
    setAnalyzing(true);
    setTimeout(() => {
      setAnalyzing(false);
      setScannedResult({
        disease: currentLang === 'mr' ? 'करपा रोग (Cercospora Leaf Spot)' : 'Cercospora Leaf Spot',
        severity: currentLang === 'mr' ? 'कमी (प्रारंभिक लक्षणे)' : 'Low (Early Stage)',
        remedy: currentLang === 'mr' 
          ? 'कॉपर ऑक्सिक्लोराईड (२.५ ग्रॅम/लिटर) किंवा ट्रायकोडर्मा जैविक बुरशीनाशकाची फवारणी करा.' 
          : 'Spray Copper Oxychloride (2.5g/L) or Trichoderma organic bio-fungicide.'
      });
    }, 1200);
  };

  return (
    <div style={{ 
      padding: '16px 18px', 
      display: 'flex', 
      flexDirection: 'column', 
      gap: '16px',
      position: 'relative',
      zIndex: 10 
    }}>
      
      {/* Header Banner in Glass Card */}
      <div className="glass-card" style={{
        padding: '18px',
        border: '1px solid rgba(105, 217, 138, 0.35)',
        background: 'rgba(10, 43, 28, 0.60)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <span className="glass-pill" style={{
            background: 'rgba(105, 217, 138, 0.18)',
            border: '1px solid rgba(105, 217, 138, 0.35)',
            color: '#69D98A'
          }}>
            <ShieldCheck size={14} />
            {currentLang === 'mr' ? 'पीक आरोग्य' : 'Crop Health'}
          </span>
          <span style={{ fontSize: '13px', fontWeight: 800, color: '#69D98A' }}>
            ९४% निरोगी
          </span>
        </div>
        <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#FFFFFF', marginBottom: '4px' }}>
          {cropName} {currentLang === 'mr' ? 'संरक्षण कवच' : 'Protection Shield'}
        </h3>
        <p style={{ fontSize: '13px', color: '#D5E3D9', lineHeight: '1.45' }}>
          {currentLang === 'mr' 
            ? 'पिकाच्या पानावरील डाग किंवा रोगाचा फोटो काढून त्वरित निदान मिळवा.'
            : 'Capture leaf photo to diagnose pests, fungus and nutrient deficiency.'}
        </p>
      </div>

      {/* AI Leaf Scanner Glass Card */}
      <div className="glass-card" style={{ 
        textAlign: 'center', 
        padding: '24px 18px', 
        border: '2px dashed rgba(197, 243, 107, 0.45)',
        background: 'rgba(10, 43, 28, 0.55)'
      }}>
        <div style={{
          width: '64px',
          height: '64px',
          borderRadius: '50%',
          background: 'rgba(197, 243, 107, 0.18)',
          border: '1px solid rgba(197, 243, 107, 0.35)',
          color: '#C5F36B',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 14px',
          boxShadow: '0 0 16px rgba(197, 243, 107, 0.25)'
        }}>
          <Camera size={32} />
        </div>
        <h4 style={{ fontSize: '17px', fontWeight: 800, color: '#FFFFFF', marginBottom: '6px' }}>
          {currentLang === 'mr' ? 'पानाचा फोटो घ्या' : 'Scan Leaf with Camera'}
        </h4>
        <p style={{ fontSize: '13px', color: '#D5E3D9', marginBottom: '18px' }}>
          {currentLang === 'mr' ? 'एआय द्वारे २ सेकंदात अचूक औषध व सल्ला' : 'Instant AI disease diagnosis & remedies'}
        </p>

        <button
          onClick={handleSimulateScan}
          disabled={analyzing}
          className="btn-glass-primary"
          style={{ maxWidth: '280px', margin: '0 auto' }}
        >
          <Camera size={18} />
          <span>{analyzing ? (currentLang === 'mr' ? 'तपासणी चालू आहे...' : 'Analyzing Leaf...') : (currentLang === 'mr' ? 'फोटो स्कॅन करा' : 'Scan Crop Leaf')}</span>
        </button>

        {scannedResult && (
          <div style={{
            marginTop: '18px',
            padding: '16px',
            background: 'rgba(255, 195, 77, 0.14)',
            backdropFilter: 'blur(16px)',
            borderRadius: '16px',
            textAlign: 'left',
            border: '1.5px solid rgba(255, 195, 77, 0.4)',
            boxShadow: '0 4px 20px rgba(0,0,0,0.3)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#FFC34D', fontWeight: 800, fontSize: '15px' }}>
              <AlertTriangle size={18} />
              <span>{scannedResult.disease}</span>
            </div>
            <div style={{ fontSize: '12px', color: '#D5E3D9', margin: '6px 0 10px' }}>
              तीव्रता: <strong style={{ color: '#FFC34D' }}>{scannedResult.severity}</strong>
            </div>
            <div style={{ 
              fontSize: '12.5px', 
              color: '#FFFFFF', 
              lineHeight: '1.5',
              padding: '10px 12px',
              background: 'rgba(7, 31, 22, 0.7)',
              borderRadius: '10px',
              border: '1px solid rgba(255, 255, 255, 0.10)'
            }}>
              <strong>💡 उपाय / Remedy:</strong> {scannedResult.remedy}
            </div>
          </div>
        )}
      </div>

      {/* Advisory & Preventive Tips */}
      <div className="glass-card" style={{ padding: '16px' }}>
        <h4 style={{ fontSize: '14px', fontWeight: 800, color: '#FFFFFF', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Sparkles size={16} color="#C5F36B" />
          {currentLang === 'mr' ? 'पिकांच्या संरक्षणासाठी सूचना' : 'Crop Protection Tips'}
        </h4>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div className="glass-panel" style={{ padding: '10px 12px', fontSize: '12.5px', color: '#D5E3D9', lineHeight: '1.45' }}>
            🌿 <strong>ओलावा नियंत्रण:</strong> अतिरिक्त पाण्यामुळे मुळांवर बुरशीचा प्रादुर्भाव वाढू शकतो; सेन्सर सल्ल्यानुसारच पाणी द्या.
          </div>
          <div className="glass-panel" style={{ padding: '10px 12px', fontSize: '12.5px', color: '#D5E3D9', lineHeight: '1.45' }}>
            🔍 <strong>नियमित पाहणी:</strong> पानांच्या खालच्या बाजूला रसशोषक किडींचे निरीक्षण दुपारी १२ ते ३ दरम्यान करा.
          </div>
        </div>
      </div>
    </div>
  );
}
