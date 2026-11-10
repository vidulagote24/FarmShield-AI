/**
 * FarmShield AI - useIrrigationPlanner Custom Hook
 * 
 * Manages data fetching, zone filtering, decision recommendations,
 * and validated event creation for the Irrigation Planner feature.
 * 
 * Safety & Agronomic Restrictions (per AGENTS.md):
 * - Advisory-only: never interacts with pumps, valves, or relays.
 * - In Live Mode: submits only to backend endpoints, never creates fake events.
 * - In Demo Mode: clearly flagged as simulated in-memory session state.
 */

import { useState, useEffect, useCallback } from 'react';
import { irrigationApi, recommendationsApi, farmsApi, zonesApi } from '../../../lib/api/index.js';
import { 
  DEMO_FARM_FIXTURE, 
  DEMO_ZONES_FIXTURE, 
  DEMO_RECOMMENDATIONS_FIXTURE, 
  DEMO_IRRIGATION_EVENTS_FIXTURE 
} from '../../../data/fixtures/demoFarm.js';

export function useIrrigationPlanner(initialFarmId = null, initialZoneId = null) {
  const [farm, setFarm] = useState(null);
  const [zones, setZones] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [history, setHistory] = useState([]);
  const [selectedZoneId, setSelectedZoneId] = useState(initialZoneId);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Submission state
  const [submitting, setSubmitting] = useState(false);
  const [submissionError, setSubmissionError] = useState(null);
  const [lastSavedEvent, setLastSavedEvent] = useState(null);

  // Initialize data provider mode from environment
  const [isDemoMode, setIsDemoMode] = useState(() => {
    return import.meta.env.VITE_DATA_MODE === 'demo';
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    // -------------------------------------------------------------
    // DEMO / SIMULATION MODE
    // -------------------------------------------------------------
    if (isDemoMode) {
      try {
        setFarm(DEMO_FARM_FIXTURE);
        setZones(DEMO_ZONES_FIXTURE);
        setRecommendations(DEMO_RECOMMENDATIONS_FIXTURE);
        setHistory(DEMO_IRRIGATION_EVENTS_FIXTURE);
        setLoading(false);
      } catch (err) {
        console.error('[useIrrigationPlanner] Demo loading error:', err);
        setError('Failed to load demo irrigation planner data.');
        setLoading(false);
      }
      return;
    }

    // -------------------------------------------------------------
    // LIVE REST API MODE
    // -------------------------------------------------------------
    try {
      let effectiveFarmId = initialFarmId;
      if (!effectiveFarmId) {
        const farmsList = await farmsApi.listFarms({ page: 1, page_size: 1 });
        const items = farmsList?.items || (Array.isArray(farmsList) ? farmsList : []);
        if (items.length > 0) {
          effectiveFarmId = items[0].id;
        } else {
          setFarm(null);
          setZones([]);
          setRecommendations([]);
          setHistory([]);
          setLoading(false);
          return;
        }
      }

      // 1. Fetch farm details
      try {
        const farmRes = await farmsApi.getById(effectiveFarmId);
        setFarm(farmRes);
      } catch (fErr) {
        console.warn('[useIrrigationPlanner] Farm metadata query warning:', fErr.message);
      }

      // 2. Fetch farm zones
      let zoneItems = [];
      try {
        const zonesRes = await zonesApi.listFarmZones(effectiveFarmId);
        zoneItems = zonesRes.items || (Array.isArray(zonesRes) ? zonesRes : []);
        setZones(zoneItems);
        // If the initially selected zone does not exist in the active farm's zones, default to all zones
        if (selectedZoneId && zoneItems.length > 0 && !zoneItems.some((z) => z.id === selectedZoneId)) {
          setSelectedZoneId(null);
        }
      } catch (zErr) {
        console.warn('[useIrrigationPlanner] Zones query warning:', zErr.message);
      }

      // 3. Fetch active recommendations
      try {
        const recRes = await recommendationsApi.listFarmRecommendations(effectiveFarmId, {
          page_size: 50,
        });
        const recItems = recRes.items || (Array.isArray(recRes) ? recRes : []);
        setRecommendations(recItems);
      } catch (rErr) {
        console.warn('[useIrrigationPlanner] Recommendations query warning:', rErr.message);
      }

      // 4. Fetch irrigation history
      try {
        const histRes = await irrigationApi.listFarmIrrigationEvents(effectiveFarmId, {
          page_size: 50,
        });
        const histItems = histRes.items || (Array.isArray(histRes) ? histRes : []);
        setHistory(histItems);
      } catch (hErr) {
        console.warn('[useIrrigationPlanner] History query warning:', hErr.message);
      }

      setLoading(false);
    } catch (err) {
      console.error('[useIrrigationPlanner] Live API error:', err);
      setError(err.message || 'Unable to load live irrigation planner data from backend.');
      setLoading(false);
    }
  }, [initialFarmId, isDemoMode]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // -------------------------------------------------------------
  // Record Irrigation Activity
  // -------------------------------------------------------------
  const recordIrrigation = async (eventData) => {
    setSubmitting(true);
    setSubmissionError(null);
    setLastSavedEvent(null);

    // Basic frontend verification before dispatch
    if (!eventData.water_quantity || Number(eventData.water_quantity) <= 0) {
      setSubmissionError('Water quantity must be a positive number greater than 0.');
      setSubmitting(false);
      return false;
    }
    if (!eventData.irrigation_date) {
      setSubmissionError('Irrigation date is required.');
      setSubmitting(false);
      return false;
    }

    // 1. Demo Mode Simulation
    if (isDemoMode) {
      await new Promise((resolve) => setTimeout(resolve, 600)); // Simulate realistic network latency
      const matchingZone = zones.find((z) => z.id === eventData.zone_id);

      const simulatedEvent = {
        id: `irrig-sim-${Date.now()}`,
        farm_id: farm?.id || 'f8a1c9e2-4b3d-4e5f-8a1b-2c3d4e5f6a7b',
        zone_id: eventData.zone_id || null,
        zone_name: matchingZone ? matchingZone.zone_name : 'Whole Farm (सर्व शेत)',
        irrigation_date: new Date(eventData.irrigation_date).toISOString(),
        water_quantity: Number(eventData.water_quantity),
        water_unit: eventData.water_unit || 'cubic_meters',
        irrigation_method: eventData.irrigation_method || 'drip',
        notes: eventData.notes || '',
        created_at: new Date().toISOString(),
        is_simulated: true,
      };

      setHistory((prev) => [simulatedEvent, ...prev]);
      setLastSavedEvent(simulatedEvent);
      setSubmitting(false);
      return true;
    }

    // 2. Live Backend Submission
    try {
      const effectiveFarmId = farm?.id || initialFarmId;
      const payload = {
        farm_id: effectiveFarmId,
        zone_id: eventData.zone_id || undefined,
        irrigation_date: new Date(eventData.irrigation_date).toISOString(),
        water_quantity: Number(eventData.water_quantity),
        water_unit: eventData.water_unit || 'liters',
        irrigation_method: eventData.irrigation_method || undefined,
        notes: eventData.notes || undefined,
      };

      const savedResponse = await irrigationApi.createFarmIrrigationEvent(effectiveFarmId, payload);
      
      // Verify that backend returned a valid event object containing an identifier
      if (!savedResponse || !savedResponse.id) {
        throw new Error('Backend response did not return a valid confirmed event identifier.');
      }

      setLastSavedEvent(savedResponse);

      // Refresh history list from live database
      const refreshedHist = await irrigationApi.listFarmIrrigationEvents(effectiveFarmId, { page_size: 50 });
      setHistory(refreshedHist.items || (Array.isArray(refreshedHist) ? refreshedHist : []));

      setSubmitting(false);
      return true;
    } catch (err) {
      console.error('[useIrrigationPlanner] Recording error:', err);
      setSubmissionError(err.message || 'Failed to record irrigation event on the backend.');
      setSubmitting(false);
      return false;
    }
  };

  const toggleDataMode = () => {
    setIsDemoMode((prev) => !prev);
  };

  const clearSubmissionStatus = () => {
    setLastSavedEvent(null);
    setSubmissionError(null);
  };

  // Filter recommendations and history based on selectedZoneId
  const filteredRecommendations = selectedZoneId
    ? recommendations.filter((r) => r.zone_id === selectedZoneId)
    : recommendations;

  const filteredHistory = selectedZoneId
    ? history.filter((h) => h.zone_id === selectedZoneId)
    : history;

  return {
    farm,
    zones,
    recommendations: filteredRecommendations,
    allRecommendations: recommendations,
    history: filteredHistory,
    allHistory: history,
    selectedZoneId,
    selectZone: setSelectedZoneId,
    loading,
    error,
    submitting,
    submissionError,
    lastSavedEvent,
    recordIrrigation,
    clearSubmissionStatus,
    isDemoMode,
    toggleDataMode,
    refetch: fetchData,
  };
}

export default useIrrigationPlanner;

