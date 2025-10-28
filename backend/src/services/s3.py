"""AWS S3 service for file storage and management."""

import boto3
from typing import Dict, List, Any, Optional, BinaryIO
from botocore.exceptions import ClientError
import logging
import uuid
from datetime import datetime, timedelta
import mimetypes

from ..config import settings
from ..utils.aws_client import get_boto3_client

logger = logging.getLogger(__name__)


class S3Service:
    """Service for AWS S3 operations."""

    def __init__(self):
        self.s3_client = get_boto3_client('s3')
        self.bucket_name = settings.content_bucket

    def ensure_bucket_exists(self) -> bool:
        """
        Check if the S3 bucket exists, and create it if it doesn't.

        Returns:
            True if bucket exists or was created successfully
        """
        try:
            # Try to get bucket location (this will fail if bucket doesn't exist)
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 bucket {self.bucket_name} already exists")
            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']

            # If bucket doesn't exist, create it
            if error_code == '404':
                try:
                    logger.info(f"Creating S3 bucket: {self.bucket_name}")

                    # Create bucket with region-specific configuration
                    region = settings.aws_region
                    if region == 'us-east-1':
                        # us-east-1 doesn't require LocationConstraint
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': region}
                        )

                    # Enable server-side encryption by default
                    self.s3_client.put_bucket_encryption(
                        Bucket=self.bucket_name,
                        ServerSideEncryptionConfiguration={
                            'Rules': [
                                {
                                    'ApplyServerSideEncryptionByDefault': {
                                        'SSEAlgorithm': 'AES256'
                                    },
                                    'BucketKeyEnabled': True
                                }
                            ]
                        }
                    )

                    # Enable versioning for data protection
                    self.s3_client.put_bucket_versioning(
                        Bucket=self.bucket_name,
                        VersioningConfiguration={'Status': 'Enabled'}
                    )

                    # Block public access by default
                    self.s3_client.put_public_access_block(
                        Bucket=self.bucket_name,
                        PublicAccessBlockConfiguration={
                            'BlockPublicAcls': True,
                            'IgnorePublicAcls': True,
                            'BlockPublicPolicy': True,
                            'RestrictPublicBuckets': True
                        }
                    )

                    # Add lifecycle policy to manage cache data
                    self.s3_client.put_bucket_lifecycle_configuration(
                        Bucket=self.bucket_name,
                        LifecycleConfiguration={
                            'Rules': [
                                {
                                    'Id': 'DeleteOldCacheData',
                                    'Status': 'Enabled',
                                    'Filter': {'Prefix': 'cache/'},
                                    'Expiration': {'Days': 30},
                                    'NoncurrentVersionExpiration': {'NoncurrentDays': 7}
                                }
                            ]
                        }
                    )

                    logger.info(f"Successfully created S3 bucket: {self.bucket_name}")
                    return True

                except ClientError as create_error:
                    logger.error(f"Failed to create S3 bucket: {create_error}")
                    raise ValueError(f"Failed to create S3 bucket: {create_error.response['Error']['Message']}")
            else:
                # Other errors (like permission denied)
                logger.error(f"Error accessing S3 bucket: {e}")
                raise ValueError(f"Error accessing S3 bucket: {e.response['Error']['Message']}")

        except Exception as e:
            logger.error(f"Unexpected error ensuring bucket exists: {e}")
            raise ValueError(f"Unexpected error: {str(e)}")
    
    async def upload_file(
        self, 
        file_content: bytes, 
        file_name: str,
        user_id: str,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload file to S3 and return file information."""
        try:
            # Generate unique file key
            file_extension = file_name.split('.')[-1] if '.' in file_name else ''
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}" if file_extension else uuid.uuid4().hex
            object_key = f"uploads/{user_id}/{unique_filename}"
            
            # Determine content type if not provided
            if not content_type:
                content_type, _ = mimetypes.guess_type(file_name)
                if not content_type:
                    content_type = 'application/octet-stream'
            
            # Upload file
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=file_content,
                ContentType=content_type,
                Metadata={
                    'original_filename': file_name,
                    'user_id': user_id,
                    'upload_timestamp': datetime.utcnow().isoformat()
                },
                ServerSideEncryption='AES256'
            )
            
            # Get file info
            file_info = await self.get_file_info(object_key)
            
            logger.info(f"File uploaded successfully: {object_key}")
            
            return {
                'object_key': object_key,
                'bucket_name': self.bucket_name,
                'file_size': file_info['file_size'],
                'content_type': content_type,
                'upload_url': f"s3://{self.bucket_name}/{object_key}",
                'original_filename': file_name,
                'upload_timestamp': datetime.utcnow().isoformat()
            }
            
        except ClientError as e:
            logger.error(f"S3 upload error: {e}")
            raise ValueError(f"S3 upload error: {e.response['Error']['Message']}")
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise ValueError(f"Error uploading file: {str(e)}")
    
    async def download_file(self, object_key: str) -> Dict[str, Any]:
        """Download file from S3."""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            file_content = response['Body'].read()
            
            return {
                'content': file_content,
                'content_type': response.get('ContentType'),
                'file_size': response.get('ContentLength'),
                'last_modified': response.get('LastModified'),
                'metadata': response.get('Metadata', {})
            }
            
        except ClientError as e:
            logger.error(f"S3 download error: {e}")
            raise ValueError(f"S3 download error: {e.response['Error']['Message']}")
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            raise ValueError(f"Error downloading file: {str(e)}")
    
    async def get_file_info(self, object_key: str) -> Dict[str, Any]:
        """Get file metadata without downloading content."""
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            return {
                'object_key': object_key,
                'bucket_name': self.bucket_name,
                'file_size': response.get('ContentLength'),
                'content_type': response.get('ContentType'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag'),
                'metadata': response.get('Metadata', {}),
                'server_side_encryption': response.get('ServerSideEncryption')
            }
            
        except ClientError as e:
            logger.error(f"S3 head object error: {e}")
            raise ValueError(f"S3 error: {e.response['Error']['Message']}")
    
    async def delete_file(self, object_key: str) -> bool:
        """Delete file from S3."""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            logger.info(f"File deleted successfully: {object_key}")
            return True
            
        except ClientError as e:
            logger.error(f"S3 delete error: {e}")
            raise ValueError(f"S3 delete error: {e.response['Error']['Message']}")
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            raise ValueError(f"Error deleting file: {str(e)}")
    
    async def generate_presigned_url(
        self, 
        object_key: str, 
        expiration: int = 3600,
        http_method: str = 'GET'
    ) -> str:
        """Generate presigned URL for file access."""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object' if http_method == 'GET' else 'put_object',
                Params={'Bucket': self.bucket_name, 'Key': object_key},
                ExpiresIn=expiration
            )
            
            return url
            
        except ClientError as e:
            logger.error(f"Presigned URL error: {e}")
            raise ValueError(f"Presigned URL error: {e.response['Error']['Message']}")
    
    async def generate_upload_presigned_url(
        self,
        user_id: str,
        file_name: str,
        content_type: str,
        expiration: int = 3600
    ) -> Dict[str, Any]:
        """Generate presigned URL for direct file upload."""
        try:
            # Generate unique object key
            file_extension = file_name.split('.')[-1] if '.' in file_name else ''
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}" if file_extension else uuid.uuid4().hex
            object_key = f"uploads/{user_id}/{unique_filename}"
            
            # Generate presigned POST URL
            presigned_post = self.s3_client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=object_key,
                Fields={
                    'Content-Type': content_type,
                    'x-amz-meta-original-filename': file_name,
                    'x-amz-meta-user-id': user_id,
                    'x-amz-meta-upload-timestamp': datetime.utcnow().isoformat()
                },
                Conditions=[
                    {'Content-Type': content_type},
                    ['content-length-range', 1, 500 * 1024 * 1024]  # 500MB max
                ],
                ExpiresIn=expiration
            )
            
            return {
                'upload_url': presigned_post['url'],
                'fields': presigned_post['fields'],
                'object_key': object_key,
                'expires_in': expiration
            }
            
        except ClientError as e:
            logger.error(f"Presigned upload URL error: {e}")
            raise ValueError(f"Presigned upload URL error: {e.response['Error']['Message']}")
    
    async def list_user_files(self, user_id: str, max_keys: int = 100) -> List[Dict[str, Any]]:
        """List files for a specific user."""
        try:
            prefix = f"uploads/{user_id}/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            files = []
            for obj in response.get('Contents', []):
                file_info = {
                    'object_key': obj['Key'],
                    'file_size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag']
                }
                
                # Get additional metadata
                try:
                    head_response = self.s3_client.head_object(
                        Bucket=self.bucket_name,
                        Key=obj['Key']
                    )
                    file_info.update({
                        'content_type': head_response.get('ContentType'),
                        'metadata': head_response.get('Metadata', {})
                    })
                except ClientError:
                    # Skip if can't get metadata
                    pass
                
                files.append(file_info)
            
            return files
            
        except ClientError as e:
            logger.error(f"S3 list objects error: {e}")
            raise ValueError(f"S3 list error: {e.response['Error']['Message']}")
    
    async def copy_file(self, source_key: str, destination_key: str) -> Dict[str, Any]:
        """Copy file within S3 bucket."""
        try:
            copy_source = {
                'Bucket': self.bucket_name,
                'Key': source_key
            }
            
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=destination_key,
                ServerSideEncryption='AES256'
            )
            
            # Get info about copied file
            file_info = await self.get_file_info(destination_key)
            
            logger.info(f"File copied: {source_key} -> {destination_key}")
            
            return file_info
            
        except ClientError as e:
            logger.error(f"S3 copy error: {e}")
            raise ValueError(f"S3 copy error: {e.response['Error']['Message']}")
    
    async def get_bucket_info(self) -> Dict[str, Any]:
        """Get information about the S3 bucket."""
        try:
            # Get bucket location
            location_response = self.s3_client.get_bucket_location(Bucket=self.bucket_name)

            # Get bucket versioning
            versioning_response = self.s3_client.get_bucket_versioning(Bucket=self.bucket_name)

            # Get bucket encryption
            try:
                encryption_response = self.s3_client.get_bucket_encryption(Bucket=self.bucket_name)
                encryption_config = encryption_response.get('ServerSideEncryptionConfiguration')
            except ClientError:
                encryption_config = None

            return {
                'bucket_name': self.bucket_name,
                'region': location_response.get('LocationConstraint') or 'us-east-1',
                'versioning_status': versioning_response.get('Status', 'Disabled'),
                'encryption_enabled': encryption_config is not None,
                'encryption_config': encryption_config
            }

        except ClientError as e:
            logger.error(f"S3 bucket info error: {e}")
            raise ValueError(f"S3 bucket info error: {e.response['Error']['Message']}")

    async def cache_lesson_data(
        self,
        lesson_id: str,
        data_type: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Cache lesson-related data (micro-lessons, quizzes) to S3.

        Args:
            lesson_id: The lesson ID
            data_type: Type of data ('micro_lessons' or 'quiz')
            data: The data to cache

        Returns:
            Cache metadata
        """
        try:
            import json

            # Create cache key
            object_key = f"cache/lessons/{lesson_id}/{data_type}.json"

            # Convert data to JSON
            json_data = json.dumps(data, indent=2)

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=json_data.encode('utf-8'),
                ContentType='application/json',
                Metadata={
                    'lesson_id': lesson_id,
                    'data_type': data_type,
                    'cached_at': datetime.utcnow().isoformat()
                },
                ServerSideEncryption='AES256'
            )

            logger.info(f"Cached {data_type} for lesson {lesson_id} to S3")

            return {
                'object_key': object_key,
                'lesson_id': lesson_id,
                'data_type': data_type,
                'cached_at': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to cache lesson data: {e}")
            raise ValueError(f"Failed to cache lesson data: {str(e)}")

    async def get_cached_lesson_data(
        self,
        lesson_id: str,
        data_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached lesson data from S3.

        Args:
            lesson_id: The lesson ID
            data_type: Type of data ('micro_lessons' or 'quiz')

        Returns:
            Cached data or None if not found
        """
        try:
            import json

            object_key = f"cache/lessons/{lesson_id}/{data_type}.json"

            # Try to get from S3
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=object_key
            )

            json_data = response['Body'].read().decode('utf-8')
            data = json.loads(json_data)

            logger.info(f"Retrieved cached {data_type} for lesson {lesson_id} from S3")

            return data

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                # Cache miss is normal, don't log as info to reduce noise
                logger.debug(f"No cached {data_type} found for lesson {lesson_id}")
                return None
            else:
                logger.error(f"Error retrieving cached data: {e}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving cached data: {e}")
            return None

    def check_cache_exists(self, lesson_id: str, data_type: str) -> bool:
        """
        Quickly check if cached data exists without retrieving it.
        Uses head_object which is faster than get_object.

        Args:
            lesson_id: The lesson ID
            data_type: Type of data ('micro_lessons' or 'quiz')

        Returns:
            True if cache exists, False otherwise
        """
        try:
            object_key = f"cache/lessons/{lesson_id}/{data_type}.json"

            # Use head_object for fast existence check
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )

            return True

        except ClientError as e:
            if e.response['Error']['Code'] in ['NoSuchKey', '404']:
                return False
            else:
                logger.error(f"Error checking cache existence: {e}")
                return False
        except Exception as e:
            logger.error(f"Error checking cache existence: {e}")
            return False

    async def clear_lesson_cache(self, lesson_id: str) -> bool:
        """
        Clear all cached data for a lesson.

        Args:
            lesson_id: The lesson ID

        Returns:
            True if successful
        """
        try:
            prefix = f"cache/lessons/{lesson_id}/"

            # List all objects with this prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            # Delete all objects
            objects_to_delete = []
            for obj in response.get('Contents', []):
                objects_to_delete.append({'Key': obj['Key']})

            if objects_to_delete:
                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': objects_to_delete}
                )
                logger.info(f"Cleared cache for lesson {lesson_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to clear lesson cache: {e}")
            return False
    
    async def validate_file_upload(
        self, 
        file_size: int, 
        content_type: str,
        file_name: str
    ) -> Dict[str, Any]:
        """Validate file for upload."""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check file size (500MB limit)
        max_file_size = 500 * 1024 * 1024  # 500MB
        
        if file_size > max_file_size:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"File size {file_size} exceeds maximum limit of {max_file_size} bytes")
        
        # Check for potentially dangerous file types
        dangerous_extensions = ['.exe', '.bat', '.cmd', '.scr', '.pif', '.com']
        file_extension = '.' + file_name.split('.')[-1].lower() if '.' in file_name else ''
        
        if file_extension in dangerous_extensions:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"File type {file_extension} is not allowed")
        
        # Warn about large files
        if file_size > 50 * 1024 * 1024:  # 50MB
            validation_result['warnings'].append("Large file may take longer to process")
        
        return validation_result


# Global service instance
s3_service = S3Service()