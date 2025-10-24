import { config } from '../config';
import { analyticsService } from './analyticsService';

export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp?: number;
  session_id?: string;
  user_id?: string;
}

export interface WebSocketSubscription {
  id: string;
  type: string;
  callback: (data: any) => void;
}

export interface ConnectionOptions {
  autoReconnect?: boolean;
  maxReconnectAttempts?: number;
  reconnectDelay?: number;
  heartbeatInterval?: number;
}

class WebSocketService {
  private ws: WebSocket | null = null;
  private subscriptions: Map<string, WebSocketSubscription[]> = new Map();
  private connectionPromise: Promise<void> | null = null;
  private reconnectAttempts = 0;
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private connectionListeners: Array<(connected: boolean) => void> = [];
  
  private options: Required<ConnectionOptions> = {
    autoReconnect: true,
    maxReconnectAttempts: 5,
    reconnectDelay: 1000,
    heartbeatInterval: 30000 // 30 seconds
  };

  constructor(options: ConnectionOptions = {}) {
    this.options = { ...this.options, ...options };
  }

  // Connection management
  async connect(): Promise<void> {
    if (this.connectionPromise) {
      return this.connectionPromise;
    }

    this.connectionPromise = new Promise((resolve, reject) => {
      try {
        const wsUrl = this.getWebSocketUrl();
        console.log('Connecting to WebSocket:', wsUrl);
        
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log('WebSocket connected');
          this.reconnectAttempts = 0;
          this.startHeartbeat();
          this.notifyConnectionChange(true);
          
          // Track connection success
          analyticsService.recordMetric('websocket_connected', 1, {
            reconnectAttempts: this.reconnectAttempts
          });
          
          resolve();
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event);
        };

        this.ws.onclose = (event) => {
          console.log('WebSocket disconnected:', event.code, event.reason);
          this.cleanup();
          this.notifyConnectionChange(false);
          
          // Track disconnection
          analyticsService.recordMetric('websocket_disconnected', 1, {
            code: event.code,
            reason: event.reason,
            wasClean: event.wasClean
          });
          
          if (this.options.autoReconnect && !event.wasClean && 
              this.reconnectAttempts < this.options.maxReconnectAttempts) {
            this.scheduleReconnect();
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          analyticsService.recordMetric('websocket_error', 1);
          reject(error);
        };

      } catch (error) {
        console.error('Error creating WebSocket:', error);
        reject(error);
      }
    });

    return this.connectionPromise;
  }

  private getWebSocketUrl(): string {
    const baseUrl = config.api.baseUrl;
    const wsUrl = baseUrl.replace(/^https?:\/\//, '').replace(/\/$/, '');
    const protocol = baseUrl.startsWith('https') ? 'wss' : 'ws';
    const token = localStorage.getItem('auth_token');
    
    return `${protocol}://${wsUrl}/ws/realtime${token ? `?token=${token}` : ''}`;
  }

  private cleanup(): void {
    this.ws = null;
    this.connectionPromise = null;
    this.stopHeartbeat();
  }

  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    const delay = this.options.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`Scheduling WebSocket reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
    
    setTimeout(() => {
      this.connect().catch(error => {
        console.error('WebSocket reconnect failed:', error);
      });
    }, delay);
  }

  // Heartbeat mechanism
  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      if (this.isConnected()) {
        this.send({
          type: 'ping',
          data: { timestamp: Date.now() }
        });
      }
    }, this.options.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  // Message handling
  private handleMessage(event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      // Handle pong responses
      if (message.type === 'pong') {
        return;
      }

      // Notify subscribers
      const subscribers = this.subscriptions.get(message.type) || [];
      subscribers.forEach(subscription => {
        try {
          subscription.callback(message.data);
        } catch (error) {
          console.error(`Error in WebSocket subscription callback for ${message.type}:`, error);
        }
      });

      // Track message received
      analyticsService.recordMetric('websocket_message_received', 1, {
        messageType: message.type,
        subscriberCount: subscribers.length
      });

    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  }

  // Subscription management
  subscribe(type: string, callback: (data: any) => void): string {
    const subscription: WebSocketSubscription = {
      id: this.generateSubscriptionId(),
      type,
      callback
    };

    if (!this.subscriptions.has(type)) {
      this.subscriptions.set(type, []);
    }
    
    this.subscriptions.get(type)!.push(subscription);

    // Track subscription
    analyticsService.recordMetric('websocket_subscription_added', 1, {
      messageType: type,
      totalSubscriptions: this.getTotalSubscriptions()
    });

    return subscription.id;
  }

  unsubscribe(subscriptionId: string): void {
    for (const [type, subscriptions] of Array.from(this.subscriptions.entries())) {
      const index = subscriptions.findIndex(sub => sub.id === subscriptionId);
      if (index !== -1) {
        subscriptions.splice(index, 1);
        
        // Clean up empty subscription arrays
        if (subscriptions.length === 0) {
          this.subscriptions.delete(type);
        }

        // Track unsubscription
        analyticsService.recordMetric('websocket_subscription_removed', 1, {
          messageType: type,
          totalSubscriptions: this.getTotalSubscriptions()
        });
        
        return;
      }
    }
  }

  private generateSubscriptionId(): string {
    return `sub_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private getTotalSubscriptions(): number {
    let total = 0;
    for (const subscriptions of Array.from(this.subscriptions.values())) {
      total += subscriptions.length;
    }
    return total;
  }

  // Message sending
  send(message: WebSocketMessage): void {
    if (!this.isConnected()) {
      console.warn('WebSocket not connected, cannot send message:', message);
      return;
    }

    try {
      this.ws!.send(JSON.stringify({
        ...message,
        timestamp: Date.now()
      }));

      // Track message sent
      analyticsService.recordMetric('websocket_message_sent', 1, {
        messageType: message.type
      });
    } catch (error) {
      console.error('Error sending WebSocket message:', error);
    }
  }

  // Connection status
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  addConnectionListener(listener: (connected: boolean) => void): () => void {
    this.connectionListeners.push(listener);
    return () => {
      this.connectionListeners = this.connectionListeners.filter(l => l !== listener);
    };
  }

  private notifyConnectionChange(connected: boolean): void {
    this.connectionListeners.forEach(listener => {
      try {
        listener(connected);
      } catch (error) {
        console.error('Error in connection listener:', error);
      }
    });
  }

  // Disconnect
  disconnect(): void {
    this.options.autoReconnect = false; // Prevent reconnection
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
    }
    
    this.cleanup();
    this.subscriptions.clear();
    this.connectionListeners = [];
  }

  // Utility methods
  getConnectionState(): string {
    if (!this.ws) return 'DISCONNECTED';
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING: return 'CONNECTING';
      case WebSocket.OPEN: return 'CONNECTED';
      case WebSocket.CLOSING: return 'CLOSING';
      case WebSocket.CLOSED: return 'CLOSED';
      default: return 'UNKNOWN';
    }
  }

  getReconnectAttempts(): number {
    return this.reconnectAttempts;
  }

  getSubscriptionCount(): number {
    return this.getTotalSubscriptions();
  }
}

// Create singleton instance
export const websocketService = new WebSocketService();

// Specific services for different data types
export class ProgressWebSocketService {
  private subscriptionId: string | null = null;

  subscribe(callback: (progressData: any) => void): () => void {
    this.subscriptionId = websocketService.subscribe('progress_update', callback);
    
    return () => {
      if (this.subscriptionId) {
        websocketService.unsubscribe(this.subscriptionId);
        this.subscriptionId = null;
      }
    };
  }

  updateProgress(lessonId: string, progress: any): void {
    websocketService.send({
      type: 'progress_update',
      data: {
        lesson_id: lessonId,
        progress,
        timestamp: Date.now()
      }
    });
  }
}

export class AnalyticsWebSocketService {
  private subscriptionId: string | null = null;

  subscribe(callback: (analyticsData: any) => void): () => void {
    this.subscriptionId = websocketService.subscribe('analytics_update', callback);
    
    return () => {
      if (this.subscriptionId) {
        websocketService.unsubscribe(this.subscriptionId);
        this.subscriptionId = null;
      }
    };
  }

  sendEvent(eventType: string, eventData: any): void {
    websocketService.send({
      type: 'analytics_event',
      data: {
        event_type: eventType,
        event_data: eventData,
        timestamp: Date.now()
      }
    });
  }
}

export class LessonWebSocketService {
  private subscriptionId: string | null = null;

  subscribe(callback: (lessonData: any) => void): () => void {
    this.subscriptionId = websocketService.subscribe('lesson_update', callback);
    
    return () => {
      if (this.subscriptionId) {
        websocketService.unsubscribe(this.subscriptionId);
        this.subscriptionId = null;
      }
    };
  }

  requestLessonUpdate(lessonId: string): void {
    websocketService.send({
      type: 'request_lesson_update',
      data: {
        lesson_id: lessonId,
        timestamp: Date.now()
      }
    });
  }
}

// Export service instances
export const progressWebSocketService = new ProgressWebSocketService();
export const analyticsWebSocketService = new AnalyticsWebSocketService();
export const lessonWebSocketService = new LessonWebSocketService();