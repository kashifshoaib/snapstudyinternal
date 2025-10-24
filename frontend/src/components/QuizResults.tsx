import React from 'react';
import { Quiz, QuizResults as QuizResultsType, QuestionResult } from '../types';
import './QuizResults.css';

interface QuizResultsProps {
  results: QuizResultsType;
  quiz: Quiz;
  onRetakeQuiz?: () => void;
  onClose?: () => void;
}

const QuizResults: React.FC<QuizResultsProps> = ({ 
  results, 
  quiz, 
  onRetakeQuiz, 
  onClose 
}) => {
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getScoreColor = (score: number): string => {
    if (score >= 90) return '#4CAF50'; // Green
    if (score >= 75) return '#FF9800'; // Orange
    if (score >= 60) return '#FFC107'; // Yellow
    return '#F44336'; // Red
  };

  const getPerformanceMessage = (score: number): string => {
    if (score >= 90) return 'Excellent work! 🎉';
    if (score >= 75) return 'Great job! 👏';
    if (score >= 60) return 'Good effort! 👍';
    return 'Keep practicing! 💪';
  };

  const getScoreIcon = (score: number): string => {
    if (score >= 90) return '🏆';
    if (score >= 75) return '⭐';
    if (score >= 60) return '✅';
    return '📚';
  };

  return (
    <div className="quiz-results">
      <div className="results-header">
        <div className="score-circle" style={{ borderColor: getScoreColor(results.overall_score) }}>
          <div className="score-icon">{getScoreIcon(results.overall_score)}</div>
          <div className="score-percentage">{Math.round(results.overall_score)}%</div>
        </div>
        
        <div className="results-summary">
          <h2>{getPerformanceMessage(results.overall_score)}</h2>
          <div className="summary-stats">
            <div className="stat">
              <span className="stat-label">Score</span>
              <span className="stat-value">{Math.round(results.overall_score)}%</span>
            </div>
            <div className="stat">
              <span className="stat-label">Correct</span>
              <span className="stat-value">{results.correct_count}/{results.total_questions}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Time</span>
              <span className="stat-value">{formatTime(results.time_spent_seconds)}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Status</span>
              <span className={`stat-value ${results.passed ? 'passed' : 'failed'}`}>
                {results.passed ? 'Passed' : 'Failed'}
              </span>
            </div>
          </div>
        </div>

        {onClose && (
          <button onClick={onClose} className="close-results-button">
            ✕
          </button>
        )}
      </div>

      {results.feedback && (
        <div className="overall-feedback">
          <h3>Feedback</h3>
          <p>{results.feedback}</p>
        </div>
      )}

      <div className="question-breakdown">
        <h3>Question Breakdown</h3>
        <div className="questions-list">
          {results.question_results.map((questionResult, index) => {
            const question = quiz.questions.find(q => q.id === questionResult.question_id);
            
            return (
              <div 
                key={questionResult.question_id} 
                className={`question-result ${questionResult.is_correct ? 'correct' : 'incorrect'}`}
              >
                <div className="question-header">
                  <div className="question-number">
                    <span className="number">{index + 1}</span>
                    <span className={`result-icon ${questionResult.is_correct ? 'correct' : 'incorrect'}`}>
                      {questionResult.is_correct ? '✓' : '✗'}
                    </span>
                  </div>
                  <div className="question-text">
                    {question?.question || 'Question not found'}
                  </div>
                  <div className="question-score">
                    {Math.round(questionResult.score * 100)}%
                  </div>
                </div>
                
                <div className="answer-details">
                  <div className="answer-row">
                    <span className="answer-label">Your answer:</span>
                    <span className={`answer-value ${questionResult.is_correct ? 'correct' : 'incorrect'}`}>
                      {questionResult.user_answer}
                    </span>
                  </div>
                  
                  {!questionResult.is_correct && (
                    <div className="answer-row">
                      <span className="answer-label">Correct answer:</span>
                      <span className="answer-value correct">
                        {questionResult.correct_answer}
                      </span>
                    </div>
                  )}
                  
                  {questionResult.feedback && (
                    <div className="question-feedback">
                      <span className="feedback-label">Explanation:</span>
                      <p className="feedback-text">{questionResult.feedback}</p>
                    </div>
                  )}
                  
                  {questionResult.suggestions && (
                    <div className="question-suggestions">
                      <span className="suggestions-label">Suggestion:</span>
                      <p className="suggestions-text">{questionResult.suggestions}</p>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {results.recommendations && results.recommendations.length > 0 && (
        <div className="recommendations">
          <h3>Recommendations</h3>
          <ul className="recommendations-list">
            {results.recommendations.map((recommendation, index) => (
              <li key={index} className="recommendation-item">
                {recommendation}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="results-actions">
        {onRetakeQuiz && (
          <button onClick={onRetakeQuiz} className="retake-button">
            🔄 Retake Quiz
          </button>
        )}
        
        <button 
          onClick={() => window.print()} 
          className="print-button"
        >
          🖨️ Print Results
        </button>
        
        {onClose && (
          <button onClick={onClose} className="close-button">
            Continue Learning
          </button>
        )}
      </div>
    </div>
  );
};

export default QuizResults;