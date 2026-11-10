/**
 * FarmShield AI - TelemetryTrendChart Component
 * 
 * Plots actual dated observation series using Chart.js & react-chartjs-2.
 * 
 * Strict Scientific & Agronomic Rules (per AGENTS.md, AI_SPEC.md):
 * - Plots only actual dated observations; preserves real timestamps and units.
 * - Does not interpolate or fabricate synthetic intermediate data points.
 * - Does not combine unrelated variables (e.g. % moisture vs 0..1 NDVI) on an ambiguous scale.
 * - Displays an honest insufficient-data explanation when <2 dated observations exist.
 * - Explicitly labels simulated curves in Demo Mode.
 */

import React, { useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { TrendingUp, Droplets, Activity, Calendar, Info, CloudOff } from 'lucide-react';
import InsufficientDataState from './InsufficientDataState.jsx';

// Register Chart.js modular controllers and plugins
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function TelemetryTrendChart({
  observations = [],
  isDemoMode = false,
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';
  const [activeVariable, setActiveVariable] = useState('soil_moisture'); // 'soil_moisture' | 'vegetation_index'

  // Extract soil moisture series (must have valid number value)
  const soilMoistureSeries = observations
    .filter((o) => o.observation_type === 'soil_moisture' && o.value !== null && o.value !== undefined)
    .sort((a, b) => new Date(a.observed_at) - new Date(b.observed_at));

  // Extract NDVI vegetation series (must have valid number value)
  const ndviSeries = observations
    .filter((o) => o.observation_type === 'vegetation_index' && o.value !== null && o.value !== undefined)
    .sort((a, b) => new Date(a.observed_at) - new Date(b.observed_at));

  const activeSeries = activeVariable === 'soil_moisture' ? soilMoistureSeries : ndviSeries;
  const isSoil = activeVariable === 'soil_moisture';

  // Format date labels
  const labels = activeSeries.map((obs) => {
    try {
      const d = new Date(obs.observed_at);
      return `${d.getDate()} ${d.toLocaleString('default', { month: 'short' })}`;
    } catch (e) {
      return obs.observed_at || 'Date';
    }
  });

  const dataValues = activeSeries.map((obs) => obs.value);

  const chartData = {
    labels,
    datasets: [
      {
        label: isSoil
          ? (isMarathi ? 'माती ओलावा (%)' : 'Soil Moisture (%)')
          : (isMarathi ? 'कॅनॉपी NDVI इंडेक्स' : 'Vegetation Index (NDVI)'),
        data: dataValues,
        borderColor: isSoil ? '#38BDF8' : '#65C76A',
        backgroundColor: isSoil ? 'rgba(56, 189, 248, 0.14)' : 'rgba(101, 199, 106, 0.14)',
        borderWidth: 2.5,
        pointBackgroundColor: isSoil ? '#38BDF8' : '#65C76A',
        pointBorderColor: '#FFFFFF',
        pointBorderWidth: 1.5,
        pointRadius: 4.5,
        pointHoverRadius: 7,
        fill: true,
        tension: 0.25,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        backgroundColor: 'rgba(7, 31, 22, 0.95)',
        titleColor: '#C5F36B',
        bodyColor: '#FFFFFF',
        borderColor: isSoil ? '#38BDF8' : '#65C76A',
        borderWidth: 1,
        padding: 10,
        cornerRadius: 10,
        displayColors: false,
        callbacks: {
          label: (context) => {
            const val = context.parsed.y;
            return isSoil ? `${val}% Soil Moisture` : `NDVI: ${val}`;
          },
        },
      },
    },
    scales: {
      x: {
        grid: {
          color: 'rgba(255, 255, 255, 0.08)',
        },
        ticks: {
          color: '#8E9F90',
          font: {
            size: 11,
          },
        },
      },
      y: {
        min: isSoil ? 30 : 0.2,
        max: isSoil ? 90 : 0.9,
        grid: {
          color: 'rgba(255, 255, 255, 0.08)',
        },
        ticks: {
          color: '#8E9F90',
          font: {
            size: 11,
          },
          callback: (value) => (isSoil ? `${value}%` : value),
        },
      },
    },
  };

  return (
    <div
      className="glass-card"
      style={{
        padding: '18px',
        background: 'rgba(7, 31, 22, 0.75)',
        border: '1px solid rgba(197, 243, 107, 0.30)',
      }}
    >
      {/* Header and Variable Switcher */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'rgba(197, 243, 107, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#C5F36B',
            }}
          >
            <TrendingUp size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#FFFFFF', margin: 0 }}>
              {isMarathi ? 'टेलिमेट्री कल व इतिहास (Trends)' : 'Telemetry Historical Trends'}
            </h3>
            <div style={{ fontSize: '11px', color: '#B6C8BB' }}>
              {isMarathi ? 'अचूक कालावधीनुसार प्रत्यक्ष निरीक्षणे' : 'Dated in-situ and satellite observations'}
            </div>
          </div>
        </div>

        {/* Variable Switcher Tabs */}
        <div
          style={{
            display: 'flex',
            background: 'rgba(255, 255, 255, 0.08)',
            padding: '3px',
            borderRadius: '12px',
            gap: '2px',
          }}
        >
          <button
            onClick={() => setActiveVariable('soil_moisture')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '5px 10px',
              borderRadius: '9px',
              border: 'none',
              background: activeVariable === 'soil_moisture' ? '#38BDF8' : 'transparent',
              color: activeVariable === 'soil_moisture' ? '#071F16' : '#D5E3D9',
              fontSize: '11px',
              fontWeight: 700,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <Droplets size={12} />
            <span>{isMarathi ? 'माती ओलावा' : 'Moisture'}</span>
          </button>

          <button
            onClick={() => setActiveVariable('vegetation_index')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '5px 10px',
              borderRadius: '9px',
              border: 'none',
              background: activeVariable === 'vegetation_index' ? '#65C76A' : 'transparent',
              color: activeVariable === 'vegetation_index' ? '#071F16' : '#D5E3D9',
              fontSize: '11px',
              fontWeight: 700,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <Activity size={12} />
            <span>NDVI</span>
          </button>
        </div>
      </div>

      {/* Chart Canvas or Insufficient Data State */}
      {activeSeries.length < 2 ? (
        <InsufficientDataState
          title={isMarathi 
            ? `${isSoil ? 'माती ओलावा' : 'NDVI'} ट्रेंडसाठी अपुरा इतिहास` 
            : `Insufficient Historical ${isSoil ? 'Moisture' : 'NDVI'} Data`}
          message={isMarathi 
            ? `कालक्रमानुसार कल (Trend) दाखवण्यासाठी किमान २ स्वतंत्र तारखांची निरीक्षणे आवश्यक आहेत. सध्या ${activeSeries.length} निरीक्षण नोंदवले आहे.` 
            : `Displaying an empirical trend requires at least 2 dated observations. Currently ${activeSeries.length} observation is recorded.`}
          reason={isMarathi ? 'शेत सेन्सर किंवा उपग्रह कालखंडामध्ये पुरेशी आवर्तने पूर्ण झालेली नाहीत' : 'Fewer than 2 observation epochs exist in database'}
          currentLang={currentLang}
          icon={TrendingUp}
        />
      ) : (
        <div>
          <div style={{ height: '190px', width: '100%', position: 'relative' }}>
            <Line data={chartData} options={chartOptions} />
          </div>

          {/* Footer Metadata */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '10px', fontSize: '10.5px', color: '#8E9F90' }}>
            <span>
              {isSoil ? 'Threshold MAD: 45% soil moisture' : 'Sentinel-2 Level-2A Multi-spectral (10m)'}
            </span>
            {isDemoMode && (
              <span style={{ color: '#FBBF24', fontWeight: 700 }}>
                🌾 {isMarathi ? 'सिम्युलेटेड ट्रेंड वक्र' : 'Simulated curve'}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

