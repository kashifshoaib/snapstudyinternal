import api from './api';

export interface ProcessingStatus {
  lesson_id: string;
  status: 'processing' | 'completed' | 'failed';
  progress_percentage: number;
  stage: string;
  estimated_completion_time?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface ProcessingProgressCallback {
  (status: ProcessingStatus): void;
}

class ProcessingService {
  private pollingIntervals: Map<string, NodeJS.Timeout> = new Map();
  private readonly POLLING_INTERVAL = 2000; // 2 seconds as per requirements

  /**
   * Start polling for processing status of a specific lesson
   */
  async startPolling(
    lessonId: string, 
    onProgress: ProcessingProgressCallback,
    onComplete?: (status: ProcessingStatus) => void,
    onError?: (error: string) => void
  ): Promise<void> {
    // Clear any existing polling for this lesson
    this.stopPolling(lessonId);

    const poll = async () => {
      try {
        const status = await this.getProcessingStatus(lessonId);
        
        // Call progress callback
        onProgress(status);

        // Check if processing is complete
        if (status.status === 'completed') {
          this.stopPolling(lessonId);
          onComplete?.(status);
        } else if (status.status === 'failed') {
          this.stopPolling(lessonId);
          onError?.(status.error_message || 'Processing failed');
        }
        // Continue polling if still processing
      } catch (error) {
        console.error('Error polling processing status:', error);
        this.stopPolling(lessonId);
        onError?.(error instanceof Error ? error.message : 'Failed to check processing status');
      }
    };

    // Start immediate poll and then set interval
    await poll();
    
    if (!this.pollingIntervals.has(lessonId)) {
      const intervalId = setInterval(poll, this.POLLING_INTERVAL);
      this.pollingIntervals.set(lessonId, intervalId);
    }
  }

  /**
   * Stop polling for a specific lesson
   */
  stopPolling(lessonId: string): void {
    const intervalId = this.pollingIntervals.get(lessonId);
    if (intervalId) {
      clearInterval(intervalId);
      this.pollingIntervals.delete(lessonId);
    }
  }

  /**
   * Stop all active polling
   */
  stopAllPolling(): void {
    this.pollingIntervals.forEach((intervalId) => {
      clearInterval(intervalId);
    });
    this.pollingIntervals.clear();
  }

  /**
   * Get current processing status for a lesson
   */
  async getProcessingStatus(lessonId: string): Promise<ProcessingStatus> {
    try {
      const response = await api.get(`/api/v1/lessons/${lessonId}/processing-status`);
      return response.data;
    } catch (error) {
      console.error('Failed to get processing status:', error);
      throw new Error('Failed to get processing status');
    }
  }

  /**
   * Get processing status for multiple lessons
   */
  async getBatchProcessingStatus(lessonIds: string[]): Promise<ProcessingStatus[]> {
    try {
      const response = await api.post('/api/v1/lessons/batch-processing-status', {
        lesson_ids: lessonIds
      });
      return response.data;
    } catch (error) {
      console.error('Failed to get batch processing status:', error);
      throw new Error('Failed to get batch processing status');
    }
  }

  /**
   * Check if a lesson is currently being polled
   */
  isPolling(lessonId: string): boolean {
    return this.pollingIntervals.has(lessonId);
  }

  /**
   * Get all currently polling lesson IDs
   */
  getPollingLessons(): string[] {
    return Array.from(this.pollingIntervals.keys());
  }
}

export const processingService = new ProcessingService();

// Cleanup on page unload
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    processingService.stopAllPolling();
  });
}