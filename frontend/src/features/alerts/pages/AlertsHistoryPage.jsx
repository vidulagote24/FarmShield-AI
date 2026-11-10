/**
 * FarmShield AI - AlertsHistoryPage (VID-06)
 * 
 * Central hub for:
 * 1. Alerts (कृषी इशारे): Actionable, recommendation-derived alerts for urgent farming actions.
 * 2. Activity History (शेती इतिहास): Unified chronological log of irrigation, recommendations, and telemetry.
 * 
 * Strict Agronomic & Safety Integrity:
 * - Decoupled from automated actuation (no pump or valve control).
 * - Excludes terminal/closed recommendation statuses from active alerts.
 * - Respects expiration timestamps without synthetic fabrication.
 * - Handles partial data states and source errors honestly.
 */

import React from 'react';
import { 
  Bell, 
  History, 
  RotateCw, 
  ShieldCheck, 
  AlertTriangle, 
  Sparkles,
  Info,
  CheckCircle2
} from 'lucide-react';
import useAlertsAndHistory from '../hooks/useAlertsAndHistory.js';
import AlertCard from '../components/AlertCard.jsx';
import AlertFilters from '../components/AlertFilters.jsx';
import ActivityTimeline from '../components/ActivityTimeline.jsx';
import AlertsEmptyState from '../components/AlertsEmptyState.jsx';

export default function AlertsHistoryPage({
  farmId,
  currentLang = 'mr',
  onBack,
  onSelectRecommendation,
}) {
  const urlParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
  const initialSubTab = urlParams?.get('subtab') || 'alerts';

  const isMarathi = currentLang === 'mr';
  const isHindi = currentLang === 'hi';

  const {
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
    refresh,
    markAlertViewed,
    isAlertViewed,
    isDemoMode,
    setIsDemoMode,
  } = useAlertsAndHistory(farmId, initialSubTab);

  // Compute category counts for filter buttons
  const counts = React.useMemo(() => {
    return {
      all: alerts.length,
      critical: alerts.filter((a) => a.priority === 'critical' || a.severity === 'critical').length,
      high: alerts.filter((a) => a.priority === 'high' || a.severity === 'high').length,
      agronomic: alerts.filter(
        (a) =>
          a.has_independent_alerts === true ||
          (Array.isArray(a.independent_alerts) && a.independent_alerts.length > 0) ||
          a.alert_type === 'soil_salinity' ||
          a.alert_type === 'crop_vigor_decline'
      ).length,
    };
  }, [alerts]);

  // Compute unread alert count (excluding already-accepted recommendations)
  const unreadAlertsCount = React.useMemo(() => {
    return alerts.filter((a) => !isAlertViewed(a.id) && !a.is_accepted && a.status !== 'accepted').length;
  }, [alerts, isAlertViewed]);

  return (
    <div 
      className="alerts-history-page"
      style={{
        padding: '16px',
        maxWidth: '720px',
        margin: '0 auto',
        paddingBottom: '90px', // Safe clearance for floating bottom navigation
      }}
    >
      {/* Top Header & Refresh Control */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          marginBottom: '16px',
        }}
      >
        <div>
          <h2
            style={{
              fontSize: '20px',
              fontWeight: 800,
              color: '#FFFFFF',
              margin: '0 0 4px 0',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <Bell size={20} color="#C5F36B" />
            <span>{isMarathi ? 'इशारे आणि शेती इतिहास' : isHindi ? 'अलर्ट और खेती इतिहास' : 'Alerts & Activity History'}</span>
          </h2>
          <p style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.65)', margin: 0 }}>
            {isMarathi
              ? 'सल्ला-आधारित कृषी इशारे आणि शेतातील कालक्रमानुसार नोंदी'
              : 'Recommendation-derived advisories & chronological operations log'}
          </p>
        </div>

        {/* Action Controls: Refresh & Demo Mode indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {isDemoMode && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                padding: '4px 8px',
                borderRadius: '8px',
                background: 'rgba(197, 243, 107, 0.15)',
                border: '1px solid rgba(197, 243, 107, 0.4)',
                color: '#C5F36B',
                fontSize: '11px',
                fontWeight: 700,
              }}
            >
              <Sparkles size={11} />
              <span>{isMarathi ? 'नमुना शेत' : 'Demo Farm'}</span>
            </span>
          )}

          <button
            type="button"
            onClick={refresh}
            disabled={isLoading}
            title={isMarathi ? 'ताजी माहिती मिळवा' : 'Refresh data'}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              minHeight: '44px',
              borderRadius: '22px',
              background: 'rgba(255, 255, 255, 0.08)',
              border: '1px solid rgba(255, 255, 255, 0.18)',
              color: '#FFFFFF',
              fontSize: '12px',
              fontWeight: 600,
              cursor: isLoading ? 'not-allowed' : 'pointer',
              opacity: isLoading ? 0.6 : 1,
              transition: 'all 0.18s ease',
            }}
          >
            <RotateCw size={14} className={isLoading ? 'animate-spin' : ''} />
            <span>{isMarathi ? 'रिफ्रेश' : 'Refresh'}</span>
          </button>
        </div>
      </div>

      {/* Main Feature Tabs: Alerts vs Activity History */}
      <div
        role="tablist"
        aria-label={isMarathi ? 'मुख्य विभाग टॅब्स' : 'Main feature tabs'}
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '8px',
          background: 'rgba(10, 43, 28, 0.6)',
          backdropFilter: 'blur(10px)',
          padding: '4px',
          borderRadius: '16px',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          marginBottom: '16px',
        }}
      >
        {/* Tab 1: Alerts */}
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'alerts'}
          onClick={() => setActiveTab('alerts')}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            padding: '10px 14px',
            minHeight: '44px',
            borderRadius: '12px',
            background: activeTab === 'alerts' ? 'rgba(197, 243, 107, 0.25)' : 'transparent',
            border: activeTab === 'alerts' ? '1px solid #C5F36B' : '1px solid transparent',
            color: activeTab === 'alerts' ? '#C5F36B' : 'rgba(255, 255, 255, 0.75)',
            fontSize: '13px',
            fontWeight: 700,
            cursor: 'pointer',
            transition: 'all 0.18s ease',
          }}
        >
          <Bell size={16} />
          <span>{isMarathi ? 'कृषी इशारे' : isHindi ? 'कृषि अलर्ट' : 'Alerts'}</span>
          {unreadAlertsCount > 0 && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                minWidth: '20px',
                height: '20px',
                padding: '0 5px',
                borderRadius: '10px',
                background: '#EF4444',
                color: '#FFFFFF',
                fontSize: '11px',
                fontWeight: 800,
              }}
            >
              {unreadAlertsCount}
            </span>
          )}
        </button>

        {/* Tab 2: Activity History */}
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'history'}
          onClick={() => setActiveTab('history')}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            padding: '10px 14px',
            minHeight: '44px',
            borderRadius: '12px',
            background: activeTab === 'history' ? 'rgba(56, 189, 248, 0.25)' : 'transparent',
            border: activeTab === 'history' ? '1px solid #38BDF8' : '1px solid transparent',
            color: activeTab === 'history' ? '#38BDF8' : 'rgba(255, 255, 255, 0.75)',
            fontSize: '13px',
            fontWeight: 700,
            cursor: 'pointer',
            transition: 'all 0.18s ease',
          }}
        >
          <History size={16} />
          <span>{isMarathi ? 'शेती इतिहास' : isHindi ? 'खेती इतिहास' : 'Activity History'}</span>
          {history.length > 0 && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                minWidth: '20px',
                height: '20px',
                padding: '0 5px',
                borderRadius: '10px',
                background: 'rgba(255, 255, 255, 0.12)',
                color: 'rgba(255, 255, 255, 0.85)',
                fontSize: '11px',
                fontWeight: 700,
              }}
            >
              {history.length}
            </span>
          )}
        </button>
      </div>

      {/* Partial Data Notice when any source is incomplete */}
      {isPartialData && !error && (
        <div
          role="status"
          style={{
            background: 'rgba(245, 158, 11, 0.12)',
            border: '1px solid rgba(245, 158, 11, 0.35)',
            borderRadius: '12px',
            padding: '8px 12px',
            marginBottom: '14px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '11.5px',
            color: '#FDE68A',
          }}
        >
          <Info size={14} color="#F59E0B" style={{ flexShrink: 0 }} />
          <span>
            {isMarathi
              ? 'टीप: डेटा अंशतः उपलब्ध आहे. काही सेन्सर किंवा शिफारस नोंदी अद्यतनित होत आहेत.'
              : 'Notice: Displaying partial dataset. Some observation or recommendation sources are updating.'}
          </span>
        </div>
      )}

      {/* Primary Error State */}
      {error && alerts.length === 0 && history.length === 0 && (
        <div
          role="alert"
          style={{
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.45)',
            borderRadius: '16px',
            padding: '24px 16px',
            textAlign: 'center',
            margin: '20px 0',
          }}
        >
          <AlertTriangle size={36} color="#EF4444" style={{ margin: '0 auto 10px auto' }} />
          <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#FFFFFF', margin: '0 0 6px 0' }}>
            {isMarathi ? 'माहिती लोड करण्यात त्रुटी' : 'Error loading alerts & history'}
          </h4>
          <p style={{ fontSize: '12.5px', color: '#FCA5A5', margin: '0 0 16px 0' }}>
            {error}
          </p>
          <button
            type="button"
            onClick={refresh}
            style={{
              padding: '8px 18px',
              borderRadius: '20px',
              background: '#EF4444',
              color: '#FFFFFF',
              border: 'none',
              fontSize: '12px',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            {isMarathi ? 'पुन्हा प्रयत्न करा' : 'Try Again'}
          </button>
        </div>
      )}

      {/* Loading Skeletons */}
      {isLoading && alerts.length === 0 && history.length === 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', margin: '20px 0' }}>
          {[1, 2, 3].map((sk) => (
            <div
              key={sk}
              style={{
                height: '110px',
                borderRadius: '16px',
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                animation: 'pulse 1.5s infinite ease-in-out',
              }}
            />
          ))}
          <div style={{ textAlign: 'center', fontSize: '12px', color: 'rgba(255, 255, 255, 0.6)' }}>
            {isMarathi ? 'इशारे व शेती नोंदी गोळा करत आहे...' : 'Retrieving alerts and operations history...'}
          </div>
        </div>
      )}

      {/* TAB CONTENT: ALERTS */}
      {activeTab === 'alerts' && (!isLoading || alerts.length > 0) && (
        <div>
          {/* Priority Filters */}
          <AlertFilters
            currentFilter={priorityFilter}
            onFilterChange={setPriorityFilter}
            counts={counts}
            currentLang={currentLang}
          />

          {/* Alert Cards Feed */}
          {filteredAlerts.length > 0 ? (
            <div>
              {filteredAlerts.map((alert) => (
                <AlertCard
                  key={alert.id}
                  alert={alert}
                  isViewed={isAlertViewed(alert.id)}
                  onMarkViewed={markAlertViewed}
                  onSelect={onSelectRecommendation}
                  currentLang={currentLang}
                />
              ))}
            </div>
          ) : (
            <AlertsEmptyState
              type={alerts.length === 0 ? 'alerts' : 'filter_empty'}
              currentLang={currentLang}
              onResetFilter={() => setPriorityFilter('all')}
              onRefresh={refresh}
            />
          )}
        </div>
      )}

      {/* TAB CONTENT: ACTIVITY HISTORY */}
      {activeTab === 'history' && (!isLoading || history.length > 0) && (
        <div>
          {history.length > 0 ? (
            <ActivityTimeline
              items={history}
              currentLang={currentLang}
              isPartialData={isPartialData}
              sourceErrors={sourceErrors}
              onSelectRecommendation={onSelectRecommendation}
            />
          ) : (
            <AlertsEmptyState
              type="history"
              currentLang={currentLang}
              onRefresh={refresh}
            />
          )}
        </div>
      )}
    </div>
  );
}
