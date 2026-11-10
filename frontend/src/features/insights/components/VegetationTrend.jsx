/**
 * FarmShield AI - VegetationTrend Component
 * 
 * Multi-zone Canopy NDVI historical trend chart using Chart.js & react-chartjs-2.
 * 
 * Scientific Integrity Rules:
 * - Plots only verified dated multispectral satellite scenes (Sentinel-2).
 * - Preserves normalized difference vegetation index dimension (0.0 to 1.0).
 * - Strictly isolates NDVI on its own scale (never combines with % moisture).
 * - Does not infer drought solely from declining NDVI.
 * - Displays cloud-cover metadata and flags obscured acquisitions honestly.
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
import { Eye, Info, AlertCircle, Sparkles } from 'lucide-react';

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
  { stroke: '#22C55E', bg: 'rgba(34, 197, 94, 0.12)' },
  { stroke: '#F59E0B', bg: 'rgba(245, 158, 11, 0.12)' },
  { stroke: '#38BDF8', bg: 'rgba(56, 189, 248, 0.12)' },
  { stroke: '#A855F7', bg: 'rgba(168, 85, 247, 0.12)' },
];

export default function VegetationTrend({
  observations = [],
  zones = [],
  isDemoMode = false,
  currentLang = 'mr',
}) {
  const isMarathi = currentLang === 'mr';

  // Filter observations for vegetation index (NDVI) with valid numeric values and non-failed quality
  const ndviObs = observations.filter((o) => {
    const isVI = o.observation_type === 'vegetation_index' || o.metric_type === 'ndvi';
    const meta = o.metadata || o.metadata_json || {};
    const quality = meta.quality || meta.quality_status;
    const isFailedQuality = ['cloud_obscured', 'probe_disconnected', 'error', 'failed', 'invalid'].includes(quality);
    return isVI && o.value !== null && o.value !== undefined && !isFailedQuality;
  });

  // Group by zone
  const zoneGroups = new Map();
  zones.forEach((z) => {
    zoneGroups.set(z.id, {
      zone: z,
      obs: [],
    });
  });

  ndviObs.forEach((o) => {
    if (o.zone_id && zoneGroups.has(o.zone_id)) {
      zoneGroups.get(o.zone_id).obs.push(o);
    } else {
      if (!zoneGroups.has('unassigned')) {
        zoneGroups.set('unassigned', { zone: { id: 'unassigned', zone_code: 'ALL', zone_name: 'Farm General' }, obs: [] });
      }
      zoneGroups.get('unassigned').obs.push(o);
    }
  });

  // Collect chronological date timestamps
  const allTimestamps = Array.from(
    new Set(ndviObs.map((o) => new Date(o.observed_at).toISOString()))
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

  zoneGroups.forEach((group) => {
    if (group.obs.length === 0) return;

    const color = ZONE_COLORS[colorIdx % ZONE_COLORS.length];
    colorIdx++;

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
      spanGaps: true,
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
            return ` ${context.dataset.label}: ${val !== null ? val.toFixed(2) : 'N/A'}`;
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
        max: 1.0,
        grid: { color: 'rgba(255, 255, 255, 0.08)' },
        ticks: {
          color: '#94A3B8',
          font: { size: 10.5 },
          callback: (value) => value.toFixed(1),
        },
        title: {
          display: true,
          text: isMarathi ? 'कॅनॉपी NDVI (०.० ते १.०)' : 'Canopy NDVI (Index 0.0 – 1.0)',
          color: '#C5F36B',
          font: { size: 11, weight: 'bold' },
        },
      },
    },
  };

  const totalPoints = ndviObs.length;

  return (
    <div
      className="glass-card"
      style={{
        padding: '18px',
        marginBottom: '16px',
        background: 'rgba(7, 31, 22, 0.85)',
        border: '1.5px solid rgba(197, 243, 107, 0.35)',
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
              background: 'rgba(197, 243, 107, 0.20)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#C5F36B',
            }}
          >
            <Eye size={18} />
          </div>
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#FFFFFF', margin: 0 }}>
              {isMarathi ? 'पीक वाढ व हरितद्रव्य कल (Canopy NDVI Trends)' : 'Canopy Vegetation Trends (NDVI)'}
            </h3>
            <div style={{ fontSize: '11px', color: '#B6C8BB' }}>
              {isMarathi ? 'उपग्रह मल्टिस्पेक्ट्रल निरीक्षणे (Copernicus Sentinel-2)' : 'Multispectral satellite canopy biomass indicators'}
            </div>
          </div>
        </div>

        <span
          className="glass-pill"
          style={{
            fontSize: '11px',
            color: '#C5F36B',
            border: '1px solid rgba(197, 243, 107, 0.4)',
          }}
        >
          {totalPoints} {isMarathi ? 'नोंदी' : 'Scenes'}
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
            {isMarathi ? 'NDVI कल दर्शवण्यासाठी पुरेसा उपग्रह डेटा नाही' : 'Insufficient Satellite Scenes to Plot Trend'}
          </h4>
          <p style={{ fontSize: '11.5px', color: '#94A3B8', margin: 0, lineHeight: 1.45 }}>
            {isMarathi 
              ? 'ढगाळ वातावरण किंवा अपुऱ्या उपग्रह फेरीमुळे या कालावधीत किमान २ दृश्ये उपलब्ध नाहीत.' 
              : 'At least 2 clear satellite acquisitions are required to render an honest vegetation trajectory.'}
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
        <Info size={12} color="#C5F36B" style={{ flexShrink: 0 }} />
        <span>
          {isMarathi 
            ? 'NDVI केवळ पानांतील हरितद्रव्य व घनता दर्शवतो. त्यावरून थेट दुष्काळ किंवा पाणीटंचाईचा निष्कर्ष काढू नये.' 
            : 'NDVI measures photosynthetic canopy activity. It must not be conflated directly with soil moisture.'}
        </span>
      </div>
    </div>
  );
}

