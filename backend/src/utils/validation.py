"""
Input validation and sanitization utilities for SnapStudy backend.

Provides comprehensive validation for user inputs, file uploads, and API parameters.
"""

import re
import html
import bleach
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, validator, Field
from email_validator import validate_email, EmailNotValidError

from ..middleware.error_handler import ValidationError


class FileUploadValidator:
    """Validator for file uploads."""
    
    # Allowed file types and their MIME types
    ALLOWED_TYPES = {
        'pdf': ['application/pdf'],
        'doc': ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
        'txt': ['text/plain'],
        'mp3': ['audio/mpeg', 'audio/mp3'],
        'mp4': ['video/mp4'],
        'wav': ['audio/wav'],
        'jpg': ['image/jpeg'],
        'png': ['image/png'],
        'gif': ['image/gif']
    }
    
    # Maximum file sizes (in bytes)
    MAX_SIZES = {
        'pdf': 50 * 1024 * 1024,    # 50MB
        'doc': 25 * 1024 * 1024,    # 25MB
        'txt': 10 * 1024 * 1024,    # 10MB
        'mp3': 100 * 1024 * 1024,   # 100MB
        'mp4': 500 * 1024 * 1024,   # 500MB
        'wav': 100 * 1024 * 1024,   # 100MB
        'jpg': 10 * 1024 * 1024,    # 10MB
        'png': 10 * 1024 * 1024,    # 10MB
        'gif': 5 * 1024 * 1024      # 5MB
    }
    
    @classmethod
    def validate_file(cls, filename: str, content_type: str, file_size: int) -> Dict[str, Any]:
        """Validate uploaded file."""
        
        # Extract file extension
        if '.' not in filename:
            raise ValidationError("File must have an extension")
        
        extension = filename.rsplit('.', 1)[1].lower()
        
        # Check if extension is allowed
        if extension not in cls.ALLOWED_TYPES:
            raise ValidationError(
                f"File type '{extension}' not allowed",
                details={
                    "allowed_types": list(cls.ALLOWED_TYPES.keys()),
                    "provided_type": extension
                }
            )
        
        # Check MIME type
        allowed_mime_types = cls.ALLOWED_TYPES[extension]
        if content_type not in allowed_mime_types:
            raise ValidationError(
                f"Invalid MIME type for {extension} file",
                details={
                    "expected_mime_types": allowed_mime_types,
                    "provided_mime_type": content_type
                }
            )
        
        # Check file size
        max_size = cls.MAX_SIZES.get(extension, 10 * 1024 * 1024)  # Default 10MB
        if file_size > max_size:
            raise ValidationError(
                f"File too large. Maximum size for {extension} files is {max_size // (1024*1024)}MB",
                details={
                    "max_size_bytes": max_size,
                    "provided_size_bytes": file_size,
                    "file_type": extension
                }
            )
        
        return {
            "extension": extension,
            "content_type": content_type,
            "size_bytes": file_size,
            "is_valid": True
        }


class TextSanitizer:
    """Sanitizer for text inputs."""
    
    # HTML tags allowed in rich text
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote',
        'code', 'pre'
    ]
    
    # HTML attributes allowed
    ALLOWED_ATTRIBUTES = {
        '*': ['class'],
        'a': ['href', 'title'],
        'img': ['src', 'alt', 'width', 'height']
    }
    
    @classmethod
    def sanitize_html(cls, text: str, allow_html: bool = False) -> str:
        """Sanitize HTML content."""
        
        if not text:
            return ""
        
        if allow_html:
            # Clean HTML but keep allowed tags
            return bleach.clean(
                text,
                tags=cls.ALLOWED_TAGS,
                attributes=cls.ALLOWED_ATTRIBUTES,
                strip=True
            )
        else:
            # Strip all HTML tags
            return bleach.clean(text, tags=[], strip=True)
    
    @classmethod
    def sanitize_text(cls, text: str, max_length: Optional[int] = None) -> str:
        """Sanitize plain text input."""
        
        if not text:
            return ""
        
        # Remove HTML entities
        text = html.unescape(text)
        
        # Strip whitespace
        text = text.strip()
        
        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Limit length if specified
        if max_length and len(text) > max_length:
            text = text[:max_length]
        
        return text
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize filename for safe storage."""
        
        if not filename:
            return "unnamed_file"
        
        # Remove path separators and dangerous characters
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Ensure filename is not empty
        if not filename:
            return "unnamed_file"
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            max_name_length = 250 - len(ext)
            filename = name[:max_name_length] + ('.' + ext if ext else '')
        
        return filename


class URLValidator:
    """Validator for URLs."""
    
    # Allowed URL schemes
    ALLOWED_SCHEMES = ['http', 'https']
    
    # Allowed domains for specific content types
    ALLOWED_DOMAINS = {
        'youtube': [
            'youtube.com', 'www.youtube.com', 'youtu.be',
            'm.youtube.com', 'music.youtube.com'
        ],
        'educational': [
            'coursera.org', 'edx.org', 'khanacademy.org',
            'udemy.com', 'udacity.com', 'pluralsight.com'
        ]
    }
    
    @classmethod
    def validate_url(cls, url: str, allowed_domains: Optional[List[str]] = None) -> Dict[str, Any]:
        """Validate URL format and domain."""
        
        if not url:
            raise ValidationError("URL cannot be empty")
        
        # Basic URL format validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(url):
            raise ValidationError("Invalid URL format")
        
        # Extract domain
        domain_match = re.search(r'https?://([^/]+)', url)
        if not domain_match:
            raise ValidationError("Could not extract domain from URL")
        
        domain = domain_match.group(1).lower()
        
        # Check against allowed domains if specified
        if allowed_domains:
            if not any(domain.endswith(allowed_domain) for allowed_domain in allowed_domains):
                raise ValidationError(
                    f"Domain not allowed: {domain}",
                    details={
                        "allowed_domains": allowed_domains,
                        "provided_domain": domain
                    }
                )
        
        return {
            "url": url,
            "domain": domain,
            "is_valid": True
        }
    
    @classmethod
    def validate_youtube_url(cls, url: str) -> Dict[str, Any]:
        """Validate YouTube URL and extract video ID."""
        
        result = cls.validate_url(url, cls.ALLOWED_DOMAINS['youtube'])
        
        # Extract YouTube video ID
        youtube_patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/v/([a-zA-Z0-9_-]{11})'
        ]
        
        video_id = None
        for pattern in youtube_patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                break
        
        if not video_id:
            raise ValidationError("Could not extract YouTube video ID from URL")
        
        result['video_id'] = video_id
        return result


class UserInputValidator:
    """Validator for user inputs."""
    
    @staticmethod
    def validate_email(email: str) -> str:
        """Validate email address."""
        
        if not email:
            raise ValidationError("Email cannot be empty")
        
        try:
            # Use email-validator library
            valid = validate_email(email)
            return valid.email
        except EmailNotValidError as e:
            raise ValidationError(f"Invalid email address: {str(e)}")
    
    @staticmethod
    def validate_password(password: str) -> str:
        """Validate password strength."""
        
        if not password:
            raise ValidationError("Password cannot be empty")
        
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")
        
        if len(password) > 128:
            raise ValidationError("Password must be less than 128 characters")
        
        # Check for required character types
        has_upper = re.search(r'[A-Z]', password)
        has_lower = re.search(r'[a-z]', password)
        has_digit = re.search(r'\d', password)
        
        missing_types = []
        if not has_upper:
            missing_types.append("uppercase letter")
        if not has_lower:
            missing_types.append("lowercase letter")
        if not has_digit:
            missing_types.append("number")
        
        if missing_types:
            raise ValidationError(
                f"Password must contain: {', '.join(missing_types)}",
                details={"missing_requirements": missing_types}
            )
        
        return password
    
    @staticmethod
    def validate_username(username: str) -> str:
        """Validate username format."""
        
        if not username:
            raise ValidationError("Username cannot be empty")
        
        if len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long")
        
        if len(username) > 30:
            raise ValidationError("Username must be less than 30 characters")
        
        # Allow letters, numbers, underscores, and hyphens
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            raise ValidationError("Username can only contain letters, numbers, underscores, and hyphens")
        
        return username.lower()
    
    @staticmethod
    def validate_name(name: str, field_name: str = "Name") -> str:
        """Validate person name."""
        
        if not name:
            raise ValidationError(f"{field_name} cannot be empty")
        
        name = TextSanitizer.sanitize_text(name, max_length=50)
        
        if len(name) < 1:
            raise ValidationError(f"{field_name} cannot be empty after sanitization")
        
        # Allow letters, spaces, hyphens, and apostrophes
        if not re.match(r"^[a-zA-Z\s\-']+$", name):
            raise ValidationError(f"{field_name} can only contain letters, spaces, hyphens, and apostrophes")
        
        return name.title()


class APIParameterValidator:
    """Validator for API parameters."""
    
    @staticmethod
    def validate_pagination(page: int = 1, limit: int = 20) -> Dict[str, int]:
        """Validate pagination parameters."""
        
        if page < 1:
            raise ValidationError("Page number must be at least 1")
        
        if page > 1000:
            raise ValidationError("Page number cannot exceed 1000")
        
        if limit < 1:
            raise ValidationError("Limit must be at least 1")
        
        if limit > 100:
            raise ValidationError("Limit cannot exceed 100")
        
        return {"page": page, "limit": limit}
    
    @staticmethod
    def validate_sort_params(sort_by: str, allowed_fields: List[str], sort_order: str = "asc") -> Dict[str, str]:
        """Validate sorting parameters."""
        
        if sort_by not in allowed_fields:
            raise ValidationError(
                f"Invalid sort field: {sort_by}",
                details={"allowed_fields": allowed_fields}
            )
        
        if sort_order.lower() not in ["asc", "desc"]:
            raise ValidationError("Sort order must be 'asc' or 'desc'")
        
        return {"sort_by": sort_by, "sort_order": sort_order.lower()}
    
    @staticmethod
    def validate_date_range(start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Optional[datetime]]:
        """Validate date range parameters."""
        
        parsed_start = None
        parsed_end = None
        
        if start_date:
            try:
                parsed_start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except ValueError:
                raise ValidationError("Invalid start_date format. Use ISO 8601 format.")
        
        if end_date:
            try:
                parsed_end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except ValueError:
                raise ValidationError("Invalid end_date format. Use ISO 8601 format.")
        
        if parsed_start and parsed_end and parsed_start > parsed_end:
            raise ValidationError("start_date cannot be after end_date")
        
        return {"start_date": parsed_start, "end_date": parsed_end}


# Pydantic models for request validation
class UserRegistrationRequest(BaseModel):
    """Request model for user registration."""
    
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    username: Optional[str] = Field(None, description="Username")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    
    @validator('email')
    def validate_email_field(cls, v):
        return UserInputValidator.validate_email(v)
    
    @validator('password')
    def validate_password_field(cls, v):
        return UserInputValidator.validate_password(v)
    
    @validator('username')
    def validate_username_field(cls, v):
        if v:
            return UserInputValidator.validate_username(v)
        return v
    
    @validator('first_name')
    def validate_first_name_field(cls, v):
        if v:
            return UserInputValidator.validate_name(v, "First name")
        return v
    
    @validator('last_name')
    def validate_last_name_field(cls, v):
        if v:
            return UserInputValidator.validate_name(v, "Last name")
        return v


class ContentUploadRequest(BaseModel):
    """Request model for content upload."""
    
    title: Optional[str] = Field(None, description="Content title")
    description: Optional[str] = Field(None, description="Content description")
    content_type: str = Field(..., description="Type of content")
    
    @validator('title')
    def validate_title_field(cls, v):
        if v:
            return TextSanitizer.sanitize_text(v, max_length=200)
        return v
    
    @validator('description')
    def validate_description_field(cls, v):
        if v:
            return TextSanitizer.sanitize_html(v, allow_html=True)
        return v
    
    @validator('content_type')
    def validate_content_type_field(cls, v):
        allowed_types = ['pdf', 'document', 'video', 'audio', 'url']
        if v not in allowed_types:
            raise ValueError(f"Content type must be one of: {allowed_types}")
        return v