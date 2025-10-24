"""
AWS Step Functions Multi-Agent Orchestrator for SnapStudy.

This service uses AWS Step Functions to orchestrate complex multi-agent workflows
that involve multiple Bedrock Agents working together autonomously to achieve
educational objectives.

Key Features:
- Multi-agent coordination using Step Functions
- Error handling and retry logic
- Parallel agent execution
- State management across agent steps
- Audit trail of agent decisions
"""

import boto3
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import uuid
from enum import Enum

from ..config import settings

logger = logging.getLogger(__name__)


class WorkflowType(str, Enum):
    """Types of multi-agent workflows."""
    ADAPTIVE_LEARNING_PATH = "adaptive_learning_path"
    CONTENT_GENERATION_PIPELINE = "content_generation_pipeline"
    ASSESSMENT_CREATION = "assessment_creation"
    PERSONALIZATION_ENGINE = "personalization_engine"


class StepFunctionsOrchestrator:
    """
    Orchestrates multi-agent workflows using AWS Step Functions.

    Provides sophisticated agent coordination patterns beyond simple sequential execution:
    - Parallel agent execution
    - Conditional branching based on agent outputs
    - Error recovery and retry strategies
    - Human-in-the-loop decision points (optional)
    - State persistence across workflow steps
    """

    def __init__(self):
        self.stepfunctions_client = boto3.client('stepfunctions', region_name=settings.aws_region)
        self.state_machine_arn = getattr(settings, 'agent_orchestrator_state_machine_arn', None)

        logger.info(f"StepFunctionsOrchestrator initialized")

    def get_adaptive_learning_workflow_definition(self) -> Dict[str, Any]:
        """
        Define the adaptive learning workflow state machine.

        This workflow orchestrates multiple agents to create a personalized learning path:
        1. Profile Analysis Agent - Analyzes learner profile
        2. Content Recommendation Agent - Recommends content based on profile
        3. Parallel execution:
           a. Difficulty Calibration Agent - Adjusts content difficulty
           b. Format Selection Agent - Chooses optimal content format
        4. Content Generation Agent - Generates final personalized content
        5. Quality Assurance Agent - Reviews generated content
        """
        return {
            "Comment": "Adaptive Learning Path Multi-Agent Workflow",
            "StartAt": "AnalyzeUserProfile",
            "States": {
                "AnalyzeUserProfile": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::bedrock:invokeAgent",
                    "Parameters": {
                        "AgentId": settings.learning_agent_id,
                        "AgentAliasId": settings.bedrock_agent_alias_id,
                        "SessionId.$": "$.sessionId",
                        "InputText.$": "States.Format('Analyze learner profile for user {} with learning history: {}', $.userId, $.learningHistory)"
                    },
                    "ResultPath": "$.profileAnalysis",
                    "Next": "RecommendContent",
                    "Catch": [{
                        "ErrorEquals": ["States.ALL"],
                        "ResultPath": "$.error",
                        "Next": "HandleProfileAnalysisError"
                    }]
                },
                "RecommendContent": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::bedrock:invokeAgent",
                    "Parameters": {
                        "AgentId": settings.adaptive_agent_id,
                        "AgentAliasId": settings.bedrock_agent_alias_id,
                        "SessionId.$": "$.sessionId",
                        "InputText.$": "States.Format('Recommend learning content based on profile: {}', $.profileAnalysis)"
                    },
                    "ResultPath": "$.contentRecommendations",
                    "Next": "ParallelContentOptimization"
                },
                "ParallelContentOptimization": {
                    "Type": "Parallel",
                    "Branches": [
                        {
                            "StartAt": "CalibrateDifficulty",
                            "States": {
                                "CalibrateDifficulty": {
                                    "Type": "Task",
                                    "Resource": "arn:aws:states:::bedrock:invokeAgent",
                                    "Parameters": {
                                        "AgentId": settings.adaptive_agent_id,
                                        "AgentAliasId": settings.bedrock_agent_alias_id,
                                        "SessionId.$": "$.sessionId",
                                        "InputText.$": "States.Format('Calibrate difficulty for content: {}', $.contentRecommendations)"
                                    },
                                    "End": True
                                }
                            }
                        },
                        {
                            "StartAt": "SelectOptimalFormat",
                            "States": {
                                "SelectOptimalFormat": {
                                    "Type": "Task",
                                    "Resource": "arn:aws:states:::bedrock:invokeAgent",
                                    "Parameters": {
                                        "AgentId": settings.learning_agent_id,
                                        "AgentAliasId": settings.bedrock_agent_alias_id,
                                        "SessionId.$": "$.sessionId",
                                        "InputText.$": "States.Format('Select optimal content format based on learning style: {}', $.profileAnalysis.learningStyle)"
                                    },
                                    "End": True
                                }
                            }
                        }
                    ],
                    "ResultPath": "$.optimizationResults",
                    "Next": "GeneratePersonalizedContent"
                },
                "GeneratePersonalizedContent": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::bedrock:invokeAgent",
                    "Parameters": {
                        "AgentId": settings.learning_agent_id,
                        "AgentAliasId": settings.bedrock_agent_alias_id,
                        "SessionId.$": "$.sessionId",
                        "InputText.$": "States.Format('Generate personalized content with difficulty {} and format {}', $.optimizationResults[0], $.optimizationResults[1])"
                    },
                    "ResultPath": "$.generatedContent",
                    "Next": "QualityAssuranceReview"
                },
                "QualityAssuranceReview": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::bedrock:invokeAgent",
                    "Parameters": {
                        "AgentId": settings.learning_agent_id,
                        "AgentAliasId": settings.bedrock_agent_alias_id,
                        "SessionId.$": "$.sessionId",
                        "InputText.$": "States.Format('Review quality of generated content: {}', $.generatedContent)"
                    },
                    "ResultPath": "$.qualityReview",
                    "Next": "CheckQualityScore"
                },
                "CheckQualityScore": {
                    "Type": "Choice",
                    "Choices": [{
                        "Variable": "$.qualityReview.score",
                        "NumericGreaterThanEquals": 0.8,
                        "Next": "WorkflowSuccess"
                    }],
                    "Default": "RegenerateContent"
                },
                "RegenerateContent": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::bedrock:invokeAgent",
                    "Parameters": {
                        "AgentId": settings.learning_agent_id,
                        "AgentAliasId": settings.bedrock_agent_alias_id,
                        "SessionId.$": "$.sessionId",
                        "InputText.$": "States.Format('Regenerate content addressing quality issues: {}', $.qualityReview.issues)"
                    },
                    "ResultPath": "$.generatedContent",
                    "Next": "WorkflowSuccess"
                },
                "HandleProfileAnalysisError": {
                    "Type": "Pass",
                    "Result": {
                        "error": "Profile analysis failed",
                        "fallbackUsed": True
                    },
                    "ResultPath": "$.profileAnalysis",
                    "Next": "RecommendContent"
                },
                "WorkflowSuccess": {
                    "Type": "Succeed"
                }
            }
        }

    def get_content_generation_pipeline_definition(self) -> Dict[str, Any]:
        """
        Define content generation pipeline workflow.

        Multi-stage content generation with quality gates:
        1. Topic Analysis Agent
        2. Outline Generation Agent
        3. Content Writing Agent
        4. Review Agent
        5. Guardrails Check
        """
        return {
            "Comment": "Content Generation Pipeline with Multi-Agent Collaboration",
            "StartAt": "AnalyzeTopic",
            "States": {
                "AnalyzeTopic": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::bedrock:invokeAgent",
                    "Parameters": {
                        "AgentId": settings.learning_agent_id,
                        "AgentAliasId": settings.bedrock_agent_alias_id,
                        "SessionId.$": "$.sessionId",
                        "InputText.$": "States.Format('Analyze topic and extract key concepts: {}', $.topic)"
                    },
                    "ResultPath": "$.topicAnalysis",
                    "Next": "GenerateOutline"
                },
                "GenerateOutline": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::bedrock:invokeAgent",
                    "Parameters": {
                        "AgentId": settings.learning_agent_id,
                        "AgentAliasId": settings.bedrock_agent_alias_id,
                        "SessionId.$": "$.sessionId",
                        "InputText.$": "States.Format('Generate detailed outline for topic analysis: {}', $.topicAnalysis)"
                    },
                    "ResultPath": "$.outline",
                    "Next": "ParallelContentCreation"
                },
                "ParallelContentCreation": {
                    "Type": "Parallel",
                    "Branches": [
                        {
                            "StartAt": "WriteMainContent",
                            "States": {
                                "WriteMainContent": {
                                    "Type": "Task",
                                    "Resource": "arn:aws:states:::bedrock:invokeAgent",
                                    "Parameters": {
                                        "AgentId": settings.learning_agent_id,
                                        "AgentAliasId": settings.bedrock_agent_alias_id,
                                        "InputText.$": "States.Format('Write educational content for outline: {}', $.outline)"
                                    },
                                    "End": True
                                }
                            }
                        },
                        {
                            "StartAt": "GenerateExamples",
                            "States": {
                                "GenerateExamples": {
                                    "Type": "Task",
                                    "Resource": "arn:aws:states:::bedrock:invokeAgent",
                                    "Parameters": {
                                        "AgentId": settings.learning_agent_id,
                                        "AgentAliasId": settings.bedrock_agent_alias_id,
                                        "InputText.$": "States.Format('Generate practical examples for concepts: {}', $.topicAnalysis.keyConcepts)"
                                    },
                                    "End": True
                                }
                            }
                        },
                        {
                            "StartAt": "CreateAssessment",
                            "States": {
                                "CreateAssessment": {
                                    "Type": "Task",
                                    "Resource": "arn:aws:states:::bedrock:invokeAgent",
                                    "Parameters": {
                                        "AgentId": settings.adaptive_agent_id,
                                        "AgentAliasId": settings.bedrock_agent_alias_id,
                                        "InputText.$": "States.Format('Create assessment questions for outline: {}', $.outline)"
                                    },
                                    "End": True
                                }
                            }
                        }
                    ],
                    "ResultPath": "$.contentComponents",
                    "Next": "AssembleContent"
                },
                "AssembleContent": {
                    "Type": "Pass",
                    "Parameters": {
                        "mainContent.$": "$.contentComponents[0]",
                        "examples.$": "$.contentComponents[1]",
                        "assessment.$": "$.contentComponents[2]",
                        "outline.$": "$.outline"
                    },
                    "ResultPath": "$.assembledContent",
                    "Next": "ReviewContent"
                },
                "ReviewContent": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::bedrock:invokeAgent",
                    "Parameters": {
                        "AgentId": settings.learning_agent_id,
                        "AgentAliasId": settings.bedrock_agent_alias_id,
                        "InputText.$": "States.Format('Review assembled content for quality and coherence: {}', $.assembledContent)"
                    },
                    "ResultPath": "$.review",
                    "Next": "ApplyGuardrails"
                },
                "ApplyGuardrails": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::aws-sdk:bedrockruntime:applyGuardrail",
                    "Parameters": {
                        "GuardrailIdentifier": settings.bedrock_guardrail_id,
                        "GuardrailVersion": settings.bedrock_guardrail_version,
                        "Source": "INPUT",
                        "Content": [{
                            "Text": {
                                "Text.$": "$.assembledContent.mainContent"
                            }
                        }]
                    },
                    "ResultPath": "$.guardrailsResult",
                    "Next": "CheckGuardrails"
                },
                "CheckGuardrails": {
                    "Type": "Choice",
                    "Choices": [{
                        "Variable": "$.guardrailsResult.Action",
                        "StringEquals": "NONE",
                        "Next": "ContentApproved"
                    }],
                    "Default": "ContentBlocked"
                },
                "ContentApproved": {
                    "Type": "Succeed"
                },
                "ContentBlocked": {
                    "Type": "Fail",
                    "Error": "ContentGuardrailViolation",
                    "Cause": "Content blocked by Bedrock Guardrails"
                }
            }
        }

    async def start_workflow(
        self,
        workflow_type: WorkflowType,
        input_data: Dict[str, Any],
        execution_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start a multi-agent workflow execution.

        Args:
            workflow_type: Type of workflow to execute
            input_data: Input data for the workflow
            execution_name: Optional execution name (auto-generated if not provided)

        Returns:
            Dict containing execution ARN and start information
        """
        try:
            if not execution_name:
                execution_name = f"{workflow_type.value}-{uuid.uuid4()}"

            # Add metadata to input
            workflow_input = {
                **input_data,
                'workflowType': workflow_type.value,
                'sessionId': str(uuid.uuid4()),
                'startedAt': datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"Starting workflow: {workflow_type.value}, execution: {execution_name}")

            # Start execution
            response = self.stepfunctions_client.start_execution(
                stateMachineArn=self.state_machine_arn,
                name=execution_name,
                input=json.dumps(workflow_input)
            )

            return {
                'success': True,
                'executionArn': response['executionArn'],
                'executionName': execution_name,
                'workflowType': workflow_type.value,
                'startDate': response['startDate'].isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to start workflow: {e}")
            return {
                'success': False,
                'error': str(e),
                'workflowType': workflow_type.value
            }

    async def get_execution_status(self, execution_arn: str) -> Dict[str, Any]:
        """
        Get status of a workflow execution.

        Args:
            execution_arn: ARN of the execution

        Returns:
            Dict containing execution status and results
        """
        try:
            response = self.stepfunctions_client.describe_execution(
                executionArn=execution_arn
            )

            result = {
                'executionArn': execution_arn,
                'status': response['status'],
                'startDate': response['startDate'].isoformat(),
                'name': response['name']
            }

            if 'stopDate' in response:
                result['stopDate'] = response['stopDate'].isoformat()
                result['duration'] = (response['stopDate'] - response['startDate']).total_seconds()

            if response['status'] == 'SUCCEEDED' and 'output' in response:
                result['output'] = json.loads(response['output'])

            if response['status'] == 'FAILED' and 'error' in response:
                result['error'] = response.get('error')
                result['cause'] = response.get('cause')

            return result

        except Exception as e:
            logger.error(f"Failed to get execution status: {e}")
            return {
                'executionArn': execution_arn,
                'status': 'UNKNOWN',
                'error': str(e)
            }

    async def get_execution_history(self, execution_arn: str) -> List[Dict[str, Any]]:
        """
        Get detailed execution history showing all agent interactions.

        Args:
            execution_arn: ARN of the execution

        Returns:
            List of execution events
        """
        try:
            response = self.stepfunctions_client.get_execution_history(
                executionArn=execution_arn,
                maxResults=100,
                reverseOrder=False
            )

            events = []
            for event in response.get('events', []):
                events.append({
                    'timestamp': event['timestamp'].isoformat(),
                    'type': event['type'],
                    'id': event['id'],
                    'details': event.get('stateEnteredEventDetails') or
                              event.get('stateExitedEventDetails') or
                              event.get('taskScheduledEventDetails') or
                              event.get('taskSucceededEventDetails') or
                              event.get('taskFailedEventDetails') or
                              {}
                })

            return events

        except Exception as e:
            logger.error(f"Failed to get execution history: {e}")
            return []


# Global orchestrator instance
stepfunctions_orchestrator = StepFunctionsOrchestrator()
