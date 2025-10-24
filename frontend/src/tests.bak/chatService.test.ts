/**
 * Chat Service Tests
 * 
 * Tests for chat service functionality including WebSocket integration
 */

import { chatService } from '../services/chatService';
import { ChatMessage, ChatResponse } from '../types';

// Mock axios
jest.mock('../services/api', () => ({
  get: jest.fn(),
  post: jest.fn(),
}));

// Mock config
jest.mock('../config', () => ({
  config: {
    api: {
      baseUrl: 'https://api.example.com'
    }
  }
}));

import api from '../services/api';
const mockApi = api as jest.Mocked<typeof api>;

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
    // Mock send functionality
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

// Replace global WebSocket with mock
(global as any).WebSocket = MockWebSocket;

describe('ChatService', () => {
  let mockWebSocket: MockWebSocket;

  beforeEach(() => {
    jest.clearAllMocks();
    chatService.disconnect();
    
    // Mock localStorage
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: jest.fn(() => 'mock-token'),
        setItem: jest.fn(),
        removeItem: jest.fn(),
      },
      writable: true,
    });
  });

  afterEach(() => {
    chatService.disconnect();
  });

  describe('sendMessage', () => {
    test('should send message via HTTP API', async () => {
      const mockResponse: ChatResponse = {
        content: 'AI response',
        session_id: 'session-123'
      };

      mockApi.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await chatService.sendMessage('Hello', 'lesson-123', 'session-123');

      expect(mockApi.post).toHaveBeenCalledWith('/api/v1/chat/message', {
        message: 'Hello',
        lesson_id: 'lesson-123',
        session_id: 'session-123'
      });
      expect(result).toEqual(mockResponse);
    });

    test('should handle API errors', async () => {
      mockApi.post.mockRejectedValueOnce(new Error('Network error'));

      await expect(chatService.sendMessage('Hello'))
        .rejects.toThrow('Network error');
    });
  });

  describe('getChatHistory', () => {
    test('should fetch chat history', async () => {
      const mockMessages: ChatMessage[] = [
        {
          id: '1',
          content: 'Hello',
          sender: 'user',
          timestamp: new Date()
        },
        {
          id: '2',
          content: 'Hi there!',
          sender: 'ai',
          timestamp: new Date()
        }
      ];

      mockApi.get.mockResolvedValueOnce({ data: { messages: mockMessages } });

      const result = await chatService.getChatHistory('session-123');

      expect(mockApi.get).toHaveBeenCalledWith('/api/v1/chat/history/session-123');
      expect(result).toEqual(mockMessages);
    });

    test('should return empty array on error', async () => {
      mockApi.get.mockRejectedValueOnce(new Error('Network error'));

      const result = await chatService.getChatHistory('session-123');

      expect(result).toEqual([]);
    });
  });

  describe('startNewSession', () => {
    test('should start new chat session', async () => {
      const mockSessionId = 'new-session-123';
      mockApi.post.mockResolvedValueOnce({ data: { session_id: mockSessionId } });

      const result = await chatService.startNewSession('lesson-123');

      expect(mockApi.post).toHaveBeenCalledWith('/api/v1/chat/session', {
        lesson_id: 'lesson-123'
      });
      expect(result).toBe(mockSessionId);
    });

    test('should handle session creation errors', async () => {
      mockApi.post.mockRejectedValueOnce(new Error('Server error'));

      await expect(chatService.startNewSession())
        .rejects.toThrow('Server error');
    });
  });

  describe('WebSocket functionality', () => {
    test('should establish WebSocket connection', async () => {
      const callbacks = {
        onChunk: jest.fn(),
        onComplete: jest.fn(),
        onError: jest.fn()
      };

      await chatService.sendStreamingMessage('Hello', 'lesson-123', 'session-123', callbacks);

      expect(chatService.isWebSocketConnected()).toBe(true);
    });

    test('should handle streaming message chunks', async () => {
      const callbacks = {
        onChunk: jest.fn(),
        onComplete: jest.fn(),
        onError: jest.fn()
      };

      // Start streaming
      const streamingPromise = chatService.sendStreamingMessage('Hello', 'lesson-123', 'session-123', callbacks);

      // Wait for WebSocket to connect
      await new Promise(resolve => setTimeout(resolve, 20));

      // Get the WebSocket instance
      const wsInstance = (global as any).WebSocket.mock.instances[0] as MockWebSocket;

      // Simulate receiving chunks
      wsInstance.simulateMessage({
        type: 'stream_chunk',
        session_id: 'session-123',
        data: { chunk: 'Hello ' }
      });

      wsInstance.simulateMessage({
        type: 'stream_chunk',
        session_id: 'session-123',
        data: { chunk: 'world!' }
      });

      wsInstance.simulateMessage({
        type: 'stream_end',
        session_id: 'session-123',
        data: { full_message: 'Hello world!' }
      });

      await streamingPromise;

      expect(callbacks.onChunk).toHaveBeenCalledWith('Hello ');
      expect(callbacks.onChunk).toHaveBeenCalledWith('world!');
      expect(callbacks.onComplete).toHaveBeenCalledWith('Hello world!');
    });

    test('should handle WebSocket errors', async () => {
      const callbacks = {
        onChunk: jest.fn(),
        onComplete: jest.fn(),
        onError: jest.fn()
      };

      // Start streaming
      const streamingPromise = chatService.sendStreamingMessage('Hello', 'lesson-123', 'session-123', callbacks);

      // Wait for WebSocket to connect
      await new Promise(resolve => setTimeout(resolve, 20));

      // Get the WebSocket instance and simulate error
      const wsInstance = (global as any).WebSocket.mock.instances[0] as MockWebSocket;
      wsInstance.simulateMessage({
        type: 'error',
        session_id: 'session-123',
        data: { error: 'Processing failed' }
      });

      await streamingPromise;

      expect(callbacks.onError).toHaveBeenCalledWith('Processing failed');
    });

    test('should disconnect WebSocket properly', async () => {
      const callbacks = {
        onChunk: jest.fn(),
        onComplete: jest.fn(),
        onError: jest.fn()
      };

      await chatService.sendStreamingMessage('Hello', 'lesson-123', 'session-123', callbacks);
      expect(chatService.isWebSocketConnected()).toBe(true);

      chatService.disconnect();
      expect(chatService.isWebSocketConnected()).toBe(false);
    });

    test('should handle WebSocket connection failures', async () => {
      // Mock WebSocket constructor to throw error
      const originalWebSocket = (global as any).WebSocket;
      (global as any).WebSocket = jest.fn(() => {
        throw new Error('Connection failed');
      });

      const callbacks = {
        onChunk: jest.fn(),
        onComplete: jest.fn(),
        onError: jest.fn()
      };

      await expect(
        chatService.sendStreamingMessage('Hello', 'lesson-123', 'session-123', callbacks)
      ).rejects.toThrow('Connection failed');

      expect(callbacks.onError).toHaveBeenCalledWith('Failed to send message');

      // Restore original WebSocket
      (global as any).WebSocket = originalWebSocket;
    });
  });

  describe('connection management', () => {
    test('should report WebSocket connection status correctly', () => {
      expect(chatService.isWebSocketConnected()).toBe(false);
    });

    test('should handle multiple connection attempts', async () => {
      const callbacks1 = {
        onChunk: jest.fn(),
        onComplete: jest.fn(),
        onError: jest.fn()
      };

      const callbacks2 = {
        onChunk: jest.fn(),
        onComplete: jest.fn(),
        onError: jest.fn()
      };

      // Start two streaming requests simultaneously
      const promise1 = chatService.sendStreamingMessage('Hello 1', 'lesson-123', 'session-123', callbacks1);
      const promise2 = chatService.sendStreamingMessage('Hello 2', 'lesson-123', 'session-123', callbacks2);

      await Promise.all([promise1, promise2]);

      // Should only create one WebSocket connection
      expect((global as any).WebSocket).toHaveBeenCalledTimes(1);
    });
  });
});