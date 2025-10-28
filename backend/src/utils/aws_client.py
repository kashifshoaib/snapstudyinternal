"""AWS client utility for creating boto3 clients with profile support."""

import boto3
import logging
from typing import Any
from ..config import settings

logger = logging.getLogger(__name__)


def get_boto3_session() -> boto3.Session:
    """
    Create a boto3 Session with optional AWS profile support.

    Returns:
        boto3.Session: Configured boto3 session
    """
    session_kwargs = {
        'region_name': settings.aws_region
    }

    # Add profile if specified in environment
    if settings.aws_profile:
        session_kwargs['profile_name'] = settings.aws_profile
        logger.info(f"Using AWS profile: {settings.aws_profile}")
    else:
        logger.debug("Using default AWS credentials (no profile specified)")

    return boto3.Session(**session_kwargs)


def get_boto3_client(service_name: str, **kwargs) -> Any:
    """
    Create a boto3 client with optional AWS profile support.

    Args:
        service_name: AWS service name (e.g., 's3', 'dynamodb', 'bedrock-runtime')
        **kwargs: Additional arguments to pass to boto3.client()

    Returns:
        boto3 client for the specified service
    """
    session = get_boto3_session()

    # Merge region_name with kwargs if not already specified
    if 'region_name' not in kwargs:
        kwargs['region_name'] = settings.aws_region

    client = session.client(service_name, **kwargs)
    logger.debug(f"Created boto3 client for service: {service_name}")

    return client


def get_boto3_resource(service_name: str, **kwargs) -> Any:
    """
    Create a boto3 resource with optional AWS profile support.

    Args:
        service_name: AWS service name (e.g., 'dynamodb', 's3')
        **kwargs: Additional arguments to pass to boto3.resource()

    Returns:
        boto3 resource for the specified service
    """
    session = get_boto3_session()

    # Merge region_name with kwargs if not already specified
    if 'region_name' not in kwargs:
        kwargs['region_name'] = settings.aws_region

    resource = session.resource(service_name, **kwargs)
    logger.debug(f"Created boto3 resource for service: {service_name}")

    return resource
