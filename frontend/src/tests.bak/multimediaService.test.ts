/**
 * MultimediaService Tests
 * 
 * Tests for multimedia service API integration including content generation,
 * status tracking, and multimedia library functionality
 */

import multimediaService from '../services/multimediaService';
import api from '../services/api';
import { AudioLesson, VideoLesson, GenerationStatus } from '../types';

// Mock the API service
jest.mock('../services/api');
const mockApi = api as jest.Mocked<typeof api>;

describe('MultimediaService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Audio Generation', () => {
    const mockAudioLesson: AudioLesson = {
      audio_lesson_id: 'audio-123',
      text_lesson_id: 'lesson-123',
      title: 'Test Audio Lesson',
      audio_url: 'https://example.com/audio.mp3',
      duration_seconds: 300,
      file_size_bytes: 5000000,
      voice_profile: {
        VoiceId: 'professional_female',
        Engine: 'neural',
        LanguageCode: 'en-US'
      },
      learning_adaptations: {},
      transcript: 'This is a test transcript',
      key_timestamps: [
        {
          time_seconds: 30,
          concept: 'Introduction',
          type: 'concept'
        }
      ],
      generated_at: '2024-01-01T00:00:00Z',
      format: 'mp3',
      sample_rate: '44100'
    };

    it('should generate audio lesson with default preferences', async () => {
      (mockApi.post as jest.Mock).mockResolvedValue({ data: { audio_lesson: mockAudioLesson } });

      const result = await multimediaService.generateAudioLesson('lesson-123');

      expect(mockApi.post).toHaveBeenCalledWith('/api/v1/multimedia/generate-audio', {
        text_lesson_id: 'lesson-123',
        voice_preference: 'professional_female',
        tone_preference: 'professional',
        speaking_rate: 'medium',
        audio_volume: 'medium'
      });
      expect(result).toEqual(mockAudioLesson);
    });

    it('should generate audio lesson with custom preferences', async () => {
      (mockApi.post as jest.Mock).mockResolvedValue({ data: { audio_lesson: mockAudioLesson } });

      const preferences = {
        voice_preference: 'friendly_male',
        tone_preference: 'friendly',
        speaking_rate: 'fast',
        audio_volume: 'high'
      };

      await multimediaService.generateAudioLesson('lesson-123', preferences);

      expect(mockApi.post).toHaveBeenCalledWith('/api/v1/multimedia/generate-audio', {
        text_lesson_id: 'lesson-123',
        voice_preference: 'friendly_male',
        tone_preference: 'friendly',
        speaking_rate: 'fast',
        audio_volume: 'high'
      });
    });

    it('should handle audio generation errors', async () => {
      (mockApi.post as jest.Mock).mockRejectedValue(new Error('API Error'));

      await expect(multimediaService.generateAudioLesson('lesson-123'))
        .rejects.toThrow('Failed to generate audio lesson. Please try again.');
    });

    it('should fetch audio lesson by ID', async () => {
      (mockApi.get as jest.Mock).mockResolvedValue({ data: { audio_lesson: mockAudioLesson } });

      const result = await multimediaService.getAudioLesson('audio-123');

      expect(mockApi.get).toHaveBeenCalledWith('/api/v1/multimedia/audio-lesson/audio-123');
      expect(result).toEqual(mockAudioLesson);
    });
  });

  describe('Video Generation', () => {
    const mockVideoLesson: VideoLesson = {
      video_lesson_id: 'video-123',
      text_lesson_id: 'lesson-123',
      title: 'Test Video Lesson',
      video_url: 'https://example.com/video.mp4',
      duration_seconds: 600,
      file_size_bytes: 50000000,
      resolution: '1080p',
      frame_rate: 30,
      visual_style: {
        style: 'educational',
        color_scheme: 'warm',
        background: 'gradient',
        typography: 'modern'
      },
      learning_adaptations: {},
      script: {},
      scenes: ['intro', 'main_content', 'conclusion'],
      narration_metadata: {},
      key_timestamps: [
        {
          time_seconds: 60,
          concept: 'Key Concept',
          type: 'concept'
        }
      ],
      interactive_elements: [
        {
          type: 'quiz',
          time_seconds: 120,
          title: 'Quick Check',
          description: 'Test your understanding'
        }
      ],
      generated_at: '2024-01-01T00:00:00Z',
      format: 'mp4'
    };

    it('should generate video lesson with default preferences', async () => {
      (mockApi.post as jest.Mock).mockResolvedValue({ data: { video_lesson: mockVideoLesson } });

      const result = await multimediaService.generateVideoLesson('lesson-123');

      expect(mockApi.post).toHaveBeenCalledWith('/api/v1/multimedia/generate-video', {
        text_lesson_id: 'lesson-123',
        visual_style: 'educational',
        include_narration: true,
        include_subtitles: true,
        video_quality: 'hd'
      });
      expect(result).toEqual(mockVideoLesson);
    });

    it('should generate video lesson with custom preferences', async () => {
      (mockApi.post as jest.Mock).mockResolvedValue({ data: { video_lesson: mockVideoLesson } });

      const preferences = {
        visual_style: 'technical',
        include_narration: false,
        include_subtitles: false,
        video_quality: 'sd'
      };

      await multimediaService.generateVideoLesson('lesson-123', preferences);

      expect(mockApi.post).toHaveBeenCalledWith('/api/v1/multimedia/generate-video', {
        text_lesson_id: 'lesson-123',
        visual_style: 'technical',
        include_narration: false,
        include_subtitles: false,
        video_quality: 'sd'
      });
    });

    it('should handle video generation errors', async () => {
      (mockApi.post as jest.Mock).mockRejectedValue(new Error('API Error'));

      await expect(multimediaService.generateVideoLesson('lesson-123'))
        .rejects.toThrow('Failed to generate video lesson. Please try again.');
    });

    it('should fetch video lesson by ID', async () => {
      (mockApi.get as jest.Mock).mockResolvedValue({ data: { video_lesson: mockVideoLesson } });

      const result = await multimediaService.getVideoLesson('video-123');

      expect(mockApi.get).toHaveBeenCalledWith('/api/v1/multimedia/video-lesson/video-123');
      expect(result).toEqual(mockVideoLesson);
    });
  });

  describe('Multi-Modal Generation', () => {
    it('should generate multi-modal content', async () => {
      const mockResponse = {
        audio_lesson: { audio_lesson_id: 'audio-123' },
        video_lesson: { video_lesson_id: 'video-123' }
      };
      (mockApi.post as jest.Mock).mockResolvedValue({ data: mockResponse });

      const result = await multimediaService.generateMultiModalLesson(
        'Test lesson content',
        ['text', 'audio', 'video'],
        { voice_preference: 'professional_female' }
      );

      expect(mockApi.post).toHaveBeenCalledWith('/api/v1/multimedia/generate-multimodal', {
        lesson_content: 'Test lesson content',
        content_types: ['text', 'audio', 'video'],
        user_preferences: { voice_preference: 'professional_female' }
      });
      expect(result).toEqual(mockResponse);
    });

    it('should handle multi-modal generation errors', async () => {
      (mockApi.post as jest.Mock).mockRejectedValue(new Error('API Error'));

      await expect(multimediaService.generateMultiModalLesson('content'))
        .rejects.toThrow('Failed to generate multi-modal lesson. Please try again.');
    });
  });

  describe('Generation Status Tracking', () => {
    const mockGenerationStatus: GenerationStatus = {
      lesson_id: 'lesson-123',
      text_lesson: {
        status: 'completed',
        available: true
      },
      audio_lesson: {
        status: 'generating',
        available: false,
        audio_lesson_id: 'audio-123'
      },
      video_lesson: {
        status: 'pending',
        available: false
      },
      generation_options: {
        can_generate_audio: true,
        can_generate_video: true,
        estimated_audio_time: '2-5 minutes',
        estimated_video_time: '5-15 minutes'
      }
    };

    it('should fetch generation status', async () => {
      (mockApi.get as jest.Mock).mockResolvedValue({ data: mockGenerationStatus });

      const result = await multimediaService.getGenerationStatus('lesson-123');

      expect(mockApi.get).toHaveBeenCalledWith('/api/v1/multimedia/generation-status/lesson-123');
      expect(result).toEqual(mockGenerationStatus);
    });

    it('should handle generation status errors', async () => {
      (mockApi.get as jest.Mock).mockRejectedValue(new Error('API Error'));

      await expect(multimediaService.getGenerationStatus('lesson-123'))
        .rejects.toThrow('Failed to check generation status.');
    });
  });

  describe('Multimedia Library', () => {
    const mockLibrary = {
      audio: {
        count: 2,
        lessons: [
          { audio_lesson_id: 'audio-1', title: 'Audio Lesson 1' },
          { audio_lesson_id: 'audio-2', title: 'Audio Lesson 2' }
        ]
      },
      video: {
        count: 1,
        lessons: [
          { video_lesson_id: 'video-1', title: 'Video Lesson 1' }
        ]
      },
      total_multimedia_lessons: 3
    };

    it('should fetch user multimedia lessons', async () => {
      (mockApi.get as jest.Mock).mockResolvedValue({ data: { multimedia_lessons: mockLibrary } });

      const result = await multimediaService.getUserMultimediaLessons();

      expect(mockApi.get).toHaveBeenCalledWith('/api/v1/multimedia/user-multimedia-lessons');
      expect(result).toEqual(mockLibrary);
    });

    it('should handle library fetch errors', async () => {
      (mockApi.get as jest.Mock).mockRejectedValue(new Error('API Error'));

      await expect(multimediaService.getUserMultimediaLessons())
        .rejects.toThrow('Failed to load multimedia library.');
    });
  });

  describe('Analytics Tracking', () => {
    it('should track multimedia events', async () => {
      (mockApi.post as jest.Mock).mockResolvedValue({ data: { success: true } });

      await multimediaService.trackMultimediaEvent(
        'audio_played',
        'audio-123',
        { current_time: 30 }
      );

      expect(mockApi.post).toHaveBeenCalledWith('/api/v1/analytics/events', {
        event_type: 'audio_played',
        event_data: {
          multimedia_id: 'audio-123',
          current_time: 30
        }
      });
    });

    it('should not throw errors for analytics tracking failures', async () => {
      (mockApi.post as jest.Mock).mockRejectedValue(new Error('API Error'));

      // Should not throw
      await expect(multimediaService.trackMultimediaEvent('audio_played', 'audio-123'))
        .resolves.toBeUndefined();
    });
  });

  describe('Configuration Methods', () => {
    it('should return voice profiles', () => {
      const profiles = multimediaService.getVoiceProfiles();
      
      expect(profiles).toHaveLength(6);
      expect(profiles[0]).toEqual({
        id: 'professional_female',
        name: 'Professional Female',
        description: 'Clear, professional female voice'
      });
    });

    it('should return visual styles', () => {
      const styles = multimediaService.getVisualStyles();
      
      expect(styles).toHaveLength(4);
      expect(styles[0]).toEqual({
        id: 'professional',
        name: 'Professional',
        description: 'Clean, corporate style with professional colors'
      });
    });

    it('should return estimated generation times', () => {
      const times = multimediaService.getEstimatedGenerationTimes();
      
      expect(times).toEqual({
        audio: '2-5 minutes',
        video: '5-15 minutes'
      });
    });
  });

  describe('Service Availability', () => {
    it('should check multimedia availability when healthy', async () => {
      (mockApi.get as jest.Mock).mockResolvedValue({ data: { status: 'healthy' } });

      const result = await multimediaService.checkMultimediaAvailability();

      expect(mockApi.get).toHaveBeenCalledWith('/health');
      expect(result).toEqual({
        audio: true,
        video: true
      });
    });

    it('should handle availability check errors', async () => {
      (mockApi.get as jest.Mock).mockRejectedValue(new Error('Service unavailable'));

      const result = await multimediaService.checkMultimediaAvailability();

      expect(result).toEqual({
        audio: false,
        video: false
      });
    });
  });
});