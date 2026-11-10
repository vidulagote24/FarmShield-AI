import React from 'react';
import { User, Phone, MapPin, ChevronRight, ShieldCheck, Info } from 'lucide-react';

export default function Register({ 
  formData, 
  onChangeForm, 
  onNext, 
  onBack, 
  t 
}) {
  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      alert(t.fullNamePlaceholder);
      return;
    }
    onNext();
  };

  return (
    <div style={{
      padding: '20px 20px 32px',
      display: 'flex',
      flexDirection: 'column',
      minHeight: '100%',
      justifyContent: 'space-between',
      position: 'relative',
      zIndex: 10
    }}>
      <div>
        {/* Glass Progress Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
          <div style={{ 
            flex: 1, 
            height: '6px', 
            background: '#C5F36B', 
            borderRadius: '3px',
            boxShadow: '0 0 10px rgba(197, 243, 107, 0.4)'
          }} />
          <div style={{ flex: 1, height: '6px', background: 'rgba(255, 255, 255, 0.16)', borderRadius: '3px' }} />
          <div style={{ flex: 1, height: '6px', background: 'rgba(255, 255, 255, 0.16)', borderRadius: '3px' }} />
        </div>

        {/* Header Title with Demo Profile badge */}
        <div style={{ marginBottom: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span className="glass-pill" style={{ color: '#C5F36B' }}>
              <ShieldCheck size={14} />
              पायरी १ / Step 1
            </span>
            <span className="demo-tag">
              🔒 काल्पनिक / Demo Data
            </span>
          </div>

          <h2 style={{
            fontSize: '23px',
            fontWeight: 800,
            color: '#FFFFFF',
            letterSpacing: '-0.3px',
            marginTop: '6px',
            marginBottom: '4px',
            textShadow: '0 2px 8px rgba(0, 0, 0, 0.4)'
          }}>
            {t.loginRegister}
          </h2>
          <p style={{ fontSize: '13px', color: '#D5E3D9', lineHeight: '1.45' }}>
            {t.enterDetails}
          </p>
        </div>

        {/* Registration Form in Glass Card */}
        <div className="glass-card" style={{ padding: '20px 18px' }}>
          <form onSubmit={handleSubmit}>
            {/* Full Name */}
            <div className="farmer-input-group">
              <label className="farmer-input-label">
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: '#FFFFFF' }}>
                  <User size={15} color="#C5F36B" />
                  {t.fullName} *
                </span>
              </label>
              <input
                type="text"
                className="glass-input"
                value={formData.name}
                onChange={(e) => onChangeForm('name', e.target.value)}
                placeholder={t.fullNamePlaceholder}
                required
              />
            </div>

            {/* Mobile Number */}
            <div className="farmer-input-group">
              <label className="farmer-input-label">
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: '#FFFFFF' }}>
                  <Phone size={15} color="#C5F36B" />
                  {t.phone} *
                </span>
              </label>
              <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                <span style={{
                  position: 'absolute',
                  left: '16px',
                  fontSize: '14px',
                  fontWeight: 700,
                  color: '#C5F36B'
                }}>
                  +91
                </span>
                <input
                  type="tel"
                  maxLength={10}
                  className="glass-input"
                  style={{ paddingLeft: '54px' }}
                  value={formData.phone}
                  onChange={(e) => onChangeForm('phone', e.target.value)}
                  placeholder={t.phonePlaceholder}
                />
              </div>
            </div>

            {/* Village / District */}
            <div className="farmer-input-group">
              <label className="farmer-input-label">
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: '#FFFFFF' }}>
                  <MapPin size={15} color="#C5F36B" />
                  {t.village} *
                </span>
              </label>
              <input
                type="text"
                className="glass-input"
                value={formData.village}
                onChange={(e) => onChangeForm('village', e.target.value)}
                placeholder={t.villagePlaceholder}
                required
              />
            </div>

            {/* Privacy & Hackathon Demo note */}
            <div className="glass-panel" style={{
              padding: '12px 14px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              marginTop: '10px',
              border: '1px solid rgba(197, 243, 107, 0.25)'
            }}>
              <Info size={18} color="#C5F36B" style={{ flexShrink: 0 }} />
              <span style={{ fontSize: '11.5px', color: '#D5E3D9', fontWeight: 500, lineHeight: '1.4' }}>
                गोपनीयता संरक्षण: हॅकाथॉन डेमोसाठी काल्पनिक माहिती वापरण्यात आली आहे.
              </span>
            </div>
          </form>
        </div>
      </div>

      <div style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <button
          type="button"
          className="btn-glass-primary"
          onClick={handleSubmit}
        >
          <span>{t.registerBtn}</span>
          <ChevronRight size={20} />
        </button>

        {onBack && (
          <button
            type="button"
            className="btn-glass-secondary"
            onClick={onBack}
          >
            मागे जा / Back
          </button>
        )}
      </div>
    </div>
  );
}
