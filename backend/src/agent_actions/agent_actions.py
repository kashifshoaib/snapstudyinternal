"""
Amazon Bedrock Agent Action Functions for SnapStudy.

These functions are invoked by Bedrock Agents to perform autonomous actions
like analyzing student performance, adapting content, and managing learning paths.
"""

import json
import boto3
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import os
from decimal import Decimal

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

# Table references
users_table = dynamodb.Table(os.environ['USERS_TABLE'])
lessons_table = dynamodb.Table(os.environ['LESSONS_TABLE'])
micro_lessons_table = dynamodb.Table(os.environ['MICRO_LESSONS_TABLE'])
user_engagement_table = dynamodb.Table(os.environ['USER_ENGAGEMENT_TABLE'])
content_bucket = os.environ['CONTENT_BUCKET']


def handler(event, context):
    """
    Main handler for Bedrock Agent action invocations.
    Routes agent requests to appropriate action functions.
    """
    try:
        logger.info(f"Agent action invoked: {json.dumps(event)}")
        
        # Extract action information from Bedrock Agent event
        action_group = event.get('actionGroup', '')
        function_name = event.get('function', '')
        parameters = event.get('parameters', {})
        
        # Route to appropriate action function
        if function_name == 'analyze_student_performance':
            return analyze_student_performance(parameters)
        elif function_name == 'adapt_learning_path':
            return adapt_learning_path(parameters)
        elif function_name == 'generate_personalized_content':
            return generate_personalized_content(parameters)
        elif function_name == 'update_learning_progress':
            return update_learning_progress(parameters)
        elif function_name == 'get_student_context':
            return get_student_context(parameters)
        elif function_name == 'recommend_next_action':
            return recommend_next_action(parameters)
        else:
            return {
                'statusCode': 400,
                'body': {
                    'error': f'Unknown function: {function_name}',
                    'available_functions': [
                        'analyze_student_performance',
                        'adapt_learning_path', 
                        'generate_personalized_content',
                        'update_learning_progress',
                        'get_student_context',
                        'recommend_next_action'
                    ]
                }
            }
            
    except Exception as e:
        logger.error(f"Error in agent action handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'error': 'Internal server error',
                'message': str(e)
            }
        }


def analyze_student_performance(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze student performance across multiple dimensions.
    Used by agents to make autonomous adaptation decisions.
    """
    try:
        user_id = parameters.get('user_id')
        lesson_id = parameters.get('lesson_id')
        time_window = parameters.get('time_window', '7d')  # Last 7 days by default
        
        if not user_id:
            return {'statusCode': 400, 'body': {'error': 'user_id required'}}
        
        # Get recent engagement data
        engagement_data = get_recent_engagement(user_id, time_window)
        
        # Calculate performance metrics
        performance_analysis = {
            'user_id': user_id,
            'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
            'time_window': time_window,
            'metrics': {
                'average_quiz_score': calculate_average_quiz_score(engagement_data),
                'completion_rate': calculate_completion_rate(engagement_data),
                'engagement_level': calculate_engagement_level(engagement_data),
                'learning_velocity': calculate_learning_velocity(engagement_data),
                'difficulty_adaptation_needed': assess_difficulty_needs(engagement_data),
                'knowledge_gaps': identify_knowledge_gaps(engagement_data),
                'strengths': identify_strengths(engagement_data)
            },
            'recommendations': {
                'adaptation_strategy': determine_adaptation_strategy(engagement_data),
                'confidence_level': calculate_recommendation_confidence(engagement_data),
                'priority_areas': get_priority_learning_areas(engagement_data)
            }
        }
        
        return {
            'statusCode': 200,
            'body': performance_analysis
        }
        
    except Exception as e:
        logger.error(f"Error analyzing student performance: {str(e)}")
        return {
            'statusCode': 500,
            'body': {'error': 'Failed to analyze performance', 'details': str(e)}
        }


def adapt_learning_path(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Autonomously adapt the learning path based on performance analysis.
    Makes real-time decisions about content difficulty and pacing.
    """
    try:
        user_id = parameters.get('user_id')
        current_lesson_id = parameters.get('current_lesson_id')
        performance_data = parameters.get('performance_data', {})
        adaptation_strategy = parameters.get('strategy', 'auto')
        
        if not user_id or not current_lesson_id:
            return {'statusCode': 400, 'body': {'error': 'user_id and current_lesson_id required'}}
        
        # Get current learning context
        learning_context = get_learning_context(user_id, current_lesson_id)
        
        # Determine adaptation action based on performance
        if adaptation_strategy == 'auto':
            adaptation_action = auto_determine_adaptation(performance_data, learning_context)
        else:
            adaptation_action = adaptation_strategy
        
        # Execute the adaptation
        adaptation_result = execute_learning_adaptation(
            user_id, current_lesson_id, adaptation_action, learning_context
        )
        
        # Log the autonomous decision
        log_autonomous_decision(user_id, adaptation_action, adaptation_result, performance_data)
        
        return {
            'statusCode': 200,
            'body': {
                'user_id': user_id,
                'adaptation_applied': adaptation_action,
                'result': adaptation_result,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'autonomous_decision': True,
                'reasoning': adaptation_result.get('reasoning', 'Automatic adaptation based on performance analysis')
            }
        }
        
    except Exception as e:
        logger.error(f"Error adapting learning path: {str(e)}")
        return {
            'statusCode': 500,
            'body': {'error': 'Failed to adapt learning path', 'details': str(e)}
        }


def generate_personalized_content(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate personalized learning content based on student profile and performance.
    """
    try:
        user_id = parameters.get('user_id')
        content_type = parameters.get('content_type', 'explanation')  # explanation, quiz, example
        topic = parameters.get('topic')
        difficulty_level = parameters.get('difficulty_level', 'auto')
        learning_style = parameters.get('learning_style', 'auto')
        
        if not user_id or not topic:
            return {'statusCode': 400, 'body': {'error': 'user_id and topic required'}}
        
        # Get user profile for personalization
        user_profile = get_user_profile(user_id)
        
        # Auto-determine parameters if needed
        if difficulty_level == 'auto':
            difficulty_level = determine_optimal_difficulty(user_id, topic)
        
        if learning_style == 'auto':
            learning_style = user_profile.get('preferred_learning_style', 'mixed')
        
        # Generate content specification
        content_spec = {
            'user_id': user_id,
            'content_type': content_type,
            'topic': topic,
            'difficulty_level': difficulty_level,
            'learning_style': learning_style,
            'personalization_factors': {
                'user_interests': user_profile.get('interests', []),
                'knowledge_level': user_profile.get('knowledge_level', {}),
                'learning_pace': user_profile.get('learning_pace', 'medium'),
                'previous_performance': get_topic_performance_history(user_id, topic)
            },
            'generation_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        return {
            'statusCode': 200,
            'body': {
                'content_specification': content_spec,
                'ready_for_generation': True,
                'personalization_applied': True
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating personalized content: {str(e)}")
        return {
            'statusCode': 500,
            'body': {'error': 'Failed to generate content specification', 'details': str(e)}
        }


def update_learning_progress(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update student learning progress and trigger autonomous adaptations.
    """
    try:
        user_id = parameters.get('user_id')
        lesson_id = parameters.get('lesson_id')
        progress_data = parameters.get('progress_data', {})
        
        if not user_id or not lesson_id:
            return {'statusCode': 400, 'body': {'error': 'user_id and lesson_id required'}}
        
        # Update engagement record
        engagement_record = {
            'user_id': user_id,
            'lesson_id': lesson_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'progress_data': progress_data,
            'updated_by': 'autonomous_agent'
        }
        
        # Store in DynamoDB
        user_engagement_table.put_item(Item=engagement_record)
        
        # Check if autonomous adaptation is needed
        adaptation_needed = check_adaptation_triggers(user_id, lesson_id, progress_data)
        
        result = {
            'user_id': user_id,
            'lesson_id': lesson_id,
            'progress_updated': True,
            'timestamp': engagement_record['timestamp'],
            'adaptation_triggered': adaptation_needed
        }
        
        if adaptation_needed:
            # Trigger autonomous adaptation
            adaptation_result = trigger_autonomous_adaptation(user_id, lesson_id, progress_data)
            result['adaptation_result'] = adaptation_result
        
        return {
            'statusCode': 200,
            'body': result
        }
        
    except Exception as e:
        logger.error(f"Error updating learning progress: {str(e)}")
        return {
            'statusCode': 500,
            'body': {'error': 'Failed to update progress', 'details': str(e)}
        }


def get_student_context(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve comprehensive student context for agent decision-making.
    """
    try:
        user_id = parameters.get('user_id')
        include_history = parameters.get('include_history', True)
        
        if not user_id:
            return {'statusCode': 400, 'body': {'error': 'user_id required'}}
        
        # Get user profile
        user_profile = get_user_profile(user_id)
        
        # Get current learning state
        current_lessons = get_current_lessons(user_id)
        
        # Get recent performance
        recent_performance = get_recent_performance(user_id) if include_history else {}
        
        # Get learning preferences
        learning_preferences = get_learning_preferences(user_id)
        
        context = {
            'user_id': user_id,
            'profile': user_profile,
            'current_lessons': current_lessons,
            'recent_performance': recent_performance,
            'learning_preferences': learning_preferences,
            'context_timestamp': datetime.now(timezone.utc).isoformat(),
            'agent_ready': True
        }
        
        return {
            'statusCode': 200,
            'body': context
        }
        
    except Exception as e:
        logger.error(f"Error getting student context: {str(e)}")
        return {
            'statusCode': 500,
            'body': {'error': 'Failed to get student context', 'details': str(e)}
        }


def recommend_next_action(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Autonomously recommend the next learning action for a student.
    """
    try:
        user_id = parameters.get('user_id')
        current_context = parameters.get('current_context', {})
        
        if not user_id:
            return {'statusCode': 400, 'body': {'error': 'user_id required'}}
        
        # Analyze current state
        student_context = get_student_context({'user_id': user_id})['body']
        performance_analysis = analyze_student_performance({'user_id': user_id})['body']
        
        # Determine optimal next action
        next_action = determine_optimal_next_action(student_context, performance_analysis)
        
        # Calculate confidence in recommendation
        confidence = calculate_action_confidence(student_context, performance_analysis, next_action)
        
        recommendation = {
            'user_id': user_id,
            'recommended_action': next_action,
            'confidence_score': confidence,
            'reasoning': generate_action_reasoning(student_context, performance_analysis, next_action),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'autonomous_recommendation': True
        }
        
        return {
            'statusCode': 200,
            'body': recommendation
        }
        
    except Exception as e:
        logger.error(f"Error recommending next action: {str(e)}")
        return {
            'statusCode': 500,
            'body': {'error': 'Failed to recommend action', 'details': str(e)}
        }


# Helper functions for autonomous decision-making

def get_recent_engagement(user_id: str, time_window: str) -> List[Dict]:
    """Get recent engagement data for analysis."""
    # Implementation would query DynamoDB for recent engagement records
    # This is a simplified version
    try:
        response = user_engagement_table.query(
            KeyConditionExpression='user_id = :user_id',
            ExpressionAttributeValues={':user_id': user_id},
            ScanIndexForward=False,  # Most recent first
            Limit=50  # Last 50 interactions
        )
        return response.get('Items', [])
    except Exception as e:
        logger.error(f"Error getting engagement data: {str(e)}")
        return []


def calculate_average_quiz_score(engagement_data: List[Dict]) -> float:
    """Calculate average quiz score from engagement data."""
    quiz_scores = []
    for record in engagement_data:
        if record.get('activity_type') == 'quiz' and 'score' in record:
            quiz_scores.append(float(record['score']))
    
    return sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0.0


def calculate_completion_rate(engagement_data: List[Dict]) -> float:
    """Calculate lesson completion rate."""
    completed = sum(1 for record in engagement_data if record.get('completed', False))
    total = len(engagement_data)
    return (completed / total) if total > 0 else 0.0


def calculate_engagement_level(engagement_data: List[Dict]) -> str:
    """Determine engagement level based on interaction patterns."""
    if not engagement_data:
        return 'low'
    
    # Simple heuristic based on time spent and interaction frequency
    avg_time_spent = sum(record.get('time_spent', 0) for record in engagement_data) / len(engagement_data)
    
    if avg_time_spent > 300:  # 5 minutes
        return 'high'
    elif avg_time_spent > 120:  # 2 minutes
        return 'medium'
    else:
        return 'low'


def auto_determine_adaptation(performance_data: Dict, learning_context: Dict) -> str:
    """Autonomously determine the best adaptation strategy."""
    avg_score = performance_data.get('metrics', {}).get('average_quiz_score', 0)
    engagement = performance_data.get('metrics', {}).get('engagement_level', 'low')
    
    # Autonomous decision logic
    if avg_score >= 0.85 and engagement == 'high':
        return 'advance'  # Student is ready for next level
    elif avg_score < 0.6:
        return 'simplify'  # Content is too difficult
    elif avg_score < 0.75:
        return 'reinforce'  # Need more practice
    elif engagement == 'low':
        return 'engage'  # Need to increase engagement
    else:
        return 'continue'  # Current path is working


def execute_learning_adaptation(user_id: str, lesson_id: str, action: str, context: Dict) -> Dict:
    """Execute the determined learning adaptation."""
    adaptation_result = {
        'action_taken': action,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'success': True,
        'reasoning': f'Autonomous adaptation: {action} based on performance analysis'
    }
    
    # Log the adaptation decision
    try:
        adaptation_record = {
            'user_id': user_id,
            'lesson_id': lesson_id,
            'adaptation_action': action,
            'timestamp': adaptation_result['timestamp'],
            'context': context,
            'autonomous': True
        }
        
        # Store adaptation record (you would implement this based on your schema)
        logger.info(f"Autonomous adaptation executed: {adaptation_record}")
        
    except Exception as e:
        logger.error(f"Error logging adaptation: {str(e)}")
        adaptation_result['success'] = False
        adaptation_result['error'] = str(e)
    
    return adaptation_result


def get_user_profile(user_id: str) -> Dict:
    """Get user profile from DynamoDB."""
    try:
        response = users_table.get_item(Key={'user_id': user_id})
        return response.get('Item', {})
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        return {}


def determine_optimal_difficulty(user_id: str, topic: str) -> str:
    """Determine optimal difficulty level for user and topic."""
    # This would analyze user's performance history for the topic
    # Simplified implementation
    user_profile = get_user_profile(user_id)
    knowledge_level = user_profile.get('knowledge_level', {}).get(topic, 'beginner')
    
    difficulty_mapping = {
        'beginner': 'easy',
        'intermediate': 'medium', 
        'advanced': 'hard'
    }
    
    return difficulty_mapping.get(knowledge_level, 'medium')


# Additional helper functions would be implemented here...
def calculate_learning_velocity(engagement_data): return 'medium'
def assess_difficulty_needs(engagement_data): return False
def identify_knowledge_gaps(engagement_data): return []
def identify_strengths(engagement_data): return []
def determine_adaptation_strategy(engagement_data): return 'continue'
def calculate_recommendation_confidence(engagement_data): return 0.8
def get_priority_learning_areas(engagement_data): return []
def get_learning_context(user_id, lesson_id): return {}
def log_autonomous_decision(user_id, action, result, performance): pass
def check_adaptation_triggers(user_id, lesson_id, progress): return False
def trigger_autonomous_adaptation(user_id, lesson_id, progress): return {}
def get_current_lessons(user_id): return []
def get_recent_performance(user_id): return {}
def get_learning_preferences(user_id): return {}
def determine_optimal_next_action(context, performance): return 'continue_learning'
def calculate_action_confidence(context, performance, action): return 0.85
def generate_action_reasoning(context, performance, action): return f"Based on analysis, {action} is recommended"
def get_topic_performance_history(user_id, topic): return {}