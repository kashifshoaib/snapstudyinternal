"""
Audio Micro-Lesson Generation Service using Amazon Polly.

This service converts text-based micro-lessons into high-quality audio content
with personalization based on user preferences and learning styles.
"""

import boto3
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import uuid
import io
from botocore.exceptions import ClientError

from ..config import settings
from .dynamodb import db_service
from .bedrock import bedrock_service

logger = logging.getLogger(__name__)


class AudioMicroLessonGenerator:
    """
    Generate personalized audio micro-lessons using Amazon Polly.
    
    Features:
    - Text-to-speech conversion with voice personalization
    - Learning-optimized pacing and emphasis
    - SSML markup for enhanced speech quality
    - Audio file management and storage
    """
    
    def __init__(self):
        self.polly_client = boto3.client('polly', region_name=settings.aws_region)
        self.s3_client = boto3.client('s3', region_name=settings.aws_region)
        self.bedrock = bedrock_service
        self.db = db_service
        
        # Audio configuration
        self.audio_bucket = getattr(settings, 'audio_content_bucket', settings.s3_bucket_name)
        self.audio_format = 'mp3'
        self.sample_rate = '22050'
        
        # Voice profiles for different user preferences
        self.voice_profiles = {
            'professional_male': {
                'VoiceId': 'Matthew',
                'Engine': 'neural',
                'LanguageCode': 'en-US'
            },
            'professional_female': {
                'VoiceId': 'Joanna',
                'Engine': 'neural', 
                'LanguageCode': 'en-US'
            },
            'friendly_male': {
                'VoiceId': 'Justin',
                'Engine': 'neural',
                'LanguageCode': 'en-US'
            },
            'friendly_female': {
                'VoiceId': 'Kimberly',
                'Engine': 'neural',
                'LanguageCode': 'en-US'
            },
            'authoritative_male': {
                'VoiceId': 'Brian',
                'Engine': 'neural',
                'LanguageCode': 'en-GB'
            },
            'authoritative_female': {
                'VoiceId': 'Emma',
                'Engine': 'neural',
                'LanguageCode': 'en-GB'
            }
        }
        
        # Learning style audio adaptations
        self.learning_adaptations = {
            'visual': {
                'speaking_rate': 'medium',
                'emphasis_level': 'moderate',
                'pause_duration': '1s',
                'description_detail': 'high'
            },
            'auditory': {
                'speaking_rate': 'medium',
                'emphasis_level': 'strong',
                'pause_duration': '0.5s',
                'description_detail': 'medium'
            },
            'reading': {
                'speaking_rate': 'slow',
                'emphasis_level': 'moderate',
                'pause_duration': '1.5s',
                'description_detail': 'high'
            },
            'kinesthetic': {
                'speaking_rate': 'medium-fast',
                'emphasis_level': 'strong',
                'pause_duration': '0.5s',
                'description_detail': 'low'
            }
        }
    
    async def generate_audio_micro_lesson(
        self,
        text_lesson: Dict[str, Any],
        user_profile: Dict[str, Any],
        lesson_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate audio micro-lesson from text content.
        
        Args:
            text_lesson: Text-based micro-lesson content
            user_profile: User preferences and learning profile
            lesson_context: Additional context about the lesson sequence
            
        Returns:
            Dict containing audio lesson metadata and URLs
        """
        try:
            logger.info(f"Generating audio micro-lesson: {text_lesson.get('title', 'Untitled')}")
            
            # 1. Optimize text content for speech
            speech_optimized_content = await self._optimize_text_for_speech(
                text_lesson, user_profile
            )
            
            # 2. Select appropriate voice profile
            voice_config = await self._select_voice_profile(user_profile)
            
            # 3. Generate SSML markup for enhanced speech
            ssml_content = await self._generate_ssml_markup(
                speech_optimized_content, user_profile, voice_config
            )
            
            # 4. Generate audio using Polly
            audio_data = await self._synthesize_speech(
                ssml_content, voice_config
            )
            
            # 5. Add learning enhancements
            enhanced_audio = await self._add_learning_enhancements(
                audio_data, text_lesson, user_profile
            )
            
            # 6. Store audio file in S3
            audio_url = await self._store_audio_file(
                enhanced_audio, text_lesson, user_profile
            )
            
            # 7. Create audio lesson metadata
            audio_lesson = {
                'audio_lesson_id': str(uuid.uuid4()),
                'text_lesson_id': text_lesson.get('micro_lesson_id'),
                'title': text_lesson.get('title'),
                'audio_url': audio_url,
                'duration_seconds': enhanced_audio['duration'],
                'file_size_bytes': enhanced_audio['file_size'],
                'voice_profile': voice_config,
                'learning_adaptations': self.learning_adaptations.get(
                    user_profile.get('learning_style', 'visual')
                ),
                'transcript': speech_optimized_content['full_text'],
                'key_timestamps': enhanced_audio.get('key_timestamps', []),
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'format': self.audio_format,
                'sample_rate': self.sample_rate
            }
            
            # 8. Store metadata in DynamoDB
            await self._store_audio_lesson_metadata(audio_lesson, user_profile)
            
            logger.info(f"Audio micro-lesson generated successfully: {audio_lesson['audio_lesson_id']}")
            return audio_lesson
            
        except Exception as e:
            logger.error(f"Error generating audio micro-lesson: {e}")
            raise Exception(f"Failed to generate audio micro-lesson: {str(e)}")
    
    async def _optimize_text_for_speech(
        self,
        text_lesson: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize text content for natural speech synthesis."""
        
        learning_style = user_profile.get('learning_style', 'visual')
        attention_span = user_profile.get('attention_span', 15)
        
        system_prompt = """You are an expert in converting written educational content into natural, engaging speech. Optimize text for audio learning while maintaining educational value."""
        
        prompt = f"""
        Convert this written micro-lesson into speech-optimized content:

        Original Lesson:
        Title: {text_lesson.get('title', '')}
        Content: {text_lesson.get('content', '')}
        Key Concepts: {text_lesson.get('key_concepts', [])}
        
        User Profile:
        - Learning Style: {learning_style}
        - Attention Span: {attention_span} minutes
        - Profession: {user_profile.get('profession', 'general')}
        
        Optimize for audio by:
        1. Converting written text to natural spoken language
        2. Adding verbal transitions and connectors
        3. Including pronunciation guides for technical terms
        4. Adding emphasis markers for key concepts
        5. Including natural pauses for comprehension
        6. Adapting complexity for {learning_style} learners
        
        Return JSON with:
        {{
            "introduction": "Engaging audio introduction",
            "main_content": "Speech-optimized main content",
            "key_concepts_audio": ["Concept 1 with pronunciation", "Concept 2"],
            "conclusion": "Audio-friendly conclusion",
            "full_text": "Complete speech text",
            "emphasis_points": ["Important phrase 1", "Key term 2"],
            "pause_markers": [45, 120, 180], // Seconds where natural pauses should occur
            "pronunciation_guide": {{"technical_term": "pronunciation"}},
            "estimated_speech_duration": 300 // seconds
        }}
        """
        
        try:
            response = await self.bedrock.invoke_claude(
                prompt, max_tokens=4096, temperature=0.3, system_prompt=system_prompt
            )
            return json.loads(response.strip())
        except Exception as e:
            logger.error(f"Error optimizing text for speech: {e}")
            # Fallback to basic optimization
            return {
                "introduction": f"Welcome to today's lesson on {text_lesson.get('title', 'our topic')}.",
                "main_content": text_lesson.get('content', ''),
                "conclusion": "That concludes this lesson. Take a moment to review the key concepts.",
                "full_text": f"Welcome to today's lesson on {text_lesson.get('title', 'our topic')}. {text_lesson.get('content', '')} That concludes this lesson.",
                "emphasis_points": text_lesson.get('key_concepts', []),
                "pause_markers": [30, 60, 90],
                "estimated_speech_duration": len(text_lesson.get('content', '')) * 0.1
            }
    
    async def _select_voice_profile(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Select appropriate voice based on user preferences."""
        
        # Default voice selection logic
        age = user_profile.get('age', 30)
        gender_preference = user_profile.get('voice_preference', 'female')
        tone_preference = user_profile.get('tone_preference', 'professional')
        
        # Select voice based on preferences
        if tone_preference == 'professional':
            if gender_preference == 'male':
                voice_key = 'professional_male'
            else:
                voice_key = 'professional_female'
        elif tone_preference == 'friendly':
            if gender_preference == 'male':
                voice_key = 'friendly_male'
            else:
                voice_key = 'friendly_female'
        else:  # authoritative
            if gender_preference == 'male':
                voice_key = 'authoritative_male'
            else:
                voice_key = 'authoritative_female'
        
        voice_config = self.voice_profiles.get(voice_key, self.voice_profiles['professional_female'])
        
        # Add user-specific customizations
        voice_config['speaking_rate'] = user_profile.get('speaking_rate', 'medium')
        voice_config['volume'] = user_profile.get('audio_volume', 'medium')
        
        return voice_config
    
    async def _generate_ssml_markup(
        self,
        speech_content: Dict[str, Any],
        user_profile: Dict[str, Any],
        voice_config: Dict[str, Any]
    ) -> str:
        """Generate SSML markup for enhanced speech synthesis."""
        
        learning_style = user_profile.get('learning_style', 'visual')
        adaptations = self.learning_adaptations.get(learning_style, self.learning_adaptations['visual'])
        
        # Build SSML with learning-optimized markup
        ssml_parts = ['<speak>']
        
        # Add prosody settings
        ssml_parts.append(f'<prosody rate="{adaptations["speaking_rate"]}" volume="{voice_config.get("volume", "medium")}">')
        
        # Introduction with emphasis
        if speech_content.get('introduction'):
            ssml_parts.append(f'<emphasis level="moderate">{speech_content["introduction"]}</emphasis>')
            ssml_parts.append(f'<break time="{adaptations["pause_duration"]}"/>')
        
        # Main content with emphasis on key points
        main_content = speech_content.get('main_content', '')
        
        # Add emphasis to key concepts
        for emphasis_point in speech_content.get('emphasis_points', []):
            if emphasis_point in main_content:
                main_content = main_content.replace(
                    emphasis_point,
                    f'<emphasis level="{adaptations["emphasis_level"]}">{emphasis_point}</emphasis>'
                )
        
        # Add pauses at natural break points
        for pause_time in speech_content.get('pause_markers', []):
            # Insert pauses at approximate word positions
            words = main_content.split()
            if len(words) > pause_time // 2:  # Rough estimate of words per second
                insert_pos = min(pause_time // 2, len(words) - 1)
                words.insert(insert_pos, f'<break time="{adaptations["pause_duration"]}"/>')
                main_content = ' '.join(words)
        
        ssml_parts.append(main_content)
        
        # Conclusion with final pause
        if speech_content.get('conclusion'):
            ssml_parts.append(f'<break time="{adaptations["pause_duration"]}"/>')
            ssml_parts.append(f'<emphasis level="moderate">{speech_content["conclusion"]}</emphasis>')
        
        ssml_parts.append('</prosody>')
        ssml_parts.append('</speak>')
        
        return ' '.join(ssml_parts)
    
    async def _synthesize_speech(
        self,
        ssml_content: str,
        voice_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synthesize speech using Amazon Polly."""
        
        try:
            response = self.polly_client.synthesize_speech(
                Text=ssml_content,
                TextType='ssml',
                VoiceId=voice_config['VoiceId'],
                Engine=voice_config['Engine'],
                LanguageCode=voice_config['LanguageCode'],
                OutputFormat=self.audio_format,
                SampleRate=self.sample_rate
            )
            
            # Read audio stream
            audio_stream = response['AudioStream'].read()
            
            return {
                'audio_data': audio_stream,
                'content_type': response['ContentType'],
                'request_characters': response['RequestCharacters'],
                'file_size': len(audio_stream),
                'duration': self._estimate_audio_duration(len(ssml_content))
            }
            
        except ClientError as e:
            logger.error(f"Polly synthesis error: {e}")
            raise Exception(f"Speech synthesis failed: {e}")
    
    def _estimate_audio_duration(self, text_length: int) -> int:
        """Estimate audio duration based on text length."""
        # Average speaking rate: ~150 words per minute, ~5 characters per word
        words_per_minute = 150
        characters_per_word = 5
        characters_per_minute = words_per_minute * characters_per_word
        
        duration_minutes = text_length / characters_per_minute
        return int(duration_minutes * 60)  # Convert to seconds
    
    async def _add_learning_enhancements(
        self,
        audio_data: Dict[str, Any],
        text_lesson: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add learning-specific enhancements to audio."""
        
        # For now, return audio data with basic enhancements
        # Future: Add background music, sound effects, interactive elements
        
        enhanced_audio = {
            **audio_data,
            'enhancements': {
                'learning_optimized': True,
                'key_concept_emphasis': True,
                'natural_pacing': True,
                'pronunciation_guides': True
            },
            'key_timestamps': self._generate_key_timestamps(text_lesson, audio_data['duration'])
        }
        
        return enhanced_audio
    
    def _generate_key_timestamps(self, text_lesson: Dict[str, Any], duration: int) -> List[Dict[str, Any]]:
        """Generate timestamps for key concepts in the audio."""
        
        key_concepts = text_lesson.get('key_concepts', [])
        if not key_concepts:
            return []
        
        # Distribute key concepts evenly throughout the audio
        timestamps = []
        interval = duration // (len(key_concepts) + 1)
        
        for i, concept in enumerate(key_concepts):
            timestamp = (i + 1) * interval
            timestamps.append({
                'time_seconds': timestamp,
                'concept': concept,
                'type': 'key_concept'
            })
        
        return timestamps
    
    async def _store_audio_file(
        self,
        audio_data: Dict[str, Any],
        text_lesson: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> str:
        """Store audio file in S3 and return URL."""
        
        try:
            # Generate unique filename
            lesson_id = text_lesson.get('micro_lesson_id', str(uuid.uuid4()))
            user_id = user_profile.get('user_id', 'anonymous')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            filename = f"audio_lessons/{user_id}/{lesson_id}_{timestamp}.{self.audio_format}"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.audio_bucket,
                Key=filename,
                Body=audio_data['audio_data'],
                ContentType=audio_data['content_type'],
                Metadata={
                    'lesson_id': lesson_id,
                    'user_id': user_id,
                    'duration': str(audio_data['duration']),
                    'generated_at': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Generate presigned URL (valid for 24 hours)
            audio_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.audio_bucket, 'Key': filename},
                ExpiresIn=86400  # 24 hours
            )
            
            return audio_url
            
        except Exception as e:
            logger.error(f"Error storing audio file: {e}")
            raise Exception(f"Failed to store audio file: {str(e)}")
    
    async def _store_audio_lesson_metadata(
        self,
        audio_lesson: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> None:
        """Store audio lesson metadata in DynamoDB."""
        
        try:
            # Store in AudioLessons table (create if needed)
            await self.db.put_item('AudioLessons', audio_lesson)
            
            # Track engagement
            await self.db.track_engagement({
                'user_id': user_profile.get('user_id'),
                'event_type': 'audio_lesson_generated',
                'event_data': {
                    'audio_lesson_id': audio_lesson['audio_lesson_id'],
                    'text_lesson_id': audio_lesson.get('text_lesson_id'),
                    'duration_seconds': audio_lesson['duration_seconds'],
                    'voice_profile': audio_lesson['voice_profile']['VoiceId']
                }
            })
            
        except Exception as e:
            logger.error(f"Error storing audio lesson metadata: {e}")
            # Don't raise exception - audio file is already created
    
    async def get_audio_lesson(self, audio_lesson_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve audio lesson metadata."""
        try:
            return await self.db.get_item('AudioLessons', {'audio_lesson_id': audio_lesson_id})
        except Exception as e:
            logger.error(f"Error retrieving audio lesson: {e}")
            return None
    
    async def list_user_audio_lessons(self, user_id: str) -> List[Dict[str, Any]]:
        """List all audio lessons for a user."""
        try:
            # Query by user_id (requires GSI)
            return await self.db.query_items('AudioLessons', 'user_id', user_id)
        except Exception as e:
            logger.error(f"Error listing user audio lessons: {e}")
            return []


# Initialize service instance
audio_generation_service = AudioMicroLessonGenerator()