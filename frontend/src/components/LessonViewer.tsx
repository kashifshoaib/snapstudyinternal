import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Lesson, MicroLesson, AdaptiveLearningState, User } from '../types';
import { lessonService } from '../services/lessonService';
import QuizInterface from './QuizInterface';
import { SkeletonLesson } from './SkeletonLoader';
import { useLoadingState } from '../hooks/useLoadingState';
import './LessonViewer.css';

interface LessonViewerProps {
  lesson: Lesson | null;
  microLessons: MicroLesson[];
  user: User;
  isProcessing?: boolean;
  onProgressUpdate?: (progress: number) => void;
}

// SVG Icons matching snapstudy.html
const PlayIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24">
    <path d="M8 5v14l11-7z" fill="currentColor"/>
  </svg>
);

const AudioIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24">
    <path d="M14 3.23v17.54c0 .79-.9 1.27-1.54.82L7 18H4a1 1 0 0 1-1-1v-6a1 1 0 0 1 1-1h3l5.46-3.59c.64-.45 1.54.03 1.54.82z" fill="currentColor"/>
  </svg>
);

const QuizIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24">
    <path d="M20 2H8a2 2 0 0 0-2 2v3H4a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3h2a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2Zm-4 18H4V9h12Zm4-5h-2V9a2 2 0 0 0-2-2H8V4h12Z" fill="currentColor"/>
  </svg>
);

const SummaryIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24">
    <path d="M6 2h9l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Zm8 1.5V8h4.5L14 3.5ZM8 11h8v2H8v-2Zm0 4h8v2H8v-2Z" fill="currentColor"/>
  </svg>
);

const LessonViewer: React.FC<LessonViewerProps> = ({
  lesson,
  microLessons,
  user,
  isProcessing = false,
  onProgressUpdate
}) => {
  const [adaptiveState, setAdaptiveState] = useState<AdaptiveLearningState | null>(null);
  const [currentMicroLesson, setCurrentMicroLesson] = useState<MicroLesson | null>(null);
  const [showQuiz, setShowQuiz] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transitionMessage, setTransitionMessage] = useState<string | null>(null);
  
  const { setLoading, isLoading } = useLoadingState();

  // Memoize stable values to prevent unnecessary re-renders
  const lessonId = lesson?.lesson_id;
  const microLessonCount = microLessons.length;
  const userPreferencesJson = useMemo(
    () => JSON.stringify(user.preferences),
    [user.preferences]
  );

  const initializeAdaptiveLearning = useCallback(async () => {
    if (!lessonId || microLessonCount === 0) return;

    try {
      setLoading('initialization', true, { timeout: 10000 });
      setError(null); // Clear any previous errors

      const state = await lessonService.initializeAdaptiveLearning(
        lessonId,
        JSON.parse(userPreferencesJson)
      );
      setAdaptiveState(state);

      // Set the first micro lesson
      const firstMicroLesson = microLessons.find(ml => ml.micro_lesson_id === state.current_micro_lesson_id);
      if (firstMicroLesson) {
        setCurrentMicroLesson(firstMicroLesson);
        console.log('✅ Adaptive learning initialized with micro-lesson:', firstMicroLesson.title);
      }
    } catch (error) {
      console.error('Failed to initialize adaptive learning:', error);
      // Fallback: directly load first micro lesson without adaptive state
      if (microLessons.length > 0) {
        console.log('⚠️ Using fallback: Loading first micro-lesson directly');
        setCurrentMicroLesson(microLessons[0]);
        setError(null); // Clear error since we have a fallback
      } else {
        setError('Failed to load lesson content');
      }
    } finally {
      setLoading('initialization', false);
    }
  }, [lessonId, microLessonCount, userPreferencesJson, microLessons, setLoading]);

  // Reset state when lesson changes
  useEffect(() => {
    console.log('📚 Lesson changed to:', lessonId);
    setCurrentMicroLesson(null);
    setAdaptiveState(null);
    setShowQuiz(false);
    setError(null);
  }, [lessonId]);

  // Display micro-lessons when available, but don't auto-initialize adaptive learning
  useEffect(() => {
    if (lessonId && microLessonCount > 0) {
      // Simply display the first micro-lesson without initializing adaptive session
      if (!currentMicroLesson) {
        console.log('📖 Displaying first micro-lesson for:', lessonId);
        setCurrentMicroLesson(microLessons[0]);
      }
    } else if (lessonId && microLessonCount === 0 && !isProcessing) {
      console.log('⏳ Lesson selected but no micro-lessons available...');
      setCurrentMicroLesson(null);
      setError(null);
    }
  }, [lessonId, microLessonCount, microLessons, currentMicroLesson, isProcessing]);

  const handleNextContent = useCallback(async () => {
    if (!lesson) return;

    // If adaptive state is not initialized, initialize it first
    if (!adaptiveState) {
      console.log('🚀 Initializing adaptive learning session on Continue click...');
      await initializeAdaptiveLearning();
      return;
    }

    try {
      setLoading('nextContent', true, { timeout: 15000 });
      setTransitionMessage('Determining your next learning step...');

      const nextContent = await lessonService.getNextAdaptiveContent(
        lesson.lesson_id,
        adaptiveState.current_micro_lesson_id,
        {
          quiz_scores: [], // Will be populated from quiz results
          time_spent: 0, // Track time spent on current content
          engagement_level: 0.8 // Default engagement level
        }
      );

      // Update progress
      if (onProgressUpdate) {
        onProgressUpdate(nextContent.progress_update.overall_progress);
      }

      // Handle different content types
      if (nextContent.content_type === 'quiz') {
        setShowQuiz(true);
        setTransitionMessage(nextContent.transition_reason);
      } else if (nextContent.content_type === 'micro_lesson' && nextContent.micro_lesson) {
        setCurrentMicroLesson(nextContent.micro_lesson);
        setTransitionMessage(nextContent.transition_reason);

        // Update adaptive state
        setAdaptiveState(prev => prev ? {
          ...prev,
          current_micro_lesson_id: nextContent.micro_lesson!.micro_lesson_id,
          progress: nextContent.progress_update.overall_progress,
          completed_micro_lessons: [...prev.completed_micro_lessons, prev.current_micro_lesson_id]
        } : null);
      } else if (nextContent.content_type === 'summary') {
        setTransitionMessage('Congratulations! You\'ve completed this lesson.');
        // Handle lesson completion
      }

      // Clear transition message after a delay
      setTimeout(() => setTransitionMessage(null), 3000);

    } catch (error) {
      console.error('Failed to get next adaptive content:', error);
      setError('Failed to load next content');
    } finally {
      setLoading('nextContent', false);
    }
  }, [lesson, adaptiveState, onProgressUpdate, initializeAdaptiveLearning]);

  const handleQuizComplete = useCallback(async (results: any) => {
    setShowQuiz(false);
    
    // Update adaptive state with quiz performance
    if (adaptiveState) {
      await lessonService.updateLearningProgress(
        adaptiveState.lesson_id,
        adaptiveState.current_micro_lesson_id,
        {
          quiz_score: results.overall_score,
          time_spent: results.time_spent_seconds,
          engagement_level: results.overall_score / 100
        }
      );
    }

    // Automatically proceed to next content
    setTimeout(() => {
      handleNextContent();
    }, 1000);
  }, [adaptiveState, handleNextContent]);

  const handleActionClick = useCallback((action: string, microLesson: MicroLesson) => {
    switch (action) {
      case 'quiz':
        setShowQuiz(true);
        break;
      case 'next':
        handleNextContent();
        break;
      case 'video':
        // Handle video playback
        if (microLesson.video_url) {
          window.open(microLesson.video_url, '_blank');
        }
        break;
      case 'audio':
        // Handle audio playback
        if (microLesson.audio_url) {
          window.open(microLesson.audio_url, '_blank');
        }
        break;
      default:
        break;
    }
  }, [handleNextContent]);

  if (isLoading('initialization') && !currentMicroLesson) {
    return <SkeletonLesson className="lesson-viewer-skeleton" />;
  }

  if (error) {
    return (
      <div className="lesson-viewer-error">
        <h3>Unable to load lesson</h3>
        <p>{error}</p>
        <button onClick={initializeAdaptiveLearning}>Try Again</button>
      </div>
    );
  }

  if (showQuiz && lesson && currentMicroLesson) {
    return (
      <QuizInterface
        lessonId={lesson.lesson_id}
        microLessonId={currentMicroLesson.micro_lesson_id}
        existingQuiz={currentMicroLesson.quiz}
        user={user}
        onQuizComplete={handleQuizComplete}
        onClose={() => setShowQuiz(false)}
      />
    );
  }

  return (
    <>
      <div className="panel-header">
        <span>My Snaps</span>
        {adaptiveState && (
          <div className="progress-indicator">
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${adaptiveState.progress}%` }}
              ></div>
            </div>
            <span className="progress-text">{Math.round(adaptiveState.progress)}% Complete</span>
          </div>
        )}
      </div>
      
      <div className="panel-body">
        {transitionMessage && (
          <div className="transition-message">
            <div className="transition-icon">🎯</div>
            <p>{transitionMessage}</p>
          </div>
        )}

        {isProcessing || (lesson && microLessons.length === 0 && !error) ? (
          <div className="processing-state">
            <div className="processing-header">
              <h3>🔄 Processing Your Lesson</h3>
              <p>Generating personalized micro-lessons...</p>
            </div>
            <div className="processing-progress">
              <div className="progress-bar-container">
                <div className="progress-bar-fill animating"></div>
              </div>
              <p className="progress-text">This usually takes 30-60 seconds</p>
            </div>
          </div>
        ) : !lesson ? (
          <>
            {/* Default content matching snapstudy.html */}
            <div className="card">
              <h3>Recap</h3>
              <p>Cosine similarity measures how close two vectors are in direction—great for comparing text embeddings.</p>
              <div className="actions">
                <button className="icon-btn">
                  <span className="ico"><PlayIcon /></span>
                  <span>Video</span>
                  <span className="meta">2:45</span>
                </button>
                <button className="icon-btn">
                  <span className="ico"><AudioIcon /></span>
                  <span>Audio</span>
                  <span className="meta">1:10</span>
                </button>
                <button className="icon-btn">
                  <span className="ico"><QuizIcon /></span>
                  <span>Quiz</span>
                </button>
                <button className="icon-btn">
                  <span className="ico"><SummaryIcon /></span>
                  <span>Summary</span>
                </button>
              </div>
            </div>

            <div className="card">
              <h3>Approximate Nearest Neighbor (ANN)</h3>
              <p>ANN indexes (HNSW, IVF-Flat) trade exactness for speed, enabling scalable similarity search with low latency.</p>
              <div className="actions">
                <button className="icon-btn">
                  <span className="ico"><PlayIcon /></span>
                  <span>Video</span>
                  <span className="meta">3:30</span>
                </button>
                <button className="icon-btn">
                  <span className="ico"><AudioIcon /></span>
                  <span>Audio</span>
                  <span className="meta">1:25</span>
                </button>
                <button className="icon-btn">
                  <span className="ico"><QuizIcon /></span>
                  <span>Quiz</span>
                </button>
                <button className="icon-btn">
                  <span className="ico"><SummaryIcon /></span>
                  <span>Summary</span>
                </button>
              </div>
            </div>
          </>
        ) : currentMicroLesson ? (
          <div className="adaptive-lesson-container">
            <div key={currentMicroLesson.micro_lesson_id} className="card current-lesson">
              <div className="lesson-header">
                <h3>{currentMicroLesson.title}</h3>
                {adaptiveState && (
                  <span className="lesson-sequence">
                    Lesson {currentMicroLesson.order} of {microLessons.length}
                  </span>
                )}
              </div>
              <p>{currentMicroLesson.summary}</p>
              <div className="actions">
                {currentMicroLesson.video_url && (
                  <button 
                    className="icon-btn"
                    onClick={() => handleActionClick('video', currentMicroLesson)}
                  >
                    <span className="ico"><PlayIcon /></span>
                    <span>Video</span>
                    {currentMicroLesson.video_duration && (
                      <span className="meta">{currentMicroLesson.video_duration}</span>
                    )}
                  </button>
                )}
                {currentMicroLesson.audio_url && (
                  <button 
                    className="icon-btn"
                    onClick={() => handleActionClick('audio', currentMicroLesson)}
                  >
                    <span className="ico"><AudioIcon /></span>
                    <span>Audio</span>
                    {currentMicroLesson.audio_duration && (
                      <span className="meta">{currentMicroLesson.audio_duration}</span>
                    )}
                  </button>
                )}
                <button 
                  className="icon-btn"
                  onClick={() => handleActionClick('quiz', currentMicroLesson)}
                >
                  <span className="ico"><QuizIcon /></span>
                  <span>Quiz</span>
                </button>
                <button 
                  className="icon-btn primary"
                  onClick={() => handleActionClick('next', currentMicroLesson)}
                  disabled={isLoading('nextContent')}
                >
                  <span className="ico">→</span>
                  <span>{isLoading('nextContent') ? 'Loading...' : 'Continue'}</span>
                </button>
              </div>
            </div>

            {/* Show upcoming lessons preview */}
            {adaptiveState && adaptiveState.learning_path.length > 1 && (
              <div className="upcoming-lessons">
                <h4>Coming Up Next</h4>
                <div className="lesson-preview">
                  {microLessons
                    .filter(ml => adaptiveState.learning_path.includes(ml.micro_lesson_id))
                    .slice(1, 3)
                    .map(ml => (
                      <div key={ml.micro_lesson_id} className="preview-card">
                        <h5>{ml.title}</h5>
                        <p>{ml.summary.substring(0, 100)}...</p>
                      </div>
                    ))
                  }
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="no-content">
            <p>No content available for this lesson.</p>
          </div>
        )}
      </div>
    </>
  );
};

export default LessonViewer;