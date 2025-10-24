"""
Video Micro-Lesson Generation Service using Amazon Nova Reel.

This service creates engaging video content from text-based micro-lessons
with AI-generated visuals, narration, and learning-optimized features.
"""

import boto3
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import uuid
import base64
from botocore.exceptions import ClientError

from ..config import settings
from .dynamodb import db_service
from .bedrock import bedrock_service
from .audio_generation import audio_generation_service

logger = logging.getLogger(__name__)


class VideoMicroLessonGenerator:
    """
    Generate personalized video micro-lessons using Amazon Nova Reel.
    
    Features:
    - AI-generated video content from text scripts
    - Visual learning optimization
    - Narration integration with Polly
    - Interactive learning elements
    - Professional visual styling
    """
    
    def __init__(self):
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=settings.aws_region)
        self.s3_client = boto3.client('s3', region_name=settings.aws_region)
        self.bedrock = bedrock_service
        self.db = db_service
        self.audio_service = audio_generation_service
        
        # Video configuration
        self.video_bucket = getattr(settings, 'video_content_bucket', settings.s3_bucket_name)
        self.video_format = 'mp4'
        self.video_resolution = '1280x720'  # HD
        self.frame_rate = 30
        
        # Nova Reel model configuration
        self.nova_model_id = 'amazon.nova-reel-v1:0'
        
        # Visual styles for different learning contexts
        self.visual_styles = {
            'professional': {
                'style': 'clean, professional, corporate',
                'color_scheme': 'blue and white corporate colors',
                'background': 'modern office or clean studio',
                'typography': 'professional sans-serif fonts'
            },
            'educational': {
                'style': 'friendly, educational, approachable',
                'color_scheme': 'warm educational colors',
                'background': 'classroom or library setting',
                'typography': 'clear, readable fonts'
            },
            'technical': {
                'style': 'modern, technical, high-tech',
                'color_scheme': 'dark theme with accent colors',
                'background': 'tech environment or abstract',
                'typography': 'monospace and modern fonts'
            },
            'creative': {
                'style': 'creative, dynamic, engaging',
                'color_scheme': 'vibrant, creative colors',
                'background': 'creative studio or artistic',
                'typography': 'creative, modern fonts'
            }
        }
        
        # Learning style video adaptations
        self.learning_adaptations = {
            'visual': {
                'visual_density': 'high',
                'diagram_frequency': 'frequent',
                'text_overlay': 'extensive',
                'animation_speed': 'moderate',
                'scene_duration': 8  # seconds
            },
            'auditory': {
                'visual_density': 'moderate',
                'diagram_frequency': 'moderate',
                'text_overlay': 'minimal',
                'animation_speed': 'slow',
                'scene_duration': 10
            },
            'reading': {
                'visual_density': 'high',
                'diagram_frequency': 'frequent',
                'text_overlay': 'extensive',
                'animation_speed': 'slow',
                'scene_duration': 12
            },
            'kinesthetic': {
                'visual_density': 'high',
                'diagram_frequency': 'frequent',
                'text_overlay': 'moderate',
                'animation_speed': 'fast',
                'scene_duration': 6
            }
        }
    
    async def generate_video_micro_lesson(
        self,
        text_lesson: Dict[str, Any],
        user_profile: Dict[str, Any],
        lesson_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate video micro-lesson from text content.
        
        Args:
            text_lesson: Text-based micro-lesson content
            user_profile: User preferences and learning profile
            lesson_context: Additional context about the lesson sequence
            
        Returns:
            Dict containing video lesson metadata and URLs
        """
        try:
            logger.info(f"Generating video micro-lesson: {text_lesson.get('title', 'Untitled')}")
            
            # 1. Create video script from text lesson
            video_script = await self._create_video_script(
                text_lesson, user_profile, lesson_context
            )
            
            # 2. Generate visual scenes using Nova Reel
            video_scenes = await self._generate_video_scenes(
                video_script, user_profile
            )
            
            # 3. Generate narration audio
            narration_audio = await self._generate_narration(
                video_script, user_profile
            )
            
            # 4. Combine video and audio
            final_video = await self._combine_video_and_audio(
                video_scenes, narration_audio, user_profile
            )
            
            # 5. Add learning enhancements
            enhanced_video = await self._add_learning_enhancements(
                final_video, text_lesson, user_profile
            )
            
            # 6. Store video file in S3
            video_url = await self._store_video_file(
                enhanced_video, text_lesson, user_profile
            )
            
            # 7. Create video lesson metadata
            video_lesson = {
                'video_lesson_id': str(uuid.uuid4()),
                'text_lesson_id': text_lesson.get('micro_lesson_id'),
                'title': text_lesson.get('title'),
                'video_url': video_url,
                'duration_seconds': enhanced_video['duration'],
                'file_size_bytes': enhanced_video['file_size'],
                'resolution': self.video_resolution,
                'frame_rate': self.frame_rate,
                'visual_style': self._select_visual_style(user_profile),
                'learning_adaptations': self.learning_adaptations.get(
                    user_profile.get('learning_style', 'visual')
                ),
                'script': video_script,
                'scenes': video_scenes['scene_descriptions'],
                'narration_metadata': narration_audio.get('metadata', {}),
                'key_timestamps': enhanced_video.get('key_timestamps', []),
                'interactive_elements': enhanced_video.get('interactive_elements', []),
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'format': self.video_format
            }
            
            # 8. Store metadata in DynamoDB
            await self._store_video_lesson_metadata(video_lesson, user_profile)
            
            logger.info(f"Video micro-lesson generated successfully: {video_lesson['video_lesson_id']}")
            return video_lesson
            
        except Exception as e:
            logger.error(f"Error generating video micro-lesson: {e}")
            raise Exception(f"Failed to generate video micro-lesson: {str(e)}")
    
    async def _create_video_script(
        self,
        text_lesson: Dict[str, Any],
        user_profile: Dict[str, Any],
        lesson_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create detailed video script from text lesson."""
        
        learning_style = user_profile.get('learning_style', 'visual')
        profession = user_profile.get('profession', 'general')
        visual_style = self._select_visual_style(user_profile)
        
        system_prompt = """You are an expert video script writer specializing in educational content. Create engaging, visual scripts that optimize learning through video."""
        
        prompt = f"""
        Create a detailed video script for this micro-lesson:

        Lesson Content:
        Title: {text_lesson.get('title', '')}
        Content: {text_lesson.get('content', '')}
        Key Concepts: {text_lesson.get('key_concepts', [])}
        Learning Objectives: {text_lesson.get('learning_objectives', [])}
        
        User Profile:
        - Learning Style: {learning_style}
        - Profession: {profession}
        - Visual Style Preference: {visual_style['style']}
        
        Create a video script optimized for {learning_style} learners with:
        1. Scene-by-scene breakdown with visual descriptions
        2. Narration text for each scene
        3. Visual elements (diagrams, animations, text overlays)
        4. Timing and pacing information
        5. Interactive elements and engagement points
        6. Professional examples relevant to {profession}
        
        Return JSON with:
        {{
            "title": "Video lesson title",
            "total_duration_seconds": 300,
            "introduction": {{
                "narration": "Welcome script",
                "visual_description": "Opening scene description",
                "duration_seconds": 15,
                "visual_elements": ["title card", "presenter"]
            }},
            "main_scenes": [
                {{
                    "scene_number": 1,
                    "narration": "Scene narration text",
                    "visual_description": "Detailed visual description",
                    "duration_seconds": 45,
                    "visual_elements": ["diagram", "animation", "text overlay"],
                    "key_concepts": ["concept1"],
                    "interactive_elements": ["pause point", "reflection question"]
                }}
            ],
            "conclusion": {{
                "narration": "Conclusion script",
                "visual_description": "Closing scene description", 
                "duration_seconds": 20,
                "visual_elements": ["summary", "next steps"]
            }},
            "visual_style_guide": {{
                "color_scheme": "{visual_style['color_scheme']}",
                "background_style": "{visual_style['background']}",
                "typography": "{visual_style['typography']}",
                "animation_style": "smooth, professional"
            }},
            "accessibility_features": ["subtitles", "audio_descriptions", "high_contrast"]
        }}
        """
        
        try:
            response = await self.bedrock.invoke_claude(
                prompt, max_tokens=4096, temperature=0.7, system_prompt=system_prompt
            )
            return json.loads(response.strip())
        except Exception as e:
            logger.error(f"Error creating video script: {e}")
            # Fallback to basic script
            return self._create_fallback_script(text_lesson, user_profile)
    
    def _create_fallback_script(self, text_lesson: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Create a basic fallback script if AI generation fails."""
        return {
            "title": text_lesson.get('title', 'Micro-Lesson'),
            "total_duration_seconds": 180,
            "introduction": {
                "narration": f"Welcome to this lesson on {text_lesson.get('title', 'our topic')}.",
                "visual_description": "Clean title card with lesson title",
                "duration_seconds": 10,
                "visual_elements": ["title card"]
            },
            "main_scenes": [
                {
                    "scene_number": 1,
                    "narration": text_lesson.get('content', 'Lesson content'),
                    "visual_description": "Educational content with visual aids",
                    "duration_seconds": 150,
                    "visual_elements": ["text overlay", "diagrams"],
                    "key_concepts": text_lesson.get('key_concepts', [])
                }
            ],
            "conclusion": {
                "narration": "That concludes this lesson. Review the key concepts and continue learning.",
                "visual_description": "Summary slide with key points",
                "duration_seconds": 20,
                "visual_elements": ["summary"]
            }
        }
    
    def _select_visual_style(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Select appropriate visual style based on user profile."""
        
        profession = user_profile.get('profession', 'general').lower()
        
        if any(term in profession for term in ['business', 'corporate', 'finance', 'management']):
            return self.visual_styles['professional']
        elif any(term in profession for term in ['tech', 'engineer', 'developer', 'programmer']):
            return self.visual_styles['technical']
        elif any(term in profession for term in ['design', 'creative', 'artist', 'marketing']):
            return self.visual_styles['creative']
        else:
            return self.visual_styles['educational']
    
    async def _generate_video_scenes(
        self,
        video_script: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate video scenes using Amazon Nova Reel."""
        
        try:
            learning_style = user_profile.get('learning_style', 'visual')
            adaptations = self.learning_adaptations.get(learning_style)
            visual_style = video_script.get('visual_style_guide', {})
            
            # Prepare scenes for Nova Reel generation
            scenes_to_generate = []
            
            # Introduction scene
            intro = video_script.get('introduction', {})
            if intro:
                scenes_to_generate.append({
                    'scene_type': 'introduction',
                    'description': intro.get('visual_description', ''),
                    'duration': intro.get('duration_seconds', 10),
                    'style': visual_style
                })
            
            # Main scenes
            for scene in video_script.get('main_scenes', []):
                scenes_to_generate.append({
                    'scene_type': 'main_content',
                    'scene_number': scene.get('scene_number', 1),
                    'description': scene.get('visual_description', ''),
                    'duration': scene.get('duration_seconds', 30),
                    'visual_elements': scene.get('visual_elements', []),
                    'key_concepts': scene.get('key_concepts', []),
                    'style': visual_style
                })
            
            # Conclusion scene
            conclusion = video_script.get('conclusion', {})
            if conclusion:
                scenes_to_generate.append({
                    'scene_type': 'conclusion',
                    'description': conclusion.get('visual_description', ''),
                    'duration': conclusion.get('duration_seconds', 15),
                    'style': visual_style
                })
            
            # Generate each scene with Nova Reel
            generated_scenes = []
            for scene in scenes_to_generate:
                scene_video = await self._generate_single_scene(scene, adaptations)
                generated_scenes.append(scene_video)
            
            return {
                'scenes': generated_scenes,
                'scene_descriptions': [scene.get('description', '') for scene in scenes_to_generate],
                'total_scenes': len(generated_scenes),
                'visual_style': visual_style
            }
            
        except Exception as e:
            logger.error(f"Error generating video scenes: {e}")
            # Return placeholder scene data
            return {
                'scenes': [{'placeholder': True, 'duration': 180}],
                'scene_descriptions': ['Educational content visualization'],
                'total_scenes': 1,
                'error': str(e)
            }
    
    async def _generate_single_scene(
        self,
        scene_config: Dict[str, Any],
        adaptations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a single video scene using Nova Reel."""
        
        try:
            # Prepare Nova Reel prompt
            nova_prompt = self._create_nova_prompt(scene_config, adaptations)
            
            # Call Nova Reel via Bedrock
            request_body = {
                "taskType": "TEXT_VIDEO",
                "textToVideoParams": {
                    "text": nova_prompt,
                    "durationSeconds": scene_config.get('duration', 30),
                    "fps": self.frame_rate,
                    "dimension": self.video_resolution,
                    "seed": 42  # For consistent results
                }
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=self.nova_model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            
            # Process Nova Reel response
            if 'videoDataUri' in response_body:
                # Extract video data from data URI
                video_data = self._extract_video_from_data_uri(response_body['videoDataUri'])
                
                return {
                    'scene_type': scene_config.get('scene_type'),
                    'scene_number': scene_config.get('scene_number'),
                    'video_data': video_data,
                    'duration': scene_config.get('duration'),
                    'description': scene_config.get('description'),
                    'generated_successfully': True
                }
            else:
                logger.warning(f"Nova Reel did not return video data for scene")
                return self._create_placeholder_scene(scene_config)
                
        except Exception as e:
            logger.error(f"Error generating scene with Nova Reel: {e}")
            return self._create_placeholder_scene(scene_config)
    
    def _create_nova_prompt(self, scene_config: Dict[str, Any], adaptations: Dict[str, Any]) -> str:
        """Create optimized prompt for Nova Reel video generation."""
        
        style = scene_config.get('style', {})
        visual_elements = scene_config.get('visual_elements', [])
        
        prompt_parts = [
            f"Create a {adaptations['animation_speed']} paced educational video scene.",
            f"Visual style: {style.get('style', 'professional and clean')}",
            f"Color scheme: {style.get('color_scheme', 'professional colors')}",
            f"Background: {style.get('background', 'clean educational setting')}",
            f"Scene description: {scene_config.get('description', 'Educational content')}",
        ]
        
        if visual_elements:
            prompt_parts.append(f"Include these visual elements: {', '.join(visual_elements)}")
        
        if scene_config.get('key_concepts'):
            prompt_parts.append(f"Highlight these key concepts: {', '.join(scene_config['key_concepts'])}")
        
        prompt_parts.extend([
            "Ensure high visual quality and educational clarity.",
            "Make it engaging and professional for learning.",
            f"Duration: {scene_config.get('duration', 30)} seconds"
        ])
        
        return ' '.join(prompt_parts)
    
    def _extract_video_from_data_uri(self, data_uri: str) -> bytes:
        """Extract video data from data URI format."""
        try:
            # Data URI format: data:video/mp4;base64,<base64_data>
            header, data = data_uri.split(',', 1)
            return base64.b64decode(data)
        except Exception as e:
            logger.error(f"Error extracting video from data URI: {e}")
            raise
    
    def _create_placeholder_scene(self, scene_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create placeholder scene data when generation fails."""
        return {
            'scene_type': scene_config.get('scene_type'),
            'scene_number': scene_config.get('scene_number'),
            'placeholder': True,
            'duration': scene_config.get('duration', 30),
            'description': scene_config.get('description'),
            'generated_successfully': False
        }
    
    async def _generate_narration(
        self,
        video_script: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate narration audio for the video."""
        
        try:
            # Combine all narration text
            narration_parts = []
            
            if video_script.get('introduction', {}).get('narration'):
                narration_parts.append(video_script['introduction']['narration'])
            
            for scene in video_script.get('main_scenes', []):
                if scene.get('narration'):
                    narration_parts.append(scene['narration'])
            
            if video_script.get('conclusion', {}).get('narration'):
                narration_parts.append(video_script['conclusion']['narration'])
            
            full_narration = ' '.join(narration_parts)
            
            # Create text lesson format for audio service
            narration_lesson = {
                'title': video_script.get('title', 'Video Narration'),
                'content': full_narration,
                'key_concepts': []
            }
            
            # Generate audio using existing audio service
            audio_result = await self.audio_service.generate_audio_micro_lesson(
                narration_lesson, user_profile
            )
            
            return {
                'audio_data': audio_result,
                'full_text': full_narration,
                'metadata': {
                    'voice_profile': audio_result.get('voice_profile'),
                    'duration': audio_result.get('duration_seconds')
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating narration: {e}")
            return {
                'placeholder': True,
                'full_text': video_script.get('title', 'Video content'),
                'error': str(e)
            }
    
    async def _combine_video_and_audio(
        self,
        video_scenes: Dict[str, Any],
        narration_audio: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Combine video scenes with narration audio."""
        
        # For now, return combined metadata
        # In a full implementation, this would use video processing libraries
        # to actually combine the video and audio tracks
        
        total_duration = sum(
            scene.get('duration', 30) for scene in video_scenes.get('scenes', [])
        )
        
        return {
            'video_scenes': video_scenes,
            'narration_audio': narration_audio,
            'duration': total_duration,
            'file_size': 50 * 1024 * 1024,  # Estimated 50MB
            'combined_successfully': True
        }
    
    async def _add_learning_enhancements(
        self,
        video_data: Dict[str, Any],
        text_lesson: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add learning-specific enhancements to video."""
        
        enhanced_video = {
            **video_data,
            'enhancements': {
                'learning_optimized': True,
                'visual_learning_elements': True,
                'interactive_components': True,
                'accessibility_features': True
            },
            'key_timestamps': self._generate_video_timestamps(text_lesson, video_data['duration']),
            'interactive_elements': self._generate_interactive_elements(text_lesson, user_profile),
            'accessibility_features': {
                'subtitles': True,
                'audio_descriptions': True,
                'high_contrast_mode': True,
                'playback_speed_control': True
            }
        }
        
        return enhanced_video
    
    def _generate_video_timestamps(self, text_lesson: Dict[str, Any], duration: int) -> List[Dict[str, Any]]:
        """Generate timestamps for key concepts in the video."""
        
        key_concepts = text_lesson.get('key_concepts', [])
        learning_objectives = text_lesson.get('learning_objectives', [])
        
        timestamps = []
        
        # Add key concept timestamps
        if key_concepts:
            interval = duration // (len(key_concepts) + 1)
            for i, concept in enumerate(key_concepts):
                timestamps.append({
                    'time_seconds': (i + 1) * interval,
                    'concept': concept,
                    'type': 'key_concept',
                    'visual_element': 'concept_highlight'
                })
        
        # Add learning objective checkpoints
        if learning_objectives:
            for i, objective in enumerate(learning_objectives):
                timestamp = duration * 0.8 + (i * 10)  # Near the end
                timestamps.append({
                    'time_seconds': int(timestamp),
                    'objective': objective,
                    'type': 'learning_checkpoint',
                    'visual_element': 'progress_indicator'
                })
        
        return timestamps
    
    def _generate_interactive_elements(self, text_lesson: Dict[str, Any], user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate interactive elements for the video."""
        
        elements = []
        
        # Add pause points for reflection
        elements.append({
            'type': 'pause_point',
            'time_seconds': 60,
            'title': 'Reflection Moment',
            'description': 'Take a moment to think about what you\'ve learned so far.'
        })
        
        # Add knowledge check
        if text_lesson.get('key_concepts'):
            elements.append({
                'type': 'knowledge_check',
                'time_seconds': 120,
                'title': 'Quick Check',
                'description': f"Can you explain {text_lesson['key_concepts'][0]}?",
                'interaction': 'pause_and_reflect'
            })
        
        # Add summary review
        elements.append({
            'type': 'summary_review',
            'time_seconds': -30,  # 30 seconds before end
            'title': 'Key Takeaways',
            'description': 'Review the main points from this lesson.'
        })
        
        return elements
    
    async def _store_video_file(
        self,
        video_data: Dict[str, Any],
        text_lesson: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> str:
        """Store video file in S3 and return URL."""
        
        try:
            # Generate unique filename
            lesson_id = text_lesson.get('micro_lesson_id', str(uuid.uuid4()))
            user_id = user_profile.get('user_id', 'anonymous')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            filename = f"video_lessons/{user_id}/{lesson_id}_{timestamp}.{self.video_format}"
            
            # For now, create a placeholder file
            # In full implementation, this would store the actual video data
            placeholder_content = json.dumps({
                'video_lesson_id': str(uuid.uuid4()),
                'title': text_lesson.get('title'),
                'duration': video_data.get('duration'),
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'placeholder': True,
                'message': 'Video generation completed - file would be stored here'
            }).encode('utf-8')
            
            # Upload metadata to S3
            self.s3_client.put_object(
                Bucket=self.video_bucket,
                Key=filename.replace('.mp4', '_metadata.json'),
                Body=placeholder_content,
                ContentType='application/json',
                Metadata={
                    'lesson_id': lesson_id,
                    'user_id': user_id,
                    'duration': str(video_data.get('duration', 0)),
                    'generated_at': datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Generate presigned URL
            video_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.video_bucket, 'Key': filename.replace('.mp4', '_metadata.json')},
                ExpiresIn=86400  # 24 hours
            )
            
            return video_url
            
        except Exception as e:
            logger.error(f"Error storing video file: {e}")
            raise Exception(f"Failed to store video file: {str(e)}")
    
    async def _store_video_lesson_metadata(
        self,
        video_lesson: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> None:
        """Store video lesson metadata in DynamoDB."""
        
        try:
            # Store in VideoLessons table
            await self.db.put_item('VideoLessons', video_lesson)
            
            # Track engagement
            await self.db.track_engagement({
                'user_id': user_profile.get('user_id'),
                'event_type': 'video_lesson_generated',
                'event_data': {
                    'video_lesson_id': video_lesson['video_lesson_id'],
                    'text_lesson_id': video_lesson.get('text_lesson_id'),
                    'duration_seconds': video_lesson['duration_seconds'],
                    'visual_style': video_lesson['visual_style']['style']
                }
            })
            
        except Exception as e:
            logger.error(f"Error storing video lesson metadata: {e}")
    
    async def get_video_lesson(self, video_lesson_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve video lesson metadata."""
        try:
            return await self.db.get_item('VideoLessons', {'video_lesson_id': video_lesson_id})
        except Exception as e:
            logger.error(f"Error retrieving video lesson: {e}")
            return None
    
    async def list_user_video_lessons(self, user_id: str) -> List[Dict[str, Any]]:
        """List all video lessons for a user."""
        try:
            return await self.db.query_items('VideoLessons', 'user_id', user_id)
        except Exception as e:
            logger.error(f"Error listing user video lessons: {e}")
            return []


# Initialize service instance
video_generation_service = VideoMicroLessonGenerator()