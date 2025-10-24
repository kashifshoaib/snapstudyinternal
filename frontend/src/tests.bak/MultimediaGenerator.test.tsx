/**
 * MultimediaGenerator Component Tests
 * 
 * Tests for MultimediaGenerator component including content generation,
 * preference selection, and status tracking functionality
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import MultimediaGenerator from '../components/MultimediaGenerator';
import multimediaService from '../services/multimediaService';
import { GenerationStatus } from '../types';

// Mock the multimedia service
jest.mock('../services/multimediaService', () => ({
  getGenerationStatus: jest.fn(),
  getVoiceProfiles: jest.fn(),
  getVisualStyles: jest.fn(),
  getEstimatedGenerationTimes: jest.fn(),
  generateAudioLesson: jest.fn(),
  generateVideoLesson: jest.fn()
}));

const mockMultimediaService = multimediaService as jest.Mocked<typeof multimediaService>;

describe('MultimediaGenerator', () => {
  const mockGenerationStatus: GenerationStatus = {
    lesson_id: 'lesson-123',
    text_lesson: {
      status: 'completed',
      available: true
    },
    audio_lesson: {
      status: 'not_generated',
      available: false
    },
    video_lesson: {
      status: 'not_generated',
      available: false
    },
    generation_options: {
      can_generate_audio: true,
      can_generate_video: true,
      estimated_audio_time: '2-5 minutes',
      estimated_video_time: '5-15 minutes'
    }
  };

  const mockVoiceProfiles = [
    { id: 'professional_female', name: 'Professional Female', description: 'Clear, professional female voice' },
    { id: 'friendly_male', name: 'Friendly Male', description: 'Warm, approachable male voice' }
  ];

  const mockVisualStyles = [
    { id: 'educational', name: 'Educational', description: 'Friendly, classroom-style with warm colors' },
    { id: 'technical', name: 'Technical', description: 'Modern, high-tech style with dark themes' }
  ];

  const mockEstimatedTimes = {
    audio: '2-5 minutes',
    video: '5-15 minutes'
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockMultimediaService.getGenerationStatus.mockResolvedValue(mockGenerationStatus);
    mockMultimediaService.getVoiceProfiles.mockReturnValue(mockVoiceProfiles);
    mockMultimediaService.getVisualStyles.mockReturnValue(mockVisualStyles);
    mockMultimediaService.getEstimatedGenerationTimes.mockReturnValue(mockEstimatedTimes);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Component Rendering', () => {
    it('should render generator with lesson title', async () => {
      render(
        <MultimediaGenerator 
          lessonId="lesson-123" 
          lessonTitle="Test Lesson" 
        />
      );

      await waitFor(() => {
        expect(screen.getByText('🎵 Generate Multimedia Content')).toBeInTheDocument();
        expect(screen.getByText('For: Test Lesson')).toBeInTheDocument();
      });
    });

    it('should show loading state initially', () => {
      mockMultimediaService.getGenerationStatus.mockImplementation(() => new Promise(() => {}));
      
      render(
        <MultimediaGenerator 
          lessonId="lesson-123" 
          lessonTitle="Test Lesson" 
        />
      );

      expect(screen.getByText('Loading generation options...')).toBeInTheDocument();
    });

    it('should render close button when onClose provided', async () => {
      const mockOnClose = jest.fn();
      render(
        <MultimediaGenerator 
          lessonId="lesson-123" 
          lessonTitle="Test Lesson"
          onClose={mockOnClose}
        />
      );

      await waitFor(() => {
        const closeButton = screen.getByLabelText('Close');
        expect(closeButton).toBeInTheDocument();
        
        fireEvent.click(closeButton);
        expect(mockOnClose).toHaveBeenCalled();
      });
    });
  });

  describe('Generation Status Display', () => {
    it('should display current generation status', async () => {
      render(
        <MultimediaGenerator 
          lessonId="lesson-123" 
          lessonTitle="Test Lesson" 
        />
      );

      await waitFor(() => {
        expect(screen.getByText('📊 Current Status')).toBeInTheDocument();
        expect(screen.getByText('✅ Available')).toBeInTheDocument();
        expect(screen.getAllByText('❌ Not Generated')).toHaveLength(2);
      });
    });

    it('should show available content when already generated', async () => {
      const statusWithGenerated = {
        ...mockGenerationStatus,
        audio_lesson: {
          status: 'completed',
          available: true,
          audio_lesson_id: 'audio-123'
        }
      };
      
      mockMultimediaService.getGenerationStatus.mockResolvedValue(statusWithGenerated);

      render(
        <MultimediaGenerator 
          lessonId="lesson-123" 
          lessonTitle="Test Lesson" 
        />
      );

      await waitFor(() => {
        const availableStatuses = screen.getAllByText('✅ Available');
        expect(availableStatuses).toHaveLength(2); // Text + Audio
      });
    });
  });

  describe('Generation Type Selection', () => {
    it('should allow selecting audio generation', async () => {
      render(
        <MultimediaGenerator 
          lessonId="lesson-123" 
          lessonTitle="Test Lesson" 
        />
      );

      await waitFor(() => {
        const audioOption = screen.getByLabelText(/Audio Lesson/);
        expect(audioOption).toBeChecked(); // Default selection
        
        expect(screen.getByText('High-quality narration with voice personalization')).toBeInTheDocument();
        expect(screen.getByText('⏱️ 2-5 minutes')).toBeInTheDocument();
      });
    });

    it('should allow selecting video generation', async () => {
      render(
        <MultimediaGenerator 
          lessonId="lesson-123" 
          lessonTitle="Test Lesson" 
        />
      );

      await waitFor(() => {
        const videoOption = screen.getByLabelText(/Video Lesson/);
        fireEvent.click(videoOption);
        
        expect(videoOption).toBeChecked();
        expect(screen.getByText('AI-generated visuals with narration and subtitles')).toBeInTheDocument();
      });
    });

    it('should allow selecting both audio and video', async () => {
      render(
        <MultimediaGenerator 
          lessonId="lesson-123" 
          lessonTitle="Test Lesson" 
        />
      );

      await waitFor(() => {
        const bothOption = screen.getByLabelText(/Both Audio & Video/);
        fireEvent.click(bothOption);
        
        expect(bothOption).toBeChecked();
        expect(screen.getByText('Complete multimedia experience')).toBeInTheDocument();
        expect(screen.getByText('⏱️ 7-20 minutes')).toBeInTheDocument();
      });
    });

    it('should disable options when generation not available', async () => {
      const statusWithLimitations = {
        ...mockGenerationStatus,
        generation_options: {
          can_generate_audio: false,
          can_generate_video: true,
          estimated_audio_time: '2-5 minutes',
          estimated_video_time: '5-15 minutes'
        }
      };
      
      mockMultimediaService.getGenerationStatus.mockResolvedValue(statusWithLimitations);

      render(
        <MultimediaGenerator 
          lessonId="lesson-123" 
          lessonTitle="Test Lesson" 
        />
      );

      await waitFor(() => {
        const audioOption = screen.getByLabelText(/Audio Lesson/);
        expect(audioOption).toBeDisabled();
        
        const videoOption = screen.getByLabelText(/Video Lesson/);
        expect(videoOption).not.toBeDisabled();
      });
    });
  });

  describe('Audio Preferences', () => {
    it('should display audio preferences when audio selected', async () => {
      render(
        <MultimediaGenerator 
          lessonId="lesson-123" 
          lessonTitle="Test Lesson" 
        />
      );

      await waitFor(() => {
        expect(screen.getByText('🎤 Audio Preferences')).toBeInTheDocument();
        expect(screen.getByText('Voice Profile')).toBeInTheDocument();
        expect(screen.getByText('Speaking Rate')).toBeInTheDocument();
        expect(screen.getByText('Tone')).toBeInTheDocument();
      });
    });

    it('should allow changing voice profile', async () => {
      render(
        <MultimediaGenerator 
          lessonId="lesson-123" 
          lessonTitle="Test Lesson" 
        />
      );

      await waitFor(() => {
        const voiceSelect = screen.getByDisplayValue('Professional Female');
        fireEvent.change(voiceSelect, { target: { value: 'friendly_male' } });
        
        expect(voiceSelect).toHaveValue('friendly_male');
        expect(screen.getByText('Warm, approachable male voice')).toBeInTheDocument();
      });
    });

    it('should allow changing speaking rate and tone', async () => {
      render(
        <MultimediaGenerator 
          lessonId="lesson-123" 
          lessonTitle="Test Lesson" 
        />
      );

      await waitFor(() => {
        const rateSelect = screen.getByDisplayValue('Medium');
        fireEvent.change(rateSelect, { target: { value: 'fast' } });
        expect(rateSelect).toHaveValue('fast');

        const toneSelect = screen.getByDisplayValue('Professional');
        fireEvent.change(toneSelect, { target: { value: 'friendly' } });
        expect(toneSelect).toHaveValue('friendly');
      });
    });
  });

  describe('Video Preferences', () => {
    it('should display video preferences when video selected', async () => {
      render(
        <MultimediaGenerator 
          lessonId="lesson-123" 
          lessonTitle="Test Lesson" 
        />
      );

      await waitFor(() => {
        const videoOption = screen.getByLabelText(/Video Lesson/);
        fireEvent.click(videoOption);
        
        expect(screen.getByText('🎥 Video Preferences')).toBeInTheDocument();
        expect(screen.getByText('Visual Style')).toBeInTheDocument();
        expect(screen.getByText('Video Quality')).toBeInTheDocument();
        expect(screen.getByText('Include Narration')).toBeInTheDocument();
        expect(screen.getByText('Include Subtitles')).toBeInTheDocument();
      });
    });

    it('should allow changing visual style', async () => {
      render(
        <MultimediaGenerator 
          lessonId="lesson-123" 
          lessonTitle="Test Lesson" 
        />
      );

      await waitFor(() => {
        const videoOption = screen.getByLabelText(/Video Lesson/);
        fireEvent.click(videoOption);
        
        const styleSelect = screen.getByDisplayValue('Educational');
        fireEvent.change(styleSelect, { target: { value: 'technical' } });
        
        expect(styleSelect).toHaveValue('technical');
        expect(screen.getByText('Modern, high-tech style with dark themes')).toBeInTheDocument();
      });
    });

    it('should allow toggling narration and subtitles', async () => {
      render(
        <MultimediaGenerator 
          lessonId="lesson-123" 
          lessonTitle="Test Lesson" 
        />
      );

      await waitFor(() => {
        const videoOption = screen.getByLabelText(/Video Lesson/);
        fireEvent.click(videoOption);
        
        const narrationCheckbox = screen.getByLabelText('Include Narration');
        const subtitlesCheckbox = screen.getByLabelText('Include Subtitles');
        
        expect(narrationCheckbox).toBeChecked();
        expect(subtitlesCheckbox).toBeChecked();
        
        fireEvent.click(narrationCheckbox);
        fireEvent.click(subtitlesCheckbox);
        
        expect(narrationCheckbox).not.toBeChecked();
        expect(subtitlesCheckbox).not.toBeChecked();
      });
    });
  });

  describe('Generation Process', () => {
    it('should handle audio generation', async () => {
      const mockOnComplete = jest.fn();
      mockMultimediaService.generateAudioLesson.mockResolvedValue({} as any);
      
      render(
        <MultimediaGenerator 
          lessonId="lesson-123" 
          lessonTitle="Test Lesson"
          onGenerationComplete={mockOnComplete}
        />
      );

      await waitFor(() => {
        const generateButton = screen.getByText(/Generate audio Content/);
        fireEvent.click(generateButton);
      });

      await waitFor(() => {
        expect(screen.getByText('🔄 Generating audio content...')).toBeInTheDocument();
        expect(screen.getByText('This may take 2-5 minutes. Please don\'t close this window.')).toBeInTheDocument();
      });

      await waitFor(() => {
        expect(mockMultimediaService.generateAudioLesson).toHaveBeenCalledWith('lesson-123', {
          voice_preference: 'professional_female',
          tone_preference: 'professional',
          speaking_rate: 'medium',
          audio_volume: 'medium'
        });
      });

      await waitFor(() => {
        expect(mockOnComplete).toHaveBeenCalledWith('audio', 'lesson-123');
      });
    });

    it('should handle video generation', async () => {
      const mockOnComplete = jest.fn();
      mockMultimediaService.generateVideoLesson.mockResolvedValue({} as any);
      
      render(
        <MultimediaGenerator 
          lessonId="lesson-123" 
          lessonTitle="Test Lesson"
          onGenerationComplete={mockOnComplete}
        />
      );

      await waitFor(() => {
        const videoOption = screen.getByLabelText(/Video Lesson/);
        fireEvent.click(videoOption);
        
        const generateButton = screen.getByText(/Generate video Content/);
        fireEvent.click(generateButton);
      });

      await waitFor(() => {
        expect(mockMultimediaService.generateVideoLesson).toHaveBeenCalledWith('lesson-123', {
          visual_style: 'educational',
          include_narration: true,
          include_subtitles: true,
          video_quality: 'hd'
        });
      });

      await waitFor(() => {
        expect(mockOnComplete).toHaveBeenCalledWith('video', 'lesson-123');
      });
    });

    it('should handle both audio and video generation', async () => {
      const mockOnComplete = jest.fn();
      mockMultimediaService.generateAudioLesson.mockResolvedValue({} as any);
      mockMultimediaService.generateVideoLesson.mockResolvedValue({} as any);
      
      render(
        <MultimediaGenerator 
          lessonId="lesson-123" 
          lessonTitle="Test Lesson"
          onGenerationComplete={mockOnComplete}
        />
      );

      await waitFor(() => {
        const bothOption = screen.getByLabelText(/Both Audio & Video/);
        fireEvent.click(bothOption);
        
        const generateButton = screen.getByText(/Generate Audio & Video Content/);
        fireEvent.click(generateButton);
      });

      await waitFor(() => {
        expect(mockMultimediaService.generateAudioLesson).toHaveBeenCalled();
        expect(mockMultimediaService.generateVideoLesson).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(mockOnComplete).toHaveBeenCalledWith('video', 'lesson-123');
      });
    });

    it('should show progress during generation', async () => {
      mockMultimediaService.generateAudioLesson.mockImplementation(() => new Promise(() => {}));
      
      render(
        <MultimediaGenerator 
          lessonId="lesson-123" 
          lessonTitle="Test Lesson"
        />
      );

      await waitFor(() => {
        const generateButton = screen.getByText(/Generate audio Content/);
        fireEvent.click(generateButton);
      });

      await waitFor(() => {
        expect(screen.getByText('🔄 Generating audio content...')).toBeInTheDocument();
        expect(document.querySelector('.progress-bar')).toBeInTheDocument();
        expect(screen.getByText('0% complete')).toBeInTheDocument();
      });
    });

    it('should handle generation errors', async () => {
      mockMultimediaService.generateAudioLesson.mockRejectedValue(new Error('Generation failed'));
      
      render(
        <MultimediaGenerator 
          lessonId="lesson-123" 
          lessonTitle="Test Lesson"
        />
      );

      await waitFor(() => {
        const generateButton = screen.getByText(/Generate audio Content/);
        fireEvent.click(generateButton);
      });

      await waitFor(() => {
        expect(screen.getByText('Generation failed')).toBeInTheDocument();
        expect(screen.getByText('⚠️')).toBeInTheDocument();
      });

      // Should be able to dismiss error
      const dismissButton = screen.getByText('✕');
      fireEvent.click(dismissButton);
      
      await waitFor(() => {
        expect(screen.queryByText('Generation failed')).not.toBeInTheDocument();
      });
    });

    it('should disable generate button when generation not possible', async () => {
      const statusWithExisting = {
        ...mockGenerationStatus,
        generation_options: {
          can_generate_audio: false,
          can_generate_video: false,
          estimated_audio_time: '2-5 minutes',
          estimated_video_time: '5-15 minutes'
        }
      };
      
      mockMultimediaService.getGenerationStatus.mockResolvedValue(statusWithExisting);

      render(
        <MultimediaGenerator 
          lessonId="lesson-123" 
          lessonTitle="Test Lesson" 
        />
      );

      await waitFor(() => {
        const generateButton = screen.getByText(/Generate audio Content/);
        expect(generateButton).toBeDisabled();
        expect(screen.getByText('Audio content already exists for this lesson.')).toBeInTheDocument();
      });
    });
  });

  describe('Status Refresh', () => {
    it('should refresh status after successful generation', async () => {
      mockMultimediaService.generateAudioLesson.mockResolvedValue({} as any);
      
      render(
        <MultimediaGenerator 
          lessonId="lesson-123" 
          lessonTitle="Test Lesson"
        />
      );

      await waitFor(() => {
        const generateButton = screen.getByText(/Generate audio Content/);
        fireEvent.click(generateButton);
      });

      await waitFor(() => {
        expect(mockMultimediaService.getGenerationStatus).toHaveBeenCalledTimes(2); // Initial + refresh
      });
    });
  });
});