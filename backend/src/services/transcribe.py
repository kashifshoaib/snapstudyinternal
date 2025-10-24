"""AWS Transcribe service for audio/video transcription."""

import boto3
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError
import logging
import time
import uuid

from ..config import settings

logger = logging.getLogger(__name__)


class TranscribeService:
    """Service for AWS Transcribe operations."""
    
    def __init__(self):
        self.transcribe_client = boto3.client('transcribe', region_name=settings.aws_region)
        self.s3_client = boto3.client('s3', region_name=settings.aws_region)
    
    async def transcribe_audio_from_s3(
        self, 
        bucket_name: str, 
        object_key: str,
        language_code: str = 'en-US'
    ) -> Dict[str, Any]:
        """Transcribe audio/video file from S3."""
        try:
            # Generate unique job name
            job_name = f"snapstudy-transcribe-{uuid.uuid4().hex[:8]}"
            
            # Get file extension to determine media format
            file_extension = object_key.split('.')[-1].lower()
            media_format = self._get_media_format(file_extension)
            
            # Start transcription job
            response = self.transcribe_client.start_transcription_job(
                TranscriptionJobName=job_name,
                LanguageCode=language_code,
                MediaFormat=media_format,
                Media={
                    'MediaFileUri': f's3://{bucket_name}/{object_key}'
                },
                OutputBucketName=bucket_name,
                OutputKey=f'transcriptions/{job_name}.json',
                Settings={
                    'ShowSpeakerLabels': True,
                    'MaxSpeakerLabels': 5,
                    'ShowAlternatives': True,
                    'MaxAlternatives': 3
                }
            )
            
            job_name = response['TranscriptionJob']['TranscriptionJobName']
            logger.info(f"Started transcription job: {job_name}")
            
            # Poll for job completion
            max_attempts = 120  # 10 minutes max
            attempt = 0
            
            while attempt < max_attempts:
                job_status = self.transcribe_client.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                
                status = job_status['TranscriptionJob']['TranscriptionJobStatus']
                
                if status == 'COMPLETED':
                    break
                elif status == 'FAILED':
                    failure_reason = job_status['TranscriptionJob'].get('FailureReason', 'Unknown error')
                    raise ValueError(f"Transcription job failed: {failure_reason}")
                
                # Wait before next check
                time.sleep(5)
                attempt += 1
            
            if attempt >= max_attempts:
                raise ValueError("Transcription job timed out")
            
            # Get transcription results
            transcript_uri = job_status['TranscriptionJob']['Transcript']['TranscriptFileUri']
            transcript_data = await self._download_transcript(transcript_uri)
            
            # Parse transcript
            parsed_transcript = self._parse_transcript(transcript_data)
            
            return {
                'transcript': parsed_transcript['transcript'],
                'confidence': parsed_transcript['confidence'],
                'speaker_labels': parsed_transcript.get('speaker_labels', []),
                'word_count': len(parsed_transcript['transcript'].split()),
                'duration_seconds': parsed_transcript.get('duration', 0),
                'job_name': job_name,
                'language_code': language_code
            }
            
        except ClientError as e:
            logger.error(f"Transcribe API error: {e}")
            raise ValueError(f"Transcribe API error: {e.response['Error']['Message']}")
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            raise ValueError(f"Error transcribing audio: {str(e)}")
    
    async def transcribe_with_custom_vocabulary(
        self,
        bucket_name: str,
        object_key: str,
        vocabulary_name: str,
        language_code: str = 'en-US'
    ) -> Dict[str, Any]:
        """Transcribe with custom vocabulary for technical terms."""
        try:
            job_name = f"snapstudy-custom-{uuid.uuid4().hex[:8]}"
            file_extension = object_key.split('.')[-1].lower()
            media_format = self._get_media_format(file_extension)
            
            response = self.transcribe_client.start_transcription_job(
                TranscriptionJobName=job_name,
                LanguageCode=language_code,
                MediaFormat=media_format,
                Media={
                    'MediaFileUri': f's3://{bucket_name}/{object_key}'
                },
                OutputBucketName=bucket_name,
                OutputKey=f'transcriptions/{job_name}.json',
                Settings={
                    'VocabularyName': vocabulary_name,
                    'ShowSpeakerLabels': True,
                    'MaxSpeakerLabels': 5,
                    'ShowAlternatives': True,
                    'MaxAlternatives': 3
                }
            )
            
            # Similar polling logic as above
            return await self._poll_and_get_results(job_name, language_code)
            
        except ClientError as e:
            logger.error(f"Custom vocabulary transcription error: {e}")
            raise ValueError(f"Transcribe API error: {e.response['Error']['Message']}")
    
    async def create_custom_vocabulary(
        self,
        vocabulary_name: str,
        language_code: str,
        phrases: List[str]
    ) -> Dict[str, Any]:
        """Create custom vocabulary for domain-specific terms."""
        try:
            # Create vocabulary
            response = self.transcribe_client.create_vocabulary(
                VocabularyName=vocabulary_name,
                LanguageCode=language_code,
                Phrases=phrases
            )
            
            # Wait for vocabulary to be ready
            max_attempts = 60
            attempt = 0
            
            while attempt < max_attempts:
                vocab_status = self.transcribe_client.get_vocabulary(
                    VocabularyName=vocabulary_name
                )
                
                status = vocab_status['VocabularyState']
                
                if status == 'READY':
                    break
                elif status == 'FAILED':
                    failure_reason = vocab_status.get('FailureReason', 'Unknown error')
                    raise ValueError(f"Vocabulary creation failed: {failure_reason}")
                
                time.sleep(5)
                attempt += 1
            
            if attempt >= max_attempts:
                raise ValueError("Vocabulary creation timed out")
            
            return {
                'vocabulary_name': vocabulary_name,
                'language_code': language_code,
                'status': 'ready',
                'phrase_count': len(phrases)
            }
            
        except ClientError as e:
            logger.error(f"Vocabulary creation error: {e}")
            raise ValueError(f"Vocabulary creation error: {e.response['Error']['Message']}")
    
    async def get_supported_formats(self) -> List[str]:
        """Get list of supported audio/video formats."""
        return [
            'mp3', 'mp4', 'wav', 'flac', 'ogg', 'amr', 'webm', 'm4a'
        ]
    
    async def get_supported_languages(self) -> List[Dict[str, str]]:
        """Get list of supported languages."""
        return [
            {'code': 'en-US', 'name': 'English (US)'},
            {'code': 'en-GB', 'name': 'English (UK)'},
            {'code': 'es-US', 'name': 'Spanish (US)'},
            {'code': 'fr-FR', 'name': 'French'},
            {'code': 'de-DE', 'name': 'German'},
            {'code': 'it-IT', 'name': 'Italian'},
            {'code': 'pt-BR', 'name': 'Portuguese (Brazil)'},
            {'code': 'ja-JP', 'name': 'Japanese'},
            {'code': 'ko-KR', 'name': 'Korean'},
            {'code': 'zh-CN', 'name': 'Chinese (Mandarin)'}
        ]
    
    def _get_media_format(self, file_extension: str) -> str:
        """Map file extension to Transcribe media format."""
        format_mapping = {
            'mp3': 'mp3',
            'mp4': 'mp4',
            'wav': 'wav',
            'flac': 'flac',
            'ogg': 'ogg',
            'amr': 'amr',
            'webm': 'webm',
            'm4a': 'mp4'
        }
        
        return format_mapping.get(file_extension, 'mp3')
    
    async def _download_transcript(self, transcript_uri: str) -> Dict[str, Any]:
        """Download transcript JSON from S3."""
        try:
            # Parse S3 URI
            uri_parts = transcript_uri.replace('s3://', '').split('/', 1)
            bucket_name = uri_parts[0]
            object_key = uri_parts[1]
            
            # Download transcript
            response = self.s3_client.get_object(Bucket=bucket_name, Key=object_key)
            transcript_json = response['Body'].read().decode('utf-8')
            
            import json
            return json.loads(transcript_json)
            
        except Exception as e:
            logger.error(f"Error downloading transcript: {e}")
            raise ValueError(f"Error downloading transcript: {str(e)}")
    
    def _parse_transcript(self, transcript_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse transcript JSON and extract useful information."""
        try:
            results = transcript_data.get('results', {})
            
            # Get full transcript
            transcript_text = ""
            if 'transcripts' in results and results['transcripts']:
                transcript_text = results['transcripts'][0]['transcript']
            
            # Calculate average confidence
            items = results.get('items', [])
            confidences = []
            
            for item in items:
                if item['type'] == 'pronunciation' and 'alternatives' in item:
                    for alt in item['alternatives']:
                        if 'confidence' in alt:
                            confidences.append(float(alt['confidence']))
            
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Extract speaker labels if available
            speaker_labels = []
            if 'speaker_labels' in results:
                segments = results['speaker_labels'].get('segments', [])
                for segment in segments:
                    speaker_labels.append({
                        'speaker': segment.get('speaker_label'),
                        'start_time': segment.get('start_time'),
                        'end_time': segment.get('end_time'),
                        'items': segment.get('items', [])
                    })
            
            return {
                'transcript': transcript_text,
                'confidence': avg_confidence,
                'speaker_labels': speaker_labels,
                'word_count': len(transcript_text.split()),
                'duration': self._calculate_duration(items)
            }
            
        except Exception as e:
            logger.error(f"Error parsing transcript: {e}")
            raise ValueError(f"Error parsing transcript: {str(e)}")
    
    def _calculate_duration(self, items: List[Dict[str, Any]]) -> float:
        """Calculate audio duration from transcript items."""
        if not items:
            return 0.0
        
        try:
            last_item = items[-1]
            if 'end_time' in last_item:
                return float(last_item['end_time'])
        except (ValueError, KeyError):
            pass
        
        return 0.0
    
    async def _poll_and_get_results(self, job_name: str, language_code: str) -> Dict[str, Any]:
        """Poll for job completion and return results."""
        max_attempts = 120
        attempt = 0
        
        while attempt < max_attempts:
            job_status = self.transcribe_client.get_transcription_job(
                TranscriptionJobName=job_name
            )
            
            status = job_status['TranscriptionJob']['TranscriptionJobStatus']
            
            if status == 'COMPLETED':
                break
            elif status == 'FAILED':
                failure_reason = job_status['TranscriptionJob'].get('FailureReason', 'Unknown error')
                raise ValueError(f"Transcription job failed: {failure_reason}")
            
            time.sleep(5)
            attempt += 1
        
        if attempt >= max_attempts:
            raise ValueError("Transcription job timed out")
        
        # Get results
        transcript_uri = job_status['TranscriptionJob']['Transcript']['TranscriptFileUri']
        transcript_data = await self._download_transcript(transcript_uri)
        parsed_transcript = self._parse_transcript(transcript_data)
        
        return {
            'transcript': parsed_transcript['transcript'],
            'confidence': parsed_transcript['confidence'],
            'speaker_labels': parsed_transcript.get('speaker_labels', []),
            'word_count': len(parsed_transcript['transcript'].split()),
            'duration_seconds': parsed_transcript.get('duration', 0),
            'job_name': job_name,
            'language_code': language_code
        }
    
    async def validate_audio_file(self, file_size: int, content_type: str) -> Dict[str, Any]:
        """Validate audio file for transcription."""
        supported_formats = await self.get_supported_formats()
        
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check file size (2GB limit)
        max_file_size = 2 * 1024 * 1024 * 1024  # 2GB
        
        if file_size > max_file_size:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"File size {file_size} exceeds maximum limit of {max_file_size} bytes")
        
        # Check content type
        file_extension = content_type.split('/')[-1] if '/' in content_type else content_type
        if file_extension not in supported_formats:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Unsupported format: {content_type}")
        
        # Warn about large files
        if file_size > 100 * 1024 * 1024:  # 100MB
            validation_result['warnings'].append("Large file may take longer to process")
        
        return validation_result


# Global service instance
transcribe_service = TranscribeService()