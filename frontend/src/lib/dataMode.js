/**
 * FarmShield AI - Centralized Data Mode Management
 * 
 * Provides a unified, synchronized data provider mode ('demo' vs 'live')
 * across all screens and hooks:
 * - Farm Map
 * - Zone Details
 * - Irrigation Planner
 * - Farm Insights
 * - Alerts & Activity History
 * - Recommendation Details
 * - Dashboard
 * 
 * Guarantees:
 * 1. Single source of truth across all features (no local-storage split-brain).
 * 2. Cross-screen synchronization via window custom events.
 * 3. Default to 'demo' when VITE_DATA_MODE is unset or 'demo', preventing accidental
 *    live API network errors in preview or demo deployments.
 * 4. Respects 'live' when explicitly configured via VITE_DATA_MODE or toggle.
 */

import { useState, useEffect, useCallback } from 'react';

export const DATA_MODE_STORAGE_KEY = 'farmshield_data_mode';
export const DATA_MODE_CHANGE_EVENT = 'farmshield_data_mode_change';

/**
 * Determine initial data mode:
 * Priority:
 * 1. Runtime localStorage override ('live' | 'demo') if in browser.
 * 2. Build-time environment variable VITE_DATA_MODE ('live' | 'demo').
 * 3. Default fallback: 'demo'.
 */
export function getSharedDataMode() {
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      const stored = window.localStorage.getItem(DATA_MODE_STORAGE_KEY);
      if (stored === 'live' || stored === 'demo') {
        return stored;
      }
    } catch {
      // Storage unavailable or blocked
    }
  }

  const envMode = typeof import.meta !== 'undefined' ? import.meta.env?.VITE_DATA_MODE : undefined;
  if (envMode === 'live') {
    return 'live';
  }

  return 'demo';
}

/**
 * Persist and broadcast a new data mode to all active components.
 */
export function setSharedDataMode(mode) {
  const nextMode = mode === 'live' ? 'live' : 'demo';

  if (typeof window !== 'undefined') {
    if (window.localStorage) {
      try {
        window.localStorage.setItem(DATA_MODE_STORAGE_KEY, nextMode);
      } catch {
        // Storage unavailable
      }
    }
    window.dispatchEvent(
      new CustomEvent(DATA_MODE_CHANGE_EVENT, { detail: { mode: nextMode } })
    );
  }

  return nextMode;
}

/**
 * Toggle between demo and live mode and broadcast change.
 */
export function toggleSharedDataMode() {
  const current = getSharedDataMode();
  const next = current === 'demo' ? 'live' : 'demo';
  return setSharedDataMode(next);
}

/**
 * Check if demo mode is currently active.
 */
export function isSharedDemoMode() {
  return getSharedDataMode() === 'demo';
}

/**
 * React hook for consuming and updating data mode synchronously.
 */
export function useDataMode() {
  const [mode, setMode] = useState(getSharedDataMode);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleModeChange = (event) => {
      const newMode = event.detail?.mode || getSharedDataMode();
      setMode(newMode);
    };

    const handleStorageChange = (event) => {
      if (event.key === DATA_MODE_STORAGE_KEY) {
        setMode(getSharedDataMode());
      }
    };

    window.addEventListener(DATA_MODE_CHANGE_EVENT, handleModeChange);
    window.addEventListener('storage', handleStorageChange);

    return () => {
      window.removeEventListener(DATA_MODE_CHANGE_EVENT, handleModeChange);
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  const toggle = useCallback(() => {
    const next = toggleSharedDataMode();
    setMode(next);
  }, []);

  const setSpecificMode = useCallback((newMode) => {
    const next = setSharedDataMode(newMode);
    setMode(next);
  }, []);

  return {
    dataMode: mode,
    isDemoMode: mode === 'demo',
    isLiveMode: mode === 'live',
    toggleDataMode: toggle,
    setDataMode: setSpecificMode,
  };
}
