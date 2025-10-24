"""Configuration settings for SnapStudy backend."""

import os
from typing import List

class Settings:
    """Application settings."""
    
    # API Configuration
    api_version: str = os.getenv("API_VERSION", "1.0.0")
    
    # AWS Configuration
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    
    # DynamoDB Table Names
    users_table: str = os.getenv("USERS_TABLE", "SnapStudy-Users")
    lessons_table: str = os.getenv("LESSONS_TABLE", "SnapStudy-Lessons")
    micro_lessons_table: str = os.getenv("MICRO_LESSONS_TABLE", "SnapStudy-MicroLessons")
    quizzes_table: str = os.getenv("QUIZZES_TABLE", "SnapStudy-Quizzes")
    user_engagement_table: str = os.getenv("USER_ENGAGEMENT_TABLE", "SnapStudy-UserEngagement")
    chat_history_table: str = os.getenv("CHAT_HISTORY_TABLE", "SnapStudy-ChatHistory")
    audio_lessons_table: str = os.getenv("AUDIO_LESSONS_TABLE", "SnapStudy-AudioLessons")
    video_lessons_table: str = os.getenv("VIDEO_LESSONS_TABLE", "SnapStudy-VideoLessons")
    
    # S3 Configuration
    content_bucket: str = os.getenv("CONTENT_BUCKET", "snapstudy-content")
    s3_bucket_name: str = os.getenv("S3_BUCKET_NAME", "snapstudy-content")
    audio_content_bucket: str = os.getenv("AUDIO_CONTENT_BUCKET", "snapstudy-audio-content")
    
    # Cognito Configuration
    user_pool_id: str = os.getenv("USER_POOL_ID", "")
    user_pool_client_id: str = os.getenv("USER_POOL_CLIENT_ID", "")
    
    # JWT Configuration
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # CORS Configuration
    cors_origins: List[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # Bedrock Configuration
    bedrock_model_id: str = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")
    bedrock_region: str = os.getenv("BEDROCK_REGION", "us-east-1")

    # Bedrock Agents Configuration (AgentCore)
    learning_agent_id: str = os.getenv("LEARNING_AGENT_ID", "")
    adaptive_agent_id: str = os.getenv("ADAPTIVE_AGENT_ID", "")
    bedrock_agent_alias_id: str = os.getenv("BEDROCK_AGENT_ALIAS_ID", "TSTALIASID")

    # Knowledge Base Configuration
    knowledge_base_id: str = os.getenv("KNOWLEDGE_BASE_ID", "")
    opensearch_endpoint: str = os.getenv("OPENSEARCH_ENDPOINT", "")

    # Bedrock Guardrails Configuration
    bedrock_guardrail_id: str = os.getenv("BEDROCK_GUARDRAIL_ID", "")
    bedrock_guardrail_version: str = os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT")

    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    # Throttling and Rate Limiting Configuration
    bedrock_max_requests_per_minute: int = int(os.getenv("BEDROCK_MAX_RPM", "80"))
    bedrock_burst_capacity: int = int(os.getenv("BEDROCK_BURST_CAPACITY", "10"))
    bedrock_agent_max_rpm: int = int(os.getenv("BEDROCK_AGENT_MAX_RPM", "40"))
    bedrock_model_max_rpm: int = int(os.getenv("BEDROCK_MODEL_MAX_RPM", "60"))
    
    # Request Queue Configuration
    max_concurrent_requests: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "2"))
    request_processing_delay: float = float(os.getenv("REQUEST_PROCESSING_DELAY", "0.8"))

settings = Settings()