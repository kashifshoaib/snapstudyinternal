/**
 * Network status manager for graceful degradation.
 * 
 * This module handles network connectivity issues and provides
 * graceful degradation strategies for offline scenarios.
 */

import { useState, useEffect, useCallback } from 'react';
import { notificationManager } from './loadingStateManager';

export interface NetworkStatus {
  isOnline: boolean;
  isSlowConnection: boolean;
  connectionType: string;
  effectiveType: string;
  downlink: number;
  rtt: number;
  lastOnline: Date | null;
  lastOffline: Date | null;
}

export interface OfflineQueueItem {
  id: string;
  operation: string;
  data: any;
  timestamp: Date;
  retryCount: number;
  maxRetries: number;
}

class NetworkStatusManager {
  private listeners: Set<(status: NetworkStatus) => void> = new Set();
  private offlineQueue: OfflineQueueItem[] = [];
  private currentStatus: NetworkStatus = {
    isOnline: navigator.onLine,
    isSlowConnection: false,
    connectionType: 'unknown',
    effectiveType: 'unknown',
    downlink: 0,
    rtt: 0,
    lastOnline: navigator.onLine ? new Date() : null,
    lastOffline: null
  };

  constructor() {
    this.initializeNetworkMonitoring();
    this.loadOfflineQueue();
  }

  private initializeNetworkMonitoring() {
    // Basic online/offline detection
    window.addEventListener('online', this.handleOnline);
    window.addEventListener('offline', this.handleOffline);

    // Network Information API (if available)
    if ('connection' in navigator) {
      const connection = (navigator as any).connection;
      this.updateConnectionInfo(connection);
      
      connection.addEventListener('change', () => {
        this.updateConnectionInfo(connection);
      });
    }

    // Periodic connectivity check
    this.startPeriodicCheck();
  }

  private handleOnline = () => {
    this.currentStatus = {
      ...this.currentStatus,
      isOnline: true,
      lastOnline: new Date()
    };
    
    this.notifyListeners();
    this.processOfflineQueue();
    
    notificationManager.success(
      'Back Online',
      'Your connection has been restored. Syncing your data...'
    );
  };

  private handleOffline = () => {
    this.currentStatus = {
      ...this.currentStatus,
      isOnline: false,
      lastOffline: new Date()
    };
    
    this.notifyListeners();
    
    notificationManager.warning(
      'Connection Lost',
      'You\'re currently offline. Your changes will be saved and synced when you reconnect.',
      10000
    );
  };

  private updateConnectionInfo(connection: any) {
    this.currentStatus = {
      ...this.currentStatus,
      connectionType: connection.type || 'unknown',
      effectiveType: connection.effectiveType || 'unknown',
      downlink: connection.downlink || 0,
      rtt: connection.rtt || 0,
      isSlowConnection: this.isSlowConnection(connection)
    };
    
    this.notifyListeners();
    
    // Warn about slow connection
    if (this.currentStatus.isSlowConnection) {
      notificationManager.info(
        'Slow Connection',
        'Your connection appears to be slow. Some features may take longer to load.',
        8000
      );
    }
  }

  private isSlowConnection(connection: any): boolean {
    // Consider connection slow if:
    // - Effective type is 'slow-2g' or '2g'
    // - RTT is > 1000ms
    // - Downlink is < 0.5 Mbps
    return (
      connection.effectiveType === 'slow-2g' ||
      connection.effectiveType === '2g' ||
      connection.rtt > 1000 ||
      connection.downlink < 0.5
    );
  }

  private startPeriodicCheck() {
    setInterval(() => {
      this.checkConnectivity();
    }, 30000); // Check every 30 seconds
  }

  private async checkConnectivity() {
    try {
      // Try to fetch a small resource to verify connectivity
      const response = await fetch('/api/health', {
        method: 'HEAD',
        cache: 'no-cache',
        signal: AbortSignal.timeout(5000)
      });
      
      if (!this.currentStatus.isOnline && response.ok) {
        // We're back online
        this.handleOnline();
      }
    } catch (error) {
      if (this.currentStatus.isOnline) {
        // We've gone offline
        this.handleOffline();
      }
    }
  }

  subscribe(listener: (status: NetworkStatus) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  getStatus(): NetworkStatus {
    return { ...this.currentStatus };
  }

  // Offline queue management
  addToOfflineQueue(operation: string, data: any, maxRetries = 3): string {
    const item: OfflineQueueItem = {
      id: `offline-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      operation,
      data,
      timestamp: new Date(),
      retryCount: 0,
      maxRetries
    };

    this.offlineQueue.push(item);
    this.saveOfflineQueue();
    
    return item.id;
  }

  removeFromOfflineQueue(id: string): void {
    this.offlineQueue = this.offlineQueue.filter(item => item.id !== id);
    this.saveOfflineQueue();
  }

  getOfflineQueue(): OfflineQueueItem[] {
    return [...this.offlineQueue];
  }

  private async processOfflineQueue() {
    if (!this.currentStatus.isOnline || this.offlineQueue.length === 0) {
      return;
    }

    const itemsToProcess = [...this.offlineQueue];
    
    for (const item of itemsToProcess) {
      try {
        await this.retryOfflineOperation(item);
        this.removeFromOfflineQueue(item.id);
      } catch (error) {
        item.retryCount++;
        
        if (item.retryCount >= item.maxRetries) {
          // Max retries reached, remove from queue
          this.removeFromOfflineQueue(item.id);
          
          notificationManager.error(
            'Sync Failed',
            `Failed to sync "${item.operation}" after ${item.maxRetries} attempts.`,
            true
          );
        }
      }
    }
    
    this.saveOfflineQueue();
  }

  private async retryOfflineOperation(item: OfflineQueueItem): Promise<void> {
    // This would be implemented based on your specific operations
    // For now, it's a placeholder that simulates the retry
    
    switch (item.operation) {
      case 'updateProfile':
        // Retry profile update
        await this.retryProfileUpdate(item.data);
        break;
      case 'uploadLesson':
        // Retry lesson upload
        await this.retryLessonUpload(item.data);
        break;
      case 'saveProgress':
        // Retry progress save
        await this.retryProgressSave(item.data);
        break;
      default:
        throw new Error(`Unknown operation: ${item.operation}`);
    }
  }

  private async retryProfileUpdate(data: any): Promise<void> {
    // Implementation would call the actual profile update API
    const response = await fetch('/api/v1/users/profile', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAuthToken()}`
      },
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      throw new Error('Profile update failed');
    }
  }

  private async retryLessonUpload(data: any): Promise<void> {
    // Implementation would call the actual lesson upload API
    const formData = new FormData();
    formData.append('file', data.file);

    const response = await fetch('/api/v1/lessons/upload', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.getAuthToken()}`
      },
      body: formData
    });

    if (!response.ok) {
      throw new Error('Lesson upload failed');
    }
  }

  private async retryProgressSave(data: any): Promise<void> {
    // Implementation would call the actual progress save API
    const response = await fetch('/api/v1/analytics/track-event', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAuthToken()}`
      },
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      throw new Error('Progress save failed');
    }
  }

  private getAuthToken(): string | null {
    try {
      const authData = localStorage.getItem('auth');
      if (authData) {
        const parsed = JSON.parse(authData);
        return parsed.access_token;
      }
    } catch (error) {
      console.error('Failed to get auth token:', error);
    }
    return null;
  }

  private saveOfflineQueue(): void {
    try {
      localStorage.setItem('offlineQueue', JSON.stringify(this.offlineQueue));
    } catch (error) {
      console.error('Failed to save offline queue:', error);
    }
  }

  private loadOfflineQueue(): void {
    try {
      const saved = localStorage.getItem('offlineQueue');
      if (saved) {
        this.offlineQueue = JSON.parse(saved).map((item: any) => ({
          ...item,
          timestamp: new Date(item.timestamp)
        }));
      }
    } catch (error) {
      console.error('Failed to load offline queue:', error);
      this.offlineQueue = [];
    }
  }

  private notifyListeners(): void {
    this.listeners.forEach(listener => listener(this.currentStatus));
  }

  // Cleanup
  destroy(): void {
    window.removeEventListener('online', this.handleOnline);
    window.removeEventListener('offline', this.handleOffline);
  }
}

// Global instance
export const networkStatusManager = new NetworkStatusManager();

// React hook for using network status
export function useNetworkStatus(): [NetworkStatus, {
  addToOfflineQueue: (operation: string, data: any, maxRetries?: number) => string;
  getOfflineQueue: () => OfflineQueueItem[];
}] {
  const [status, setStatus] = useState<NetworkStatus>(networkStatusManager.getStatus());

  useEffect(() => {
    const unsubscribe = networkStatusManager.subscribe(setStatus);
    return unsubscribe;
  }, []);

  const actions = {
    addToOfflineQueue: useCallback((operation: string, data: any, maxRetries = 3) => {
      return networkStatusManager.addToOfflineQueue(operation, data, maxRetries);
    }, []),
    getOfflineQueue: useCallback(() => {
      return networkStatusManager.getOfflineQueue();
    }, [])
  };

  return [status, actions];
}

// Higher-order component for network-aware components
export function withNetworkStatus<T extends object>(
  Component: React.ComponentType<T>
): React.ComponentType<T> {
  return function NetworkStatusWrapper(props: T) {
    const [networkStatus, networkActions] = useNetworkStatus();
    
    const enhancedProps = {
      ...props,
      networkStatus,
      networkActions
    } as T & {
      networkStatus: NetworkStatus;
      networkActions: ReturnType<typeof useNetworkStatus>[1];
    };

    return <Component {...enhancedProps} />;
  };
}

// Utility functions for network-aware operations
export async function executeWithNetworkFallback<T>(
  operation: () => Promise<T>,
  fallbackData?: T,
  operationName?: string
): Promise<T> {
  try {
    if (!navigator.onLine) {
      if (fallbackData !== undefined) {
        notificationManager.info(
          'Offline Mode',
          'Showing cached data. Changes will sync when you reconnect.'
        );
        return fallbackData;
      }
      throw new Error('Operation requires internet connection');
    }

    return await operation();
  } catch (error) {
    if (!navigator.onLine && fallbackData !== undefined) {
      return fallbackData;
    }
    
    // Queue for retry if it's a network error
    if (operationName && error instanceof Error && 
        (error.message.includes('fetch') || error.message.includes('network'))) {
      notificationManager.warning(
        'Connection Issue',
        'Operation will be retried when connection is restored.'
      );
    }
    
    throw error;
  }
}

// Service worker integration for offline support
export function registerOfflineSupport(): void {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js')
      .then(registration => {
        console.log('Service Worker registered:', registration);
      })
      .catch(error => {
        console.error('Service Worker registration failed:', error);
      });
  }
}