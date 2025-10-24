import React, { useState, useEffect } from 'react';
import { AnalyticsDashboard as AnalyticsDashboardType, User, LearningVelocity } from '../types';
import { analyticsService } from '../services/analyticsService';
import ProgressCharts from './ProgressCharts';
import PerformanceMetrics from './PerformanceMetrics';
import { SkeletonDashboard } from './SkeletonLoader';
import { useLoadingState } from '../hooks/useLoadingState';
import './AnalyticsDashboard.css';

// SVG Icons matching main screen style
const BookIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 4h5v8l-2.5-1.5L6 12V4z"/>
  </svg>
);

const QuizIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M20 2H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-8.5 7.5c0 .83-.67 1.5-1.5 1.5H9v2H7.5V7H10c.83 0 1.5.67 1.5 1.5v1zm5 2c0 .83-.67 1.5-1.5 1.5h-2.5V7H15c.83 0 1.5.67 1.5 1.5v3zm4-3H19v1h1.5V11H19v2h-1.5V7h3v1.5zM9 9.5h1v-1H9v1zM4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm10 5.5h1v-3h-1v3z"/>
  </svg>
);

const ChartIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/>
  </svg>
);

const ClockIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/>
  </svg>
);

const RocketIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2.5s4.5 2.04 4.5 10.5c0 2.49-1.04 5.57-1.6 7H9.1c-.56-1.43-1.6-4.51-1.6-7C7.5 4.54 12 2.5 12 2.5zm-2 14h4c-.46 1.23-1.08 2.56-1.57 3.48-.23.43-.93.43-1.16 0C10.78 19.06 10.16 17.73 9.5 16.5h.5zM12 11c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z"/>
  </svg>
);

const TrendUpIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6z"/>
  </svg>
);

const TrendDownIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M16 18l2.29-2.29-4.88-4.88-4 4L2 7.41 3.41 6l6 6 4-4 6.3 6.29L22 12v6z"/>
  </svg>
);

const FireIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M13.5.67s.74 2.65.74 4.8c0 2.06-1.35 3.73-3.41 3.73-2.07 0-3.63-1.67-3.63-3.73l.03-.36C5.21 7.51 4 10.62 4 14c0 4.42 3.58 8 8 8s8-3.58 8-8C20 8.61 17.41 3.8 13.5.67zM11.71 19c-1.78 0-3.22-1.4-3.22-3.14 0-1.62 1.05-2.76 2.81-3.12 1.77-.36 3.6-1.21 4.62-2.58.39 1.29.59 2.65.59 4.04 0 2.65-2.15 4.8-4.8 4.8z"/>
  </svg>
);

const MedalIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 4l-1.5 4.5h-4.5l3.63 2.63L8.13 15.5 12 12.87l3.87 2.63-1.5-4.37L18 8.5h-4.5L12 4zm0 8l-1.88 1.37.72-2.13L9 10.5h2.3L12 8.37l.7 2.13H15l-1.88 1.37.72 2.13L12 12z"/>
  </svg>
);

const RefreshIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor">
    <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
  </svg>
);

interface AnalyticsDashboardProps {
  user: User;
}

const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({ user }) => {
  const [dashboard, setDashboard] = useState<AnalyticsDashboardType | null>(null);
  const [velocity, setVelocity] = useState<LearningVelocity | null>(null);
  const [strugglingConcepts, setStrugglingConcepts] = useState<any[]>([]);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState(7);
  
  const { setLoading, isLoading } = useLoadingState();

  useEffect(() => {
    loadAnalyticsData();
  }, [selectedPeriod]);

  const loadAnalyticsData = async () => {
    try {
      setLoading('dashboard', true, { timeout: 15000 });
      setError(null);

      // Load all analytics data in parallel
      const [
        dashboardData,
        velocityData,
        strugglingData,
        recommendationsData
      ] = await Promise.all([
        analyticsService.getDashboard(),
        analyticsService.getLearningVelocity(selectedPeriod),
        analyticsService.getStrugglingConcepts(),
        analyticsService.getRecommendations()
      ]);

      setDashboard(dashboardData);
      setVelocity(velocityData);
      setStrugglingConcepts(strugglingData.struggling_concepts || []);
      setRecommendations(recommendationsData.recommendations || []);

    } catch (error) {
      console.error('Failed to load analytics data:', error);
      setError('Failed to load analytics data. Please try again.');
    } finally {
      setLoading('dashboard', false);
    }
  };

  const formatLearningPace = (pace: string): { text: string; color: string; icon: React.ReactNode } => {
    switch (pace) {
      case 'fast':
        return { text: 'Fast Learner', color: '#4CAF50', icon: <RocketIcon /> };
      case 'moderate':
        return { text: 'Steady Progress', color: '#FF9800', icon: <TrendUpIcon /> };
      case 'slow':
        return { text: 'Taking Your Time', color: '#2196F3', icon: <TrendDownIcon /> };
      default:
        return { text: 'Getting Started', color: '#9E9E9E', icon: <TrendUpIcon /> };
    }
  };

  const getDifficultyColor = (difficulty: string): string => {
    switch (difficulty) {
      case 'mastered': return '#4CAF50';
      case 'comfortable': return '#8BC34A';
      case 'learning': return '#FF9800';
      case 'struggling': return '#F44336';
      default: return '#9E9E9E';
    }
  };

  const getPriorityColor = (priority: string): string => {
    switch (priority) {
      case 'high': return '#F44336';
      case 'medium': return '#FF9800';
      case 'low': return '#4CAF50';
      default: return '#9E9E9E';
    }
  };

  if (isLoading('dashboard')) {
    return <SkeletonDashboard className="analytics-dashboard-skeleton" />;
  }

  if (error) {
    return (
      <div className="analytics-dashboard error">
        <div className="error-message">
          <h3>Unable to load analytics</h3>
          <p>{error}</p>
          <button onClick={loadAnalyticsData} className="retry-button">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!dashboard || !velocity) {
    return (
      <div className="analytics-dashboard empty">
        <div className="empty-state">
          <h3>No analytics data available</h3>
          <p>Start learning to see your progress and analytics!</p>
        </div>
      </div>
    );
  }

  const paceInfo = formatLearningPace(velocity.learning_pace);

  return (
    <div className="analytics-dashboard">
      <div className="dashboard-header">
        <h2>Your Learning Analytics</h2>
        <div className="period-selector">
          <label>Time Period:</label>
          <select 
            value={selectedPeriod} 
            onChange={(e) => setSelectedPeriod(Number(e.target.value))}
          >
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
          </select>
        </div>
      </div>

      <div className="dashboard-grid">
        {/* Key Metrics Cards */}
        <div className="metrics-row">
          <div className="metric-card">
            <div className="metric-icon"><BookIcon /></div>
            <div className="metric-content">
              <div className="metric-value">{dashboard.metrics.lessons_completed}</div>
              <div className="metric-label">Lessons Completed</div>
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon"><QuizIcon /></div>
            <div className="metric-content">
              <div className="metric-value">{dashboard.metrics.quizzes_taken}</div>
              <div className="metric-label">Quizzes Taken</div>
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon"><ChartIcon /></div>
            <div className="metric-content">
              <div className="metric-value">{Math.round(dashboard.metrics.average_score)}%</div>
              <div className="metric-label">Average Score</div>
            </div>
          </div>

          <div className="metric-card">
            <div className="metric-icon"><ClockIcon /></div>
            <div className="metric-content">
              <div className="metric-value">{Math.round(dashboard.metrics.total_time_spent_minutes)}</div>
              <div className="metric-label">Minutes Studied</div>
            </div>
          </div>
        </div>

        {/* Learning Velocity */}
        <div className="velocity-card">
          <h3>Learning Velocity</h3>
          <div className="velocity-content">
            <div className="pace-indicator" style={{ color: paceInfo.color }}>
              <span className="pace-icon">{paceInfo.icon}</span>
              <span className="pace-text">{paceInfo.text}</span>
            </div>
            
            <div className="velocity-stats">
              <div className="velocity-stat">
                <span className="stat-value">{velocity.daily_averages.lessons}</span>
                <span className="stat-label">Lessons/day</span>
              </div>
              <div className="velocity-stat">
                <span className="stat-value">{velocity.daily_averages.quizzes}</span>
                <span className="stat-label">Quizzes/day</span>
              </div>
              <div className="velocity-stat">
                <span className="stat-value">{Math.round(velocity.daily_averages.time_minutes)}</span>
                <span className="stat-label">Minutes/day</span>
              </div>
            </div>
            
            <div className="activity-score">
              <div className="activity-bar">
                <div 
                  className="activity-fill" 
                  style={{ width: `${Math.min(velocity.activity_score, 100)}%` }}
                ></div>
              </div>
              <span className="activity-label">
                Activity Score: {Math.round(velocity.activity_score)}/100
              </span>
            </div>
          </div>
        </div>

        {/* Retention Metrics */}
        <div className="retention-card">
          <h3>Learning Consistency</h3>
          <div className="retention-content">
            <div className="streak-info">
              <div className="streak-stat">
                <span className="streak-icon"><FireIcon /></span>
                <div className="streak-details">
                  <span className="streak-value">{dashboard.retention.current_streak}</span>
                  <span className="streak-label">Current Streak</span>
                </div>
              </div>

              <div className="streak-stat">
                <span className="streak-icon"><MedalIcon /></span>
                <div className="streak-details">
                  <span className="streak-value">{dashboard.retention.longest_streak}</span>
                  <span className="streak-label">Best Streak</span>
                </div>
              </div>
            </div>
            
            <div className="consistency-metrics">
              <div className="consistency-item">
                <span className="consistency-label">Retention Rate</span>
                <span className="consistency-value">{dashboard.retention.retention_rate}%</span>
              </div>
              <div className="consistency-item">
                <span className="consistency-label">Consistency Score</span>
                <span className="consistency-value">{dashboard.retention.consistency_score}%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Learning Patterns */}
        <div className="patterns-card">
          <h3>Learning Patterns</h3>
          <div className="patterns-content">
            {dashboard.learning_patterns.map((pattern, index) => (
              <div key={index} className="pattern-tag">
                {pattern.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </div>
            ))}
          </div>
        </div>

        {/* Progress Charts */}
        <div className="charts-section">
          <ProgressCharts 
            dashboard={dashboard}
            velocity={velocity}
          />
        </div>

        {/* Performance Metrics */}
        <div className="performance-section">
          <PerformanceMetrics 
            dashboard={dashboard}
            strugglingConcepts={strugglingConcepts}
          />
        </div>

        {/* Struggling Concepts */}
        {strugglingConcepts.length > 0 && (
          <div className="struggling-concepts-card">
            <h3>Areas for Improvement</h3>
            <div className="concepts-list">
              {strugglingConcepts.slice(0, 5).map((concept, index) => (
                <div key={index} className="concept-item">
                  <div className="concept-info">
                    <span className="concept-name">{concept.concept}</span>
                    <span className="concept-score">{Math.round(concept.recent_average)}%</span>
                  </div>
                  <div className="concept-details">
                    <span className="attempts">Attempts: {concept.attempts}</span>
                    <span className={`trend ${concept.improvement_trend}`}>
                      {concept.improvement_trend === 'improving' ? <TrendUpIcon /> : <TrendDownIcon />} {concept.improvement_trend}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recommendations */}
        {recommendations.length > 0 && (
          <div className="recommendations-card">
            <h3>Personalized Recommendations</h3>
            <div className="recommendations-list">
              {recommendations.map((rec, index) => (
                <div 
                  key={index} 
                  className={`recommendation-item priority-${rec.priority}`}
                  style={{ borderLeftColor: getPriorityColor(rec.priority) }}
                >
                  <div className="recommendation-header">
                    <span className="recommendation-title">{rec.title}</span>
                    <span className={`priority-badge priority-${rec.priority}`}>
                      {rec.priority.toUpperCase()}
                    </span>
                  </div>
                  <p className="recommendation-description">{rec.description}</p>
                  <div className="recommendation-meta">
                    <span className="recommendation-type">{rec.type}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="dashboard-footer">
        <p className="last-updated">
          Last updated: {new Date(dashboard.generated_at).toLocaleString()}
        </p>
        <button onClick={loadAnalyticsData} className="refresh-button">
          <RefreshIcon /> Refresh Data
        </button>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;