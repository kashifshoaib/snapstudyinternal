import React, { createContext, useContext, useReducer, useCallback, useEffect } from 'react';

// Types for data synchronization
interface CacheEntry<T = any> {
  data: T;
  timestamp: number;
  expiry: number;
  version: number;
}

interface SyncState {
  cache: Map<string, CacheEntry>;
  syncQueue: Array<{ key: string; data: any; timestamp: number }>;
  isOnline: boolean;
  lastSync: number;
}

interface SyncAction {
  type: 'SET_DATA' | 'INVALIDATE' | 'SET_ONLINE' | 'QUEUE_SYNC' | 'CLEAR_QUEUE' | 'CONFLICT_RESOLVE';
  payload?: any;
}

interface DataSyncContextType {
  state: SyncState;
  setData: <T>(key: string, data: T, ttl?: number) => void;
  getData: <T>(key: string) => T | null;
  invalidateData: (key: string) => void;
  queueSync: (key: string, data: any) => void;
  clearSyncQueue: () => void;
  isDataStale: (key: string) => boolean;
  getLastSync: () => number;
}

const DataSyncContext = createContext<DataSyncContextType | undefined>(undefined);

// Default TTL: 5 minutes
const DEFAULT_TTL = 5 * 60 * 1000;

function syncReducer(state: SyncState, action: SyncAction): SyncState {
  switch (action.type) {
    case 'SET_DATA': {
      const { key, data, ttl = DEFAULT_TTL } = action.payload;
      const now = Date.now();
      const newCache = new Map(state.cache);
      
      newCache.set(key, {
        data,
        timestamp: now,
        expiry: now + ttl,
        version: (state.cache.get(key)?.version || 0) + 1
      });

      return {
        ...state,
        cache: newCache,
        lastSync: now
      };
    }

    case 'INVALIDATE': {
      const { key } = action.payload;
      const newCache = new Map(state.cache);
      newCache.delete(key);
      
      return {
        ...state,
        cache: newCache
      };
    }

    case 'SET_ONLINE': {
      return {
        ...state,
        isOnline: action.payload
      };
    }

    case 'QUEUE_SYNC': {
      const { key, data } = action.payload;
      return {
        ...state,
        syncQueue: [
          ...state.syncQueue.filter(item => item.key !== key),
          { key, data, timestamp: Date.now() }
        ]
      };
    }

    case 'CLEAR_QUEUE': {
      return {
        ...state,
        syncQueue: []
      };
    }

    case 'CONFLICT_RESOLVE': {
      const { key, serverData, serverVersion } = action.payload;
      const newCache = new Map(state.cache);
      const existing = newCache.get(key);
      
      // Server priority resolution
      if (!existing || serverVersion > existing.version) {
        newCache.set(key, {
          data: serverData,
          timestamp: Date.now(),
          expiry: Date.now() + DEFAULT_TTL,
          version: serverVersion
        });
      }

      return {
        ...state,
        cache: newCache
      };
    }

    default:
      return state;
  }
}

export function DataSyncProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(syncReducer, {
    cache: new Map(),
    syncQueue: [],
    isOnline: navigator.onLine,
    lastSync: 0
  });

  // Online/offline detection
  useEffect(() => {
    const handleOnline = () => dispatch({ type: 'SET_ONLINE', payload: true });
    const handleOffline = () => dispatch({ type: 'SET_ONLINE', payload: false });

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Cache cleanup interval
  useEffect(() => {
    const cleanup = setInterval(() => {
      const now = Date.now();
      const newCache = new Map(state.cache);
      let hasExpired = false;

      for (const [key, entry] of Array.from(newCache.entries())) {
        if (entry.expiry < now) {
          newCache.delete(key);
          hasExpired = true;
        }
      }

      if (hasExpired) {
        dispatch({ type: 'SET_DATA', payload: { key: '__cleanup__', data: null, ttl: 0 } });
      }
    }, 60000); // Check every minute

    return () => clearInterval(cleanup);
  }, [state.cache]);

  const setData = useCallback(<T,>(key: string, data: T, ttl?: number) => {
    dispatch({
      type: 'SET_DATA',
      payload: { key, data, ttl }
    });
  }, []);

  const getData = useCallback(<T,>(key: string): T | null => {
    const entry = state.cache.get(key);
    if (!entry) return null;
    
    const now = Date.now();
    if (entry.expiry < now) {
      dispatch({ type: 'INVALIDATE', payload: { key } });
      return null;
    }
    
    return entry.data as T;
  }, [state.cache]);

  const invalidateData = useCallback((key: string) => {
    dispatch({ type: 'INVALIDATE', payload: { key } });
  }, []);

  const queueSync = useCallback((key: string, data: any) => {
    dispatch({ type: 'QUEUE_SYNC', payload: { key, data } });
  }, []);

  const clearSyncQueue = useCallback(() => {
    dispatch({ type: 'CLEAR_QUEUE' });
  }, []);

  const isDataStale = useCallback((key: string): boolean => {
    const entry = state.cache.get(key);
    if (!entry) return true;
    
    const now = Date.now();
    const staleThreshold = entry.expiry - (DEFAULT_TTL * 0.2); // 20% before expiry
    return now > staleThreshold;
  }, [state.cache]);

  const getLastSync = useCallback(() => state.lastSync, [state.lastSync]);

  const contextValue: DataSyncContextType = {
    state,
    setData,
    getData,
    invalidateData,
    queueSync,
    clearSyncQueue,
    isDataStale,
    getLastSync
  };

  return (
    <DataSyncContext.Provider value={contextValue}>
      {children}
    </DataSyncContext.Provider>
  );
}

export function useDataSync() {
  const context = useContext(DataSyncContext);
  if (context === undefined) {
    throw new Error('useDataSync must be used within a DataSyncProvider');
  }
  return context;
}