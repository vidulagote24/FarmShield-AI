/**
 * FarmShield AI - useRecommendationDetails Custom Hook
 * 
 * Provides robust state management and data orchestration for the Recommendation Details screen.
 * Handles dual-mode data loading (Live REST API vs Curated Baramati Demo Fixtures)
 * and verifies status transitions (pending -> accepted -> applied / dismissed).
 * 
 * Scientific Integrity Rules:
 * - Does not calculate water depth or volume in frontend code.
 * - Does not invent missing telemetry or confidence values.
 * - In Live Mode: sends PATCH /api/v1/recommendations/{id}/status.
 * - In Demo Mode: executes in-memory simulation clearly labeled as demo.
 */

import { useState, useEffect, useCallback } from 'react';
import { recommendationsApi, zonesApi, farmsApi, observationsApi } from '../../../lib/api/index.js';
import {
  DEMO_FARM_FIXTURE,
  DEMO_ZONES_FIXTURE,
  DEMO_OBSERVATIONS_FIXTURE,
  DEMO_RECOMMENDATIONS_FIXTURE,
} from '../../../data/fixtures/demoFarm.js';
import { useDataMode } from '../../../lib/dataMode.js';

// In-memory session store for demo mode status updates
const demoStatusOverrides = new Map();

export function useRecommendationDetails(recommendationId, initialFarmId = null, initialZoneId = null) {
  const { isDemoMode, dataMode, toggleDataMode, setDataMode } = useDataMode();

  const [recommendation, setRecommendation] = useState(null);
  const [zone, setZone] = useState(null);
  const [farm, setFarm] = useState(null);
  const [observations, setObservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [statusUpdateError, setStatusUpdateError] = useState(null);

  const fetchData = useCallback(async () => {
    if (!recommendationId) {
      setLoading(false);
      setError('Recommendation ID is required.');
      return;
    }

    setLoading(true);
    setError(null);
    setStatusUpdateError(null);

    // -------------------------------------------------------------
    // DEMO / SIMULATION MODE
    // -------------------------------------------------------------
    if (isDemoMode) {
      try {
        const found = DEMO_RECOMMENDATIONS_FIXTURE.find((r) => r.id === recommendationId);
        if (!found) {
          setError(`Recommendation '${recommendationId}' was not found in demo fixtures.`);
          setRecommendation(null);
          setLoading(false);
          return;
        }

        // Apply session status override if user changed status earlier
        const currentStatus = demoStatusOverrides.get(recommendationId) || found.status;
        const mergedRec = { ...found, status: currentStatus, is_simulated: true };

        setRecommendation(mergedRec);
        setFarm(DEMO_FARM_FIXTURE);

        // Find associated zone if any
        if (mergedRec.zone_id) {
          const matchedZone = DEMO_ZONES_FIXTURE.find((z) => z.id === mergedRec.zone_id);
          setZone(matchedZone || null);

          // Get observations for this zone
          const zoneObs = DEMO_OBSERVATIONS_FIXTURE.filter((o) => o.zone_id === mergedRec.zone_id);
          setObservations(zoneObs);
        } else {
          setZone(null);
          setObservations([]);
        }

        setLoading(false);
      } catch (err) {
        setError(`Failed to load demo recommendation: ${err.message}`);
        setLoading(false);
      }
      return;
    }

    // -------------------------------------------------------------
    // LIVE REST API MODE
    // -------------------------------------------------------------
    try {
      // 1. Fetch Recommendation by UUID
      const recData = await recommendationsApi.getRecommendation(recommendationId);
      if (!recData) {
        setError(`Recommendation '${recommendationId}' was not found on the server.`);
        setLoading(false);
        return;
      }
      setRecommendation(recData);

      // 2. Fetch Farm Details
      if (recData.farm_id) {
        try {
          const farmData = await farmsApi.getFarm(recData.farm_id);
          setFarm(farmData);
        } catch {
          // Farm metadata optional fallback
        }
      }

      // 3. Fetch Zone Details
      if (recData.zone_id) {
        try {
          const zoneData = await zonesApi.getZone(recData.zone_id);
          setZone(zoneData);
        } catch {
          // Zone metadata optional fallback
        }

        // 4. Fetch Zone Observations for Evidence Breakdown
        try {
          const obsData = await observationsApi.listZoneObservations(recData.zone_id, { page_size: 10 });
          const items = Array.isArray(obsData) ? obsData : (obsData?.items || []);
          setObservations(items);
        } catch {
          setObservations([]);
        }
      } else {
        setZone(null);
        setObservations([]);
      }

      setLoading(false);
    } catch (err) {
      const msg = err.status === 404
        ? `Recommendation '${recommendationId}' was not found on the backend.`
        : (err.message || 'Unable to connect to backend server to fetch recommendation.');
      setError(msg);
      setLoading(false);
    }
  }, [recommendationId, isDemoMode]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  /**
   * Status Transition Dispatcher
   * Supports: accepted (acknowledge), applied, dismissed, pending
   */
  const updateStatus = async (targetStatus) => {
    if (!recommendation) return;

    setIsUpdatingStatus(true);
    setStatusUpdateError(null);

    // DEMO MODE: In-memory simulation
    if (isDemoMode) {
      await new Promise((r) => setTimeout(r, 450));
      demoStatusOverrides.set(recommendation.id, targetStatus);
      setRecommendation((prev) => ({
        ...prev,
        status: targetStatus,
        updated_at: new Date().toISOString(),
        is_simulated: true,
      }));
      setIsUpdatingStatus(false);
      return;
    }

    // LIVE MODE: Call backend PATCH endpoint
    try {
      const updated = await recommendationsApi.updateRecommendationStatus(recommendation.id, targetStatus);
      if (updated && updated.status) {
        setRecommendation(updated);
      } else {
        // Fallback if backend returned 204 or partial
        setRecommendation((prev) => ({ ...prev, status: targetStatus }));
      }
      setIsUpdatingStatus(false);
    } catch (err) {
      const msg = err.details?.detail || err.message || 'Failed to update recommendation status on server.';
      setStatusUpdateError(msg);
      setIsUpdatingStatus(false);
      throw err;
    }
  };

  return {
    recommendation,
    zone,
    farm,
    observations,
    loading,
    error,
    isUpdatingStatus,
    statusUpdateError,
    isDemoMode,
    dataMode,
    toggleDataMode,
    setIsDemoMode: setDataMode,
    updateStatus,
    refetch: fetchData,
  };
}

export default useRecommendationDetails;

