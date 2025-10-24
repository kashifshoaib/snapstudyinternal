import React, { useState, useRef, useEffect } from 'react';
import { AudioLesson, VideoLesson, Timestamp } from '../types';
import multimediaService from '../services/multimediaService';
import './MultimediaPlayer.css';

interface MultimediaPlayerProps {
  audioLesson?: AudioLesson;
  videoLesson?: VideoLesson;
  onComplete?: () => void;
  onProgress?: (progress: number) => void;
  onTimestampClick?: (timestamp: Timestamp) => void;
}

const MultimediaPlayer: React.FC<MultimediaPlayerProps> = ({
  audioLesson,
  videoLesson,
  onComplete,
  onProgress,
  onTimestampClick
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [volume, setVolume] = useState(1);
  const [showTranscript, setShowTranscript] = useState(false);
  const [showTimestamps, setShowTimestamps] = useState(true);
  const [currentChapter, setCurrentChapter] = useState<Timestamp | null>(null);

  const audioRef = useRef<HTMLAudioElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  const mediaRef = videoLesson ? videoRef : audioRef;
  const lesson = videoLesson || audioLesson;
  const isVideo = !!videoLesson;

  useEffect(() => {
    const media = mediaRef.current;
    if (!media) return;

    const handleTimeUpdate = () => {
      const current = media.currentTime;
      setCurrentTime(current);
      
      if (onProgress) {
        onProgress((current / media.duration) * 100);
      }

      // Update current chapter based on timestamps
      if (lesson?.key_timestamps) {
        const currentTimestamp = lesson.key_timestamps
          .filter(t => t.time_seconds <= current)
          .pop();
        
        if (currentTimestamp && currentTimestamp !== currentChapter) {
          setCurrentChapter(currentTimestamp);
        }
      }
    };

    const handleLoadedMetadata = () => {
      setDuration(media.duration);
    };

    const handleEnded = () => {
      setIsPlaying(false);
      if (onComplete) {
        onComplete();
      }
      
      // Track completion
      if (lesson) {
        multimediaService.trackMultimediaEvent(
          isVideo ? 'video_lesson_completed' : 'audio_lesson_completed',
          isVideo ? videoLesson!.video_lesson_id : audioLesson!.audio_lesson_id,
          {
            duration_seconds: duration,
            playback_rate: playbackRate,
            completion_percentage: 100
          }
        );
      }
    };

    media.addEventListener('timeupdate', handleTimeUpdate);
    media.addEventListener('loadedmetadata', handleLoadedMetadata);
    media.addEventListener('ended', handleEnded);

    return () => {
      media.removeEventListener('timeupdate', handleTimeUpdate);
      media.removeEventListener('loadedmetadata', handleLoadedMetadata);
      media.removeEventListener('ended', handleEnded);
    };
  }, [lesson, currentChapter, duration, playbackRate, onComplete, onProgress]);

  const togglePlayPause = () => {
    const media = mediaRef.current;
    if (!media) return;

    if (isPlaying) {
      media.pause();
      multimediaService.trackMultimediaEvent(
        isVideo ? 'video_paused' : 'audio_paused',
        lesson ? (isVideo ? videoLesson!.video_lesson_id : audioLesson!.audio_lesson_id) : '',
        { current_time: currentTime }
      );
    } else {
      media.play();
      multimediaService.trackMultimediaEvent(
        isVideo ? 'video_played' : 'audio_played',
        lesson ? (isVideo ? videoLesson!.video_lesson_id : audioLesson!.audio_lesson_id) : '',
        { current_time: currentTime }
      );
    }
    
    setIsPlaying(!isPlaying);
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const media = mediaRef.current;
    if (!media) return;

    const newTime = (parseFloat(e.target.value) / 100) * duration;
    media.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const handlePlaybackRateChange = (rate: number) => {
    const media = mediaRef.current;
    if (!media) return;

    media.playbackRate = rate;
    setPlaybackRate(rate);
    
    multimediaService.trackMultimediaEvent(
      'playback_rate_changed',
      lesson ? (isVideo ? videoLesson!.video_lesson_id : audioLesson!.audio_lesson_id) : '',
      { playback_rate: rate }
    );
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const media = mediaRef.current;
    if (!media) return;

    const newVolume = parseFloat(e.target.value) / 100;
    media.volume = newVolume;
    setVolume(newVolume);
  };

  const jumpToTimestamp = (timestamp: Timestamp) => {
    const media = mediaRef.current;
    if (!media) return;

    media.currentTime = timestamp.time_seconds;
    setCurrentTime(timestamp.time_seconds);
    
    if (onTimestampClick) {
      onTimestampClick(timestamp);
    }

    multimediaService.trackMultimediaEvent(
      'timestamp_clicked',
      lesson ? (isVideo ? videoLesson!.video_lesson_id : audioLesson!.audio_lesson_id) : '',
      { timestamp: timestamp.time_seconds, concept: timestamp.concept }
    );
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!lesson) {
    return (
      <div className="multimedia-player-empty">
        <div className="empty-state">
          <div className="empty-icon">🎵</div>
          <h3>No multimedia content available</h3>
          <p>Generate audio or video content to start learning with multimedia.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`multimedia-player ${isVideo ? 'video-player' : 'audio-player'}`}>
      {/* Media Element */}
      <div className="media-container">
        {isVideo ? (
          <video
            ref={videoRef}
            src={videoLesson!.video_url}
            className="video-element"
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
          />
        ) : (
          <div className="audio-visualization">
            <audio
              ref={audioRef}
              src={audioLesson!.audio_url}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
            />
            <div className="audio-visual">
              <div className="audio-icon">🎵</div>
              <div className="audio-title">{lesson.title}</div>
              {currentChapter && (
                <div className="current-chapter">
                  <span className="chapter-label">Current Topic:</span>
                  <span className="chapter-concept">{currentChapter.concept}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="media-controls">
        <div className="primary-controls">
          <button
            className="play-pause-btn"
            onClick={togglePlayPause}
            aria-label={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? '⏸️' : '▶️'}
          </button>

          <div className="time-display">
            <span>{formatTime(currentTime)}</span>
            <span>/</span>
            <span>{formatTime(duration)}</span>
          </div>

          <div className="progress-container">
            <input
              type="range"
              className="progress-slider"
              min="0"
              max="100"
              value={duration ? (currentTime / duration) * 100 : 0}
              onChange={handleSeek}
            />
          </div>
        </div>

        <div className="secondary-controls">
          <div className="playback-rate">
            <label>Speed:</label>
            <select
              value={playbackRate}
              onChange={(e) => handlePlaybackRateChange(parseFloat(e.target.value))}
            >
              <option value={0.5}>0.5x</option>
              <option value={0.75}>0.75x</option>
              <option value={1}>1x</option>
              <option value={1.25}>1.25x</option>
              <option value={1.5}>1.5x</option>
              <option value={2}>2x</option>
            </select>
          </div>

          <div className="volume-control">
            <label>🔊</label>
            <input
              type="range"
              className="volume-slider"
              min="0"
              max="100"
              value={volume * 100}
              onChange={handleVolumeChange}
            />
          </div>

          <div className="view-toggles">
            {!isVideo && (
              <button
                className={`toggle-btn ${showTranscript ? 'active' : ''}`}
                onClick={() => setShowTranscript(!showTranscript)}
              >
                📝 Transcript
              </button>
            )}
            
            <button
              className={`toggle-btn ${showTimestamps ? 'active' : ''}`}
              onClick={() => setShowTimestamps(!showTimestamps)}
            >
              🔖 Chapters
            </button>
          </div>
        </div>
      </div>

      {/* Additional Content */}
      <div className="additional-content">
        {/* Timestamps/Chapters */}
        {showTimestamps && lesson.key_timestamps && lesson.key_timestamps.length > 0 && (
          <div className="timestamps-panel">
            <h4>📚 Chapters</h4>
            <div className="timestamps-list">
              {lesson.key_timestamps.map((timestamp, index) => (
                <div
                  key={index}
                  className={`timestamp-item ${currentChapter === timestamp ? 'active' : ''}`}
                  onClick={() => jumpToTimestamp(timestamp)}
                >
                  <div className="timestamp-time">{formatTime(timestamp.time_seconds)}</div>
                  <div className="timestamp-concept">{timestamp.concept}</div>
                  <div className="timestamp-type">{timestamp.type}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Transcript (Audio only) */}
        {showTranscript && audioLesson && (
          <div className="transcript-panel">
            <h4>📝 Transcript</h4>
            <div className="transcript-content">
              {audioLesson.transcript}
            </div>
          </div>
        )}

        {/* Interactive Elements (Video only) */}
        {isVideo && videoLesson!.interactive_elements && videoLesson!.interactive_elements.length > 0 && (
          <div className="interactive-elements">
            <h4>🎯 Interactive Elements</h4>
            <div className="elements-list">
              {videoLesson!.interactive_elements.map((element, index) => (
                <div key={index} className="interactive-element">
                  <div className="element-time">{formatTime(element.time_seconds)}</div>
                  <div className="element-content">
                    <div className="element-title">{element.title}</div>
                    <div className="element-description">{element.description}</div>
                  </div>
                  <div className="element-type">{element.type}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Lesson Info */}
      <div className="lesson-info">
        <div className="lesson-metadata">
          <span className="duration">Duration: {formatTime(lesson.duration_seconds)}</span>
          <span className="format">Format: {isVideo ? 'Video' : 'Audio'}</span>
          {isVideo && (
            <span className="resolution">Quality: {videoLesson!.resolution}</span>
          )}
          {!isVideo && (
            <span className="voice">Voice: {audioLesson!.voice_profile.VoiceId}</span>
          )}
        </div>
      </div>
    </div>
  );
};

export default MultimediaPlayer;