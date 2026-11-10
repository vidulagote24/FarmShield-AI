/**
 * FarmShield AI - Observations API Module
 * 
 * Endpoints for weather, vegetation index (NDVI), and soil telemetry observations.
 * Aligns with backend/app/api/v1/endpoints/observations.py & farms.py
 */

import apiClient from './client.js';

export const observationsApi = {
  /**
   * List observations for an owned farm with filtering
   */
  async listFarmObservations(farmId, params = {}, options = {}) {
    const query = new URLSearchParams();
    if (params.zone_id) query.append('zone_id', params.zone_id);
    if (params.observation_type) query.append('observation_type', params.observation_type);
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    if (params.page) query.append('page', params.page);
    if (params.page_size) query.append('page_size', params.page_size);

    const queryString = query.toString();
    const endpoint = queryString 
      ? `/farms/${farmId}/observations?${queryString}` 
      : `/farms/${farmId}/observations`;
    return apiClient.get(endpoint, options);
  },

  /**
   * Complete Pagination Fetcher:
   * Retrieves all observations across pages for a given farm and date filter.
   * - Uses maximum allowed page_size=100 per backend schema.
   * - Iterates through all remaining pages (up to safety limit maxPages=20, i.e. 2000 records).
   * - Deduplicates items using Map by unique item.id.
   * - Handles partial failures without throwing away previously fetched pages.
   * - Reports progress and partial data status.
   */
  async fetchAllFarmObservations(farmId, params = {}, options = {}) {
    const {
      pageSize = 100, // Maximum allowed by backend le=100
      maxPages = 20,  // Safety ceiling (up to 2000 observations)
      onProgress,
      signal,
    } = options;

    const baseParams = { ...params, page_size: pageSize };
    
    // 1. Fetch Page 1
    const firstPageRes = await this.listFarmObservations(farmId, { ...baseParams, page: 1 }, { signal });
    
    // Normalize response structure (support array or PaginatedResponse)
    const itemsFirstPage = Array.isArray(firstPageRes) ? firstPageRes : (firstPageRes?.items || []);
    const totalRecords = typeof firstPageRes?.total === 'number' ? firstPageRes.total : itemsFirstPage.length;
    const totalPages = typeof firstPageRes?.total_pages === 'number' 
      ? firstPageRes.total_pages 
      : Math.ceil(totalRecords / pageSize);

    const recordMap = new Map();
    itemsFirstPage.forEach(item => {
      if (item && item.id) recordMap.set(item.id, item);
    });

    if (onProgress) {
      onProgress({
        loadedPages: 1,
        totalPages: totalPages || 1,
        loadedRecords: recordMap.size,
        totalRecords,
      });
    }

    // If only 1 page needed or empty, return immediately
    if (totalPages <= 1 || recordMap.size >= totalRecords) {
      return {
        items: Array.from(recordMap.values()),
        total: totalRecords,
        isPartial: recordMap.size < totalRecords,
        totalPagesFetched: 1,
        totalPages: totalPages || 1,
        partialError: null,
      };
    }

    // 2. Fetch remaining pages
    const pagesToFetch = Math.min(totalPages, maxPages);
    let partialError = null;
    let fetchedPageCount = 1;

    for (let pageNum = 2; pageNum <= pagesToFetch; pageNum++) {
      if (signal?.aborted) {
        throw new Error('Request was aborted.');
      }

      try {
        const pageRes = await this.listFarmObservations(farmId, { ...baseParams, page: pageNum }, { signal });
        const pageItems = Array.isArray(pageRes) ? pageRes : (pageRes?.items || []);
        
        pageItems.forEach(item => {
          if (item && item.id) recordMap.set(item.id, item);
        });

        fetchedPageCount++;

        if (onProgress) {
          onProgress({
            loadedPages: fetchedPageCount,
            totalPages,
            loadedRecords: recordMap.size,
            totalRecords,
          });
        }
      } catch (err) {
        // Partial page failure: preserve already loaded items and flag partial data
        partialError = `Failed to load page ${pageNum} of ${totalPages}: ${err.message || 'Network error'}`;
        break; // Stop fetching further pages, return what we have
      }
    }

    const isPartial = recordMap.size < totalRecords || Boolean(partialError) || totalPages > maxPages;

    return {
      items: Array.from(recordMap.values()),
      total: totalRecords,
      isPartial,
      totalPagesFetched: fetchedPageCount,
      totalPages,
      partialError,
    };
  },

  /**
   * List observations filtered by zone UUID
   */
  async listZoneObservations(zoneId, params = {}) {
    if (params.farm_id) {
      return this.listFarmObservations(params.farm_id, { ...params, zone_id: zoneId });
    }
    const query = new URLSearchParams();
    query.append('zone_id', zoneId);
    if (params.observation_type) query.append('observation_type', params.observation_type);
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    if (params.page) query.append('page', params.page);
    if (params.page_size) query.append('page_size', params.page_size);

    return apiClient.get(`/observations?${query.toString()}`);
  },

  /**
   * General query observations endpoint
   */
  async listObservations(params = {}) {
    const query = new URLSearchParams();
    if (params.farm_id) query.append('farm_id', params.farm_id);
    if (params.zone_id) query.append('zone_id', params.zone_id);
    if (params.observation_type) query.append('observation_type', params.observation_type);
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    if (params.page) query.append('page', params.page);
    if (params.page_size) query.append('page_size', params.page_size);

    const queryString = query.toString();
    return apiClient.get(queryString ? `/observations?${queryString}` : '/observations');
  },

  /**
   * Get observation details by UUID
   */
  async getObservation(observationId) {
    return apiClient.get(`/observations/${observationId}`);
  },

  /**
   * Record a new observation (sensor, satellite index, or manual reading)
   * @param {string} farmId
   * @param {Object} payload { observation_type, source, observed_at, value, unit, zone_id, metadata }
   */
  async createFarmObservation(farmId, payload) {
    return apiClient.post(`/farms/${farmId}/observations`, payload);
  },

  /**
   * Delete an observation record
   */
  async deleteObservation(observationId) {
    return apiClient.delete(`/observations/${observationId}`);
  },
};

export default observationsApi;

