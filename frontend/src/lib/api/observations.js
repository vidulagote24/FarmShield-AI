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
  async listFarmObservations(farmId, params = {}) {
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
    return apiClient.get(endpoint);
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

