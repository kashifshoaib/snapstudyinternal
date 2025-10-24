"""
Learning Analytics and Progress Tracking Service.

This service provides comprehensive analytics for user engagement, learning patterns,
progress tracking, and performance metrics for the SnapStudy platform.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from collections import defaultdict, Counter
import statistics
import uuid

from .dynamodb import db_service
from .bedrock import bedrock_service
from ..config import settings

logger = logging.getLogger(__name__)


class EngagementType(str, Enum):
    """Types of user engagement events."""
    LESSON_STARTED = "lesson_started"
    LESSON_COMPLETED = "lesson_completed"
    MICRO_LESSON_VIEWED = "micro_lesson_viewed"
    QUIZ_GENERATED = "quiz_generated"
    QUIZ_COMPLETED = "quiz_completed"
    QUIZ_SUBMITTED = "quiz_submitted"
    HINT_REQUESTED = "hint_requested"
    CHAT_INTERACTION = "chat_interaction"
    CONTENT_UPLOADED = "content_uploaded"
    ADAPTIVE_DECISION = "adaptive_decision"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"


class LearningPattern(str, Enum):
    """Identified learning patterns."""
    CONSISTENT_LEARNER = "consistent_learner"
    BINGE_LEARNER = "binge_learner"
    STRUGGLING_LEARNER = "struggling_learner"
    FAST_LEARNER = "fast_learner"
    QUIZ_DEPENDENT = "quiz_dependent"
    CHAT_HEAVY_USER = "chat_heavy_user"
    PERFECTIONIST = "perfectionist"
    CASUAL_LEARNER = "casual_learner"


class ConceptDifficulty(str, Enum):
    """Difficulty levels for concepts."""
    MASTERED = "mastered"
    COMFORTABLE = "comfortable"
    LEARNING = "learning"
    STRUGGLING = "struggling"
    NOT_ATTEMPTED = "not_attempted"


class AnalyticsService:
    """
    Comprehensive analytics service for learning data collection and analysis.
    """
    
    def __init__(self):
        self.db = db_service
        self.bedrock = bedrock_service
        
        # Analytics configuration
        self.retention_days = 365  # Keep analytics data for 1 year
        self.pattern_analysis_window = 30  # Days to analyze for patterns
        self.struggling_threshold = 0.6  # Score below which indicates struggling
        self.mastery_threshold = 0.85  # Score above which indicates mastery
        
    async def track_engagement_event(
        self, 
        user_id: str, 
        event_type: EngagementType, 
        event_data: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track a user engagement event with comprehensive metadata.
        """
        try:
            # Enrich event data with additional context
            enriched_data = await self._enrich_event_data(user_id, event_type, event_data)
            
            # Store the engagement event
            engagement_record = await self.db.track_engagement({
                'user_id': user_id,
                'event_type': event_type.value,
                'event_data': enriched_data,
                'session_id': session_id or str(uuid.uuid4()),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Update real-time analytics
            await self._update_real_time_metrics(user_id, event_type, enriched_data)
            
            # Trigger pattern analysis if needed
            await self._trigger_pattern_analysis(user_id, event_type)
            
            logger.info(f"Tracked engagement event: {event_type.value} for user {user_id}")
            return engagement_record
            
        except Exception as e:
            logger.error(f"Failed to track engagement event: {e}")
            raise
    
    async def get_user_analytics_dashboard(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive analytics dashboard data for a user.
        """
        try:
            # Get recent engagement data
            engagement_data = await self.db.get_user_engagement(user_id, limit=100)
            
            # Calculate key metrics
            metrics = await self._calculate_user_metrics(user_id, engagement_data)
            
            # Analyze learning patterns
            patterns = await self._analyze_learning_patterns(user_id, engagement_data)
            
            # Get progress tracking
            progress = await self._calculate_progress_metrics(user_id, engagement_data)
            
            # Get concept-level analytics
            concept_analytics = await self._analyze_concept_performance(user_id, engagement_data)
            
            # Get retention and streak data
            retention_data = await self._calculate_retention_metrics(user_id, engagement_data)
            
            return {
                'user_id': user_id,
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'metrics': metrics,
                'learning_patterns': patterns,
                'progress': progress,
                'concept_analytics': concept_analytics,
                'retention': retention_data,
                'recommendations': await self._generate_recommendations(user_id, patterns, metrics)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate analytics dashboard: {e}")
            raise
    
    async def get_struggling_concepts(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Identify concepts where the user is struggling.
        """
        try:
            engagement_data = await self.db.get_user_engagement(user_id, limit=50)
            
            # Analyze quiz performance by concept
            concept_performance = defaultdict(list)
            
            for event in engagement_data:
                if event.get('event_type') == 'quiz_completed':
                    event_data = event.get('event_data', {})
                    concepts = event_data.get('concepts', [])
                    score = event_data.get('score', 0)
                    
                    for concept in concepts:
                        concept_performance[concept].append(score)
            
            # Identify struggling concepts
            struggling_concepts = []
            
            for concept, scores in concept_performance.items():
                if scores:
                    avg_score = statistics.mean(scores)
                    recent_scores = scores[-3:]  # Last 3 attempts
                    recent_avg = statistics.mean(recent_scores) if recent_scores else avg_score
                    
                    if recent_avg < self.struggling_threshold * 100:
                        struggling_concepts.append({
                            'concept': concept,
                            'average_score': avg_score,
                            'recent_average': recent_avg,
                            'attempts': len(scores),
                            'difficulty_level': ConceptDifficulty.STRUGGLING.value,
                            'improvement_trend': 'improving' if len(scores) > 1 and scores[-1] > scores[0] else 'declining',
                            'last_attempt': max(engagement_data, key=lambda x: x.get('timestamp', ''))['timestamp'] if engagement_data else None
                        })
            
            # Sort by most struggling (lowest recent average)
            struggling_concepts.sort(key=lambda x: x['recent_average'])
            
            return struggling_concepts
            
        except Exception as e:
            logger.error(f"Failed to identify struggling concepts: {e}")
            return []
    
    async def calculate_learning_velocity(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Calculate learning velocity and pace metrics.
        """
        try:
            # Get recent engagement data
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            engagement_data = await self.db.get_user_engagement(user_id, limit=200)
            
            # Filter to recent data
            recent_data = [
                event for event in engagement_data
                if datetime.fromisoformat(event.get('timestamp', '').replace('Z', '+00:00')) > cutoff_date
            ]
            
            # Calculate velocity metrics
            lessons_completed = len([e for e in recent_data if e.get('event_type') == 'lesson_completed'])
            quizzes_taken = len([e for e in recent_data if e.get('event_type') == 'quiz_completed'])
            chat_interactions = len([e for e in recent_data if e.get('event_type') == 'chat_interaction'])
            
            # Calculate time spent
            total_time_spent = 0
            for event in recent_data:
                event_data = event.get('event_data', {})
                time_spent = event_data.get('time_spent', 0)
                if isinstance(time_spent, (int, float)):
                    total_time_spent += time_spent
            
            # Calculate daily averages
            daily_lessons = lessons_completed / days if days > 0 else 0
            daily_quizzes = quizzes_taken / days if days > 0 else 0
            daily_time = total_time_spent / days if days > 0 else 0
            
            # Determine learning pace
            if daily_lessons >= 1 and daily_quizzes >= 2:
                pace = 'fast'
            elif daily_lessons >= 0.5 and daily_quizzes >= 1:
                pace = 'moderate'
            elif daily_lessons > 0 or daily_quizzes > 0:
                pace = 'slow'
            else:
                pace = 'inactive'
            
            return {
                'period_days': days,
                'lessons_completed': lessons_completed,
                'quizzes_taken': quizzes_taken,
                'chat_interactions': chat_interactions,
                'total_time_spent_minutes': total_time_spent / 60,
                'daily_averages': {
                    'lessons': round(daily_lessons, 2),
                    'quizzes': round(daily_quizzes, 2),
                    'time_minutes': round(daily_time / 60, 2)
                },
                'learning_pace': pace,
                'activity_score': min(100, (lessons_completed * 10 + quizzes_taken * 5 + chat_interactions) / days * 10)
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate learning velocity: {e}")
            return {}
    
    async def get_retention_analytics(self, user_id: str) -> Dict[str, Any]:
        """
        Calculate user retention and engagement consistency metrics.
        """
        try:
            # Get all engagement data
            engagement_data = await self.db.get_user_engagement(user_id, limit=500)
            
            if not engagement_data:
                return {
                    'total_days_active': 0,
                    'current_streak': 0,
                    'longest_streak': 0,
                    'retention_rate': 0.0,
                    'consistency_score': 0.0
                }
            
            # Group events by date
            daily_activity = defaultdict(int)
            for event in engagement_data:
                date_str = event.get('timestamp', '')[:10]  # YYYY-MM-DD
                daily_activity[date_str] += 1
            
            # Calculate streaks
            active_dates = sorted(daily_activity.keys())
            current_streak = self._calculate_current_streak(active_dates)
            longest_streak = self._calculate_longest_streak(active_dates)
            
            # Calculate retention metrics
            total_days_active = len(active_dates)
            
            # Calculate retention rate (active days in last 30 days)
            thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
            recent_active_days = len([d for d in active_dates if d >= thirty_days_ago])
            retention_rate = (recent_active_days / 30) * 100
            
            # Calculate consistency score
            if len(active_dates) > 1:
                first_date = datetime.fromisoformat(active_dates[0])
                last_date = datetime.fromisoformat(active_dates[-1])
                total_possible_days = (last_date - first_date).days + 1
                consistency_score = (total_days_active / total_possible_days) * 100
            else:
                consistency_score = 100.0 if total_days_active > 0 else 0.0
            
            return {
                'total_days_active': total_days_active,
                'current_streak': current_streak,
                'longest_streak': longest_streak,
                'retention_rate': round(retention_rate, 1),
                'consistency_score': round(consistency_score, 1),
                'first_activity': active_dates[0] if active_dates else None,
                'last_activity': active_dates[-1] if active_dates else None,
                'average_daily_events': round(sum(daily_activity.values()) / len(daily_activity), 1) if daily_activity else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate retention analytics: {e}")
            return {}
    
    async def _enrich_event_data(
        self, 
        user_id: str, 
        event_type: EngagementType, 
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enrich event data with additional context and metadata.
        """
        enriched = event_data.copy()
        
        # Add timestamp if not present
        if 'timestamp' not in enriched:
            enriched['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        # Add user context
        enriched['user_id'] = user_id
        
        # Add device/session context (if available)
        enriched['platform'] = 'web'  # Could be enhanced with actual device detection
        
        # Add performance context for quiz events
        if event_type in [EngagementType.QUIZ_COMPLETED, EngagementType.QUIZ_SUBMITTED]:
            score = enriched.get('score', 0)
            enriched['performance_category'] = (
                'excellent' if score >= 90 else
                'good' if score >= 75 else
                'average' if score >= 60 else
                'needs_improvement'
            )
        
        # Add engagement intensity
        enriched['engagement_intensity'] = self._calculate_engagement_intensity(event_type, enriched)
        
        return enriched
    
    def _calculate_engagement_intensity(self, event_type: EngagementType, event_data: Dict[str, Any]) -> str:
        """
        Calculate engagement intensity based on event type and data.
        """
        time_spent = event_data.get('time_spent', 0)
        
        if event_type == EngagementType.LESSON_COMPLETED:
            return 'high' if time_spent > 600 else 'medium' if time_spent > 300 else 'low'
        elif event_type == EngagementType.QUIZ_COMPLETED:
            score = event_data.get('score', 0)
            return 'high' if score > 80 and time_spent > 180 else 'medium' if score > 60 else 'low'
        elif event_type == EngagementType.CHAT_INTERACTION:
            return 'high' if time_spent > 120 else 'medium' if time_spent > 30 else 'low'
        else:
            return 'medium'
    
    async def _update_real_time_metrics(
        self, 
        user_id: str, 
        event_type: EngagementType, 
        event_data: Dict[str, Any]
    ) -> None:
        """
        Update real-time metrics based on the event.
        """
        try:
            # This could update a real-time metrics cache or dashboard
            # For now, we'll log the metric update
            logger.info(f"Real-time metric update: {event_type.value} for user {user_id}")
            
            # In a production system, this might update Redis cache or send to a metrics service
            
        except Exception as e:
            logger.error(f"Failed to update real-time metrics: {e}")
    
    async def _trigger_pattern_analysis(self, user_id: str, event_type: EngagementType) -> None:
        """
        Trigger pattern analysis if certain conditions are met.
        """
        try:
            # Trigger analysis for significant events
            trigger_events = [
                EngagementType.LESSON_COMPLETED,
                EngagementType.QUIZ_COMPLETED,
                EngagementType.SESSION_ENDED
            ]
            
            if event_type in trigger_events:
                # Could trigger async pattern analysis
                logger.info(f"Pattern analysis triggered for user {user_id} after {event_type.value}")
                
        except Exception as e:
            logger.error(f"Failed to trigger pattern analysis: {e}")
    
    async def _calculate_user_metrics(self, user_id: str, engagement_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate comprehensive user metrics.
        """
        if not engagement_data:
            return {
                'total_events': 0,
                'lessons_completed': 0,
                'quizzes_taken': 0,
                'average_score': 0.0,
                'total_time_spent_minutes': 0.0,
                'chat_interactions': 0
            }
        
        # Count events by type
        event_counts = Counter(event.get('event_type') for event in engagement_data)
        
        # Calculate quiz metrics
        quiz_events = [e for e in engagement_data if e.get('event_type') == 'quiz_completed']
        quiz_scores = [e.get('event_data', {}).get('score', 0) for e in quiz_events]
        average_score = statistics.mean(quiz_scores) if quiz_scores else 0.0
        
        # Calculate total time spent
        total_time = 0
        for event in engagement_data:
            time_spent = event.get('event_data', {}).get('time_spent', 0)
            if isinstance(time_spent, (int, float)):
                total_time += time_spent
        
        return {
            'total_events': len(engagement_data),
            'lessons_completed': event_counts.get('lesson_completed', 0),
            'quizzes_taken': event_counts.get('quiz_completed', 0),
            'average_score': round(average_score, 1),
            'total_time_spent_minutes': round(total_time / 60, 1),
            'chat_interactions': event_counts.get('chat_interaction', 0),
            'content_uploads': event_counts.get('content_uploaded', 0),
            'hints_requested': event_counts.get('hint_requested', 0)
        }
    
    async def _analyze_learning_patterns(self, user_id: str, engagement_data: List[Dict[str, Any]]) -> List[str]:
        """
        Analyze user behavior to identify learning patterns.
        """
        if not engagement_data:
            return []
        
        patterns = []
        
        # Analyze consistency
        daily_activity = defaultdict(int)
        for event in engagement_data[-30:]:  # Last 30 events
            date_str = event.get('timestamp', '')[:10]
            daily_activity[date_str] += 1
        
        if len(daily_activity) >= 7 and all(count >= 2 for count in daily_activity.values()):
            patterns.append(LearningPattern.CONSISTENT_LEARNER.value)
        
        # Analyze quiz dependency
        quiz_events = len([e for e in engagement_data if e.get('event_type') == 'quiz_completed'])
        total_events = len(engagement_data)
        
        if quiz_events / total_events > 0.4:
            patterns.append(LearningPattern.QUIZ_DEPENDENT.value)
        
        # Analyze chat usage
        chat_events = len([e for e in engagement_data if e.get('event_type') == 'chat_interaction'])
        if chat_events / total_events > 0.3:
            patterns.append(LearningPattern.CHAT_HEAVY_USER.value)
        
        # Analyze performance patterns
        quiz_scores = [e.get('event_data', {}).get('score', 0) for e in engagement_data if e.get('event_type') == 'quiz_completed']
        if quiz_scores:
            avg_score = statistics.mean(quiz_scores)
            if avg_score > 85:
                patterns.append(LearningPattern.FAST_LEARNER.value)
            elif avg_score < 60:
                patterns.append(LearningPattern.STRUGGLING_LEARNER.value)
        
        return patterns if patterns else [LearningPattern.CASUAL_LEARNER.value]
    
    async def _calculate_progress_metrics(self, user_id: str, engagement_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate progress tracking metrics.
        """
        lessons_started = len([e for e in engagement_data if e.get('event_type') == 'lesson_started'])
        lessons_completed = len([e for e in engagement_data if e.get('event_type') == 'lesson_completed'])
        
        completion_rate = (lessons_completed / lessons_started * 100) if lessons_started > 0 else 0
        
        # Calculate recent progress (last 7 days)
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_events = [
            e for e in engagement_data
            if datetime.fromisoformat(e.get('timestamp', '').replace('Z', '+00:00')) > seven_days_ago
        ]
        
        recent_lessons = len([e for e in recent_events if e.get('event_type') == 'lesson_completed'])
        recent_quizzes = len([e for e in recent_events if e.get('event_type') == 'quiz_completed'])
        
        return {
            'lessons_started': lessons_started,
            'lessons_completed': lessons_completed,
            'completion_rate': round(completion_rate, 1),
            'recent_activity': {
                'lessons_this_week': recent_lessons,
                'quizzes_this_week': recent_quizzes,
                'total_events_this_week': len(recent_events)
            }
        }
    
    async def _analyze_concept_performance(self, user_id: str, engagement_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze performance at the concept level.
        """
        concept_data = defaultdict(lambda: {'scores': [], 'attempts': 0, 'time_spent': 0})
        
        for event in engagement_data:
            if event.get('event_type') == 'quiz_completed':
                event_data = event.get('event_data', {})
                concepts = event_data.get('concepts', [])
                score = event_data.get('score', 0)
                time_spent = event_data.get('time_spent', 0)
                
                for concept in concepts:
                    concept_data[concept]['scores'].append(score)
                    concept_data[concept]['attempts'] += 1
                    concept_data[concept]['time_spent'] += time_spent
        
        # Analyze each concept
        concept_analytics = {}
        for concept, data in concept_data.items():
            if data['scores']:
                avg_score = statistics.mean(data['scores'])
                recent_scores = data['scores'][-3:]
                recent_avg = statistics.mean(recent_scores) if recent_scores else avg_score
                
                # Determine difficulty level
                if recent_avg >= self.mastery_threshold * 100:
                    difficulty = ConceptDifficulty.MASTERED.value
                elif recent_avg >= 75:
                    difficulty = ConceptDifficulty.COMFORTABLE.value
                elif recent_avg >= self.struggling_threshold * 100:
                    difficulty = ConceptDifficulty.LEARNING.value
                else:
                    difficulty = ConceptDifficulty.STRUGGLING.value
                
                concept_analytics[concept] = {
                    'average_score': round(avg_score, 1),
                    'recent_average': round(recent_avg, 1),
                    'attempts': data['attempts'],
                    'total_time_minutes': round(data['time_spent'] / 60, 1),
                    'difficulty_level': difficulty,
                    'trend': 'improving' if len(data['scores']) > 1 and data['scores'][-1] > data['scores'][0] else 'stable'
                }
        
        return concept_analytics
    
    async def _calculate_retention_metrics(self, user_id: str, engagement_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate retention and consistency metrics.
        """
        return await self.get_retention_analytics(user_id)
    
    async def _generate_recommendations(
        self, 
        user_id: str, 
        patterns: List[str], 
        metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate personalized recommendations based on analytics.
        """
        recommendations = []
        
        # Performance-based recommendations
        avg_score = metrics.get('average_score', 0)
        if avg_score < 60:
            recommendations.append({
                'type': 'performance',
                'priority': 'high',
                'title': 'Focus on Fundamentals',
                'description': 'Your quiz scores suggest reviewing basic concepts before advancing.',
                'action': 'review_concepts'
            })
        elif avg_score > 85:
            recommendations.append({
                'type': 'performance',
                'priority': 'medium',
                'title': 'Challenge Yourself',
                'description': 'You\'re doing great! Try more advanced topics or increase difficulty.',
                'action': 'increase_difficulty'
            })
        
        # Pattern-based recommendations
        if LearningPattern.STRUGGLING_LEARNER.value in patterns:
            recommendations.append({
                'type': 'learning_pattern',
                'priority': 'high',
                'title': 'Get Extra Support',
                'description': 'Consider using the chat tutor more frequently for help with difficult concepts.',
                'action': 'use_chat_tutor'
            })
        
        if LearningPattern.CONSISTENT_LEARNER.value in patterns:
            recommendations.append({
                'type': 'learning_pattern',
                'priority': 'low',
                'title': 'Maintain Your Streak',
                'description': 'Great consistency! Keep up your regular learning schedule.',
                'action': 'maintain_schedule'
            })
        
        # Engagement-based recommendations
        chat_interactions = metrics.get('chat_interactions', 0)
        total_events = metrics.get('total_events', 1)
        
        if chat_interactions / total_events < 0.1:
            recommendations.append({
                'type': 'engagement',
                'priority': 'medium',
                'title': 'Try the AI Tutor',
                'description': 'The AI tutor can provide instant help and explanations. Give it a try!',
                'action': 'try_chat_tutor'
            })
        
        return recommendations
    
    def _calculate_current_streak(self, active_dates: List[str]) -> int:
        """
        Calculate current consecutive days streak.
        """
        if not active_dates:
            return 0
        
        today = datetime.now(timezone.utc).date()
        current_streak = 0
        
        # Check if user was active today or yesterday
        last_date = datetime.fromisoformat(active_dates[-1]).date()
        if (today - last_date).days > 1:
            return 0
        
        # Count consecutive days backwards
        for i in range(len(active_dates) - 1, -1, -1):
            date = datetime.fromisoformat(active_dates[i]).date()
            expected_date = today - timedelta(days=current_streak)
            
            if date == expected_date:
                current_streak += 1
            else:
                break
        
        return current_streak
    
    def _calculate_longest_streak(self, active_dates: List[str]) -> int:
        """
        Calculate longest consecutive days streak.
        """
        if not active_dates:
            return 0
        
        longest_streak = 1
        current_streak = 1
        
        for i in range(1, len(active_dates)):
            prev_date = datetime.fromisoformat(active_dates[i-1]).date()
            curr_date = datetime.fromisoformat(active_dates[i]).date()
            
            if (curr_date - prev_date).days == 1:
                current_streak += 1
                longest_streak = max(longest_streak, current_streak)
            else:
                current_streak = 1
        
        return longest_streak


# Global service instance
analytics_service = AnalyticsService()