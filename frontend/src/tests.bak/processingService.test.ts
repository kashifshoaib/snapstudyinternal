/**
 * Processing Service Tests
 * 
 * Tests for the processing status polling service functionality
 */

import { processingService, ProcessingStatus } from '../services/processingService';

// Mock axios
jest.mock('../services/api', () => ({
  get: jest.fn(),
  post: jest.fn(),
}));

import api from '../services/api';
const mockApi = api as jest.Mocked<typeof api>;

describe('Processing Service', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    processingService.stopAllPolling();
    jest.clearAllTimers();
    jest.useFakeTimers();
  });

  afterEach(() => {
    processingService.stopAllPolling();
    jest.useRealTimers();
  });

  describe('getProcessingStatus', () => {
    test('should fetch processing status for a lesson', async () => {
      const mockStatus: ProcessingStatus = {
        lesson_id: 'lesson-123',
        status: 'processing',
        progress_percentage: 45,
        stage: 'analyzing',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:05:00Z'
      };

      mockApi.get.mockResolvedValueOnce({ data: mockStatus });

      const result = await processingService.getProcessingStatus('lesson-123');

      expect(mockApi.get).toHaveBeenCalledWith('/api/v1/lessons/lesson-123/processing-status');
      expect(result).toEqual(mockStatus);
    });

    test('should handle API errors when fetching status', async () => {
      mockApi.get.mockRejectedValueOnce(new Error('Network error'));

      await expect(processingService.getProcessingStatus('lesson-123'))
        .rejects.toThrow('Failed to get processing status');
    });
  });

  describe('getBatchProcessingStatus', () => {
    test('should fetch status for multiple lessons', async () => {
      const mockStatuses: ProcessingStatus[] = [
        {
          lesson_id: 'lesson-1',
          status: 'completed',
          progress_percentage: 100,
          stage: 'completed',
          created_at: '2023-01-01T00:00:00Z',
          updated_at: '2023-01-01T00:10:00Z'
        },
        {
          lesson_id: 'lesson-2',
          status: 'processing',
          progress_percentage: 30,
          stage: 'parsing',
          created_at: '2023-01-01T00:05:00Z',
          updated_at: '2023-01-01T00:07:00Z'
        }
      ];

      mockApi.post.mockResolvedValueOnce({ data: mockStatuses });

      const result = await processingService.getBatchProcessingStatus(['lesson-1', 'lesson-2']);

      expect(mockApi.post).toHaveBeenCalledWith('/api/v1/lessons/batch-processing-status', {
        lesson_ids: ['lesson-1', 'lesson-2']
      });
      expect(result).toEqual(mockStatuses);
    });
  });

  describe('startPolling', () => {
    test('should start polling and call progress callback', async () => {
      const mockStatus: ProcessingStatus = {
        lesson_id: 'lesson-123',
        status: 'processing',
        progress_percentage: 50,
        stage: 'generating',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:05:00Z'
      };

      mockApi.get.mockResolvedValue({ data: mockStatus });

      const onProgress = jest.fn();
      const onComplete = jest.fn();
      const onError = jest.fn();

      await processingService.startPolling('lesson-123', onProgress, onComplete, onError);

      expect(mockApi.get).toHaveBeenCalledWith('/api/v1/lessons/lesson-123/processing-status');
      expect(onProgress).toHaveBeenCalledWith(mockStatus);
      expect(processingService.isPolling('lesson-123')).toBe(true);
    });

    test('should call onComplete when processing is finished', async () => {
      const completedStatus: ProcessingStatus = {
        lesson_id: 'lesson-123',
        status: 'completed',
        progress_percentage: 100,
        stage: 'completed',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:10:00Z'
      };

      mockApi.get.mockResolvedValue({ data: completedStatus });

      const onProgress = jest.fn();
      const onComplete = jest.fn();
      const onError = jest.fn();

      await processingService.startPolling('lesson-123', onProgress, onComplete, onError);

      expect(onProgress).toHaveBeenCalledWith(completedStatus);
      expect(onComplete).toHaveBeenCalledWith(completedStatus);
      expect(processingService.isPolling('lesson-123')).toBe(false);
    });

    test('should call onError when processing fails', async () => {
      const failedStatus: ProcessingStatus = {
        lesson_id: 'lesson-123',
        status: 'failed',
        progress_percentage: 0,
        stage: 'failed',
        error_message: 'Processing failed due to invalid content',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:05:00Z'
      };

      mockApi.get.mockResolvedValue({ data: failedStatus });

      const onProgress = jest.fn();
      const onComplete = jest.fn();
      const onError = jest.fn();

      await processingService.startPolling('lesson-123', onProgress, onComplete, onError);

      expect(onProgress).toHaveBeenCalledWith(failedStatus);
      expect(onError).toHaveBeenCalledWith('Processing failed due to invalid content');
      expect(processingService.isPolling('lesson-123')).toBe(false);
    });

    test('should handle API errors during polling', async () => {
      mockApi.get.mockRejectedValue(new Error('Network error'));

      const onProgress = jest.fn();
      const onComplete = jest.fn();
      const onError = jest.fn();

      await processingService.startPolling('lesson-123', onProgress, onComplete, onError);

      expect(onError).toHaveBeenCalledWith('Network error');
      expect(processingService.isPolling('lesson-123')).toBe(false);
    });

    test('should continue polling while processing', async () => {
      const processingStatus: ProcessingStatus = {
        lesson_id: 'lesson-123',
        status: 'processing',
        progress_percentage: 25,
        stage: 'parsing',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:02:00Z'
      };

      mockApi.get.mockResolvedValue({ data: processingStatus });

      const onProgress = jest.fn();
      const onComplete = jest.fn();
      const onError = jest.fn();

      await processingService.startPolling('lesson-123', onProgress, onComplete, onError);

      // Verify initial call
      expect(onProgress).toHaveBeenCalledWith(processingStatus);
      expect(processingService.isPolling('lesson-123')).toBe(true);

      // Advance timer to trigger next poll
      jest.advanceTimersByTime(2000);

      // Should still be polling since status is 'processing'
      expect(processingService.isPolling('lesson-123')).toBe(true);
    });
  });

  describe('stopPolling', () => {
    test('should stop polling for a specific lesson', async () => {
      const mockStatus: ProcessingStatus = {
        lesson_id: 'lesson-123',
        status: 'processing',
        progress_percentage: 50,
        stage: 'generating',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:05:00Z'
      };

      mockApi.get.mockResolvedValue({ data: mockStatus });

      const onProgress = jest.fn();
      await processingService.startPolling('lesson-123', onProgress);

      expect(processingService.isPolling('lesson-123')).toBe(true);

      processingService.stopPolling('lesson-123');

      expect(processingService.isPolling('lesson-123')).toBe(false);
    });

    test('should handle stopping non-existent polling', () => {
      expect(() => {
        processingService.stopPolling('non-existent-lesson');
      }).not.toThrow();
    });
  });

  describe('stopAllPolling', () => {
    test('should stop all active polling', async () => {
      const mockStatus: ProcessingStatus = {
        lesson_id: 'lesson-123',
        status: 'processing',
        progress_percentage: 50,
        stage: 'generating',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:05:00Z'
      };

      mockApi.get.mockResolvedValue({ data: mockStatus });

      const onProgress = jest.fn();
      await processingService.startPolling('lesson-1', onProgress);
      await processingService.startPolling('lesson-2', onProgress);

      expect(processingService.getPollingLessons()).toHaveLength(2);

      processingService.stopAllPolling();

      expect(processingService.getPollingLessons()).toHaveLength(0);
    });
  });

  describe('utility methods', () => {
    test('should track polling lessons correctly', async () => {
      const mockStatus: ProcessingStatus = {
        lesson_id: 'lesson-123',
        status: 'processing',
        progress_percentage: 50,
        stage: 'generating',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:05:00Z'
      };

      mockApi.get.mockResolvedValue({ data: mockStatus });

      const onProgress = jest.fn();
      await processingService.startPolling('lesson-1', onProgress);
      await processingService.startPolling('lesson-2', onProgress);

      expect(processingService.isPolling('lesson-1')).toBe(true);
      expect(processingService.isPolling('lesson-2')).toBe(true);
      expect(processingService.isPolling('lesson-3')).toBe(false);

      const pollingLessons = processingService.getPollingLessons();
      expect(pollingLessons).toContain('lesson-1');
      expect(pollingLessons).toContain('lesson-2');
      expect(pollingLessons).toHaveLength(2);
    });
  });
});