"""IAM permissions helper for AWS services."""

import boto3
from typing import Dict, List, Any
from botocore.exceptions import ClientError
import logging

from ..config import settings

logger = logging.getLogger(__name__)


class IAMHelper:
    """Helper class for managing IAM permissions and roles."""
    
    def __init__(self):
        self.iam_client = boto3.client('iam', region_name=settings.aws_region)
        self.sts_client = boto3.client('sts', region_name=settings.aws_region)
    
    async def check_bedrock_permissions(self) -> Dict[str, Any]:
        """Check if current credentials have Bedrock permissions."""
        try:
            # Get current identity
            identity = self.sts_client.get_caller_identity()
            
            # Try to list foundation models (requires bedrock:ListFoundationModels)
            bedrock_client = boto3.client('bedrock', region_name=settings.aws_region)
            bedrock_client.list_foundation_models()
            
            return {
                'has_permissions': True,
                'identity': identity,
                'services': ['bedrock:ListFoundationModels', 'bedrock:InvokeModel']
            }
            
        except ClientError as e:
            return {
                'has_permissions': False,
                'error': str(e),
                'required_permissions': [
                    'bedrock:ListFoundationModels',
                    'bedrock:InvokeModel',
                    'bedrock:GetFoundationModel'
                ]
            }
    
    async def check_textract_permissions(self) -> Dict[str, Any]:
        """Check if current credentials have Textract permissions."""
        try:
            textract_client = boto3.client('textract', region_name=settings.aws_region)
            # Try to list jobs - this is a safe operation
            try:
                textract_client.list_document_analysis_jobs(MaxResults=1)
            except AttributeError:
                # Fallback for older boto3 versions
                pass
            
            return {
                'has_permissions': True,
                'services': ['textract:StartDocumentTextDetection', 'textract:GetDocumentTextDetection']
            }
            
        except ClientError as e:
            return {
                'has_permissions': False,
                'error': str(e),
                'required_permissions': [
                    'textract:StartDocumentTextDetection',
                    'textract:GetDocumentTextDetection',
                    'textract:StartDocumentAnalysis',
                    'textract:GetDocumentAnalysis'
                ]
            }
    
    async def check_transcribe_permissions(self) -> Dict[str, Any]:
        """Check if current credentials have Transcribe permissions."""
        try:
            transcribe_client = boto3.client('transcribe', region_name=settings.aws_region)
            # Try to list transcription jobs - this is a safe operation
            transcribe_client.list_transcription_jobs(MaxResults=1)
            
            return {
                'has_permissions': True,
                'services': ['transcribe:StartTranscriptionJob', 'transcribe:GetTranscriptionJob']
            }
            
        except ClientError as e:
            return {
                'has_permissions': False,
                'error': str(e),
                'required_permissions': [
                    'transcribe:StartTranscriptionJob',
                    'transcribe:GetTranscriptionJob',
                    'transcribe:ListTranscriptionJobs'
                ]
            }
    
    async def check_s3_permissions(self, bucket_name: str) -> Dict[str, Any]:
        """Check if current credentials have S3 permissions for the bucket."""
        try:
            s3_client = boto3.client('s3', region_name=settings.aws_region)
            
            # Test basic operations
            s3_client.head_bucket(Bucket=bucket_name)
            s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
            
            return {
                'has_permissions': True,
                'bucket': bucket_name,
                'services': ['s3:GetObject', 's3:PutObject', 's3:ListBucket']
            }
            
        except ClientError as e:
            return {
                'has_permissions': False,
                'error': str(e),
                'bucket': bucket_name,
                'required_permissions': [
                    's3:GetObject',
                    's3:PutObject',
                    's3:DeleteObject',
                    's3:ListBucket',
                    's3:GetBucketLocation'
                ]
            }
    
    async def get_comprehensive_permissions_check(self) -> Dict[str, Any]:
        """Run comprehensive permissions check for all required services."""
        results = {
            'timestamp': boto3.Session().region_name,
            'region': settings.aws_region,
            'services': {}
        }
        
        # Check each service
        results['services']['bedrock'] = await self.check_bedrock_permissions()
        results['services']['textract'] = await self.check_textract_permissions()
        results['services']['transcribe'] = await self.check_transcribe_permissions()
        results['services']['s3'] = await self.check_s3_permissions(settings.content_bucket)
        
        # Overall status
        all_services_ok = all(
            service_result.get('has_permissions', False) 
            for service_result in results['services'].values()
        )
        
        results['overall_status'] = 'ready' if all_services_ok else 'missing_permissions'
        
        return results
    
    def get_required_policy_document(self) -> Dict[str, Any]:
        """Generate IAM policy document with all required permissions."""
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:ListFoundationModels",
                        "bedrock:GetFoundationModel",
                        "bedrock:InvokeModel"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "textract:StartDocumentTextDetection",
                        "textract:GetDocumentTextDetection",
                        "textract:StartDocumentAnalysis",
                        "textract:GetDocumentAnalysis",
                        "textract:DetectDocumentText"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "transcribe:StartTranscriptionJob",
                        "transcribe:GetTranscriptionJob",
                        "transcribe:ListTranscriptionJobs",
                        "transcribe:CreateVocabulary",
                        "transcribe:GetVocabulary"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject",
                        "s3:ListBucket",
                        "s3:GetBucketLocation"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{settings.content_bucket}",
                        f"arn:aws:s3:::{settings.content_bucket}/*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:Query",
                        "dynamodb:Scan"
                    ],
                    "Resource": [
                        f"arn:aws:dynamodb:{settings.aws_region}:{settings.aws_account_id}:table/SnapStudy-*"
                    ]
                }
            ]
        }


# Global helper instance
iam_helper = IAMHelper()