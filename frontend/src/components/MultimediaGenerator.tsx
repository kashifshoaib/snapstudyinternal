import React, { useState, useEffect } from 'react';
import { GenerationStatus, MultimediaPreferences } from '../types';
import multimediaService from '../services/multimediaService';
import './MultimediaGenerator.css';

interface MultimediaGeneratorProps {
  lessonId: string;
  lessonTitle: string;
  onGenerationComplete?: (type: 'audio' | 'video', lessonId: string) => void;
  onClose?: () => void;
}

const MultimediaGenerator: React.FC<MultimediaGeneratorProps> = ({
  lessonId,
  lessonTitle,
  onGenerationComplete,
  onClose
}) => {
  const [generationStatus, setGenerationStatus] = useState<GenerationStatus | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationType, setGenerationType] = useState<'audio' | 'video' | 'both'>('audio');
  const [preferences, setPreferences] = useState<Partial<MultimediaPreferences>>({
    voice_preference: 'professional_female',
    tone_preference: 'professional',
    speaking_rate: 'medium',
    audio_volume: 'medium',
    visual_style: 'educational',
    include_narration: true,
    include_subtitles: true,
    video_quality: 'hd'
  });
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  const voiceProfiles = multimediaService.getVoiceProfiles();
  const visualStyles = multimediaService.getVisualStyles();
  const estimatedTimes = multimediaService.getEstimatedGenerationTimes();

  useEffect(() => {
    loadGenerationStatus();
  }, [lessonId]);

  const loadGenerationStatus = async () => {
    try {
      const status = await multimediaService.getGenerationStatus(lessonId);
      setGenerationStatus(status);
    } catch (error) {
      console.error('Error loading generation status:', error);
    }
  };

  const handleGenerate = async () => {
    if (!generationStatus) return;

    setIsGenerating(true);
    setError(null);
    setProgress(0);

    try {
      if (generationType === 'audio' || generationType === 'both') {
        await generateAudio();
      }

      if (generationType === 'video' || generationType === 'both') {
        await generateVideo();
      }

      // Refresh status
      await loadGenerationStatus();
      
      if (onGenerationComplete) {
        onGenerationComplete(generationType === 'both' ? 'video' : generationType, lessonId);
      }

    } catch (error) {
      console.error('Generation error:', error);
      setError(error instanceof Error ? error.message : 'Generation failed. Please try again.');
    } finally {
      setIsGenerating(false);
      setProgress(0);
    }
  };

  const generateAudio = async () => {
    setProgress(25);
    
    const audioPreferences = {
      voice_preference: preferences.voice_preference,
      tone_preference: preferences.tone_preference,
      speaking_rate: preferences.speaking_rate,
      audio_volume: preferences.audio_volume
    };

    await multimediaService.generateAudioLesson(lessonId, audioPreferences);
    setProgress(generationType === 'audio' ? 100 : 50);
  };

  const generateVideo = async () => {
    setProgress(generationType === 'video' ? 25 : 75);
    
    const videoPreferences = {
      visual_style: preferences.visual_style,
      include_narration: preferences.include_narration,
      include_subtitles: preferences.include_subtitles,
      video_quality: preferences.video_quality
    };

    await multimediaService.generateVideoLesson(lessonId, videoPreferences);
    setProgress(100);
  };

  const handlePreferenceChange = (key: keyof MultimediaPreferences, value: any) => {
    setPreferences(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const getEstimatedTime = (): string => {
    switch (generationType) {
      case 'audio':
        return estimatedTimes.audio;
      case 'video':
        return estimatedTimes.video;
      case 'both':
        return '7-20 minutes';
      default:
        return '';
    }
  };

  const canGenerate = (): boolean => {
    if (!generationStatus) return false;
    
    switch (generationType) {
      case 'audio':
        return generationStatus.generation_options.can_generate_audio;
      case 'video':
        return generationStatus.generation_options.can_generate_video;
      case 'both':
        return generationStatus.generation_options.can_generate_audio || 
               generationStatus.generation_options.can_generate_video;
      default:
        return false;
    }
  };

  if (!generationStatus) {
    return (
      <div className="multimedia-generator loading">
        <div className="loading-spinner"></div>
        <p>Loading generation options...</p>
      </div>
    );
  }

  return (
    <div className="multimedia-generator">
      <div className="generator-header">
        <h2>🎵 Generate Multimedia Content</h2>
        <p className="lesson-title">For: {lessonTitle}</p>
        {onClose && (
          <button className="close-button" onClick={onClose} aria-label="Close">
            ✕
          </button>
        )}
      </div>

      {error && (
        <div className="error-message">
          <div className="error-icon">⚠️</div>
          <div className="error-text">{error}</div>
          <button className="error-dismiss" onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {isGenerating && (
        <div className="generation-progress">
          <div className="progress-header">
            <h3>🔄 Generating {generationType} content...</h3>
            <p>This may take {getEstimatedTime()}. Please don't close this window.</p>
          </div>
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          <div className="progress-text">{progress}% complete</div>
        </div>
      )}

      {!isGenerating && (
        <>
          {/* Current Status */}
          <div className="current-status">
            <h3>📊 Current Status</h3>
            <div className="status-grid">
              <div className="status-item">
                <div className="status-label">Text Lesson</div>
                <div className="status-value available">✅ Available</div>
              </div>
              <div className="status-item">
                <div className="status-label">Audio Lesson</div>
                <div className={`status-value ${generationStatus.audio_lesson.available ? 'available' : 'unavailable'}`}>
                  {generationStatus.audio_lesson.available ? '✅ Available' : '❌ Not Generated'}
                </div>
              </div>
              <div className="status-item">
                <div className="status-label">Video Lesson</div>
                <div className={`status-value ${generationStatus.video_lesson.available ? 'available' : 'unavailable'}`}>
                  {generationStatus.video_lesson.available ? '✅ Available' : '❌ Not Generated'}
                </div>
              </div>
            </div>
          </div>

          {/* Generation Type Selection */}
          <div className="generation-type">
            <h3>🎯 What would you like to generate?</h3>
            <div className="type-options">
              <label className={`type-option ${generationType === 'audio' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  value="audio"
                  checked={generationType === 'audio'}
                  onChange={(e) => setGenerationType(e.target.value as 'audio')}
                  disabled={!generationStatus.generation_options.can_generate_audio}
                />
                <div className="option-content">
                  <div className="option-icon">🎵</div>
                  <div className="option-details">
                    <div className="option-title">Audio Lesson</div>
                    <div className="option-description">High-quality narration with voice personalization</div>
                    <div className="option-time">⏱️ {estimatedTimes.audio}</div>
                  </div>
                </div>
              </label>

              <label className={`type-option ${generationType === 'video' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  value="video"
                  checked={generationType === 'video'}
                  onChange={(e) => setGenerationType(e.target.value as 'video')}
                  disabled={!generationStatus.generation_options.can_generate_video}
                />
                <div className="option-content">
                  <div className="option-icon">🎥</div>
                  <div className="option-details">
                    <div className="option-title">Video Lesson</div>
                    <div className="option-description">AI-generated visuals with narration and subtitles</div>
                    <div className="option-time">⏱️ {estimatedTimes.video}</div>
                  </div>
                </div>
              </label>

              <label className={`type-option ${generationType === 'both' ? 'selected' : ''}`}>
                <input
                  type="radio"
                  value="both"
                  checked={generationType === 'both'}
                  onChange={(e) => setGenerationType(e.target.value as 'both')}
                  disabled={!generationStatus.generation_options.can_generate_audio && 
                           !generationStatus.generation_options.can_generate_video}
                />
                <div className="option-content">
                  <div className="option-icon">🎬</div>
                  <div className="option-details">
                    <div className="option-title">Both Audio & Video</div>
                    <div className="option-description">Complete multimedia experience</div>
                    <div className="option-time">⏱️ 7-20 minutes</div>
                  </div>
                </div>
              </label>
            </div>
          </div>

          {/* Audio Preferences */}
          {(generationType === 'audio' || generationType === 'both') && (
            <div className="preferences-section">
              <h3>🎤 Audio Preferences</h3>
              <div className="preferences-grid">
                <div className="preference-group">
                  <label>Voice Profile</label>
                  <select
                    value={preferences.voice_preference}
                    onChange={(e) => handlePreferenceChange('voice_preference', e.target.value)}
                  >
                    {voiceProfiles.map(profile => (
                      <option key={profile.id} value={profile.id}>
                        {profile.name}
                      </option>
                    ))}
                  </select>
                  <div className="preference-description">
                    {voiceProfiles.find(p => p.id === preferences.voice_preference)?.description}
                  </div>
                </div>

                <div className="preference-group">
                  <label>Speaking Rate</label>
                  <select
                    value={preferences.speaking_rate}
                    onChange={(e) => handlePreferenceChange('speaking_rate', e.target.value)}
                  >
                    <option value="slow">Slow</option>
                    <option value="medium">Medium</option>
                    <option value="fast">Fast</option>
                  </select>
                </div>

                <div className="preference-group">
                  <label>Tone</label>
                  <select
                    value={preferences.tone_preference}
                    onChange={(e) => handlePreferenceChange('tone_preference', e.target.value)}
                  >
                    <option value="professional">Professional</option>
                    <option value="friendly">Friendly</option>
                    <option value="authoritative">Authoritative</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Video Preferences */}
          {(generationType === 'video' || generationType === 'both') && (
            <div className="preferences-section">
              <h3>🎥 Video Preferences</h3>
              <div className="preferences-grid">
                <div className="preference-group">
                  <label>Visual Style</label>
                  <select
                    value={preferences.visual_style}
                    onChange={(e) => handlePreferenceChange('visual_style', e.target.value)}
                  >
                    {visualStyles.map(style => (
                      <option key={style.id} value={style.id}>
                        {style.name}
                      </option>
                    ))}
                  </select>
                  <div className="preference-description">
                    {visualStyles.find(s => s.id === preferences.visual_style)?.description}
                  </div>
                </div>

                <div className="preference-group">
                  <label>Video Quality</label>
                  <select
                    value={preferences.video_quality}
                    onChange={(e) => handlePreferenceChange('video_quality', e.target.value)}
                  >
                    <option value="sd">Standard (720p)</option>
                    <option value="hd">High Definition (1080p)</option>
                  </select>
                </div>

                <div className="preference-group checkbox-group">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={preferences.include_narration}
                      onChange={(e) => handlePreferenceChange('include_narration', e.target.checked)}
                    />
                    Include Narration
                  </label>
                </div>

                <div className="preference-group checkbox-group">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={preferences.include_subtitles}
                      onChange={(e) => handlePreferenceChange('include_subtitles', e.target.checked)}
                    />
                    Include Subtitles
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* Generation Button */}
          <div className="generation-actions">
            <button
              className="generate-button"
              onClick={handleGenerate}
              disabled={!canGenerate() || isGenerating}
            >
              <span className="button-icon">🚀</span>
              <span className="button-text">
                Generate {generationType === 'both' ? 'Audio & Video' : generationType} Content
              </span>
              <span className="button-time">({getEstimatedTime()})</span>
            </button>

            {!canGenerate() && (
              <div className="generation-note">
                <p>
                  {generationType === 'audio' && !generationStatus.generation_options.can_generate_audio && 
                    'Audio content already exists for this lesson.'}
                  {generationType === 'video' && !generationStatus.generation_options.can_generate_video && 
                    'Video content already exists for this lesson.'}
                  {generationType === 'both' && 
                   !generationStatus.generation_options.can_generate_audio && 
                   !generationStatus.generation_options.can_generate_video && 
                    'Both audio and video content already exist for this lesson.'}
                </p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default MultimediaGenerator;