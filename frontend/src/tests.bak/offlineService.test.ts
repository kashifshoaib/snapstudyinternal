import { offlineService, OfflineAction } from '../services/offlineService';

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock navigator.onLine
Object.defineProperty(navigator, 'onLine', {
  writable: true,
  value: true,
});

// Mock fetch for connectivity checks
global.fetch = jest.fn();

describe('OfflineService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(null);
    (navigator as any).onLine = true;
    (global.fetch as jest.Mock).mockResolvedValue({ ok: true });
  });

  describe('online status detection', () => {
    it('should detect initial online status', () => {
      expect(offlineService.getOnlineStatus()).toBe(true);
    });

    it('should notify listeners of status changes', (done) => {
      const listener = jest.fn((isOnline) => {
        expect(isOnline).toBe(false);
        done();
      });

      offlineService.addOnlineStatusListener(listener);

      // Simulate going offline
      (navigator as any).onLine = false;
      window.dispatchEvent(new Event('offline'));
    });

    it('should remove listeners correctly', () => {
      const listener = jest.fn();
      const removeListener = offlineService.addOnlineStatusListener(listener);

      removeListener();

      // Simulate status change
      window.dispatchEvent(new Event('offline'));

      expect(listener).not.toHaveBeenCalled();
    });
  });

  describe('action queue management', () => {
    it('should queue actions when offline', () => {
      const actionId = offlineService.queueAction({
        type: 'lesson_progress',
        data: { lessonId: '123', progress: 50 },
        maxRetries: 3
      });

      expect(actionId).toBeDefined();
      expect(typeof actionId).toBe('string');
      expect(localStorageMock.setItem).toHaveBeenCalled();
    });

    it('should retrieve action queue', () => {
      const mockQueue = [
        {
          id: 'action_1',
          type: 'lesson_progress',
          data: { lessonId: '123' },
          timestamp: Date.now(),
          retryCount: 0,
          maxRetries: 3
        }
      ];

      localStorageMock.getItem.mockReturnValue(JSON.stringify(mockQueue));

      const queue = offlineService.getActionQueue();

      expect(queue).toEqual(mockQueue);
      expect(localStorageMock.getItem).toHaveBeenCalledWith('snapstudy_offline_action_queue');
    });

    it('should remove actions from queue', () => {
      const mockQueue = [
        {
          id: 'action_1',
          type: 'lesson_progress',
          data: { lessonId: '123' },
          timestamp: Date.now(),
          retryCount: 0,
          maxRetries: 3
        },
        {
          id: 'action_2',
          type: 'quiz_completion',
          data: { quizId: '456' },
          timestamp: Date.now(),
          retryCount: 0,
          maxRetries: 3
        }
      ];

      localStorageMock.getItem.mockReturnValue(JSON.stringify(mockQueue));

      offlineService.removeActionFromQueue('action_1');

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'snapstudy_offline_action_queue',
        JSON.stringify([mockQueue[1]])
      );
    });

    it('should clear action queue', () => {
      offlineService.clearActionQueue();

      expect(localStorageMock.removeItem).toHaveBeenCalledWith('snapstudy_offline_action_queue');
    });
  });

  describe('critical data storage', () => {
    it('should store lesson data offline', () => {
      const lessonData = { id: '123', title: 'Test Lesson', content: 'Content' };

      offlineService.storeLessonOffline('123', lessonData);

      expect(localStorageMock.setItem).toHaveBeenCalled();
    });

    it('should retrieve lesson data offline', () => {
      const mockCriticalData = {
        lessons: {
          '123': { id: '123', title: 'Test Lesson', cachedAt: Date.now() }
        },
        progress: {},
        analytics: {},
        userProfile: null,
        settings: {}
      };

      localStorageMock.getItem.mockReturnValue(JSON.stringify(mockCriticalData));

      const lessonData = offlineService.getLessonOffline('123');

      expect(lessonData).toEqual(mockCriticalData.lessons['123']);
    });

    it('should store progress data offline', () => {
      const progressData = { completed: 75, timeSpent: 3600 };

      offlineService.storeProgressOffline(progressData, '123');

      expect(localStorageMock.setItem).toHaveBeenCalled();
    });

    it('should retrieve progress data offline', () => {
      const mockCriticalData = {
        lessons: {},
        progress: {
          '123': { completed: 75, timeSpent: 3600, cachedAt: Date.now() }
        },
        analytics: {},
        userProfile: null,
        settings: {}
      };

      localStorageMock.getItem.mockReturnValue(JSON.stringify(mockCriticalData));

      const progressData = offlineService.getProgressOffline('123');

      expect(progressData).toEqual(mockCriticalData.progress['123']);
    });

    it('should store analytics data offline', () => {
      const analyticsData = { totalTime: 7200, sessionsCount: 15 };

      offlineService.storeAnalyticsOffline(analyticsData, 'dashboard');

      expect(localStorageMock.setItem).toHaveBeenCalled();
    });

    it('should retrieve analytics data offline', () => {
      const mockCriticalData = {
        lessons: {},
        progress: {},
        analytics: {
          'dashboard': { totalTime: 7200, sessionsCount: 15, cachedAt: Date.now() }
        },
        userProfile: null,
        settings: {}
      };

      localStorageMock.getItem.mockReturnValue(JSON.stringify(mockCriticalData));

      const analyticsData = offlineService.getAnalyticsOffline('dashboard');

      expect(analyticsData).toEqual(mockCriticalData.analytics['dashboard']);
    });
  });

  describe('storage management', () => {
    it('should calculate storage usage', () => {
      localStorageMock.getItem.mockImplementation((key) => {
        if (key.startsWith('snapstudy_offline_')) {
          return 'x'.repeat(1000); // 1KB of data
        }
        return null;
      });

      // Mock localStorage keys
      Object.defineProperty(localStorage, 'length', { value: 2 });
      Object.defineProperty(localStorage, 'key', {
        value: (index: number) => {
          const keys = ['snapstudy_offline_critical_data', 'snapstudy_offline_action_queue'];
          return keys[index];
        }
      });

      const usage = offlineService.getStorageUsage();

      expect(usage.used).toBeGreaterThan(0);
      expect(usage.available).toBeGreaterThan(0);
      expect(usage.percentage).toBeGreaterThan(0);
    });

    it('should clear offline data', () => {
      // Mock localStorage keys
      Object.defineProperty(localStorage, 'length', { value: 3 });
      Object.defineProperty(localStorage, 'key', {
        value: (index: number) => {
          const keys = ['snapstudy_offline_critical_data', 'other_key', 'snapstudy_offline_action_queue'];
          return keys[index];
        }
      });

      offlineService.clearOfflineData();

      expect(localStorageMock.removeItem).toHaveBeenCalledWith('snapstudy_offline_critical_data');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('snapstudy_offline_action_queue');
      expect(localStorageMock.removeItem).not.toHaveBeenCalledWith('other_key');
    });
  });

  describe('network connectivity checks', () => {
    it('should handle fetch errors gracefully', async () => {
      (global.fetch as jest.Mock).mockRejectedValue(new Error('Network error'));

      // Wait for connectivity check
      await new Promise(resolve => setTimeout(resolve, 100));

      expect(offlineService.getOnlineStatus()).toBe(false);
    });

    it('should update status based on fetch response', async () => {
      (global.fetch as jest.Mock).mockResolvedValue({ ok: false });

      // Wait for connectivity check
      await new Promise(resolve => setTimeout(resolve, 100));

      expect(offlineService.getOnlineStatus()).toBe(false);
    });
  });
});