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
      justifyContent: 'space-between'
    }}>
      <div>
        {/* Progress indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '18px' }}>
          <div style={{ flex: 1, height: '6px', background: 'var(--primary)', borderRadius: '3px' }} />
          <div style={{ flex: 1, height: '6px', background: 'var(--primary)', borderRadius: '3px' }} />
          <div style={{ flex: 1, height: '6px', background: 'var(--border-color)', borderRadius: '3px' }} />
        </div>

        {/* Title */}
        <div style={{ marginBottom: '18px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <span className="status-pill" style={{
              background: 'var(--primary-light)',
              color: 'var(--primary-dark)'
            }}>
              <Sprout size={14} />
              पायरी २ / Step 2
            </span>
            <span className="demo-tag">
              🌱 नमुना शेती पॅरामीटर्स
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
            {t.farmSetupTitle}
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            {t.farmSetupSubtitle}
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Farm Area */}
          <div className="farmer-input-group">
            <label className="farmer-input-label">
              {t.farmArea} *
            </label>
            <input
              type="number"
              step="0.1"
              className="farmer-input"
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
                <Sprout size={15} color="var(--primary)" />
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
                      padding: '10px 12px',
                      borderRadius: '12px',
                      border: isSelected ? '2px solid var(--primary)' : '1.5px solid var(--border-color)',
                      background: isSelected ? 'var(--primary-light)' : '#FFFFFF',
                      color: isSelected ? 'var(--primary-dark)' : 'var(--text-main)',
                      fontWeight: 700,
                      fontSize: '12.5px',
                      cursor: 'pointer',
                      textAlign: 'left'
                    }}
                  >
                    <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontSize: '16px' }}>{crop.icon}</span>
                      <span>{crop.label}</span>
                    </span>
                    {isSelected && <Check size={14} color="var(--primary)" strokeWidth={3} />}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Soil Type */}
          <div className="farmer-input-group">
            <label className="farmer-input-label">
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                <Layers size={15} color="var(--primary)" />
                {t.soilSelect} *
              </span>
            </label>
            <select
              className="farmer-input"
              value={farmData.soil}
              onChange={(e) => onChangeFarm('soil', e.target.value)}
            >
              {soilList.map((soil) => (
                <option key={soil.id} value={soil.id}>
                  {soil.label}
                </option>
              ))}
            </select>
          </div>

          {/* Sowing Date */}
          <div className="farmer-input-group">
            <label className="farmer-input-label">
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                <Calendar size={15} color="var(--primary)" />
                {t.sowingDate}
              </span>
            </label>
            <input
              type="date"
              className="farmer-input"
              value={farmData.sowingDate}
              onChange={(e) => onChangeFarm('sowingDate', e.target.value)}
            />
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px', display: 'block' }}>
              💡 पेरणी १ ऑक्टोबर २०२६ (आज ९ नोव्हेंबर २०२६ नुसार वाढीचा ३९ वा दिवस - शाकीय वाढ)
            </span>
          </div>
        </form>
      </div>

      <div style={{ marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <button
          type="button"
          className="btn-farmer-primary"
          onClick={handleSubmit}
        >
          <span>{t.saveFarmBtn}</span>
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
