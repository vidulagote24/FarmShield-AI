/**
 * FarmShield AI - Alerts API Adapter
 * 
 * Capability Audit & Task 11.1.1 Correctness Rules:
 * The backend does NOT possess a dedicated Alert database model or `/alerts` endpoint.
 * This adapter derives the alert feed strictly from actual farm recommendations,
 * preserving recommendation IDs, provenance, and structured reasoning.
 * 
 * Strict Alert Eligibility Rules (Task 11.1.1):
 * 1. Status Eligibility:
 *    - Strictly limited to 'pending' (awaiting farmer action) and 'accepted' (acknowledged, action planned).
 *    - Recommendations with terminal or closed statuses ('applied', 'completed', 'dismissed', 'rejected', 'expired')
 *      are strictly EXCLUDED from active alerts. They are preserved in the activity history.
 * 2. Expiration Eligibility (valid_until):
 *    - If `valid_until` is present and valid ISO, expired recommendations are strictly EXCLUDED.
 *    - If `valid_until` is null, undefined, or invalid ISO, do NOT fabricate an expiration timestamp;
 *      eligibility remains governed by active status.
 * 3. Alert Candidate Criteria:
 *    - Primary Alerts: Backend priority is 'critical' or 'high'.
 *    - Independent Agronomic Alerts: Structured reasoning explicitly contains independent non-watering alerts
 *      (`Array.isArray(reasoning.independent_alerts) && reasoning.independent_alerts.length > 0`).
 *    - Supporting evidence such as `reasoning.stress_reasons` alone does NOT qualify a recommendation as an alert.
 * 4. Free-Text Rejection:
 *    - Does NOT infer alerts by scraping or guessing from generic text strings (drought/pest).
 * 5. Stable Identification & Deduplication:
 *    - Alerts strictly use the stable recommendation UUID as their `id` (`id: rec.id`).
 *    - Exactly one alert per recommendation ID (zero duplication).
 * 6. Classification Metadata:
 *    - Clearly carries `alert_origin: 'recommendation_derived'`.
 *    - Explicitly sets `is_delivered_notification: false` (no claims of SMS or WhatsApp delivery).
 */

import recommendationsApi from './recommendations.js';
import { DEMO_ALERTS_FIXTURE } from '../../data/fixtures/demoFarm.js';

export const alertsApi = {
  /**
   * Derive active alerts for a farm from actual backend recommendations
   * @param {string} farmId - UUID of the farm
   * @param {Object} params - Query filters (zone_id, status, priority, referenceTime, etc.)
   * @param {Object} options - Client options (signal for AbortController, referenceTime)
   */
  async listFarmAlerts(farmId, params = {}, options = {}) {
    // 1. In demo mode, return curated demo alerts fixture
    if (params.isDemoMode || (typeof import.meta !== 'undefined' && import.meta.env?.VITE_DATA_MODE === 'demo' && !farmId)) {
      let filtered = [...DEMO_ALERTS_FIXTURE];
      if (params.priority && params.priority !== 'all') {
        filtered = filtered.filter(a => a.severity === params.priority || a.priority === params.priority);
      }
      if (params.zone_id && params.zone_id !== 'all') {
        filtered = filtered.filter(a => a.zone_id === params.zone_id);
      }
      return {
        items: filtered,
        total: filtered.length,
        origin: 'recommendation_derived',
        is_simulated: true,
      };
    }

    // 2. Fetch actual recommendations from backend
    const recParams = {
      ...params,
      page_size: params.page_size || 50,
    };

    const res = await recommendationsApi.listFarmRecommendations(farmId, recParams, options);
    const recList = Array.isArray(res) ? res : (res?.items || []);

    const alertMap = new Map();
    const referenceTime = options.referenceTime || params.referenceTime || Date.now();
    const refTimestamp = new Date(referenceTime).getTime();

    for (const rec of recList) {
      if (!rec || !rec.id) continue;

      // -------------------------------------------------------------
      // 1. Status Eligibility Check:
      // Only 'pending' or 'accepted' qualify as active alerts.
      // 'applied', 'completed', 'dismissed', 'rejected', 'expired' are strictly excluded.
      // -------------------------------------------------------------
      const status = (rec.status || 'pending').toLowerCase();
      const isActiveStatus = status === 'pending' || status === 'accepted';
      if (!isActiveStatus) {
        continue;
      }

      // -------------------------------------------------------------
      // 2. Expiration Eligibility Check (valid_until):
      // If valid_until exists and is valid, check against reference timestamp.
      // If missing/invalid, do NOT fabricate an expiration timestamp.
      // -------------------------------------------------------------
      if (rec.valid_until) {
        const validUntilTime = new Date(rec.valid_until).getTime();
        if (!isNaN(validUntilTime) && validUntilTime < refTimestamp) {
          continue; // Expired recommendation is not an active alert
        }
      }

      // -------------------------------------------------------------
      // 3. Alert Qualification Criteria:
      // Criterion A: Primary alert - Backend priority is 'critical' or 'high'.
      // Criterion B: Independent agronomic alert - Structured reasoning explicitly contains independent non-watering alerts.
      // Note: stress_reasons alone are recommendation evidence, NOT independent agronomic alerts.
      // -------------------------------------------------------------
      const isHighOrCritical = rec.priority === 'critical' || rec.priority === 'high';
      const reasoning = rec.reasoning || {};
      const hasIndependentAlerts = Array.isArray(reasoning.independent_alerts) && reasoning.independent_alerts.length > 0;

      if (!isHighOrCritical && !hasIndependentAlerts) {
        continue; // Low or medium priority without independent alerts is an advisory, not an alert
      }

      // -------------------------------------------------------------
      // 4. Stable Mapping & Deduplication
      // -------------------------------------------------------------
      if (!alertMap.has(rec.id)) {
        alertMap.set(rec.id, {
          id: rec.id, // Stable recommendation UUID (no artificial IDs)
          recommendation_id: rec.id,
          farm_id: rec.farm_id,
          zone_id: rec.zone_id,
          title: rec.title,
          title_en: rec.title_en || rec.title,
          description: rec.description,
          description_en: rec.description_en || rec.description,
          priority: rec.priority, // Actual backend priority: 'critical' | 'high' | 'medium' | 'low'
          severity: rec.priority === 'critical' ? 'critical' : rec.priority === 'high' ? 'high' : 'warning',
          status: rec.status, // Actual status: 'pending' or 'accepted'
          is_accepted: status === 'accepted',
          generated_at: rec.generated_at,
          valid_until: rec.valid_until,
          created_at: rec.created_at || rec.generated_at,
          source: reasoning.sources?.join(', ') || rec.source || 'FarmShield Advisory Engine',
          independent_alerts: hasIndependentAlerts ? reasoning.independent_alerts : [],
          has_independent_alerts: hasIndependentAlerts,
          stress_reasons: Array.isArray(reasoning.stress_reasons) ? reasoning.stress_reasons : [],
          recommended_action: rec.recommended_action || {},
          reasoning: rec.reasoning || {},
          alert_origin: 'recommendation_derived',
          is_delivered_notification: false, // Strictly false: not an SMS/push notification
          is_simulated: Boolean(rec.is_simulated),
          raw_recommendation: rec,
        });
      }
    }

    const items = Array.from(alertMap.values()).sort((a, b) => {
      const timeA = new Date(a.generated_at || a.created_at).getTime() || 0;
      const timeB = new Date(b.generated_at || b.created_at).getTime() || 0;
      return timeB - timeA;
    });

    return {
      items,
      total: items.length,
      origin: 'recommendation_derived',
      is_simulated: false,
    };
  },

  /**
   * Dismiss an alert by transitioning the parent recommendation status to 'dismissed'
   * @param {string} recommendationId - UUID of the recommendation
   */
  async dismissAlert(recommendationId) {
    return recommendationsApi.updateRecommendationStatus(recommendationId, 'dismissed');
  },

  /**
   * Acknowledge an alert by transitioning the parent recommendation status to 'accepted'
   * @param {string} recommendationId - UUID of the recommendation
   */
  async acknowledgeAlert(recommendationId) {
    return recommendationsApi.updateRecommendationStatus(recommendationId, 'accepted');
  },
};

export default alertsApi;
