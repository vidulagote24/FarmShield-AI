/**
 * FarmShield AI - FarmMapPage Component (Screen 04: Farm Digital Twin)
 * 
 * Primary interactive geospatial screen displaying farm boundaries,
 * multi-zone management polygons, remote sensing indices, and detailed zone evidence.
 */

import React from 'react';
import { 
  Shield, 
  Layers, 
  RotateCw, 
  AlertCircle, 
  ArrowLeft, 
  Satellite, 
  Sprout, 
  MapPin,
  Maximize2
} from 'lucide-react';
import useFarmMap from '../hooks/useFarmMap.js';
import FarmMapView from '../components/FarmMapView.jsx';
import MapLegend from '../components/MapLegend.jsx';
import MapLayerSelector from '../components/MapLayerSelector.jsx';
import MapFreshnessLabel from '../components/MapFreshnessLabel.jsx';
import ZoneList from '../components/ZoneList.jsx';
import SelectedZonePanel from '../components/SelectedZonePanel.jsx';

export default function FarmMapPage({
  currentLang = 'mr',
  onBack,
  onNavigateZoneDetails,
}) {
  const isMarathi = currentLang === 'mr';

  const {
    farm,
    zones,
    selectedZoneId,
    selectedZone,
    selectZone,
    activeLayer,
    setActiveLayer,
    isLoading,
    error,
    isDemoMode,
    dataMode,
    toggleDataMode,
    resetMap,
    resetViewTrigger,
    refetch,
  } = useFarmMap();

  const hasNdvi = zones.some((z) => z.ndvi_value !== null);
  const hasMoisture = zones.some((z) => z.soil_moisture_pct !== null);

  // Loading State
  if (isLoading) {
    return (
      <div style={{ padding: '24px 20px', textAlign: 'center', minHeight: '60vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          border: '3px solid rgba(197, 243, 107, 0.25)',
          borderTopColor: '#C5F36B',
          animation: 'spin 1s linear infinite',
          marginBottom: '16px',
        }} />
        <h3 style={{ fontSize: '17px', fontWeight: 800, color: '#FFFFFF', marginBottom: '4px' }}>
          {isMarathi ? 'नकाशा डेटा लोड होत आहे...' : 'Loading Farm Digital Twin...'}
        </h3>
        <p style={{ fontSize: '13px', color: '#D5E3D9' }}>
          {isMarathi ? 'सेंटिनेल उपग्रह व पोस्टगिस विभाग लोड करत आहे' : 'Fetching satellite telemetry and zone boundaries'}
        </p>
      </div>
    );
  }

  // Error State (in Live Mode)
  if (error) {
    return (
      <div style={{ padding: '24px 18px', textAlign: 'center' }}>
        <div
          className="glass-card"
          style={{
            padding: '24px 18px',
            border: '1.5px solid rgba(239, 68, 68, 0.45)',
            background: 'rgba(50, 15, 15, 0.75)',
          }}
        >
          <div style={{ color: '#F87171', marginBottom: '12px', display: 'flex', justifyContent: 'center' }}>
            <AlertCircle size={44} />
          </div>
          <h3 style={{ fontSize: '18px', fontWeight: 800, color: '#FFFFFF', marginBottom: '6px' }}>
            {isMarathi ? 'डेटा कनेक्शन त्रुटी' : 'API Connection Error'}
          </h3>
          <p style={{ fontSize: '13px', color: '#FECACA', marginBottom: '18px', lineHeight: 1.45 }}>
            {error}
          </p>

          <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
            <button
              onClick={refetch}
              className="btn-glass-primary"
              style={{ maxWidth: '180px', fontSize: '13px' }}
            >
              <RotateCw size={15} />
              <span>{isMarathi ? 'पुन्हा प्रयत्न करा' : 'Retry Connection'}</span>
            </button>

            <button
              onClick={toggleDataMode}
              className="btn-glass-secondary"
              style={{ maxWidth: '180px', fontSize: '13px', color: '#C5F36B' }}
            >
              <span>{isMarathi ? 'नमुना मोड पहा' : 'Switch to Demo Mode'}</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  const farmName = isMarathi ? (farm?.name || 'शेताचा डिजिटल नकाशा') : (farm?.name_en || farm?.name || 'Farm Digital Twin');
  const cropName = farm?.crop_type || farm?.crop || 'कापूस (Cotton)';
  const areaDisplay = farm?.area_acres ? `${farm.area_acres} ${isMarathi ? 'एकर' : 'Acres'}` : (farm?.area_hectares ? `${farm.area_hectares} ha` : '3.5 एकर');

  return (
    <div style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: '14px', position: 'relative', zIndex: 10 }}>
      {/* Top Header Card */}
      <div
        className="glass-card"
        style={{
          padding: '16px',
          background: 'rgba(10, 43, 28, 0.70)',
          border: '1px solid rgba(197, 243, 107, 0.35)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '2px' }}>
              <span className="glass-pill" style={{ color: '#C5F36B', fontSize: '11px' }}>
                <Shield size={12} />
                {isMarathi ? 'डिजिटल ट्विन' : 'Digital Twin'}
              </span>
              <span style={{ fontSize: '11px', color: '#B6C8BB' }}>
                📍 {farm?.location_name || 'बारामती, पुणे'}
              </span>
            </div>
            <h2 style={{ fontSize: '20px', fontWeight: 800, color: '#FFFFFF', letterSpacing: '-0.3px', marginTop: '2px' }}>
              {farmName}
            </h2>
          </div>

          {/* Mode Switcher Pill */}
          <button
            onClick={toggleDataMode}
            title={isMarathi ? 'लाइव्ह / नमुना डेटा मोड बदला' : 'Toggle Live API / Demo Mode'}
            style={{
              padding: '4px 10px',
              borderRadius: '20px',
              border: isDemoMode ? '1px solid #F59E0B' : '1px solid #65C76A',
              background: isDemoMode ? 'rgba(245, 158, 11, 0.20)' : 'rgba(101, 199, 106, 0.20)',
              color: isDemoMode ? '#FBBF24' : '#C5F36B',
              fontSize: '11px',
              fontWeight: 800,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              transition: 'all 0.15s ease',
            }}
          >
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: isDemoMode ? '#FBBF24' : '#65C76A' }} />
            <span>{isDemoMode ? 'DEMO' : 'LIVE'}</span>
          </button>
        </div>

        {/* Quick Parameters Row */}
        <div style={{ display: 'flex', gap: '8px', marginTop: '10px', flexWrap: 'wrap' }}>
          <span className="glass-pill" style={{ color: '#FFFFFF' }}>
            🌾 {cropName}
          </span>
          <span className="glass-pill" style={{ color: '#FFFFFF' }}>
            📏 {areaDisplay}
          </span>
          <span className="glass-pill" style={{ color: '#C5F36B' }}>
            🗺️ {zones.length} {isMarathi ? 'व्यवस्थापन विभाग' : 'Zones'}
          </span>
        </div>
      </div>

      {/* Freshness & Attribution Banner */}
      <MapFreshnessLabel
        farm={farm}
        isDemoMode={isDemoMode}
        currentLang={currentLang}
        activeLayer={activeLayer}
      />

      {/* Layer Selector */}
      <MapLayerSelector
        activeLayer={activeLayer}
        onSelectLayer={setActiveLayer}
        hasNdviData={hasNdvi}
        hasMoistureData={hasMoisture}
        currentLang={currentLang}
      />

      {/* Interactive GIS Map Viewport */}
      <FarmMapView
        farm={farm}
        zones={zones}
        selectedZoneId={selectedZoneId}
        onSelectZone={selectZone}
        activeLayer={activeLayer}
        resetViewTrigger={resetViewTrigger}
        onResetView={resetMap}
        currentLang={currentLang}
        height="360px"
      />

      {/* Map Legend */}
      <MapLegend currentLang={currentLang} activeLayer={activeLayer} />

      {/* Active Selected Zone Detail Panel */}
      {selectedZone && (
        <SelectedZonePanel
          zone={selectedZone}
          onClose={() => selectZone(null)}
          onViewZoneDetails={onNavigateZoneDetails}
          currentLang={currentLang}
        />
      )}

      {/* Accessible List-Based Zone Selector Alternative */}
      <ZoneList
        zones={zones}
        selectedZoneId={selectedZoneId}
        onSelectZone={selectZone}
        currentLang={currentLang}
      />
    </div>
  );
}
