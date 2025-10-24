import { dataSyncService, SyncConflict } from '../services/dataSyncService';
import api from '../services/api';

// Mock the API
jest.mock('../services/api');
const mockedApi = api as jest.Mocked<typeof api>;

describe('DataSyncService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('syncWithServer', () => {
    it('should sync data successfully with no conflicts', async () => {
      const localCache = new Map();
      localCache.set('test-key', {
        data: { value: 'local' },
        version: 1,
        timestamp: Date.now(),
        expiry: Date.now() + 300000
      });

      const syncQueue = [
        { key: 'queue-key', data: { value: 'queued' }, timestamp: Date.now() }
      ];

      // Mock API responses
      mockedApi.post.mockResolvedValue({ data: { success: true } });
      mockedApi.get.mockResolvedValue({
        data: {
          'test-key': {
            data: { value: 'local' },
            version: 1
          }
        }
      });

      const result = await dataSyncService.syncWithServer(localCache, syncQueue);

      expect(result.success).toBe(true);
      expect(result.conflicts).toHaveLength(0);
      expect(result.synced).toContain('queue-key');
      expect(result.errors).toHaveLength(0);
    });

    it('should handle conflicts with server priority', async () => {
      const localCache = new Map();
      localCache.set('conflict-key', {
        data: { value: 'local' },
        version: 1,
        timestamp: Date.now(),
        expiry: Date.now() + 300000
      });

      const syncQueue: any[] = [];

      // Mock API responses
      mockedApi.get.mockResolvedValue({
        data: {
          'conflict-key': {
            data: { value: 'server' },
            version: 2
          }
        }
      });

      const result = await dataSyncService.syncWithServer(localCache, syncQueue);

      expect(result.conflicts).toHaveLength(1);
      expect(result.conflicts[0].key).toBe('conflict-key');
      expect(result.conflicts[0].serverVersion).toBe(2);
      expect(result.conflicts[0].localVersion).toBe(1);
    });

    it('should handle sync errors gracefully', async () => {
      const localCache = new Map();
      const syncQueue = [
        { key: 'error-key', data: { value: 'error' }, timestamp: Date.now() }
      ];

      // Mock API error
      mockedApi.post.mockRejectedValue(new Error('Network error'));

      const result = await dataSyncService.syncWithServer(localCache, syncQueue);

      expect(result.success).toBe(false);
      expect(result.errors).toHaveLength(1);
      expect(result.errors[0].key).toBe('error-key');
      expect(result.errors[0].error).toContain('Network error');
    });
  });

  describe('conflict resolution', () => {
    it('should use custom conflict resolver', async () => {
      const customResolver = jest.fn().mockResolvedValue({ value: 'resolved' });
      dataSyncService.setConflictResolver(customResolver);

      const localCache = new Map();
      localCache.set('conflict-key', {
        data: { value: 'local' },
        version: 1,
        timestamp: Date.now(),
        expiry: Date.now() + 300000
      });

      const syncQueue: any[] = [];

      mockedApi.get.mockResolvedValue({
        data: {
          'conflict-key': {
            data: { value: 'server' },
            version: 2
          }
        }
      });

      await dataSyncService.syncWithServer(localCache, syncQueue);

      expect(customResolver).toHaveBeenCalledWith({
        key: 'conflict-key',
        localData: { value: 'local' },
        serverData: { value: 'server' },
        localVersion: 1,
        serverVersion: 2
      });
    });
  });

  describe('specific sync methods', () => {
    it('should sync user progress', async () => {
      mockedApi.get.mockResolvedValue({
        data: { progress: 75, completed_lessons: 5 }
      });

      const result = await dataSyncService.syncUserProgress();

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/sync/user-progress');
      expect(result).toEqual({ progress: 75, completed_lessons: 5 });
    });

    it('should sync lesson data', async () => {
      const lessonId = 'lesson-123';
      mockedApi.get.mockResolvedValue({
        data: { id: lessonId, title: 'Test Lesson' }
      });

      const result = await dataSyncService.syncLessonData(lessonId);

      expect(mockedApi.get).toHaveBeenCalledWith(`/api/v1/sync/lesson/${lessonId}`);
      expect(result).toEqual({ id: lessonId, title: 'Test Lesson' });
    });

    it('should sync analytics', async () => {
      mockedApi.get.mockResolvedValue({
        data: { total_time: 3600, sessions: 10 }
      });

      const result = await dataSyncService.syncAnalytics();

      expect(mockedApi.get).toHaveBeenCalledWith('/api/v1/sync/analytics');
      expect(result).toEqual({ total_time: 3600, sessions: 10 });
    });
  });

  describe('batch sync', () => {
    it('should sync multiple keys successfully', async () => {
      mockedApi.get
        .mockResolvedValueOnce({ data: { progress: 50 } })
        .mockResolvedValueOnce({ data: { total_time: 1800 } });

      const result = await dataSyncService.batchSync(['user-progress', 'analytics']);

      expect(result.success).toBe(true);
      expect(result.synced).toEqual(['user-progress', 'analytics']);
      expect(result.errors).toHaveLength(0);
    });

    it('should handle partial failures in batch sync', async () => {
      mockedApi.get
        .mockResolvedValueOnce({ data: { progress: 50 } })
        .mockRejectedValueOnce(new Error('Analytics sync failed'));

      const result = await dataSyncService.batchSync(['user-progress', 'analytics']);

      expect(result.success).toBe(false);
      expect(result.synced).toEqual(['user-progress']);
      expect(result.errors).toHaveLength(1);
      expect(result.errors[0].key).toBe('analytics');
    });
  });

  describe('utility methods', () => {
    it('should determine if sync is needed', () => {
      const now = Date.now();
      const fiveMinutesAgo = now - (5 * 60 * 1000);
      const tenMinutesAgo = now - (10 * 60 * 1000);

      expect(dataSyncService.shouldSync(fiveMinutesAgo)).toBe(false);
      expect(dataSyncService.shouldSync(tenMinutesAgo)).toBe(true);
      expect(dataSyncService.shouldSync(fiveMinutesAgo, 2 * 60 * 1000)).toBe(true);
    });

    it('should track sync progress', () => {
      expect(dataSyncService.isSyncInProgress()).toBe(false);
    });
  });
});