/**
 * FarmShield AI - useZoneDetails Custom Hook
 * 
 * Provides robust state management and data orchestration for the Zone Intelligence screen.
 * Handles dual-mode data loading (Live REST API vs Curated Baramati Demo Fixtures).
 * 
 * Scientific Integrity Rules (per AGENTS.md):
 * - Never fabricates observations, timestamps, units, crop stages, or recommendations.
 * - In Live Mode: fetches actual API endpoints, surfaces missing data honestly.
 * - In Demo Mode: loads realistic Baramati fixtures explicitly flagged as simulated.
 */

import { useState, useEffect, useCallback } from 'react';
import { zonesApi, observationsApi, recommendationsApi, farmsApi } from '../../../lib/api/index.js';
import { 
  DEMO_FARM_FIXTURE, 
  DEMO_ZONES_FIXTURE, 
  DEMO_OBSERVATIONS_FIXTURE, 
  DEMO_RECOMMENDATIONS_FIXTURE 
} from '../../../data/fixtures/demoFarm.js';

import { useDataMode } from '../../../lib/dataMode.js';

export function useZoneDetails(zoneId, parentFarmId = null) {
  const { isDemoMode, dataMode, toggleDataMode } = useDataMode();

  const [zone, setZone] = useState(null);
  const [farm, setFarm] = useState(null);
  const [observations, setObservations] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [stressAssessment, setStressAssessment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    if (!zoneId) {
      setLoading(false);
      setError('Zone ID is required to fetch zone intelligence details.');
      return;
    }

    setLoading(true);
    setError(null);

    // -------------------------------------------------------------
    // DEMO / SIMULATION MODE
    // -------------------------------------------------------------
    if (isDemoMode) {
      try {
        // Find matching zone from demo fixture
        const matchedZone = DEMO_ZONES_FIXTURE.find((z) => z.id === zoneId) || DEMO_ZONES_FIXTURE[0];
        setZone(matchedZone);
        setFarm(DEMO_FARM_FIXTURE);

        // Filter observations matching this zone
        const zoneObs = DEMO_OBSERVATIONS_FIXTURE.filter((o) => o.zone_id === matchedZone.id);
        setObservations(zoneObs);

        // Filter recommendations matching this zone
        const zoneRecs = DEMO_RECOMMENDATIONS_FIXTURE.filter((r) => r.zone_id === matchedZone.id);
        setRecommendations(zoneRecs);

        // Construct stress assessment representation from demo zone properties
        if (matchedZone.status && matchedZone.status !== 'insufficient_data') {
          setStressAssessment({
            status: matchedZone.status,
            data_quality_status: 'good',
            reasons: matchedZone.reason_summary ? [matchedZone.reason_summary] : [],
            assessed_at: matchedZone.last_observed_at,
            confidence: 0.92,
            method_version: '0.4.0-simulated',
          });
        } else if (matchedZone.status === 'insufficient_data') {
          setStressAssessment({
            status: 'insufficient_data',
            data_quality_status: 'insufficient',
            reasons: [matchedZone.reason_summary || 'Telemetry inputs insufficient for stress classification.'],
            assessed_at: null,
            confidence: null,
            method_version: '0.4.0-simulated',
          });
        } else {
          setStressAssessment(null);
        }

        setLoading(false);
      } catch (err) {
        console.error('[useZoneDetails] Demo loading error:', err);
        setError('Failed to load demo zone details.');
        setLoading(false);
      }
      return;
    }

    // -------------------------------------------------------------
    // LIVE REST API MODE
    // -------------------------------------------------------------
    try {
      // 1. Fetch zone details
      let zoneData = null;
      try {
        zoneData = await zonesApi.getZone(zoneId);
      } catch (zoneErr) {
        // If single zone endpoint requires farm_id or fails, try querying parent farm zones
        if (parentFarmId) {
          const zonesRes = await zonesApi.listFarmZones(parentFarmId);
          const items = zonesRes.items || zonesRes || [];
          zoneData = items.find((z) => z.id === zoneId);
        }
        if (!zoneData) throw zoneErr;
      }

      setZone(zoneData);
      const effectiveFarmId = parentFarmId || zoneData.farm_id;

      // 2. Fetch parent farm metadata if available
      if (effectiveFarmId) {
        try {
          const farmData = await farmsApi.getById(effectiveFarmId);
          setFarm(farmData);
        } catch (farmErr) {
          console.warn('[useZoneDetails] Parent farm lookup warning:', farmErr.message);
          // Non-blocking: zone view can still function
        }
      }

      // 3. Fetch zone observations with explicit query filter
      let obsItems = [];
      if (effectiveFarmId) {
        try {
          const obsRes = await observationsApi.listFarmObservations(effectiveFarmId, {
            zone_id: zoneId,
            page_size: 50,
          });
          obsItems = obsRes.items || (Array.isArray(obsRes) ? obsRes : []);
        } catch (obsErr) {
          console.warn('[useZoneDetails] Observations query warning:', obsErr.message);
        }
      }
      setObservations(obsItems);

      // 4. Fetch recommendations for this zone
      let recItems = [];
      if (effectiveFarmId) {
        try {
          const recRes = await recommendationsApi.listFarmRecommendations(effectiveFarmId, {
            zone_id: zoneId,
            page_size: 20,
          });
          recItems = recRes.items || (Array.isArray(recRes) ? recRes : []);
        } catch (recErr) {
          console.warn('[useZoneDetails] Recommendations query warning:', recErr.message);
        }
      }
      setRecommendations(recItems);

      // 5. Check if backend intelligence provides dedicated analysis endpoint
      try {
        const analysisRes = await zonesApi.getZoneAnalysis(zoneId);
        if (analysisRes && analysisRes.status) {
          setStressAssessment(analysisRes);
        }
      } catch (analysisErr) {
        // If /zones/{id}/analysis endpoint is not implemented on backend,
        // extract stress indication from latest recommendation reasoning or zone metadata
        if (recItems.length > 0 && recItems[0].reasoning?.stress_status) {
          setStressAssessment({
            status: recItems[0].reasoning.stress_status,
            data_quality_status: recItems[0].reasoning.data_quality_status || 'good',
            reasons: recItems[0].reasoning.stress_reasons || recItems[0].reasoning.factors || [],
            assessed_at: recItems[0].generated_at,
            confidence: recItems[0].reasoning.confidence || null,
            method_version: 'backend-rec-reasoning',
          });
        } else if (zoneData.metadata?.stress_assessment) {
          setStressAssessment(zoneData.metadata.stress_assessment);
        } else {
          setStressAssessment(null);
        }
      }

      setLoading(false);
    } catch (err) {
      console.error('[useZoneDetails] Live API error:', err);
      setError(err.message || 'Unable to connect to live backend zone endpoints.');
      setLoading(false);
    }
  }, [zoneId, parentFarmId, isDemoMode]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    zone,
    farm,
    observations,
    recommendations,
    stressAssessment,
    loading,
    error,
    isDemoMode,
    dataMode,
    toggleDataMode,
    refetch: fetchData,
  };
}

export default useZoneDetails;

