import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Quiz, QuizQuestion, QuizResults as QuizResultsType, User } from '../types';
import { quizService } from '../services/quizService';
import { analyticsService } from '../services/analyticsService';
import QuizResults from './QuizResults';
import { SkeletonQuiz } from './SkeletonLoader';
import { useLoadingState } from '../hooks/useLoadingState';
import { debounce } from '../utils/apiOptimization';
import './QuizInterface.css';

interface QuizInterfaceProps {
  lessonId: string;
  user: User;
  onQuizComplete?: (results: QuizResultsType) => void;
  onClose?: () => void;
}

const QuizInterface: React.FC<QuizInterfaceProps> = ({ 
  lessonId, 
  user, 
  onQuizComplete, 
  onClose 
}) => {
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [answerFeedback, setAnswerFeedback] = useState<Record<string, any>>({});
  const [results, setResults] = useState<QuizResultsType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showHint, setShowHint] = useState(false);
  const [hint, setHint] = useState<string | null>(null);
  const [timeSpent, setTimeSpent] = useState(0);
  const [startTime] = useState(Date.now());
  const [questionStartTime, setQuestionStartTime] = useState(Date.now());
  const [questionTimes, setQuestionTimes] = useState<Record<string, number>>({});
  
  const { setLoading, isLoading } = useLoadingState();

  useEffect(() => {
    generateQuiz();
  }, [lessonId]);

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeSpent(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    return () => clearInterval(timer);
  }, [startTime]);

  const generateQuiz = async () => {
    try {
      setLoading('quiz', true, { timeout: 10000 });
      setError(null);
      
      // Generate adaptive quiz based on user preferences and performance
      const quizData = await quizService.generateQuiz(
        lessonId, 
        user.preferences?.difficulty_level || 'adaptive',
        5 // Default number of questions
      );
      
      setQuiz(quizData);
      setQuestionStartTime(Date.now());
      quizService.startQuizTimer();
      
      // Track quiz generation
      await analyticsService.trackEngagementEvent('quiz_generated', {
        quiz_id: quizData.quiz_id,
        lesson_id: lessonId,
        difficulty: quizData.difficulty_level,
        num_questions: quizData.total_questions,
        adaptive_features: quizData.quiz_metadata.adaptive_features || []
      });
      
    } catch (error) {
      console.error('Failed to generate quiz:', error);
      setError('Failed to generate quiz. Please try again.');
    } finally {
      setLoading('quiz', false);
    }
  };

  // Debounced feedback function to prevent excessive API calls
  const debouncedFeedbackRef = useRef<ReturnType<typeof debounce> | null>(null);

  useEffect(() => {
    // Create debounced function that waits 500ms after user stops selecting answers
    debouncedFeedbackRef.current = debounce(
      async (quizId: string, questionId: string, answer: string) => {
        try {
          const feedback = await quizService.getImmediateFeedback(quizId, questionId, answer);
          if (feedback && feedback.show_immediate_feedback) {
            setAnswerFeedback(prev => ({
              ...prev,
              [questionId]: feedback
            }));
          }
        } catch (error) {
          console.error('Failed to get immediate feedback:', error);
        }
      },
      500 // Wait 500ms after user stops selecting
    );

    return () => {
      // Cleanup: cancel any pending debounced calls
      if (debouncedFeedbackRef.current) {
        debouncedFeedbackRef.current.cancel();
      }
    };
  }, []);

  const handleAnswerChange = (questionId: string, answer: string) => {
    // Update answer immediately for UI responsiveness
    setAnswers(prev => ({
      ...prev,
      [questionId]: answer
    }));

    // Call debounced feedback function to reduce API calls
    if (quiz && debouncedFeedbackRef.current) {
      debouncedFeedbackRef.current(quiz.quiz_id, questionId, answer);
    }
  };

  const handleNextQuestion = async () => {
    if (!quiz) return;
    
    const currentQuestion = quiz.questions[currentQuestionIndex];
    const timeOnQuestion = (Date.now() - questionStartTime) / 1000;
    
    // Track time spent on current question
    setQuestionTimes(prev => ({
      ...prev,
      [currentQuestion.id]: timeOnQuestion
    }));

    // Submit question progress to backend
    if (answers[currentQuestion.id]) {
      await quizService.submitQuestionProgress(
        quiz.quiz_id,
        currentQuestion.id,
        timeOnQuestion,
        1 // For now, assume 1 attempt per question
      );
    }

    if (currentQuestionIndex < quiz.questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1);
      setQuestionStartTime(Date.now());
      setShowHint(false);
      setHint(null);
    }
  };

  const handlePreviousQuestion = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1);
      setQuestionStartTime(Date.now());
      setShowHint(false);
      setHint(null);
    }
  };

  const handleGetHint = async () => {
    if (!quiz) return;
    
    const currentQuestion = quiz.questions[currentQuestionIndex];
    
    try {
      const hintData = await quizService.getHint(
        quiz.quiz_id,
        currentQuestion.id,
        'Student requested help',
        answers[currentQuestion.id] ? [answers[currentQuestion.id]] : []
      );
      
      setHint(hintData.hint_text || 'Here\'s a hint to help you think about this question.');
      setShowHint(true);
      
      // Track hint request
      await analyticsService.trackEngagementEvent('hint_requested', {
        quiz_id: quiz.quiz_id,
        question_id: currentQuestion.id,
        hint_type: hintData.hint_type || 'general'
      });
      
    } catch (error) {
      console.error('Failed to get hint:', error);
      setHint('Sorry, I couldn\'t generate a hint right now. Try thinking about the key concepts from the lesson.');
      setShowHint(true);
    }
  };

  const handleSubmitQuiz = async () => {
    if (!quiz) return;
    
    try {
      setLoading('submit', true, { timeout: 10000 });
      
      // Calculate detailed engagement metrics
      const totalHintsUsed = Object.keys(answerFeedback).length + (showHint ? 1 : 0);
      const averageTimePerQuestion = Object.values(questionTimes).length > 0 
        ? Object.values(questionTimes).reduce((a, b) => a + b, 0) / Object.values(questionTimes).length
        : timeSpent / quiz.questions.length;
      
      const engagementMetrics = {
        questions_attempted: Object.keys(answers).length,
        hints_used: totalHintsUsed,
        time_per_question: averageTimePerQuestion,
        question_times: questionTimes,
        immediate_feedback_used: Object.keys(answerFeedback).length,
        completion_rate: (Object.keys(answers).length / quiz.questions.length) * 100,
        user_preferences: {
          difficulty_level: user.preferences?.difficulty_level,
          learning_style: user.preferences?.learning_style,
          attention_span: user.preferences?.attention_span
        }
      };

      const quizResults = await quizService.submitQuiz(
        quiz.quiz_id,
        answers,
        timeSpent,
        engagementMetrics
      );
      
      setResults(quizResults);
      
      // Track quiz completion with enhanced analytics
      await analyticsService.trackQuizCompleted(
        quiz.quiz_id,
        quizResults.overall_score,
        timeSpent
      );

      // Track detailed engagement metrics
      await analyticsService.trackEngagementEvent('quiz_completed_detailed', {
        quiz_id: quiz.quiz_id,
        lesson_id: lessonId,
        score: quizResults.overall_score,
        time_spent: timeSpent,
        engagement_metrics: engagementMetrics
      });
      
      if (onQuizComplete) {
        onQuizComplete(quizResults);
      }
      
    } catch (error) {
      console.error('Failed to submit quiz:', error);
      setError('Failed to submit quiz. Please try again.');
    } finally {
      setLoading('submit', false);
    }
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const isQuizComplete = quiz && Object.keys(answers).length === quiz.questions.length;

  if (isLoading('quiz') && !quiz) {
    return <SkeletonQuiz className="quiz-interface-skeleton" />;
  }

  if (error) {
    return (
      <div className="quiz-interface error">
        <div className="error-message">
          <h3>Oops! Something went wrong</h3>
          <p>{error}</p>
          <button onClick={generateQuiz} className="retry-button">
            Try Again
          </button>
          {onClose && (
            <button onClick={onClose} className="close-button">
              Close
            </button>
          )}
        </div>
      </div>
    );
  }

  if (results) {
    return (
      <QuizResults 
        results={results} 
        quiz={quiz!}
        onRetakeQuiz={() => {
          setResults(null);
          setAnswers({});
          setCurrentQuestionIndex(0);
          generateQuiz();
        }}
        onClose={onClose}
      />
    );
  }

  if (!quiz) {
    return null;
  }

  const currentQuestion = quiz.questions[currentQuestionIndex];
  const progress = ((currentQuestionIndex + 1) / quiz.questions.length) * 100;

  return (
    <div className="quiz-interface">
      <div className="quiz-header">
        <div className="quiz-progress">
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          <span className="progress-text">
            Question {currentQuestionIndex + 1} of {quiz.questions.length}
          </span>
        </div>
        
        <div className="quiz-info">
          <span className="time-spent">Time: {formatTime(timeSpent)}</span>
          <span className="difficulty">Difficulty: {quiz.difficulty_level}</span>
        </div>
        
        {onClose && (
          <button onClick={onClose} className="close-quiz-button">
            ✕
          </button>
        )}
      </div>

      <div className="quiz-content">
        <div className="question-container">
          <h3 className="question-text">{currentQuestion.question}</h3>
          
          <div className="answer-options">
            <div className="multiple-choice">
              {currentQuestion.options.map((option, index) => {
                const isSelected = answers[currentQuestion.id] === option;
                const feedback = answerFeedback[currentQuestion.id];
                const showFeedbackForOption = feedback && isSelected;
                
                return (
                  <label key={index} className={`option-label ${isSelected ? 'selected' : ''} ${showFeedbackForOption ? 'has-feedback' : ''}`}>
                    <input
                      type="radio"
                      name={currentQuestion.id}
                      value={option}
                      checked={isSelected}
                      onChange={(e) => handleAnswerChange(currentQuestion.id, e.target.value)}
                    />
                    <span className="option-text">{option}</span>
                    {showFeedbackForOption && (
                      <div className={`immediate-feedback ${feedback.is_correct ? 'correct' : 'incorrect'}`}>
                        <div className="feedback-icon">
                          {feedback.is_correct ? '✓' : '✗'}
                        </div>
                        <div className="feedback-text">
                          {feedback.feedback_text || (feedback.is_correct ? 'Correct!' : 'Not quite right.')}
                        </div>
                      </div>
                    )}
                  </label>
                );
              })}
            </div>
          </div>

          {showHint && hint && (
            <div className="hint-container">
              <div className="hint-icon">💡</div>
              <div className="hint-text">{hint}</div>
            </div>
          )}
        </div>

        <div className="quiz-actions">
          <div className="navigation-buttons">
            <button
              onClick={handlePreviousQuestion}
              disabled={currentQuestionIndex === 0}
              className="nav-button prev-button"
            >
              ← Previous
            </button>
            
            <button
              onClick={handleGetHint}
              className="hint-button"
              disabled={showHint}
            >
              💡 Get Hint
            </button>
            
            {currentQuestionIndex < quiz.questions.length - 1 ? (
              <button
                onClick={handleNextQuestion}
                className="nav-button next-button"
              >
                Next →
              </button>
            ) : (
              <button
                onClick={handleSubmitQuiz}
                disabled={!isQuizComplete || isLoading('submit')}
                className="submit-button"
              >
                {isLoading('submit') ? 'Submitting...' : 'Submit Quiz'}
              </button>
            )}
          </div>
          
          <div className="quiz-status">
            <span className="answered-count">
              Answered: {Object.keys(answers).length} / {quiz.questions.length}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default QuizInterface;