"""AWS Textract service for PDF text extraction."""

import boto3
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError
import logging
import time

from ..config import settings

logger = logging.getLogger(__name__)


class TextractService:
    """Service for AWS Textract operations."""
    
    def __init__(self):
        self.textract_client = boto3.client('textract', region_name=settings.aws_region)
        self.s3_client = boto3.client('s3', region_name=settings.aws_region)
    
    async def extract_text_from_s3(self, bucket_name: str, object_key: str) -> Dict[str, Any]:
        """Extract text from a PDF stored in S3."""
        try:
            # Start document text detection job
            response = self.textract_client.start_document_text_detection(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': bucket_name,
                        'Name': object_key
                    }
                }
            )
            
            job_id = response['JobId']
            logger.info(f"Started Textract job: {job_id}")
            
            # Poll for job completion
            max_attempts = 60  # 5 minutes max
            attempt = 0
            
            while attempt < max_attempts:
                job_status = self.textract_client.get_document_text_detection(JobId=job_id)
                status = job_status['JobStatus']
                
                if status == 'SUCCEEDED':
                    break
                elif status == 'FAILED':
                    error_msg = job_status.get('StatusMessage', 'Unknown error')
                    raise ValueError(f"Textract job failed: {error_msg}")
                
                # Wait before next check
                time.sleep(5)
                attempt += 1
            
            if attempt >= max_attempts:
                raise ValueError("Textract job timed out")
            
            # Get all pages of results
            extracted_text = []
            next_token = None
            
            while True:
                if next_token:
                    result = self.textract_client.get_document_text_detection(
                        JobId=job_id,
                        NextToken=next_token
                    )
                else:
                    result = self.textract_client.get_document_text_detection(JobId=job_id)
                
                # Extract text from blocks
                for block in result.get('Blocks', []):
                    if block['BlockType'] == 'LINE':
                        extracted_text.append(block['Text'])
                
                next_token = result.get('NextToken')
                if not next_token:
                    break
            
            full_text = '\n'.join(extracted_text)
            
            return {
                'text': full_text,
                'page_count': len(extracted_text),
                'word_count': len(full_text.split()),
                'character_count': len(full_text),
                'job_id': job_id,
                'extraction_confidence': self._calculate_confidence(result.get('Blocks', []))
            }
            
        except ClientError as e:
            logger.error(f"Textract API error: {e}")
            raise ValueError(f"Textract API error: {e.response['Error']['Message']}")
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            raise ValueError(f"Error extracting text: {str(e)}")
    
    async def extract_text_from_bytes(self, document_bytes: bytes) -> Dict[str, Any]:
        """Extract text from PDF bytes (for smaller documents < 5MB)."""
        try:
            # For synchronous processing of smaller documents
            response = self.textract_client.detect_document_text(
                Document={'Bytes': document_bytes}
            )
            
            # Extract text from blocks
            extracted_text = []
            for block in response.get('Blocks', []):
                if block['BlockType'] == 'LINE':
                    extracted_text.append(block['Text'])
            
            full_text = '\n'.join(extracted_text)
            
            return {
                'text': full_text,
                'page_count': 1,  # Estimated for sync processing
                'word_count': len(full_text.split()),
                'character_count': len(full_text),
                'extraction_confidence': self._calculate_confidence(response.get('Blocks', []))
            }
            
        except ClientError as e:
            logger.error(f"Textract API error: {e}")
            raise ValueError(f"Textract API error: {e.response['Error']['Message']}")
        except Exception as e:
            logger.error(f"Error extracting text from bytes: {e}")
            raise ValueError(f"Error extracting text: {str(e)}")
    
    async def extract_tables_from_s3(self, bucket_name: str, object_key: str) -> Dict[str, Any]:
        """Extract tables from a PDF stored in S3."""
        try:
            # Start document analysis job for tables
            response = self.textract_client.start_document_analysis(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': bucket_name,
                        'Name': object_key
                    }
                },
                FeatureTypes=['TABLES']
            )
            
            job_id = response['JobId']
            logger.info(f"Started Textract table analysis job: {job_id}")
            
            # Poll for job completion
            max_attempts = 60
            attempt = 0
            
            while attempt < max_attempts:
                job_status = self.textract_client.get_document_analysis(JobId=job_id)
                status = job_status['JobStatus']
                
                if status == 'SUCCEEDED':
                    break
                elif status == 'FAILED':
                    error_msg = job_status.get('StatusMessage', 'Unknown error')
                    raise ValueError(f"Textract table analysis failed: {error_msg}")
                
                time.sleep(5)
                attempt += 1
            
            if attempt >= max_attempts:
                raise ValueError("Textract table analysis timed out")
            
            # Extract tables
            tables = []
            blocks = job_status.get('Blocks', [])
            
            # Find table blocks
            table_blocks = [block for block in blocks if block['BlockType'] == 'TABLE']
            
            for table_block in table_blocks:
                table_data = self._extract_table_data(table_block, blocks)
                tables.append(table_data)
            
            return {
                'tables': tables,
                'table_count': len(tables),
                'job_id': job_id
            }
            
        except ClientError as e:
            logger.error(f"Textract table analysis error: {e}")
            raise ValueError(f"Textract API error: {e.response['Error']['Message']}")
        except Exception as e:
            logger.error(f"Error extracting tables: {e}")
            raise ValueError(f"Error extracting tables: {str(e)}")
    
    def _calculate_confidence(self, blocks: List[Dict[str, Any]]) -> float:
        """Calculate average confidence score from Textract blocks."""
        if not blocks:
            return 0.0
        
        confidences = []
        for block in blocks:
            if 'Confidence' in block:
                confidences.append(block['Confidence'])
        
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def _extract_table_data(self, table_block: Dict[str, Any], all_blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract structured data from a table block."""
        # This is a simplified table extraction
        # In a production system, you'd want more sophisticated table parsing
        
        table_data = {
            'rows': [],
            'columns': 0,
            'confidence': table_block.get('Confidence', 0.0)
        }
        
        # For now, return basic table structure
        # Full implementation would parse cell relationships
        if 'Relationships' in table_block:
            for relationship in table_block['Relationships']:
                if relationship['Type'] == 'CHILD':
                    # Process child cells
                    pass
        
        return table_data
    
    async def get_supported_formats(self) -> List[str]:
        """Get list of supported document formats."""
        return [
            'application/pdf',
            'image/jpeg',
            'image/png',
            'image/tiff'
        ]
    
    async def validate_document(self, file_size: int, content_type: str) -> Dict[str, Any]:
        """Validate document for Textract processing."""
        supported_formats = await self.get_supported_formats()
        
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'processing_method': 'sync'  # or 'async'
        }
        
        # Check file size
        max_sync_size = 5 * 1024 * 1024  # 5MB
        max_async_size = 500 * 1024 * 1024  # 500MB
        
        if file_size > max_async_size:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"File size {file_size} exceeds maximum limit of {max_async_size} bytes")
        elif file_size > max_sync_size:
            validation_result['processing_method'] = 'async'
            validation_result['warnings'].append("Large file will be processed asynchronously")
        
        # Check content type
        if content_type not in supported_formats:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Unsupported format: {content_type}")
        
        return validation_result


# Global service instance
textract_service = TextractService()