import { useState, useEffect, useCallback, useMemo } from 'react';
import { offlineService, OfflineAction } from '../services/offlineService';
import { analyticsService } from '../services/analyticsService';

export interface OfflineModeState {
  isOnline: boolean;
  pendingActions: number;
  storageUsage: {
    used: number;
    available: number;
    percentage: number;
  };
  isProcessingActions: boolean;
}

export function useOfflineMode() {
  const [state, setState] = useState<OfflineModeState>({
    isOnline: offlineService.getOnlineStatus(),
    pendingActions: offlineService.getActionQueue().length,
    storageUsage: offlineService.getStorageUsage(),
    isProcessingActions: false
  });

  // Update state when online status changes
  useEffect(() => {
    const unsubscribe = offlineService.addOnlineStatusListener((isOnline) => {
      setState(prev => ({
        ...prev,
        isOnline,
        isProcessingActions: isOnline && prev.pendingActions > 0
      }));

      // Track online/offline events
      analyticsService.recordMetric('network_status_change', 1, {
        isOnline,
        pendingActions: offlineService.getActionQueue().length
      });
    });

    return unsubscribe;
  }, []);

  // Update storage usage periodically
  useEffect(() => {
    const updateStorageUsage = () => {
      setState(prev => ({
        ...prev,
        storageUsage: offlineService.getStorageUsage(),
        pendingActions: offlineService.getActionQueue().length
      }));
    };

    const interval = setInterval(updateStorageUsage, 10000); // Update every 10 seconds
    return () => clearInterval(interval);
  }, []);

  // Queue an action for offline processing
  const queueAction = useCallback((
    type: string,
    data: any,
    maxRetries: number = 3
  ): string => {
    const actionId = offlineService.queueAction({
      type,
      data,
      maxRetries
    });

    setState(prev => ({
      ...prev,
      pendingActions: prev.pendingActions + 1
    }));

    return actionId;
  }, []);

  // Process pending actions manually
  const processPendingActions = useCallback(async () => {
    if (!state.isOnline || state.isProcessingActions) {
      return;
    }

    setState(prev => ({ ...prev, isProcessingActions: true }));

    try {
      await offlineService.processPendingActions();
      setState(prev => ({
        ...prev,
        pendingActions: offlineService.getActionQueue().length,
        isProcessingActions: false
      }));
    } catch (error) {
      console.error('Failed to process pending actions:', error);
      setState(prev => ({ ...prev, isProcessingActions: false }));
    }
  }, [state.isOnline, state.isProcessingActions]);

  // Clear all offline data
  const clearOfflineData = useCallback(() => {
    offlineService.clearOfflineData();
    setState(prev => ({
      ...prev,
      pendingActions: 0,
      storageUsage: offlineService.getStorageUsage()
    }));
  }, []);

  // Store data for offline access
  const storeForOffline = useMemo(() => ({
    lesson: (lessonId: string, lessonData: any) => {
      offlineService.storeLessonOffline(lessonId, lessonData);
      setState(prev => ({
        ...prev,
        storageUsage: offlineService.getStorageUsage()
      }));
    },
    progress: (progressData: any, lessonId?: string) => {
      offlineService.storeProgressOffline(progressData, lessonId);
      setState(prev => ({
        ...prev,
        storageUsage: offlineService.getStorageUsage()
      }));
    },
    analytics: (analyticsData: any, type: string) => {
      offlineService.storeAnalyticsOffline(analyticsData, type);
      setState(prev => ({
        ...prev,
        storageUsage: offlineService.getStorageUsage()
      }));
    }
  }), []);

  // Get data from offline storage
  const getFromOffline = useMemo(() => ({
    lesson: (lessonId: string) => offlineService.getLessonOffline(lessonId),
    progress: (lessonId?: string) => offlineService.getProgressOffline(lessonId),
    analytics: (type: string) => offlineService.getAnalyticsOffline(type)
  }), []);

  return {
    // State
    ...state,
    
    // Actions
    queueAction,
    processPendingActions,
    clearOfflineData,
    
    // Data management
    storeForOffline,
    getFromOffline,
    
    // Utilities
    canStoreMore: state.storageUsage.percentage < 90,
    needsCleanup: state.storageUsage.percentage > 80
  };
}

// Hook for offline-aware data fetching
export function useOfflineData<T>(
  key: string,
  fetcher: () => Promise<T>,
  options: {
    storeOffline?: boolean;
    fallbackToOffline?: boolean;
    maxAge?: number;
  } = {}
) {
  const { storeOffline = true, fallbackToOffline = true, maxAge = 24 * 60 * 60 * 1000 } = options;
  const { isOnline, storeForOffline, getFromOffline } = useOfflineMode();
  
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async (forceRefresh = false) => {
    setLoading(true);
    setError(null);

    try {
      if (isOnline || forceRefresh) {
        // Try to fetch from network
        const networkData = await fetcher();
        setData(networkData);
        
        // Store for offline use
        if (storeOffline) {
          if (key.startsWith('lesson-')) {
            const lessonId = key.replace('lesson-', '');
            storeForOffline.lesson(lessonId, networkData);
          } else if (key.startsWith('progress-')) {
            const lessonId = key.replace('progress-', '') || undefined;
            storeForOffline.progress(networkData, lessonId);
          } else if (key.startsWith('analytics-')) {
            const type = key.replace('analytics-', '');
            storeForOffline.analytics(networkData, type);
          }
        }
      } else if (fallbackToOffline) {
        // Try to get from offline storage
        let offlineData = null;
        
        if (key.startsWith('lesson-')) {
          const lessonId = key.replace('lesson-', '');
          offlineData = getFromOffline.lesson(lessonId);
        } else if (key.startsWith('progress-')) {
          const lessonId = key.replace('progress-', '') || undefined;
          offlineData = getFromOffline.progress(lessonId);
        } else if (key.startsWith('analytics-')) {
          const type = key.replace('analytics-', '');
          offlineData = getFromOffline.analytics(type);
        }

        if (offlineData) {
          // Check if data is not too old
          const age = Date.now() - (offlineData.cachedAt || 0);
          if (age <= maxAge) {
            setData(offlineData);
          } else {
            throw new Error('Offline data is too old');
          }
        } else {
          throw new Error('No offline data available');
        }
      } else {
        throw new Error('Network unavailable and offline fallback disabled');
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error);
      
      // Track offline data access attempts
      analyticsService.recordMetric('offline_data_access', 1, {
        key,
        success: false,
        isOnline,
        error: error.message
      });
    } finally {
      setLoading(false);
    }
  }, [key, fetcher, isOnline, storeOffline, fallbackToOffline, maxAge, storeForOffline, getFromOffline]);

  // Initial fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Refetch when coming online
  useEffect(() => {
    if (isOnline && error) {
      fetchData();
    }
  }, [isOnline, error, fetchData]);

  return {
    data,
    loading,
    error,
    refetch: () => fetchData(true),
    isStale: !isOnline && !!data
  };
}