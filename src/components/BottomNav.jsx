import React from 'react';
import { Home, Droplets, Sprout, User } from 'lucide-react';

export default function BottomNav({ activeTab, onSelectTab, t, isDarkTheme = false }) {
  const tabs = [
    { id: 'dashboard', label: t.nav.home, icon: Home },
    { id: 'irrigation', label: t.nav.irrigation, icon: Droplets, highlight: true },
    { id: 'crops', label: t.nav.crops, icon: Sprout },
    { id: 'profile', label: t.nav.profile, icon: User },
  ];

  return (
    <nav 
      className={`bottom-nav ${isDarkTheme ? 'dark-glass-nav' : ''}`}
      style={isDarkTheme ? {
        background: 'rgba(7, 31, 22, 0.90)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderTop: '1px solid rgba(255, 255, 255, 0.12)',
        boxShadow: '0 -8px 32px rgba(0, 0, 0, 0.4)'
      } : {}}
    >
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            className={`nav-tab-item ${isActive ? 'active' : ''} ${isDarkTheme ? 'dark-item' : ''}`}
            onClick={() => onSelectTab(tab.id)}
            style={{
              color: isActive 
                ? (isDarkTheme ? '#C5F36B' : 'var(--primary-dark)') 
                : (isDarkTheme ? '#8E9F90' : 'var(--text-light)')
            }}
          >
            <div 
              className="nav-icon-wrapper" 
              style={{
                position: 'relative',
                background: isActive && isDarkTheme ? 'rgba(168, 217, 74, 0.16)' : undefined,
                borderRadius: isDarkTheme ? '12px' : undefined,
                ...(tab.highlight && !isActive ? { color: isDarkTheme ? '#38BDF8' : '#0284C7' } : {})
              }}
            >
              <Icon size={20} strokeWidth={isActive ? 2.5 : 2} />
              {tab.highlight && !isActive && (
                <span style={{
                  position: 'absolute',
                  top: '1px',
                  right: '3px',
                  width: '6px',
                  height: '6px',
                  backgroundColor: isDarkTheme ? '#38BDF8' : '#0284C7',
                  borderRadius: '50%',
                  boxShadow: isDarkTheme ? '0 0 6px #38BDF8' : 'none'
                }} />
              )}
            </div>
            <span style={{
              fontSize: '11px',
              fontWeight: isActive ? 800 : 500,
              maxWidth: '75px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap'
            }}>
              {tab.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
