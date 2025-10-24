/**
 * Hook for managing loading states across components
 */

import { useState, useCallback, useRef, useEffect } from 'react';

interface LoadingState {
  [key: string]: boolean;
}

interface LoadingOptions {
  timeout?: number;
  onTimeout?: () => void;
}

export const useLoadingState = (initialState: LoadingState = {}) => {
  const [loadingStates, setLoadingStates] = useState<LoadingState>(initialState);
  const timeoutsRef = useRef<{ [key: string]: NodeJS.Timeout }>({});

  const setLoading = useCallback((key: string, isLoading: boolean, options?: LoadingOptions) => {
    // Clear existing timeout for this key
    if (timeoutsRef.current[key]) {
      clearTimeout(timeoutsRef.current[key]);
      delete timeoutsRef.current[key];
    }

    setLoadingStates(prev => ({
      ...prev,
      [key]: isLoading
    }));

    // Set timeout if loading is true and timeout is specified
    if (isLoading && options?.timeout) {
      timeoutsRef.current[key] = setTimeout(() => {
        setLoadingStates(prev => ({
          ...prev,
          [key]: false
        }));
        options.onTimeout?.();
        delete timeoutsRef.current[key];
      }, options.timeout);
    }
  }, []);

  const isLoading = useCallback((key: string): boolean => {
    return loadingStates[key] || false;
  }, [loadingStates]);

  const isAnyLoading = useCallback((): boolean => {
    return Object.values(loadingStates).some(loading => loading);
  }, [loadingStates]);

  const clearLoading = useCallback((key?: string) => {
    if (key) {
      if (timeoutsRef.current[key]) {
        clearTimeout(timeoutsRef.current[key]);
        delete timeoutsRef.current[key];
      }
      setLoadingStates(prev => {
        const newState = { ...prev };
        delete newState[key];
        return newState;
      });
    } else {
      // Clear all loading states
      Object.keys(timeoutsRef.current).forEach(key => {
        clearTimeout(timeoutsRef.current[key]);
      });
      timeoutsRef.current = {};
      setLoadingStates({});
    }
  }, []);

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      Object.values(timeoutsRef.current).forEach(timeout => {
        clearTimeout(timeout);
      });
    };
  }, []);

  return {
    loadingStates,
    setLoading,
    isLoading,
    isAnyLoading,
    clearLoading
  };
};

// Hook for managing concurrent requests
export const useConcurrentLoading = () => {
  const [activeRequests, setActiveRequests] = useState<Set<string>>(new Set());

  const startRequest = useCallback((requestId: string) => {
    setActiveRequests(prev => new Set(prev).add(requestId));
  }, []);

  const endRequest = useCallback((requestId: string) => {
    setActiveRequests(prev => {
      const newSet = new Set(prev);
      newSet.delete(requestId);
      return newSet;
    });
  }, []);

  const isRequestActive = useCallback((requestId: string): boolean => {
    return activeRequests.has(requestId);
  }, [activeRequests]);

  const hasActiveRequests = useCallback((): boolean => {
    return activeRequests.size > 0;
  }, [activeRequests]);

  const getActiveRequestCount = useCallback((): number => {
    return activeRequests.size;
  }, [activeRequests]);

  return {
    startRequest,
    endRequest,
    isRequestActive,
    hasActiveRequests,
    getActiveRequestCount,
    activeRequests: Array.from(activeRequests)
  };
};

// Hook for progressive loading with priorities
export const useProgressiveLoading = () => {
  const [loadedItems, setLoadedItems] = useState<Set<string>>(new Set());
  const [loadingQueue, setLoadingQueue] = useState<Array<{ id: string; priority: number }>>([]);

  const addToQueue = useCallback((id: string, priority: number = 0) => {
    setLoadingQueue(prev => {
      const filtered = prev.filter(item => item.id !== id);
      const newQueue = [...filtered, { id, priority }];
      return newQueue.sort((a, b) => b.priority - a.priority);
    });
  }, []);

  const markAsLoaded = useCallback((id: string) => {
    setLoadedItems(prev => new Set(prev).add(id));
    setLoadingQueue(prev => prev.filter(item => item.id !== id));
  }, []);

  const isLoaded = useCallback((id: string): boolean => {
    return loadedItems.has(id);
  }, [loadedItems]);

  const getNextToLoad = useCallback((): string | null => {
    return loadingQueue.length > 0 ? loadingQueue[0].id : null;
  }, [loadingQueue]);

  const reset = useCallback(() => {
    setLoadedItems(new Set());
    setLoadingQueue([]);
  }, []);

  return {
    addToQueue,
    markAsLoaded,
    isLoaded,
    getNextToLoad,
    reset,
    loadedItems: Array.from(loadedItems),
    queueLength: loadingQueue.length
  };
};