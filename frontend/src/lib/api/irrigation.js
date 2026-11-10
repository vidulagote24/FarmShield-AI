/**
 * FarmShield AI - Irrigation Events API Module
 * 
 * Endpoints for logging and querying farmer-recorded irrigation events and water volume.
 * Aligns with backend/app/api/v1/endpoints/irrigation.py & farms.py
 */

import apiClient from './client.js';

export const irrigationApi = {
  /**
   * Retrieve irrigation history for a farm with pagination
   */
  async listFarmIrrigationEvents(farmId, params = {}) {
    const query = new URLSearchParams();
    if (params.zone_id) query.append('zone_id', params.zone_id);
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    if (params.page) query.append('page', params.page);
    if (params.page_size) query.append('page_size', params.page_size);

    const queryString = query.toString();
    const endpoint = queryString 
      ? `/farms/${farmId}/irrigation-events?${queryString}` 
      : `/farms/${farmId}/irrigation-events`;
    return apiClient.get(endpoint);
  },

  /**
   * Get irrigation event by UUID
   */
  async getIrrigationEvent(eventId) {
    return apiClient.get(`/irrigation/${eventId}`);
  },

  /**
   * Log a new irrigation event for a farm or zone
   * @param {string} farmId
   * @param {Object} payload { irrigation_date, water_quantity, water_unit, irrigation_method, notes, zone_id }
   */
  async createFarmIrrigationEvent(farmId, payload) {
    return apiClient.post(`/farms/${farmId}/irrigation-events`, payload);
  },

  /**
   * Update details of an existing irrigation event
   */
  async updateIrrigationEvent(eventId, payload) {
    return apiClient.put(`/irrigation/${eventId}`, payload);
  },

  /**
   * Delete an irrigation event record
   */
  async deleteIrrigationEvent(eventId) {
    return apiClient.delete(`/irrigation/${eventId}`);
  },
};

export default irrigationApi;
