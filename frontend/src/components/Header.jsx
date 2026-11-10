import React, { useRef } from 'react';
import {
  Globe,
  Bell,
  ChevronLeft,
  Shield,
  Home,
  Map as MapIcon,
  Droplets,
  TrendingUp,
  Sprout,
  User,
  Smartphone,
  Monitor,
  MapPin
} from 'lucide-react';

export default function Header({
  title,
  subtitle,
  showBack,
  onBack,
  currentLang = 'mr',
  onToggleLang,
  farmerName = 'आनंदराव शिंदे',
  farmerVillage = 'बारामती, पुणे',
  activeTab = 'dashboard',
  onSelectTab,
  onToggleAlerts,
  isPhoneFrame = false,
  onTogglePhoneFrame,
  isDarkTheme = true,
  currentScreen = 'main'
}) {
  const headerRef = useRef(null);

  const langLabels = {
    mr: 'मराठी',
    hi: 'हिंदी',
    en: 'EN'
  };

  // Primary navigation destinations - exact existing routes & labels preserved
  const navItems = [
    {
      id: 'dashboard',
      label: currentLang === 'mr' ? 'डॅशबोर्ड' : currentLang === 'hi' ? 'डैशबोर्ड' : 'Dashboard',
      icon: Home,
      match: ['dashboard'],
    },
    {
      id: 'farm_map',
      label: currentLang === 'mr' ? 'शेताचा नकाशा' : currentLang === 'hi' ? 'खेत नक्शा' : 'Farm Map',
      icon: MapIcon,
      match: ['farm_map', 'zone_details'],
    },
    {
      id: 'irrigation',
      label: currentLang === 'mr' ? 'पाणी नियोजन' : currentLang === 'hi' ? 'सिंचाई' : 'Irrigation',
      icon: Droplets,
      match: ['irrigation'],
    },
    {
      id: 'insights',
      label: currentLang === 'mr' ? 'कल विश्लेषण' : currentLang === 'hi' ? 'विश्लेषण' : 'Insights',
      icon: TrendingUp,
      match: ['insights'],
    },
    {
      id: 'alerts',
      label: currentLang === 'mr' ? 'इशारे' : currentLang === 'hi' ? 'इशारे' : 'Alerts',
      icon: Bell,
      match: ['alerts'],
      hasDot: true,
    },
    {
      id: 'crops',
      label: currentLang === 'mr' ? 'पीक रक्षण' : currentLang === 'hi' ? 'फसल सुरक्षा' : 'Crops',
      icon: Sprout,
      match: ['crops'],
    },
  ];

  const handleNavClick = (tabId) => {
    if (tabId === 'alerts' && onToggleAlerts) {
      onToggleAlerts();
    } else if (onSelectTab) {
      onSelectTab(tabId);
    }
  };

  const isItemActive = (item) => {
    return item.match.includes(activeTab);
  };

  const isMainApp = currentScreen === 'main';

  return (
    <header
      ref={headerRef}
      className="main-navbar"
      role="banner"
    >
      <div className="navbar-container">

        {/* ============================================================== */}
        {/* 1. LEFT: Brand Identity & Subpage Back Navigation              */}
        {/* ============================================================== */}
        <div className="navbar-brand-section">
          {showBack ? (
            <button
              onClick={onBack}
              className="navbar-back-btn"
              aria-label={currentLang === 'mr' ? 'मागे जा' : currentLang === 'hi' ? 'पीछे जाएं' : 'Go back'}
            >
              <ChevronLeft size={20} />
              <span className="navbar-back-label">
                {currentLang === 'mr' ? 'मागे' : currentLang === 'hi' ? 'वापस' : 'Back'}
              </span>
            </button>
          ) : (
            <div
              className="navbar-logo-btn"
              onClick={() => onSelectTab && onSelectTab('dashboard')}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === 'Enter' && onSelectTab) onSelectTab('dashboard'); }}
              aria-label="FarmShield AI Home"
            >
              <div className="navbar-shield-icon">
                <Shield size={20} />
              </div>
              <div className="navbar-title-group">
                <div className="navbar-brand-row">
                  <span className="navbar-brand-name">FarmShield AI</span>
                  <span className="navbar-pro-badge">PRO</span>
                </div>
                {subtitle && (
                  <span className="navbar-subtitle-text">{subtitle}</span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ============================================================== */}
        {/* 2. CENTER: Polished Horizontal Nav (>= 768px Desktop/Tablet)    */}
        {/* ============================================================== */}
        {isMainApp && (
          <nav
            className="navbar-desktop-nav"
            role="navigation"
            aria-label="Desktop Navigation"
          >
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = isItemActive(item);
              return (
                <button
                  key={item.id}
                  onClick={() => handleNavClick(item.id)}
                  className={`navbar-nav-item ${active ? 'active' : ''}`}
                  aria-current={active ? 'page' : undefined}
                  title={item.label}
                >
                  <Icon size={16} strokeWidth={active ? 2.4 : 1.9} />
                  <span>{item.label}</span>
                  {item.hasDot && !active && (
                    <span className="navbar-unread-dot" aria-hidden="true" />
                  )}
                  {active && <span className="navbar-active-bar" aria-hidden="true" />}
                </button>
              );
            })}
          </nav>
        )}

        {/* ============================================================== */}
        {/* 3. RIGHT: Actions (Language, Notifications, Profile, Toggle)  */}
        {/* ============================================================== */}
        <div className="navbar-actions-section">
          {/* Farmer Location Chip (Desktop >= 1024px) */}
          {isMainApp && farmerVillage && (
            <div className="navbar-farmer-chip" title={`${farmerName} (${farmerVillage})`}>
              <MapPin size={13} color="#C5F36B" />
              <span className="farmer-chip-text">{farmerVillage.split(',')[0]}</span>
            </div>
          )}

          {/* Bilingual Language Switcher */}
          <button
            onClick={onToggleLang}
            className="navbar-action-btn navbar-lang-btn"
            title={currentLang === 'mr' ? 'भाषा बदला (Change Language)' : 'Change Language'}
            aria-label={`Current language: ${langLabels[currentLang]}. Click to switch.`}
          >
            <Globe size={14} />
            <span className="lang-code-text">{langLabels[currentLang] || 'EN'}</span>
          </button>

          {/* Notifications Bell Button */}
          {isMainApp && (
            <button
              onClick={() => handleNavClick('alerts')}
              className={`navbar-action-btn navbar-icon-btn ${activeTab === 'alerts' ? 'active-icon' : ''}`}
              title={currentLang === 'mr' ? 'इशारे व सूचना' : 'Alerts and Notifications'}
              aria-label="Alerts and Notifications"
            >
              <Bell size={17} />
              <span className="navbar-pulse-badge" aria-hidden="true" />
            </button>
          )}

          {/* Farmer Profile Button */}
          {isMainApp && (
            <button
              onClick={() => onSelectTab && onSelectTab('profile')}
              className={`navbar-action-btn navbar-profile-btn ${activeTab === 'profile' ? 'active-icon' : ''}`}
              title={currentLang === 'mr' ? 'शेतकरी खाते' : 'Farmer Profile'}
              aria-label="Farmer Profile"
            >
              <User size={17} />
            </button>
          )}

          {/* Device Shell Simulator Toggle (Desktop >= 1024px) */}
          {isMainApp && onTogglePhoneFrame && (
            <button
              onClick={onTogglePhoneFrame}
              className="navbar-action-btn navbar-frame-toggle-btn"
              title={isPhoneFrame ? 'Switch to Full Width Responsive View' : 'Switch to Phone Shell Simulator View'}
              aria-label="Toggle frame layout"
            >
              {isPhoneFrame ? <Monitor size={15} color="#C5F36B" /> : <Smartphone size={15} color="#C5F36B" />}
              <span className="frame-toggle-label">{isPhoneFrame ? 'Full Width' : 'Phone Shell'}</span>
            </button>
          )}
        </div>
      </div>

      {/* ============================================================== */}
      {/* 4. MOBILE: Visible Multi-Row Navigation Grid (< 768px)         */}
      {/*    All 6 primary destinations visible simultaneously in 2 cols */}
      {/*    No horizontal scrolling, no clipping, no hidden menus       */}
      {/* ============================================================== */}
      {isMainApp && (
        <nav
          className="navbar-mobile-nav"
          role="navigation"
          aria-label="Mobile Primary Navigation"
        >
          <div className="navbar-mobile-grid">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = isItemActive(item);
              return (
                <button
                  key={`mob-${item.id}`}
                  onClick={() => handleNavClick(item.id)}
                  className={`navbar-mobile-item ${active ? 'active' : ''}`}
                  aria-current={active ? 'page' : undefined}
                >
                  <div className="mobile-item-icon-wrap">
                    <Icon size={16} strokeWidth={active ? 2.5 : 1.9} />
                    {item.hasDot && !active && (
                      <span className="navbar-unread-dot mobile-unread-dot" aria-hidden="true" />
                    )}
                  </div>
                  <span className="mobile-item-label">{item.label}</span>
                  {active && <span className="mobile-active-indicator" aria-hidden="true" />}
                </button>
              );
            })}
          </div>
        </nav>
      )}
    </header>
  );
}
