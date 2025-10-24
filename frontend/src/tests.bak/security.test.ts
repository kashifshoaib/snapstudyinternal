/**
 * Security utilities tests
 */

import { SecurityValidator, CertificateValidator } from '../utils/security';
import { InputValidator, ValidationPresets, CSPValidator } from '../utils/inputValidation';
import { SecureStorage, SessionManager } from '../utils/secureStorage';

describe('SecurityValidator', () => {
  describe('validateHttpsUrl', () => {
    it('should validate HTTPS URLs correctly', () => {
      expect(SecurityValidator.validateHttpsUrl('https://example.com')).toBe(true);
      expect(SecurityValidator.validateHttpsUrl('http://example.com')).toBe(false);
      expect(SecurityValidator.validateHttpsUrl('invalid-url')).toBe(false);
    });
  });

  describe('enforceHttps', () => {
    it('should upgrade HTTP to HTTPS for non-localhost URLs', () => {
      expect(SecurityValidator.enforceHttps('http://example.com')).toBe('https://example.com/');
      expect(SecurityValidator.enforceHttps('https://example.com')).toBe('https://example.com');
      expect(SecurityValidator.enforceHttps('http://localhost:3000')).toBe('http://localhost:3000');
    });
  });

  describe('validateSecurityHeaders', () => {
    it('should validate required security headers', () => {
      const headers = {
        'strict-transport-security': 'max-age=31536000',
        'x-content-type-options': 'nosniff',
        'x-frame-options': 'DENY',
        'x-xss-protection': '1; mode=block'
      };

      const result = SecurityValidator.validateSecurityHeaders(headers);
      expect(result.valid).toBe(true);
      expect(result.missing).toHaveLength(0);
    });

    it('should detect missing security headers', () => {
      const headers = {
        'content-type': 'application/json'
      };

      const result = SecurityValidator.validateSecurityHeaders(headers);
      expect(result.valid).toBe(false);
      expect(result.missing.length).toBeGreaterThan(0);
    });
  });

  describe('sanitizeRequestData', () => {
    it('should sanitize string data', () => {
      const maliciousString = '<script>alert("xss")</script>Hello';
      const sanitized = SecurityValidator.sanitizeRequestData(maliciousString);
      expect(sanitized).not.toContain('<script>');
      expect(sanitized).not.toContain('alert');
    });

    it('should sanitize object data recursively', () => {
      const maliciousData = {
        name: '<script>alert("xss")</script>John',
        email: 'javascript:alert("xss")//user@example.com',
        nested: {
          value: 'onclick="alert(1)"test'
        }
      };

      const sanitized = SecurityValidator.sanitizeRequestData(maliciousData);
      expect(sanitized.name).not.toContain('<script>');
      expect(sanitized.email).not.toContain('javascript:');
      expect(sanitized.nested.value).not.toContain('onclick=');
    });
  });

  describe('validateResponseData', () => {
    it('should detect script injection in response data', () => {
      const maliciousResponse = {
        message: 'Hello <script>alert("xss")</script>',
        data: ['normal', 'javascript:alert(1)']
      };

      const result = SecurityValidator.validateResponseData(maliciousResponse);
      expect(result.safe).toBe(false);
      expect(result.issues.length).toBeGreaterThan(0);
    });

    it('should pass clean response data', () => {
      const cleanResponse = {
        message: 'Hello world',
        data: ['item1', 'item2'],
        user: { name: 'John', email: 'john@example.com' }
      };

      const result = SecurityValidator.validateResponseData(cleanResponse);
      expect(result.safe).toBe(true);
      expect(result.issues).toHaveLength(0);
    });
  });
});

describe('InputValidator', () => {
  describe('sanitizeString', () => {
    it('should remove dangerous HTML tags', () => {
      const malicious = '<script>alert("xss")</script><p>Hello</p>';
      const sanitized = InputValidator.sanitizeString(malicious);
      expect(sanitized).not.toContain('<script>');
      expect(sanitized).not.toContain('alert');
    });

    it('should encode HTML entities', () => {
      const input = '<div>Hello & "World"</div>';
      const sanitized = InputValidator.sanitizeString(input);
      expect(sanitized).toContain('&lt;');
      expect(sanitized).toContain('&gt;');
      expect(sanitized).toContain('&amp;');
      expect(sanitized).toContain('&quot;');
    });
  });

  describe('validateEmail', () => {
    it('should validate correct email addresses', () => {
      const result = InputValidator.validateEmail('user@example.com');
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should reject invalid email addresses', () => {
      const result = InputValidator.validateEmail('invalid-email');
      expect(result.isValid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });

    it('should sanitize email input', () => {
      const result = InputValidator.validateEmail('<script>user@example.com');
      expect(result.sanitizedValue).not.toContain('<script>');
    });
  });

  describe('validatePassword', () => {
    it('should validate strong passwords', () => {
      const result = InputValidator.validatePassword('StrongPass123!');
      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should reject weak passwords', () => {
      const result = InputValidator.validatePassword('weak');
      expect(result.isValid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });
  });

  describe('validateFile', () => {
    it('should validate file size', () => {
      const largeFile = new File(['x'.repeat(11 * 1024 * 1024)], 'large.txt', { type: 'text/plain' });
      const result = InputValidator.validateFile(largeFile, { maxSize: 10 * 1024 * 1024 });
      expect(result.isValid).toBe(false);
      expect(result.errors.some(e => e.includes('size'))).toBe(true);
    });

    it('should validate file types', () => {
      const file = new File(['content'], 'test.exe', { type: 'application/x-executable' });
      const result = InputValidator.validateFile(file, { allowedTypes: ['text/plain'] });
      expect(result.isValid).toBe(false);
    });

    it('should pass valid files', () => {
      const file = new File(['content'], 'test.txt', { type: 'text/plain' });
      const result = InputValidator.validateFile(file, { 
        maxSize: 10 * 1024 * 1024,
        allowedTypes: ['text/plain']
      });
      expect(result.isValid).toBe(true);
    });
  });

  describe('sanitizeChatMessage', () => {
    it('should remove dangerous content from chat messages', () => {
      const malicious = '<script>alert("xss")</script>Hello <b>world</b>';
      const sanitized = InputValidator.sanitizeChatMessage(malicious);
      expect(sanitized).not.toContain('<script>');
      expect(sanitized).toContain('<b>world</b>'); // Safe tags should remain
    });

    it('should limit message length', () => {
      const longMessage = 'x'.repeat(2500);
      const sanitized = InputValidator.sanitizeChatMessage(longMessage);
      expect(sanitized.length).toBeLessThanOrEqual(2003); // 2000 + '...'
    });
  });

  describe('validateUrl', () => {
    it('should validate HTTPS URLs', () => {
      const result = InputValidator.validateUrl('https://example.com');
      expect(result.isValid).toBe(true);
    });

    it('should reject dangerous protocols', () => {
      const result = InputValidator.validateUrl('javascript:alert(1)');
      expect(result.isValid).toBe(false);
      expect(result.errors.some(e => e.includes('protocol'))).toBe(true);
    });
  });
});

describe('CSPValidator', () => {
  describe('validateContent', () => {
    it('should detect inline scripts', () => {
      const content = '<div><script>alert("xss")</script></div>';
      const result = CSPValidator.validateContent(content, false);
      expect(result.safe).toBe(false);
      expect(result.violations.some(v => v.includes('script'))).toBe(true);
    });

    it('should detect inline event handlers', () => {
      const content = '<div onclick="alert(1)">Click me</div>';
      const result = CSPValidator.validateContent(content);
      expect(result.safe).toBe(false);
      expect(result.violations.some(v => v.includes('event handler'))).toBe(true);
    });

    it('should pass clean content', () => {
      const content = '<div>Hello <b>world</b></div>';
      const result = CSPValidator.validateContent(content);
      expect(result.safe).toBe(true);
      expect(result.violations).toHaveLength(0);
    });
  });
});

describe('SecureStorage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('setItem and getItem', () => {
    it('should store and retrieve data without encryption', async () => {
      const testData = { name: 'John', age: 30 };
      await SecureStorage.setItem('test', testData, { encrypt: false });
      
      const retrieved = await SecureStorage.getItem('test');
      expect(retrieved).toEqual(testData);
    });

    it('should handle expiration', async () => {
      const testData = { name: 'John' };
      await SecureStorage.setItem('test', testData, { expirationMinutes: -1 }); // Already expired
      
      const retrieved = await SecureStorage.getItem('test');
      expect(retrieved).toBeNull();
    });

    it('should store data with encryption when supported', async () => {
      if (!SecureStorage.isEncryptionSupported()) {
        console.log('Skipping encryption test - Web Crypto API not available');
        return;
      }

      const testData = { sensitive: 'data' };
      await SecureStorage.setItem('encrypted', testData, { encrypt: true });
      
      const retrieved = await SecureStorage.getItem('encrypted');
      expect(retrieved).toEqual(testData);
    });
  });

  describe('cleanupExpired', () => {
    it('should remove expired items', async () => {
      await SecureStorage.setItem('expired', 'data', { expirationMinutes: -1 });
      await SecureStorage.setItem('valid', 'data', { expirationMinutes: 60 });
      
      await SecureStorage.cleanupExpired();
      
      const expired = await SecureStorage.getItem('expired');
      const valid = await SecureStorage.getItem('valid');
      
      expect(expired).toBeNull();
      expect(valid).not.toBeNull();
    });
  });

  describe('isEncryptionSupported', () => {
    it('should detect Web Crypto API support', () => {
      const supported = SecureStorage.isEncryptionSupported();
      expect(typeof supported).toBe('boolean');
    });
  });
});

describe('SessionManager', () => {
  beforeEach(() => {
    SessionManager.clearSession();
  });

  describe('session management', () => {
    it('should start and validate sessions', async () => {
      SessionManager.startSession(1); // 1 minute
      
      const isValid = await SessionManager.isSessionValid();
      expect(isValid).toBe(true);
    });

    it('should detect expired sessions', async () => {
      SessionManager.startSession(-1); // Already expired
      
      const isValid = await SessionManager.isSessionValid();
      expect(isValid).toBe(false);
    });

    it('should calculate remaining time', async () => {
      SessionManager.startSession(60); // 60 minutes
      
      const remaining = await SessionManager.getRemainingTime();
      expect(remaining).toBeGreaterThan(0);
      expect(remaining).toBeLessThanOrEqual(60);
    });
  });

  describe('session timeout callback', () => {
    it('should allow setting timeout callback', () => {
      const mockCallback = jest.fn();
      SessionManager.onTimeout(mockCallback);
      
      // This test just verifies the callback can be set
      // Actual timeout testing would require waiting or mocking timers
      expect(mockCallback).not.toHaveBeenCalled();
    });
  });
});

// Integration tests
describe('Security Integration', () => {
  it('should work together for secure form handling', async () => {
    const maliciousInput = '<script>alert("xss")</script>user@example.com';
    
    // Validate and sanitize email
    const emailValidation = InputValidator.validateEmail(maliciousInput);
    expect(emailValidation.sanitizedValue).not.toContain('<script>');
    
    // Store securely if valid
    if (emailValidation.isValid) {
      await SecureStorage.setItem('user_email', emailValidation.sanitizedValue, { 
        encrypt: true,
        expirationMinutes: 60 
      });
      
      const stored = await SecureStorage.getItem('user_email');
      expect(stored).toBe(emailValidation.sanitizedValue);
    }
  });

  it('should validate API security configuration', async () => {
    const testUrl = 'https://api.example.com';
    
    // Validate HTTPS
    const httpsValid = SecurityValidator.validateHttpsUrl(testUrl);
    expect(httpsValid).toBe(true);
    
    // Enforce HTTPS
    const secureUrl = SecurityValidator.enforceHttps(testUrl);
    expect(secureUrl).toBe(testUrl);
  });
});