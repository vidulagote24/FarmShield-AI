import React from 'react';
import { Shield, Sparkles, Droplets, Sun, ChevronRight, Check } from 'lucide-react';

export default function Welcome({ currentLang, onSelectLang, onNext, t }) {
  const languages = [
    { code: 'mr', label: 'मराठी', sublabel: 'मराठी मध्ये वापरा' },
    { code: 'hi', label: 'हिंदी', sublabel: 'हिंदी में उपयोग करें' },
    { code: 'en', label: 'English', sublabel: 'Use in English' },
  ];

  return (
    <div style={{
      padding: '24px 20px 32px',
      display: 'flex',
      flexDirection: 'column',
      minHeight: '100%',
      justifyContent: 'space-between',
      position: 'relative',
      zIndex: 10
    }}>
      {/* Top Hero Brand Container */}
      <div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '16px',
          marginTop: '6px'
        }}>
          <div style={{
            width: '78px',
            height: '78px',
            borderRadius: '26px',
            background: 'linear-gradient(135deg, rgba(101, 199, 106, 0.3) 0%, rgba(13, 56, 38, 0.85) 100%)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            border: '1.5px solid rgba(197, 243, 107, 0.45)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#C5F36B',
            boxShadow: '0 12px 30px rgba(0, 0, 0, 0.45), 0 0 20px rgba(197, 243, 107, 0.3)',
            position: 'relative'
          }}>
            <Shield size={40} />
            <div style={{
              position: 'absolute',
              bottom: '-3px',
              right: '-3px',
              background: '#F59E0B',
              borderRadius: '50%',
              padding: '4px',
              border: '2px solid rgba(7, 31, 22, 0.9)',
              boxShadow: '0 2px 8px rgba(0,0,0,0.4)'
            }}>
              <Sparkles size={12} color="#FFFFFF" />
            </div>
          </div>
        </div>

        <div style={{ textAlign: 'center', marginBottom: '22px' }}>
          <h1 style={{
            fontSize: '25px',
            fontWeight: 800,
            color: '#FFFFFF',
            letterSpacing: '-0.5px',
            marginBottom: '6px',
            textShadow: '0 2px 10px rgba(0, 0, 0, 0.5)'
          }}>
            {t.welcomeTitle}
          </h1>
          <p style={{
            fontSize: '13.5px',
            color: '#D5E3D9',
            lineHeight: '1.45',
            maxWidth: '300px',
            margin: '0 auto',
            textShadow: '0 1px 4px rgba(0, 0, 0, 0.4)'
          }}>
            {t.welcomeSubtitle}
          </p>
        </div>

        {/* Feature Highlights Glass Cards */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '8px',
          marginBottom: '26px'
        }}>
          <div className="glass-panel" style={{
            padding: '12px 8px',
            textAlign: 'center',
            border: '1px solid rgba(255, 255, 255, 0.16)'
          }}>
            <div style={{ color: '#38BDF8', marginBottom: '4px', display: 'flex', justifyContent: 'center' }}>
              <Droplets size={22} />
            </div>
            <div style={{ fontSize: '11px', fontWeight: 800, color: '#FFFFFF' }}>
              {currentLang === 'mr' ? 'पाणी नियोजन' : currentLang === 'hi' ? 'स्मार्ट सिंचाई' : 'Smart Water'}
            </div>
          </div>

          <div className="glass-panel" style={{
            padding: '12px 8px',
            textAlign: 'center',
            border: '1px solid rgba(255, 255, 255, 0.16)'
          }}>
            <div style={{ color: '#4ADE80', marginBottom: '4px', display: 'flex', justifyContent: 'center' }}>
              <Shield size={22} />
            </div>
            <div style={{ fontSize: '11px', fontWeight: 800, color: '#FFFFFF' }}>
              {currentLang === 'mr' ? 'पीक रक्षण' : currentLang === 'hi' ? 'फसल सुरक्षा' : 'Pest Shield'}
            </div>
          </div>

          <div className="glass-panel" style={{
            padding: '12px 8px',
            textAlign: 'center',
            border: '1px solid rgba(255, 255, 255, 0.16)'
          }}>
            <div style={{ color: '#FBBF24', marginBottom: '4px', display: 'flex', justifyContent: 'center' }}>
              <Sun size={22} />
            </div>
            <div style={{ fontSize: '11px', fontWeight: 800, color: '#FFFFFF' }}>
              {currentLang === 'mr' ? 'अचूक हवामान' : currentLang === 'hi' ? 'मौसम सलाह' : 'Live Weather'}
            </div>
          </div>
        </div>

        {/* Language Selection */}
        <div>
          <label style={{
            display: 'block',
            fontSize: '13.5px',
            fontWeight: 800,
            color: '#FFFFFF',
            marginBottom: '10px',
            textAlign: 'center',
            textShadow: '0 1px 3px rgba(0, 0, 0, 0.5)'
          }}>
            🌐 {t.selectLang}
          </label>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '9px' }}>
            {languages.map((item) => {
              const isSelected = currentLang === item.code;
              return (
                <button
                  key={item.code}
                  onClick={() => onSelectLang(item.code)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '13px 18px',
                    borderRadius: '16px',
                    border: isSelected ? '2px solid #C5F36B' : '1px solid rgba(255, 255, 255, 0.16)',
                    background: isSelected 
                      ? 'rgba(197, 243, 107, 0.16)' 
                      : 'rgba(255, 255, 255, 0.08)',
                    backdropFilter: 'blur(16px)',
                    WebkitBackdropFilter: 'blur(16px)',
                    color: '#FFFFFF',
                    cursor: 'pointer',
                    boxShadow: isSelected ? '0 0 16px rgba(197, 243, 107, 0.25)' : 'none',
                    transition: 'all 0.2s ease'
                  }}
                >
                  <div style={{ textAlign: 'left' }}>
                    <div style={{ fontSize: '15px', fontWeight: 800, color: isSelected ? '#C5F36B' : '#FFFFFF' }}>
                      {item.label}
                    </div>
                    <div style={{ fontSize: '11.5px', color: '#B6C8BB' }}>
                      {item.sublabel}
                    </div>
                  </div>
                  {isSelected ? (
                    <div style={{
                      width: '24px',
                      height: '24px',
                      borderRadius: '50%',
                      background: '#C5F36B',
                      color: '#071F16',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      boxShadow: '0 0 10px #C5F36B'
                    }}>
                      <Check size={15} strokeWidth={3} />
                    </div>
                  ) : (
                    <div style={{
                      width: '22px',
                      height: '22px',
                      borderRadius: '50%',
                      border: '2px solid rgba(255, 255, 255, 0.25)'
                    }} />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Continue Action Button */}
      <div style={{ marginTop: '26px', paddingBottom: '8px' }}>
        <button
          className="btn-glass-primary"
          onClick={onNext}
        >
          <span>{t.getStarted}</span>
          <ChevronRight size={20} />
        </button>
      </div>
    </div>
  );
}
