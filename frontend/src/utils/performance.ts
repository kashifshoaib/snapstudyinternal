/**
 * Frontend performance monitoring utilities.
 * 
 * Provides performance tracking, metrics collection, and optimization helpers.
 */

import React from 'react';
import { analyticsService } from '../services/analyticsService';

// Global performance monitor instance
class PerformanceMonitor {
  private metrics: Map<string, number> = new Map();
  private timers: Map<string, number> = new Map();

  startTimer(name: string): void {
    this.timers.set(name, performance.now());
  }

  endTimer(name: string): number {
    const startTime = this.timers.get(name);
    if (!startTime) {
      console.warn(`Timer ${name} was not started`);
      return 0;
    }

    const duration = performance.now() - startTime;
    this.timers.delete(name);
    this.recordMetric(name, duration);
    return duration;
  }

  recordMetric(name: string, value: number, metadata?: Record<string, any>): void {
    this.metrics.set(name, value);
    analyticsService.recordMetric(name, value, metadata);
  }

  getMetric(name: string): number | undefined {
    return this.metrics.get(name);
  }

  getAllMetrics(): Record<string, number> {
    return Object.fromEntries(this.metrics);
  }

  async measureAsyncOperation<T>(
    name: string,
    operation: () => Promise<T>
  ): Promise<T> {
    this.startTimer(name);
    try {
      const result = await operation();
      this.endTimer(name);
      return result;
    } catch (error) {
      this.endTimer(name);
      this.recordMetric(`${name}_error`, 1);
      throw error;
    }
  }

  measureSyncOperation<T>(name: string, operation: () => T): T {
    this.startTimer(name);
    try {
      const result = operation();
      this.endTimer(name);
      return result;
    } catch (error) {
      this.endTimer(name);
      this.recordMetric(`${name}_error`, 1);
      throw error;
    }
  }
}

export const performanceMonitor = new PerformanceMonitor();

// React hook for performance monitoring
export function usePerformanceMonitor(componentName: string) {
  const measureAsyncOperation = React.useCallback(
    async <T>(operationName: string, operation: () => Promise<T>): Promise<T> => {
      return performanceMonitor.measureAsyncOperation(
        `${componentName}.${operationName}`,
        operation
      );
    },
    [componentName]
  );

  const measureSyncOperation = React.useCallback(
    <T>(operationName: string, operation: () => T): T => {
      return performanceMonitor.measureSyncOperation(
        `${componentName}.${operationName}`,
        operation
      );
    },
    [componentName]
  );

  const recordMetric = React.useCallback(
    (metricName: string, value: number, metadata?: Record<string, any>) => {
      performanceMonitor.recordMetric(
        `${componentName}.${metricName}`,
        value,
        metadata
      );
    },
    [componentName]
  );

  return {
    measureAsyncOperation,
    measureSyncOperation,
    recordMetric
  };
}