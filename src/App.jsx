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

  const isDarkDashboard = currentScreen === 'main' && activeTab === 'dashboard';

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
    return { title: 'FarmShield AI' };
  };

  const headerInfo = getHeaderInfo();

  return (
    <>
      {/* Top Desktop Controls: Toggle between Phone Frame and Responsive View */}
      <div className="top-desktop-controls">
        <span style={{ fontSize: '12px', fontWeight: 700, color: '#334435' }}>
          📱 FarmShield AI Mobile Preview
        </span>
        <button
          onClick={() => setIsPhoneFrame(!isPhoneFrame)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            background: 'var(--primary-light)',
            color: 'var(--primary-dark)',
            border: 'none',
            padding: '5px 10px',
            borderRadius: '16px',
            fontSize: '11px',
            fontWeight: 700,
            cursor: 'pointer'
          }}
        >
          {isPhoneFrame ? <Monitor size={14} /> : <Smartphone size={14} />}
          <span>{isPhoneFrame ? 'Full Width' : 'Phone Shell'}</span>
        </button>
      </div>

      <div 
        className={`app-viewport-wrapper ${isDarkDashboard ? 'dark-dashboard-mode' : ''}`} 
        style={!isPhoneFrame ? { maxWidth: '100%', minHeight: '100vh', height: '100vh', borderRadius: 0, border: 'none', boxShadow: 'none' } : {}}
      >
        {/* Mobile Phone Top Status Bar Simulation */}
        <div 
          className="phone-status-bar"
          style={isDarkDashboard ? { color: '#FFFFFF' } : {}}
        >
          <span>9:41</span>
          <div className="status-bar-notch" style={isDarkDashboard ? { backgroundColor: '#071F16', border: '1px solid rgba(255,255,255,0.1)' } : {}} />
          <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
            <span>5G</span>
            <span>100%</span>
          </div>
        </div>

        {/* Global App Header */}
        <Header
          title={headerInfo.title}
          subtitle={headerInfo.subtitle}
          showBack={currentScreen === 'register' || currentScreen === 'farm_setup'}
          onBack={() => {
            if (currentScreen === 'register') setCurrentScreen('welcome');
            if (currentScreen === 'farm_setup') setCurrentScreen('register');
          }}
          currentLang={currentLang}
          onToggleLang={cycleLanguage}
          farmerName={farmerData.name}
          isDarkTheme={isDarkDashboard}
        />

        {/* Main Screen Content View */}
        <main className={`screen-scroll-container ${currentScreen !== 'main' ? 'onboarding-screen' : ''} ${isDarkDashboard ? 'dark-scroll-container' : ''}`}>
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
            </>
          )}
        </main>

        {/* Bottom Navigation Bar (Visible in Main App) */}
        {currentScreen === 'main' && (
          <BottomNav
            activeTab={activeTab}
            onSelectTab={(tab) => setActiveTab(tab)}
            t={t}
            isDarkTheme={isDarkDashboard}
          />
        )}
      </div>
    </>
  );
}
