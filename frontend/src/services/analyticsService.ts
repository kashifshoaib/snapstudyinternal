import api from './api';

class AnalyticsService {
  private useBackendAPI = false; // Set to true when backend is configured

  recordMetric(name: string, value: number, metadata?: Record<string, any>): void {
    // Simple analytics recording - in production this would send to a real analytics service
    console.log(`Analytics: ${name} = ${value}`, metadata);

    // Store locally for now
    const analytics = JSON.parse(localStorage.getItem('analytics') || '[]');
    analytics.push({
      name,
      value,
      metadata,
      timestamp: new Date().toISOString()
    });

    // Keep only last 100 events
    if (analytics.length > 100) {
      analytics.splice(0, analytics.length - 100);
    }

    localStorage.setItem('analytics', JSON.stringify(analytics));
  }

  getMetrics(): any[] {
    return JSON.parse(localStorage.getItem('analytics') || '[]');
  }

  // Dashboard data - uses backend API if available, falls back to mock data
  async getDashboard(): Promise<any> {
    if (this.useBackendAPI) {
      try {
        const response = await api.get('/api/v1/analytics/dashboard');
        return response.data;
      } catch (error) {
        console.error('Failed to fetch dashboard from backend, using mock data:', error);
      }
    }

    // Mock data fallback
    return {
      metrics: {
        lessons_completed: 12,
        quizzes_taken: 8,
        average_score: 85,
        total_time_spent_minutes: 240
      },
      retention: {
        current_streak: 5,
        longest_streak: 12,
        retention_rate: 78,
        consistency_score: 82
      },
      learning_patterns: ['visual_learner', 'morning_study', 'quick_sessions'],
      generated_at: new Date().toISOString()
    };
  }

  async getLearningVelocity(period: number): Promise<any> {
    if (this.useBackendAPI) {
      try {
        const response = await api.get(`/api/v1/analytics/velocity?period=${period}`);
        return response.data;
      } catch (error) {
        console.error('Failed to fetch velocity from backend, using mock data:', error);
      }
    }

    // Mock data fallback
    return {
      learning_pace: 'moderate',
      daily_averages: {
        lessons: 1.7,
        quizzes: 1.1,
        time_minutes: 34
      },
      activity_score: 75
    };
  }

  async getStrugglingConcepts(): Promise<any> {
    if (this.useBackendAPI) {
      try {
        const response = await api.get('/api/v1/analytics/struggling-concepts');
        return response.data;
      } catch (error) {
        console.error('Failed to fetch struggling concepts from backend, using mock data:', error);
      }
    }

    // Mock data fallback
    return {
      struggling_concepts: [
        {
          concept: 'Calculus Integration',
          recent_average: 65,
          attempts: 8,
          improvement_trend: 'improving'
        },
        {
          concept: 'Organic Chemistry',
          recent_average: 58,
          attempts: 12,
          improvement_trend: 'declining'
        }
      ]
    };
  }

  async getRecommendations(): Promise<any> {
    if (this.useBackendAPI) {
      try {
        const response = await api.get('/api/v1/analytics/recommendations');
        return response.data;
      } catch (error) {
        console.error('Failed to fetch recommendations from backend, using mock data:', error);
      }
    }

    // Mock data fallback
    return {
      recommendations: [
        {
          title: 'Review Integration Techniques',
          description: 'Focus on integration by parts and substitution methods',
          type: 'study_focus',
          priority: 'high'
        },
        {
          title: 'Practice More Quizzes',
          description: 'Take more practice quizzes to improve retention',
          type: 'activity',
          priority: 'medium'
        }
      ]
    };
  }

  // Additional tracking methods
  async trackEngagementEvent(event: string, data: any): Promise<void> {
    this.recordMetric(event, 1, data);

    if (this.useBackendAPI) {
      try {
        await api.post('/api/v1/analytics/track-event', {
          event_name: event,
          event_data: data
        });
      } catch (error) {
        console.error('Failed to track event to backend:', error);
      }
    }
  }

  async trackQuizCompleted(quizId: string, score: number, timeSpent: number): Promise<void> {
    this.recordMetric('quiz_completed', score, { quizId, timeSpent });

    if (this.useBackendAPI) {
      await this.trackEngagementEvent('quiz_completed', { quizId, score, timeSpent });
    }
  }

  async trackLessonCompleted(lessonId: string, timeSpent: number): Promise<void> {
    this.recordMetric('lesson_completed', timeSpent, { lessonId });

    if (this.useBackendAPI) {
      await this.trackEngagementEvent('lesson_completed', { lessonId, timeSpent });
    }
  }

  async trackStudySession(duration: number, activities: any[]): Promise<void> {
    this.recordMetric('study_session', duration, { activities });

    if (this.useBackendAPI) {
      await this.trackEngagementEvent('study_session', { duration, activities });
    }
  }

  async trackError(errorReport: any): Promise<void> {
    this.recordMetric('error_occurred', 1, errorReport);

    if (this.useBackendAPI) {
      try {
        await api.post('/api/v1/analytics/track-error', errorReport);
      } catch (error) {
        console.error('Failed to track error to backend:', error);
      }
    }
  }
}

export const analyticsService = new AnalyticsService();