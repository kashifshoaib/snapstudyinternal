export interface User {
  id: string;
  email: string;
  username?: string;
  first_name?: string;
  last_name?: string;
  full_name?: string;
  age?: number;
  profession?: string;
  education_level?: string;
  country?: string;
  onboarding_completed?: boolean;
  preferences?: UserPreferences;
}

export interface Lesson {
  lesson_id: string;
  user_id: string;
  title: string;
  content_type: string;
  s3_key: string;
  status: 'processing' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
  original_filename?: string;
  original_file_s3_key?: string;
  original_file_size?: number;
  original_file_content_type?: string;
}

export interface MicroLesson {
  micro_lesson_id: string;
  lesson_id: string;
  title: string;
  content: string;
  summary: string;
  order: number; // Maps to sequence_number from backend
  estimated_duration_minutes: number;
  key_concepts?: string[];
  learning_objectives?: string[];
  examples?: Array<{ title: string; description: string }>;
  visual_aids?: string[];
  quiz?: {
    quiz_id: string;
    questions: any[];
    total_questions: number;
    passing_score: number;
  };
  video_url?: string;
  audio_url?: string;
  video_duration?: string;
  audio_duration?: string;
  created_at?: string;
}

export interface QuizQuestion {
  id: string;
  question: string;
  options: string[];
  correct_answer: string;
  question_type?: string; // 'multiple_choice', 'true_false', 'short_answer'
}



export interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'ai';
  timestamp: Date;
}

export interface ChatResponse {
  success: boolean;
  session_id: string;
  message: string;
  response: string;  // The actual AI response message
  intent?: string | null;
  confidence: string;
  autonomous_recognition: boolean;
  timestamp: string;
}

export interface UserProfile {
  user_id: string;
  email: string;
  username?: string;
  first_name?: string;
  last_name?: string;
  profile_picture?: string;
  created_at: string;
  updated_at: string;
  last_login: string;
  preferences: UserPreferences;
}

export interface UserPreferences {
  learning_style: 'visual' | 'auditory' | 'reading';
  attention_span: number; // minutes
  difficulty_level: 'beginner' | 'intermediate' | 'advanced';
}

export interface OnboardingData {
  // Personal info
  full_name?: string;
  age?: number;
  profession?: string;
  education_level?: string;
  country?: string;

  // Learning preferences
  learning_style: 'visual' | 'auditory' | 'reading';
  attention_span: number;
  difficulty_level: 'beginner' | 'intermediate' | 'advanced';
}

export interface Quiz {
  quiz_id: string;
  micro_lesson_id?: string;
  lesson_id?: string;
  questions: QuizQuestion[];
  total_questions: number;
  passing_score: number;
  difficulty_level: string;
  estimated_duration_minutes: number;
  quiz_metadata: QuizMetadata;
  instructions?: string;
  hints_available?: boolean;
}

export interface QuizMetadata {
  total_questions: number;
  passing_score: number;
  difficulty_level: string;
  estimated_duration_minutes: number;
  adaptive_features?: string[];
}

// Multimedia Types
export interface VoiceProfile {
  VoiceId: string;
  Engine: string;
  LanguageCode: string;
  speaking_rate?: string;
  volume?: string;
}

export interface VisualStyle {
  style: string;
  color_scheme: string;
  background: string;
  typography: string;
}

export interface Timestamp {
  time_seconds: number;
  concept: string;
  type: string;
  visual_element?: string;
}

export interface InteractiveElement {
  type: string;
  time_seconds: number;
  title: string;
  description: string;
  interaction?: string;
}

export interface AudioLesson {
  audio_lesson_id: string;
  text_lesson_id: string;
  title: string;
  audio_url: string;
  duration_seconds: number;
  file_size_bytes: number;
  voice_profile: VoiceProfile;
  learning_adaptations: Record<string, any>;
  transcript: string;
  key_timestamps: Timestamp[];
  generated_at: string;
  format: string;
  sample_rate: string;
}

export interface VideoLesson {
  video_lesson_id: string;
  text_lesson_id: string;
  title: string;
  video_url: string;
  duration_seconds: number;
  file_size_bytes: number;
  resolution: string;
  frame_rate: number;
  visual_style: VisualStyle;
  learning_adaptations: Record<string, any>;
  script: Record<string, any>;
  scenes: string[];
  narration_metadata: Record<string, any>;
  key_timestamps: Timestamp[];
  interactive_elements: InteractiveElement[];
  generated_at: string;
  format: string;
}

export interface MultimediaPreferences {
  voice_preference: string;
  tone_preference: string;
  speaking_rate: string;
  audio_volume: string;
  visual_style: string;
  include_narration: boolean;
  include_subtitles: boolean;
  video_quality: string;
}

export interface GenerationStatus {
  lesson_id: string;
  text_lesson: {
    status: string;
    available: boolean;
  };
  audio_lesson: {
    status: string;
    available: boolean;
    audio_lesson_id?: string;
  };
  video_lesson: {
    status: string;
    available: boolean;
    video_lesson_id?: string;
  };
  generation_options: {
    can_generate_audio: boolean;
    can_generate_video: boolean;
    estimated_audio_time: string;
    estimated_video_time: string;
  };
}

export interface QuizResults {
  quiz_id: string;
  overall_score: number;
  total_questions: number;
  correct_count: number;
  time_spent_seconds: number;
  question_results: QuestionResult[];
  feedback?: string;
  recommendations?: string[];
  passed: boolean;
}

export interface QuestionResult {
  question_id: string;
  user_answer: string;
  correct_answer: string;
  is_correct: boolean;
  score: number;
  feedback: string;
  suggestions?: string;
}

export interface QuizSubmission {
  quiz_id: string;
  answers: Record<string, string>;
  time_spent_seconds: number;
  engagement_metrics?: Record<string, any>;
}

export interface AnalyticsDashboard {
  user_id: string;
  generated_at: string;
  metrics: UserMetrics;
  learning_patterns: string[];
  progress: ProgressMetrics;
  concept_analytics: Record<string, ConceptAnalytics>;
  retention: RetentionMetrics;
  recommendations: Recommendation[];
}

export interface UserMetrics {
  total_events: number;
  lessons_completed: number;
  quizzes_taken: number;
  average_score: number;
  total_time_spent_minutes: number;
  chat_interactions: number;
  content_uploads: number;
  hints_requested: number;
}

export interface ProgressMetrics {
  lessons_started: number;
  lessons_completed: number;
  completion_rate: number;
  recent_activity: {
    lessons_this_week: number;
    quizzes_this_week: number;
    total_events_this_week: number;
  };
}

export interface ConceptAnalytics {
  average_score: number;
  recent_average: number;
  attempts: number;
  total_time_minutes: number;
  difficulty_level: string;
  trend: string;
}

export interface RetentionMetrics {
  total_days_active: number;
  current_streak: number;
  longest_streak: number;
  retention_rate: number;
  consistency_score: number;
  first_activity?: string;
  last_activity?: string;
  average_daily_events: number;
}

export interface Recommendation {
  type: string;
  priority: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  action: string;
}

export interface LearningVelocity {
  period_days: number;
  lessons_completed: number;
  quizzes_taken: number;
  chat_interactions: number;
  total_time_spent_minutes: number;
  daily_averages: {
    lessons: number;
    quizzes: number;
    time_minutes: number;
  };
  learning_pace: string;
  activity_score: number;
}

export interface EngagementEvent {
  event_type: string;
  event_data: Record<string, any>;
  session_id?: string;
  timestamp?: string;
}

export interface ProfileConfig {
  guestEnabled: boolean;
  guestUser: User;
}

// Adaptive Learning Types
export interface AdaptiveLearningState {
  current_micro_lesson_id: string;
  lesson_id: string;
  progress: number;
  next_content_type: 'micro_lesson' | 'quiz' | 'summary';
  difficulty_adjustment: number;
  learning_path: string[];
  completed_micro_lessons: string[];
}

export interface AdaptiveContentRequest {
  lesson_id: string;
  current_micro_lesson_id?: string;
  user_performance?: {
    quiz_scores: number[];
    time_spent: number;
    engagement_level: number;
  };
  learning_preferences?: UserPreferences;
}

export interface AdaptiveContentResponse {
  content_type: 'micro_lesson' | 'quiz' | 'summary';
  micro_lesson?: MicroLesson;
  quiz?: Quiz;
  transition_reason: string;
  progress_update: {
    overall_progress: number;
    micro_lesson_progress: number;
    estimated_completion_time: number;
  };
  next_available: boolean;
}