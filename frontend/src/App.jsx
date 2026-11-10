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
import ZoneDetailsPage from './features/zones/pages/ZoneDetailsPage';
import IrrigationPlannerPage from './features/irrigation/pages/IrrigationPlannerPage';
import RecommendationDetailsPage from './features/recommendations/pages/RecommendationDetailsPage';
import FarmInsightsPage from './features/insights/pages/FarmInsightsPage';
import AlertsHistoryPage from './features/alerts/pages/AlertsHistoryPage';
import { Smartphone, Monitor } from 'lucide-react';

export default function App() {
  const urlParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
  const paramScreen = urlParams?.get('screen');
  const paramTab = urlParams?.get('tab');
  const paramZone = urlParams?.get('zone');
  const paramRec = urlParams?.get('rec');

  const [currentLang, setCurrentLang] = useState('mr'); // default to Marathi
  const [currentScreen, setCurrentScreen] = useState(paramScreen || 'main'); // 'welcome' | 'register' | 'farm_setup' | 'main'
  const [activeTab, setActiveTab] = useState(paramTab || 'zone_details'); // 'dashboard' | 'irrigation' | 'crops' | 'profile' | 'farm_map' | 'zone_details' | 'recommendation_details'

  // Active selected zone context for Zone Intelligence inspection
  const [selectedZoneId, setSelectedZoneId] = useState(paramZone || 'z3-south-west-003');
  const [selectedFarmId, setSelectedFarmId] = useState(null);

  // Active recommendation context for Recommendation Details deep-dive
  const [selectedRecId, setSelectedRecId] = useState(paramRec || 'rec-c-03');
  const [originatingTab, setOriginatingTab] = useState('zone_details');

  // Responsive frame toggle for desktop preview
  const [isPhoneFrame, setIsPhoneFrame] = useState(false);

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
    if (activeTab === 'zone_details') {
      return {
        title: 'FarmShield AI',
        subtitle: currentLang === 'mr' ? 'विभाग बुद्धिमत्ता व विश्लेषण' : 'Zone Intelligence & Details'
      };
    }
    if (activeTab === 'recommendation_details') {
      return {
        title: 'FarmShield AI',
        subtitle: currentLang === 'mr' ? 'सल्ला विश्लेषण व निर्णय पुरावा' : 'Recommendation Details & Evidence'
      };
    }
    if (activeTab === 'insights') {
      return {
        title: 'FarmShield AI',
        subtitle: currentLang === 'mr' ? 'शेत कल व विश्लेषण' : 'Farm Insights & Historical Trends'
      };
    }
    if (activeTab === 'alerts') {
      return {
        title: 'FarmShield AI',
        subtitle: currentLang === 'mr' ? 'इशारे व शेती इतिहास' : 'Alerts & Activity History'
      };
    }
    return { title: 'FarmShield AI' };
  };

  const headerInfo = getHeaderInfo();

  // Navigation handlers
  const handleToggleAlerts = () => setActiveTab(activeTab === 'alerts' ? 'dashboard' : 'alerts');

  return (
    <>
      <div
        className={`app-viewport-wrapper ${isPhoneFrame ? 'phone-frame-mode' : 'responsive-mode'}`}
        style={!isPhoneFrame ? {
          maxWidth: '100%',
          minHeight: '100vh',
          height: '100vh',
          borderRadius: 0,
          border: 'none',
          boxShadow: 'none'
        } : {}}
      >
        {/* Mobile Phone Top Status Bar Simulation (Only in Phone Shell Preview Mode) */}
        {isPhoneFrame && (
          <div className="phone-status-bar">
            <span>9:41</span>
            <div className="status-bar-notch" />
            <div style={{ display: 'flex', gap: '5px', alignItems: 'center' }}>
              <span>5G</span>
              <span>100%</span>
            </div>
          </div>
        )}

        {/* Global Responsive Glass App Navigation Bar */}
        <Header
          title={headerInfo.title}
          subtitle={headerInfo.subtitle}
          showBack={currentScreen === 'register' || currentScreen === 'farm_setup' || activeTab === 'farm_map' || activeTab === 'zone_details' || activeTab === 'recommendation_details' || activeTab === 'insights' || activeTab === 'alerts'}
          onBack={() => {
            if (currentScreen === 'register') setCurrentScreen('welcome');
            else if (currentScreen === 'farm_setup') setCurrentScreen('register');
            else if (activeTab === 'recommendation_details') setActiveTab(originatingTab || 'zone_details');
            else if (activeTab === 'zone_details') setActiveTab('farm_map');
            else if (activeTab === 'farm_map') setActiveTab('dashboard');
            else if (activeTab === 'insights') setActiveTab('dashboard');
            else if (activeTab === 'alerts') setActiveTab('dashboard');
          }}
          currentLang={currentLang}
          onToggleLang={cycleLanguage}
          farmerName={farmerData.name}
          farmerVillage={farmerData.village}
          activeTab={activeTab}
          onSelectTab={(tab) => setActiveTab(tab)}
          onToggleAlerts={handleToggleAlerts}
          isPhoneFrame={isPhoneFrame}
          onTogglePhoneFrame={() => setIsPhoneFrame(!isPhoneFrame)}
          isDarkTheme={true}
          currentScreen={currentScreen}
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
                <IrrigationPlannerPage
                  farmId={selectedFarmId}
                  initialZoneId={selectedZoneId}
                  currentLang={currentLang}
                  onBack={() => setActiveTab('dashboard')}
                  onSelectRecommendation={(recId) => {
                    setSelectedRecId(recId);
                    setOriginatingTab('irrigation');
                    setActiveTab('recommendation_details');
                  }}
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
                    setSelectedZoneId(zone.id);
                    setSelectedFarmId(zone.farm_id);
                    setActiveTab('zone_details');
                  }}
                />
              )}

              {activeTab === 'zone_details' && (
                <ZoneDetailsPage
                  zoneId={selectedZoneId || 'z1-north-west-001'}
                  farmId={selectedFarmId}
                  currentLang={currentLang}
                  onBack={() => setActiveTab('farm_map')}
                  onNavigateIrrigationPlanner={(rec) => {
                    if (rec?.zone_id) setSelectedZoneId(rec.zone_id);
                    setActiveTab('irrigation');
                  }}
                  onSelectRecommendation={(recId) => {
                    setSelectedRecId(recId);
                    setOriginatingTab('zone_details');
                    setActiveTab('recommendation_details');
                  }}
                />
              )}

              {activeTab === 'recommendation_details' && (
                <RecommendationDetailsPage
                  recommendationId={selectedRecId || 'rec-c-03'}
                  currentLang={currentLang}
                  onBack={() => setActiveTab(originatingTab || 'zone_details')}
                  onNavigateIrrigationPlanner={(rec) => {
                    if (rec?.zone_id) setSelectedZoneId(rec.zone_id);
                    setActiveTab('irrigation');
                  }}
                />
              )}

              {activeTab === 'insights' && (
                <FarmInsightsPage
                  farmId={selectedFarmId}
                  currentLang={currentLang}
                  onBack={() => setActiveTab('dashboard')}
                />
              )}

              {activeTab === 'alerts' && (
                <AlertsHistoryPage
                  farmId={selectedFarmId}
                  currentLang={currentLang}
                  onBack={() => setActiveTab('dashboard')}
                  onSelectRecommendation={(recId) => {
                    setSelectedRecId(recId);
                    setOriginatingTab('alerts');
                    setActiveTab('recommendation_details');
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
