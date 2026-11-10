import React, { useState } from 'react';
import { translations } from './data/translations';
import Header from './components/Header';
import BottomNav from './components/BottomNav';
import Welcome from './pages/Welcome';
import Register from './pages/Register';
import FarmSetup from './pages/FarmSetup';
import Dashboard from './pages/Dashboard';
import Irrigation from './pages/Irrigation';
import Crops from './pages/Crops';
import Profile from './pages/Profile';
import FarmMapPage from './features/farm-map/pages/FarmMapPage';
import { Smartphone, Monitor } from 'lucide-react';

export default function App() {
  const [currentLang, setCurrentLang] = useState('mr'); // default to Marathi
  const [currentScreen, setCurrentScreen] = useState('welcome'); // 'welcome' | 'register' | 'farm_setup' | 'main'
  const [activeTab, setActiveTab] = useState('dashboard'); // 'dashboard' | 'irrigation' | 'crops' | 'profile'
  
  // Responsive frame toggle for desktop preview
  const [isPhoneFrame, setIsPhoneFrame] = useState(true);

  // Fictional farmer profile data for Hackathon demo privacy
  const [farmerData, setFarmerData] = useState({
    name: 'आनंदराव शिंदे',
    phone: '9800000000',
    village: 'बारामती, पुणे (Plot #4)'
  });

  // Farm configuration data (Sowing date 2026-10-01 = 39 days ago as of 9 Nov 2026)
  const [farmData, setFarmData] = useState({
    area: '3.5',
    crop: 'cotton',
    soil: 'black',
    sowingDate: '2026-10-01'
  });

  const t = translations[currentLang] || translations.mr;

  const cycleLanguage = () => {
    if (currentLang === 'mr') setCurrentLang('hi');
    else if (currentLang === 'hi') setCurrentLang('en');
    else setCurrentLang('mr');
  };

  const handleUpdateFarmer = (field, value) => {
    setFarmerData(prev => ({ ...prev, [field]: value }));
  };

  const handleUpdateFarm = (field, value) => {
    setFarmData(prev => ({ ...prev, [field]: value }));
  };

  // Determine header title based on active view
  const getHeaderInfo = () => {
    if (currentScreen === 'welcome') {
      return { title: 'FarmShield AI', subtitle: 'शेतकरी सहाय्यक' };
    }
    if (currentScreen === 'register') {
      return { title: t.loginRegister, subtitle: 'पायरी १ / ३ (Demo)' };
    }
    if (currentScreen === 'farm_setup') {
      return { title: t.farmSetupTitle, subtitle: 'पायरी २ / ३' };
    }
    // Main navigation tabs
    if (activeTab === 'dashboard') {
      return { title: 'FarmShield AI', subtitle: `${farmerData.name || 'शेतकरी'} • ${farmData.area} एकर` };
    }
    if (activeTab === 'irrigation') {
      return { title: t.irrigation.title, subtitle: 'स्मार्ट पाणी निर्णय' };
    }
    if (activeTab === 'crops') {
      return { title: t.nav.crops, subtitle: 'रोग व कीड रक्षण' };
    }
    if (activeTab === 'profile') {
      return { title: t.nav.profile, subtitle: 'खाते व शेत तपशील' };
    }
    if (activeTab === 'farm_map') {
      return { 
        title: 'FarmShield AI', 
        subtitle: currentLang === 'mr' ? 'शेताचा डिजिटल नकाशा (४ विभाग)' : 'Farm Digital Twin (4 Zones)' 
      };
    }
    return { title: 'FarmShield AI' };
  };

  const headerInfo = getHeaderInfo();

  return (
    <>
      {/* Top Desktop Controls: Toggle between Phone Frame and Responsive View */}
      <div className="top-desktop-controls">
        <span style={{ fontSize: '12px', fontWeight: 800, color: '#C5F36B', display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span>🌾</span> FarmShield AI Glassmorphic Preview
        </span>
        <button
          onClick={() => setActiveTab(activeTab === 'farm_map' ? 'dashboard' : 'farm_map')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            background: activeTab === 'farm_map' ? 'rgba(197, 243, 107, 0.25)' : 'rgba(255, 255, 255, 0.12)',
            backdropFilter: 'blur(10px)',
            color: activeTab === 'farm_map' ? '#C5F36B' : '#FFFFFF',
            border: activeTab === 'farm_map' ? '1px solid #C5F36B' : '1px solid rgba(255, 255, 255, 0.2)',
            padding: '5px 12px',
            borderRadius: '16px',
            fontSize: '11.5px',
            fontWeight: 700,
            cursor: 'pointer',
            transition: 'all 0.2s ease',
          }}
        >
          <span>🗺️ {activeTab === 'farm_map' ? (currentLang === 'mr' ? 'डॅशबोर्ड' : 'Dashboard') : (currentLang === 'mr' ? 'नकाशा' : 'Farm Map')}</span>
        </button>
        <button
          onClick={() => setIsPhoneFrame(!isPhoneFrame)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            background: 'rgba(255, 255, 255, 0.12)',
            backdropFilter: 'blur(10px)',
            color: '#FFFFFF',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            padding: '5px 12px',
            borderRadius: '16px',
            fontSize: '11.5px',
            fontWeight: 700,
            cursor: 'pointer',
            transition: 'all 0.2s ease'
          }}
        >
          {isPhoneFrame ? <Monitor size={14} color="#C5F36B" /> : <Smartphone size={14} color="#C5F36B" />}
          <span>{isPhoneFrame ? 'Full Width' : 'Phone Shell'}</span>
        </button>
      </div>

      <div 
        className="app-viewport-wrapper" 
        style={!isPhoneFrame ? { 
          maxWidth: '100%', 
          minHeight: '100vh', 
          height: '100vh', 
          borderRadius: 0, 
          border: 'none', 
          boxShadow: 'none' 
        } : {}}
      >
        {/* Mobile Phone Top Status Bar Simulation */}
        <div className="phone-status-bar">
          <span>9:41</span>
          <div className="status-bar-notch" />
          <div style={{ display: 'flex', gap: '5px', alignItems: 'center' }}>
            <span>5G</span>
            <span>100%</span>
          </div>
        </div>

        {/* Global Glass App Header */}
        <Header
          title={headerInfo.title}
          subtitle={headerInfo.subtitle}
          showBack={currentScreen === 'register' || currentScreen === 'farm_setup' || activeTab === 'farm_map'}
          onBack={() => {
            if (currentScreen === 'register') setCurrentScreen('welcome');
            else if (currentScreen === 'farm_setup') setCurrentScreen('register');
            else if (activeTab === 'farm_map') setActiveTab('dashboard');
          }}
          currentLang={currentLang}
          onToggleLang={cycleLanguage}
          farmerName={farmerData.name}
          isDarkTheme={true}
        />

        {/* Main Screen Content View */}
        <main className={`screen-scroll-container ${currentScreen !== 'main' ? 'onboarding-screen' : ''}`}>
          {currentScreen === 'welcome' && (
            <Welcome
              currentLang={currentLang}
              onSelectLang={(code) => setCurrentLang(code)}
              onNext={() => setCurrentScreen('register')}
              t={t}
            />
          )}

          {currentScreen === 'register' && (
            <Register
              formData={farmerData}
              onChangeForm={handleUpdateFarmer}
              onNext={() => setCurrentScreen('farm_setup')}
              onBack={() => setCurrentScreen('welcome')}
              t={t}
            />
          )}

          {currentScreen === 'farm_setup' && (
            <FarmSetup
              farmData={farmData}
              onChangeFarm={handleUpdateFarm}
              onComplete={() => setCurrentScreen('main')}
              onBack={() => setCurrentScreen('register')}
              t={t}
            />
          )}

          {currentScreen === 'main' && (
            <>
              {activeTab === 'dashboard' && (
                <Dashboard
                  farmerData={farmerData}
                  farmData={farmData}
                  onNavigateTab={(tab) => setActiveTab(tab)}
                  t={t}
                  currentLang={currentLang}
                />
              )}

              {activeTab === 'irrigation' && (
                <Irrigation
                  farmData={farmData}
                  t={t}
                  currentLang={currentLang}
                />
              )}

              {activeTab === 'crops' && (
                <Crops
                  farmData={farmData}
                  t={t}
                  currentLang={currentLang}
                />
              )}

              {activeTab === 'profile' && (
                <Profile
                  farmerData={farmerData}
                  farmData={farmData}
                  onResetSetup={() => setCurrentScreen('register')}
                  currentLang={currentLang}
                  onChangeLang={(code) => setCurrentLang(code)}
                  t={t}
                />
              )}

              {activeTab === 'farm_map' && (
                <FarmMapPage
                  currentLang={currentLang}
                  onBack={() => setActiveTab('dashboard')}
                  onNavigateZoneDetails={(zone) => {
                    // Pre-hook for Zone Details
                  }}
                />
              )}
            </>
          )}
        </main>

        {/* Floating Glass Bottom Navigation Bar (Visible in Main App) */}
        {currentScreen === 'main' && (
          <BottomNav
            activeTab={activeTab}
            onSelectTab={(tab) => setActiveTab(tab)}
            t={t}
            isDarkTheme={true}
          />
        )}
      </div>
    </>
  );
}
