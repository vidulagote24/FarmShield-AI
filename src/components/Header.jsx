import React from 'react';
import { Globe, Bell, ChevronLeft, Shield, Sparkles } from 'lucide-react';

export default function Header({ 
  title, 
  subtitle, 
  showBack, 
  onBack, 
  currentLang, 
  onToggleLang, 
  farmerName,
  isDarkTheme = false
}) {
  const langLabels = {
    mr: 'मराठी',
    hi: 'हिंदी',
    en: 'EN'
  };

  return (
    <header style={{
      padding: '14px 18px 12px',
      background: isDarkTheme ? 'rgba(7, 31, 22, 0.85)' : '#FFFFFF',
      backdropFilter: isDarkTheme ? 'blur(16px)' : 'none',
      WebkitBackdropFilter: isDarkTheme ? 'blur(16px)' : 'none',
      borderBottom: isDarkTheme ? '1px solid rgba(255, 255, 255, 0.10)' : '1px solid var(--border-color)',
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
              border: isDarkTheme ? '1px solid rgba(255, 255, 255, 0.15)' : '1px solid var(--border-color)',
              background: isDarkTheme ? 'rgba(255, 255, 255, 0.08)' : '#F4F7F2',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              color: isDarkTheme ? '#FFFFFF' : 'var(--text-main)'
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
            background: isDarkTheme 
              ? 'linear-gradient(135deg, #164B32 0%, #0B2D20 100%)' 
              : 'linear-gradient(135deg, #2E7D32, #1B5E20)',
            border: isDarkTheme ? '1px solid rgba(168, 217, 74, 0.4)' : 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: isDarkTheme ? '#C5F36B' : '#FFFFFF',
            boxShadow: isDarkTheme ? '0 0 12px rgba(168, 217, 74, 0.25)' : 'none'
          }}>
            <Shield size={20} />
          </div>
        )}

        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <h1 style={{
              fontSize: '16px',
              fontWeight: 800,
              color: isDarkTheme ? '#FFFFFF' : 'var(--primary-dark)',
              letterSpacing: '-0.3px',
              lineHeight: 1.2
            }}>
              {title || 'FarmShield AI'}
            </h1>
            {isDarkTheme && (
              <span style={{
                fontSize: '9.5px',
                fontWeight: 800,
                color: '#C5F36B',
                background: 'rgba(168, 217, 74, 0.15)',
                border: '1px solid rgba(168, 217, 74, 0.3)',
                padding: '1px 6px',
                borderRadius: '8px',
                letterSpacing: '0.4px'
              }}>
                PRO
              </span>
            )}
          </div>
          {subtitle && (
            <p style={{
              fontSize: '11.5px',
              color: isDarkTheme ? '#C4D4C8' : 'var(--text-muted)',
              fontWeight: 500
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
            padding: '6px 11px',
            borderRadius: '20px',
            border: isDarkTheme ? '1px solid rgba(168, 217, 74, 0.35)' : '1.5px solid var(--primary-soft)',
            background: isDarkTheme ? 'rgba(22, 75, 50, 0.55)' : 'var(--primary-light)',
            color: isDarkTheme ? '#C5F36B' : 'var(--primary-dark)',
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
            border: isDarkTheme ? '1px solid rgba(255, 255, 255, 0.14)' : '1px solid var(--border-color)',
            background: isDarkTheme ? 'rgba(255, 255, 255, 0.08)' : '#FFFFFF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: isDarkTheme ? '#C4D4C8' : 'var(--text-muted)',
            cursor: 'pointer',
            position: 'relative'
          }}
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
            boxShadow: isDarkTheme ? '0 0 6px #C5F36B' : 'none'
          }} />
        </button>
      </div>
    </header>
  );
}
