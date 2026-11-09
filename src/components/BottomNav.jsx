import React from 'react';
import { Home, Droplets, Sprout, User } from 'lucide-react';

export default function BottomNav({ activeTab, onSelectTab, t, isDarkTheme = true }) {
  const tabs = [
    { id: 'dashboard', label: t.nav.home, icon: Home },
    { id: 'irrigation', label: t.nav.irrigation, icon: Droplets, highlight: true },
    { id: 'crops', label: t.nav.crops, icon: Sprout },
    { id: 'profile', label: t.nav.profile, icon: User },
  ];

  return (
    <nav 
      className="bottom-nav"
      style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        height: '74px',
        background: 'rgba(7, 31, 22, 0.84)',
        backdropFilter: 'blur(24px) saturate(160%)',
        WebkitBackdropFilter: 'blur(24px) saturate(160%)',
        borderTop: '1px solid rgba(255, 255, 255, 0.14)',
        boxShadow: '0 -8px 32px rgba(0, 0, 0, 0.45)',
        display: 'flex',
        justifyContent: 'space-around',
        alignItems: 'center',
        padding: '0 8px',
        zIndex: 50
      }}
    >
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            className={`nav-tab-item ${isActive ? 'active' : ''}`}
            onClick={() => onSelectTab(tab.id)}
            style={{
              color: isActive ? '#C5F36B' : '#A3B8A8',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '3px',
              flex: 1,
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '6px 0',
              transition: 'all 0.2s ease'
            }}
          >
            <div 
              className="nav-icon-wrapper" 
              style={{
                position: 'relative',
                width: '38px',
                height: '32px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: isActive ? 'rgba(197, 243, 107, 0.18)' : 'transparent',
                borderRadius: '12px',
                boxShadow: isActive ? '0 0 14px rgba(197, 243, 107, 0.25)' : 'none',
                color: isActive ? '#C5F36B' : (tab.highlight ? '#38BDF8' : '#D5E3D9'),
                transition: 'all 0.2s ease'
              }}
            >
              <Icon size={20} strokeWidth={isActive ? 2.5 : 2} />
              {tab.highlight && !isActive && (
                <span style={{
                  position: 'absolute',
                  top: '2px',
                  right: '4px',
                  width: '6px',
                  height: '6px',
                  backgroundColor: '#38BDF8',
                  borderRadius: '50%',
                  boxShadow: '0 0 8px #38BDF8'
                }} />
              )}
            </div>
            <span style={{
              fontSize: '11px',
              fontWeight: isActive ? 800 : 500,
              maxWidth: '75px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              color: isActive ? '#C5F36B' : '#A3B8A8',
              letterSpacing: '-0.2px'
            }}>
              {tab.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
