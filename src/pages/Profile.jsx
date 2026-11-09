import React from 'react';
import { User, Phone, MapPin, Sprout, Layers, Calendar, Globe, LogOut, CheckCircle } from 'lucide-react';

export default function Profile({ 
  farmerData, 
  farmData, 
  onResetSetup, 
  currentLang, 
  onChangeLang, 
  t 
}) {
  const cropName = t.crops[farmData.crop] || farmData.crop;
  const soilName = t.soils[farmData.soil] || farmData.soil;

  return (
    <div style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      
      {/* Profile Card */}
      <div className="farmer-card" style={{ textAlign: 'center', padding: '24px 18px' }}>
        <div style={{
          width: '74px',
          height: '74px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #2E7D32, #1B5E20)',
          color: '#FFFFFF',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 12px',
          boxShadow: 'var(--shadow-sm)'
        }}>
          <User size={38} />
        </div>

        <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-main)', marginBottom: '2px' }}>
          {farmerData.name || 'शेतकरी मित्र'}
        </h3>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          +91 {farmerData.phone || '9876543210'} • {farmerData.village || 'बारामती'}
        </p>

        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          background: 'var(--primary-light)',
          color: 'var(--primary-dark)',
          padding: '4px 12px',
          borderRadius: '20px',
          fontSize: '12px',
          fontWeight: 700,
          marginTop: '10px'
        }}>
          <CheckCircle size={14} />
          {currentLang === 'mr' ? 'प्रमाणित शेतकरी खाते' : 'Verified Farmer Account'}
        </div>
      </div>

      {/* Farm Profile Summary */}
      <div className="farmer-card">
        <h4 style={{ fontSize: '14px', fontWeight: 800, color: 'var(--text-main)', marginBottom: '12px' }}>
          🌾 {t.farmSetupTitle}
        </h4>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', paddingBottom: '8px', borderBottom: '1px solid var(--border-color)' }}>
            <span style={{ color: 'var(--text-muted)' }}>{t.cropSelect}</span>
            <span style={{ fontWeight: 700, color: 'var(--text-main)' }}>{cropName}</span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', paddingBottom: '8px', borderBottom: '1px solid var(--border-color)' }}>
            <span style={{ color: 'var(--text-muted)' }}>{t.farmArea}</span>
            <span style={{ fontWeight: 700, color: 'var(--text-main)' }}>{farmData.area} एकर</span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', paddingBottom: '8px', borderBottom: '1px solid var(--border-color)' }}>
            <span style={{ color: 'var(--text-muted)' }}>{t.soilSelect}</span>
            <span style={{ fontWeight: 700, color: 'var(--text-main)' }}>{soilName}</span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
            <span style={{ color: 'var(--text-muted)' }}>{t.sowingDate}</span>
            <span style={{ fontWeight: 700, color: 'var(--text-main)' }}>{farmData.sowingDate || '२०२६-१०-०१'}</span>
          </div>
        </div>
      </div>

      {/* Language Preferences */}
      <div className="farmer-card">
        <h4 style={{ fontSize: '14px', fontWeight: 800, color: 'var(--text-main)', marginBottom: '12px' }}>
          🌐 {t.selectLang}
        </h4>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
          {[
            { code: 'mr', label: 'मराठी' },
            { code: 'hi', label: 'हिंदी' },
            { code: 'en', label: 'English' }
          ].map((item) => (
            <button
              key={item.code}
              onClick={() => onChangeLang(item.code)}
              style={{
                padding: '10px',
                borderRadius: '12px',
                border: currentLang === item.code ? '2px solid var(--primary)' : '1px solid var(--border-color)',
                background: currentLang === item.code ? 'var(--primary-light)' : '#FFFFFF',
                color: currentLang === item.code ? 'var(--primary-dark)' : 'var(--text-main)',
                fontWeight: 700,
                fontSize: '13px',
                cursor: 'pointer'
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* Edit Setup or Switch Account */}
      <button
        onClick={onResetSetup}
        className="btn-farmer-secondary"
      >
        <LogOut size={16} />
        <span>{currentLang === 'mr' ? 'नोंदणी व शेताची माहिती बदला' : 'Edit Profile & Farm Setup'}</span>
      </button>
    </div>
  );
}
