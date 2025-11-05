"""
Utility functions for Lambda
"""

import logging
import boto3

logger = logging.getLogger(__name__)


def download_file_from_s3(bucket: str, key: str, local_path: str) -> None:
    """
    Download a file from S3 to local filesystem

    Args:
        bucket: S3 bucket name
        key: S3 object key
        local_path: Local file path to save to
    """
    s3_client = boto3.client('s3')

    logger.info(f"Downloading s3://{bucket}/{key} to {local_path}")

    try:
        s3_client.download_file(bucket, key, local_path)
        logger.info(f"Successfully downloaded {key}")
    except Exception as e:
        logger.error(f"Error downloading {key}: {e}")
        raise
