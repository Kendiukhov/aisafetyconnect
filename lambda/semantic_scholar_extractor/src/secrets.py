"""
AWS Secrets Manager helper
"""

import json
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def get_secret_value(secret_arn: str) -> str:
    """
    Retrieve secret value from AWS Secrets Manager

    Args:
        secret_arn: ARN of the secret

    Returns:
        Secret string value

    Raises:
        Exception if secret cannot be retrieved
    """
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager')

    try:
        response = client.get_secret_value(SecretId=secret_arn)

        # Secret can be string or binary
        if 'SecretString' in response:
            secret = response['SecretString']
            try:
                # Try to parse as JSON
                secret_dict = json.loads(secret)
                # If it's a dict with 'api_key' field, return that
                if isinstance(secret_dict, dict) and 'api_key' in secret_dict:
                    return secret_dict['api_key']
                # Otherwise return the whole JSON string
                return secret
            except json.JSONDecodeError:
                # Not JSON, return as-is
                return secret
        else:
            # Binary secret
            return response['SecretBinary'].decode('utf-8')

    except ClientError as e:
        logger.error(f"Error retrieving secret {secret_arn}: {e}")
        raise
