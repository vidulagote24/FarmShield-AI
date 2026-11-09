import React from 'react';
import { User, Phone, MapPin, Sprout, Layers, Calendar, Globe, LogOut, CheckCircle, ShieldCheck } from 'lucide-react';

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
    <div style={{ 
      padding: '16px 18px', 
      display: 'flex', 
      flexDirection: 'column', 
      gap: '16px',
      position: 'relative',
      zIndex: 10 
    }}>
      
      {/* Profile Hero Card */}
      <div className="glass-card" style={{ textAlign: 'center', padding: '24px 18px' }}>
        <div style={{
          width: '76px',
          height: '76px',
          borderRadius: '50%',
          background: 'linear-gradient(135deg, rgba(101, 199, 106, 0.3) 0%, rgba(13, 56, 38, 0.85) 100%)',
          border: '1.5px solid rgba(197, 243, 107, 0.45)',
          color: '#C5F36B',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 12px',
          boxShadow: '0 0 20px rgba(197, 243, 107, 0.25)'
        }}>
          <User size={40} />
        </div>

        <h3 style={{ fontSize: '19px', fontWeight: 800, color: '#FFFFFF', marginBottom: '4px' }}>
          {farmerData.name || 'शेतकरी मित्र'}
        </h3>
        <p style={{ fontSize: '13px', color: '#D5E3D9' }}>
          +91 {farmerData.phone || '9876543210'} • {farmerData.village || 'बारामती'}
        </p>

        <div className="glass-pill" style={{
          marginTop: '12px',
          color: '#69D98A',
          background: 'rgba(105, 217, 138, 0.16)',
          border: '1px solid rgba(105, 217, 138, 0.35)'
        }}>
          <ShieldCheck size={14} />
          <span>{currentLang === 'mr' ? 'प्रमाणित शेतकरी खाते (Verified)' : 'Verified Farmer Account'}</span>
        </div>
      </div>

      {/* Farm Profile Summary */}
      <div className="glass-card">
        <h4 style={{ fontSize: '14.5px', fontWeight: 800, color: '#FFFFFF', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          🌾 {t.farmSetupTitle}
        </h4>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '11px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13.5px', paddingBottom: '9px', borderBottom: '1px solid rgba(255, 255, 255, 0.10)' }}>
            <span style={{ color: '#B6C8BB' }}>{t.cropSelect}</span>
            <span style={{ fontWeight: 800, color: '#FFFFFF' }}>{cropName}</span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13.5px', paddingBottom: '9px', borderBottom: '1px solid rgba(255, 255, 255, 0.10)' }}>
            <span style={{ color: '#B6C8BB' }}>{t.farmArea}</span>
            <span style={{ fontWeight: 800, color: '#FFFFFF' }}>{farmData.area} एकर</span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13.5px', paddingBottom: '9px', borderBottom: '1px solid rgba(255, 255, 255, 0.10)' }}>
            <span style={{ color: '#B6C8BB' }}>{t.soilSelect}</span>
            <span style={{ fontWeight: 800, color: '#FFFFFF' }}>{soilName}</span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13.5px' }}>
            <span style={{ color: '#B6C8BB' }}>{t.sowingDate}</span>
            <span style={{ fontWeight: 800, color: '#C5F36B' }}>{farmData.sowingDate || '२०२६-१०-०१'}</span>
          </div>
        </div>
      </div>

      {/* Language Preferences */}
      <div className="glass-card">
        <h4 style={{ fontSize: '14.5px', fontWeight: 800, color: '#FFFFFF', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          🌐 {t.selectLang}
        </h4>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
          {[
            { code: 'mr', label: 'मराठी' },
            { code: 'hi', label: 'हिंदी' },
            { code: 'en', label: 'English' }
          ].map((item) => {
            const isSelected = currentLang === item.code;
            return (
              <button
                key={item.code}
                onClick={() => onChangeLang(item.code)}
                style={{
                  padding: '11px',
                  borderRadius: '14px',
                  border: isSelected ? '2px solid #C5F36B' : '1px solid rgba(255, 255, 255, 0.16)',
                  background: isSelected ? 'rgba(197, 243, 107, 0.20)' : 'rgba(255, 255, 255, 0.08)',
                  backdropFilter: 'blur(12px)',
                  color: isSelected ? '#C5F36B' : '#FFFFFF',
                  fontWeight: 800,
                  fontSize: '13px',
                  cursor: 'pointer',
                  boxShadow: isSelected ? '0 0 12px rgba(197, 243, 107, 0.25)' : 'none',
                  transition: 'all 0.15s ease'
                }}
              >
                {item.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Edit Setup or Switch Account */}
      <button
        onClick={onResetSetup}
        className="btn-glass-secondary"
      >
        <LogOut size={16} />
        <span>{currentLang === 'mr' ? 'नोंदणी व शेताची माहिती बदला' : 'Edit Profile & Farm Setup'}</span>
      </button>
    </div>
  );
}
