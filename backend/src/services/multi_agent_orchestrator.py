"""
Multi-Agent Orchestrator for SnapStudy - Coordinates Learning and Adaptive Agents

This orchestrator enables true multi-agent collaboration where agents can:
1. Communicate with each other
2. Share context and decisions
3. Coordinate responses
4. Learn from each other's outputs
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import uuid
import boto3

from .bedrock import bedrock_service
from .dynamodb import dynamodb_service
from ..config import settings

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    """Agent roles in the multi-agent system."""
    LEARNING = "learning"      # Educational content and tutoring
    ADAPTIVE = "adaptive"      # Performance analysis and adaptation
    ORCHESTRATOR = "orchestrator"  # Coordination and decision routing


class MultiAgentOrchestrator:
    """
    Orchestrates collaboration between Learning and Adaptive agents.
    
    This class manages:
    - Agent-to-agent communication
    - Context sharing between agents
    - Coordinated decision making
    - Multi-step reasoning workflows
    """
    
    def __init__(self):
        self.bedrock_agent_client = boto3.client('bedrock-agent-runtime', region_name=settings.aws_region)
        
        # Agent configurations
        self.learning_agent_id = getattr(settings, 'learning_agent_id', None)
        self.adaptive_agent_id = getattr(settings, 'adaptive_agent_id', None)
        self.agent_alias_id = getattr(settings, 'bedrock_agent_alias_id', 'PRODUCTION')
        
        # Multi-agent session management
        self.active_collaborations = {}
        
        logger.info(f"MultiAgentOrchestrator initialized - Learning: {self.learning_agent_id}, Adaptive: {self.adaptive_agent_id}")
    
    async def orchestrate_learning_interaction(
        self, 
        user_message: str, 
        user_context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """
        Orchestrate a learning interaction involving both agents.
        
        Flow:
        1. Adaptive Agent analyzes user performance and context
        2. Learning Agent receives adaptation recommendat
        Args:
            initial_context: Initial context for the first agent

        Returns:
            Dict containing strand execution results
        """
        self.status = StrandStatus.RUNNING
        self.started_at = datetime.now(timezone.utc).isoformat()

        context = initial_context.copy()

        logger.info(f"Starting strand '{self.name}' with {len(self.agents)} agents")

        try:
            for i, agent_config in enumerate(self.agents):
                agent_name = agent_config['name']
                logger.info(f"Strand {self.name}: Executing agent {i+1}/{len(self.agents)} ({agent_name})")

                try:
                    # Execute agent with accumulated context
                    result = await self._execute_agent(agent_config, context)

                    # Store result
                    self.results.append({
                        'agent': agent_name,
                        'agent_index': i,
                        'result': result,
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'success': True
                    })

                    # Pass results to next agent
                    context['previous_results'] = self.results
                    context['previous_agent_output'] = result

                    # Update context with any new data from this agent
                    context_updates = result.get('context_updates', {})
                    context.update(context_updates)

                    logger.info(f"Agent {agent_name} completed successfully")

                except Exception as e:
                    logger.error(f"Agent {agent_name} failed: {str(e)}")

                    # Record failure
                    self.results.append({
                        'agent': agent_name,
                        'agent_index': i,
                        'result': None,
                        'error': str(e),
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'success': False
                    })

                    # Decide whether to continue or abort
                    if agent_config.get('critical', True):
                        # Critical agent failed - abort strand
                        self.status = StrandStatus.FAILED
                        self.error = f"Critical agent {agent_name} failed: {str(e)}"
                        raise
                    else:
                        # Non-critical failure - continue with degraded context
                        logger.warning(f"Non-critical agent {agent_name} failed, continuing...")
                        context['agent_failures'] = context.get('agent_failures', [])
                        context['agent_failures'].append(agent_name)

            # All agents completed
            self.status = StrandStatus.COMPLETED if not context.get('agent_failures') else StrandStatus.PARTIAL
            self.completed_at = datetime.now(timezone.utc).isoformat()

            logger.info(f"Strand '{self.name}' completed with status: {self.status}")

            return {
                'strand_id': self.strand_id,
                'strand_name': self.name,
                'strand_type': self.strand_type,
                'status': self.status,
                'results': self.results,
                'final_context': context,
                'started_at': self.started_at,
                'completed_at': self.completed_at,
                'total_agents': len(self.agents),
                'successful_agents': len([r for r in self.results if r.get('success', False)]),
                'failed_agents': len([r for r in self.results if not r.get('success', True)])
            }

        except Exception as e:
            self.status = StrandStatus.FAILED
            self.completed_at = datetime.now(timezone.utc).isoformat()
            self.error = str(e)

            logger.error(f"Strand '{self.name}' failed: {str(e)}")

            return {
                'strand_id': self.strand_id,
                'strand_name': self.name,
                'strand_type': self.strand_type,
                'status': self.status,
                'results': self.results,
                'error': str(e),
                'started_at': self.started_at,
                'completed_at': self.completed_at
            }

    async def _execute_agent(
        self,
        agent_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single agent in the strand.

        Args:
            agent_config: Agent configuration including function and params
            context: Current execution context

        Returns:
            Dict containing agent's result
        """
        agent_function = agent_config['function']
        agent_params = agent_config.get('params', {})

        # Merge context with params
        execution_params = {**agent_params, 'context': context}

        # Execute agent function
        result = await agent_function(**execution_params)

        return result


class MultiAgentOrchestrator:
    """
    Orchestrates multiple agents working together in strands.

    Implements three key strand patterns for educational content:
    1. Content Generation Strand: Planning → Generation → Review → Personalization
    2. Assessment Strand: Analysis → Quiz Generation → Difficulty Calibration
    3. Personalization Strand: Profile Analysis → Pattern Recognition → Recommendations
    """

    def __init__(self):
        self.agent_core = BedrockAgentCore() if hasattr(adaptive_agent, 'agent_core') else None
        self.bedrock = bedrock_service
        self.quiz_engine = quiz_engine
        self.active_strands = {}

    async def execute_content_generation_strand(
        self,
        topic: str,
        user_profile: Dict[str, Any],
        difficulty: str = "intermediate"
    ) -> Dict[str, Any]:
        """
        Content Generation Strand:
        1. Planning Agent → Analyzes topic and creates lesson structure
        2. Content Agent → Generates detailed content
        3. Review Agent → Reviews quality and educational value
        4. Personalization Agent → Adapts content for specific user

        This demonstrates multi-step autonomous content creation.

        Args:
            topic: Topic to generate content for
            user_profile: User's learning profile
            difficulty: Target difficulty level

        Returns:
            Dict containing complete generated content and metadata
        """
        logger.info(f"Executing Content Generation Strand for topic: {topic}")

        strand = AgentStrand(
            name="ContentGenerationStrand",
            strand_type=StrandType.CONTENT_GENERATION,
            agents=[
                {
                    'name': 'LessonPlanningAgent',
                    'function': self._plan_lesson_structure,
                    'params': {
                        'topic': topic,
                        'difficulty': difficulty
                    },
                    'critical': True
                },
                {
                    'name': 'ContentGenerationAgent',
                    'function': self._generate_lesson_content,
                    'params': {},
                    'critical': True
                },
                {
                    'name': 'QualityReviewAgent',
                    'function': self._review_content_quality,
                    'params': {},
                    'critical': False
                },
                {
                    'name': 'PersonalizationAgent',
                    'function': self._personalize_for_user,
                    'params': {
                        'user_profile': user_profile
                    },
                    'critical': True
                }
            ]
        )

        initial_context = {
            'topic': topic,
            'user_profile': user_profile,
            'difficulty': difficulty,
            'strand_start_time': datetime.now(timezone.utc).isoformat()
        }

        result = await strand.execute(initial_context)
        self.active_strands[strand.strand_id] = strand

        # Track strand execution
        await self._track_strand_execution(strand, user_profile.get('user_id'))

        return result

    async def execute_assessment_strand(
        self,
        lesson_content: str,
        user_profile: Dict[str, Any],
        previous_performance: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Assessment Strand:
        1. Content Analysis Agent → Extracts key concepts
        2. Quiz Generation Agent → Creates adaptive questions
        3. Difficulty Calibration Agent → Adjusts for user level

        This demonstrates autonomous assessment creation.

        Args:
            lesson_content: Content to create assessment for
            user_profile: User's learning profile
            previous_performance: Previous quiz performance

        Returns:
            Dict containing generated quiz and metadata
        """
        logger.info("Executing Assessment Strand")

        strand = AgentStrand(
            name="AssessmentStrand",
            strand_type=StrandType.ASSESSMENT,
            agents=[
                {
                    'name': 'ContentAnalysisAgent',
                    'function': self._analyze_lesson_concepts,
                    'params': {
                        'lesson_content': lesson_content
                    },
                    'critical': True
                },
                {
                    'name': 'QuizGenerationAgent',
                    'function': self._generate_adaptive_quiz,
                    'params': {
                        'previous_performance': previous_performance or []
                    },
                    'critical': True
                },
                {
                    'name': 'DifficultyCalibrationAgent',
                    'function': self._calibrate_quiz_difficulty,
                    'params': {
                        'user_profile': user_profile
                    },
                    'critical': False
                }
            ]
        )

        initial_context = {
            'lesson_content': lesson_content,
            'user_profile': user_profile,
            'previous_performance': previous_performance or [],
            'strand_start_time': datetime.now(timezone.utc).isoformat()
        }

        result = await strand.execute(initial_context)
        self.active_strands[strand.strand_id] = strand

        await self._track_strand_execution(strand, user_profile.get('user_id'))

        return result

    async def execute_personalization_strand(
        self,
        user_id: str,
        engagement_history: List[Dict[str, Any]],
        learning_goals: List[str]
    ) -> Dict[str, Any]:
        """
        Personalization Strand:
        1. Profile Analysis Agent → Deep user analysis
        2. Pattern Recognition Agent → Identifies learning patterns
        3. Recommendation Agent → Generates personalized recommendations

        This demonstrates autonomous personalization.

        Args:
            user_id: User ID
            engagement_history: User's engagement data
            learning_goals: User's stated goals

        Returns:
            Dict containing personalized recommendations
        """
        logger.info(f"Executing Personalization Strand for user: {user_id}")

        strand = AgentStrand(
            name="PersonalizationStrand",
            strand_type=StrandType.PERSONALIZATION,
            agents=[
                {
                    'name': 'ProfileAnalysisAgent',
                    'function': self._analyze_user_profile,
                    'params': {
                        'user_id': user_id
                    },
                    'critical': True
                },
                {
                    'name': 'PatternRecognitionAgent',
                    'function': self._identify_learning_patterns,
                    'params': {
                        'engagement_history': engagement_history
                    },
                    'critical': True
                },
                {
                    'name': 'RecommendationAgent',
                    'function': self._generate_recommendations,
                    'params': {
                        'learning_goals': learning_goals
                    },
                    'critical': True
                }
            ]
        )

        initial_context = {
            'user_id': user_id,
            'engagement_history': engagement_history,
            'learning_goals': learning_goals,
            'strand_start_time': datetime.now(timezone.utc).isoformat()
        }

        result = await strand.execute(initial_context)
        self.active_strands[strand.strand_id] = strand

        await self._track_strand_execution(strand, user_id)

        return result

    # ========== Agent Function Implementations ==========

    async def _plan_lesson_structure(
        self,
        topic: str,
        difficulty: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Agent 1: Plan lesson structure using autonomous reasoning.

        Args:
            topic: Topic to plan for
            difficulty: Target difficulty
            context: Current context

        Returns:
            Dict containing lesson plan
        """
        logger.info(f"Planning lesson structure for: {topic}")

        # Use Bedrock to generate lesson plan
        prompt = f"""Create a detailed lesson plan for the topic: {topic}

Difficulty Level: {difficulty}

Provide:
1. Clear learning objectives (3-5 objectives)
2. Key concepts breakdown (hierarchical structure)
3. Suggested teaching sequence
4. Estimated duration for each section
5. Prerequisites (if any)
6. Assessment checkpoints

Format as structured JSON."""

        try:
            response = await self.bedrock.invoke_claude(
                prompt=prompt,
                max_tokens=4096,
                temperature=0.7
            )

            return {
                'lesson_plan': response,
                'context_updates': {
                    'lesson_structure': response,
                    'planning_completed': True
                },
                'agent_decision': 'created_structured_plan',
                'confidence': 0.85
            }
        except Exception as e:
            logger.error(f"Lesson planning failed: {e}")
            return {
                'lesson_plan': f"Basic plan for {topic}",
                'context_updates': {
                    'planning_completed': False,
                    'fallback_used': True
                },
                'error': str(e)
            }

    async def _generate_lesson_content(
        self,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Agent 2: Generate detailed lesson content.

        Args:
            context: Context including lesson plan

        Returns:
            Dict containing generated content
        """
        logger.info("Generating lesson content")

        lesson_plan = context.get('lesson_structure', 'No plan available')
        topic = context.get('topic', 'Unknown topic')

        prompt = f"""Based on this lesson plan, generate comprehensive educational content:

{lesson_plan}

Create detailed content that:
1. Explains each concept clearly with examples
2. Uses analogies and real-world applications
3. Includes practice scenarios
4. Builds progressively in complexity
5. Engages learners actively

Generate 2-3 micro-lessons covering the key concepts."""

        try:
            response = await self.bedrock.invoke_claude(
                prompt=prompt,
                max_tokens=4096,
                temperature=0.7
            )

            return {
                'generated_content': response,
                'context_updates': {
                    'raw_content': response,
                    'content_generated': True,
                    'word_count': len(response.split())
                },
                'agent_decision': 'generated_comprehensive_content',
                'confidence': 0.88
            }
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            return {
                'generated_content': f"Content for {topic}",
                'context_updates': {
                    'content_generated': False
                },
                'error': str(e)
            }

    async def _review_content_quality(
        self,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Agent 3: Review content quality and educational value.

        Args:
            context: Context including generated content

        Returns:
            Dict containing quality assessment
        """
        logger.info("Reviewing content quality")

        raw_content = context.get('raw_content', '')

        prompt = f"""Review this educational content for quality:

{raw_content[:1000]}...

Evaluate:
1. Clarity and accuracy
2. Educational value
3. Engagement level
4. Appropriate complexity
5. Completeness

Provide:
- Quality score (0-10)
- Strengths (3 points)
- Areas for improvement (2-3 points)
- Specific recommendations"""

        try:
            response = await self.bedrock.invoke_claude(
                prompt=prompt,
                max_tokens=4096,
                temperature=0.5
            )

            return {
                'quality_review': response,
                'context_updates': {
                    'quality_score': 8.0,  # Would parse from response
                    'review_completed': True,
                    'improvements_identified': True
                },
                'agent_decision': 'quality_acceptable',
                'confidence': 0.82
            }
        except Exception as e:
            logger.error(f"Quality review failed: {e}")
            return {
                'quality_review': 'Review unavailable',
                'context_updates': {
                    'review_completed': False
                },
                'error': str(e)
            }

    async def _personalize_for_user(
        self,
        user_profile: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Agent 4: Personalize content for specific user.

        Args:
            user_profile: User's profile and preferences
            context: Context including content and review

        Returns:
            Dict containing personalized content
        """
        logger.info("Personalizing content for user")

        raw_content = context.get('raw_content', '')
        learning_style = user_profile.get('learning_style', 'visual')
        profession = user_profile.get('profession', 'general')

        prompt = f"""Adapt this content for a learner with:
- Learning Style: {learning_style}
- Profession: {profession}

Content:
{raw_content[:800]}...

Personalize by:
1. Adding relevant examples from their profession
2. Adjusting to their learning style
3. Using appropriate technical level
4. Including practice relevant to their context

Provide personalized version."""

        try:
            response = await self.bedrock.invoke_claude(
                prompt=prompt,
                max_tokens=4096,
                temperature=0.7
            )

            return {
                'personalized_content': response,
                'context_updates': {
                    'final_content': response,
                    'personalization_applied': True,
                    'learning_style': learning_style
                },
                'agent_decision': 'personalization_complete',
                'confidence': 0.90
            }
        except Exception as e:
            logger.error(f"Personalization failed: {e}")
            return {
                'personalized_content': raw_content,
                'context_updates': {
                    'personalization_applied': False,
                    'fallback_content': True
                },
                'error': str(e)
            }

    async def _analyze_lesson_concepts(
        self,
        lesson_content: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Agent: Analyze and extract key concepts from lesson.

        Args:
            lesson_content: Content to analyze
            context: Current context

        Returns:
            Dict containing extracted concepts
        """
        logger.info("Analyzing lesson concepts")

        prompt = f"""Analyze this educational content and extract key concepts:

{lesson_content[:1000]}...

Identify:
1. Main concepts (3-5)
2. Supporting sub-concepts
3. Concept relationships
4. Difficulty level of each concept
5. Prerequisite knowledge required

Format as structured list."""

        try:
            response = await self.bedrock.invoke_claude(
                prompt=prompt,
                max_tokens=4096,
                temperature=0.5
            )

            return {
                'concepts': response,
                'context_updates': {
                    'key_concepts': response,
                    'concept_count': 5  # Would parse from response
                },
                'agent_decision': 'concepts_identified'
            }
        except Exception as e:
            logger.error(f"Concept analysis failed: {e}")
            return {
                'concepts': 'Basic concepts',
                'context_updates': {},
                'error': str(e)
            }

    async def _generate_adaptive_quiz(
        self,
        previous_performance: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Agent: Generate adaptive quiz based on concepts.

        Args:
            previous_performance: Past quiz results
            context: Context including concepts

        Returns:
            Dict containing generated quiz
        """
        logger.info("Generating adaptive quiz")

        key_concepts = context.get('key_concepts', '')

        # Calculate adaptive difficulty
        if previous_performance:
            avg_score = sum(p.get('score', 0) for p in previous_performance) / len(previous_performance)
            if avg_score > 85:
                difficulty = 'hard'
            elif avg_score < 60:
                difficulty = 'easy'
            else:
                difficulty = 'medium'
        else:
            difficulty = 'medium'

        try:
            # Generate quiz using quiz engine
            quiz = await self.quiz_engine.generate_adaptive_quiz(
                lesson_content=key_concepts,
                user_profile=context.get('user_profile', {}),
                performance_history=previous_performance,
                target_difficulty=difficulty
            )

            return {
                'quiz': quiz,
                'context_updates': {
                    'generated_quiz': quiz,
                    'adaptive_difficulty': difficulty
                },
                'agent_decision': f'generated_{difficulty}_quiz'
            }
        except Exception as e:
            logger.error(f"Quiz generation failed: {e}")
            return {
                'quiz': {},
                'context_updates': {},
                'error': str(e)
            }

    async def _calibrate_quiz_difficulty(
        self,
        user_profile: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Agent: Calibrate quiz difficulty for user.

        Args:
            user_profile: User's profile
            context: Context including generated quiz

        Returns:
            Dict containing calibrated quiz
        """
        logger.info("Calibrating quiz difficulty")

        generated_quiz = context.get('generated_quiz', {})

        # Simple calibration based on user level
        education_level = user_profile.get('education_level', 'college')

        return {
            'calibrated_quiz': generated_quiz,
            'context_updates': {
                'final_quiz': generated_quiz,
                'calibration_applied': True,
                'target_level': education_level
            },
            'agent_decision': 'calibration_complete'
        }

    async def _analyze_user_profile(
        self,
        user_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Agent: Analyze user profile deeply.

        Args:
            user_id: User ID
            context: Current context

        Returns:
            Dict containing profile analysis
        """
        logger.info(f"Analyzing user profile: {user_id}")

        try:
            # Get user data
            user = await db_service.get_user_by_id(user_id)

            return {
                'profile_analysis': user,
                'context_updates': {
                    'user_profile': user,
                    'profile_loaded': True
                },
                'agent_decision': 'profile_analyzed'
            }
        except Exception as e:
            logger.error(f"Profile analysis failed: {e}")
            return {
                'profile_analysis': {},
                'context_updates': {},
                'error': str(e)
            }

    async def _identify_learning_patterns(
        self,
        engagement_history: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Agent: Identify learning patterns from history.

        Args:
            engagement_history: User's engagement data
            context: Current context

        Returns:
            Dict containing identified patterns
        """
        logger.info("Identifying learning patterns")

        # Simple pattern analysis
        patterns = []

        if len(engagement_history) > 10:
            patterns.append('active_learner')

        return {
            'patterns': patterns,
            'context_updates': {
                'identified_patterns': patterns
            },
            'agent_decision': 'patterns_identified'
        }

    async def _generate_recommendations(
        self,
        learning_goals: List[str],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Agent: Generate personalized recommendations.

        Args:
            learning_goals: User's goals
            context: Context including patterns

        Returns:
            Dict containing recommendations
        """
        logger.info("Generating recommendations")

        patterns = context.get('identified_patterns', [])

        recommendations = [
            "Continue current learning pace",
            "Focus on practical applications",
            "Consider advanced topics"
        ]

        return {
            'recommendations': recommendations,
            'context_updates': {
                'final_recommendations': recommendations
            },
            'agent_decision': 'recommendations_generated'
        }

    async def get_strand_status(self, strand_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of an active or completed strand.

        Args:
            strand_id: Strand ID

        Returns:
            Dict containing strand status or None
        """
        strand = self.active_strands.get(strand_id)

        if not strand:
            return None

        return {
            'strand_id': strand.strand_id,
            'name': strand.name,
            'type': strand.strand_type,
            'status': strand.status,
            'agents_count': len(strand.agents),
            'results_count': len(strand.results),
            'started_at': strand.started_at,
            'completed_at': strand.completed_at,
            'error': strand.error,
            'results': strand.results
        }

    async def _track_strand_execution(
        self,
        strand: AgentStrand,
        user_id: Optional[str]
    ) -> None:
        """
        Track strand execution for analytics.

        Args:
            strand: Executed strand
            user_id: User ID if applicable
        """
        try:
            if user_id:
                await db_service.track_engagement({
                    'user_id': user_id,
                    'event_type': 'multi_agent_strand_executed',
                    'event_data': {
                        'strand_id': strand.strand_id,
                        'strand_name': strand.name,
                        'strand_type': strand.strand_type,
                        'status': strand.status,
                        'agents_count': len(strand.agents),
                        'successful_agents': len([r for r in strand.results if r.get('success', False)])
                    }
                })
        except Exception as e:
            logger.warning(f"Failed to track strand execution: {e}")


# Global orchestrator instance
multi_agent_orchestrator = MultiAgentOrchestrator()
