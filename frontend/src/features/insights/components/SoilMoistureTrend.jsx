/**
 * FarmShield AI - SoilMoistureTrend Component
 * 
 * Multi-zone Soil Moisture historical trend chart using Chart.js & react-chartjs-2.
 * 
 * Scientific Integrity Rules:
 * - Plots only verified dated measurements.
 * - Preserves physical unit (% volumetric water content).
 * - Distinguishes individual management zones with dedicated colored traces.
 * - Does not interpolate missing dates or treat missing data as zero.
 * - Displays an honest insufficient-data explanation when < 2 data points exist.
 */

import React from 'react';
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
import { Droplets, Info, AlertCircle } from 'lucide-react';
import InsightsEmptyState from './InsightsEmptyState.jsx';

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

const ZONE_COLORS = [
  { stroke: '#22C55E', bg: 'rgba(34, 197, 94, 0.12)', name: 'Zone A' },
  { stroke: '#F59E0B', bg: 'rgba(245, 158, 11, 0.12)', name: 'Zone B' },
  { stroke: '#38BDF8', bg: 'rgba(56, 189, 248, 0.12)', name: 'Zone C' },
  { stroke: '#F43F5E', bg: 'rgba(244, 63, 94, 0.12)', name: 'Zone D' },
];

export default function SoilMoistureTrend({
  observations = [],
  zones = [],
  isDemoMode = false,
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';

  // Filter observations for soil moisture with valid numeric values and non-failed quality
  const smObs = observations.filter((o) => {
    const isSM = o.observation_type === 'soil_moisture' || o.metric_type === 'soil_moisture';
    const meta = o.metadata || o.metadata_json || {};
    const quality = meta.quality || meta.quality_status;
    const isFailedQuality = ['cloud_obscured', 'probe_disconnected', 'error', 'failed', 'invalid'].includes(quality);
    return isSM && o.value !== null && o.value !== undefined && !isFailedQuality;
  });

  // Group by zone
  const zoneGroups = new Map();
  zones.forEach((z) => {
    zoneGroups.set(z.id, {
      zone: z,
      obs: [],
    });
  });

  smObs.forEach((o) => {
    if (o.zone_id && zoneGroups.has(o.zone_id)) {
      zoneGroups.get(o.zone_id).obs.push(o);
    } else {
      // General or unassigned zone observation
      if (!zoneGroups.has('unassigned')) {
        zoneGroups.set('unassigned', { zone: { id: 'unassigned', zone_code: 'ALL', zone_name: 'Farm General' }, obs: [] });
      }
      zoneGroups.get('unassigned').obs.push(o);
    }
  });

  // Collect all unique chronological date timestamps across all zones
  const allTimestamps = Array.from(
    new Set(smObs.map((o) => new Date(o.observed_at).toISOString()))
  ).sort();

  const labels = allTimestamps.map((iso) => {
    try {
      const d = new Date(iso);
      return `${d.getDate()} ${d.toLocaleString('default', { month: 'short' })}`;
    } catch {
      return iso;
    }
  });

  // Build chart datasets
  const datasets = [];
  let colorIdx = 0;

  zoneGroups.forEach((group, zoneId) => {
    if (group.obs.length === 0) return;

    const color = ZONE_COLORS[colorIdx % ZONE_COLORS.length];
    colorIdx++;

    // Map each chronological timestamp to this zone's value if present (or null if not observed on this date)
    const dataPoints = allTimestamps.map((iso) => {
      const match = group.obs.find(
        (o) => new Date(o.observed_at).toISOString() === iso
      );
      return match ? match.value : null;
    });

    datasets.push({
      label: `${group.zone.zone_code || 'ZONE'} (${group.zone.zone_name || group.zone.name})`,
      data: dataPoints,
      borderColor: color.stroke,
      backgroundColor: color.bg,
      borderWidth: 2.2,
      pointBackgroundColor: color.stroke,
      pointBorderColor: '#FFFFFF',
      pointBorderWidth: 1.5,
      pointRadius: 4.5,
      pointHoverRadius: 7,
      spanGaps: true, // Connect lines across sparse sampling dates without faking data points
      tension: 0.2,
    });
  });

  const chartData = {
    labels,
    datasets,
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: '#E2E8F0',
          font: { size: 11, family: 'Inter, system-ui, sans-serif', weight: 'bold' },
          boxWidth: 12,
          padding: 10,
        },
      },
      tooltip: {
        backgroundColor: 'rgba(7, 31, 22, 0.95)',
        titleColor: '#C5F36B',
        bodyColor: '#FFFFFF',
        borderColor: 'rgba(197, 243, 107, 0.4)',
        borderWidth: 1,
        padding: 10,
        callbacks: {
          label: (context) => {
            const val = context.parsed.y;
            return ` ${context.dataset.label}: ${val !== null ? `${val}%` : 'N/A'}`;
          },
        },
      },
    },
    scales: {
      x: {
        grid: { color: 'rgba(255, 255, 255, 0.08)' },
        ticks: { color: '#94A3B8', font: { size: 10.5 } },
      },
      y: {
        min: 0,
        max: 100,
        grid: { color: 'rgba(255, 255, 255, 0.08)' },
        ticks: {
          color: '#94A3B8',
          font: { size: 10.5 },
          callback: (value) => `${value}%`,
        },
        title: {
          display: true,
          text: isMarathi ? 'माती ओलावा (%)' : 'Soil Moisture (% Volumetric)',
          color: '#38BDF8',
          font: { size: 11, weight: 'bold' },
        },
      },
    },
  };

  const totalPoints = smObs.length;

  return (
    <div
      className="glass-card"
      style={{
        padding: '18px',
        marginBottom: '16px',
        background: 'rgba(7, 31, 22, 0.85)',
        border: '1.5px solid rgba(56, 189, 248, 0.35)',
      }}
    >
      {/* Chart Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'rgba(56, 189, 248, 0.20)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#38BDF8',
            }}
          >
            <Droplets size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#FFFFFF', margin: 0 }}>
              {isMarathi ? 'मातीतील ओलावा कल (Soil Moisture Trends)' : 'Soil Moisture Trends (% Volumetric)'}
            </h3>
            <div style={{ fontSize: '11px', color: '#B6C8BB' }}>
              {isMarathi ? 'प्रत्यक्ष सेन्सर नोंदी व ओलावा घट (Depletion)' : 'Physical capacitive sensor depth measurements'}
            </div>
          </div>
        </div>

        <span
          className="glass-pill"
          style={{
            fontSize: '11px',
            color: '#38BDF8',
            border: '1px solid rgba(56, 189, 248, 0.4)',
          }}
        >
          {totalPoints} {isMarathi ? 'नोंदी' : 'Points'}
        </span>
      </div>

      {/* Chart Canvas or Insufficient Data State */}
      {totalPoints < 2 ? (
        <div
          style={{
            padding: '24px 16px',
            textAlign: 'center',
            background: 'rgba(255, 255, 255, 0.03)',
            borderRadius: '12px',
            border: '1px dashed rgba(255, 255, 255, 0.15)',
          }}
        >
          <AlertCircle size={28} color="#94A3B8" style={{ margin: '0 auto 8px auto' }} />
          <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#E2E8F0', margin: '0 0 4px 0' }}>
            {isMarathi ? 'कल दर्शवण्यासाठी पुरेसा डेटा नाही' : 'Insufficient Data to Plot Trend'}
          </h4>
          <p style={{ fontSize: '11.5px', color: '#94A3B8', margin: 0, lineHeight: 1.45 }}>
            {isMarathi 
              ? 'कल रेषा काढण्यासाठी किमान २ स्वतंत्र तारखांच्या नोंदी आवश्यक असतात. डेटा न बनवता किंवा अंदाज न बांधता ही माहिती दाखवली जाते.' 
              : 'At least 2 dated observations are required to render a trend curve without synthesizing data.'}
          </p>
        </div>
      ) : (
        <div style={{ height: '240px', width: '100%', position: 'relative' }}>
          <Line data={chartData} options={chartOptions} />
        </div>
      )}

      {/* Technical Footer Notice */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          marginTop: '12px',
          paddingTop: '8px',
          borderTop: '1px solid rgba(255, 255, 255, 0.08)',
          fontSize: '10.5px',
          color: '#8E9F90',
        }}
      >
        <Info size={12} color="#38BDF8" style={{ flexShrink: 0 }} />
        <span>
          {isMarathi 
            ? 'प्रत्येक बिंदू ३० सेमी खोलीवरील प्रत्यक्ष तपासणी दर्शवतो. मध्यंतरीच्या तारखांचा खोटा अंदाज बांधलेला नाही.' 
            : 'Each node represents an actual physical sensor observation. No synthetic intermediate values are plotted.'}
        </span>
      </div>
    </div>
  );
}

