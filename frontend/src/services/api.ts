import axios, { AxiosResponse, AxiosError } from 'axios';
import { config } from '../config';
import { SecurityValidator, CertificateValidator } from '../utils/security';

// Enforce HTTPS for API base URL
const secureBaseUrl = SecurityValidator.enforceHttps(config.api.baseUrl);

// Validate HTTPS usage
if (!SecurityValidator.validateHttpsUrl(secureBaseUrl) && !secureBaseUrl.includes('localhost')) {
  console.error('API must use HTTPS in production environment');
}

// Create axios instance with security headers
const api = axios.create({
  baseURL: secureBaseUrl,
  timeout: config.api.timeout,
  headers: {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest', // CSRF protection
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache'
  },
});

// Add auth token and security validation to requests
api.interceptors.request.use(async (config) => {
  // Add auth token from SecureStorage
  try {
    // Import SecureStorage to get the token properly
    const { SecureStorage } = await import('../utils/secureStorage');
    const token = await SecureStorage.getItem('auth_token');
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    } else {
      // Fallback to localStorage for backward compatibility
      const fallbackToken = localStorage.getItem('auth_token');
      if (fallbackToken) {
        config.headers.Authorization = `Bearer ${fallbackToken}`;
      }
    }
  } catch (error) {
    console.warn('Failed to get auth token:', error);
    // Fallback to localStorage
    const fallbackToken = localStorage.getItem('auth_token');
    if (fallbackToken) {
      config.headers.Authorization = `Bearer ${fallbackToken}`;
    }
  }

  // Handle file uploads - don't set Content-Type for FormData
  if (config.data instanceof FormData) {
    // Remove Content-Type header to let browser set it automatically with boundary
    delete config.headers['Content-Type'];
  } else {
    // Sanitize request data for non-file uploads
    if (config.data) {
      config.data = SecurityValidator.sanitizeRequestData(config.data);
    }
  }

  // Sanitize URL parameters
  if (config.params) {
    config.params = SecurityValidator.sanitizeRequestData(config.params);
  }

  // Ensure HTTPS for the request URL
  if (config.url && !config.url.startsWith('/')) {
    config.url = SecurityValidator.enforceHttps(config.url);
  }

  return config;
}, (error) => {
  return Promise.reject(error);
});

// Handle auth errors and security validation
api.interceptors.response.use(
  (response: AxiosResponse) => {
    // Validate security headers
    const headers: Record<string, string> = {};
    Object.entries(response.headers).forEach(([key, value]) => {
      if (typeof value === 'string') {
        headers[key] = value;
      }
    });
    const headerValidation = SecurityValidator.validateSecurityHeaders(headers);
    if (!headerValidation.valid && process.env.NODE_ENV === 'development') {
      console.warn('Missing security headers:', headerValidation.missing);
      if (headerValidation.warnings.length > 0) {
        console.warn('Security header warnings:', headerValidation.warnings);
      }
    }

    // Validate response data for security issues
    if (response.data) {
      const dataValidation = SecurityValidator.validateResponseData(response.data);
      if (!dataValidation.safe) {
        console.error('Security issues in response data:', dataValidation.issues);
        // In production, you might want to reject the response
        if (process.env.NODE_ENV === 'production') {
          return Promise.reject(new Error('Response data failed security validation'));
        }
      }
    }

    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as any;

    // Handle authentication errors with token refresh
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Try to refresh the token
        const { SecureStorage } = await import('../utils/secureStorage');
        const refreshToken = await SecureStorage.getItem('refresh_token');
        
        if (refreshToken) {
          // Attempt token refresh
          const refreshResponse = await axios.post(`${secureBaseUrl}/api/v1/auth/refresh`, {
            refresh_token: refreshToken
          });

          const { access_token, refresh_token: newRefreshToken } = refreshResponse.data;

          // Store new tokens
          await SecureStorage.setItem('auth_token', access_token, {
            encrypt: true,
            expirationMinutes: 60
          });

          if (newRefreshToken) {
            await SecureStorage.setItem('refresh_token', newRefreshToken, {
              encrypt: true,
              expirationMinutes: 10080 // 7 days
            });
          }

          // Update the original request with new token
          originalRequest.headers.Authorization = `Bearer ${access_token}`;

          // Retry the original request
          return api(originalRequest);
        }
      } catch (refreshError) {
        console.warn('Token refresh failed:', refreshError);
        // Fall through to logout logic
      }

      // If refresh fails, logout user
      const isOnLoginPage = window.location.pathname.includes('/login') ||
                            window.location.pathname === '/';

      if (!isOnLoginPage) {
        // Clear all tokens
        try {
          const { SecureStorage } = await import('../utils/secureStorage');
          await SecureStorage.removeItem('auth_token');
          await SecureStorage.removeItem('refresh_token');
        } catch (e) {
          console.warn('Failed to clear secure storage:', e);
        }

        // Clear localStorage fallback
        localStorage.removeItem('auth_token');
        localStorage.removeItem('refresh_token');

        // Dispatch custom event for logout
        window.dispatchEvent(new CustomEvent('auth:expired', {
          detail: { error: error.message, reason: 'token_expired' }
        }));
      }
    }

    // Log security-related errors
    if (error.response?.status === 403) {
      console.warn('Access forbidden - possible security issue');
    }

    // Handle SSL/TLS errors
    if (error.code === 'CERT_INVALID' || error.message?.includes('certificate')) {
      console.error('SSL Certificate validation failed');
    }

    return Promise.reject(error);
  }
);

export default api;

// Security validation functions for external use
export const validateApiSecurity = async (): Promise<{
  httpsEnforced: boolean;
  certificateValid: boolean;
  secureContext: boolean;
}> => {
  const httpsEnforced = SecurityValidator.validateHttpsUrl(secureBaseUrl);
  const certificateValidation = await CertificateValidator.validateCertificate(secureBaseUrl);
  const secureContext = CertificateValidator.isSecureContext();

  return {
    httpsEnforced,
    certificateValid: certificateValidation.valid,
    secureContext
  };
};

// Export security utilities for use in other services
export { SecurityValidator, CertificateValidator };