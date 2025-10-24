/**
 * API Optimization Utilities
 *
 * Provides request caching, deduplication, and debouncing to reduce
 * unnecessary API calls and prevent rate limiting issues.
 */

interface CacheEntry {
  data: any;
  timestamp: number;
}

interface DebouncedFunction<T extends (...args: any[]) => any> {
  (...args: Parameters<T>): Promise<ReturnType<T>>;
  cancel: () => void;
}

/**
 * API Request Cache
 * Caches API responses with TTL to avoid duplicate requests
 */
class ApiCache {
  private cache = new Map<string, CacheEntry>();
  private defaultTTL = 5 * 60 * 1000; // 5 minutes

  /**
   * Get cached data if available and not expired
   */
  get(key: string, ttl: number = this.defaultTTL): any | null {
    const entry = this.cache.get(key);
    if (!entry) return null;

    const isExpired = Date.now() - entry.timestamp > ttl;
    if (isExpired) {
      this.cache.delete(key);
      return null;
    }

    return entry.data;
  }

  /**
   * Set cache entry
   */
  set(key: string, data: any): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now()
    });
  }

  /**
   * Remove cache entry
   */
  remove(key: string): void {
    this.cache.delete(key);
  }

  /**
   * Clear all cache entries
   */
  clear(): void {
    this.cache.clear();
  }

  /**
   * Clear expired entries
   */
  clearExpired(ttl: number = this.defaultTTL): void {
    const now = Date.now();
    for (const [key, entry] of this.cache.entries()) {
      if (now - entry.timestamp > ttl) {
        this.cache.delete(key);
      }
    }
  }
}

/**
 * Request Deduplication
 * Prevents duplicate in-flight requests
 */
class RequestDeduplicator {
  private inflightRequests = new Map<string, Promise<any>>();

  /**
   * Execute API call with deduplication
   * If the same request is already in-flight, return the existing promise
   */
  async execute<T>(key: string, apiCall: () => Promise<T>): Promise<T> {
    // Check if request is already in-flight
    if (this.inflightRequests.has(key)) {
      return this.inflightRequests.get(key) as Promise<T>;
    }

    // Execute new request
    const promise = apiCall().finally(() => {
      this.inflightRequests.delete(key);
    });

    this.inflightRequests.set(key, promise);
    return promise;
  }

  /**
   * Check if request is in-flight
   */
  isInFlight(key: string): boolean {
    return this.inflightRequests.has(key);
  }

  /**
   * Clear all in-flight requests
   */
  clear(): void {
    this.inflightRequests.clear();
  }
}

/**
 * Cached API Call
 * Combines caching and deduplication
 */
export const apiCache = new ApiCache();
export const requestDeduplicator = new RequestDeduplicator();

export async function cachedApiCall<T>(
  key: string,
  apiCall: () => Promise<T>,
  options: {
    ttl?: number;
    skipCache?: boolean;
    skipDeduplication?: boolean;
  } = {}
): Promise<T> {
  const { ttl = 5 * 60 * 1000, skipCache = false, skipDeduplication = false } = options;

  // Check cache first
  if (!skipCache) {
    const cached = apiCache.get(key, ttl);
    if (cached !== null) {
      return cached;
    }
  }

  // Execute with deduplication
  const execute = async () => {
    const data = await apiCall();
    apiCache.set(key, data);
    return data;
  };

  if (skipDeduplication) {
    return execute();
  }

  return requestDeduplicator.execute(key, execute);
}

/**
 * Debounce function for API calls
 * Delays execution until after wait milliseconds have elapsed since the last call
 */
export function debounce<T extends (...args: any[]) => Promise<any>>(
  func: T,
  wait: number = 500
): DebouncedFunction<T> {
  let timeoutId: NodeJS.Timeout | null = null;
  let latestResolve: ((value: any) => void) | null = null;
  let latestReject: ((reason: any) => void) | null = null;

  const debouncedFunction = (...args: Parameters<T>): Promise<ReturnType<T>> => {
    return new Promise((resolve, reject) => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }

      latestResolve = resolve;
      latestReject = reject;

      timeoutId = setTimeout(async () => {
        try {
          const result = await func(...args);
          if (latestResolve) latestResolve(result);
        } catch (error) {
          if (latestReject) latestReject(error);
        } finally {
          timeoutId = null;
          latestResolve = null;
          latestReject = null;
        }
      }, wait);
    });
  };

  debouncedFunction.cancel = () => {
    if (timeoutId) {
      clearTimeout(timeoutId);
      timeoutId = null;
    }
    if (latestReject) {
      latestReject(new Error('Debounced function cancelled'));
      latestReject = null;
      latestResolve = null;
    }
  };

  return debouncedFunction;
}

/**
 * Throttle function for API calls
 * Limits execution to once per wait milliseconds
 */
export function throttle<T extends (...args: any[]) => Promise<any>>(
  func: T,
  wait: number = 1000
): (...args: Parameters<T>) => Promise<ReturnType<T>> {
  let lastExecution = 0;
  let timeoutId: NodeJS.Timeout | null = null;

  return async (...args: Parameters<T>): Promise<ReturnType<T>> => {
    const now = Date.now();
    const timeSinceLastExecution = now - lastExecution;

    if (timeSinceLastExecution >= wait) {
      lastExecution = now;
      return func(...args);
    }

    // Queue execution for later
    return new Promise((resolve, reject) => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }

      timeoutId = setTimeout(async () => {
        lastExecution = Date.now();
        try {
          const result = await func(...args);
          resolve(result);
        } catch (error) {
          reject(error);
        }
      }, wait - timeSinceLastExecution);
    });
  };
}

/**
 * Batch API calls
 * Collects multiple calls and executes them together
 */
export class BatchProcessor<T, R> {
  private queue: Array<{
    item: T;
    resolve: (value: R) => void;
    reject: (reason: any) => void;
  }> = [];
  private timeoutId: NodeJS.Timeout | null = null;
  private batchSize: number;
  private batchDelay: number;
  private processBatch: (items: T[]) => Promise<R[]>;

  constructor(
    processBatch: (items: T[]) => Promise<R[]>,
    options: {
      batchSize?: number;
      batchDelay?: number;
    } = {}
  ) {
    this.processBatch = processBatch;
    this.batchSize = options.batchSize || 10;
    this.batchDelay = options.batchDelay || 50;
  }

  async add(item: T): Promise<R> {
    return new Promise((resolve, reject) => {
      this.queue.push({ item, resolve, reject });

      // Process immediately if batch is full
      if (this.queue.length >= this.batchSize) {
        this.flush();
        return;
      }

      // Otherwise, schedule batch processing
      if (this.timeoutId) {
        clearTimeout(this.timeoutId);
      }

      this.timeoutId = setTimeout(() => {
        this.flush();
      }, this.batchDelay);
    });
  }

  private async flush(): Promise<void> {
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }

    if (this.queue.length === 0) return;

    const batch = this.queue.splice(0, this.queue.length);
    const items = batch.map(b => b.item);

    try {
      const results = await this.processBatch(items);
      batch.forEach((b, index) => {
        b.resolve(results[index]);
      });
    } catch (error) {
      batch.forEach(b => {
        b.reject(error);
      });
    }
  }
}

/**
 * Clear all caches and in-flight requests
 * Useful for logout or page transitions
 */
export function clearAllOptimizations(): void {
  apiCache.clear();
  requestDeduplicator.clear();
}

/**
 * Auto-cleanup expired cache entries periodically
 */
let cleanupInterval: NodeJS.Timeout | null = null;

export function startAutoCacheCleanup(intervalMs: number = 60000): void {
  if (cleanupInterval) {
    clearInterval(cleanupInterval);
  }

  cleanupInterval = setInterval(() => {
    apiCache.clearExpired();
  }, intervalMs);
}

export function stopAutoCacheCleanup(): void {
  if (cleanupInterval) {
    clearInterval(cleanupInterval);
    cleanupInterval = null;
  }
}

// Start auto-cleanup by default
if (typeof window !== 'undefined') {
  startAutoCacheCleanup();
}
