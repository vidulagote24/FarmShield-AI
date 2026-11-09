import React, { useState } from 'react';
import { ShieldCheck, Bug, Camera, AlertTriangle, CheckCircle, Search } from 'lucide-react';

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
    <div style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      
      {/* Header Banner */}
      <div style={{
        background: '#FFFFFF',
        borderRadius: '20px',
        padding: '18px',
        border: '1px solid var(--border-color)',
        boxShadow: 'var(--shadow-sm)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <span className="status-pill" style={{ background: '#DCFCE7', color: '#16A34A' }}>
            <ShieldCheck size={14} />
            {currentLang === 'mr' ? 'पीक आरोग्य' : 'Crop Health'}
          </span>
          <span style={{ fontSize: '13px', fontWeight: 800, color: '#16A34A' }}>
            ९४% निरोगी
          </span>
        </div>
        <h3 style={{ fontSize: '17px', fontWeight: 800, color: 'var(--text-main)' }}>
          {cropName} {currentLang === 'mr' ? 'संरक्षण कवच' : 'Protection Shield'}
        </h3>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
          {currentLang === 'mr' 
            ? 'पिकाच्या पानावरील डाग किंवा रोगाचा फोटो काढून त्वरित निदान मिळवा.'
            : 'Capture leaf photo to diagnose pests, fungus and nutrient deficiency.'}
        </p>
      </div>

      {/* AI Leaf Scanner Button */}
      <div className="farmer-card" style={{ textAlign: 'center', padding: '24px 18px', border: '2px dashed var(--primary)' }}>
        <div style={{
          width: '60px',
          height: '60px',
          borderRadius: '50%',
          background: 'var(--primary-light)',
          color: 'var(--primary)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 12px'
        }}>
          <Camera size={30} />
        </div>
        <h4 style={{ fontSize: '16px', fontWeight: 800, color: 'var(--text-main)', marginBottom: '6px' }}>
          {currentLang === 'mr' ? 'पानाचा फोटो घ्या' : 'Scan Leaf with Camera'}
        </h4>
        <p style={{ fontSize: '12.5px', color: 'var(--text-muted)', marginBottom: '16px' }}>
          {currentLang === 'mr' ? 'एआय द्वारे २ सेकंदात अचूक औषध व सल्ला' : 'Instant AI disease diagnosis & remedies'}
        </p>

        <button
          onClick={handleSimulateScan}
          disabled={analyzing}
          className="btn-farmer-primary"
          style={{ maxWidth: '280px', margin: '0 auto' }}
        >
          <Camera size={18} />
          <span>{analyzing ? (currentLang === 'mr' ? 'तपासणी चालू आहे...' : 'Analyzing Leaf...') : (currentLang === 'mr' ? 'फोटो स्कॅन करा' : 'Scan Crop Leaf')}</span>
        </button>

        {scannedResult && (
          <div style={{
            marginTop: '16px',
            padding: '14px',
            background: '#FEF3C7',
            borderRadius: '14px',
            textAlign: 'left',
            border: '1.5px solid #FCD34D'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#92400E', fontWeight: 800, fontSize: '14px' }}>
              <AlertTriangle size={16} />
              <span>{scannedResult.disease}</span>
            </div>
            <div style={{ fontSize: '12px', color: '#B45309', margin: '4px 0 8px' }}>
              तीव्रता: {scannedResult.severity}
            </div>
            <div style={{ fontSize: '12.5px', color: 'var(--text-main)', lineHeight: '1.4' }}>
              💊 {scannedResult.remedy}
            </div>
          </div>
        )}
      </div>

      {/* Seasonal Alert List */}
      <div>
        <h4 style={{ fontSize: '14px', fontWeight: 800, color: 'var(--text-main)', marginBottom: '10px' }}>
          🔔 {currentLang === 'mr' ? 'चालू हंगामातील संभाव्य धोके' : 'Seasonal Risk Alerts'}
        </h4>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div className="farmer-card" style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              background: '#DCFCE7',
              color: '#16A34A',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}>
              <CheckCircle size={20} />
            </div>
            <div>
              <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-main)' }}>
                {currentLang === 'mr' ? 'गुलाबी बोंडअळी धोका: शून्य' : 'Pink Bollworm Risk: None'}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                {currentLang === 'mr' ? 'फेरोमोन ट्रॅप्समधील संख्या नियंत्रणात आहे.' : 'Pheromone traps show zero counts.'}
              </div>
            </div>
          </div>

          <div className="farmer-card" style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              background: '#FEF3C7',
              color: '#D97706',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}>
              <Bug size={20} />
            </div>
            <div>
              <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-main)' }}>
                {currentLang === 'mr' ? 'मावा / तुडतुडे सावधगिरी' : 'Aphids / Jassids Alert'}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                {currentLang === 'mr' ? 'पिवळे चिकट सापळे एकरी ५ या प्रमाणात लावा.' : 'Install 5 yellow sticky traps per acre.'}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
