/**
 * Secure storage utilities using Web Crypto API for encryption
 */

export interface StorageOptions {
  encrypt?: boolean;
  expirationMinutes?: number;
}

export interface StoredData {
  data: string;
  timestamp: number;
  expirationTime?: number;
  encrypted: boolean;
}

export class SecureStorage {
  private static readonly ENCRYPTION_ALGORITHM = 'AES-GCM';
  private static readonly KEY_LENGTH = 256;
  private static readonly IV_LENGTH = 12;
  private static readonly STORAGE_PREFIX = 'ss_'; // SnapStudy prefix

  /**
   * Generates a cryptographic key for encryption
   */
  private static async generateKey(): Promise<CryptoKey> {
    return await window.crypto.subtle.generateKey(
      {
        name: this.ENCRYPTION_ALGORITHM,
        length: this.KEY_LENGTH,
      },
      true,
      ['encrypt', 'decrypt']
    );
  }

  /**
   * Derives a key from a password using PBKDF2
   */
  private static async deriveKey(password: string, salt: Uint8Array): Promise<CryptoKey> {
    const encoder = new TextEncoder();
    const keyMaterial = await window.crypto.subtle.importKey(
      'raw',
      encoder.encode(password),
      'PBKDF2',
      false,
      ['deriveBits', 'deriveKey']
    );

    return await window.crypto.subtle.deriveKey(
      {
        name: 'PBKDF2',
        salt: salt,
        iterations: 100000,
        hash: 'SHA-256',
      },
      keyMaterial,
      { name: this.ENCRYPTION_ALGORITHM, length: this.KEY_LENGTH },
      true,
      ['encrypt', 'decrypt']
    );
  }

  /**
   * Encrypts data using AES-GCM
   */
  private static async encryptData(data: string, key: CryptoKey): Promise<{
    encrypted: ArrayBuffer;
    iv: Uint8Array;
  }> {
    const encoder = new TextEncoder();
    const iv = window.crypto.getRandomValues(new Uint8Array(this.IV_LENGTH));
    
    const encrypted = await window.crypto.subtle.encrypt(
      {
        name: this.ENCRYPTION_ALGORITHM,
        iv: iv,
      },
      key,
      encoder.encode(data)
    );

    return { encrypted, iv };
  }

  /**
   * Decrypts data using AES-GCM
   */
  private static async decryptData(
    encryptedData: ArrayBuffer,
    key: CryptoKey,
    iv: Uint8Array
  ): Promise<string> {
    const decrypted = await window.crypto.subtle.decrypt(
      {
        name: this.ENCRYPTION_ALGORITHM,
        iv: iv,
      },
      key,
      encryptedData
    );

    const decoder = new TextDecoder();
    return decoder.decode(decrypted);
  }

  /**
   * Converts ArrayBuffer to base64 string
   */
  private static arrayBufferToBase64(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return window.btoa(binary);
  }

  /**
   * Converts base64 string to ArrayBuffer
   */
  private static base64ToArrayBuffer(base64: string): ArrayBuffer {
    const binary = window.atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
  }

  /**
   * Gets the master key for encryption (derived from session)
   */
  private static async getMasterKey(): Promise<CryptoKey> {
    // Use a combination of session data to derive a consistent key
    const sessionData = `${window.location.origin}-${navigator.userAgent.slice(0, 50)}`;
    const salt = new TextEncoder().encode('snapstudy-salt-2024');
    
    return await this.deriveKey(sessionData, salt);
  }

  /**
   * Stores data securely with optional encryption and expiration
   */
  static async setItem(
    key: string,
    value: any,
    options: StorageOptions = {}
  ): Promise<void> {
    try {
      const { encrypt = false, expirationMinutes } = options;
      const timestamp = Date.now();
      const expirationTime = expirationMinutes 
        ? timestamp + (expirationMinutes * 60 * 1000)
        : undefined;

      let dataToStore = JSON.stringify(value);

      if (encrypt && window.crypto && window.crypto.subtle) {
        try {
          const masterKey = await this.getMasterKey();
          const { encrypted, iv } = await this.encryptData(dataToStore, masterKey);
          
          const encryptedData = {
            data: this.arrayBufferToBase64(encrypted),
            iv: this.arrayBufferToBase64(iv.buffer),
            encrypted: true,
            timestamp,
            expirationTime
          };

          localStorage.setItem(
            `${this.STORAGE_PREFIX}${key}`,
            JSON.stringify(encryptedData)
          );
          return;
        } catch (encryptError) {
          console.warn('Encryption failed, storing without encryption:', encryptError);
        }
      }

      // Store without encryption as fallback
      const storedData: StoredData = {
        data: dataToStore,
        timestamp,
        expirationTime,
        encrypted: false
      };

      localStorage.setItem(
        `${this.STORAGE_PREFIX}${key}`,
        JSON.stringify(storedData)
      );
    } catch (error) {
      console.error('Failed to store data:', error);
      throw new Error('Storage operation failed');
    }
  }

  /**
   * Retrieves and decrypts data from storage
   */
  static async getItem<T = any>(key: string): Promise<T | null> {
    try {
      const storedItem = localStorage.getItem(`${this.STORAGE_PREFIX}${key}`);
      if (!storedItem) return null;

      const storedData: StoredData = JSON.parse(storedItem);

      // Check expiration
      if (storedData.expirationTime && Date.now() > storedData.expirationTime) {
        await this.removeItem(key);
        return null;
      }

      let dataString = storedData.data;

      // Decrypt if encrypted
      if (storedData.encrypted && window.crypto && window.crypto.subtle) {
        try {
          const masterKey = await this.getMasterKey();
          const encryptedBuffer = this.base64ToArrayBuffer(storedData.data);
          const ivBuffer = this.base64ToArrayBuffer((storedData as any).iv);
          const iv = new Uint8Array(ivBuffer);

          dataString = await this.decryptData(encryptedBuffer, masterKey, iv);
        } catch (decryptError) {
          console.error('Decryption failed:', decryptError);
          await this.removeItem(key);
          return null;
        }
      }

      return JSON.parse(dataString);
    } catch (error) {
      console.error('Failed to retrieve data:', error);
      return null;
    }
  }

  /**
   * Removes item from storage
   */
  static async removeItem(key: string): Promise<void> {
    localStorage.removeItem(`${this.STORAGE_PREFIX}${key}`);
  }

  /**
   * Clears all secure storage items
   */
  static async clear(): Promise<void> {
    const keys = Object.keys(localStorage);
    keys.forEach(key => {
      if (key.startsWith(this.STORAGE_PREFIX)) {
        localStorage.removeItem(key);
      }
    });
  }

  /**
   * Cleans up expired items
   */
  static async cleanupExpired(): Promise<void> {
    const keys = Object.keys(localStorage);
    const now = Date.now();

    for (const key of keys) {
      if (key.startsWith(this.STORAGE_PREFIX)) {
        try {
          const storedItem = localStorage.getItem(key);
          if (storedItem) {
            const storedData: StoredData = JSON.parse(storedItem);
            if (storedData.expirationTime && now > storedData.expirationTime) {
              localStorage.removeItem(key);
            }
          }
        } catch (error) {
          // Remove corrupted items
          localStorage.removeItem(key);
        }
      }
    }
  }

  /**
   * Checks if Web Crypto API is available
   */
  static isEncryptionSupported(): boolean {
    return !!(window.crypto && window.crypto.subtle);
  }
}

/**
 * Session timeout manager
 */
export class SessionManager {
  private static readonly SESSION_KEY = 'session_info';
  private static readonly DEFAULT_TIMEOUT_MINUTES = 30;
  private static timeoutId: NodeJS.Timeout | null = null;
  private static onTimeoutCallback: (() => void) | null = null;

  /**
   * Starts session timeout monitoring
   */
  static startSession(timeoutMinutes = this.DEFAULT_TIMEOUT_MINUTES): void {
    this.extendSession(timeoutMinutes);
    this.setupActivityListeners();
  }

  /**
   * Extends the current session
   */
  static extendSession(timeoutMinutes = this.DEFAULT_TIMEOUT_MINUTES): void {
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
    }

    const expirationTime = Date.now() + (timeoutMinutes * 60 * 1000);
    
    SecureStorage.setItem(this.SESSION_KEY, {
      startTime: Date.now(),
      expirationTime,
      timeoutMinutes
    }, { encrypt: true });

    this.timeoutId = setTimeout(() => {
      this.handleSessionTimeout();
    }, timeoutMinutes * 60 * 1000);
  }

  /**
   * Handles session timeout
   */
  private static handleSessionTimeout(): void {
    console.warn('Session timeout detected');
    
    if (this.onTimeoutCallback) {
      this.onTimeoutCallback();
    } else {
      // Default timeout behavior
      this.clearSession();
      alert('Your session has expired. Please log in again.');
      window.location.href = '/login';
    }
  }

  /**
   * Sets up activity listeners to extend session on user activity
   */
  private static setupActivityListeners(): void {
    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
    let lastActivity = Date.now();

    const activityHandler = () => {
      const now = Date.now();
      // Only extend session if more than 5 minutes have passed since last extension
      if (now - lastActivity > 5 * 60 * 1000) {
        lastActivity = now;
        this.extendSession();
      }
    };

    events.forEach(event => {
      document.addEventListener(event, activityHandler, true);
    });
  }

  /**
   * Sets callback for session timeout
   */
  static onTimeout(callback: () => void): void {
    this.onTimeoutCallback = callback;
  }

  /**
   * Clears the current session
   */
  static clearSession(): void {
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }
    SecureStorage.removeItem(this.SESSION_KEY);
  }

  /**
   * Checks if session is still valid
   */
  static async isSessionValid(): Promise<boolean> {
    const sessionInfo = await SecureStorage.getItem(this.SESSION_KEY);
    if (!sessionInfo) return false;

    return Date.now() < sessionInfo.expirationTime;
  }

  /**
   * Gets remaining session time in minutes
   */
  static async getRemainingTime(): Promise<number> {
    const sessionInfo = await SecureStorage.getItem(this.SESSION_KEY);
    if (!sessionInfo) return 0;

    const remaining = sessionInfo.expirationTime - Date.now();
    return Math.max(0, Math.floor(remaining / (60 * 1000)));
  }
}

// Auto-cleanup expired items on page load
if (typeof window !== 'undefined') {
  SecureStorage.cleanupExpired();
}