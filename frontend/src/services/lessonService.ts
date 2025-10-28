import api from './api';
import { Lesson, MicroLesson, AdaptiveLearningState, AdaptiveContentRequest, AdaptiveContentResponse, UserPreferences } from '../types';
import { cachedApiCall } from '../utils/apiOptimization';

class LessonService {
  async getUserLessons(): Promise<Lesson[]> {
    try {
      return await cachedApiCall<Lesson[]>(
        'lessons:user',
        async () => {
          const response = await api.get('/api/v1/lessons');
          return response.data;
        },
        { ttl: 3 * 60 * 1000 } // Cache for 3 minutes
      );
    } catch (error) {
      console.error('Failed to get user lessons:', error);
      return [];
    }
  }

  async uploadLesson(file: File, onProgress?: (progress: number) => void): Promise<Lesson> {
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await api.post('/api/v1/lessons/upload', formData, {
        // Don't set Content-Type header - let the browser set it automatically with boundary
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            onProgress(progress);
          }
        },
      });
      
      return response.data;
    } catch (error) {
      console.error('Upload error:', error);
      throw new Error('Failed to upload lesson');
    }
  }

  async getMicroLessons(lessonId: string): Promise<MicroLesson[]> {
    try {
      return await cachedApiCall<MicroLesson[]>(
        `lessons:${lessonId}:micro-lessons`,
        async () => {
          const response = await api.get(`/api/v1/lessons/${lessonId}/micro-lessons`);
          return response.data;
        },
        { ttl: 5 * 60 * 1000 } // Cache for 5 minutes
      );
    } catch (error) {
      console.error('Failed to get micro lessons:', error);
      return [];
    }
  }

  async getLesson(lessonId: string): Promise<Lesson | null> {
    try {
      const response = await api.get(`/api/v1/lessons/${lessonId}`);
      return response.data;
    } catch (error) {
      console.error('Failed to get lesson:', error);
      return null;
    }
  }

  // Adaptive Learning Methods
  async initializeAdaptiveLearning(lessonId: string, userPreferences?: UserPreferences): Promise<AdaptiveLearningState> {
    try {
      const response = await api.post('/api/v1/lessons/adaptive/initialize', {
        lesson_id: lessonId,
        user_preferences: userPreferences || {}
      });
      
      return response.data.data;
    } catch (error) {
      console.error('Failed to initialize adaptive learning:', error);
      throw new Error('Failed to start adaptive learning session');
    }
  }

  async getNextAdaptiveContent(
    lessonId: string, 
    currentMicroLessonId: string, 
    userPerformance: {
      quiz_scores: number[];
      time_spent: number;
      engagement_level: number;
    }
  ): Promise<AdaptiveContentResponse> {
    try {
      const request: AdaptiveContentRequest = {
        lesson_id: lessonId,
        current_micro_lesson_id: currentMicroLessonId,
        user_performance: userPerformance
      };

      const response = await api.post('/api/v1/lessons/adaptive/next-content', request);
      return response.data.data;
    } catch (error) {
      console.error('Failed to get next adaptive content:', error);
      throw new Error('Failed to load next content');
    }
  }

  async updateLearningProgress(
    lessonId: string, 
    microLessonId: string, 
    progressData: {
      quiz_score?: number;
      time_spent: number;
      engagement_level: number;
    }
  ): Promise<void> {
    try {
      await api.post('/api/v1/lessons/adaptive/progress', {
        lesson_id: lessonId,
        micro_lesson_id: microLessonId,
        progress_data: progressData,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error('Failed to update learning progress:', error);
      // Don't throw error as this is not critical for user experience
    }
  }

  async getAdaptiveLearningState(lessonId: string): Promise<AdaptiveLearningState | null> {
    try {
      const response = await api.get(`/api/v1/lessons/adaptive/state/${lessonId}`);
      return response.data.data;
    } catch (error) {
      console.error('Failed to get adaptive learning state:', error);
      return null;
    }
  }

  async resetAdaptiveLearning(lessonId: string): Promise<AdaptiveLearningState> {
    try {
      const response = await api.post('/api/v1/lessons/adaptive/reset', {
        lesson_id: lessonId
      });
      
      return response.data.data;
    } catch (error) {
      console.error('Failed to reset adaptive learning:', error);
      throw new Error('Failed to reset learning session');
    }
  }

  // Content Type Support
  async getContentByType(lessonId: string, contentType: 'text' | 'audio' | 'video'): Promise<any> {
    try {
      const response = await api.get(`/api/v1/lessons/${lessonId}/content/${contentType}`);
      return response.data.data;
    } catch (error) {
      console.error(`Failed to get ${contentType} content:`, error);
      throw new Error(`Failed to load ${contentType} content`);
    }
  }

  async generateMultiModalContent(
    lessonId: string, 
    contentType: 'audio' | 'video',
    preferences?: {
      voice_preference?: string;
      visual_style?: string;
      include_subtitles?: boolean;
    }
  ): Promise<{ generation_id: string; estimated_time: number }> {
    try {
      const response = await api.post(`/api/v1/lessons/${lessonId}/generate/${contentType}`, {
        preferences: preferences || {}
      });
      
      return response.data.data;
    } catch (error) {
      console.error(`Failed to generate ${contentType} content:`, error);
      throw new Error(`Failed to generate ${contentType} content`);
    }
  }

  async getGenerationStatus(lessonId: string, generationId: string): Promise<{
    status: 'pending' | 'processing' | 'completed' | 'failed';
    progress: number;
    estimated_completion: string;
    result_url?: string;
  }> {
    try {
      const response = await api.get(`/api/v1/lessons/${lessonId}/generation/${generationId}/status`);
      return response.data.data;
    } catch (error) {
      console.error('Failed to get generation status:', error);
      throw new Error('Failed to check generation status');
    }
  }

  // Progress Synchronization
  async syncProgressAcrossDevices(lessonId: string): Promise<{
    current_position: number;
    completed_micro_lessons: string[];
    quiz_scores: Record<string, number>;
    last_updated: string;
  }> {
    try {
      const response = await api.get(`/api/v1/lessons/${lessonId}/sync-progress`);
      return response.data.data;
    } catch (error) {
      console.error('Failed to sync progress:', error);
      throw new Error('Failed to synchronize progress');
    }
  }

  async updateProgressSync(
    lessonId: string,
    progressData: {
      current_position: number;
      completed_micro_lessons: string[];
      quiz_scores: Record<string, number>;
    }
  ): Promise<void> {
    try {
      await api.post(`/api/v1/lessons/${lessonId}/sync-progress`, {
        progress_data: progressData,
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error('Failed to update progress sync:', error);
      // Don't throw error as this is not critical
    }
  }

  // Original File Access
  async getOriginalFileUrl(lessonId: string): Promise<string> {
    try {
      const token = localStorage.getItem('auth_token');
      const baseUrl = api.defaults.baseURL || '';
      return `${baseUrl}/api/v1/lessons/${lessonId}/original-file?token=${token}`;
    } catch (error) {
      console.error('Failed to get original file URL:', error);
      throw new Error('Failed to get original file');
    }
  }

  async viewOriginalFile(lessonId: string): Promise<void> {
    try {
      const url = await this.getOriginalFileUrl(lessonId);
      window.open(url, '_blank');
    } catch (error) {
      console.error('Failed to view original file:', error);
      throw error;
    }
  }
}

export const lessonService = new LessonService();