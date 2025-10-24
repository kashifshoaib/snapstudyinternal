"""
Content Guardrails Service for Educational Safety and Appropriateness.

This service provides comprehensive content filtering and safety validation
specifically designed for educational environments, ensuring all AI-generated
content is appropriate for learning contexts.
"""

import boto3
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from botocore.exceptions import ClientError
from enum import Enum
from datetime import datetime, timezone

from ..config import settings

logger = logging.getLogger(__name__)


class ContentSafetyLevel(str, Enum):
    """Content safety levels for educational environments."""
    SAFE = "safe"
    EDUCATIONAL_REVIEW = "educational_review"
    CONTENT_WARNING = "content_warning"
    BLOCKED = "blocked"


class EducationalContentType(str, Enum):
    """Types of educational content."""
    ACADEMIC = "academic"
    RESEARCH = "research"
    TUTORIAL = "tutorial"
    EXPLANATION = "explanation"
    EXAMPLE = "example"
    EXERCISE = "exercise"
    GENERAL = "general"


class ContentGuardrailsService:
    """
    Comprehensive content guardrails service for educational safety.
    
    Provides multi-layered content validation including:
    - Bedrock Guardrails integration
    - Educational appropriateness validation
    - Age-appropriate content filtering
    - Academic integrity checks
    - Harmful content detection
    """
    
    def __init__(self):
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=settings.aws_region)
        self.bedrock_client = boto3.client('bedrock', region_name=settings.aws_region)

        # Guardrails configuration
        self.guardrail_id = settings.bedrock_guardrail_id
        self.guardrail_version = settings.bedrock_guardrail_version
        self.safety_level = getattr(settings, 'content_safety_level', 'strict')

        logger.info(f"ContentGuardrailsService initialized with Guardrail ID: {self.guardrail_id}")
        
        # Educational content validation rules
        self.educational_keywords = {
            'positive': [
                'learn', 'study', 'understand', 'explain', 'teach', 'education',
                'academic', 'research', 'knowledge', 'skill', 'practice', 'example',
                'tutorial', 'guide', 'concept', 'theory', 'analysis', 'solution'
            ],
            'neutral': [
                'information', 'data', 'fact', 'detail', 'description', 'overview',
                'summary', 'review', 'comparison', 'discussion', 'question'
            ]
        }
        
        # Blocked content patterns for educational environments
        self.blocked_patterns = {
            'violence': [
                'violence', 'violent', 'attack', 'assault', 'harm', 'hurt',
                'kill', 'murder', 'weapon', 'fight', 'war', 'battle'
            ],
            'inappropriate': [
                'adult content', 'explicit', 'sexual', 'pornographic', 'nude',
                'inappropriate', 'offensive', 'vulgar', 'profanity'
            ],
            'harmful': [
                'suicide', 'self-harm', 'depression', 'eating disorder',
                'substance abuse', 'illegal drugs', 'alcohol abuse'
            ],
            'discrimination': [
                'racism', 'sexism', 'discrimination', 'hate speech',
                'prejudice', 'bias', 'stereotype', 'harassment'
            ],
            'illegal': [
                'illegal activity', 'criminal', 'fraud', 'theft', 'piracy',
                'hacking', 'cheating', 'plagiarism'
            ]
        }
        
        # Age-appropriate content guidelines
        self.age_guidelines = {
            'elementary': {
                'max_complexity': 'simple',
                'avoid_topics': ['advanced_science', 'complex_math', 'adult_themes'],
                'preferred_language': 'simple_vocabulary'
            },
            'middle_school': {
                'max_complexity': 'moderate',
                'avoid_topics': ['adult_themes', 'controversial_topics'],
                'preferred_language': 'age_appropriate'
            },
            'high_school': {
                'max_complexity': 'advanced',
                'avoid_topics': ['adult_themes'],
                'preferred_language': 'academic'
            },
            'college': {
                'max_complexity': 'expert',
                'avoid_topics': [],
                'preferred_language': 'academic_advanced'
            }
        }
    
    async def validate_content_comprehensive(
        self,
        content: str,
        content_type: EducationalContentType = EducationalContentType.GENERAL,
        user_age_group: str = "college",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive content validation with multiple safety layers.
        
        Args:
            content: Content to validate
            content_type: Type of educational content
            user_age_group: Age group of the user (elementary, middle_school, high_school, college)
            context: Additional context for validation
            
        Returns:
            Dict containing validation results and recommendations
        """
        try:
            validation_results = {
                'overall_safety': ContentSafetyLevel.SAFE,
                'is_educational': True,
                'age_appropriate': True,
                'confidence': 0.0,
                'issues_found': [],
                'recommendations': [],
                'detailed_analysis': {}
            }
            
            # Layer 1: Bedrock Guardrails validation
            bedrock_validation = await self._validate_with_bedrock_guardrails(content)
            validation_results['detailed_analysis']['bedrock_guardrails'] = bedrock_validation
            
            # Layer 2: Educational appropriateness check
            educational_validation = await self._validate_educational_appropriateness(
                content, content_type
            )
            validation_results['detailed_analysis']['educational_check'] = educational_validation
            
            # Layer 3: Age appropriateness validation
            age_validation = await self._validate_age_appropriateness(content, user_age_group)
            validation_results['detailed_analysis']['age_appropriateness'] = age_validation
            
            # Layer 4: Harmful content detection
            harmful_content_check = await self._detect_harmful_content(content)
            validation_results['detailed_analysis']['harmful_content'] = harmful_content_check
            
            # Layer 5: Academic integrity validation
            integrity_check = await self._validate_academic_integrity(content, context)
            validation_results['detailed_analysis']['academic_integrity'] = integrity_check
            
            # Combine all validation results
            overall_result = await self._combine_validation_results([
                bedrock_validation,
                educational_validation,
                age_validation,
                harmful_content_check,
                integrity_check
            ])
            
            validation_results.update(overall_result)
            
            # Generate recommendations based on issues found
            if validation_results['issues_found']:
                validation_results['recommendations'] = await self._generate_content_recommendations(
                    validation_results['issues_found'], content_type, user_age_group
                )
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Comprehensive content validation failed: {e}")
            return {
                'overall_safety': ContentSafetyLevel.EDUCATIONAL_REVIEW,
                'is_educational': False,
                'age_appropriate': False,
                'confidence': 0.0,
                'issues_found': [f'Validation error: {str(e)}'],
                'recommendations': ['Content requires manual review due to validation error'],
                'error': str(e)
            }
    
    async def _validate_with_bedrock_guardrails(self, content: str) -> Dict[str, Any]:
        """Validate content using Bedrock Guardrails."""
        try:
            if not self.guardrail_id:
                return {
                    'status': 'skipped',
                    'reason': 'Bedrock Guardrails not configured',
                    'safety_level': ContentSafetyLevel.EDUCATIONAL_REVIEW
                }
            
            response = self.bedrock_client.apply_guardrail(
                guardrailIdentifier=self.guardrail_id,
                guardrailVersion=self.guardrail_version,
                source='INPUT',
                content=[{
                    'text': {
                        'text': content
                    }
                }]
            )
            
            action = response.get('action', 'NONE')
            
            if action == 'BLOCKED':
                return {
                    'status': 'blocked',
                    'reason': 'Content blocked by Bedrock Guardrails',
                    'safety_level': ContentSafetyLevel.BLOCKED,
                    'guardrail_response': response
                }
            elif action == 'GUARDRAIL_INTERVENED':
                return {
                    'status': 'intervened',
                    'reason': 'Content modified by guardrails',
                    'safety_level': ContentSafetyLevel.CONTENT_WARNING,
                    'guardrail_response': response
                }
            else:
                return {
                    'status': 'passed',
                    'reason': 'Content passed Bedrock Guardrails',
                    'safety_level': ContentSafetyLevel.SAFE,
                    'guardrail_response': response
                }
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.warning(f"Bedrock Guardrails validation failed: {error_code}")
            
            return {
                'status': 'error',
                'reason': f'Guardrails validation failed: {error_code}',
                'safety_level': ContentSafetyLevel.EDUCATIONAL_REVIEW
            }
        except Exception as e:
            logger.error(f"Unexpected error in Bedrock Guardrails: {e}")
            return {
                'status': 'error',
                'reason': f'Guardrails error: {str(e)}',
                'safety_level': ContentSafetyLevel.EDUCATIONAL_REVIEW
            }
    
    async def _validate_educational_appropriateness(
        self,
        content: str,
        content_type: EducationalContentType
    ) -> Dict[str, Any]:
        """Validate that content is appropriate for educational use."""
        content_lower = content.lower()
        
        # Calculate educational score
        educational_score = 0.0
        positive_matches = 0
        neutral_matches = 0
        
        # Check for positive educational keywords
        for keyword in self.educational_keywords['positive']:
            if keyword in content_lower:
                positive_matches += 1
                educational_score += 0.1
        
        # Check for neutral educational keywords
        for keyword in self.educational_keywords['neutral']:
            if keyword in content_lower:
                neutral_matches += 1
                educational_score += 0.05
        
        # Bonus for specific content types
        content_type_bonus = {
            EducationalContentType.ACADEMIC: 0.2,
            EducationalContentType.RESEARCH: 0.2,
            EducationalContentType.TUTORIAL: 0.15,
            EducationalContentType.EXPLANATION: 0.15,
            EducationalContentType.EXAMPLE: 0.1,
            EducationalContentType.EXERCISE: 0.1,
            EducationalContentType.GENERAL: 0.0
        }
        
        educational_score += content_type_bonus.get(content_type, 0.0)
        
        # Normalize score
        educational_score = min(1.0, educational_score)
        
        # Determine appropriateness
        is_educational = educational_score >= 0.3
        
        if educational_score >= 0.7:
            safety_level = ContentSafetyLevel.SAFE
        elif educational_score >= 0.3:
            safety_level = ContentSafetyLevel.EDUCATIONAL_REVIEW
        else:
            safety_level = ContentSafetyLevel.BLOCKED
        
        return {
            'status': 'completed',
            'is_educational': is_educational,
            'educational_score': educational_score,
            'positive_matches': positive_matches,
            'neutral_matches': neutral_matches,
            'safety_level': safety_level,
            'content_type': content_type
        }
    
    async def _validate_age_appropriateness(self, content: str, age_group: str) -> Dict[str, Any]:
        """Validate content is appropriate for the specified age group."""
        
        guidelines = self.age_guidelines.get(age_group, self.age_guidelines['college'])
        content_lower = content.lower()
        
        issues = []
        
        # Check for topics to avoid
        for topic in guidelines['avoid_topics']:
            topic_keywords = {
                'advanced_science': ['quantum', 'molecular', 'advanced physics', 'complex chemistry'],
                'complex_math': ['calculus', 'differential equations', 'advanced statistics'],
                'adult_themes': ['adult', 'mature', 'inappropriate'],
                'controversial_topics': ['politics', 'religion', 'controversial']
            }
            
            if topic in topic_keywords:
                for keyword in topic_keywords[topic]:
                    if keyword in content_lower:
                        issues.append(f"Contains {topic} content: {keyword}")
        
        # Check language complexity (simplified check)
        words = content.split()
        avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
        
        complexity_thresholds = {
            'elementary': 5.0,
            'middle_school': 6.0,
            'high_school': 7.0,
            'college': 10.0
        }
        
        max_complexity = complexity_thresholds.get(age_group, 10.0)
        
        if avg_word_length > max_complexity:
            issues.append(f"Language complexity too high for {age_group}")
        
        is_age_appropriate = len(issues) == 0
        
        return {
            'status': 'completed',
            'is_age_appropriate': is_age_appropriate,
            'age_group': age_group,
            'issues': issues,
            'avg_word_length': avg_word_length,
            'safety_level': ContentSafetyLevel.SAFE if is_age_appropriate else ContentSafetyLevel.CONTENT_WARNING
        }
    
    async def _detect_harmful_content(self, content: str) -> Dict[str, Any]:
        """Detect harmful content patterns."""
        content_lower = content.lower()
        
        detected_issues = []
        
        for category, patterns in self.blocked_patterns.items():
            for pattern in patterns:
                if pattern in content_lower:
                    detected_issues.append({
                        'category': category,
                        'pattern': pattern,
                        'severity': 'high' if category in ['violence', 'harmful'] else 'medium'
                    })
        
        has_harmful_content = len(detected_issues) > 0
        
        # Determine safety level based on issues found
        if any(issue['severity'] == 'high' for issue in detected_issues):
            safety_level = ContentSafetyLevel.BLOCKED
        elif detected_issues:
            safety_level = ContentSafetyLevel.CONTENT_WARNING
        else:
            safety_level = ContentSafetyLevel.SAFE
        
        return {
            'status': 'completed',
            'has_harmful_content': has_harmful_content,
            'detected_issues': detected_issues,
            'safety_level': safety_level
        }
    
    async def _validate_academic_integrity(
        self,
        content: str,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate academic integrity aspects of content."""
        
        integrity_issues = []
        
        # Check for potential plagiarism indicators (simplified)
        plagiarism_indicators = [
            'copy and paste', 'copied from', 'taken from', 'source:',
            'according to [author]', 'as stated in'
        ]
        
        content_lower = content.lower()
        for indicator in plagiarism_indicators:
            if indicator in content_lower:
                integrity_issues.append(f"Potential citation needed: {indicator}")
        
        # Check for academic dishonesty keywords
        dishonesty_keywords = [
            'cheat', 'cheating', 'plagiarize', 'copy homework',
            'academic dishonesty', 'fake citation'
        ]
        
        for keyword in dishonesty_keywords:
            if keyword in content_lower:
                integrity_issues.append(f"Academic integrity concern: {keyword}")
        
        # Check if content encourages proper academic practices
        good_practices = [
            'cite sources', 'reference', 'bibliography', 'original work',
            'academic honesty', 'proper attribution'
        ]
        
        promotes_integrity = any(practice in content_lower for practice in good_practices)
        
        has_integrity_issues = len(integrity_issues) > 0
        
        return {
            'status': 'completed',
            'has_integrity_issues': has_integrity_issues,
            'promotes_integrity': promotes_integrity,
            'issues': integrity_issues,
            'safety_level': ContentSafetyLevel.CONTENT_WARNING if has_integrity_issues else ContentSafetyLevel.SAFE
        }
    
    async def _combine_validation_results(self, validation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine multiple validation results into overall assessment."""
        
        # Determine overall safety level (most restrictive wins)
        safety_levels = [result.get('safety_level', ContentSafetyLevel.SAFE) for result in validation_results]
        
        if ContentSafetyLevel.BLOCKED in safety_levels:
            overall_safety = ContentSafetyLevel.BLOCKED
        elif ContentSafetyLevel.CONTENT_WARNING in safety_levels:
            overall_safety = ContentSafetyLevel.CONTENT_WARNING
        elif ContentSafetyLevel.EDUCATIONAL_REVIEW in safety_levels:
            overall_safety = ContentSafetyLevel.EDUCATIONAL_REVIEW
        else:
            overall_safety = ContentSafetyLevel.SAFE
        
        # Collect all issues
        all_issues = []
        for result in validation_results:
            if 'issues' in result:
                all_issues.extend(result['issues'])
            if 'detected_issues' in result:
                all_issues.extend([f"{issue['category']}: {issue['pattern']}" for issue in result['detected_issues']])
            if result.get('status') == 'blocked':
                all_issues.append(result.get('reason', 'Content blocked'))
        
        # Calculate overall confidence
        confidences = []
        for result in validation_results:
            if 'educational_score' in result:
                confidences.append(result['educational_score'])
            elif result.get('status') == 'passed':
                confidences.append(0.9)
            elif result.get('status') == 'completed':
                confidences.append(0.8)
            else:
                confidences.append(0.5)
        
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        # Determine educational appropriateness
        educational_results = [result for result in validation_results if 'is_educational' in result]
        is_educational = all(result['is_educational'] for result in educational_results) if educational_results else True
        
        # Determine age appropriateness
        age_results = [result for result in validation_results if 'is_age_appropriate' in result]
        age_appropriate = all(result['is_age_appropriate'] for result in age_results) if age_results else True
        
        return {
            'overall_safety': overall_safety,
            'is_educational': is_educational,
            'age_appropriate': age_appropriate,
            'confidence': overall_confidence,
            'issues_found': all_issues
        }
    
    async def _generate_content_recommendations(
        self,
        issues: List[str],
        content_type: EducationalContentType,
        age_group: str
    ) -> List[str]:
        """Generate recommendations for improving content safety and appropriateness."""
        
        recommendations = []
        
        # General recommendations based on issues
        if any('harmful' in issue.lower() for issue in issues):
            recommendations.append("Remove or rephrase content that could be harmful or inappropriate")
        
        if any('complexity' in issue.lower() for issue in issues):
            recommendations.append(f"Simplify language and concepts for {age_group} audience")
        
        if any('educational' in issue.lower() for issue in issues):
            recommendations.append("Add more educational context and learning objectives")
        
        if any('integrity' in issue.lower() for issue in issues):
            recommendations.append("Include proper citations and promote academic honesty")
        
        # Content type specific recommendations
        if content_type == EducationalContentType.RESEARCH:
            recommendations.append("Ensure all sources are properly cited and credible")
        elif content_type == EducationalContentType.TUTORIAL:
            recommendations.append("Include step-by-step instructions and learning checkpoints")
        elif content_type == EducationalContentType.EXPLANATION:
            recommendations.append("Use clear examples and analogies appropriate for the audience")
        
        # Age group specific recommendations
        age_recommendations = {
            'elementary': "Use simple vocabulary and concrete examples",
            'middle_school': "Include age-appropriate examples and avoid complex concepts",
            'high_school': "Provide academic rigor while maintaining accessibility",
            'college': "Include advanced concepts with proper academic context"
        }
        
        if age_group in age_recommendations:
            recommendations.append(age_recommendations[age_group])
        
        return recommendations if recommendations else ["Content appears appropriate for educational use"]
    
    async def create_educational_guardrail(
        self,
        name: str,
        description: str,
        age_group: str = "college"
    ) -> Dict[str, Any]:
        """
        Create a custom Bedrock Guardrail for educational content.
        
        This is a placeholder for when Bedrock Guardrails API supports programmatic creation.
        """
        try:
            # This would be the actual implementation when the API is available
            # For now, return configuration that can be used to manually create the guardrail
            
            guardrail_config = {
                'name': name,
                'description': description,
                'age_group': age_group,
                'content_policy': {
                    'filters': [
                        {
                            'type': 'HATE',
                            'input_strength': 'HIGH',
                            'output_strength': 'HIGH'
                        },
                        {
                            'type': 'INSULTS',
                            'input_strength': 'HIGH',
                            'output_strength': 'HIGH'
                        },
                        {
                            'type': 'MISCONDUCT',
                            'input_strength': 'HIGH',
                            'output_strength': 'HIGH'
                        },
                        {
                            'type': 'PROMPT_ATTACK',
                            'input_strength': 'HIGH',
                            'output_strength': 'NONE'
                        }
                    ]
                },
                'topic_policy': {
                    'topics': [
                        {
                            'name': 'Educational Content Only',
                            'definition': 'Content must be educational, academic, or learning-focused',
                            'examples': ['study materials', 'academic research', 'learning resources'],
                            'type': 'ALLOW'
                        },
                        {
                            'name': 'Inappropriate Content',
                            'definition': 'Content inappropriate for educational environments',
                            'examples': ['violence', 'adult content', 'illegal activities'],
                            'type': 'DENY'
                        }
                    ]
                },
                'word_policy': {
                    'words': [
                        {
                            'text': word,
                            'action': 'BLOCK'
                        } for category_words in self.blocked_patterns.values() for word in category_words
                    ]
                }
            }
            
            return {
                'success': True,
                'message': 'Guardrail configuration generated. Use AWS Console to create the actual guardrail.',
                'config': guardrail_config
            }
            
        except Exception as e:
            logger.error(f"Error creating guardrail configuration: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to generate guardrail configuration'
            }
    
    async def get_content_safety_report(
        self,
        content_list: List[str],
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """Generate a comprehensive safety report for multiple content pieces."""
        
        try:
            total_content = len(content_list)
            safe_content = 0
            flagged_content = 0
            blocked_content = 0
            
            detailed_results = []
            
            # Process content in batches
            for i in range(0, total_content, batch_size):
                batch = content_list[i:i + batch_size]
                
                for j, content in enumerate(batch):
                    result = await self.validate_content_comprehensive(content)
                    
                    detailed_results.append({
                        'content_index': i + j,
                        'content_preview': content[:100] + '...' if len(content) > 100 else content,
                        'safety_level': result['overall_safety'],
                        'is_educational': result['is_educational'],
                        'issues_count': len(result['issues_found']),
                        'confidence': result['confidence']
                    })
                    
                    # Update counters
                    if result['overall_safety'] == ContentSafetyLevel.SAFE:
                        safe_content += 1
                    elif result['overall_safety'] == ContentSafetyLevel.BLOCKED:
                        blocked_content += 1
                    else:
                        flagged_content += 1
            
            return {
                'summary': {
                    'total_content': total_content,
                    'safe_content': safe_content,
                    'flagged_content': flagged_content,
                    'blocked_content': blocked_content,
                    'safety_percentage': (safe_content / total_content) * 100 if total_content > 0 else 0
                },
                'detailed_results': detailed_results,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating safety report: {e}")
            return {
                'summary': {
                    'total_content': len(content_list),
                    'error': str(e)
                },
                'detailed_results': [],
                'timestamp': datetime.now(timezone.utc).isoformat()
            }


# Global service instance
content_guardrails_service = ContentGuardrailsService()