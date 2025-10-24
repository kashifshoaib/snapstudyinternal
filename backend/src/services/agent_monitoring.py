"""
AWS CloudWatch Monitoring for Bedrock Agents and Multi-Agent Orchestration.

This service provides comprehensive monitoring and observability for:
- Bedrock Agent invocations
- Knowledge Base retrievals
- Guardrails validations
- Step Functions workflows
- Agent decision-making patterns
- Performance metrics
"""

import boto3
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from enum import Enum

from ..config import settings

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of agent metrics."""
    AGENT_INVOCATION = "AgentInvocation"
    AGENT_SUCCESS = "AgentSuccess"
    AGENT_ERROR = "AgentError"
    AGENT_LATENCY = "AgentLatency"
    KB_RETRIEVAL = "KnowledgeBaseRetrieval"
    KB_RETRIEVAL_LATENCY = "KBRetrievalLatency"
    GUARDRAILS_CHECK = "GuardrailsCheck"
    GUARDRAILS_BLOCKED = "GuardrailsBlocked"
    WORKFLOW_EXECUTION = "WorkflowExecution"
    WORKFLOW_SUCCESS = "WorkflowSuccess"
    WORKFLOW_FAILURE = "WorkflowFailure"
    DECISION_QUALITY = "DecisionQuality"
    ADAPTATION_ACTION = "AdaptationAction"


class AgentMonitoringService:
    """
    Comprehensive monitoring service for AI agents and orchestration.

    Tracks:
    - Agent performance and reliability
    - Knowledge Base effectiveness
    - Guardrails intervention rates
    - Workflow success rates
    - Learning outcome correlations
    """

    def __init__(self):
        self.cloudwatch = boto3.client('cloudwatch', region_name=settings.aws_region)
        self.logs = boto3.client('logs', region_name=settings.aws_region)

        # Metric namespace
        self.namespace = "SnapStudy/Agents"

        # Log groups
        self.agent_log_group = "/aws/bedrock/agents/snapstudy"
        self.workflow_log_group = "/aws/stepfunctions/snapstudy"

        logger.info("AgentMonitoringService initialized")

    async def log_agent_invocation(
        self,
        agent_id: str,
        agent_name: str,
        function_name: str,
        success: bool,
        latency_ms: float,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log detailed agent invocation metrics.

        Args:
            agent_id: Bedrock Agent ID
            agent_name: Human-readable agent name
            function_name: Function/action invoked
            success: Whether invocation succeeded
            latency_ms: Response latency in milliseconds
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            metadata: Additional metadata
        """
        try:
            dimensions = [
                {'Name': 'AgentId', 'Value': agent_id},
                {'Name': 'AgentName', 'Value': agent_name},
                {'Name': 'Function', 'Value': function_name}
            ]

            metrics = [
                {
                    'MetricName': MetricType.AGENT_INVOCATION.value,
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': datetime.now(timezone.utc),
                    'Dimensions': dimensions
                },
                {
                    'MetricName': MetricType.AGENT_LATENCY.value,
                    'Value': latency_ms,
                    'Unit': 'Milliseconds',
                    'Timestamp': datetime.now(timezone.utc),
                    'Dimensions': dimensions
                }
            ]

            if success:
                metrics.append({
                    'MetricName': MetricType.AGENT_SUCCESS.value,
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': datetime.now(timezone.utc),
                    'Dimensions': dimensions
                })
            else:
                metrics.append({
                    'MetricName': MetricType.AGENT_ERROR.value,
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': datetime.now(timezone.utc),
                    'Dimensions': dimensions
                })

            # Add token metrics if available
            if input_tokens is not None:
                metrics.append({
                    'MetricName': 'InputTokens',
                    'Value': input_tokens,
                    'Unit': 'Count',
                    'Timestamp': datetime.now(timezone.utc),
                    'Dimensions': dimensions
                })

            if output_tokens is not None:
                metrics.append({
                    'MetricName': 'OutputTokens',
                    'Value': output_tokens,
                    'Unit': 'Count',
                    'Timestamp': datetime.now(timezone.utc),
                    'Dimensions': dimensions
                })

            # Send metrics to CloudWatch
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=metrics
            )

            # Log details
            logger.info(f"Agent invocation logged: {agent_name}.{function_name} - "
                       f"Success: {success}, Latency: {latency_ms}ms")

        except Exception as e:
            logger.error(f"Failed to log agent invocation: {e}")

    async def log_knowledge_base_retrieval(
        self,
        knowledge_base_id: str,
        query: str,
        num_results: int,
        latency_ms: float,
        success: bool,
        relevance_scores: Optional[List[float]] = None
    ) -> None:
        """
        Log Knowledge Base retrieval metrics.

        Args:
            knowledge_base_id: Knowledge Base ID
            query: Search query
            num_results: Number of results retrieved
            latency_ms: Retrieval latency
            success: Whether retrieval succeeded
            relevance_scores: Relevance scores of results
        """
        try:
            dimensions = [
                {'Name': 'KnowledgeBaseId', 'Value': knowledge_base_id},
                {'Name': 'Operation', 'Value': 'Retrieve'}
            ]

            metrics = [
                {
                    'MetricName': MetricType.KB_RETRIEVAL.value,
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': datetime.now(timezone.utc),
                    'Dimensions': dimensions
                },
                {
                    'MetricName': MetricType.KB_RETRIEVAL_LATENCY.value,
                    'Value': latency_ms,
                    'Unit': 'Milliseconds',
                    'Timestamp': datetime.now(timezone.utc),
                    'Dimensions': dimensions
                },
                {
                    'MetricName': 'ResultsRetrieved',
                    'Value': num_results,
                    'Unit': 'Count',
                    'Timestamp': datetime.now(timezone.utc),
                    'Dimensions': dimensions
                }
            ]

            # Add average relevance score
            if relevance_scores:
                avg_relevance = sum(relevance_scores) / len(relevance_scores)
                metrics.append({
                    'MetricName': 'AverageRelevanceScore',
                    'Value': avg_relevance,
                    'Unit': 'None',
                    'Timestamp': datetime.now(timezone.utc),
                    'Dimensions': dimensions
                })

            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=metrics
            )

            logger.info(f"KB retrieval logged: {num_results} results, {latency_ms}ms")

        except Exception as e:
            logger.error(f"Failed to log KB retrieval: {e}")

    async def log_guardrails_check(
        self,
        guardrail_id: str,
        content_type: str,
        action: str,
        latency_ms: float,
        intervention_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log Bedrock Guardrails check metrics.

        Args:
            guardrail_id: Guardrail ID
            content_type: Type of content checked
            action: Guardrails action (NONE, BLOCKED, INTERVENED)
            latency_ms: Check latency
            intervention_details: Details of intervention if applicable
        """
        try:
            dimensions = [
                {'Name': 'GuardrailId', 'Value': guardrail_id},
                {'Name': 'ContentType', 'Value': content_type},
                {'Name': 'Action', 'Value': action}
            ]

            metrics = [
                {
                    'MetricName': MetricType.GUARDRAILS_CHECK.value,
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': datetime.now(timezone.utc),
                    'Dimensions': dimensions
                }
            ]

            if action == 'BLOCKED':
                metrics.append({
                    'MetricName': MetricType.GUARDRAILS_BLOCKED.value,
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': datetime.now(timezone.utc),
                    'Dimensions': dimensions
                })

            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=metrics
            )

            logger.info(f"Guardrails check logged: {action} for {content_type}")

        except Exception as e:
            logger.error(f"Failed to log guardrails check: {e}")

    async def log_workflow_execution(
        self,
        workflow_type: str,
        execution_id: str,
        status: str,
        duration_seconds: Optional[float] = None,
        num_steps: Optional[int] = None,
        agent_invocations: Optional[int] = None
    ) -> None:
        """
        Log Step Functions workflow execution metrics.

        Args:
            workflow_type: Type of workflow
            execution_id: Execution ID
            status: Execution status
            duration_seconds: Execution duration
            num_steps: Number of steps executed
            agent_invocations: Number of agent invocations
        """
        try:
            dimensions = [
                {'Name': 'WorkflowType', 'Value': workflow_type},
                {'Name': 'Status', 'Value': status}
            ]

            metrics = [
                {
                    'MetricName': MetricType.WORKFLOW_EXECUTION.value,
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': datetime.now(timezone.utc),
                    'Dimensions': dimensions
                }
            ]

            if status == 'SUCCEEDED':
                metrics.append({
                    'MetricName': MetricType.WORKFLOW_SUCCESS.value,
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': datetime.now(timezone.utc),
                    'Dimensions': dimensions
                })
            elif status in ['FAILED', 'TIMED_OUT', 'ABORTED']:
                metrics.append({
                    'MetricName': MetricType.WORKFLOW_FAILURE.value,
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': datetime.now(timezone.utc),
                    'Dimensions': dimensions
                })

            if duration_seconds is not None:
                metrics.append({
                    'MetricName': 'WorkflowDuration',
                    'Value': duration_seconds,
                    'Unit': 'Seconds',
                    'Timestamp': datetime.now(timezone.utc),
                    'Dimensions': dimensions
                })

            if num_steps is not None:
                metrics.append({
                    'MetricName': 'WorkflowSteps',
                    'Value': num_steps,
                    'Unit': 'Count',
                    'Timestamp': datetime.now(timezone.utc),
                    'Dimensions': dimensions
                })

            if agent_invocations is not None:
                metrics.append({
                    'MetricName': 'AgentInvocationsPerWorkflow',
                    'Value': agent_invocations,
                    'Unit': 'Count',
                    'Timestamp': datetime.now(timezone.utc),
                    'Dimensions': dimensions
                })

            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=metrics
            )

            logger.info(f"Workflow execution logged: {workflow_type} - {status}")

        except Exception as e:
            logger.error(f"Failed to log workflow execution: {e}")

    async def log_adaptation_decision(
        self,
        decision_type: str,
        confidence: float,
        user_performance: float,
        decision_metadata: Dict[str, Any]
    ) -> None:
        """
        Log autonomous adaptation decision metrics.

        Args:
            decision_type: Type of adaptation decision
            confidence: Agent confidence in decision
            user_performance: User's performance score
            decision_metadata: Additional decision metadata
        """
        try:
            dimensions = [
                {'Name': 'DecisionType', 'Value': decision_type}
            ]

            metrics = [
                {
                    'MetricName': MetricType.ADAPTATION_ACTION.value,
                    'Value': 1,
                    'Unit': 'Count',
                    'Timestamp': datetime.now(timezone.utc),
                    'Dimensions': dimensions
                },
                {
                    'MetricName': 'DecisionConfidence',
                    'Value': confidence,
                    'Unit': 'None',
                    'Timestamp': datetime.now(timezone.utc),
                    'Dimensions': dimensions
                },
                {
                    'MetricName': 'UserPerformance',
                    'Value': user_performance,
                    'Unit': 'None',
                    'Timestamp': datetime.now(timezone.utc),
                    'Dimensions': dimensions
                }
            ]

            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=metrics
            )

            logger.info(f"Adaptation decision logged: {decision_type}, confidence: {confidence}")

        except Exception as e:
            logger.error(f"Failed to log adaptation decision: {e}")

    async def get_agent_performance_metrics(
        self,
        agent_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Get performance metrics for a specific agent.

        Args:
            agent_id: Agent ID
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Dict containing performance metrics
        """
        try:
            metrics = {}

            # Get invocation count
            invocations = self.cloudwatch.get_metric_statistics(
                Namespace=self.namespace,
                MetricName=MetricType.AGENT_INVOCATION.value,
                Dimensions=[{'Name': 'AgentId', 'Value': agent_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Sum']
            )

            # Get success rate
            successes = self.cloudwatch.get_metric_statistics(
                Namespace=self.namespace,
                MetricName=MetricType.AGENT_SUCCESS.value,
                Dimensions=[{'Name': 'AgentId', 'Value': agent_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Sum']
            )

            # Get average latency
            latency = self.cloudwatch.get_metric_statistics(
                Namespace=self.namespace,
                MetricName=MetricType.AGENT_LATENCY.value,
                Dimensions=[{'Name': 'AgentId', 'Value': agent_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average', 'Maximum']
            )

            total_invocations = sum(d['Sum'] for d in invocations.get('Datapoints', []))
            total_successes = sum(d['Sum'] for d in successes.get('Datapoints', []))

            metrics['agent_id'] = agent_id
            metrics['total_invocations'] = total_invocations
            metrics['successful_invocations'] = total_successes
            metrics['success_rate'] = (total_successes / total_invocations * 100) if total_invocations > 0 else 0
            metrics['average_latency_ms'] = sum(d['Average'] for d in latency.get('Datapoints', [])) / len(latency.get('Datapoints', [1]))
            metrics['max_latency_ms'] = max([d['Maximum'] for d in latency.get('Datapoints', [])], default=0)

            return metrics

        except Exception as e:
            logger.error(f"Failed to get agent performance metrics: {e}")
            return {}

    async def create_agent_dashboard(self) -> str:
        """
        Create CloudWatch dashboard for agent monitoring.

        Returns:
            Dashboard name
        """
        dashboard_name = "SnapStudy-AgentMonitoring"

        dashboard_body = {
            "widgets": [
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            [self.namespace, MetricType.AGENT_INVOCATION.value],
                            [".", MetricType.AGENT_SUCCESS.value],
                            [".", MetricType.AGENT_ERROR.value]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": settings.aws_region,
                        "title": "Agent Invocations"
                    }
                },
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            [self.namespace, MetricType.AGENT_LATENCY.value, {"stat": "Average"}]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": settings.aws_region,
                        "title": "Agent Response Latency"
                    }
                },
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            [self.namespace, MetricType.KB_RETRIEVAL.value],
                            [".", "AverageRelevanceScore"]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": settings.aws_region,
                        "title": "Knowledge Base Performance"
                    }
                },
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            [self.namespace, MetricType.GUARDRAILS_CHECK.value],
                            [".", MetricType.GUARDRAILS_BLOCKED.value]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": settings.aws_region,
                        "title": "Guardrails Activity"
                    }
                },
                {
                    "type": "metric",
                    "properties": {
                        "metrics": [
                            [self.namespace, MetricType.WORKFLOW_EXECUTION.value],
                            [".", MetricType.WORKFLOW_SUCCESS.value],
                            [".", MetricType.WORKFLOW_FAILURE.value]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": settings.aws_region,
                        "title": "Multi-Agent Workflow Executions"
                    }
                }
            ]
        }

        try:
            self.cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )

            logger.info(f"Created CloudWatch dashboard: {dashboard_name}")
            return dashboard_name

        except Exception as e:
            logger.error(f"Failed to create dashboard: {e}")
            return ""


# Global monitoring service instance
agent_monitoring_service = AgentMonitoringService()
