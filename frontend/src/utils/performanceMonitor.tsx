/**
 * Frontend performance monitoring system for authentication flows.
 * 
 * This module provides comprehensive performance monitoring, optimization utilities,
 * and caching strategies for the frontend authentication system.
 */

import { useState, useEffect, useCallback, useRef } from 'react';

export interface PerformanceMetric {
  operation: string;
  duration: number;
  timestamp: number;
  success: boolean;
  metadata?: Record<string, any>;
}

export interface CacheEntry<T = any> {
  value: T;
  timestamp: number;
  ttl: number;
  hits: number;
}

export interface PerformanceReport {
  metrics: Record<string, PerformanceMetric[]>;
  cacheStats: {
    totalEntries: number;
    hitRate: number;
    totalHits: number;
    totalMisses: number;
  };
  slowOperations: PerformanceMetric[];
  recommendations: string[];
}

class FrontendPerformanceMonitor {
  private metrics: Record<string, PerformanceMetric[]> = {};
  private cache: Map<string, CacheEntry> = new Map();
  private cacheHits = 0;
  private cacheMisses = 0;
  private observers: Set<(report: PerformanceReport) => void> = new Set();

  // Record a performance metric
  recordMetric(
    operation: string,
    duration: number,
    success: boolean = true,
    metadata?: Record<string, any>
  ): void {
    const metric: PerformanceMetric = {
      operation,
      duration,
      timestamp: Date.now(),
      success,
      metadata
    };

    if (!this.metrics[operation]) {
      this.metrics[operation] = [];
    }

    this.metrics[operation].push(metric);

    // Keep only last 100 metrics per operation
    if (this.metrics[operation].length > 100) {
      this.metrics[operation] = this.metrics[operation].slice(-100);
    }

    // Log slow operations (> 1 second)
    if (duration > 1000) {
      console.warn(`Slow operation detected: ${operation} took ${duration}ms`);
    }

    this.notifyObservers();
  }

  // Measure and record an async operation
  async measureAsync<T>(
    operation: string,
    fn: () => Promise<T>,
    metadata?: Record<string, any>
  ): Promise<T> {
    const startTime = performance.now();
    let success = true;
    let error: Error | null = null;

    try {
      const result = await fn();
      return result;
    } catch (e) {
      success = false;
      error = e as Error;
      throw e;
    } finally {
      const duration = performance.now() - startTime;
      this.recordMetric(operation, duration, success, {
        ...metadata,
        error: error?.message
      });
    }
  }

  // Measure and record a sync operation
  measureSync<T>(
    operation: string,
    fn: () => T,
    metadata?: Record<string, any>
  ): T {
    const startTime = performance.now();
    let success = true;
    let error: Error | null = null;

    try {
      const result = fn();
      return result;
    } catch (e) {
      success = false;
      error = e as Error;
      throw e;
    } finally {
      const duration = performance.now() - startTime;
      this.recordMetric(operation, duration, success, {
        ...metadata,
        error: error?.message
      });
    }
  }

  // Cache management
  setCache<T>(key: string, value: T, ttl: number = 300000): void { // 5 minutes default
    this.cache.set(key, {
      value,
      timestamp: Date.now(),
      ttl,
      hits: 0
    });
  }

  getCache<T>(key: string): T | null {
    const entry = this.cache.get(key);
    
    if (!entry) {
      this.cacheMisses++;
      return null;
    }

    // Check if expired
    if (Date.now() - entry.timestamp > entry.ttl) {
      this.cache.delete(key);
      this.cacheMisses++;
      return null;
    }

    entry.hits++;
    this.cacheHits++;
    return entry.value as T;
  }

  clearCache(): void {
    this.cache.clear();
  }

  // Get performance statistics
  getOperationStats(operation: string): {
    totalCalls: number;
    successRate: number;
    avgDuration: number;
    minDuration: number;
    maxDuration: number;
    p95Duration: number;
  } | null {
    const metrics = this.metrics[operation];
    if (!metrics || metrics.length === 0) {
      return null;
    }

    const durations = metrics.map(m => m.duration);
    const successes = metrics.filter(m => m.success).length;

    return {
      totalCalls: metrics.length,
      successRate: (successes / metrics.length) * 100,
      avgDuration: durations.reduce((a, b) => a + b, 0) / durations.length,
      minDuration: Math.min(...durations),
      maxDuration: Math.max(...durations),
      p95Duration: this.percentile(durations, 95)
    };
  }

  // Get slow operations (> 1 second)
  getSlowOperations(limit: number = 20): PerformanceMetric[] {
    const allMetrics = Object.values(this.metrics).flat();
    return allMetrics
      .filter(m => m.duration > 1000)
      .sort((a, b) => b.duration - a.duration)
      .slice(0, limit);
  }

  // Generate performance report
  getPerformanceReport(): PerformanceReport {
    const totalCacheRequests = this.cacheHits + this.cacheMisses;
    
    return {
      metrics: { ...this.metrics },
      cacheStats: {
        totalEntries: this.cache.size,
        hitRate: totalCacheRequests > 0 ? (this.cacheHits / totalCacheRequests) * 100 : 0,
        totalHits: this.cacheHits,
        totalMisses: this.cacheMisses
      },
      slowOperations: this.getSlowOperations(),
      recommendations: this.generateRecommendations()
    };
  }

  // Generate performance recommendations
  private generateRecommendations(): string[] {
    const recommendations: string[] = [];
    const slowOps = this.getSlowOperations(5);
    
    if (slowOps.length > 0) {
      recommendations.push(
        `Found ${slowOps.length} slow operations. Consider optimizing: ${slowOps.map(op => op.operation).join(', ')}`
      );
    }

    const totalCacheRequests = this.cacheHits + this.cacheMisses;
    if (totalCacheRequests > 0) {
      const hitRate = (this.cacheHits / totalCacheRequests) * 100;
      if (hitRate < 70) {
        recommendations.push(
          `Cache hit rate is ${hitRate.toFixed(1)}%. Consider increasing cache TTL or improving cache strategy.`
        );
      }
    }

    // Check for operations with high error rates
    Object.entries(this.metrics).forEach(([operation, metrics]) => {
      const successRate = (metrics.filter(m => m.success).length / metrics.length) * 100;
      if (successRate < 95 && metrics.length > 5) {
        recommendations.push(
          `Operation '${operation}' has ${successRate.toFixed(1)}% success rate. Investigate errors.`
        );
      }
    });

    return recommendations;
  }

  // Subscribe to performance updates
  subscribe(observer: (report: PerformanceReport) => void): () => void {
    this.observers.add(observer);
    return () => this.observers.delete(observer);
  }

  private notifyObservers(): void {
    const report = this.getPerformanceReport();
    this.observers.forEach(observer => observer(report));
  }

  private percentile(arr: number[], p: number): number {
    const sorted = [...arr].sort((a, b) => a - b);
    const index = Math.ceil((p / 100) * sorted.length) - 1;
    return sorted[Math.max(0, Math.min(index, sorted.length - 1))];
  }

  // Cleanup expired cache entries
  cleanupCache(): number {
    const now = Date.now();
    let removed = 0;

    for (const [key, entry] of this.cache.entries()) {
      if (now - entry.timestamp > entry.ttl) {
        this.cache.delete(key);
        removed++;
      }
    }

    return removed;
  }
}

// Global performance monitor instance
export const performanceMonitor = new FrontendPerformanceMonitor();

// React hooks for performance monitoring
export function usePerformanceMonitor(operation?: string) {
  const [report, setReport] = useState<PerformanceReport | null>(null);

  useEffect(() => {
    const unsubscribe = performanceMonitor.subscribe(setReport);
    return unsubscribe;
  }, []);

  const measureAsync = useCallback(async <T extends any>(
    fn: () => Promise<T>,
    operationName?: string,
    metadata?: Record<string, any>
  ): Promise<T> => {
    const opName = operationName || operation || 'unknown';
    return performanceMonitor.measureAsync(opName, fn, metadata);
  }, [operation]);

  const measureSync = useCallback(<T extends any>(
    fn: () => T,
    operationName?: string,
    metadata?: Record<string, any>
  ): T => {
    const opName = operationName || operation || 'unknown';
    return performanceMonitor.measureSync(opName, fn, metadata);
  }, [operation]);

  const recordMetric = useCallback((
    duration: number,
    success: boolean = true,
    operationName?: string,
    metadata?: Record<string, any>
  ) => {
    const opName = operationName || operation || 'unknown';
    performanceMonitor.recordMetric(opName, duration, success, metadata);
  }, [operation]);

  return {
    report,
    measureAsync,
    measureSync,
    recordMetric
  };
}

// Higher-order component for automatic performance monitoring
export function withPerformanceMonitoring<T extends object>(
  Component: React.ComponentType<T>,
  operationName: string
): React.ComponentType<T> {
  return function PerformanceMonitoredComponent(props: T) {
    const renderStartTime = useRef(performance.now());
    
    useEffect(() => {
      const renderDuration = performance.now() - renderStartTime.current;
      performanceMonitor.recordMetric(`${operationName}_render`, renderDuration);
    });

    return <Component {...props} />;
  };
}

// Optimized fetch wrapper with caching and performance monitoring
export async function optimizedFetch(
  url: string,
  options: RequestInit = {},
  cacheKey?: string,
  cacheTtl: number = 300000
): Promise<Response> {
  // Try cache first if cache key provided
  if (cacheKey) {
    const cached = performanceMonitor.getCache<Response>(cacheKey);
    if (cached) {
      return cached.clone();
    }
  }

  // Perform fetch with monitoring
  const response = await performanceMonitor.measureAsync(
    'fetch',
    async () => {
      const resp = await fetch(url, options);
      
      // Cache successful responses
      if (cacheKey && resp.ok) {
        performanceMonitor.setCache(cacheKey, resp.clone(), cacheTtl);
      }
      
      return resp;
    },
    { url, method: options.method || 'GET' }
  );

  return response;
}

// Authentication-specific performance utilities
export class AuthPerformanceUtils {
  // Optimized token validation with caching
  static async validateTokenCached(token: string): Promise<boolean> {
    const cacheKey = `token_valid_${token.slice(-10)}`;
    
    const cached = performanceMonitor.getCache<boolean>(cacheKey);
    if (cached !== null) {
      return cached;
    }

    const isValid = await performanceMonitor.measureAsync(
      'token_validation',
      async () => {
        const response = await fetch('/api/v1/auth/verify', {
          headers: { Authorization: `Bearer ${token}` }
        });
        return response.ok;
      }
    );

    // Cache for 5 minutes
    performanceMonitor.setCache(cacheKey, isValid, 300000);
    return isValid;
  }

  // Optimized user profile loading with caching
  // Removed loadUserProfileCached method - no longer needed

  // Debounced profile update to prevent excessive API calls
  static debounceProfileUpdate = (() => {
    let timeoutId: NodeJS.Timeout;
    
    return (updateData: any, delay: number = 1000): Promise<void> => {
      return new Promise((resolve, reject) => {
        clearTimeout(timeoutId);
        
        timeoutId = setTimeout(async () => {
          try {
            await performanceMonitor.measureAsync(
              'update_user_profile',
              async () => {
                const response = await fetch('/api/v1/users/profile', {
                  method: 'PUT',
                  headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${localStorage.getItem('auth_token')}`
                  },
                  body: JSON.stringify(updateData)
                });
                
                if (!response.ok) {
                  throw new Error('Profile update failed');
                }
                
                return response.json();
              }
            );
            
            // Invalidate cache
            performanceMonitor.clearCache();
            resolve();
          } catch (error) {
            reject(error);
          }
        }, delay);
      });
    };
  })();
}

// Performance monitoring initialization
export function initializePerformanceMonitoring(): void {
  // Set up periodic cache cleanup
  setInterval(() => {
    const removed = performanceMonitor.cleanupCache();
    if (removed > 0) {
      console.log(`Cleaned up ${removed} expired cache entries`);
    }
  }, 60000); // Every minute

  // Monitor page load performance
  if (typeof window !== 'undefined') {
    window.addEventListener('load', () => {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      if (navigation) {
        performanceMonitor.recordMetric(
          'page_load',
          navigation.loadEventEnd - navigation.fetchStart,
          true,
          {
            domContentLoaded: navigation.domContentLoadedEventEnd - navigation.fetchStart,
            firstPaint: navigation.responseEnd - navigation.fetchStart
          }
        );
      }
    });

    // Monitor route changes (for SPAs)
    let lastUrl = location.href;
    new MutationObserver(() => {
      const url = location.href;
      if (url !== lastUrl) {
        performanceMonitor.recordMetric('route_change', performance.now(), true, { url });
        lastUrl = url;
      }
    }).observe(document, { subtree: true, childList: true });
  }

  console.log('Frontend performance monitoring initialized');
}

// Export performance report for debugging
export function logPerformanceReport(): void {
  const report = performanceMonitor.getPerformanceReport();
  console.group('🚀 Performance Report');
  console.log('Metrics:', report.metrics);
  console.log('Cache Stats:', report.cacheStats);
  console.log('Slow Operations:', report.slowOperations);
  console.log('Recommendations:', report.recommendations);
  console.groupEnd();
}