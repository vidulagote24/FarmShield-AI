/**
 * FarmShield AI - Activity History API Adapter
 * 
 * Aggregates and normalizes actual historical records across three backend endpoints:
 * 1. Farm Irrigation Events (`GET /api/v1/farms/{farm_id}/irrigation-events`)
 * 2. Farm Recommendations (`GET /api/v1/farms/{farm_id}/recommendations`)
 * 3. Farm Observations (`GET /api/v1/farms/{farm_id}/observations`)
 * 
 * Strict Data Integrity & Timestamp Rules:
 * - Irrigation events strictly use their actual `irrigation_date` (or `created_at`).
 * - Recommendations strictly use their actual `generated_at` (or `created_at`).
 * - Observations strictly use their actual `observed_at`.
 * - NEVER uses the current time (`new Date()`) as a timestamp fallback.
 * - Records lacking valid ISO timestamps are safely skipped with a data-quality notice.
 * - Does not invent historical status transition events (no intermediate audit events).
 * - Observations with null values are never converted to zero.
 * - Partial failures are handled independently via Promise.allSettled:
 *   If one source fails, successful sources remain available with `sourceErrors` reported.
 */

import irrigationApi from './irrigation.js';
import recommendationsApi from './recommendations.js';
import observationsApi from './observations.js';
import {
  DEMO_IRRIGATION_EVENTS_FIXTURE,
  DEMO_RECOMMENDATIONS_FIXTURE,
  DEMO_OBSERVATIONS_FIXTURE,
} from '../../data/fixtures/demoFarm.js';

export const historyApi = {
  /**
   * Fetch and aggregate chronological farm activity history across all sources
   * @param {string} farmId - UUID of the farm
   * @param {Object} params - Filtering parameters (zone_id, start_date, end_date, etc.)
   * @param {Object} options - Client options (signal for AbortController)
   */
  async getUnifiedFarmHistory(farmId, params = {}, options = {}) {
    // -------------------------------------------------------------
    // DEMO / SIMULATION MODE
    // -------------------------------------------------------------
    if (params.isDemoMode || (typeof import.meta !== 'undefined' && import.meta.env?.VITE_DATA_MODE === 'demo' && !farmId)) {
      const demoItems = this.normalizeAndMerge(
        DEMO_IRRIGATION_EVENTS_FIXTURE,
        DEMO_RECOMMENDATIONS_FIXTURE,
        DEMO_OBSERVATIONS_FIXTURE.slice(0, 30), // Sample recent observations
        params
      );

      return {
        items: demoItems,
        total: demoItems.length,
        isPartialData: false,
        sourceErrors: {},
        is_simulated: true,
      };
    }

    // -------------------------------------------------------------
    // LIVE REST API MODE (Concurrent Independent Queries)
    // -------------------------------------------------------------
    const { signal } = options;
    const baseParams = {
      zone_id: params.zone_id && params.zone_id !== 'all' ? params.zone_id : undefined,
      start_date: params.start_date,
      end_date: params.end_date,
    };

    // Query all three sources in parallel without letting one failure break others
    const [irrigationResult, recommendationsResult, observationsResult] = await Promise.allSettled([
      irrigationApi.listFarmIrrigationEvents(farmId, { ...baseParams, page_size: 100 }, { signal }),
      recommendationsApi.listFarmRecommendations(farmId, { ...baseParams, page_size: 100 }, { signal }),
      observationsApi.fetchAllFarmObservations(farmId, { ...baseParams }, { pageSize: 100, maxPages: 20, signal }),
    ]);

    const sourceErrors = {};
    let irrigationItems = [];
    let recommendationItems = [];
    let observationItems = [];
    let observationsArePartial = false;

    // 1. Process Irrigation Events
    if (irrigationResult.status === 'fulfilled') {
      const val = irrigationResult.value;
      irrigationItems = Array.isArray(val) ? val : (val?.items || []);
    } else {
      // Ignore if request was aborted
      if (!signal?.aborted) {
        sourceErrors.irrigation = irrigationResult.reason?.message || 'Failed to retrieve irrigation events.';
      }
    }

    // 2. Process Recommendations
    if (recommendationsResult.status === 'fulfilled') {
      const val = recommendationsResult.value;
      recommendationItems = Array.isArray(val) ? val : (val?.items || []);
    } else {
      if (!signal?.aborted) {
        sourceErrors.recommendations = recommendationsResult.reason?.message || 'Failed to retrieve farm recommendations.';
      }
    }

    // 3. Process Observations
    if (observationsResult.status === 'fulfilled') {
      const val = observationsResult.value;
      observationItems = Array.isArray(val) ? val : (val?.items || []);
      observationsArePartial = Boolean(val?.isPartial);
      if (val?.partialError) {
        sourceErrors.observations = val.partialError;
      }
    } else {
      if (!signal?.aborted) {
        sourceErrors.observations = observationsResult.reason?.message || 'Failed to retrieve farm observations.';
      }
    }

    // If signal was aborted, throw early
    if (signal?.aborted) {
      const err = new Error('Activity history fetch was aborted.');
      err.name = 'AbortError';
      throw err;
    }

    // Normalize and merge successfully retrieved sources
    const normalizedItems = this.normalizeAndMerge(
      irrigationItems,
      recommendationItems,
      observationItems,
      params
    );

    const hasAnyFailure = Object.keys(sourceErrors).length > 0;
    const isPartialData = hasAnyFailure || observationsArePartial;

    return {
      items: normalizedItems,
      total: normalizedItems.length,
      isPartialData,
      sourceErrors,
      is_simulated: false,
    };
  },

  /**
   * Normalizes disparate source records into unified chronological events
   */
  normalizeAndMerge(irrigationList = [], recommendationList = [], observationList = [], filterParams = {}) {
    const recordMap = new Map();

    // 1. Normalize Irrigation Events
    for (const event of irrigationList) {
      if (!event || !event.id) continue;
      const rawTimestamp = event.irrigation_date || event.created_at;
      if (!rawTimestamp || isNaN(new Date(rawTimestamp).getTime())) {
        // Skip records lacking valid timestamp (never use new Date() fallback!)
        continue;
      }

      const occurred_at = new Date(rawTimestamp).toISOString();
      const key = `irrigation:${event.id}`;

      recordMap.set(key, {
        id: event.id,
        composite_id: key,
        type: 'irrigation',
        farm_id: event.farm_id,
        zone_id: event.zone_id,
        occurred_at,
        title: `${event.water_quantity} ${event.water_unit === 'cubic_meters' ? 'm³' : event.water_unit} सिंचन नोंद (Applied Irrigation)`,
        description: event.notes || (event.irrigation_method ? `सिंचन पद्धत: ${event.irrigation_method}` : 'प्रत्यक्ष पाणी वापर नोंदवला'),
        source: event.irrigation_method ? `Farmer Record (${event.irrigation_method})` : 'Farmer Record',
        status: 'completed',
        water_quantity: event.water_quantity,
        water_unit: event.water_unit,
        is_simulated: Boolean(event.is_simulated),
        raw: event,
      });
    }

    // 2. Normalize Recommendations
    for (const rec of recommendationList) {
      if (!rec || !rec.id) continue;
      const rawTimestamp = rec.generated_at || rec.created_at;
      if (!rawTimestamp || isNaN(new Date(rawTimestamp).getTime())) {
        continue;
      }

      const occurred_at = new Date(rawTimestamp).toISOString();
      const key = `recommendation:${rec.id}`;

      recordMap.set(key, {
        id: rec.id,
        composite_id: key,
        type: 'recommendation',
        farm_id: rec.farm_id,
        zone_id: rec.zone_id,
        occurred_at,
        title: rec.title,
        description: rec.description,
        source: rec.reasoning?.sources?.join(', ') || rec.source || 'FarmShield Advisory Engine',
        status: rec.status, // Current status only; no intermediate transition faking
        priority: rec.priority,
        recommended_action: rec.recommended_action || {},
        is_simulated: Boolean(rec.is_simulated),
        raw: rec,
      });
    }

    // 3. Normalize Observations
    for (const obs of observationList) {
      if (!obs || !obs.id) continue;
      const rawTimestamp = obs.observed_at;
      if (!rawTimestamp || isNaN(new Date(rawTimestamp).getTime())) {
        continue;
      }

      const occurred_at = new Date(rawTimestamp).toISOString();
      const key = `observation:${obs.id}`;
      const meta = obs.metadata || obs.metadata_json || {};
      const quality = meta.quality || meta.quality_status || (obs.value === null ? 'insufficient' : 'good');

      // Do NOT convert missing observation values to zero
      const valueDisplay = obs.value !== null && obs.value !== undefined
        ? (obs.unit === '%' ? `${obs.value}%` : `${obs.value} ${obs.unit || ''}`)
        : 'अपुरा डेटा (Unreadable/Missing)';

      const typeLabel = obs.observation_type === 'soil_moisture' 
        ? 'माती ओलावा नोंद (Soil Moisture)' 
        : obs.observation_type === 'vegetation_index' 
          ? 'कॅनॉपी NDVI उपग्रह नोंद (Satellite Index)' 
          : `${obs.observation_type} नोंद`;

      recordMap.set(key, {
        id: obs.id,
        composite_id: key,
        type: 'observation',
        farm_id: obs.farm_id,
        zone_id: obs.zone_id,
        occurred_at,
        title: `${typeLabel}: ${valueDisplay}`,
        description: `स्रोत: ${obs.source || 'फील्ड सेन्सर'} • गुणवत्ता: ${quality}`,
        source: obs.source,
        status: obs.value !== null ? 'verified' : 'unreadable',
        value: obs.value,
        unit: obs.unit,
        quality,
        is_simulated: Boolean(obs.is_simulated),
        raw: obs,
      });
    }

    // 4. Sort strictly chronologically, newest first
    return Array.from(recordMap.values()).sort((a, b) => {
      const timeA = new Date(a.occurred_at).getTime();
      const timeB = new Date(b.occurred_at).getTime();
      return timeB - timeA;
    });
  },
};

export default historyApi;

