import api from './api';
import { ChatMessage, ChatResponse } from '../types';
import { config } from '../config';
import { InputValidator } from '../utils/inputValidation';

interface WebSocketMessage {
  type: 'message' | 'error' | 'connection' | 'stream_chunk' | 'stream_end';
  data: any;
  session_id?: string;
}

interface StreamingCallbacks {
  onChunk: (chunk: string) => void;
  onComplete: (fullMessage: string) => void;
  onError: (error: string) => void;
}

class ChatService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private streamingCallbacks: Map<string, StreamingCallbacks> = new Map();
  private connectionPromise: Promise<void> | null = null;

  private getWebSocketUrl(): string {
    const baseUrl = config.api.baseUrl;
    const wsUrl = baseUrl.replace(/^https?:\/\//, '').replace(/\/$/, '');
    const protocol = baseUrl.startsWith('https') ? 'wss' : 'ws';
    return `${protocol}://${wsUrl}/ws/chat`;
  }

  private async connectWebSocket(): Promise<void> {
    if (this.connectionPromise) {
      return this.connectionPromise;
    }

    this.connectionPromise = new Promise((resolve, reject) => {
      try {
        const token = localStorage.getItem('auth_token');
        const wsUrl = `${this.getWebSocketUrl()}${token ? `?token=${token}` : ''}`;
        
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log('WebSocket connected');
          this.reconnectAttempts = 0;
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            this.handleWebSocketMessage(message);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        this.ws.onclose = (event) => {
          console.log('WebSocket disconnected:', event.code, event.reason);
          this.ws = null;
          this.connectionPromise = null;
          
          if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };

      } catch (error) {
        console.error('Error creating WebSocket:', error);
        reject(error);
      }
    });

    return this.connectionPromise;
  }

  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`Scheduling WebSocket reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
    
    setTimeout(() => {
      this.connectWebSocket().catch(error => {
        console.error('WebSocket reconnect failed:', error);
      });
    }, delay);
  }

  private handleWebSocketMessage(message: WebSocketMessage): void {
    const { type, data, session_id } = message;

    switch (type) {
      case 'stream_chunk':
        if (session_id && this.streamingCallbacks.has(session_id)) {
          const callbacks = this.streamingCallbacks.get(session_id)!;
          callbacks.onChunk(data.chunk);
        }
        break;

      case 'stream_end':
        if (session_id && this.streamingCallbacks.has(session_id)) {
          const callbacks = this.streamingCallbacks.get(session_id)!;
          callbacks.onComplete(data.full_message);
          this.streamingCallbacks.delete(session_id);
        }
        break;

      case 'error':
        if (session_id && this.streamingCallbacks.has(session_id)) {
          const callbacks = this.streamingCallbacks.get(session_id)!;
          callbacks.onError(data.error);
          this.streamingCallbacks.delete(session_id);
        }
        break;

      default:
        console.log('Received WebSocket message:', message);
    }
  }

  async sendMessage(message: string, lessonId?: string, sessionId?: string): Promise<ChatResponse> {
    try {
      // Sanitize the message before sending
      const sanitizedMessage = InputValidator.sanitizeChatMessage(message);
      
      if (!sanitizedMessage.trim()) {
        throw new Error('Message cannot be empty');
      }

      if (sanitizedMessage.length > 2000) {
        throw new Error('Message is too long. Please keep it under 2000 characters.');
      }

      const response = await api.post('/api/v1/chat/message', {
        message: sanitizedMessage,
        lesson_id: lessonId,
        session_id: sessionId
      });
      
      return response.data;
    } catch (error) {
      console.error('Error sending chat message:', error);
      throw error;
    }
  }

  async sendStreamingMessage(
    message: string, 
    lessonId?: string, 
    sessionId?: string,
    callbacks?: StreamingCallbacks
  ): Promise<void> {
    try {
      // Sanitize the message before sending
      const sanitizedMessage = InputValidator.sanitizeChatMessage(message);
      
      if (!sanitizedMessage.trim()) {
        throw new Error('Message cannot be empty');
      }

      if (sanitizedMessage.length > 2000) {
        throw new Error('Message is too long. Please keep it under 2000 characters.');
      }

      // Ensure WebSocket connection
      await this.connectWebSocket();

      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        throw new Error('WebSocket not connected');
      }

      // Register streaming callbacks if provided
      if (callbacks && sessionId) {
        this.streamingCallbacks.set(sessionId, callbacks);
      }

      // Send message via WebSocket
      const wsMessage = {
        type: 'chat_message',
        data: {
          message: sanitizedMessage,
          lesson_id: lessonId,
          session_id: sessionId
        }
      };

      this.ws.send(JSON.stringify(wsMessage));
    } catch (error) {
      console.error('Error sending streaming message:', error);
      
      // Clean up callbacks on error
      if (sessionId && this.streamingCallbacks.has(sessionId)) {
        const callbacks = this.streamingCallbacks.get(sessionId)!;
        callbacks.onError('Failed to send message');
        this.streamingCallbacks.delete(sessionId);
      }
      
      throw error;
    }
  }

  async getChatHistory(sessionId: string): Promise<ChatMessage[]> {
    try {
      const response = await api.get(`/api/v1/chat/history/${sessionId}`);
      return response.data.messages || [];
    } catch (error) {
      console.error('Error fetching chat history:', error);
      return [];
    }
  }

  async startNewSession(lessonId?: string): Promise<string> {
    try {
      const response = await api.post('/api/v1/chat/session', {
        lesson_id: lessonId
      });
      
      return response.data.session_id;
    } catch (error) {
      console.error('Error starting chat session:', error);
      throw error;
    }
  }

  isWebSocketConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    this.connectionPromise = null;
    this.streamingCallbacks.clear();
  }
}

export const chatService = new ChatService();