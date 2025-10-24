import { websocketService, WebSocketMessage } from '../services/websocketService';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(public url: string) {
    // Simulate connection opening
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 10);
  }

  send(data: string) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
    // Mock sending data
  }

  close(code?: number, reason?: string) {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code, reason, wasClean: true }));
    }
  }

  // Helper method to simulate receiving messages
  simulateMessage(data: any) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
    }
  }

  // Helper method to simulate errors
  simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }
}

// Mock global WebSocket
(global as any).WebSocket = MockWebSocket;

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

describe('WebSocketService', () => {
  let mockWs: MockWebSocket;

  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockReturnValue('mock-token');
    
    // Reset websocket service state
    websocketService.disconnect();
  });

  afterEach(() => {
    websocketService.disconnect();
  });

  describe('connection management', () => {
    it('should connect to WebSocket successfully', async () => {
      const connectPromise = websocketService.connect();

      // Wait for connection to complete
      await connectPromise;

      expect(websocketService.isConnected()).toBe(true);
      expect(websocketService.getConnectionState()).toBe('CONNECTED');
    });

    it('should handle connection errors', async () => {
      // Mock WebSocket constructor to throw error
      (global as any).WebSocket = jest.fn().mockImplementation(() => {
        throw new Error('Connection failed');
      });

      await expect(websocketService.connect()).rejects.toThrow('Connection failed');
    });

    it('should notify connection listeners', async () => {
      const listener = jest.fn();
      websocketService.addConnectionListener(listener);

      await websocketService.connect();

      expect(listener).toHaveBeenCalledWith(true);
    });

    it('should remove connection listeners', async () => {
      const listener = jest.fn();
      const removeListener = websocketService.addConnectionListener(listener);

      removeListener();
      await websocketService.connect();

      expect(listener).not.toHaveBeenCalled();
    });

    it('should disconnect properly', async () => {
      await websocketService.connect();
      
      websocketService.disconnect();

      expect(websocketService.isConnected()).toBe(false);
    });
  });

  describe('message handling', () => {
    beforeEach(async () => {
      await websocketService.connect();
      mockWs = (websocketService as any).ws;
    });

    it('should handle incoming messages', () => {
      const callback = jest.fn();
      const subscriptionId = websocketService.subscribe('test_message', callback);

      const testMessage = {
        type: 'test_message',
        data: { content: 'Hello World' }
      };

      mockWs.simulateMessage(testMessage);

      expect(callback).toHaveBeenCalledWith({ content: 'Hello World' });
    });

    it('should handle pong messages without notifying subscribers', () => {
      const callback = jest.fn();
      websocketService.subscribe('pong', callback);

      mockWs.simulateMessage({ type: 'pong', data: {} });

      expect(callback).not.toHaveBeenCalled();
    });

    it('should handle malformed messages gracefully', () => {
      const callback = jest.fn();
      websocketService.subscribe('test_message', callback);

      // Simulate malformed JSON
      if (mockWs.onmessage) {
        mockWs.onmessage(new MessageEvent('message', { data: 'invalid json' }));
      }

      expect(callback).not.toHaveBeenCalled();
    });

    it('should send messages successfully', () => {
      const sendSpy = jest.spyOn(mockWs, 'send');

      const message: WebSocketMessage = {
        type: 'test_send',
        data: { content: 'Test message' }
      };

      websocketService.send(message);

      expect(sendSpy).toHaveBeenCalledWith(
        JSON.stringify({
          ...message,
          timestamp: expect.any(Number)
        })
      );
    });

    it('should not send messages when disconnected', () => {
      websocketService.disconnect();

      const message: WebSocketMessage = {
        type: 'test_send',
        data: { content: 'Test message' }
      };

      // Should not throw error, just log warning
      expect(() => websocketService.send(message)).not.toThrow();
    });
  });

  describe('subscription management', () => {
    beforeEach(async () => {
      await websocketService.connect();
      mockWs = (websocketService as any).ws;
    });

    it('should subscribe to message types', () => {
      const callback = jest.fn();
      const subscriptionId = websocketService.subscribe('test_type', callback);

      expect(subscriptionId).toBeDefined();
      expect(typeof subscriptionId).toBe('string');
      expect(websocketService.getSubscriptionCount()).toBe(1);
    });

    it('should unsubscribe from message types', () => {
      const callback = jest.fn();
      const subscriptionId = websocketService.subscribe('test_type', callback);

      websocketService.unsubscribe(subscriptionId);

      expect(websocketService.getSubscriptionCount()).toBe(0);

      // Message should not be received after unsubscribe
      mockWs.simulateMessage({ type: 'test_type', data: { test: true } });
      expect(callback).not.toHaveBeenCalled();
    });

    it('should handle multiple subscriptions to same message type', () => {
      const callback1 = jest.fn();
      const callback2 = jest.fn();

      websocketService.subscribe('test_type', callback1);
      websocketService.subscribe('test_type', callback2);

      mockWs.simulateMessage({ type: 'test_type', data: { test: true } });

      expect(callback1).toHaveBeenCalledWith({ test: true });
      expect(callback2).toHaveBeenCalledWith({ test: true });
    });

    it('should handle subscription callback errors gracefully', () => {
      const errorCallback = jest.fn().mockImplementation(() => {
        throw new Error('Callback error');
      });
      const normalCallback = jest.fn();

      websocketService.subscribe('test_type', errorCallback);
      websocketService.subscribe('test_type', normalCallback);

      mockWs.simulateMessage({ type: 'test_type', data: { test: true } });

      expect(errorCallback).toHaveBeenCalled();
      expect(normalCallback).toHaveBeenCalled();
    });
  });

  describe('heartbeat mechanism', () => {
    beforeEach(async () => {
      await websocketService.connect();
      mockWs = (websocketService as any).ws;
    });

    it('should send ping messages periodically', (done) => {
      const sendSpy = jest.spyOn(mockWs, 'send');

      // Wait for heartbeat interval (mocked to be shorter)
      setTimeout(() => {
        expect(sendSpy).toHaveBeenCalledWith(
          JSON.stringify({
            type: 'ping',
            data: { timestamp: expect.any(Number) },
            timestamp: expect.any(Number)
          })
        );
        done();
      }, 100);
    }, 10000);
  });

  describe('reconnection logic', () => {
    it('should attempt reconnection on unexpected disconnect', async () => {
      await websocketService.connect();
      mockWs = (websocketService as any).ws;

      const connectSpy = jest.spyOn(websocketService, 'connect');

      // Simulate unexpected disconnect
      mockWs.close(1006, 'Connection lost');

      // Wait for reconnection attempt
      await new Promise(resolve => setTimeout(resolve, 1100));

      expect(connectSpy).toHaveBeenCalled();
    });

    it('should not reconnect on clean disconnect', async () => {
      await websocketService.connect();
      mockWs = (websocketService as any).ws;

      const connectSpy = jest.spyOn(websocketService, 'connect');

      // Simulate clean disconnect
      websocketService.disconnect();

      // Wait to ensure no reconnection attempt
      await new Promise(resolve => setTimeout(resolve, 1100));

      expect(connectSpy).toHaveBeenCalledTimes(1); // Only the initial connect
    });
  });

  describe('utility methods', () => {
    it('should return correct connection state', () => {
      expect(websocketService.getConnectionState()).toBe('DISCONNECTED');
    });

    it('should return reconnect attempts count', () => {
      expect(websocketService.getReconnectAttempts()).toBe(0);
    });

    it('should return subscription count', async () => {
      await websocketService.connect();
      
      expect(websocketService.getSubscriptionCount()).toBe(0);
      
      websocketService.subscribe('test', () => {});
      expect(websocketService.getSubscriptionCount()).toBe(1);
    });
  });
});