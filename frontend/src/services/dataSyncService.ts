import api from './api';

export interface SyncConflict {
  key: string;
  localData: any;
  serverData: any;
  localVersion: number;
  serverVersion: number;
}

export interface SyncResult {
  success: boolean;
  conflicts: SyncConflict[];
  synced: string[];
  errors: Array<{ key: string; error: string }>;
}

class DataSyncService {
  private syncInProgress = false;
  private conflictResolver: (conflict: SyncConflict) => Promise<any> = this.defaultConflictResolver;

  // Set custom conflict resolver
  setConflictResolver(resolver: (conflict: SyncConflict) => Promise<any>) {
    this.conflictResolver = resolver;
  }

  // Default conflict resolver - server wins
  private async defaultConflictResolver(conflict: SyncConflict): Promise<any> {
    console.warn(`Data conflict for ${conflict.key}, using server data`, conflict);
    return conflict.serverData;
  }

  // Sync data with server
  async syncWithServer(
    localCache: Map<string, any>,
    syncQueue: Array<{ key: string; data: any; timestamp: number }>
  ): Promise<SyncResult> {
    if (this.syncInProgress) {
      throw new Error('Sync already in progress');
    }

    this.syncInProgress = true;
    const result: SyncResult = {
      success: true,
      conflicts: [],
      synced: [],
      errors: []
    };

    try {
      // First, push queued changes to server
      for (const queueItem of syncQueue) {
        try {
          await this.pushToServer(queueItem.key, queueItem.data);
          result.synced.push(queueItem.key);
        } catch (error) {
          result.errors.push({
            key: queueItem.key,
            error: error instanceof Error ? error.message : 'Unknown error'
          });
          result.success = false;
        }
      }

      // Then, pull latest data from server
      const serverData = await this.pullFromServer();
      
      // Check for conflicts
      for (const [key, serverEntry] of Object.entries(serverData)) {
        const localEntry = localCache.get(key);
        
        if (localEntry && localEntry.version !== serverEntry.version) {
          const conflict: SyncConflict = {
            key,
            localData: localEntry.data,
            serverData: serverEntry.data,
            localVersion: localEntry.version,
            serverVersion: serverEntry.version
          };
          
          result.conflicts.push(conflict);
        }
      }

      // Resolve conflicts
      for (const conflict of result.conflicts) {
        try {
          const resolvedData = await this.conflictResolver(conflict);
          // Update local cache with resolved data
          localCache.set(conflict.key, {
            data: resolvedData,
            timestamp: Date.now(),
            expiry: Date.now() + (5 * 60 * 1000), // 5 minutes
            version: Math.max(conflict.localVersion, conflict.serverVersion) + 1
          });
        } catch (error) {
          result.errors.push({
            key: conflict.key,
            error: `Conflict resolution failed: ${error instanceof Error ? error.message : 'Unknown error'}`
          });
          result.success = false;
        }
      }

    } catch (error) {
      result.success = false;
      result.errors.push({
        key: 'sync',
        error: error instanceof Error ? error.message : 'Sync failed'
      });
    } finally {
      this.syncInProgress = false;
    }

    return result;
  }

  // Push data to server
  private async pushToServer(key: string, data: any): Promise<void> {
    try {
      await api.post('/api/v1/sync/push', {
        key,
        data,
        timestamp: Date.now()
      });
    } catch (error) {
      throw new Error(`Failed to push ${key} to server: ${error}`);
    }
  }

  // Pull data from server
  private async pullFromServer(): Promise<Record<string, any>> {
    try {
      const response = await api.get('/api/v1/sync/pull');
      return response.data || {};
    } catch (error) {
      throw new Error(`Failed to pull data from server: ${error}`);
    }
  }

  // Sync specific data types
  async syncUserProgress(): Promise<void> {
    try {
      const response = await api.get('/api/v1/sync/user-progress');
      return response.data;
    } catch (error) {
      console.error('Failed to sync user progress:', error);
      throw error;
    }
  }

  async syncLessonData(lessonId: string): Promise<void> {
    try {
      const response = await api.get(`/api/v1/sync/lesson/${lessonId}`);
      return response.data;
    } catch (error) {
      console.error(`Failed to sync lesson ${lessonId}:`, error);
      throw error;
    }
  }

  async syncAnalytics(): Promise<void> {
    try {
      const response = await api.get('/api/v1/sync/analytics');
      return response.data;
    } catch (error) {
      console.error('Failed to sync analytics:', error);
      throw error;
    }
  }

  // Batch sync multiple keys
  async batchSync(keys: string[]): Promise<SyncResult> {
    const result: SyncResult = {
      success: true,
      conflicts: [],
      synced: [],
      errors: []
    };

    for (const key of keys) {
      try {
        await this.syncSpecificKey(key);
        result.synced.push(key);
      } catch (error) {
        result.errors.push({
          key,
          error: error instanceof Error ? error.message : 'Unknown error'
        });
        result.success = false;
      }
    }

    return result;
  }

  private async syncSpecificKey(key: string): Promise<void> {
    // Implementation depends on key type
    switch (key) {
      case 'user-progress':
        await this.syncUserProgress();
        break;
      case 'analytics':
        await this.syncAnalytics();
        break;
      default:
        if (key.startsWith('lesson-')) {
          const lessonId = key.replace('lesson-', '');
          await this.syncLessonData(lessonId);
        } else {
          throw new Error(`Unknown sync key: ${key}`);
        }
    }
  }

  // Check if sync is needed
  shouldSync(lastSyncTime: number, threshold: number = 5 * 60 * 1000): boolean {
    return Date.now() - lastSyncTime > threshold;
  }

  // Get sync status
  isSyncInProgress(): boolean {
    return this.syncInProgress;
  }
}

export const dataSyncService = new DataSyncService();