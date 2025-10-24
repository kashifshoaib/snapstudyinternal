/**
 * Adaptive Learning Integration Tests
 * 
 * Tests for adaptive learning flow including micro-lesson transitions,
 * quiz integration, and backend communication.
 */

import { lessonService } from '../services/lessonService';
import { quizService } from '../services/quizService';
import { AdaptiveLearningState, AdaptiveContentResponse, MicroLesson, Quiz } from '../types';

// Mock the API service
jest.mock('../services/api', () => ({
  get: jest.fn(),
  post: jest.fn(),
}));

import api from '../services/api';
const mockApi = api as jest.Mocked<typeof api>;

describe('Adaptive Learning Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Lesson Service - Adaptive Learning', () => {
    describe('initializeAdaptiveLearning', () => {
      test('should initialize adaptive learning session', async () => {
        const mockState: AdaptiveLearningState = {
          current_micro_lesson_id: 'ml-1',
          lesson_id: 'lesson-123',
          progress: 0,
          next_content_type: 'micro_lesson',
          difficulty_adjustment: 0,
          learning_path: ['ml-1', 'ml-2', 'ml-3'],
          completed_micro_lessons: []
        };

        mockApi.post.mockResolvedValueOnce({ data: { data: mockState } });

        const result = await lessonService.initializeAdaptiveLearning('lesson-123', {
          difficulty_level: 'intermediate',
          learning_style: 'visual',
          attention_span: 15
        });

        expect(mockApi.post).toHaveBeenCalledWith('/api/v1/lessons/adaptive/initialize', {
          lesson_id: 'lesson-123',
          user_preferences: {
            difficulty_level: 'intermediate',
            learning_style: 'visual',
            attention_span: 15
          }
        });
        expect(result).toEqual(mockState);
      });

      test('should handle initialization errors', async () => {
        mockApi.post.mockRejectedValueOnce(new Error('Network error'));

        await expect(lessonService.initializeAdaptiveLearning('lesson-123'))
          .rejects.toThrow('Failed to start adaptive learning session');
      });
    });

    describe('getNextAdaptiveContent', () => {
      test('should get next micro lesson content', async () => {
        const mockResponse: AdaptiveContentResponse = {
          content_type: 'micro_lesson',
          micro_lesson: {
            micro_lesson_id: 'ml-2',
            lesson_id: 'lesson-123',
            title: 'Advanced Concepts',
            summary: 'Learn advanced concepts',
            sequence_number: 2,
            created_at: '2023-01-01T00:00:00Z'
          },
          transition_reason: 'Good progress on previous lesson',
          progress_update: {
            overall_progress: 40,
            micro_lesson_progress: 100,
            estimated_completion_time: 15
          },
          next_available: true
        };

        mockApi.post.mockResolvedValueOnce({ data: { data: mockResponse } });

        const result = await lessonService.getNextAdaptiveContent('lesson-123', 'ml-1', {
          quiz_scores: [85],
          time_spent: 300,
          engagement_level: 0.8
        });

        expect(mockApi.post).toHaveBeenCalledWith('/api/v1/lessons/adaptive/next-content', {
          lesson_id: 'lesson-123',
          current_micro_lesson_id: 'ml-1',
          user_performance: {
            quiz_scores: [85],
            time_spent: 300,
            engagement_level: 0.8
          }
        });
        expect(result).toEqual(mockResponse);
      });

      test('should get quiz content when adaptive engine decides', async () => {
        const mockResponse: AdaptiveContentResponse = {
          content_type: 'quiz',
          quiz: {
            quiz_id: 'quiz-456',
            lesson_id: 'lesson-123',
            questions: [
              {
                id: 'q1',
                question: 'What is the main concept?',
                options: ['A', 'B', 'C', 'D'],
                correct_answer: 'A'
              }
            ],
            total_questions: 1,
            passing_score: 70,
            difficulty_level: 'intermediate',
            estimated_duration_minutes: 5,
            quiz_metadata: {
              total_questions: 1,
              passing_score: 70,
              difficulty_level: 'intermediate',
              estimated_duration_minutes: 5
            }
          },
          transition_reason: 'Time for knowledge check',
          progress_update: {
            overall_progress: 50,
            micro_lesson_progress: 100,
            estimated_completion_time: 10
          },
          next_available: true
        };

        mockApi.post.mockResolvedValueOnce({ data: { data: mockResponse } });

        const result = await lessonService.getNextAdaptiveContent('lesson-123', 'ml-1', {
          quiz_scores: [],
          time_spent: 600,
          engagement_level: 0.6
        });

        expect(result.content_type).toBe('quiz');
        expect(result.quiz).toBeDefined();
        expect(result.transition_reason).toBe('Time for knowledge check');
      });

      test('should handle errors when getting next content', async () => {
        mockApi.post.mockRejectedValueOnce(new Error('Server error'));

        await expect(lessonService.getNextAdaptiveContent('lesson-123', 'ml-1', {
          quiz_scores: [],
          time_spent: 300,
          engagement_level: 0.8
        })).rejects.toThrow('Failed to load next content');
      });
    });

    describe('updateLearningProgress', () => {
      test('should update learning progress successfully', async () => {
        mockApi.post.mockResolvedValueOnce({ data: { success: true } });

        await lessonService.updateLearningProgress('lesson-123', 'ml-1', {
          quiz_score: 85,
          time_spent: 300,
          engagement_level: 0.8
        });

        expect(mockApi.post).toHaveBeenCalledWith('/api/v1/lessons/adaptive/progress', {
          lesson_id: 'lesson-123',
          micro_lesson_id: 'ml-1',
          progress_data: {
            quiz_score: 85,
            time_spent: 300,
            engagement_level: 0.8
          },
          timestamp: expect.any(String)
        });
      });

      test('should not throw error on progress update failure', async () => {
        mockApi.post.mockRejectedValueOnce(new Error('Network error'));

        // Should not throw error as this is not critical
        await expect(lessonService.updateLearningProgress('lesson-123', 'ml-1', {
          time_spent: 300,
          engagement_level: 0.8
        })).resolves.not.toThrow();
      });
    });

    describe('getAdaptiveLearningState', () => {
      test('should retrieve current adaptive learning state', async () => {
        const mockState: AdaptiveLearningState = {
          current_micro_lesson_id: 'ml-2',
          lesson_id: 'lesson-123',
          progress: 60,
          next_content_type: 'quiz',
          difficulty_adjustment: 1,
          learning_path: ['ml-1', 'ml-2', 'ml-3'],
          completed_micro_lessons: ['ml-1']
        };

        mockApi.get.mockResolvedValueOnce({ data: { data: mockState } });

        const result = await lessonService.getAdaptiveLearningState('lesson-123');

        expect(mockApi.get).toHaveBeenCalledWith('/api/v1/lessons/adaptive/state/lesson-123');
        expect(result).toEqual(mockState);
      });

      test('should return null on error', async () => {
        mockApi.get.mockRejectedValueOnce(new Error('Not found'));

        const result = await lessonService.getAdaptiveLearningState('lesson-123');

        expect(result).toBeNull();
      });
    });
  });

  describe('Quiz Service - Adaptive Integration', () => {
    describe('getImmediateFeedback', () => {
      test('should get immediate feedback for quiz answer', async () => {
        const mockFeedback = {
          is_correct: true,
          feedback_text: 'Excellent! That\'s the correct answer.',
          show_immediate_feedback: true,
          explanation: 'This is correct because...'
        };

        mockApi.post.mockResolvedValueOnce({ data: { data: mockFeedback } });

        const result = await quizService.getImmediateFeedback('quiz-123', 'q1', 'Library');

        expect(mockApi.post).toHaveBeenCalledWith('/api/v1/quiz/immediate-feedback', {
          quiz_id: 'quiz-123',
          question_id: 'q1',
          user_answer: 'Library',
          user_id: 'current'
        });
        expect(result).toEqual(mockFeedback);
      });

      test('should handle feedback errors gracefully', async () => {
        mockApi.post.mockRejectedValueOnce(new Error('Server error'));

        await expect(quizService.getImmediateFeedback('quiz-123', 'q1', 'Answer'))
          .rejects.toThrow('Error getting immediate feedback');
      });
    });

    describe('submitQuestionProgress', () => {
      test('should submit question progress without throwing', async () => {
        mockApi.post.mockResolvedValueOnce({ data: { success: true } });

        await quizService.submitQuestionProgress('quiz-123', 'q1', 45, 2);

        expect(mockApi.post).toHaveBeenCalledWith('/api/v1/quiz/question-progress', {
          quiz_id: 'quiz-123',
          question_id: 'q1',
          time_spent_seconds: 45,
          attempts_count: 2,
          user_id: 'current'
        });
      });

      test('should not throw error on submission failure', async () => {
        mockApi.post.mockRejectedValueOnce(new Error('Network error'));

        // Should not throw as this is not critical
        await expect(quizService.submitQuestionProgress('quiz-123', 'q1', 45, 2))
          .resolves.not.toThrow();
      });
    });
  });

  describe('Micro-lesson Transitions', () => {
    test('should handle smooth transition from lesson to quiz', async () => {
      // First, get next content that returns a quiz
      const quizResponse: AdaptiveContentResponse = {
        content_type: 'quiz',
        quiz: {
          quiz_id: 'quiz-789',
          lesson_id: 'lesson-123',
          questions: [
            {
              id: 'q1',
              question: 'Test question',
              options: ['A', 'B', 'C', 'D'],
              correct_answer: 'A'
            }
          ],
          total_questions: 1,
          passing_score: 70,
          difficulty_level: 'intermediate',
          estimated_duration_minutes: 3,
          quiz_metadata: {
            total_questions: 1,
            passing_score: 70,
            difficulty_level: 'intermediate',
            estimated_duration_minutes: 3
          }
        },
        transition_reason: 'Ready for assessment',
        progress_update: {
          overall_progress: 75,
          micro_lesson_progress: 100,
          estimated_completion_time: 5
        },
        next_available: true
      };

      mockApi.post.mockResolvedValueOnce({ data: { data: quizResponse } });

      const result = await lessonService.getNextAdaptiveContent('lesson-123', 'ml-2', {
        quiz_scores: [80],
        time_spent: 400,
        engagement_level: 0.9
      });

      expect(result.content_type).toBe('quiz');
      expect(result.quiz?.quiz_id).toBe('quiz-789');
      expect(result.progress_update.overall_progress).toBe(75);
    });

    test('should handle transition from quiz back to lesson', async () => {
      // Simulate quiz completion and getting next lesson
      const lessonResponse: AdaptiveContentResponse = {
        content_type: 'micro_lesson',
        micro_lesson: {
          micro_lesson_id: 'ml-3',
          lesson_id: 'lesson-123',
          title: 'Final Concepts',
          summary: 'Wrap up the lesson',
          sequence_number: 3,
          created_at: '2023-01-01T00:00:00Z'
        },
        transition_reason: 'Great quiz performance! Moving to advanced content.',
        progress_update: {
          overall_progress: 90,
          micro_lesson_progress: 0,
          estimated_completion_time: 8
        },
        next_available: true
      };

      mockApi.post.mockResolvedValueOnce({ data: { data: lessonResponse } });

      const result = await lessonService.getNextAdaptiveContent('lesson-123', 'quiz-789', {
        quiz_scores: [90],
        time_spent: 180,
        engagement_level: 0.95
      });

      expect(result.content_type).toBe('micro_lesson');
      expect(result.micro_lesson?.micro_lesson_id).toBe('ml-3');
      expect(result.transition_reason).toContain('Great quiz performance');
    });
  });

  describe('Progress Synchronization', () => {
    test('should sync progress across devices', async () => {
      const mockSyncData = {
        current_position: 2,
        completed_micro_lessons: ['ml-1', 'ml-2'],
        quiz_scores: { 'quiz-1': 85, 'quiz-2': 92 },
        last_updated: '2023-01-01T12:00:00Z'
      };

      mockApi.get.mockResolvedValueOnce({ data: { data: mockSyncData } });

      const result = await lessonService.syncProgressAcrossDevices('lesson-123');

      expect(mockApi.get).toHaveBeenCalledWith('/api/v1/lessons/lesson-123/sync-progress');
      expect(result).toEqual(mockSyncData);
    });

    test('should update progress sync', async () => {
      const progressData = {
        current_position: 3,
        completed_micro_lessons: ['ml-1', 'ml-2', 'ml-3'],
        quiz_scores: { 'quiz-1': 85, 'quiz-2': 92, 'quiz-3': 88 }
      };

      mockApi.post.mockResolvedValueOnce({ data: { success: true } });

      await lessonService.updateProgressSync('lesson-123', progressData);

      expect(mockApi.post).toHaveBeenCalledWith('/api/v1/lessons/lesson-123/sync-progress', {
        progress_data: progressData,
        timestamp: expect.any(String)
      });
    });
  });

  describe('Error Handling and Resilience', () => {
    test('should handle network errors gracefully', async () => {
      mockApi.post.mockRejectedValueOnce(new Error('Network timeout'));

      await expect(lessonService.initializeAdaptiveLearning('lesson-123'))
        .rejects.toThrow('Failed to start adaptive learning session');
    });

    test('should handle malformed responses', async () => {
      mockApi.post.mockResolvedValueOnce({ data: null });

      await expect(lessonService.getNextAdaptiveContent('lesson-123', 'ml-1', {
        quiz_scores: [],
        time_spent: 300,
        engagement_level: 0.8
      })).rejects.toThrow();
    });

    test('should handle server errors with proper error messages', async () => {
      mockApi.post.mockRejectedValueOnce({
        response: {
          status: 500,
          data: { error: 'Internal server error' }
        }
      });

      await expect(lessonService.initializeAdaptiveLearning('lesson-123'))
        .rejects.toThrow('Failed to start adaptive learning session');
    });
  });

  describe('Performance and Optimization', () => {
    test('should not make unnecessary API calls', async () => {
      const mockState: AdaptiveLearningState = {
        current_micro_lesson_id: 'ml-1',
        lesson_id: 'lesson-123',
        progress: 0,
        next_content_type: 'micro_lesson',
        difficulty_adjustment: 0,
        learning_path: ['ml-1'],
        completed_micro_lessons: []
      };

      mockApi.post.mockResolvedValueOnce({ data: { data: mockState } });

      await lessonService.initializeAdaptiveLearning('lesson-123');

      expect(mockApi.post).toHaveBeenCalledTimes(1);
    });

    test('should handle concurrent requests properly', async () => {
      const mockResponse: AdaptiveContentResponse = {
        content_type: 'micro_lesson',
        micro_lesson: {
          micro_lesson_id: 'ml-2',
          lesson_id: 'lesson-123',
          title: 'Next Lesson',
          summary: 'Continue learning',
          sequence_number: 2,
          created_at: '2023-01-01T00:00:00Z'
        },
        transition_reason: 'Continuing sequence',
        progress_update: {
          overall_progress: 50,
          micro_lesson_progress: 100,
          estimated_completion_time: 10
        },
        next_available: true
      };

      mockApi.post.mockResolvedValue({ data: { data: mockResponse } });

      // Make multiple concurrent requests
      const promises = [
        lessonService.getNextAdaptiveContent('lesson-123', 'ml-1', {
          quiz_scores: [],
          time_spent: 300,
          engagement_level: 0.8
        }),
        lessonService.getNextAdaptiveContent('lesson-123', 'ml-1', {
          quiz_scores: [],
          time_spent: 300,
          engagement_level: 0.8
        })
      ];

      const results = await Promise.all(promises);

      expect(results).toHaveLength(2);
      expect(mockApi.post).toHaveBeenCalledTimes(2);
    });
  });
});