/**
 * End-to-End Integration Tests
 * 
 * This file contains comprehensive end-to-end tests that simulate complete user journeys
 * across the SnapStudy platform, testing the integration between frontend components
 * and backend services in realistic scenarios.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { DataSyncProvider } from '../contexts/DataSyncContext';

// Import main components for testing
import App from '../App';
import { UploadModal } from '../components/UploadModal';
import { LessonViewer } from '../components/LessonViewer';
import { QuizInterface } from '../components/QuizInterface';
import { StudyBuddy } from '../components/StudyBuddy';
import { AnalyticsDashboard } from '../components/AnalyticsDashboard';

// Mock services
jest.mock('../services/authService');
jest.mock('../services/lessonService');
jest.mock('../services/quizService');
jest.mock('../services/chatService');
jest.mock('../services/analyticsService');
jest.mock('../services/processingService');
jest.mock('../services/websocketService');

const mockFetch = jest.fn();
global.fetch = mockFetch;

// Test wrapper component
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <BrowserRouter>
    <DataSyncProvider>
      {children}
    </DataSyncProvider>
  </BrowserRouter>
);

describe('End-to-End Integration Tests', () => {
  let mockWebSocket: any;
  let user: any;

  beforeEach(() => {
    user = userEvent.setup();
    mockFetch.mockClear();
    
    // Mock localStorage
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: jest.fn(() => 'mock-jwt-token'),
        setItem: jest.fn(),
        removeItem: jest.fn(),
        clear: jest.fn(),
      },
      writable: true,
    });

    // Mock WebSocket
    mockWebSocket = {
      send: jest.fn(),
      close: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      readyState: 1,
    };
    global.WebSocket = jest.fn(() => mockWebSocket);

    // Mock File API
    global.File = class MockFile {
      constructor(public content: string[], public name: string, public options: any) {}
      get size() { return this.content.join('').length; }
      get type() { return this.options.type; }
    } as any;

    // Mock URL.createObjectURL
    global.URL.createObjectURL = jest.fn(() => 'mock-url');
    global.URL.revokeObjectURL = jest.fn();
  });

  afterEach(() => {
    jest.clearAllTimers();
    jest.clearAllMocks();
  });

  describe('Complete Learning Journey', () => {
    test('should complete full user journey from upload to quiz completion', async () => {
      // Mock API responses for the complete journey
      const mockLesson = {
        lesson_id: 'lesson-123',
        title: 'React Fundamentals',
        status: 'completed',
        micro_lessons: [
          { id: 'ml-1', title: 'Introduction', content: 'React is...' },
          { id: 'ml-2', title: 'Components', content: 'Components are...' }
        ]
      };

      const mockQuiz = {
        quiz_id: 'quiz-123',
        questions: [
          {
            id: 'q1',
            type: 'multiple_choice',
            question: 'What is React?',
            options: ['Library', 'Framework', 'Language', 'Tool'],
            correct_answer: 'Library'
          }
        ]
      };

      const mockQuizResults = {
        quiz_id: 'quiz-123',
        overall_score: 100,
        question_results: [{ question_id: 'q1', correct: true, score: 100 }],
        feedback: 'Excellent work!'
      };

      // Step 1: Upload lesson
      mockFetch
        .mockResolvedValueOnce({ ok: true, json: async () => mockLesson })
        .mockResolvedValueOnce({ ok: true, json: async () => mockLesson.micro_lessons })
        .mockResolvedValueOnce({ ok: true, json: async () => mockQuiz })
        .mockResolvedValueOnce({ ok: true, json: async () => mockQuizResults });

      render(
        <TestWrapper>
          <UploadModal isOpen={true} onClose={() => {}} />
        </TestWrapper>
      );

      // Simulate file upload
      const fileInput = screen.getByLabelText(/upload/i);
      const testFile = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
      
      await user.upload(fileInput, testFile);
      
      const uploadButton = screen.getByRole('button', { name: /upload/i });
      await user.click(uploadButton);

      // Wait for upload to complete
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith('/api/v1/lessons/upload', expect.any(Object));
      });

      // Step 2: Navigate to lesson viewer
      render(
        <TestWrapper>
          <LessonViewer lessonId="lesson-123" />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('React Fundamentals')).toBeInTheDocument();
      });

      // Step 3: Complete micro-lessons
      const nextButton = screen.getByRole('button', { name: /next/i });
      await user.click(nextButton);

      await waitFor(() => {
        expect(screen.getByText('Components are...')).toBeInTheDocument();
      });

      // Step 4: Start quiz
      const startQuizButton = screen.getByRole('button', { name: /start quiz/i });
      await user.click(startQuizButton);

      // Step 5: Answer quiz questions
      render(
        <TestWrapper>
          <QuizInterface quizId="quiz-123" lessonId="lesson-123" />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('What is React?')).toBeInTheDocument();
      });

      const libraryOption = screen.getByLabelText('Library');
      await user.click(libraryOption);

      const submitButton = screen.getByRole('button', { name: /submit/i });
      await user.click(submitButton);

      // Step 6: View results
      await waitFor(() => {
        expect(screen.getByText('Excellent work!')).toBeInTheDocument();
        expect(screen.getByText('100')).toBeInTheDocument(); // Score
      });

      // Verify all API calls were made correctly
      expect(mockFetch).toHaveBeenCalledTimes(4);
    });

    test('should handle offline/online transitions during learning', async () => {
      // Mock offline scenario
      Object.defineProperty(navigator, 'onLine', { value: false, writable: true });

      const mockLesson = {
        lesson_id: 'lesson-123',
        title: 'Offline Lesson',
        micro_lessons: [{ id: 'ml-1', content: 'Cached content' }]
      };

      // Mock cached data
      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockLesson });

      render(
        <TestWrapper>
          <LessonViewer lessonId="lesson-123" />
        </TestWrapper>
      );

      // Should show offline indicator
      await waitFor(() => {
        expect(screen.getByText(/offline/i)).toBeInTheDocument();
      });

      // Simulate coming back online
      Object.defineProperty(navigator, 'onLine', { value: true });
      
      // Trigger online event
      act(() => {
        window.dispatchEvent(new Event('online'));
      });

      // Should sync data when back online
      await waitFor(() => {
        expect(screen.queryByText(/offline/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Real-Time Chat Integration Journey', () => {
    test('should maintain chat context throughout learning session', async () => {
      const mockChatResponses = [
        { role: 'assistant', content: 'Hello! How can I help you with React?' },
        { role: 'assistant', content: 'Components are reusable pieces of UI...' },
        { role: 'assistant', content: 'Great question! Let me explain props...' }
      ];

      // Mock WebSocket messages
      let messageHandler: (event: any) => void;
      mockWebSocket.addEventListener = jest.fn((event, handler) => {
        if (event === 'message') {
          messageHandler = handler;
        }
      });

      render(
        <TestWrapper>
          <StudyBuddy lessonId="lesson-123" />
        </TestWrapper>
      );

      // Open chat
      const chatButton = screen.getByRole('button', { name: /chat/i });
      await user.click(chatButton);

      // Send first message
      const messageInput = screen.getByPlaceholderText(/ask a question/i);
      await user.type(messageInput, 'What is React?');
      
      const sendButton = screen.getByRole('button', { name: /send/i });
      await user.click(sendButton);

      // Simulate WebSocket response
      act(() => {
        messageHandler({ data: JSON.stringify(mockChatResponses[0]) });
      });

      await waitFor(() => {
        expect(screen.getByText('Hello! How can I help you with React?')).toBeInTheDocument();
      });

      // Send follow-up message
      await user.clear(messageInput);
      await user.type(messageInput, 'What are components?');
      await user.click(sendButton);

      act(() => {
        messageHandler({ data: JSON.stringify(mockChatResponses[1]) });
      });

      await waitFor(() => {
        expect(screen.getByText('Components are reusable pieces of UI...')).toBeInTheDocument();
      });

      // Verify chat context is maintained
      expect(screen.getByText('What is React?')).toBeInTheDocument();
      expect(screen.getByText('What are components?')).toBeInTheDocument();
    });

    test('should handle chat connection errors gracefully', async () => {
      // Mock WebSocket connection failure
      mockWebSocket.readyState = 3; // CLOSED
      
      let errorHandler: (event: any) => void;
      mockWebSocket.addEventListener = jest.fn((event, handler) => {
        if (event === 'error') {
          errorHandler = handler;
        }
      });

      render(
        <TestWrapper>
          <StudyBuddy lessonId="lesson-123" />
        </TestWrapper>
      );

      // Simulate connection error
      act(() => {
        errorHandler(new Error('Connection failed'));
      });

      await waitFor(() => {
        expect(screen.getByText(/connection error/i)).toBeInTheDocument();
      });

      // Should show retry option
      const retryButton = screen.getByRole('button', { name: /retry/i });
      expect(retryButton).toBeInTheDocument();
    });
  });

  describe('Analytics Dashboard Integration Journey', () => {
    test('should display real-time analytics updates during learning', async () => {
      const mockInitialAnalytics = {
        metrics: {
          lessons_completed: 5,
          average_score: 80,
          total_time_spent_minutes: 120
        }
      };

      const mockUpdatedAnalytics = {
        metrics: {
          lessons_completed: 6,
          average_score: 85,
          total_time_spent_minutes: 150
        }
      };

      mockFetch
        .mockResolvedValueOnce({ ok: true, json: async () => mockInitialAnalytics })
        .mockResolvedValueOnce({ ok: true, json: async () => mockUpdatedAnalytics });

      render(
        <TestWrapper>
          <AnalyticsDashboard />
        </TestWrapper>
      );

      // Initial analytics load
      await waitFor(() => {
        expect(screen.getByText('5')).toBeInTheDocument(); // lessons completed
        expect(screen.getByText('80')).toBeInTheDocument(); // average score
      });

      // Simulate completing a lesson (would trigger analytics update)
      act(() => {
        // This would be triggered by lesson completion event
        window.dispatchEvent(new CustomEvent('lessonCompleted', {
          detail: { lessonId: 'lesson-123', score: 95 }
        }));
      });

      // Analytics should update
      await waitFor(() => {
        expect(screen.getByText('6')).toBeInTheDocument(); // updated lessons completed
        expect(screen.getByText('85')).toBeInTheDocument(); // updated average score
      });
    });
  });

  describe('Multi-Modal Content Journey', () => {
    test('should seamlessly switch between content formats', async () => {
      const mockLesson = {
        lesson_id: 'lesson-123',
        title: 'Multi-Modal Lesson',
        content: {
          text: 'This is the text version...',
          audio_url: 'https://example.com/audio.mp3',
          video_url: 'https://example.com/video.mp4'
        }
      };

      mockFetch.mockResolvedValueOnce({ ok: true, json: async () => mockLesson });

      render(
        <TestWrapper>
          <LessonViewer lessonId="lesson-123" />
        </TestWrapper>
      );

      // Initially shows text content
      await waitFor(() => 