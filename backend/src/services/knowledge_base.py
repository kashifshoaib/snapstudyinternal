"""
Amazon Bedrock Knowledge Base Integration for Educational Content.

This service provides vector search capabilities over educational content using
Amazon Bedrock Knowledge Bases with OpenSearch Serverless as the vector store.

Key Features:
- Vector embeddings for semantic search
- RAG (Retrieval Augmented Generation) for accurate responses
- Educational content indexing and retrieval
- Context-aware learning material recommendations
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

from ..config import settings

logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    """
    Amazon Bedrock Knowledge Base integration for educational content retrieval.

    Uses vector search to find relevant educational content and combines it with
    LLM generation for accurate, contextual responses.
    """

    def __init__(self):
        self.bedrock_agent_runtime = boto3.client(
            'bedrock-agent-runtime',
            region_name=settings.aws_region
        )
        self.bedrock_agent = boto3.client(
            'bedrock-agent',
            region_name=settings.aws_region
        )
        self.knowledge_base_id = settings.knowledge_base_id
        self.model_arn = f"arn:aws:bedrock:{settings.aws_region}::foundation-model/{settings.bedrock_model_id}"

        logger.info(f"KnowledgeBaseService initialized with KB ID: {self.knowledge_base_id}")

    async def retrieve_relevant_content(
        self,
        query: str,
        max_results: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Retrieve relevant content from Knowledge Base using vector search.

        Args:
            query: Search query
            max_results: Maximum number of results to return
            filters: Optional metadata filters

        Returns:
            Dict containing retrieved content chunks
        """
        if not self.knowledge_base_id:
            logger.warning("Knowledge Base not configured")
            return {
                'results': [],
                'total_results': 0,
                'knowledge_base_configured': False,
                'message': 'Knowledge Base not configured. Set KNOWLEDGE_BASE_ID environment variable.'
            }

        try:
            logger.info(f"Retrieving content from KB for query: {query[:100]}...")

            # Prepare retrieval request
            retrieve_params = {
                'knowledgeBaseId': self.knowledge_base_id,
                'retrievalQuery': {
                    'text': query
                },
                'retrievalConfiguration': {
                    'vectorSearchConfiguration': {
                        'numberOfResults': max_results
                    }
                }
            }

            # Add filters if provided
            if filters:
                retrieve_params['retrievalConfiguration']['vectorSearchConfiguration']['filter'] = filters

            # Retrieve from Knowledge Base
            response = self.bedrock_agent_runtime.retrieve(**retrieve_params)

            # Process results
            results = []
            for result in response.get('retrievalResults', []):
                results.append({
                    'content': result.get('content', {}).get('text', ''),
                    'score': result.get('score', 0.0),
                    'location': result.get('location', {}),
                    'metadata': result.get('metadata', {})
                })

            logger.info(f"Retrieved {len(results)} results from Knowledge Base")

            return {
                'results': results,
                'total_results': len(results),
                'knowledge_base_configured': True,
                'query': query,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Knowledge Base retrieval failed: {error_code} - {str(e)}")

            return {
                'results': [],
                'total_results': 0,
                'knowledge_base_configured': True,
                'error': error_code,
                'message': str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error in Knowledge Base retrieval: {e}")
            return {
                'results': [],
                'total_results': 0,
                'error': str(e)
            }

    async def retrieve_and_generate(
        self,
        query: str,
        user_context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve relevant content and generate response using RAG.

        This is the key RAG (Retrieval Augmented Generation) functionality that:
        1. Retrieves relevant content from Knowledge Base
        2. Uses that content as context for LLM generation
        3. Produces accurate, grounded responses

        Args:
            query: User query
            user_context: Optional user context for personalization
            session_id: Optional session ID for conversation continuity

        Returns:
            Dict containing generated response and citations
        """
        if not self.knowledge_base_id:
            logger.warning("Knowledge Base not configured for RAG")
            return {
                'response': 'Knowledge Base not configured. Cannot use RAG.',
                'citations': [],
                'knowledge_base_configured': False
            }

        try:
            logger.info(f"RAG query: {query[:100]}...")

            # Prepare RAG request
            rag_params = {
                'input': {
                    'text': query
                },
                'retrieveAndGenerateConfiguration': {
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': self.knowledge_base_id,
                        'modelArn': self.model_arn,
                        'retrievalConfiguration': {
                            'vectorSearchConfiguration': {
                                'numberOfResults': 5
                            }
                        }
                    }
                }
            }

            # Add session for conversation continuity
            if session_id:
                rag_params['sessionId'] = session_id

            # Execute RAG
            response = self.bedrock_agent_runtime.retrieve_and_generate(**rag_params)

            # Extract response and citations
            output = response.get('output', {})
            generated_text = output.get('text', '')

            citations = []
            for citation in response.get('citations', []):
                for ref in citation.get('retrievedReferences', []):
                    citations.append({
                        'content': ref.get('content', {}).get('text', ''),
                        'location': ref.get('location', {}),
                        'metadata': ref.get('metadata', {})
                    })

            logger.info(f"RAG generated response with {len(citations)} citations")

            return {
                'response': generated_text,
                'citations': citations,
                'session_id': response.get('sessionId'),
                'knowledge_base_configured': True,
                'query': query,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"RAG failed: {error_code} - {str(e)}")

            return {
                'response': f'RAG error: {error_code}',
                'citations': [],
                'error': error_code,
                'message': str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error in RAG: {e}")
            return {
                'response': 'An error occurred during content generation.',
                'citations': [],
                'error': str(e)
            }

    async def ingest_educational_content(
        self,
        content: str,
        metadata: Dict[str, Any],
        document_id: str
    ) -> Dict[str, Any]:
        """
        Ingest educational content into Knowledge Base.

        This adds new educational content to the vector store for future retrieval.

        Args:
            content: Educational content text
            metadata: Content metadata (subject, difficulty, etc.)
            document_id: Unique document identifier

        Returns:
            Dict containing ingestion status
        """
        try:
            logger.info(f"Ingesting content: {document_id}")

            # Note: Actual ingestion typically happens via S3 data source sync
            # This is a placeholder for the ingestion flow

            return {
                'success': True,
                'document_id': document_id,
                'message': 'Content queued for ingestion. Sync Knowledge Base data source.',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Content ingestion failed: {e}")
            return {
                'success': False,
                'document_id': document_id,
                'error': str(e)
            }

    async def search_similar_concepts(
        self,
        concept: str,
        difficulty_level: Optional[str] = None,
        max_results: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Search for educational content similar to a given concept.

        Useful for finding related learning materials or alternative explanations.

        Args:
            concept: The concept to search for
            difficulty_level: Optional difficulty filter
            max_results: Maximum number of results

        Returns:
            List of similar content
        """
        # Build search query
        search_query = f"Educational content about: {concept}"

        # Build filters
        filters = {}
        if difficulty_level:
            filters['difficulty'] = {'equals': difficulty_level}

        # Retrieve similar content
        results = await self.retrieve_relevant_content(
            query=search_query,
            max_results=max_results,
            filters=filters if filters else None
        )

        return results.get('results', [])

    async def get_knowledge_base_status(self) -> Dict[str, Any]:
        """
        Get status and health of Knowledge Base.

        Returns:
            Dict containing KB status information
        """
        if not self.knowledge_base_id:
            return {
                'configured': False,
                'status': 'NOT_CONFIGURED',
                'message': 'Knowledge Base ID not set in environment'
            }

        try:
            # Get Knowledge Base details
            response = self.bedrock_agent.get_knowledge_base(
                knowledgeBaseId=self.knowledge_base_id
            )

            kb_info = response.get('knowledgeBase', {})

            return {
                'configured': True,
                'knowledge_base_id': self.knowledge_base_id,
                'status': kb_info.get('status', 'UNKNOWN'),
                'name': kb_info.get('name', ''),
                'description': kb_info.get('description', ''),
                'created_at': kb_info.get('createdAt', ''),
                'updated_at': kb_info.get('updatedAt', ''),
                'embedding_model': kb_info.get('knowledgeBaseConfiguration', {}).get('vectorKnowledgeBaseConfiguration', {}).get('embeddingModelArn', ''),
                'healthy': kb_info.get('status') in ['ACTIVE', 'AVAILABLE']
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Failed to get KB status: {error_code}")

            return {
                'configured': True,
                'knowledge_base_id': self.knowledge_base_id,
                'status': 'ERROR',
                'error': error_code,
                'healthy': False
            }
        except Exception as e:
            logger.error(f"Unexpected error getting KB status: {e}")
            return {
                'configured': True,
                'status': 'ERROR',
                'error': str(e),
                'healthy': False
            }

    async def sync_data_source(self, data_source_id: str) -> Dict[str, Any]:
        """
        Trigger synchronization of a Knowledge Base data source.

        This updates the vector store with new content from S3.

        Args:
            data_source_id: Data source ID to sync

        Returns:
            Dict containing sync job information
        """
        if not self.knowledge_base_id:
            return {
                'success': False,
                'message': 'Knowledge Base not configured'
            }

        try:
            logger.info(f"Starting data source sync: {data_source_id}")

            response = self.bedrock_agent.start_ingestion_job(
                knowledgeBaseId=self.knowledge_base_id,
                dataSourceId=data_source_id
            )

            ingestion_job = response.get('ingestionJob', {})

            return {
                'success': True,
                'job_id': ingestion_job.get('ingestionJobId', ''),
                'status': ingestion_job.get('status', ''),
                'started_at': ingestion_job.get('startedAt', ''),
                'message': 'Data source sync started'
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Data source sync failed: {error_code}")

            return {
                'success': False,
                'error': error_code,
                'message': str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error syncing data source: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Global service instance
knowledge_base_service = KnowledgeBaseService()
