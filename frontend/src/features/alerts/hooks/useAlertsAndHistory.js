/**
 * FarmShield AI - useAlertsAndHistory Custom Hook
 * 
 * Orchestrates:
 * 1. Recommendation-derived alerts feed (with priority & agronomic filtering).
 * 2. Unified activity history aggregating irrigation events, advisories, and observations.
 * 3. Client-side local viewed state scoped by farm ID (localStorage with in-memory fallback).
 * 4. Stale-request race condition protection and clean AbortController cancellation.
 * 
 * Strict Agronomic & Safety Integrity:
 * - Does not invent alerts or calculate agronomic thresholds in the frontend.
 * - Does not claim notifications were delivered (no SMS/WhatsApp claims).
 * - Viewing an alert is strictly local and never mutates recommendation status.
 * - Missing observation values are never converted to zero.
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { alertsApi } from '../../../lib/api/alerts.js';
import { historyApi } from '../../../lib/api/history.js';
import { farmsApi } from '../../../lib/api/farms.js';
import { useDataMode } from '../../../lib/dataMode.js';

// Safe localStorage helper with in-memory fallback for private browsing or quota errors
function getStorageKey(farmId) {
  return `farmshield_viewed_alerts_${farmId || 'default'}`;
}

function loadViewedAlertsFromStorage(farmId) {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return new Set();
    const raw = window.localStorage.getItem(getStorageKey(farmId));
    if (!raw) return new Set();
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? new Set(parsed) : new Set();
  } catch {
    return new Set();
  }
}

function saveViewedAlertsToStorage(farmId, viewedSet) {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return;
    const arrayData = Array.from(viewedSet);
    window.localStorage.setItem(getStorageKey(farmId), JSON.stringify(arrayData));
  } catch {
    // Gracefully handle storage quotas or security restrictions
  }
}

export function useAlertsAndHistory(targetFarmId = null, initialTab = 'alerts') {
  const { isDemoMode, dataMode, toggleDataMode, setDataMode } = useDataMode();

  const [activeTab, setActiveTab] = useState(initialTab); // 'alerts' | 'history'
  const [priorityFilter, setPriorityFilter] = useState('all'); // 'all' | 'critical' | 'high' | 'agronomic'
  
  // Data states
  const [alerts, setAlerts] = useState([]);
  const [history, setHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sourceErrors, setSourceErrors] = useState({});
  const [isPartialData, setIsPartialData] = useState(false);
  const [alertsFetchSuccess, setAlertsFetchSuccess] = useState(false);
  const [historyFetchSuccess, setHistoryFetchSuccess] = useState(false);

  // Farm-scoped local viewed alerts set
  const [viewedAlertIds, setViewedAlertIds] = useState(() => {
    return loadViewedAlertsFromStorage(targetFarmId);
  });

  // Keep viewedAlertIds in sync if targetFarmId changes
  useEffect(() => {
    setViewedAlertIds(loadViewedAlertsFromStorage(targetFarmId));
  }, [targetFarmId]);

  // Race condition sequence and abort controller refs
  const currentReqSeq = useRef(0);
  const abortControllerRef = useRef(null);

  const fetchData = useCallback(async () => {
    const seq = ++currentReqSeq.current;

    // Abort previous in-flight request if active
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsLoading(true);
    setError(null);
    setSourceErrors({});
    setIsPartialData(false);

    try {
      // 1. Resolve Farm ID if not explicitly provided
      let farmId = targetFarmId;
      if (!farmId && !isDemoMode) {
        const farmsList = await farmsApi.listFarms({ page: 1, page_size: 1 });
        if (seq !== currentReqSeq.current) return;
        const items = Array.isArray(farmsList) ? farmsList : (farmsList?.items || []);
        if (items.length > 0) {
          farmId = items[0].id;
        } else {
          setError('No farms found for the current user.');
          setIsLoading(false);
          return;
        }
      }

      // 2. Fetch Alerts and Activity History concurrently
      const [alertsRes, historyRes] = await Promise.allSettled([
        alertsApi.listFarmAlerts(farmId, { isDemoMode }, { signal: controller.signal }),
        historyApi.getUnifiedFarmHistory(farmId, { isDemoMode }, { signal: controller.signal }),
      ]);

      // Guard against stale response
      if (seq !== currentReqSeq.current) {
        return;
      }

      let alertsData = [];
      let historyData = [];
      const aggregatedErrors = {};
      let isPartial = false;
      let alertsOk = false;
      let historyOk = false;

      // Handle Alerts Result
      if (alertsRes.status === 'fulfilled') {
        alertsData = alertsRes.value?.items || [];
        alertsOk = true;
      } else {
        if (!controller.signal.aborted) {
          aggregatedErrors.alerts = alertsRes.reason?.message || 'Failed to fetch recommendation alerts.';
        }
      }

      // Handle History Result
      if (historyRes.status === 'fulfilled') {
        const histVal = historyRes.value;
        historyData = histVal?.items || [];
        isPartial = Boolean(histVal?.isPartialData);
        if (histVal?.sourceErrors) {
          Object.assign(aggregatedErrors, histVal.sourceErrors);
        }
        historyOk = true;
      } else {
        if (!controller.signal.aborted) {
          aggregatedErrors.history = historyRes.reason?.message || 'Failed to aggregate activity history.';
        }
      }

      // If all sources failed, expose top-level error
      const allFailed = alertsRes.status === 'rejected' && historyRes.status === 'rejected';
      if (allFailed) {
        setError('Unable to load alerts and activity history. Please check your network connection.');
      }

      setAlerts(alertsData);
      setHistory(historyData);
      setSourceErrors(aggregatedErrors);
      setIsPartialData(isPartial || Object.keys(aggregatedErrors).length > 0);
      setAlertsFetchSuccess(alertsOk);
      setHistoryFetchSuccess(historyOk);
      setIsLoading(false);
    } catch (err) {
      if (controller.signal.aborted || err.name === 'AbortError' || err.message?.includes('aborted')) {
        return;
      }
      if (seq === currentReqSeq.current) {
        setError(err.message || 'Error loading alerts and history data.');
        setAlertsFetchSuccess(false);
        setHistoryFetchSuccess(false);
        setIsLoading(false);
      }
    }
  }, [targetFarmId, isDemoMode]);

  useEffect(() => {
    fetchData();
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchData]);

  // Mark an alert as viewed locally (never mutates backend status)
  const markAlertViewed = useCallback((alertId) => {
    if (!alertId) return;
    setViewedAlertIds((prev) => {
      if (prev.has(alertId)) return prev;
      const next = new Set(prev);
      next.add(alertId);
      saveViewedAlertsToStorage(targetFarmId, next);
      return next;
    });
  }, [targetFarmId]);

  // Check if an alert has been viewed locally
  const isAlertViewed = useCallback((alertId) => {
    if (!alertId) return false;
    return viewedAlertIds.has(alertId);
  }, [viewedAlertIds]);

  // Filter alerts by priority / category
  const filteredAlerts = useMemo(() => {
    if (priorityFilter === 'all') return alerts;
    if (priorityFilter === 'critical') {
      return alerts.filter((a) => a.priority === 'critical' || a.severity === 'critical');
    }
    if (priorityFilter === 'high') {
      return alerts.filter((a) => a.priority === 'high' || a.severity === 'high');
    }
    if (priorityFilter === 'agronomic') {
      return alerts.filter((a) => 
        (Array.isArray(a.independent_alerts) && a.independent_alerts.length > 0) ||
        a.has_independent_alerts === true ||
        a.alert_type === 'soil_salinity' ||
        a.alert_type === 'crop_vigor_decline'
      );
    }
    return alerts;
  }, [alerts, priorityFilter]);

  return {
    alerts,
    filteredAlerts,
    history,
    activeTab,
    setActiveTab,
    priorityFilter,
    setPriorityFilter,
    isLoading,
    error,
    sourceErrors,
    isPartialData,
    alertsFetchSuccess,
    historyFetchSuccess,
    refresh: fetchData,
    markAlertViewed,
    isAlertViewed,
    isDemoMode,
    dataMode,
    toggleDataMode,
    setIsDemoMode: setDataMode,
  };
}

export default useAlertsAndHistory;

