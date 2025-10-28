"""AWS health check utility to verify credentials and permissions on startup."""

import logging
from botocore.exceptions import ClientError, NoCredentialsError
from ..config import settings
from .aws_client import get_boto3_client

logger = logging.getLogger(__name__)


async def verify_aws_credentials() -> dict:
    """
    Verify AWS credentials are properly configured and working.

    Returns:
        dict: Status information about AWS credentials
    """
    status = {
        'credentials_valid': False,
        'account_id': None,
        'user_arn': None,
        'profile_used': settings.aws_profile or 'default',
        'region': settings.aws_region,
        'errors': []
    }

    try:
        # Test credentials with STS GetCallerIdentity
        sts_client = get_boto3_client('sts')
        identity = sts_client.get_caller_identity()

        status['credentials_valid'] = True
        status['account_id'] = identity.get('Account')
        status['user_arn'] = identity.get('Arn')

        logger.info(f"✅ AWS credentials verified successfully")
        logger.info(f"   Account: {status['account_id']}")
        logger.info(f"   Identity: {status['user_arn']}")
        logger.info(f"   Region: {status['region']}")
        if settings.aws_profile:
            logger.info(f"   Profile: {settings.aws_profile}")

    except NoCredentialsError:
        error_msg = "No AWS credentials found. Set AWS_PROFILE or configure AWS credentials."
        status['errors'].append(error_msg)
        logger.error(f"❌ {error_msg}")

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))

        if error_code in ['InvalidClientTokenId', 'SignatureDoesNotMatch', 'UnrecognizedClientException']:
            if settings.aws_profile:
                error_msg = f"Invalid AWS credentials for profile '{settings.aws_profile}'. Check ~/.aws/credentials"
            else:
                error_msg = "Invalid AWS credentials. Check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"

        status['errors'].append(f"{error_code}: {error_msg}")
        logger.error(f"❌ AWS credential verification failed: {error_msg}")

    except Exception as e:
        error_msg = f"Unexpected error verifying AWS credentials: {str(e)}"
        status['errors'].append(error_msg)
        logger.error(f"❌ {error_msg}")

    return status


async def verify_bedrock_access() -> dict:
    """
    Verify access to AWS Bedrock service.

    Returns:
        dict: Status information about Bedrock access
    """
    status = {
        'bedrock_accessible': False,
        'model_id': settings.bedrock_model_id,
        'region': settings.bedrock_region,
        'errors': []
    }

    try:
        # Try to list foundation models to verify Bedrock access
        bedrock_client = get_boto3_client('bedrock', region_name=settings.bedrock_region)

        # This is a lightweight call that verifies both credentials and Bedrock permissions
        response = bedrock_client.list_foundation_models(byProvider='amazon')

        status['bedrock_accessible'] = True
        logger.info(f"✅ Bedrock access verified in region {settings.bedrock_region}")

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_msg = e.response.get('Error', {}).get('Message', str(e))

        if error_code == 'AccessDeniedException':
            error_msg = f"No permission to access Bedrock in {settings.bedrock_region}. Check IAM permissions."
        elif error_code == 'UnrecognizedClientException':
            error_msg = "Bedrock service not available in this region or invalid credentials"

        status['errors'].append(f"{error_code}: {error_msg}")
        logger.warning(f"⚠️  Bedrock access check failed: {error_msg}")
        logger.warning(f"   This may cause issues when generating AI content")

    except Exception as e:
        error_msg = f"Unexpected error checking Bedrock access: {str(e)}"
        status['errors'].append(error_msg)
        logger.warning(f"⚠️  {error_msg}")

    return status


async def verify_s3_buckets() -> dict:
    """
    Verify S3 buckets exist and create them if they don't.

    Returns:
        dict: Status information about S3 buckets
    """
    status = {
        's3_buckets_ready': False,
        'buckets': {},
        'errors': []
    }

    # Import here to avoid circular imports
    from ..services.s3 import s3_service

    try:
        # Ensure content bucket exists (this will also be used for cache)
        bucket_exists = s3_service.ensure_bucket_exists()

        status['buckets'][settings.content_bucket] = {
            'exists': bucket_exists,
            'purpose': 'Content storage and cache'
        }

        status['s3_buckets_ready'] = True
        logger.info(f"✅ S3 bucket '{settings.content_bucket}' is ready")

    except Exception as e:
        error_msg = f"Failed to verify/create S3 buckets: {str(e)}"
        status['errors'].append(error_msg)
        logger.error(f"❌ {error_msg}")

    return status


async def run_startup_aws_checks() -> dict:
    """
    Run all AWS-related health checks on startup.

    Returns:
        dict: Combined status from all checks
    """
    logger.info("🔍 Running AWS startup health checks...")

    results = {
        'credentials': await verify_aws_credentials(),
        'bedrock': await verify_bedrock_access(),
        's3': await verify_s3_buckets()
    }

    # Determine overall status
    all_healthy = (
        results['credentials']['credentials_valid'] and
        results['bedrock']['bedrock_accessible'] and
        results['s3']['s3_buckets_ready']
    )

    if all_healthy:
        logger.info("✅ All AWS health checks passed")
    else:
        logger.warning("⚠️  Some AWS health checks failed - application may have limited functionality")

    return results
