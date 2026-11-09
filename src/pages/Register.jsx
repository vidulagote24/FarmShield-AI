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
      justifyContent: 'space-between'
    }}>
      <div>
        {/* Progress indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '18px' }}>
          <div style={{ flex: 1, height: '6px', background: 'var(--primary)', borderRadius: '3px' }} />
          <div style={{ flex: 1, height: '6px', background: 'var(--border-color)', borderRadius: '3px' }} />
          <div style={{ flex: 1, height: '6px', background: 'var(--border-color)', borderRadius: '3px' }} />
        </div>

        {/* Header Title with Demo Profile badge */}
        <div style={{ marginBottom: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span className="status-pill" style={{
              background: 'var(--primary-light)',
              color: 'var(--primary-dark)'
            }}>
              <ShieldCheck size={14} />
              पायरी १ / Step 1
            </span>
            <span className="demo-tag">
              🔒 काल्पनिक / Demo Data
            </span>
          </div>

          <h2 style={{
            fontSize: '22px',
            fontWeight: 800,
            color: 'var(--text-main)',
            letterSpacing: '-0.3px',
            marginTop: '4px',
            marginBottom: '4px'
          }}>
            {t.loginRegister}
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: '1.4' }}>
            {t.enterDetails}
          </p>
        </div>

        {/* Registration Form */}
        <form onSubmit={handleSubmit}>
          {/* Full Name */}
          <div className="farmer-input-group">
            <label className="farmer-input-label">
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                <User size={15} color="var(--primary)" />
                {t.fullName} *
              </span>
            </label>
            <input
              type="text"
              className="farmer-input"
              value={formData.name}
              onChange={(e) => onChangeForm('name', e.target.value)}
              placeholder={t.fullNamePlaceholder}
              required
            />
          </div>

          {/* Mobile Number */}
          <div className="farmer-input-group">
            <label className="farmer-input-label">
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                <Phone size={15} color="var(--primary)" />
                {t.phone} *
              </span>
            </label>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <span style={{
                position: 'absolute',
                left: '14px',
                fontSize: '14px',
                fontWeight: 700,
                color: 'var(--text-muted)'
              }}>
                +91
              </span>
              <input
                type="tel"
                maxLength={10}
                className="farmer-input"
                style={{ paddingLeft: '52px' }}
                value={formData.phone}
                onChange={(e) => onChangeForm('phone', e.target.value)}
                placeholder={t.phonePlaceholder}
              />
            </div>
          </div>

          {/* Village / District */}
          <div className="farmer-input-group">
            <label className="farmer-input-label">
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                <MapPin size={15} color="var(--primary)" />
                {t.village} *
              </span>
            </label>
            <input
              type="text"
              className="farmer-input"
              value={formData.village}
              onChange={(e) => onChangeForm('village', e.target.value)}
              placeholder={t.villagePlaceholder}
              required
            />
          </div>

          {/* Privacy & Hackathon Demo note */}
          <div style={{
            background: 'var(--primary-light)',
            padding: '10px 14px',
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginTop: '8px'
          }}>
            <Info size={16} color="var(--primary)" />
            <span style={{ fontSize: '11.5px', color: 'var(--primary-dark)', fontWeight: 600 }}>
              गोपनीयता संरक्षण: हॅकाथॉन डेमोसाठी काल्पनिक माहिती वापरण्यात आली आहे.
            </span>
          </div>
        </form>
      </div>

      <div style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <button
          type="button"
          className="btn-farmer-primary"
          onClick={handleSubmit}
        >
          <span>{t.registerBtn}</span>
          <ChevronRight size={20} />
        </button>

        {onBack && (
          <button
            type="button"
            className="btn-farmer-secondary"
            onClick={onBack}
          >
            मागे जा / Back
          </button>
        )}
      </div>
    </div>
  );
}
