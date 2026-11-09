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
      padding: '20px 20px 32px',
      display: 'flex',
      flexDirection: 'column',
      minHeight: '100%',
      justifyContent: 'space-between'
    }}>
      {/* Top Hero Brand */}
      <div>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '16px',
          marginTop: '6px'
        }}>
          <div style={{
            width: '74px',
            height: '74px',
            borderRadius: '24px',
            background: 'linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#FFFFFF',
            boxShadow: '0 10px 24px rgba(46, 125, 50, 0.35)',
            position: 'relative'
          }}>
            <Shield size={38} />
            <div style={{
              position: 'absolute',
              bottom: '-3px',
              right: '-3px',
              background: '#F59E0B',
              borderRadius: '50%',
              padding: '4px',
              border: '2px solid #FFFFFF'
            }}>
              <Sparkles size={12} color="#FFFFFF" />
            </div>
          </div>
        </div>

        <div style={{ textAlign: 'center', marginBottom: '20px' }}>
          <h1 style={{
            fontSize: '24px',
            fontWeight: 800,
            color: 'var(--primary-dark)',
            letterSpacing: '-0.5px',
            marginBottom: '4px'
          }}>
            {t.welcomeTitle}
          </h1>
          <p style={{
            fontSize: '13.5px',
            color: 'var(--text-muted)',
            lineHeight: '1.4',
            maxWidth: '290px',
            margin: '0 auto'
          }}>
            {t.welcomeSubtitle}
          </p>
        </div>

        {/* Feature Highlights */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '8px',
          marginBottom: '24px'
        }}>
          <div style={{
            background: '#FFFFFF',
            borderRadius: '14px',
            padding: '10px 6px',
            textAlign: 'center',
            border: '1px solid var(--border-color)',
            boxShadow: 'var(--shadow-sm)'
          }}>
            <div style={{ color: '#0284C7', marginBottom: '3px', display: 'flex', justifyContent: 'center' }}>
              <Droplets size={20} />
            </div>
            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-main)' }}>
              {currentLang === 'mr' ? 'पाणी नियोजन' : currentLang === 'hi' ? 'स्मार्ट सिंचाई' : 'Smart Water'}
            </div>
          </div>

          <div style={{
            background: '#FFFFFF',
            borderRadius: '14px',
            padding: '10px 6px',
            textAlign: 'center',
            border: '1px solid var(--border-color)',
            boxShadow: 'var(--shadow-sm)'
          }}>
            <div style={{ color: '#16A34A', marginBottom: '3px', display: 'flex', justifyContent: 'center' }}>
              <Shield size={20} />
            </div>
            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-main)' }}>
              {currentLang === 'mr' ? 'पीक रक्षण' : currentLang === 'hi' ? 'फसल सुरक्षा' : 'Pest Shield'}
            </div>
          </div>

          <div style={{
            background: '#FFFFFF',
            borderRadius: '14px',
            padding: '10px 6px',
            textAlign: 'center',
            border: '1px solid var(--border-color)',
            boxShadow: 'var(--shadow-sm)'
          }}>
            <div style={{ color: '#F59E0B', marginBottom: '3px', display: 'flex', justifyContent: 'center' }}>
              <Sun size={20} />
            </div>
            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-main)' }}>
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
            color: 'var(--text-main)',
            marginBottom: '10px',
            textAlign: 'center'
          }}>
            🌐 {t.selectLang}
          </label>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
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
                    padding: '12px 16px',
                    borderRadius: '14px',
                    border: isSelected ? '2px solid var(--primary)' : '1.5px solid var(--border-color)',
                    background: isSelected ? 'var(--primary-light)' : '#FFFFFF',
                    color: isSelected ? 'var(--primary-dark)' : 'var(--text-main)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ textAlign: 'left' }}>
                    <div style={{ fontSize: '15px', fontWeight: 800 }}>{item.label}</div>
                    <div style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>{item.sublabel}</div>
                  </div>
                  {isSelected ? (
                    <div style={{
                      width: '22px',
                      height: '22px',
                      borderRadius: '50%',
                      background: 'var(--primary)',
                      color: '#FFFFFF',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}>
                      <Check size={14} strokeWidth={3} />
                    </div>
                  ) : (
                    <div style={{
                      width: '20px',
                      height: '20px',
                      borderRadius: '50%',
                      border: '2px solid #CBD5E1'
                    }} />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Continue Action Button - Always visible with clean margin */}
      <div style={{ marginTop: '24px', paddingBottom: '8px' }}>
        <button
          className="btn-farmer-primary"
          onClick={onNext}
        >
          <span>{t.getStarted}</span>
          <ChevronRight size={20} />
        </button>
      </div>
    </div>
  );
}
