/**
 * Security utilities for API requests and data protection
 */

// HTTPS enforcement and security validation
export class SecurityValidator {
  private static readonly REQUIRED_SECURITY_HEADERS = [
    'strict-transport-security',
    'x-content-type-options',
    'x-frame-options',
    'x-xss-protection'
  ];

  /**
   * Validates that the API URL uses HTTPS
   */
  static validateHttpsUrl(url: string): boolean {
    try {
      const urlObj = new URL(url);
      return urlObj.protocol === 'https:';
    } catch {
      return false;
    }
  }

  /**
   * Enforces HTTPS for API requests
   */
  static enforceHttps(url: string): string {
    if (!url) return url;
    
    try {
      const urlObj = new URL(url);
      if (urlObj.protocol === 'http:' && !this.isLocalhost(urlObj.hostname)) {
        console.warn('Upgrading HTTP to HTTPS for security');
        urlObj.protocol = 'https:';
        return urlObj.toString();
      }
      return url;
    } catch {
      return url;
    }
  }

  /**
   * Checks if hostname is localhost (allowed for development)
   */
  private static isLocalhost(hostname: string): boolean {
    return hostname === 'localhost' || 
           hostname === '127.0.0.1' || 
           hostname.startsWith('192.168.') ||
           hostname.endsWith('.local');
  }

  /**
   * Validates security headers in API responses
   */
  static validateSecurityHeaders(headers: Record<string, string>): {
    valid: boolean;
    missing: string[];
    warnings: string[];
  } {
    const missing: string[] = [];
    const warnings: string[] = [];
    
    // Convert headers to lowercase for case-insensitive comparison
    const lowerHeaders = Object.keys(headers).reduce((acc, key) => {
      acc[key.toLowerCase()] = headers[key];
      return acc;
    }, {} as Record<string, string>);

    // Check required security headers
    this.REQUIRED_SECURITY_HEADERS.forEach(header => {
      if (!lowerHeaders[header]) {
        missing.push(header);
      }
    });

    // Check for specific security header values
    if (lowerHeaders['x-content-type-options'] !== 'nosniff') {
      warnings.push('X-Content-Type-Options should be set to "nosniff"');
    }

    if (lowerHeaders['x-frame-options'] && 
        !['DENY', 'SAMEORIGIN'].includes(lowerHeaders['x-frame-options'].toUpperCase())) {
      warnings.push('X-Frame-Options should be set to "DENY" or "SAMEORIGIN"');
    }

    return {
      valid: missing.length === 0,
      missing,
      warnings
    };
  }

  /**
   * Sanitizes request data to prevent injection attacks
   */
  static sanitizeRequestData(data: any): any {
    if (typeof data === 'string') {
      return this.sanitizeString(data);
    }
    
    if (Array.isArray(data)) {
      return data.map(item => this.sanitizeRequestData(item));
    }
    
    if (data && typeof data === 'object') {
      const sanitized: any = {};
      for (const [key, value] of Object.entries(data)) {
        sanitized[this.sanitizeString(key)] = this.sanitizeRequestData(value);
      }
      return sanitized;
    }
    
    return data;
  }

  /**
   * Sanitizes string data to prevent XSS
   */
  private static sanitizeString(str: string): string {
    if (typeof str !== 'string') return str;
    
    return str
      .replace(/[<>]/g, '') // Remove angle brackets
      .replace(/javascript:/gi, '') // Remove javascript: protocol
      .replace(/on\w+\s*=/gi, '') // Remove event handlers
      .trim();
  }

  /**
   * Validates response data for potential security issues
   */
  static validateResponseData(data: any): {
    safe: boolean;
    issues: string[];
  } {
    const issues: string[] = [];
    
    const checkForScripts = (obj: any, path = ''): void => {
      if (typeof obj === 'string') {
        if (obj.includes('<script') || obj.includes('javascript:')) {
          issues.push(`Potential script injection at ${path}`);
        }
      } else if (Array.isArray(obj)) {
        obj.forEach((item, index) => checkForScripts(item, `${path}[${index}]`));
      } else if (obj && typeof obj === 'object') {
        Object.entries(obj).forEach(([key, value]) => {
          checkForScripts(value, path ? `${path}.${key}` : key);
        });
      }
    };

    checkForScripts(data);

    return {
      safe: issues.length === 0,
      issues
    };
  }
}

/**
 * Certificate validation utilities
 */
export class CertificateValidator {
  /**
   * Validates SSL certificate (browser-based check)
   */
  static async validateCertificate(url: string): Promise<{
    valid: boolean;
    error?: string;
  }> {
    try {
      // In browser environment, we can only do basic checks
      // The actual certificate validation is handled by the browser
      const response = await fetch(url, { 
        method: 'HEAD',
        mode: 'cors'
      });
      
      return { valid: response.ok };
    } catch (error) {
      return { 
        valid: false, 
        error: error instanceof Error ? error.message : 'Certificate validation failed'
      };
    }
  }

  /**
   * Checks if the current page is served over HTTPS
   */
  static isSecureContext(): boolean {
    return window.isSecureContext || window.location.protocol === 'https:';
  }
}