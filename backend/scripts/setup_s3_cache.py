#!/usr/bin/env python3
"""
Standalone script to ensure S3 cache bucket exists.

This script can be run independently to set up the S3 bucket for caching
before starting the application.

Usage:
    python scripts/setup_s3_cache.py
"""

import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

import logging
import asyncio
from src.config import settings
from src.services.s3 import s3_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to ensure S3 cache bucket exists."""
    logger.info("=" * 60)
    logger.info("S3 Cache Bucket Setup Script")
    logger.info("=" * 60)

    logger.info(f"Target bucket: {settings.content_bucket}")
    logger.info(f"AWS Region: {settings.aws_region}")
    if settings.aws_profile:
        logger.info(f"AWS Profile: {settings.aws_profile}")

    try:
        # Ensure the bucket exists
        logger.info("\nChecking if S3 bucket exists...")
        bucket_exists = s3_service.ensure_bucket_exists()

        if bucket_exists:
            logger.info("\n✅ SUCCESS: S3 bucket is ready for caching")
            logger.info(f"   Bucket name: {settings.content_bucket}")
            logger.info(f"   Cache path: cache/lessons/")
            logger.info(f"   Lifecycle: Cache items expire after 30 days")
            logger.info(f"   Encryption: AES256 server-side encryption enabled")
            logger.info(f"   Versioning: Enabled for data protection")
            logger.info(f"   Public Access: Blocked")

            logger.info("\n" + "=" * 60)
            logger.info("Setup completed successfully!")
            logger.info("=" * 60)
            return 0
        else:
            logger.error("\n❌ FAILED: Could not verify/create S3 bucket")
            return 1

    except Exception as e:
        logger.error(f"\n❌ ERROR: {str(e)}")
        logger.error("\nPlease check:")
        logger.error("  1. AWS credentials are properly configured")
        logger.error("  2. IAM permissions include s3:CreateBucket, s3:PutBucketEncryption, etc.")
        logger.error("  3. The bucket name is available (if creating new bucket)")
        logger.error("  4. Network connectivity to AWS")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
