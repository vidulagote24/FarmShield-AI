/**
 * FarmShield AI - useFarmMap Hook
 * 
 * Manages GIS farm boundary, zone polygons, layer switcher state,
 * individual zone selection, and dual-mode data retrieval (Live vs Demo).
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { farmsApi, zonesApi } from '../../../lib/api/index.js';
import { DEMO_FARM_FIXTURE, DEMO_ZONES_FIXTURE } from '../../../data/fixtures/demoFarm.js';

export function useFarmMap(initialFarmId = null) {
  // Determine initial mode from environment or localStorage
  const [dataMode, setDataMode] = useState(() => {
    return localStorage.getItem('farmshield_data_mode') || import.meta.env?.VITE_DATA_MODE || 'demo';
  });

  const [farm, setFarm] = useState(null);
  const [zones, setZones] = useState([]);
  const [selectedZoneId, setSelectedZoneId] = useState(null);
  const [activeLayer, setActiveLayer] = useState('zones'); // 'zones' | 'boundary' | 'ndvi' | 'moisture'
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [resetViewTrigger, setResetViewTrigger] = useState(0);

  const isDemoMode = dataMode === 'demo';

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    if (isDemoMode) {
      // Load static, scientifically sound demonstration fixture
      setFarm(DEMO_FARM_FIXTURE);
      setZones(DEMO_ZONES_FIXTURE);
      setSelectedZoneId((prev) => prev || DEMO_ZONES_FIXTURE[0]?.id || null);
      setIsLoading(false);
      return;
    }

    // LIVE MODE: Call backend endpoints
    try {
      let targetFarmId = initialFarmId;

      if (!targetFarmId) {
        const farmsList = await farmsApi.listFarms({ page: 1, page_size: 1 });
        if (farmsList?.items?.length > 0) {
          targetFarmId = farmsList.items[0].id;
        } else {
          setFarm(null);
          setZones([]);
          setIsLoading(false);
          return;
        }
      }

      // Fetch farm details and zones in parallel
      const [farmData, zonesData] = await Promise.all([
        farmsApi.getFarm(targetFarmId),
        zonesApi.listFarmZones(targetFarmId, { page: 1, page_size: 50 }),
      ]);

      setFarm(farmData);

      // Handle backend's paginated zone response
      const items = zonesData?.items || (Array.isArray(zonesData) ? zonesData : []);
      
      // Normalize zone items without fabricating stress statuses
      const normalizedZones = items.map((z) => ({
        id: z.id,
        farm_id: z.farm_id,
        zone_name: z.zone_name,
        zone_code: z.zone_code,
        area_hectares: z.area_hectares,
        area_acres: z.area_hectares ? +(z.area_hectares * 2.47105).toFixed(2) : null,
        boundary: z.boundary,
        metadata: z.metadata || {},
        // Status is strictly preserved if backend provides it; otherwise 'insufficient_data'
        status: z.status || z.metadata?.status || 'insufficient_data',
        ndvi_value: z.metadata?.ndvi_value ?? null,
        soil_moisture_pct: z.metadata?.soil_moisture_pct ?? null,
        last_observed_at: z.updated_at || z.created_at || null,
        evidence_source: z.metadata?.evidence_source || 'Registered Farm Polygon',
        reason_summary: z.metadata?.reason_summary || 'No live agronomic assessment linked yet.',
      }));

      setZones(normalizedZones);
      setSelectedZoneId((prev) => {
        if (prev && normalizedZones.some((z) => z.id === prev)) return prev;
        return normalizedZones[0]?.id || null;
      });
    } catch (err) {
      // In Live Mode, never silently fall back to mock data
      setError(err?.message || 'Failed to load farm digital twin data from backend.');
      setFarm(null);
      setZones([]);
    } finally {
      setIsLoading(false);
    }
  }, [isDemoMode, initialFarmId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Selected Zone reference
  const selectedZone = useMemo(() => {
    return zones.find((z) => z.id === selectedZoneId) || null;
  }, [zones, selectedZoneId]);

  // Reset map view trigger
  const resetMap = useCallback(() => {
    setResetViewTrigger((c) => c + 1);
  }, []);

  // Switch data mode
  const toggleDataMode = useCallback(() => {
    const nextMode = dataMode === 'demo' ? 'live' : 'demo';
    setDataMode(nextMode);
    try {
      localStorage.setItem('farmshield_data_mode', nextMode);
    } catch {
      // localStorage disabled
    }
  }, [dataMode]);

  return {
    farm,
    zones,
    selectedZoneId,
    selectedZone,
    selectZone: setSelectedZoneId,
    activeLayer,
    setActiveLayer,
    isLoading,
    error,
    isDemoMode,
    dataMode,
    toggleDataMode,
    resetMap,
    resetViewTrigger,
    refetch: loadData,
  };
}

export default useFarmMap;
