import api from './api';
import { Quiz, QuizResults, QuizSubmission } from '../types';

interface GenerateQuizRequest {
  lesson_id: string;
  user_id: string;
  target_difficulty?: string;
  num_questions?: number;
  question_types?: string[];
}

interface SubmitQuizRequest {
  quiz_id: string;
  user_id: string;
  answers: Record<string, string>;
  time_spent_seconds: number;
  engagement_metrics?: Record<string, any>;
}

interface HintRequest {
  quiz_id: string;
  question_id: string;
  user_id: string;
  user_context?: string;
  previous_attempts?: string[];
}

class QuizService {
  private startTime: number = 0;

  async generateQuiz(lessonId: string, difficulty?: string, numQuestions?: number): Promise<Quiz> {
    try {
      const response = await api.post('/api/v1/quiz/generate', {
        lesson_id: lessonId,
        user_id: 'current', // Will be handled by auth middleware
        target_difficulty: difficulty || 'adaptive',
        num_questions: numQuestions || 5
      });

      return response.data;
    } catch (error) {
      console.error('Error generating quiz:', error);
      throw error;
    }
  }

  async generateQuizForMicroLesson(microLessonId: string, difficulty?: string, numQuestions?: number): Promise<Quiz> {
    try {
      const response = await api.post('/api/v1/quiz/generate', {
        micro_lesson_id: microLessonId,
        target_difficulty: difficulty || 'intermediate',
        num_questions: numQuestions || 5
      });

      return response.data;
    } catch (error) {
      console.error('Error generating quiz for micro-lesson:', error);
      throw error;
    }
  }

  async submitQuiz(
    quizId: string,
    answers: Record<string, string>,
    timeSpent?: number,
    engagementMetrics?: Record<string, any>
  ): Promise<QuizResults> {
    try {
      const response = await api.post('/api/v1/quiz/submit', {
        quiz_id: quizId,
        user_id: 'current', // Will be handled by auth middleware
        answers,
        time_spent_seconds: timeSpent || (Date.now() - this.startTime) / 1000,
        engagement_metrics: engagementMetrics || {}
      });

      return response.data;
    } catch (error) {
      console.error('Error submitting quiz:', error);
      throw error;
    }
  }

  async getQuizResults(quizId: string): Promise<QuizResults> {
    try {
      const response = await api.get(`/api/v1/quiz/results/${quizId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching quiz results:', error);
      throw error;
    }
  }

  async getHint(quizId: string, questionId: string, context?: string, previousAttempts?: string[]): Promise<any> {
    try {
      const response = await api.post('/api/v1/quiz/hint', {
        quiz_id: quizId,
        question_id: questionId,
        struggle_context: context || 'Student requested help',
        previous_answers: previousAttempts || []
      });

      return response.data;
    } catch (error) {
      console.error('Error getting hint:', error);
      throw error;
    }
  }

  async regenerateQuestion(quizId: string, questionId: string, difficultyAdjustment?: string): Promise<any> {
    try {
      const response = await api.post('/api/v1/quiz/regenerate', {
        quiz_id: quizId,
        question_id: questionId,
        user_id: 'current', // Will be handled by auth middleware
        difficulty_adjustment: difficultyAdjustment
      });

      return response.data;
    } catch (error) {
      console.error('Error regenerating question:', error);
      throw error;
    }
  }

  async getQuizAnalytics(limit?: number): Promise<any> {
    try {
      const response = await api.get(`/api/v1/quiz/analytics/current?limit=${limit || 20}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching quiz analytics:', error);
      throw error;
    }
  }

  async getImmediateFeedback(quizId: string, questionId: string, answer: string): Promise<any> {
    try {
      const response = await api.post('/api/v1/quiz/immediate-feedback', {
        quiz_id: quizId,
        question_id: questionId,
        user_answer: answer
      });

      return response.data;
    } catch (error) {
      console.error('Error getting immediate feedback:', error);
      throw error;
    }
  }

  async submitQuestionProgress(quizId: string, questionId: string, timeSpent: number, attempts: number): Promise<void> {
    try {
      await api.post('/api/v1/quiz/question-progress', {
        quiz_id: quizId,
        question_id: questionId,
        time_spent_seconds: timeSpent,
        attempts_count: attempts,
        user_id: 'current' // Will be handled by auth middleware
      });
    } catch (error) {
      console.error('Error submitting question progress:', error);
      // Don't throw error as this is not critical
    }
  }

  startQuizTimer(): void {
    this.startTime = Date.now();
  }

  getElapsedTime(): number {
    return this.startTime ? (Date.now() - this.startTime) / 1000 : 0;
  }
}

export const quizService = new QuizService();