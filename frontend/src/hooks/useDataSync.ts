import { useCallback, useEffect, useState } from 'react';
import { useDataSync as useDataSyncContext } from '../contexts/DataSyncContext';
import { dataSyncService, SyncResult } from '../services/dataSyncService';

export interface UseSyncOptions {
  autoSync?: boolean;
  syncInterval?: number;
  onSyncComplete?: (result: SyncResult) => void;
  onSyncError?: (error: Error) => void;
}

export function useDataSync(options: UseSyncOptions = {}) {
  const {
    autoSync = true,
    syncInterval = 5 * 60 * 1000, // 5 minutes
    onSyncComplete,
    onSyncError
  } = options;

  const context = useDataSyncContext();
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSyncResult, setLastSyncResult] = useState<SyncResult | null>(null);

  // Manual sync function
  const sync = useCallback(async () => {
    if (isSyncing || !context.state.isOnline) {
      return;
    }

    setIsSyncing(true);
    try {
      const result = await dataSyncService.syncWithServer(
        context.state.cache,
        context.state.syncQueue
      );

      setLastSyncResult(result);
      
      if (result.success) {
        context.clearSyncQueue();
        onSyncComplete?.(result);
      } else {
        onSyncError?.(new Error(`Sync failed: ${result.errors.map(e => e.error).join(', ')}`));
      }
    } catch (error) {
      const syncError = error instanceof Error ? error : new Error('Sync failed');
      onSyncError?.(syncError);
    } finally {
      setIsSyncing(false);
    }
  }, [context, isSyncing, onSyncComplete, onSyncError]);

  // Auto sync when coming online
  useEffect(() => {
    if (context.state.isOnline && context.state.syncQueue.length > 0) {
      sync();
    }
  }, [context.state.isOnline, context.state.syncQueue.length, sync]);

  // Auto sync interval
  useEffect(() => {
    if (!autoSync || !context.state.isOnline) {
      return;
    }

    const interval = setInterval(() => {
      if (dataSyncService.shouldSync(context.getLastSync(), syncInterval)) {
        sync();
      }
    }, syncInterval);

    return () => clearInterval(interval);
  }, [autoSync, context, sync, syncInterval]);

  // Cached data getter with auto-refresh
  const getCachedData = useCallback(<T>(key: string, fetcher?: () => Promise<T>): T | null => {
    const cached = context.getData<T>(key);
    
    // If data is stale and we have a fetcher, refresh in background
    if (context.isDataStale(key) && fetcher && context.state.isOnline) {
      fetcher().then(data => {
        context.setData(key, data);
      }).catch(error => {
        console.error(`Failed to refresh ${key}:`, error);
      });
    }
    
    return cached;
  }, [context]);

  // Set data with offline queueing
  const setCachedData = useCallback(<T>(key: string, data: T, ttl?: number) => {
    context.setData(key, data, ttl);
    
    // Queue for sync if offline
    if (!context.state.isOnline) {
      context.queueSync(key, data);
    }
  }, [context]);

  return {
    // Sync operations
    sync,
    isSyncing,
    lastSyncResult,
    
    // Data operations
    getCachedData,
    setCachedData,
    invalidateData: context.invalidateData,
    
    // State
    isOnline: context.state.isOnline,
    syncQueueLength: context.state.syncQueue.length,
    lastSync: context.getLastSync(),
    
    // Utilities
    isDataStale: context.isDataStale,
    shouldSync: (threshold?: number) => dataSyncService.shouldSync(context.getLastSync(), threshold)
  };
}

// Hook for specific data types
export function useProgressSync() {
  const { getCachedData, setCachedData, sync } = useDataSync();
  
  const getProgress = useCallback((lessonId?: string) => {
    const key = lessonId ? `progress-${lessonId}` : 'progress-overall';
    return getCachedData(key);
  }, [getCachedData]);
  
  const setProgress = useCallback((progress: any, lessonId?: string) => {
    const key = lessonId ? `progress-${lessonId}` : 'progress-overall';
    setCachedData(key, progress);
  }, [setCachedData]);
  
  const syncProgress = useCallback(async () => {
    try {
      await dataSyncService.syncUserProgress();
      await sync();
    } catch (error) {
      console.error('Failed to sync progress:', error);
      throw error;
    }
  }, [sync]);
  
  return {
    getProgress,
    setProgress,
    syncProgress
  };
}

// Hook for analytics sync
export function useAnalyticsSync() {
  const { getCachedData, setCachedData, sync } = useDataSync();
  
  const getAnalytics = useCallback((type: string) => {
    return getCachedData(`analytics-${type}`);
  }, [getCachedData]);
  
  const setAnalytics = useCallback((data: any, type: string) => {
    setCachedData(`analytics-${type}`, data);
  }, [setCachedData]);
  
  const syncAnalytics = useCallback(async () => {
    try {
      await dataSyncService.syncAnalytics();
      await sync();
    } catch (error) {
      console.error('Failed to sync analytics:', error);
      throw error;
    }
  }, [sync]);
  
  return {
    getAnalytics,
    setAnalytics,
    syncAnalytics
  };
}