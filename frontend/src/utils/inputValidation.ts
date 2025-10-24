/**
 * Input validation and sanitization utilities
 */

export interface ValidationRule {
  required?: boolean;
  minLength?: number;
  maxLength?: number;
  pattern?: RegExp;
  customValidator?: (value: any) => boolean | string;
}

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  sanitizedValue?: any;
}

export class InputValidator {
  private static readonly XSS_PATTERNS = [
    /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi,
    /javascript:/gi,
    /on\w+\s*=/gi,
    /<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi,
    /<object\b[^<]*(?:(?!<\/object>)<[^<]*)*<\/object>/gi,
    /<embed\b[^<]*(?:(?!<\/embed>)<[^<]*)*<\/embed>/gi,
    /<link\b[^<]*(?:(?!<\/link>)<[^<]*)*<\/link>/gi,
    /<meta\b[^<]*(?:(?!<\/meta>)<[^<]*)*<\/meta>/gi,
  ];

  private static readonly SQL_INJECTION_PATTERNS = [
    /(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)/gi,
    /('|(\\')|(;)|(\\)|(\/\*)|(--)|(\*\/))/gi,
  ];

  private static readonly DANGEROUS_PROTOCOLS = [
    'javascript:',
    'data:',
    'vbscript:',
    'file:',
    'ftp:',
  ];

  /**
   * Sanitizes string input to prevent XSS attacks
   */
  static sanitizeString(input: string): string {
    if (typeof input !== 'string') return input;

    let sanitized = input;

    // Remove dangerous HTML tags and scripts
    this.XSS_PATTERNS.forEach(pattern => {
      sanitized = sanitized.replace(pattern, '');
    });

    // Remove dangerous protocols
    this.DANGEROUS_PROTOCOLS.forEach(protocol => {
      const regex = new RegExp(protocol, 'gi');
      sanitized = sanitized.replace(regex, '');
    });

    // Encode HTML entities
    sanitized = sanitized
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#x27;')
      .replace(/\//g, '&#x2F;');

    return sanitized.trim();
  }

  /**
   * Sanitizes HTML content while preserving safe tags
   */
  static sanitizeHtml(input: string, allowedTags: string[] = []): string {
    if (typeof input !== 'string') return input;

    const safeTags = ['b', 'i', 'u', 'strong', 'em', 'p', 'br', 'ul', 'ol', 'li'];
    const allowedTagsSet = new Set([...safeTags, ...allowedTags]);

    let sanitized = input;

    // Remove script tags and dangerous content
    this.XSS_PATTERNS.forEach(pattern => {
      sanitized = sanitized.replace(pattern, '');
    });

    // Remove tags not in allowed list
    sanitized = sanitized.replace(/<\/?([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>/gi, (match, tagName) => {
      if (allowedTagsSet.has(tagName.toLowerCase())) {
        // Remove any event handlers from allowed tags
        return match.replace(/\s+on\w+\s*=\s*["'][^"']*["']/gi, '');
      }
      return '';
    });

    return sanitized;
  }

  /**
   * Validates and sanitizes email addresses
   */
  static validateEmail(email: string): ValidationResult {
    const sanitized = this.sanitizeString(email);
    const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    
    const errors: string[] = [];
    
    if (!sanitized) {
      errors.push('Email is required');
    } else if (!emailPattern.test(sanitized)) {
      errors.push('Please enter a valid email address');
    } else if (sanitized.length > 254) {
      errors.push('Email address is too long');
    }

    return {
      isValid: errors.length === 0,
      errors,
      sanitizedValue: sanitized
    };
  }

  /**
   * Validates and sanitizes passwords
   */
  static validatePassword(password: string): ValidationResult {
    const errors: string[] = [];
    
    if (!password) {
      errors.push('Password is required');
    } else {
      if (password.length < 8) {
        errors.push('Password must be at least 8 characters long');
      }
      if (password.length > 128) {
        errors.push('Password is too long');
      }
      if (!/(?=.*[a-z])/.test(password)) {
        errors.push('Password must contain at least one lowercase letter');
      }
      if (!/(?=.*[A-Z])/.test(password)) {
        errors.push('Password must contain at least one uppercase letter');
      }
      if (!/(?=.*\d)/.test(password)) {
        errors.push('Password must contain at least one number');
      }
      if (!/(?=.*[@$!%*?&])/.test(password)) {
        errors.push('Password must contain at least one special character');
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      sanitizedValue: password // Don't sanitize passwords, just validate
    };
  }

  /**
   * Validates generic text input with custom rules
   */
  static validateText(input: string, rules: ValidationRule = {}): ValidationResult {
    const sanitized = this.sanitizeString(input);
    const errors: string[] = [];

    if (rules.required && !sanitized) {
      errors.push('This field is required');
    }

    if (sanitized) {
      if (rules.minLength && sanitized.length < rules.minLength) {
        errors.push(`Must be at least ${rules.minLength} characters long`);
      }

      if (rules.maxLength && sanitized.length > rules.maxLength) {
        errors.push(`Must be no more than ${rules.maxLength} characters long`);
      }

      if (rules.pattern && !rules.pattern.test(sanitized)) {
        errors.push('Invalid format');
      }

      if (rules.customValidator) {
        const customResult = rules.customValidator(sanitized);
        if (typeof customResult === 'string') {
          errors.push(customResult);
        } else if (!customResult) {
          errors.push('Invalid value');
        }
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      sanitizedValue: sanitized
    };
  }

  /**
   * Validates file uploads
   */
  static validateFile(file: File, options: {
    maxSize?: number; // in bytes
    allowedTypes?: string[];
    allowedExtensions?: string[];
  } = {}): ValidationResult {
    const errors: string[] = [];
    const { maxSize = 10 * 1024 * 1024, allowedTypes = [], allowedExtensions = [] } = options;

    if (!file) {
      errors.push('File is required');
      return { isValid: false, errors };
    }

    // Check file size
    if (file.size > maxSize) {
      errors.push(`File size must be less than ${Math.round(maxSize / (1024 * 1024))}MB`);
    }

    // Check file type
    if (allowedTypes.length > 0 && !allowedTypes.includes(file.type)) {
      errors.push(`File type ${file.type} is not allowed`);
    }

    // Check file extension
    if (allowedExtensions.length > 0) {
      const extension = file.name.split('.').pop()?.toLowerCase();
      if (!extension || !allowedExtensions.includes(extension)) {
        errors.push(`File extension .${extension} is not allowed`);
      }
    }

    // Check for potentially dangerous file names
    const dangerousPatterns = [
      /\.(exe|bat|cmd|com|pif|scr|vbs|js|jar|app|deb|pkg|dmg)$/i,
      /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\.|$)/i,
    ];

    dangerousPatterns.forEach(pattern => {
      if (pattern.test(file.name)) {
        errors.push('File name contains potentially dangerous content');
      }
    });

    return {
      isValid: errors.length === 0,
      errors,
      sanitizedValue: file
    };
  }

  /**
   * Sanitizes chat messages
   */
  static sanitizeChatMessage(message: string): string {
    if (typeof message !== 'string') return '';

    let sanitized = message;

    // Remove script tags and dangerous content
    this.XSS_PATTERNS.forEach(pattern => {
      sanitized = sanitized.replace(pattern, '');
    });

    // Remove SQL injection patterns
    this.SQL_INJECTION_PATTERNS.forEach(pattern => {
      sanitized = sanitized.replace(pattern, '');
    });

    // Allow basic formatting but remove dangerous attributes
    sanitized = sanitized.replace(/<(\w+)([^>]*?)>/gi, (match, tagName, attributes) => {
      const safeTags = ['b', 'i', 'u', 'strong', 'em', 'code', 'pre'];
      if (safeTags.includes(tagName.toLowerCase())) {
        // Remove any event handlers or dangerous attributes
        const cleanAttributes = attributes.replace(/\s+on\w+\s*=\s*["'][^"']*["']/gi, '');
        return `<${tagName}${cleanAttributes}>`;
      }
      return '';
    });

    // Limit message length
    if (sanitized.length > 2000) {
      sanitized = sanitized.substring(0, 2000) + '...';
    }

    return sanitized.trim();
  }

  /**
   * Validates URL inputs
   */
  static validateUrl(url: string): ValidationResult {
    const sanitized = this.sanitizeString(url);
    const errors: string[] = [];

    if (!sanitized) {
      errors.push('URL is required');
    } else {
      try {
        const urlObj = new URL(sanitized);
        
        // Check for dangerous protocols
        if (this.DANGEROUS_PROTOCOLS.some(protocol => 
          urlObj.protocol.toLowerCase().startsWith(protocol))) {
          errors.push('URL protocol is not allowed');
        }

        // Ensure HTTPS in production
        if (process.env.NODE_ENV === 'production' && urlObj.protocol !== 'https:') {
          errors.push('Only HTTPS URLs are allowed');
        }
      } catch {
        errors.push('Please enter a valid URL');
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      sanitizedValue: sanitized
    };
  }

  /**
   * Sanitizes form data object
   */
  static sanitizeFormData(formData: Record<string, any>): Record<string, any> {
    const sanitized: Record<string, any> = {};

    for (const [key, value] of Object.entries(formData)) {
      const sanitizedKey = this.sanitizeString(key);
      
      if (typeof value === 'string') {
        sanitized[sanitizedKey] = this.sanitizeString(value);
      } else if (Array.isArray(value)) {
        sanitized[sanitizedKey] = value.map(item => 
          typeof item === 'string' ? this.sanitizeString(item) : item
        );
      } else if (value && typeof value === 'object' && !(value instanceof File)) {
        sanitized[sanitizedKey] = this.sanitizeFormData(value);
      } else {
        sanitized[sanitizedKey] = value;
      }
    }

    return sanitized;
  }
}

/**
 * Content Security Policy utilities
 */
export class CSPValidator {
  /**
   * Validates content against CSP rules
   */
  static validateContent(content: string, allowInlineScripts = false): {
    safe: boolean;
    violations: string[];
  } {
    const violations: string[] = [];

    // Check for inline scripts
    if (!allowInlineScripts && /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi.test(content)) {
      violations.push('Inline scripts are not allowed');
    }

    // Check for inline event handlers
    if (/on\w+\s*=/gi.test(content)) {
      violations.push('Inline event handlers are not allowed');
    }

    // Check for eval-like functions
    if (/\beval\s*\(|\bFunction\s*\(|\bsetTimeout\s*\(|\bsetInterval\s*\(/gi.test(content)) {
      violations.push('Dynamic code execution is not allowed');
    }

    return {
      safe: violations.length === 0,
      violations
    };
  }
}

// Export validation presets for common use cases
export const ValidationPresets = {
  email: { 
    required: true, 
    maxLength: 254,
    customValidator: (value: string) => InputValidator.validateEmail(value).isValid
  },
  
  password: { 
    required: true, 
    minLength: 8, 
    maxLength: 128,
    customValidator: (value: string) => InputValidator.validatePassword(value).isValid
  },
  
  name: { 
    required: true, 
    minLength: 1, 
    maxLength: 100,
    pattern: /^[a-zA-Z\s'-]+$/
  },
  
  username: { 
    required: true, 
    minLength: 3, 
    maxLength: 30,
    pattern: /^[a-zA-Z0-9_-]+$/
  },
  
  chatMessage: { 
    required: true, 
    maxLength: 2000,
    customValidator: (value: string) => {
      const sanitized = InputValidator.sanitizeChatMessage(value);
      return sanitized.length > 0;
    }
  }
};