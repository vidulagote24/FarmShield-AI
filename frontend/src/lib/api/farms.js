/**
 * FarmShield AI - Farms API Module
 * 
 * Endpoints for farm registration, geospatial boundary management, and details.
 * Aligns with backend/app/api/v1/endpoints/farms.py
 */

import apiClient from './client.js';

export const farmsApi = {
  /**
   * List farms accessible to the authenticated farmer
   */
  async listFarms(params = {}) {
    const query = new URLSearchParams();
    if (params.owner_id) query.append('owner_id', params.owner_id);
    if (params.crop_type) query.append('crop_type', params.crop_type);
    if (params.page) query.append('page', params.page);
    if (params.page_size) query.append('page_size', params.page_size);

    const queryString = query.toString();
    const endpoint = queryString ? `/farms?${queryString}` : '/farms';
    return apiClient.get(endpoint);
  },

  /**
   * Get specific farm details by UUID
   */
  async getFarm(farmId) {
    return apiClient.get(`/farms/${farmId}`);
  },

  /**
   * Create a new farm with spatial boundary
   * @param {Object} payload { name, description, location_name, crop_type, crop_variety, sowing_date, boundary }
   */
  async createFarm(payload) {
    return apiClient.post('/farms', payload);
  },

  /**
   * Update farm metadata
   */
  async updateFarm(farmId, payload) {
    return apiClient.put(`/farms/${farmId}`, payload);
  },

  /**
   * Delete farm and associated zones
   */
  async deleteFarm(farmId) {
    return apiClient.delete(`/farms/${farmId}`);
  },

  /**
   * Retrieve GeoJSON boundary and calculated geodesic area
   */
  async getFarmBoundary(farmId) {
    return apiClient.get(`/farms/${farmId}/boundary`);
  },

  /**
   * Update farm spatial MultiPolygon boundary
   */
  async updateFarmBoundary(farmId, boundary) {
    return apiClient.put(`/farms/${farmId}/boundary`, { boundary });
  },

  /**
   * Retrieve dashboard summary for farm (or composite from services)
   */
  async getFarmDashboard(farmId) {
    return apiClient.get(`/farms/${farmId}/dashboard`);
  },
};

export default farmsApi;
