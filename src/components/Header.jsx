import React from 'react';
import { Globe, Bell, ChevronLeft, Shield } from 'lucide-react';

export default function Header({ 
  title, 
  subtitle, 
  showBack, 
  onBack, 
  currentLang, 
  onToggleLang, 
  farmerName,
  isDarkTheme = true
}) {
  const langLabels = {
    mr: 'मराठी',
    hi: 'हिंदी',
    en: 'EN'
  };

  return (
    <header style={{
      padding: '14px 18px 12px',
      background: 'rgba(7, 31, 22, 0.75)',
      backdropFilter: 'blur(20px) saturate(140%)',
      WebkitBackdropFilter: 'blur(20px) saturate(140%)',
      borderBottom: '1px solid rgba(255, 255, 255, 0.12)',
      boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      position: 'sticky',
      top: 0,
      zIndex: 30,
      transition: 'all 0.3s ease'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {showBack ? (
          <button 
            onClick={onBack}
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '12px',
              border: '1px solid rgba(255, 255, 255, 0.18)',
              background: 'rgba(255, 255, 255, 0.10)',
              backdropFilter: 'blur(10px)',
              WebkitBackdropFilter: 'blur(10px)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              color: '#FFFFFF',
              transition: 'all 0.2s ease'
            }}
            aria-label="Back"
          >
            <ChevronLeft size={20} />
          </button>
        ) : (
          <div style={{
            width: '38px',
            height: '38px',
            borderRadius: '12px',
            background: 'linear-gradient(135deg, rgba(101, 199, 106, 0.25) 0%, rgba(11, 45, 32, 0.8) 100%)',
            border: '1px solid rgba(197, 243, 107, 0.45)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#C5F36B',
            boxShadow: '0 0 14px rgba(197, 243, 107, 0.25)'
          }}>
            <Shield size={20} />
          </div>
        )}

        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <h1 style={{
              fontSize: '16px',
              fontWeight: 800,
              color: '#FFFFFF',
              letterSpacing: '-0.3px',
              lineHeight: 1.2
            }}>
              {title || 'FarmShield AI'}
            </h1>
            <span style={{
              fontSize: '9.5px',
              fontWeight: 800,
              color: '#C5F36B',
              background: 'rgba(197, 243, 107, 0.15)',
              border: '1px solid rgba(197, 243, 107, 0.35)',
              padding: '1px 6px',
              borderRadius: '8px',
              letterSpacing: '0.4px'
            }}>
              PRO
            </span>
          </div>
          {subtitle && (
            <p style={{
              fontSize: '11.5px',
              color: '#D5E3D9',
              fontWeight: 500,
              marginTop: '1px'
            }}>
              {subtitle}
            </p>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {/* Quick Language Toggle Button */}
        <button
          onClick={onToggleLang}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            padding: '6px 12px',
            borderRadius: '20px',
            border: '1px solid rgba(197, 243, 107, 0.35)',
            background: 'rgba(10, 43, 28, 0.65)',
            backdropFilter: 'blur(10px)',
            WebkitBackdropFilter: 'blur(10px)',
            color: '#C5F36B',
            fontSize: '12px',
            fontWeight: 700,
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
          title="Change Language"
        >
          <Globe size={13} />
          <span>{langLabels[currentLang] || 'EN'}</span>
        </button>

        {/* Notifications */}
        <button
          style={{
            width: '36px',
            height: '36px',
            borderRadius: '50%',
            border: '1px solid rgba(255, 255, 255, 0.18)',
            background: 'rgba(255, 255, 255, 0.10)',
            backdropFilter: 'blur(10px)',
            WebkitBackdropFilter: 'blur(10px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#D5E3D9',
            cursor: 'pointer',
            position: 'relative'
          }}
          aria-label="Notifications"
        >
          <Bell size={16} />
          <span style={{
            position: 'absolute',
            top: '7px',
            right: '7px',
            width: '6px',
            height: '6px',
            backgroundColor: '#C5F36B',
            borderRadius: '50%',
            boxShadow: '0 0 8px #C5F36B'
          }} />
        </button>
      </div>
    </header>
  );
}
