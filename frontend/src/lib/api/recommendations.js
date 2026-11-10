/**
 * FarmShield AI - Recommendations API Module
 * 
 * Endpoints for agronomic recommendations, action codes, reasoning, and workflow statuses.
 * Aligns with backend/app/api/v1/endpoints/recommendations.py & farms.py
 */

import apiClient from './client.js';

export const recommendationsApi = {
  /**
   * List recommendations for a farm with filtering and pagination
   */
  async listFarmRecommendations(farmId, params = {}) {
    const query = new URLSearchParams();
    if (params.zone_id) query.append('zone_id', params.zone_id);
    if (params.status) query.append('status', params.status);
    if (params.priority) query.append('priority', params.priority);
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    if (params.page) query.append('page', params.page);
    if (params.page_size) query.append('page_size', params.page_size);

    const queryString = query.toString();
    const endpoint = queryString 
      ? `/farms/${farmId}/recommendations?${queryString}` 
      : `/farms/${farmId}/recommendations`;
    return apiClient.get(endpoint);
  },

  /**
   * Get specific recommendation details by UUID
   */
  async getRecommendation(recommendationId) {
    return apiClient.get(`/recommendations/${recommendationId}`);
  },

  /**
   * Register a new recommendation for a farm or zone
   */
  async createFarmRecommendation(farmId, payload) {
    return apiClient.post(`/farms/${farmId}/recommendations`, payload);
  },

  /**
   * Update recommendation workflow status (pending, accepted, rejected, completed)
   * @param {string} recommendationId
   * @param {string} status 'pending' | 'accepted' | 'rejected' | 'completed'
   */
  async updateRecommendationStatus(recommendationId, status) {
    return apiClient.patch(`/recommendations/${recommendationId}/status`, { status });
  },
};

export default recommendationsApi;
