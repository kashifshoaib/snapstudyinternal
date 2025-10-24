import { analyticsService } from './analyticsService';

export interface OfflineAction {
  id: string;
  type: string;
  data: any;
  timestamp: number;
  retryCount: number;
  maxRetries: number;
}

export interface OfflineStorage {
  lessons: Map<string, any>;
  progress: Map<string, any>;
  analytics: Map<string, any>;
  userProfile: any;
  settings: any;
}

class OfflineService {
  private readonly STORAGE_PREFIX = 'snapstudy_offline_';
  private readonly ACTION_QUEUE_KEY = 'action_queue';
  private readonly CRITICAL_DATA_KEY = 'critical_data';
  private readonly MAX_STORAGE_SIZE = 50 * 1024 * 1024; // 50MB
  private isOnline = navigator.onLine;
  private onlineListeners: Array<(isOnline: boolean) => void> = [];

  constructor() {
    this.initializeOfflineDetection();
    this.initializeCriticalDataStorage();
  }

  // Initialize offline/online detection
  private initializeOfflineDetection() {
    const handleOnline = () => {
      this.isOnline = true;
      this.notifyOnlineStatusChange(true);
      this.processPendingActions();
    };

    const handleOffline = () => {
      this.isOnline = false;
      this.notifyOnlineStatusChange(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Additional network detection using fetch
    this.checkNetworkConnectivity();
    setInterval(() => this.checkNetworkConnectivity(), 30000); // Check every 30 seconds
  }

  // More reliable network connectivity check
  private async checkNetworkConnectivity() {
    try {
      const response = await fetch('/favicon.ico', {
        method: 'HEAD',
        cache: 'no-cache'
      });
      const wasOnline = this.isOnline;
      this.isOnline = response.ok;
      
      if (wasOnline !== this.isOnline) {
        this.notifyOnlineStatusChange(this.isOnline);
        if (this.isOnline) {
          this.processPendingActions();
        }
      }
    } catch {
      const wasOnline = this.isOnline;
      this.isOnline = false;
      if (wasOnline) {
        this.notifyOnlineStatusChange(false);
      }
    }
  }

  // Initialize critical data storage
  private initializeCriticalDataStorage() {
    const criticalData = this.getCriticalData();
    if (!criticalData) {
      this.setCriticalData({
        lessons: new Map(),
        progress: new Map(),
        analytics: new Map(),
        userProfile: null,
        settings: {}
      });
    }
  }

  // Online status management
  addOnlineStatusListener(listener: (isOnline: boolean) => void) {
    this.onlineListeners.push(listener);
    return () => {
      this.onlineListeners = this.onlineListeners.filter(l => l !== listener);
    };
  }

  private notifyOnlineStatusChange(isOnline: boolean) {
    this.onlineListeners.forEach(listener => listener(isOnline));
  }

  getOnlineStatus(): boolean {
    return this.isOnline;
  }

  // Action queue management
  queueAction(action: Omit<OfflineAction, 'id' | 'timestamp' | 'retryCount'>): string {
    const actionWithId: OfflineAction = {
      ...action,
      id: this.generateActionId(),
      timestamp: Date.now(),
      retryCount: 0
    };

    const queue = this.getActionQueue();
    queue.push(actionWithId);
    this.setActionQueue(queue);

    // Track offline action
    analyticsService.recordMetric('offline_action_queued', 1, {
      actionType: action.type,
      queueLength: queue.length
    });

    return actionWithId.id;
  }

  private generateActionId(): string {
    return `action_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  getActionQueue(): OfflineAction[] {
    const stored = localStorage.getItem(this.STORAGE_PREFIX + this.ACTION_QUEUE_KEY);
    return stored ? JSON.parse(stored) : [];
  }

  private setActionQueue(queue: OfflineAction[]) {
    localStorage.setItem(
      this.STORAGE_PREFIX + this.ACTION_QUEUE_KEY,
      JSON.stringify(queue)
    );
  }

  clearActionQueue() {
    localStorage.removeItem(this.STORAGE_PREFIX + this.ACTION_QUEUE_KEY);
  }

  removeActionFromQueue(actionId: string) {
    const queue = this.getActionQueue();
    const filteredQueue = queue.filter(action => action.id !== actionId);
    this.setActionQueue(filteredQueue);
  }

  // Process pending actions when coming online
  async processPendingActions(): Promise<void> {
    if (!this.isOnline) return;

    const queue = this.getActionQueue();
    if (queue.length === 0) return;

    console.log(`Processing ${queue.length} offline actions`);

    const processedActions: string[] = [];
    const failedActions: OfflineAction[] = [];

    for (const action of queue) {
      try {
        await this.executeAction(action);
        processedActions.push(action.id);
        
        analyticsService.recordMetric('offline_action_processed', 1, {
          actionType: action.type,
          retryCount: action.retryCount
        });
      } catch (error) {
        console.error(`Failed to process action ${action.id}:`, error);
        
        action.retryCount++;
        if (action.retryCount < action.maxRetries) {
          failedActions.push(action);
        } else {
          console.error(`Action ${action.id} exceeded max retries, discarding`);
          analyticsService.recordMetric('offline_action_failed', 1, {
            actionType: action.type,
            retryCount: action.retryCount
          });
        }
      }
    }

    // Update queue with only failed actions that haven't exceeded retries
    this.setActionQueue(failedActions);

    if (processedActions.length > 0) {
      console.log(`Successfully processed ${processedActions.length} offline actions`);
    }
  }

  private async executeAction(action: OfflineAction): Promise<void> {
    // This would be implemented based on action types
    switch (action.type) {
      case 'lesson_progress':
        await this.syncLessonProgress(action.data);
        break;
      case 'quiz_completion':
        await this.syncQuizCompletion(action.data);
        break;
      case 'analytics_event':
        await this.syncAnalyticsEvent(action.data);
        break;
      case 'profile_update':
        await this.syncProfileUpdate(action.data);
        break;
      default:
        throw new Error(`Unknown action type: ${action.type}`);
    }
  }

  // Critical data storage
  getCriticalData(): OfflineStorage | null {
    const stored = localStorage.getItem(this.STORAGE_PREFIX + this.CRITICAL_DATA_KEY);
    return stored ? JSON.parse(stored) : null;
  }

  setCriticalData(data: OfflineStorage) {
    // Check storage size
    const serialized = JSON.stringify(data);
    if (serialized.length > this.MAX_STORAGE_SIZE) {
      console.warn('Critical data exceeds max storage size, cleaning up...');
      this.cleanupOldData(data);
    }

    localStorage.setItem(this.STORAGE_PREFIX + this.CRITICAL_DATA_KEY, serialized);
  }

  // Store lesson data for offline access
  storeLessonOffline(lessonId: string, lessonData: any) {
    const criticalData = this.getCriticalData() || this.getEmptyStorage();
    criticalData.lessons.set(lessonId, {
      ...lessonData,
      cachedAt: Date.now()
    });
    this.setCriticalData(criticalData);
  }

  getLessonOffline(lessonId: string): any | null {
    const criticalData = this.getCriticalData();
    return criticalData?.lessons.get(lessonId) || null;
  }

  // Store progress data for offline access
  storeProgressOffline(progressData: any, lessonId?: string) {
    const criticalData = this.getCriticalData() || this.getEmptyStorage();
    const key = lessonId || 'overall';
    criticalData.progress.set(key, {
      ...progressData,
      cachedAt: Date.now()
    });
    this.setCriticalData(criticalData);
  }

  getProgressOffline(lessonId?: string): any | null {
    const criticalData = this.getCriticalData();
    const key = lessonId || 'overall';
    return criticalData?.progress.get(key) || null;
  }

  // Store analytics data for offline access
  storeAnalyticsOffline(analyticsData: any, type: string) {
    const criticalData = this.getCriticalData() || this.getEmptyStorage();
    criticalData.analytics.set(type, {
      ...analyticsData,
      cachedAt: Date.now()
    });
    this.setCriticalData(criticalData);
  }

  getAnalyticsOffline(type: string): any | null {
    const criticalData = this.getCriticalData();
    return criticalData?.analytics.get(type) || null;
  }

  // Cleanup old data to manage storage size
  private cleanupOldData(data: OfflineStorage) {
    const now = Date.now();
    const maxAge = 7 * 24 * 60 * 60 * 1000; // 7 days

    // Clean up old lessons
    for (const [lessonId, lesson] of Array.from(data.lessons.entries())) {
      if (lesson.cachedAt && now - lesson.cachedAt > maxAge) {
        data.lessons.delete(lessonId);
      }
    }

    // Clean up old analytics
    for (const [type, analytics] of Array.from(data.analytics.entries())) {
      if (analytics.cachedAt && now - analytics.cachedAt > maxAge) {
        data.analytics.delete(type);
      }
    }
  }

  private getEmptyStorage(): OfflineStorage {
    return {
      lessons: new Map(),
      progress: new Map(),
      analytics: new Map(),
      userProfile: null,
      settings: {}
    };
  }

  // Sync methods (to be called when processing actions)
  private async syncLessonProgress(data: any): Promise<void> {
    // Implementation would call actual API
    console.log('Syncing lesson progress:', data);
  }

  private async syncQuizCompletion(data: any): Promise<void> {
    // Implementation would call actual API
    console.log('Syncing quiz completion:', data);
  }

  private async syncAnalyticsEvent(data: any): Promise<void> {
    // Implementation would call actual API
    console.log('Syncing analytics event:', data);
  }

  private async syncProfileUpdate(data: any): Promise<void> {
    // Implementation would call actual API
    console.log('Syncing profile update:', data);
  }

  // Storage management
  getStorageUsage(): { used: number; available: number; percentage: number } {
    let used = 0;
    for (let key in localStorage) {
      if (key.startsWith(this.STORAGE_PREFIX)) {
        used += localStorage[key].length;
      }
    }

    const available = this.MAX_STORAGE_SIZE - used;
    const percentage = (used / this.MAX_STORAGE_SIZE) * 100;

    return { used, available, percentage };
  }

  clearOfflineData() {
    const keys = Object.keys(localStorage).filter(key => 
      key.startsWith(this.STORAGE_PREFIX)
    );
    keys.forEach(key => localStorage.removeItem(key));
  }
}

export const offlineService = new OfflineService();