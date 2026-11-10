/**
 * FarmShield AI - Farm Zones API Module
 * 
 * Endpoints for zone creation, spatial containment validation, inspection, and analysis.
 * Aligns with backend/app/api/v1/endpoints/zones.py & farms.py
 */

import apiClient from './client.js';

export const zonesApi = {
  /**
   * List all zones established within a parent farm
   */
  async listFarmZones(farmId, params = {}) {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page);
    if (params.page_size) query.append('page_size', params.page_size);

    const queryString = query.toString();
    const endpoint = queryString ? `/farms/${farmId}/zones?${queryString}` : `/farms/${farmId}/zones`;
    return apiClient.get(endpoint);
  },

  /**
   * Get specific zone details by UUID
   */
  async getZone(zoneId) {
    return apiClient.get(`/zones/${zoneId}`);
  },

  /**
   * Create a new zone inside a farm (must be spatially contained)
   * @param {string} farmId 
   * @param {Object} payload { zone_name, zone_code, boundary, metadata }
   */
  async createFarmZone(farmId, payload) {
    return apiClient.post(`/farms/${farmId}/zones`, payload);
  },

  /**
   * Update zone metadata or boundary geometry
   */
  async updateZone(zoneId, payload) {
    return apiClient.put(`/zones/${zoneId}`, payload);
  },

  /**
   * Delete zone from a farm
   */
  async deleteZone(zoneId) {
    return apiClient.delete(`/zones/${zoneId}`);
  },

  /**
   * Retrieve latest agronomic zone assessment and evidence summary
   */
  async getZoneAnalysis(zoneId) {
    return apiClient.get(`/zones/${zoneId}/analysis`);
  },
};

export default zonesApi;
