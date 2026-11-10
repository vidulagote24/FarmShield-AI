/**
 * FarmShield AI - useFarmInsights Custom Hook
 * 
 * Orchestrates farm-level historical observations, multi-zone telemetry trends,
 * and date-range filtering using actual backend observation endpoints.
 * 
 * Task 10.1 Pagination & Data Integrity:
 * - Uses observationsApi.fetchAllFarmObservations to iteratively retrieve all pages
 *   up to the total record count (using backend max page_size=100, up to 2000 records).
 * - Deduplicates observations across page boundaries using observation UUIDs.
 * - Protects against stale race-condition responses with request sequence IDs (reqSeq)
 *   and AbortController.
 * - Transparently tracks and reports pagination progress and partial datasets (isPartialData).
 * - Preserves partial datasets if a subsequent page fails, rather than discarding records.
 * 
 * Strict Scientific & Agronomic Rules (per AGENTS.md):
 * - Does not invent observations, interpolate missing dates, or treat missing values as zero.
 * - Does not calculate agronomic stress scores or generate new recommendations.
 * - Does not mix incompatible metrics (% vs NDVI 0..1) on ambiguous axes.
 * - In Live Mode: queries GET /api/v1/farms/{farm_id}/observations with real query params.
 * - In Demo Mode: loads curated Baramati observation fixtures with explicit simulated labels.
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { observationsApi, farmsApi, zonesApi } from '../../../lib/api/index.js';
import {
  DEMO_FARM_FIXTURE,
  DEMO_ZONES_FIXTURE,
  DEMO_OBSERVATIONS_FIXTURE,
} from '../../../data/fixtures/demoFarm.js';
import { useDataMode } from '../../../lib/dataMode.js';

export function useFarmInsights(targetFarmId = null, initialDateRange = '30d') {
  const { isDemoMode, dataMode, toggleDataMode, setDataMode } = useDataMode();

  const [farm, setFarm] = useState(null);
  const [zones, setZones] = useState([]);
  const [allObservations, setAllObservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Pagination & Data Completeness states (Task 10.1)
  const [isPartialData, setIsPartialData] = useState(false);
  const [partialDataNotice, setPartialDataNotice] = useState(null);
  const [totalMatchingRecords, setTotalMatchingRecords] = useState(0);
  const [paginationProgress, setPaginationProgress] = useState(null);

  // Filter states
  const [dateRange, setDateRange] = useState(initialDateRange); // '7d' | '30d' | '90d' | 'all'
  const [selectedZoneFilter, setSelectedZoneFilter] = useState('all'); // 'all' | zone_id

  // Request race-condition sequence & abort controller refs
  const currentReqSeq = useRef(0);
  const abortControllerRef = useRef(null);

  // Calculate start date boundary based on selected range
  const dateBoundary = useMemo(() => {
    if (dateRange === 'all') return null;
    const now = new Date();
    const days = dateRange === '7d' ? 7 : dateRange === '90d' ? 90 : 30;
    const past = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
    return past;
  }, [dateRange]);

  const fetchData = useCallback(async () => {
    const seq = ++currentReqSeq.current;

    // Abort previous in-flight request if any
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);
    setError(null);
    setPaginationProgress(null);

    // -------------------------------------------------------------
    // DEMO / SIMULATION MODE
    // -------------------------------------------------------------
    if (isDemoMode) {
      try {
        setFarm(DEMO_FARM_FIXTURE);
        setZones(DEMO_ZONES_FIXTURE);
        setAllObservations(DEMO_OBSERVATIONS_FIXTURE);
        setIsPartialData(false);
        setPartialDataNotice(null);
        setTotalMatchingRecords(DEMO_OBSERVATIONS_FIXTURE.length);
        setPaginationProgress(null);
        setLoading(false);
      } catch (err) {
        setError(`Failed to load demo insights: ${err.message}`);
        setLoading(false);
      }
      return;
    }

    // -------------------------------------------------------------
    // LIVE REST API MODE (Full Multi-Page Retrieval)
    // -------------------------------------------------------------
    try {
      // 1. Resolve Farm ID
      let farmId = targetFarmId;
      if (!farmId) {
        const farmsList = await farmsApi.listFarms({ page: 1, page_size: 1 });
        if (seq !== currentReqSeq.current) return;

        const items = Array.isArray(farmsList) ? farmsList : (farmsList?.items || []);
        if (items.length > 0) {
          farmId = items[0].id;
        } else {
          setError('No farms found for the current user. Please create a farm first.');
          setLoading(false);
          return;
        }
      }

      // 2. Fetch Farm, Zones, and all observations across pages
      const [farmData, zonesData, obsResult] = await Promise.all([
        farmsApi.getFarm(farmId),
        zonesApi.listFarmZones(farmId, { page: 1, page_size: 50 }),
        observationsApi.fetchAllFarmObservations(
          farmId,
          {
            start_date: dateBoundary ? dateBoundary.toISOString() : undefined,
          },
          {
            pageSize: 100, // backend max limit
            maxPages: 20,  // safety ceiling: up to 2000 observations
            signal: controller.signal,
            onProgress: (prog) => {
              if (seq === currentReqSeq.current) {
                setPaginationProgress(prog);
              }
            },
          }
        ),
      ]);

      // Guard: Discard stale response if a newer query was fired
      if (seq !== currentReqSeq.current) {
        return;
      }

      setFarm(farmData);
      setZones(Array.isArray(zonesData) ? zonesData : (zonesData?.items || []));
      setAllObservations(obsResult.items || []);
      setIsPartialData(Boolean(obsResult.isPartial));
      setTotalMatchingRecords(typeof obsResult.total === 'number' ? obsResult.total : (obsResult.items?.length || 0));

      if (obsResult.isPartial) {
        if (obsResult.partialError) {
          setPartialDataNotice(
            `Showing ${obsResult.items.length} of ${obsResult.total} observations due to a partial network error (${obsResult.partialError}).`
          );
        } else {
          setPartialDataNotice(
            `Showing ${obsResult.items.length} of ${obsResult.total} observations (retrieval capped at safety limit).`
          );
        }
      } else {
        setPartialDataNotice(null);
      }

      setLoading(false);
    } catch (err) {
      // Ignore cleanly aborted requests
      if (controller.signal.aborted || err.name === 'AbortError' || err.message?.includes('aborted')) {
        return;
      }

      if (seq === currentReqSeq.current) {
        setError(err.message || 'Unable to connect to backend to fetch farm observation telemetry.');
        setLoading(false);
      }
    }
  }, [targetFarmId, isDemoMode, dateBoundary]);

  useEffect(() => {
    fetchData();
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchData]);

  // Filter observations by date boundary and selected zone
  const filteredObservations = useMemo(() => {
    let list = allObservations;

    // Filter by zone if specific zone selected
    if (selectedZoneFilter !== 'all') {
      list = list.filter((obs) => obs.zone_id === selectedZoneFilter);
    }

    // Filter by date boundary (for demo mode or client-side precision)
    if (dateBoundary) {
      list = list.filter((obs) => {
        if (!obs.observed_at) return false;
        try {
          return new Date(obs.observed_at) >= dateBoundary;
        } catch {
          return true;
        }
      });
    }

    return list;
  }, [allObservations, selectedZoneFilter, dateBoundary]);

  // Telemetry grouping helpers: ensure valid numeric values and exclude failed readings
  const soilMoistureObservations = useMemo(() => {
    return filteredObservations.filter((o) => {
      const isSM = o.observation_type === 'soil_moisture' || o.metric_type === 'soil_moisture';
      const meta = o.metadata || o.metadata_json || {};
      const quality = meta.quality || meta.quality_status;
      const isFailedQuality = ['cloud_obscured', 'probe_disconnected', 'error', 'failed', 'invalid'].includes(quality);
      return isSM && o.value !== null && o.value !== undefined && !isFailedQuality;
    });
  }, [filteredObservations]);

  const vegetationIndexObservations = useMemo(() => {
    return filteredObservations.filter((o) => {
      const isVI = o.observation_type === 'vegetation_index' || o.metric_type === 'ndvi';
      const meta = o.metadata || o.metadata_json || {};
      const quality = meta.quality || meta.quality_status;
      const isFailedQuality = ['cloud_obscured', 'probe_disconnected', 'error', 'failed', 'invalid'].includes(quality);
      return isVI && o.value !== null && o.value !== undefined && !isFailedQuality;
    });
  }, [filteredObservations]);

  // Latest observed timestamp across the farm
  const latestObservationTimestamp = useMemo(() => {
    if (allObservations.length === 0) return null;
    let maxDate = null;
    allObservations.forEach((o) => {
      if (o.observed_at) {
        const d = new Date(o.observed_at);
        if (!maxDate || d > maxDate) maxDate = d;
      }
    });
    return maxDate;
  }, [allObservations]);

  return {
    farm,
    zones,
    allObservations,
    filteredObservations,
    soilMoistureObservations,
    vegetationIndexObservations,
    latestObservationTimestamp,
    loading,
    error,
    dateRange,
    setDateRange,
    selectedZoneFilter,
    setSelectedZoneFilter,
    isDemoMode,
    dataMode,
    toggleDataMode,
    setIsDemoMode: setDataMode,
    // Task 10.1 fields
    isPartialData,
    partialDataNotice,
    totalMatchingRecords,
    paginationProgress,
    refetch: fetchData,
  };
}

export default useFarmInsights;
