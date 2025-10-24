/**
 * Loading state manager for authentication system.
 * 
 * This module provides centralized loading state management with
 * user feedback for all authentication operations.
 */

import { useState, useCallback, useRef, useEffect } from 'react';

export interface LoadingState {
  isLoading: boolean;
  operation: string | null;
  progress?: number;
  message?: string;
  error?: string;
}

export interface LoadingOptions {
  operation: string;
  message?: string;
  timeout?: number;
  showProgress?: boolean;
}

export interface NotificationOptions {
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  duration?: number;
  persistent?: boolean;
  actions?: Array<{
    label: string;
    action: () => void;
    primary?: boolean;
  }>;
}

// Global loading state manager
class LoadingStateManager {
  private listeners: Set<(state: LoadingState) => void> = new Set();
  private currentState: LoadingState = {
    isLoading: false,
    operation: null
  };
  private timeoutId: NodeJS.Timeout | null = null;

  subscribe(listener: (state: LoadingState) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  getState(): LoadingState {
    return { ...this.currentState };
  }

  startLoading(options: LoadingOptions): void {
    // Clear any existing timeout
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }

    this.currentState = {
      isLoading: true,
      operation: options.operation,
      message: options.message,
      progress: options.showProgress ? 0 : undefined,
      error: undefined
    };

    this.notifyListeners();

    // Set timeout if specified
    if (options.timeout) {
      this.timeoutId = setTimeout(() => {
        this.setError(`Operation "${options.operation}" timed out. Please try again.`);
      }, options.timeout);
    }
  }

  updateProgress(progress: number, message?: string): void {
    if (this.currentState.isLoading) {
      this.currentState = {
        ...this.currentState,
        progress: Math.max(0, Math.min(100, progress)),
        message: message || this.currentState.message
      };
      this.notifyListeners();
    }
  }

  setError(error: string): void {
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }

    this.currentState = {
      ...this.currentState,
      isLoading: false,
      error
    };
    this.notifyListeners();
  }

  stopLoading(): void {
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }

    this.currentState = {
      isLoading: false,
      operation: null,
      progress: undefined,
      message: undefined,
      error: undefined
    };
    this.notifyListeners();
  }

  private notifyListeners(): void {
    this.listeners.forEach(listener => listener(this.currentState));
  }
}

// Global notification manager
class NotificationManager {
  private listeners: Set<(notification: NotificationOptions & { id: string }) => void> = new Set();
  private notificationId = 0;

  subscribe(listener: (notification: NotificationOptions & { id: string }) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  show(options: NotificationOptions): string {
    const id = `notification-${++this.notificationId}`;
    const notification = { ...options, id };
    
    this.listeners.forEach(listener => listener(notification));
    
    // Auto-dismiss non-persistent notifications
    if (!options.persistent) {
      setTimeout(() => {
        this.dismiss(id);
      }, options.duration || 5000);
    }
    
    return id;
  }

  success(title: string, message: string, duration?: number): string {
    return this.show({
      type: 'success',
      title,
      message,
      duration
    });
  }

  error(title: string, message: string, persistent = false): string {
    return this.show({
      type: 'error',
      title,
      message,
      persistent,
      duration: persistent ? undefined : 8000
    });
  }

  warning(title: string, message: string, duration?: number): string {
    return this.show({
      type: 'warning',
      title,
      message,
      duration
    });
  }

  info(title: string, message: string, duration?: number): string {
    return this.show({
      type: 'info',
      title,
      message,
      duration
    });
  }

  dismiss(id: string): void {
    // Implementation would depend on the UI framework
    // This is a placeholder for the dismiss functionality
  }
}

// Global instances
export const loadingManager = new LoadingStateManager();
export const notificationManager = new NotificationManager();

// React hooks for using the managers
export function useLoadingState(): [LoadingState, {
  startLoading: (options: LoadingOptions) => void;
  updateProgress: (progress: number, message?: string) => void;
  setError: (error: string) => void;
  stopLoading: () => void;
}] {
  const [state, setState] = useState<LoadingState>(loadingManager.getState());

  useEffect(() => {
    const unsubscribe = loadingManager.subscribe(setState);
    return unsubscribe;
  }, []);

  const actions = {
    startLoading: useCallback((options: LoadingOptions) => {
      loadingManager.startLoading(options);
    }, []),
    updateProgress: useCallback((progress: number, message?: string) => {
      loadingManager.updateProgress(progress, message);
    }, []),
    setError: useCallback((error: string) => {
      loadingManager.setError(error);
    }, []),
    stopLoading: useCallback(() => {
      loadingManager.stopLoading();
    }, [])
  };

  return [state, actions];
}

export function useNotifications(): {
  show: (options: NotificationOptions) => string;
  success: (title: string, message: string, duration?: number) => string;
  error: (title: string, message: string, persistent?: boolean) => string;
  warning: (title: string, message: string, duration?: number) => string;
  info: (title: string, message: string, duration?: number) => string;
  dismiss: (id: string) => void;
} {
  return {
    show: useCallback((options: NotificationOptions) => {
      return notificationManager.show(options);
    }, []),
    success: useCallback((title: string, message: string, duration?: number) => {
      return notificationManager.success(title, message, duration);
    }, []),
    error: useCallback((title: string, message: string, persistent = false) => {
      return notificationManager.error(title, message, persistent);
    }, []),
    warning: useCallback((title: string, message: string, duration?: number) => {
      return notificationManager.warning(title, message, duration);
    }, []),
    info: useCallback((title: string, message: string, duration?: number) => {
      return notificationManager.info(title, message, duration);
    }, []),
    dismiss: useCallback((id: string) => {
      notificationManager.dismiss(id);
    }, [])
  };
}

// Higher-order component for automatic loading management
export function withLoadingState<T extends object>(
  Component: React.ComponentType<T>,
  defaultOperation: string
): React.ComponentType<T> {
  return function LoadingStateWrapper(props: T) {
    const [loadingState, loadingActions] = useLoadingState();
    
    const enhancedProps = {
      ...props,
      loadingState,
      loadingActions: {
        ...loadingActions,
        startLoading: (options?: Partial<LoadingOptions>) => {
          loadingActions.startLoading({
            operation: defaultOperation,
            ...options
          });
        }
      }
    } as T & {
      loadingState: LoadingState;
      loadingActions: typeof loadingActions & {
        startLoading: (options?: Partial<LoadingOptions>) => void;
      };
    };

    return <Component {...enhancedProps} />;
  };
}

// Utility functions for common loading scenarios
export const AuthLoadingOperations = {
  LOGIN: 'Logging in...',
  REGISTER: 'Creating account...',
  LOGOUT: 'Logging out...',
  VERIFY_TOKEN: 'Verifying session...',
  UPDATE_PROFILE: 'Updating profile...',
  COMPLETE_ONBOARDING: 'Completing setup...',
  UPLOAD_LESSON: 'Uploading lesson...',
  LOAD_LESSONS: 'Loading lessons...',
  LOAD_ANALYTICS: 'Loading analytics...'
} as const;

export function createAuthLoadingOptions(
  operation: keyof typeof AuthLoadingOperations,
  options?: Partial<LoadingOptions>
): LoadingOptions {
  return {
    operation: AuthLoadingOperations[operation],
    timeout: 30000, // 30 second default timeout
    ...options
  };
}

// Network error handling utilities
export function handleNetworkError(error: any): string {
  if (!navigator.onLine) {
    return 'You appear to be offline. Please check your internet connection and try again.';
  }
  
  if (error.code === 'NETWORK_ERROR' || error.message?.includes('fetch')) {
    return 'Network error occurred. Please check your connection and try again.';
  }
  
  if (error.code === 'TIMEOUT_ERROR') {
    return 'The request timed out. Please try again.';
  }
  
  return 'A network error occurred. Please try again.';
}

// Graceful degradation utilities
export function createOfflineMessage(feature: string): NotificationOptions {
  return {
    type: 'warning',
    title: 'Offline Mode',
    message: `${feature} is not available while offline. Your changes will be saved when you reconnect.`,
    persistent: true,
    actions: [
      {
        label: 'Retry',
        action: () => window.location.reload(),
        primary: true
      }
    ]
  };
}

export function createMaintenanceMessage(): NotificationOptions {
  return {
    type: 'info',
    title: 'Maintenance Mode',
    message: 'The system is currently undergoing maintenance. Some features may be temporarily unavailable.',
    persistent: true
  };
}

// Performance monitoring integration
export function trackLoadingPerformance(operation: string, startTime: number): void {
  const duration = Date.now() - startTime;
  
  // Track slow operations
  if (duration > 5000) {
    console.warn(`Slow operation detected: ${operation} took ${duration}ms`);
  }
  
  // You could integrate with analytics services here
  if (typeof window !== 'undefined' && (window as any).gtag) {
    (window as any).gtag('event', 'timing_complete', {
      name: operation,
      value: duration
    });
  }
}