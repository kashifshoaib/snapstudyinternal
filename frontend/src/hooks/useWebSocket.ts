import { useState, useEffect, useCallback, useRef } from 'react';
import { 
  websocketService, 
  progressWebSocketService, 
  analyticsWebSocketService,
  lessonWebSocketService 
} from '../services/websocketService';

export interface WebSocketState {
  isConnected: boolean;
  connectionState: string;
  reconnectAttempts: number;
  subscriptionCount: number;
}

// Main WebSocket hook
export function useWebSocket() {
  const [state, setState] = useState<WebSocketState>({
    isConnected: websocketService.isConnected(),
    connectionState: websocketService.getConnectionState(),
    reconnectAttempts: websocketService.getReconnectAttempts(),
    subscriptionCount: websocketService.getSubscriptionCount()
  });

  useEffect(() => {
    // Update state when connection changes
    const unsubscribe = websocketService.addConnectionListener((connected) => {
      setState({
        isConnected: connected,
        connectionState: websocketService.getConnectionState(),
        reconnectAttempts: websocketService.getReconnectAttempts(),
        subscriptionCount: websocketService.getSubscriptionCount()
      });
    });

    // Initial connection attempt
    websocketService.connect().catch(error => {
      console.error('Failed to connect WebSocket:', error);
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const connect = useCallback(() => {
    return websocketService.connect();
  }, []);

  const disconnect = useCallback(() => {
    websocketService.disconnect();
  }, []);

  const subscribe = useCallback((type: string, callback: (data: any) => void) => {
    return websocketService.subscribe(type, callback);
  }, []);

  const unsubscribe = useCallback((subscriptionId: string) => {
    websocketService.unsubscribe(subscriptionId);
  }, []);

  const send = useCallback((type: string, data: any) => {
    websocketService.send({ type, data });
  }, []);

  return {
    ...state,
    connect,
    disconnect,
    subscribe,
    unsubscribe,
    send
  };
}

// Hook for progress synchronization
export function useProgressSync() {
  const [progressData, setProgressData] = useState<any>(null);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const unsubscribeRef = useRef<(() => void) | null>(null);

  const subscribe = useCallback(() => {
    if (isSubscribed) return;

    const unsubscribe = progressWebSocketService.subscribe((data) => {
      setProgressData(data);
    });

    unsubscribeRef.current = unsubscribe;
    setIsSubscribed(true);
  }, [isSubscribed]);

  const unsubscribe = useCallback(() => {
    if (unsubscribeRef.current) {
      unsubscribeRef.current();
      unsubscribeRef.current = null;
      setIsSubscribed(false);
    }
  }, []);

  const updateProgress = useCallback((lessonId: string, progress: any) => {
    progressWebSocketService.updateProgress(lessonId, progress);
  }, []);

  useEffect(() => {
    // Auto-subscribe on mount
    subscribe();

    return () => {
      unsubscribe();
    };
  }, [subscribe, unsubscribe]);

  return {
    progressData,
    isSubscribed,
    subscribe,
    unsubscribe,
    updateProgress
  };
}

// Hook for analytics real-time updates
export function useAnalyticsSync() {
  const [analyticsData, setAnalyticsData] = useState<any>(null);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const unsubscribeRef = useRef<(() => void) | null>(null);

  const subscribe = useCallback(() => {
    if (isSubscribed) return;

    const unsubscribe = analyticsWebSocketService.subscribe((data) => {
      setAnalyticsData(data);
    });

    unsubscribeRef.current = unsubscribe;
    setIsSubscribed(true);
  }, [isSubscribed]);

  const unsubscribe = useCallback(() => {
    if (unsubscribeRef.current) {
      unsubscribeRef.current();
      unsubscribeRef.current = null;
      setIsSubscribed(false);
    }
  }, []);

  const sendEvent = useCallback((eventType: string, eventData: any) => {
    analyticsWebSocketService.sendEvent(eventType, eventData);
  }, []);

  useEffect(() => {
    // Auto-subscribe on mount
    subscribe();

    return () => {
      unsubscribe();
    };
  }, [subscribe, unsubscribe]);

  return {
    analyticsData,
    isSubscribed,
    subscribe,
    unsubscribe,
    sendEvent
  };
}

// Hook for lesson updates
export function useLessonSync() {
  const [lessonData, setLessonData] = useState<any>(null);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const unsubscribeRef = useRef<(() => void) | null>(null);

  const subscribe = useCallback(() => {
    if (isSubscribed) return;

    const unsubscribe = lessonWebSocketService.subscribe((data) => {
      setLessonData(data);
    });

    unsubscribeRef.current = unsubscribe;
    setIsSubscribed(true);
  }, [isSubscribed]);

  const unsubscribe = useCallback(() => {
    if (unsubscribeRef.current) {
      unsubscribeRef.current();
      unsubscribeRef.current = null;
      setIsSubscribed(false);
    }
  }, []);

  const requestUpdate = useCallback((lessonId: string) => {
    lessonWebSocketService.requestLessonUpdate(lessonId);
  }, []);

  useEffect(() => {
    // Auto-subscribe on mount
    subscribe();

    return () => {
      unsubscribe();
    };
  }, [subscribe, unsubscribe]);

  return {
    lessonData,
    isSubscribed,
    subscribe,
    unsubscribe,
    requestUpdate
  };
}

// Hook for custom WebSocket subscriptions
export function useWebSocketSubscription<T>(
  messageType: string,
  callback: (data: T) => void,
  dependencies: any[] = []
) {
  const [data, setData] = useState<T | null>(null);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const subscriptionIdRef = useRef<string | null>(null);
  const callbackRef = useRef(callback);

  // Update callback ref when callback changes
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  // Subscribe/unsubscribe effect
  useEffect(() => {
    const wrappedCallback = (receivedData: T) => {
      setData(receivedData);
      callbackRef.current(receivedData);
    };

    subscriptionIdRef.current = websocketService.subscribe(messageType, wrappedCallback);
    setIsSubscribed(true);

    return () => {
      if (subscriptionIdRef.current) {
        websocketService.unsubscribe(subscriptionIdRef.current);
        subscriptionIdRef.current = null;
        setIsSubscribed(false);
      }
    };
  }, [messageType, ...dependencies]);

  const send = useCallback((data: any) => {
    websocketService.send({ type: messageType, data });
  }, [messageType]);

  return {
    data,
    isSubscribed,
    send
  };
}

// Hook for WebSocket connection status with auto-reconnect
export function useWebSocketConnection(autoConnect = true) {
  const { isConnected, connectionState, reconnectAttempts } = useWebSocket();
  const [lastConnectedAt, setLastConnectedAt] = useState<Date | null>(null);
  const [lastDisconnectedAt, setLastDisconnectedAt] = useState<Date | null>(null);

  useEffect(() => {
    if (isConnected) {
      setLastConnectedAt(new Date());
    } else {
      setLastDisconnectedAt(new Date());
    }
  }, [isConnected]);

  useEffect(() => {
    if (autoConnect && !isConnected && connectionState === 'DISCONNECTED') {
      websocketService.connect().catch(error => {
        console.error('Auto-connect failed:', error);
      });
    }
  }, [autoConnect, isConnected, connectionState]);

  const manualConnect = useCallback(() => {
    return websocketService.connect();
  }, []);

  const manualDisconnect = useCallback(() => {
    websocketService.disconnect();
  }, []);

  return {
    isConnected,
    connectionState,
    reconnectAttempts,
    lastConnectedAt,
    lastDisconnectedAt,
    connect: manualConnect,
    disconnect: manualDisconnect
  };
}