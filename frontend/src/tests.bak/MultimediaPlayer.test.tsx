/**
 * MultimediaPlayer Component Tests
 * 
 * Tests for MultimediaPlayer component including audio/video playback controls,
 * progress tracking, and user interaction functionality
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import MultimediaPlayer from '../components/MultimediaPlayer';
import multimediaService from '../services/multimediaService';
import { AudioLesson, VideoLesson } from '../types';

// Mock the multimedia service
jest.mock('../services/multimediaService', () => ({
  trackMultimediaEvent: jest.fn().mockResolvedValue(undefined)
}));

// Mock HTML media elements
Object.defineProperty(HTMLMediaElement.prototype, 'play', {
  writable: true,
  value: jest.fn().mockImplementation(() => Promise.resolve()),
});

Object.defineProperty(HTMLMediaElement.prototype, 'pause', {
  writable: true,
  value: jest.fn(),
});

Object.defineProperty(HTMLMediaElement.prototype, 'currentTime', {
  writable: true,
  value: 0,
});

Object.defineProperty(HTMLMediaElement.prototype, 'duration', {
  writable: true,
  value: 300,
});

Object.defineProperty(HTMLMediaElement.prototype, 'volume', {
  writable: true,
  value: 1,
});

Object.defineProperty(HTMLMediaElement.prototype, 'playbackRate', {
  writable: true,
  value: 1,
});

describe('MultimediaPlayer', () => {
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
    transcript: 'This is a test transcript for the audio lesson.',
    key_timestamps: [
      {
        time_seconds: 30,
        concept: 'Introduction',
        type: 'concept'
      },
      {
        time_seconds: 120,
        concept: 'Main Topic',
        type: 'concept'
      }
    ],
    generated_at: '2024-01-01T00:00:00Z',
    format: 'mp3',
    sample_rate: '44100'
  };

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

  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Audio Player', () => {
    it('should render audio player with lesson content', () => {
      render(<MultimediaPlayer audioLesson={mockAudioLesson} />);

      expect(screen.getByText('Test Audio Lesson')).toBeInTheDocument();
      expect(screen.getByText('🎵')).toBeInTheDocument();
      expect(screen.getByLabelText('Play')).toBeInTheDocument();
      expect(screen.getByText('Duration: 5:00')).toBeInTheDocument();
      expect(screen.getByText('Format: Audio')).toBeInTheDocument();
    });

    it('should display audio timestamps/chapters', () => {
      render(<MultimediaPlayer audioLesson={mockAudioLesson} />);

      expect(screen.getByText('📚 Chapters')).toBeInTheDocument();
      expect(screen.getByText('Introduction')).toBeInTheDocument();
      expect(screen.getByText('Main Topic')).toBeInTheDocument();
      expect(screen.getByText('0:30')).toBeInTheDocument();
      expect(screen.getByText('2:00')).toBeInTheDocument();
    });

    it('should toggle transcript visibility', () => {
      render(<MultimediaPlayer audioLesson={mockAudioLesson} />);

      const transcriptButton = screen.getByText('📝 Transcript');
      fireEvent.click(transcriptButton);

      expect(screen.getByText('This is a test transcript for the audio lesson.')).toBeInTheDocument();
    });

    it('should handle play/pause functionality', async () => {
      const mockOnProgress = jest.fn();
      render(<MultimediaPlayer audioLesson={mockAudioLesson} onProgress={mockOnProgress} />);

      const playButton = screen.getByLabelText('Play');
      fireEvent.click(playButton);

      await waitFor(() => {
        expect(multimediaService.trackMultimediaEvent).toHaveBeenCalledWith(
          'audio_played',
          'audio-123',
          { current_time: 0 }
        );
      });

      // Simulate pause
      fireEvent.click(screen.getByLabelText('Pause'));

      await waitFor(() => {
        expect(multimediaService.trackMultimediaEvent).toHaveBeenCalledWith(
          'audio_paused',
          'audio-123',
          { current_time: 0 }
        );
      });
    });

    it('should handle playback rate changes', async () => {
      render(<MultimediaPlayer audioLesson={mockAudioLesson} />);

      const speedSelect = screen.getByDisplayValue('1x');
      fireEvent.change(speedSelect, { target: { value: '1.5' } });

      await waitFor(() => {
        expect(multimediaService.trackMultimediaEvent).toHaveBeenCalledWith(
          'playback_rate_changed',
          'audio-123',
          { playback_rate: 1.5 }
        );
      });
    });

    it('should handle timestamp clicks', async () => {
      const mockOnTimestampClick = jest.fn();
      render(
        <MultimediaPlayer 
          audioLesson={mockAudioLesson} 
          onTimestampClick={mockOnTimestampClick}
        />
      );

      const timestampItem = screen.getByText('Introduction').closest('.timestamp-item');
      fireEvent.click(timestampItem!);

      await waitFor(() => {
        expect(multimediaService.trackMultimediaEvent).toHaveBeenCalledWith(
          'timestamp_clicked',
          'audio-123',
          { timestamp: 30, concept: 'Introduction' }
        );
      });

      expect(mockOnTimestampClick).toHaveBeenCalledWith({
        time_seconds: 30,
        concept: 'Introduction',
        type: 'concept'
      });
    });

    it('should handle volume changes', () => {
      render(<MultimediaPlayer audioLesson={mockAudioLesson} />);

      const volumeSlider = screen.getByDisplayValue('100');
      fireEvent.change(volumeSlider, { target: { value: '50' } });

      // Volume should be updated (tested through media element mock)
      expect(volumeSlider).toHaveValue('50');
    });

    it('should track completion events', async () => {
      const mockOnComplete = jest.fn();
      render(<MultimediaPlayer audioLesson={mockAudioLesson} onComplete={mockOnComplete} />);

      // Simulate audio ended event
      const audioElement = document.querySelector('audio');
      fireEvent.ended(audioElement!);

      await waitFor(() => {
        expect(multimediaService.trackMultimediaEvent).toHaveBeenCalledWith(
          'audio_lesson_completed',
          'audio-123',
          {
            duration_seconds: 300,
            playback_rate: 1,
            completion_percentage: 100
          }
        );
      });

      expect(mockOnComplete).toHaveBeenCalled();
    });
  });

  describe('Video Player', () => {
    it('should render video player with lesson content', () => {
      render(<MultimediaPlayer videoLesson={mockVideoLesson} />);

      expect(screen.getByText('Test Video Lesson')).toBeInTheDocument();
      expect(screen.getByLabelText('Play')).toBeInTheDocument();
      expect(screen.getByText('Duration: 10:00')).toBeInTheDocument();
      expect(screen.getByText('Format: Video')).toBeInTheDocument();
      expect(screen.getByText('Quality: 1080p')).toBeInTheDocument();
    });

    it('should display video element', () => {
      render(<MultimediaPlayer videoLesson={mockVideoLesson} />);

      const videoElement = document.querySelector('video');
      expect(videoElement).toBeInTheDocument();
      expect(videoElement).toHaveAttribute('src', 'https://example.com/video.mp4');
    });

    it('should display interactive elements', () => {
      render(<MultimediaPlayer videoLesson={mockVideoLesson} />);

      expect(screen.getByText('🎯 Interactive Elements')).toBeInTheDocument();
      expect(screen.getByText('Quick Check')).toBeInTheDocument();
      expect(screen.getByText('Test your understanding')).toBeInTheDocument();
      expect(screen.getByText('2:00')).toBeInTheDocument();
    });

    it('should handle video play/pause functionality', async () => {
      render(<MultimediaPlayer videoLesson={mockVideoLesson} />);

      const playButton = screen.getByLabelText('Play');
      fireEvent.click(playButton);

      await waitFor(() => {
        expect(multimediaService.trackMultimediaEvent).toHaveBeenCalledWith(
          'video_played',
          'video-123',
          { current_time: 0 }
        );
      });
    });

    it('should track video completion', async () => {
      const mockOnComplete = jest.fn();
      render(<MultimediaPlayer videoLesson={mockVideoLesson} onComplete={mockOnComplete} />);

      // Simulate video ended event
      const videoElement = document.querySelector('video');
      fireEvent.ended(videoElement!);

      await waitFor(() => {
        expect(multimediaService.trackMultimediaEvent).toHaveBeenCalledWith(
          'video_lesson_completed',
          'video-123',
          {
            duration_seconds: 300, // mocked duration
            playback_rate: 1,
            completion_percentage: 100
          }
        );
      });

      expect(mockOnComplete).toHaveBeenCalled();
    });

    it('should not show transcript button for video', () => {
      render(<MultimediaPlayer videoLesson={mockVideoLesson} />);

      expect(screen.queryByText('📝 Transcript')).not.toBeInTheDocument();
    });
  });

  describe('Empty State', () => {
    it('should render empty state when no lesson provided', () => {
      render(<MultimediaPlayer />);

      expect(screen.getByText('No multimedia content available')).toBeInTheDocument();
      expect(screen.getByText('Generate audio or video content to start learning with multimedia.')).toBeInTheDocument();
    });
  });

  describe('Progress Tracking', () => {
    it('should call onProgress callback during playback', async () => {
      const mockOnProgress = jest.fn();
      render(<MultimediaPlayer audioLesson={mockAudioLesson} onProgress={mockOnProgress} />);

      // Simulate time update
      const audioElement = document.querySelector('audio');
      Object.defineProperty(audioElement, 'currentTime', { value: 150, writable: true });
      Object.defineProperty(audioElement, 'duration', { value: 300, writable: true });
      
      fireEvent.timeUpdate(audioElement!);

      await waitFor(() => {
        expect(mockOnProgress).toHaveBeenCalledWith(50); // 150/300 * 100
      });
    });

    it('should update current chapter based on timestamps', async () => {
      render(<MultimediaPlayer audioLesson={mockAudioLesson} />);

      // Simulate time update to second timestamp
      const audioElement = document.querySelector('audio');
      Object.defineProperty(audioElement, 'currentTime', { value: 150, writable: true });
      
      fireEvent.timeUpdate(audioElement!);

      await waitFor(() => {
        const activeChapter = document.querySelector('.timestamp-item.active');
        expect(activeChapter).toHaveTextContent('Main Topic');
      });
    });
  });

  describe('Seek Functionality', () => {
    it('should handle seek operations', () => {
      render(<MultimediaPlayer audioLesson={mockAudioLesson} />);

      const progressSlider = document.querySelector('.progress-slider') as HTMLInputElement;
      fireEvent.change(progressSlider, { target: { value: '50' } });

      // Should update current time (tested through media element mock)
      expect(progressSlider.value).toBe('50');
    });
  });

  describe('Chapters Toggle', () => {
    it('should toggle chapters visibility', () => {
      render(<MultimediaPlayer audioLesson={mockAudioLesson} />);

      const chaptersButton = screen.getByText('🔖 Chapters');
      fireEvent.click(chaptersButton);

      // Chapters should be hidden
      expect(screen.queryByText('📚 Chapters')).not.toBeInTheDocument();

      // Click again to show
      fireEvent.click(chaptersButton);
      expect(screen.getByText('📚 Chapters')).toBeInTheDocument();
    });
  });
});