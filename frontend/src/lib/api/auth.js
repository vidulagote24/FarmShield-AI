/**
 * FarmShield AI - Authentication API Module
 * 
 * Endpoints for farmer registration, login, current user identity, and session termination.
 * Aligns with backend/app/api/v1/endpoints/auth.py
 */

import apiClient from './client.js';

export const authApi = {
  /**
   * Register a new farmer account
   * @param {Object} payload { email, password, full_name, phone, village }
   */
  async register(payload) {
    return apiClient.post('/auth/register', payload, { requiresAuth: false });
  },

  /**
   * Login with email and password
   * @param {Object} credentials { email, password }
   * @returns {Promise<{ access_token: string, token_type: string, user: Object }>}
   */
  async login(credentials) {
    const data = await apiClient.post('/auth/login', credentials, { requiresAuth: false });
    if (data?.access_token) {
      apiClient.setToken(data.access_token);
    }
    return data;
  },

  /**
   * Retrieve profile for currently authenticated user
   */
  async getMe() {
    return apiClient.get('/auth/me');
  },

  /**
   * Log out active user and invalidate session
   */
  async logout() {
    try {
      await apiClient.post('/auth/logout');
    } finally {
      apiClient.clearToken();
    }
  },

  /**
   * Check whether an active token exists
   */
  isAuthenticated() {
    return Boolean(apiClient.getToken());
  },
};

export default authApi;
