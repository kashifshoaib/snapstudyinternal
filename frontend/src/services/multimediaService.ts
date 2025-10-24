import api from './api';
import { AudioLesson, VideoLesson, MultimediaPreferences, GenerationStatus } from '../types';

interface AudioGenerationRequest {
  text_lesson_id: string;
  voice_preference?: string;
  tone_preference?: string;
  speaking_rate?: string;
  audio_volume?: string;
}

interface VideoGenerationRequest {
  text_lesson_id: string;
  visual_style?: string;
  include_narration?: boolean;
  include_subtitles?: boolean;
  video_quality?: string;
}

interface MultiModalGenerationRequest {
  lesson_content: string;
  content_types: string[];
  user_preferences?: Record<string, any>;
}

interface MultimediaLibrary {
  audio: {
    count: number;
    lessons: AudioLesson[];
  };
  video: {
    count: number;
    lessons: VideoLesson[];
  };
  total_multimedia_lessons: number;
}

class MultimediaService {
  /**
   * Generate audio lesson from existing text lesson
   */
  async generateAudioLesson(
    textLessonId: string,
    preferences: Partial<AudioGenerationRequest> = {}
  ): Promise<AudioLesson> {
    try {
      const response = await api.post('/api/v1/multimedia/generate-audio', {
        text_lesson_id: textLessonId,
        voice_preference: preferences.voice_preference || 'professional_female',
        tone_preference: preferences.tone_preference || 'professional',
        speaking_rate: preferences.speaking_rate || 'medium',
        audio_volume: preferences.audio_volume || 'medium'
      });

      return response.data.audio_lesson;
    } catch (error) {
      console.error('Error generating audio lesson:', error);
      throw new Error('Failed to generate audio lesson. Please try again.');
    }
  }

  /**
   * Generate video lesson from existing text lesson
   */
  async generateVideoLesson(
    textLessonId: string,
    preferences: Partial<VideoGenerationRequest> = {}
  ): Promise<VideoLesson> {
    try {
      const response = await api.post('/api/v1/multimedia/generate-video', {
        text_lesson_id: textLessonId,
        visual_style: preferences.visual_style || 'educational',
        include_narration: preferences.include_narration !== false,
        include_subtitles: preferences.include_subtitles !== false,
        video_quality: preferences.video_quality || 'hd'
      });

      return response.data.video_lesson;
    } catch (error) {
      console.error('Error generating video lesson:', error);
      throw new Error('Failed to generate video lesson. Please try again.');
    }
  }

  /**
   * Generate multiple content formats simultaneously
   */
  async generateMultiModalLesson(
    lessonContent: string,
    contentTypes: string[] = ['text', 'audio'],
    userPreferences: Record<string, any> = {}
  ): Promise<any> {
    try {
      const response = await api.post('/api/v1/multimedia/generate-multimodal', {
        lesson_content: lessonContent,
        content_types: contentTypes,
        user_preferences: userPreferences
      });

      return response.data;
    } catch (error) {
      console.error('Error generating multi-modal lesson:', error);
      throw new Error('Failed to generate multi-modal lesson. Please try again.');
    }
  }

  /**
   * Get audio lesson details and playback URL
   */
  async getAudioLesson(audioLessonId: string): Promise<AudioLesson> {
    try {
      const response = await api.get(`/api/v1/multimedia/audio-lesson/${audioLessonId}`);
      return response.data.audio_lesson;
    } catch (error) {
      console.error('Error fetching audio lesson:', error);
      throw new Error('Failed to load audio lesson.');
    }
  }

  /**
   * Get video lesson details and playback URL
   */
  async getVideoLesson(videoLessonId: string): Promise<VideoLesson> {
    try {
      const response = await api.get(`/api/v1/multimedia/video-lesson/${videoLessonId}`);
      return response.data.video_lesson;
    } catch (error) {
      console.error('Error fetching video lesson:', error);
      throw new Error('Failed to load video lesson.');
    }
  }

  /**
   * Get all multimedia lessons for current user
   */
  async getUserMultimediaLessons(): Promise<MultimediaLibrary> {
    try {
      const response = await api.get('/api/v1/multimedia/user-multimedia-lessons');
      return response.data.multimedia_lessons;
    } catch (error) {
      console.error('Error fetching user multimedia lessons:', error);
      throw new Error('Failed to load multimedia library.');
    }
  }

  /**
   * Get generation status for a lesson
   */
  async getGenerationStatus(lessonId: string): Promise<GenerationStatus> {
    try {
      const response = await api.get(`/api/v1/multimedia/generation-status/${lessonId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching generation status:', error);
      throw new Error('Failed to check generation status.');
    }
  }

  /**
   * Track multimedia engagement events
   */
  async trackMultimediaEvent(
    eventType: string,
    multimediaId: string,
    eventData: Record<string, any> = {}
  ): Promise<void> {
    try {
      await api.post('/api/v1/analytics/events', {
        event_type: eventType,
        event_data: {
          multimedia_id: multimediaId,
          ...eventData
        }
      });
    } catch (error) {
      console.error('Error tracking multimedia event:', error);
      // Don't throw error for analytics tracking
    }
  }

  /**
   * Get available voice profiles for audio generation
   */
  getVoiceProfiles(): Array<{ id: string; name: string; description: string }> {
    return [
      { id: 'professional_female', name: 'Professional Female', description: 'Clear, professional female voice' },
      { id: 'professional_male', name: 'Professional Male', description: 'Clear, professional male voice' },
      { id: 'friendly_female', name: 'Friendly Female', description: 'Warm, approachable female voice' },
      { id: 'friendly_male', name: 'Friendly Male', description: 'Warm, approachable male voice' },
      { id: 'authoritative_female', name: 'Authoritative Female', description: 'Confident, authoritative female voice' },
      { id: 'authoritative_male', name: 'Authoritative Male', description: 'Confident, authoritative male voice' }
    ];
  }

  /**
   * Get available visual styles for video generation
   */
  getVisualStyles(): Array<{ id: string; name: string; description: string }> {
    return [
      { id: 'professional', name: 'Professional', description: 'Clean, corporate style with professional colors' },
      { id: 'educational', name: 'Educational', description: 'Friendly, classroom-style with warm colors' },
      { id: 'technical', name: 'Technical', description: 'Modern, high-tech style with dark themes' },
      { id: 'creative', name: 'Creative', description: 'Dynamic, artistic style with vibrant colors' }
    ];
  }

  /**
   * Get estimated generation times
   */
  getEstimatedGenerationTimes(): { audio: string; video: string } {
    return {
      audio: '2-5 minutes',
      video: '5-15 minutes'
    };
  }

  /**
   * Check if multimedia generation is available
   */
  async checkMultimediaAvailability(): Promise<{ audio: boolean; video: boolean }> {
    try {
      const response = await api.get('/health');
      // In a real implementation, this would check service availability
      return {
        audio: true,
        video: true
      };
    } catch (error) {
      console.error('Error checking multimedia availability:', error);
      return {
        audio: false,
        video: false
      };
    }
  }
}

export const multimediaService = new MultimediaService();
export default multimediaService;