import React from 'react';
import { Sprout, Layers, Calendar, ChevronRight, Check } from 'lucide-react';

export default function FarmSetup({
  farmData,
  onChangeFarm,
  onComplete,
  onBack,
  t
}) {
  const cropList = [
    { id: 'cotton', label: t.crops.cotton, icon: '🌿' },
    { id: 'soybean', label: t.crops.soybean, icon: '🌱' },
    { id: 'sugarcane', label: t.crops.sugarcane, icon: '🎋' },
    { id: 'onion', label: t.crops.onion, icon: '🧅' },
    { id: 'wheat', label: t.crops.wheat, icon: '🌾' },
    { id: 'tomato', label: t.crops.tomato, icon: '🍅' },
  ];

  const soilList = [
    { id: 'black', label: t.soils.black },
    { id: 'red', label: t.soils.red },
    { id: 'loam', label: t.soils.loam },
    { id: 'clay', label: t.soils.clay },
  ];

  const handleSubmit = (e) => {
    e.preventDefault();
    onComplete();
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
        {/* Progress indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
          <div style={{ flex: 1, height: '6px', background: '#C5F36B', borderRadius: '3px', boxShadow: '0 0 8px rgba(197, 243, 107, 0.3)' }} />
          <div style={{ flex: 1, height: '6px', background: '#C5F36B', borderRadius: '3px', boxShadow: '0 0 8px rgba(197, 243, 107, 0.3)' }} />
          <div style={{ flex: 1, height: '6px', background: 'rgba(255, 255, 255, 0.16)', borderRadius: '3px' }} />
        </div>

        {/* Title */}
        <div style={{ marginBottom: '18px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <span className="glass-pill" style={{ color: '#C5F36B' }}>
              <Sprout size={14} />
              पायरी २ / Step 2
            </span>
            <span className="demo-tag">
              🌱 नमुना शेती पॅरामीटर्स
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
            {t.farmSetupTitle}
          </h2>
          <p style={{ fontSize: '13px', color: '#D5E3D9' }}>
            {t.farmSetupSubtitle}
          </p>
        </div>

        {/* Form Container */}
        <div className="glass-card" style={{ padding: '20px 18px' }}>
          <form onSubmit={handleSubmit}>
            {/* Farm Area */}
            <div className="farmer-input-group">
              <label className="farmer-input-label">
                {t.farmArea} *
              </label>
              <input
                type="number"
                step="0.1"
                className="glass-input"
                value={farmData.area}
                onChange={(e) => onChangeFarm('area', e.target.value)}
                placeholder={t.farmAreaPlaceholder}
                required
              />
            </div>

            {/* Select Main Crop */}
            <div className="farmer-input-group">
              <label className="farmer-input-label">
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                  <Sprout size={15} color="#C5F36B" />
                  {t.cropSelect} *
                </span>
              </label>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: '8px'
              }}>
                {cropList.map((crop) => {
                  const isSelected = farmData.crop === crop.id;
                  return (
                    <button
                      key={crop.id}
                      type="button"
                      onClick={() => onChangeFarm('crop', crop.id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '11px 12px',
                        borderRadius: '14px',
                        border: isSelected ? '2px solid #C5F36B' : '1px solid rgba(255, 255, 255, 0.16)',
                        background: isSelected ? 'rgba(197, 243, 107, 0.18)' : 'rgba(255, 255, 255, 0.08)',
                        backdropFilter: 'blur(12px)',
                        WebkitBackdropFilter: 'blur(12px)',
                        color: '#FFFFFF',
                        fontWeight: 700,
                        fontSize: '12.5px',
                        cursor: 'pointer',
                        textAlign: 'left',
                        boxShadow: isSelected ? '0 0 14px rgba(197, 243, 107, 0.25)' : 'none',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <span style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden' }}>
                        <span style={{ fontSize: '16px' }}>{crop.icon}</span>
                        <span style={{ 
                          whiteSpace: 'nowrap', 
                          overflow: 'hidden', 
                          textOverflow: 'ellipsis',
                          color: isSelected ? '#C5F36B' : '#FFFFFF' 
                        }}>
                          {crop.label}
                        </span>
                      </span>
                      {isSelected && <Check size={14} color="#C5F36B" strokeWidth={3} style={{ flexShrink: 0 }} />}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Soil Type */}
            <div className="farmer-input-group">
              <label className="farmer-input-label">
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                  <Layers size={15} color="#C5F36B" />
                  {t.soilSelect} *
                </span>
              </label>
              <select
                className="glass-input"
                style={{
                  background: 'rgba(7, 31, 22, 0.85)',
                  color: '#FFFFFF'
                }}
                value={farmData.soil}
                onChange={(e) => onChangeFarm('soil', e.target.value)}
              >
                {soilList.map((soil) => (
                  <option 
                    key={soil.id} 
                    value={soil.id} 
                    style={{ background: '#0D3826', color: '#FFFFFF' }}
                  >
                    {soil.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Sowing Date */}
            <div className="farmer-input-group" style={{ marginBottom: 0 }}>
              <label className="farmer-input-label">
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                  <Calendar size={15} color="#C5F36B" />
                  {t.sowingDate}
                </span>
              </label>
              <input
                type="date"
                className="glass-input"
                value={farmData.sowingDate}
                onChange={(e) => onChangeFarm('sowingDate', e.target.value)}
              />
              <span style={{ fontSize: '11px', color: '#D5E3D9', marginTop: '6px', display: 'block', lineHeight: '1.4' }}>
                💡 पेरणी १ ऑक्टोबर २०२६ (आज ९ नोव्हेंबर २०२६ नुसार वाढीचा ३९ वा दिवस - शाकीय वाढ)
              </span>
            </div>
          </form>
        </div>
      </div>

      <div style={{ marginTop: '22px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <button
          type="button"
          className="btn-glass-primary"
          onClick={handleSubmit}
        >
          <span>{t.saveFarmBtn}</span>
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
