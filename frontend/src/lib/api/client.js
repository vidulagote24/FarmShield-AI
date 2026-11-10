/**
 * FarmShield AI - Centralized HTTP API Client
 * 
 * Provides unified request handling, JWT token injection, timeout handling,
 * and standard error parsing across all API endpoints.
 */

const DEFAULT_TIMEOUT_MS = 10000;
const TOKEN_STORAGE_KEY = 'farmshield_auth_token';

export class ApiClientError extends Error {
  constructor(message, status = 0, details = null, code = 'API_ERROR') {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.details = details;
    this.code = code;
  }
}

class ApiClient {
  constructor() {
    this.baseUrl = (import.meta.env?.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace(/\/+$/, '');
  }

  /**
   * Token Storage Management
   */
  getToken() {
    try {
      return localStorage.getItem(TOKEN_STORAGE_KEY);
    } catch {
      return null;
    }
  }

  setToken(token) {
    try {
      if (token) {
        localStorage.setItem(TOKEN_STORAGE_KEY, token);
      } else {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
      }
    } catch {
      // Storage unavailable or disabled
    }
  }

  clearToken() {
    this.setToken(null);
  }

  /**
   * Internal Request Dispatcher
   */
  async request(endpoint, options = {}) {
    const {
      method = 'GET',
      headers = {},
      body,
      timeout = DEFAULT_TIMEOUT_MS,
      requiresAuth = true,
      ...customOptions
    } = options;

    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = `${this.baseUrl}${cleanEndpoint}`;

    const requestHeaders = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...headers,
    };

    if (requiresAuth) {
      const token = this.getToken();
      if (token) {
        requestHeaders['Authorization'] = `Bearer ${token}`;
      }
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    if (options.signal) {
      if (options.signal.aborted) {
        controller.abort();
      } else {
        options.signal.addEventListener('abort', () => controller.abort(), { once: true });
      }
    }

    const config = {
      method,
      headers: requestHeaders,
      signal: controller.signal,
      ...customOptions,
    };

    if (body !== undefined && body !== null) {
      config.body = typeof body === 'string' ? body : JSON.stringify(body);
    }

    try {
      const response = await fetch(url, config);
      clearTimeout(timeoutId);

      // Handle empty 204 No Content
      if (response.status === 204) {
        return null;
      }

      let data = null;
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        try {
          data = await response.json();
        } catch {
          data = null;
        }
      } else {
        try {
          data = await response.text();
        } catch {
          data = null;
        }
      }

      if (!response.ok) {
        this._handleHttpError(response.status, data);
      }

      return data;
    } catch (err) {
      clearTimeout(timeoutId);

      if (err instanceof ApiClientError) {
        throw err;
      }

      if (err.name === 'AbortError') {
        throw new ApiClientError(
          `Request to ${cleanEndpoint} timed out after ${timeout / 1000}s.`,
          0,
          null,
          'TIMEOUT'
        );
      }

      // Network or CORS failure
      throw new ApiClientError(
        'Unable to connect to FarmShield AI backend. Please verify your connection or server status.',
        0,
        { originalError: err.message },
        'NETWORK_ERROR'
      );
    }
  }

  /**
   * Standardized HTTP Status Mapping
   */
  _handleHttpError(status, data) {
    let message = 'An unexpected server error occurred.';
    let code = 'SERVER_ERROR';
    let details = null;

    if (data && typeof data === 'object') {
      message = data.detail || data.message || data.error?.message || message;
      details = data.error?.details || data.details || null;
      code = data.error?.code || code;
    }

    switch (status) {
      case 400:
        throw new ApiClientError(message || 'Bad request. Please verify the input.', 400, details, 'BAD_REQUEST');
      case 401:
        this.clearToken();
        throw new ApiClientError(message || 'Authentication required or session expired.', 401, details, 'UNAUTHORIZED');
      case 403:
        throw new ApiClientError(message || 'You do not have permission to access this resource.', 403, details, 'FORBIDDEN');
      case 404:
        throw new ApiClientError(message || 'The requested resource was not found.', 404, details, 'NOT_FOUND');
      case 409:
        throw new ApiClientError(message || 'A conflict occurred with existing data.', 409, details, 'CONFLICT');
      case 422:
        throw new ApiClientError(message || 'Validation error. Please verify the provided fields.', 422, details, 'VALIDATION_ERROR');
      case 429:
        throw new ApiClientError(message || 'Rate limit exceeded. Please wait before retrying.', 429, details, 'RATE_LIMITED');
      default:
        if (status >= 500) {
          throw new ApiClientError(message || 'Internal server error. Please try again later.', status, details, 'INTERNAL_SERVER_ERROR');
        }
        throw new ApiClientError(message, status, details, code);
    }
  }

  get(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'GET' });
  }

  post(endpoint, body, options = {}) {
    return this.request(endpoint, { ...options, method: 'POST', body });
  }

  put(endpoint, body, options = {}) {
    return this.request(endpoint, { ...options, method: 'PUT', body });
  }

  patch(endpoint, body, options = {}) {
    return this.request(endpoint, { ...options, method: 'PATCH', body });
  }

  delete(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'DELETE' });
  }
}

export const apiClient = new ApiClient();
export default apiClient;

