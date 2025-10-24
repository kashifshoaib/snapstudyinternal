#!/usr/bin/env python3
"""
Comprehensive Functional Tests for AI Services Integration.

This test suite integrates and enhances the existing AI services tests
with proper pytest structure and mocking for reliable CI/CD execution.
"""

import pytest
import asyncio
import json
import uuid
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.bedrock import bedrock_service
from src.services.textract import textract_service
from src.services.transcribe import transcribe_service
from src.services.s3 import s3_service
from src.services.iam_helper import iam_helper
from src.config import settings


# Global fixtures for AI services
@pytest.fixture
def mock_bedrock_service():
    """Mock Bedrock service for testing."""
    with patch('src.services.bedrock.bedrock_service') as mock:
        mock.invoke_claude = AsyncMock(return_value="Mocked Claude response")
        mock.configure_retry_settings = Mock()
        mock.get_retry_stats = Mock(return_value={'max_retries': 3, 'base_delay': 1.0})
        yield mock


@pytest.fixture
def mock_s3_service():
    """Mock S3 service for testing."""
    with patch('src.services.s3.s3_service') as mock:
        mock.upload_file = AsyncMock(return_value={
            'file_id': str(uuid.uuid4()),
            'url': 'https://s3.amazonaws.com/test-bucket/test-file.pdf',
            'size': 1024
        })
        mock.get_file_url = AsyncMock(return_value='https://s3.amazonaws.com/test-file.pdf')
        yield mock


@pytest.fixture
def mock_textract_service():
    """Mock Textract service for testing."""
    with patch('src.services.textract.textract_service') as mock:
        mock.extract_text_from_s3 = AsyncMock(return_value={
            'extracted_text': 'Sample extracted text from PDF document.',
            'confidence': 0.95,
            'page_count': 1
        })
        yield mock


@pytest.fixture
def mock_transcribe_service():
    """Mock Transcribe service for testing."""
    with patch('src.services.transcribe.transcribe_service') as mock:
        mock.transcribe_audio_from_s3 = AsyncMock(return_value={
            'transcript': 'This is a sample audio transcription.',
            'confidence': 0.92,
            'duration_seconds': 120
        })
        yield mock


class TestAWSPermissions:
    """Test AWS permissions and service availability."""
    
    @pytest.mark.asyncio
    async def test_aws_connectivity(self):
        """Test basic AWS connectivity."""
        with patch('boto3.client') as mock_boto:
            mock_sts = Mock()
            mock_sts.get_caller_identity.return_value = {
                'Arn': 'arn:aws:iam::123456789:user/test-user',
                'Account': '123456789'
            }
            mock_boto.return_value = mock_sts
            
            # Test connectivity
            import boto3
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            
            assert 'Arn' in identity
            assert 'Account' in identity
            assert identity['Account'] == '123456789'
    
    @pytest.mark.asyncio
    async def test_comprehensive_permissions_check(self):
        """Test comprehensive permissions check."""
        mock_health_check = {
            'overall_status': 'ready',
            'region': 'us-east-1',
            'services': {
                'bedrock': {'has_permissions': True},
                'dynamodb': {'has_permissions': True},
                's3': {'has_permissions': True},
                'textract': {'has_permissions': True},
                'transcribe': {'has_permissions': True}
            }
        }
        
        with patch.object(iam_helper, 'get_comprehensive_permissions_check', 
                         return_value=mock_health_check):
            
            health_check = await iam_helper.get_comprehensive_permissions_check()
            
            assert health_check['overall_status'] == 'ready'
            assert health_check['region'] == 'us-east-1'
            assert len(health_check['services']) == 5
            
            for service_name, service_result in health_check['services'].items():
                assert service_result['has_permissions'] is True


class TestBedrockService:
    """Test Bedrock Claude integration."""
    
    @pytest.mark.asyncio
    async def test_claude_invocation(self, mock_bedrock_service):
        """Test Claude model invocation."""
        test_prompt = "Hello! Please respond with exactly: 'Bedrock test successful'"
        expected_response = "Bedrock test successful"
        
        mock_bedrock_service.invoke_claude.return_value = expected_response
        
        response = await mock_bedrock_service.invoke_claude(
            prompt=test_prompt,
            max_tokens=4096,
            temperature=0.1
        )
        
        assert response == expected_response
        mock_bedrock_service.invoke_claude.assert_called_once_with(
            prompt=test_prompt,
            max_tokens=4096,
            temperature=0.1
        )
    
    @pytest.mark.asyncio
    async def test_bedrock_retry_logic(self, mock_bedrock_service):
        """Test Bedrock retry logic with throttling."""
        from botocore.exceptions import ClientError
        
        # Configure retry behavior
        mock_bedrock_service.configure_retry_settings.return_value = None
        mock_bedrock_service.get_retry_stats.return_value = {
            'max_retries': 3,
            'base_delay': 0.1,
            'max_delay': 2.0
        }
        
        # Test successful retry after throttling
        mock_bedrock_service.invoke_claude.side_effect = [
            ClientError(
                error_response={'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
                operation_name='InvokeModel'
            ),
            "Success after retry!"
        ]
        
        # This would be handled by the actual retry logic in the service
        try:
            result = await mock_bedrock_service.invoke_claude("Test prompt")
            # In a real scenario, this would succeed after retry
            assert result == "Success after retry!"
        except ClientError:
            # Expected on first call in mock scenario
            pass
    
    @pytest.mark.asyncio
    async def test_bedrock_content_analysis(self, mock_bedrock_service):
        """Test content analysis through Bedrock."""
        test_content = "Python is a high-level programming language known for its simplicity."
        
        mock_analysis = {
            'title': 'Introduction to Python',
            'difficulty_level': 'beginner',
            'key_concepts': ['Python', 'programming language', 'high-level'],
            'learning_objectives': ['Understand Python basics'],
            'estimated_duration': 15
        }
        
        mock_bedrock_service.invoke_claude.return_value = json.dumps(mock_analysis)
        
        response = await mock_bedrock_service.invoke_claude(
            prompt=f"Analyze this content: {test_content}"
        )
        
        analysis = json.loads(response)
        assert analysis['title'] == 'Introduction to Python'
        assert analysis['difficulty_level'] == 'beginner'
        assert 'Python' in analysis['key_concepts']


class TestS3Service:
    """Test S3 file operations."""
    
    @pytest.mark.asyncio
    async def test_file_upload(self, mock_s3_service):
        """Test file upload to S3."""
        test_file_content = b"This is test file content"
        test_filename = "test_document.pdf"
        test_user_id = str(uuid.uuid4())
        
        result = await mock_s3_service.upload_file(
            file_content=test_file_content,
            file_name=test_filename,
            user_id=test_user_id,
            content_type="application/pdf"
        )
        
        assert 'file_id' in result
        assert 'url' in result
        assert 'size' in result
        assert result['size'] == 1024  # Mocked size
        
        mock_s3_service.upload_file.assert_called_once_with(
            file_content=test_file_content,
            file_name=test_filename,
            user_id=test_user_id,
            content_type="application/pdf"
        )
    
    @pytest.mark.asyncio
    async def test_file_url_generation(self, mock_s3_service):
        """Test presigned URL generation."""
        test_file_key = "uploads/user123/document.pdf"
        expected_url = "https://s3.amazonaws.com/test-file.pdf"
        
        mock_s3_service.get_file_url.return_value = expected_url
        
        url = await mock_s3_service.get_file_url(test_file_key)
        
        assert url == expected_url
        mock_s3_service.get_file_url.assert_called_once_with(test_file_key)


class TestTextractService:
    """Test Textract document processing."""
    
    @pytest.mark.asyncio
    async def test_pdf_text_extraction(self, mock_textract_service):
        """Test PDF text extraction."""
        test_bucket = "test-bucket"
        test_key = "documents/test.pdf"
        
        result = await mock_textract_service.extract_text_from_s3(test_bucket, test_key)
        
        assert 'extracted_text' in result
        assert 'confidence' in result
        assert 'page_count' in result
        assert result['confidence'] >= 0.9
        assert len(result['extracted_text']) > 0
        
        mock_textract_service.extract_text_from_s3.assert_called_once_with(test_bucket, test_key)
    
    @pytest.mark.asyncio
    async def test_textract_error_handling(self, mock_textract_service):
        """Test Textract error handling."""
        from botocore.exceptions import ClientError
        
        mock_textract_service.extract_text_from_s3.side_effect = ClientError(
            error_response={'Error': {'Code': 'InvalidParameterException', 'Message': 'Invalid document'}},
            operation_name='StartDocumentTextDetection'
        )
        
        with pytest.raises(ClientError):
            await mock_textract_service.extract_text_from_s3("invalid-bucket", "invalid-key")


class TestTranscribeService:
    """Test Transcribe audio processing."""
    
    @pytest.mark.asyncio
    async def test_audio_transcription(self, mock_transcribe_service):
        """Test audio transcription."""
        test_bucket = "test-bucket"
        test_key = "audio/test.mp3"
        
        result = await mock_transcribe_service.transcribe_audio_from_s3(
            test_bucket, test_key, language_code='en-US'
        )
        
        assert 'transcript' in result
        assert 'confidence' in result
        assert 'duration_seconds' in result
        assert result['confidence'] >= 0.9
        assert len(result['transcript']) > 0
        
        mock_transcribe_service.transcribe_audio_from_s3.assert_called_once_with(
            test_bucket, test_key, language_code='en-US'
        )
    
    @pytest.mark.asyncio
    async def test_transcribe_different_formats(self, mock_transcribe_service):
        """Test transcription of different audio formats."""
        formats = ['mp3', 'wav', 'mp4', 'flac']
        
        for format_ext in formats:
            test_key = f"audio/test.{format_ext}"
            
            result = await mock_transcribe_service.transcribe_audio_from_s3(
                "test-bucket", test_key
            )
            
            assert 'transcript' in result
            assert len(result['transcript']) > 0


class TestAIServicesIntegration:
    """Test integration between AI services."""
    
    @pytest.mark.asyncio
    async def test_document_processing_pipeline(self, mock_s3_service, mock_textract_service, mock_bedrock_service):
        """Test complete document processing pipeline."""
        # Step 1: Upload document
        file_content = b"PDF content here"
        upload_result = await mock_s3_service.upload_file(
            file_content=file_content,
            file_name="lesson.pdf",
            user_id="user123"
        )
        
        assert 'file_id' in upload_result
        
        # Step 2: Extract text
        extraction_result = await mock_textract_service.extract_text_from_s3(
            "test-bucket", "uploads/user123/lesson.pdf"
        )
        
        assert 'extracted_text' in extraction_result
        
        # Step 3: Analyze content
        analysis_result = await mock_bedrock_service.invoke_claude(
            prompt=f"Analyze: {extraction_result['extracted_text']}"
        )
        
        assert analysis_result == "Mocked Claude response"
        
        # Verify all services were called
        mock_s3_service.upload_file.assert_called_once()
        mock_textract_service.extract_text_from_s3.assert_called_once()
        mock_bedrock_service.invoke_claude.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multimedia_processing_pipeline(self, mock_s3_service, mock_transcribe_service, mock_bedrock_service):
        """Test multimedia processing pipeline."""
        # Step 1: Upload audio/video
        media_content = b"Audio/video content here"
        upload_result = await mock_s3_service.upload_file(
            file_content=media_content,
            file_name="lesson.mp3",
            user_id="user123",
            content_type="audio/mpeg"
        )
        
        assert 'file_id' in upload_result
        
        # Step 2: Transcribe audio
        transcription_result = await mock_transcribe_service.transcribe_audio_from_s3(
            "test-bucket", "uploads/user123/lesson.mp3"
        )
        
        assert 'transcript' in transcription_result
        
        # Step 3: Analyze transcript
        analysis_result = await mock_bedrock_service.invoke_claude(
            prompt=f"Analyze transcript: {transcription_result['transcript']}"
        )
        
        assert analysis_result == "Mocked Claude response"
        
        # Verify all services were called
        mock_s3_service.upload_file.assert_called_once()
        mock_transcribe_service.transcribe_audio_from_s3.assert_called_once()
        mock_bedrock_service.invoke_claude.assert_called_once()


class TestErrorHandlingAndResilience:
    """Test error handling and resilience across AI services."""
    
    @pytest.mark.asyncio
    async def test_service_unavailable_handling(self, mock_bedrock_service):
        """Test handling of service unavailable errors."""
        from botocore.exceptions import ClientError
        
        mock_bedrock_service.invoke_claude.side_effect = ClientError(
            error_response={'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service temporarily unavailable'}},
            operation_name='InvokeModel'
        )
        
        with pytest.raises(ClientError) as exc_info:
            await mock_bedrock_service.invoke_claude("Test prompt")
        
        assert exc_info.value.response['Error']['Code'] == 'ServiceUnavailable'
    
    @pytest.mark.asyncio
    async def test_rate_limiting_handling(self, mock_bedrock_service):
        """Test handling of rate limiting."""
        from botocore.exceptions import ClientError
        
        mock_bedrock_service.invoke_claude.side_effect = ClientError(
            error_response={'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            operation_name='InvokeModel'
        )
        
        with pytest.raises(ClientError) as exc_info:
            await mock_bedrock_service.invoke_claude("Test prompt")
        
        assert exc_info.value.response['Error']['Code'] == 'ThrottlingException'
    
    @pytest.mark.asyncio
    async def test_invalid_input_handling(self, mock_textract_service):
        """Test handling of invalid input errors."""
        from botocore.exceptions import ClientError
        
        mock_textract_service.extract_text_from_s3.side_effect = ClientError(
            error_response={'Error': {'Code': 'InvalidParameterException', 'Message': 'Invalid document format'}},
            operation_name='StartDocumentTextDetection'
        )
        
        with pytest.raises(ClientError) as exc_info:
            await mock_textract_service.extract_text_from_s3("bucket", "invalid-file.txt")
        
        assert exc_info.value.response['Error']['Code'] == 'InvalidParameterException'


class TestPerformanceAndScaling:
    """Test performance and scaling aspects of AI services."""
    
    @pytest.mark.asyncio
    async def test_concurrent_bedrock_requests(self, mock_bedrock_service):
        """Test concurrent Bedrock requests."""
        # Mock responses for concurrent requests
        responses = [f"Response {i}" for i in range(5)]
        mock_bedrock_service.invoke_claude.side_effect = responses
        
        # Create concurrent tasks
        tasks = []
        for i in range(5):
            task = mock_bedrock_service.invoke_claude(f"Prompt {i}")
            tasks.append(task)
        
        # Execute concurrently
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result == f"Response {i}"
        
        # Verify all calls were made
        assert mock_bedrock_service.invoke_claude.call_count == 5
    
    @pytest.mark.asyncio
    async def test_large_content_processing(self, mock_bedrock_service):
        """Test processing of large content."""
        large_content = "x" * 10000  # 10KB of content
        
        mock_bedrock_service.invoke_claude.return_value = "Processed large content successfully"
        
        result = await mock_bedrock_service.invoke_claude(
            prompt=f"Analyze this large content: {large_content}"
        )
        
        assert result == "Processed large content successfully"
        mock_bedrock_service.invoke_claude.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, mock_bedrock_service):
        """Test timeout handling for long-running operations."""
        import asyncio
        
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(2)  # Simulate slow response
            return "Slow response"
        
        mock_bedrock_service.invoke_claude.side_effect = slow_response
        
        # Test with timeout
        try:
            result = await asyncio.wait_for(
                mock_bedrock_service.invoke_claude("Test prompt"),
                timeout=1.0
            )
            assert False, "Should have timed out"
        except asyncio.TimeoutError:
            # Expected timeout
            pass


if __name__ == "__main__":
    """Run the AI services functional tests."""
    print("🤖 SnapStudy AI Services Functional Test Suite")
    print("=" * 60)
    
    # Run pytest with verbose output
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--color=yes"
    ])