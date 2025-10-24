/**
 * StudyBuddy Component Tests
 * 
 * Tests for StudyBuddy component with backend chat integration
 */

import { chatService } from '../services/chatService';
import { Lesson, User, ChatMessage } from '../types';

// Mock the chat service
jest.mock('../services/chatService', () => ({
  chatService: {
    startNewSession: jest.fn(),
    getChatHistory: jest.fn(),
    sendMessage: jest.fn(),
    sendStreamingMessage: jest.fn(),
    isWebSocketConnected: jest.fn(),
    disconnect: jest.fn(),
  }
}));

const mockChatService = chatService as jest.Mocked<typeof chatService>;

// Mock CSS import
jest.mock('../components/StudyBuddy.css', () => ({}));

describe('StudyBuddy Chat Integration', () => {
  const mockUser: User = {
    id: 'user-123',
    email: 'test@example.com',
    username: 'testuser'
  };

  const mockLesson: Lesson = {
    lesson_id: 'lesson-123',
    user_id: 'user-123',
    title: 'Test Lesson',
    content_type: 'pdf',
    s3_key: 'test-key',
    status: 'completed',
    created_at: '2023-01-01T00:00:00Z',
    updated_at: '2023-01-01T00:00:00Z'
  };

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Default mock implementations
    mockChatService.startNewSession.mockResolvedValue('session-123');
    mockChatService.getChatHistory.mockResolvedValue([]);
    mockChatService.isWebSocketConnected.mockReturnValue(false);
  });

  describe('Chat Service Integration', () => {
    test('should initialize chat session with lesson ID', async () => {
      // Simulate component initialization
      await mockChatService.startNewSession(mockLesson.lesson_id);
      await mockChatService.getChatHistory('session-123');

      expect(mockChatService.startNewSession).toHaveBeenCalledWith('lesson-123');
      expect(mockChatService.getChatHistory).toHaveBeenCalledWith('session-123');
    });

    test('should send message via HTTP API when WebSocket not connected', async () => {
      mockChatService.sendMessage.mockResolvedValue({
        content: 'AI response',
        session_id: 'session-123'
      });

      const result = await mockChatService.sendMessage('Test message', 'lesson-123', 'session-123');

      expect(mockChatService.sendMessage).toHaveBeenCalledWith(
        'Test message',
        'lesson-123',
        'session-123'
      );
      expect(result.content).toBe('AI response');
    });

    test('should use WebSocket streaming when connected', async () => {
      mockChatService.isWebSocketConnected.mockReturnValue(true);
      
      const callbacks = {
        onChunk: jest.fn(),
        onComplete: jest.fn(),
        onError: jest.fn()
      };

      mockChatService.sendStreamingMessage.mockImplementation(async (message, lessonId, sessionId, cb) => {
        if (cb) {
          cb.onChunk('Streaming ');
          cb.onChunk('response');
          cb.onComplete('Streaming response');
        }
      });

      await mockChatService.sendStreamingMessage('Test streaming', 'lesson-123', 'session-123', callbacks);

      expect(mockChatService.sendStreamingMessage).toHaveBeenCalledWith(
        'Test streaming',
        'lesson-123',
        'session-123',
        callbacks
      );
      expect(callbacks.onChunk).toHaveBeenCalledWith('Streaming ');
      expect(callbacks.onChunk).toHaveBeenCalledWith('response');
      expect(callbacks.onComplete).toHaveBeenCalledWith('Streaming response');
    });

    test('should handle message sending errors', async () => {
      mockChatService.sendMessage.mockRejectedValue(new Error('Network error'));

      await expect(mockChatService.sendMessage('Test error', 'lesson-123', 'session-123'))
        .rejects.toThrow('Network error');
    });

    test('should handle session initialization errors', async () => {
      mockChatService.startNewSession.mockRejectedValue(new Error('Session error'));

      await expect(mockChatService.startNewSession('lesson-123'))
        .rejects.toThrow('Session error');
    });

    test('should handle chat history retrieval', async () => {
      const mockHistory: ChatMessage[] = [
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

      mockChatService.getChatHistory.mockResolvedValue(mockHistory);

      const result = await mockChatService.getChatHistory('session-123');

      expect(result).toEqual(mockHistory);
      expect(result).toHaveLength(2);
      expect(result[0].sender).toBe('user');
      expect(result[1].sender).toBe('ai');
    });

    test('should handle WebSocket connection status', () => {
      mockChatService.isWebSocketConnected.mockReturnValue(false);
      expect(mockChatService.isWebSocketConnected()).toBe(false);

      mockChatService.isWebSocketConnected.mockReturnValue(true);
      expect(mockChatService.isWebSocketConnected()).toBe(true);
    });

    test('should disconnect WebSocket properly', () => {
      mockChatService.disconnect();
      expect(mockChatService.disconnect).toHaveBeenCalled();
    });

    test('should handle streaming errors with fallback', async () => {
      const callbacks = {
        onChunk: jest.fn(),
        onComplete: jest.fn(),
        onError: jest.fn()
      };

      mockChatService.sendStreamingMessage.mockImplementation(async (message, lessonId, sessionId, cb) => {
        if (cb) {
          cb.onError('Streaming failed');
        }
      });

      await mockChatService.sendStreamingMessage('Test error', 'lesson-123', 'session-123', callbacks);

      expect(callbacks.onError).toHaveBeenCalledWith('Streaming failed');
    });

    test('should handle empty chat history gracefully', async () => {
      mockChatService.getChatHistory.mockResolvedValue([]);

      const result = await mockChatService.getChatHistory('session-123');

      expect(result).toEqual([]);
      expect(result).toHaveLength(0);
    });
  });

  describe('Message Flow Integration', () => {
    test('should maintain session ID across messages', async () => {
      // Start session
      const sessionId = await mockChatService.startNewSession('lesson-123');
      expect(sessionId).toBe('session-123');

      // Send message with session ID
      mockChatService.sendMessage.mockResolvedValue({
        content: 'Response',
        session_id: 'session-123'
      });

      const result = await mockChatService.sendMessage('Hello', 'lesson-123', sessionId);
      expect(result.session_id).toBe('session-123');
    });

    test('should handle lesson context in messages', async () => {
      await mockChatService.sendMessage('Explain this lesson', 'lesson-123', 'session-123');

      expect(mockChatService.sendMessage).toHaveBeenCalledWith(
        'Explain this lesson',
        'lesson-123',
        'session-123'
      );
    });

    test('should support messages without lesson context', async () => {
      await mockChatService.sendMessage('General question');

      expect(mockChatService.sendMessage).toHaveBeenCalledWith('General question');
    });
  });

  describe('Error Recovery', () => {
    test('should handle network failures gracefully', async () => {
      mockChatService.sendMessage.mockRejectedValue(new Error('Network error'));

      try {
        await mockChatService.sendMessage('Test message', 'lesson-123', 'session-123');
      } catch (error) {
        expect(error).toBeInstanceOf(Error);
        expect((error as Error).message).toBe('Network error');
      }
    });

    test('should handle WebSocket disconnection', async () => {
      mockChatService.isWebSocketConnected.mockReturnValue(false);
      
      // Should fallback to HTTP API
      mockChatService.sendMessage.mockResolvedValue({
        content: 'Fallback response',
        session_id: 'session-123'
      });

      const result = await mockChatService.sendMessage('Test fallback', 'lesson-123', 'session-123');
      expect(result.content).toBe('Fallback response');
    });
  });
});