#!/usr/bin/env python3
"""
Local test script for Lambda handler

This allows you to test the Lambda function locally before deploying to AWS.

Usage:
    uv run test_local.py
"""

import os
import json
from handler import lambda_handler

# Mock context object
class MockContext:
    """Mock Lambda context"""
    def __init__(self):
        self.function_name = "semantic-scholar-extractor"
        self.function_version = "$LATEST"
        self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789:function:semantic-scholar-extractor"
        self.memory_limit_in_mb = 2048
        self.aws_request_id = "test-request-id"
        self.log_group_name = "/aws/lambda/semantic-scholar-extractor"
        self.log_stream_name = "test-stream"

    def get_remaining_time_in_millis(self):
        return 900000  # 15 minutes


def test_small_extraction():
    """
    Test with a small extraction (2 areas, 100 papers, no secondary)

    This should complete in a few minutes locally.
    """
    # Set environment variables (simulate Lambda environment)
    os.environ['SECRET_ARN'] = 'arn:aws:secretsmanager:us-east-1:123:secret:test'
    os.environ['S3_BUCKET'] = 'aisafetyconnect-raw-dev'
    os.environ['S3_PREFIX'] = 'raw_data/snapshots/'
    os.environ['TERMS_JSON_S3_KEY'] = 'config/terms.json'

    # NOTE: This test requires:
    # 1. Semantic Scholar API key set (will try to read from Secrets Manager)
    # 2. AWS credentials configured
    # 3. terms.json uploaded to S3

    # If you don't have AWS configured yet, modify handler.py to skip S3/Secrets Manager
    # and use local files instead

    event = {
        "extraction_date": "2024-11-01",
        "year_from": 2020,
        "papers_per_query": 100,
        "min_citations": 10,
        "include_secondary": False,
        "max_workers": 2
    }

    context = MockContext()

    print("="*60)
    print("RUNNING LOCAL TEST")
    print("="*60)
    print(f"Event: {json.dumps(event, indent=2)}")
    print("="*60)

    try:
        result = lambda_handler(event, context)

        print("\n" + "="*60)
        print("TEST RESULT")
        print("="*60)
        print(json.dumps(result, indent=2))

        if result['statusCode'] == 200:
            print("\n✅ Test PASSED")
        else:
            print("\n❌ Test FAILED")

    except Exception as e:
        print(f"\n❌ Test FAILED with exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("""
    ⚠️  WARNING: This test requires:

    1. AWS credentials configured (aws configure)
    2. Semantic Scholar API key in Secrets Manager
    3. terms.json uploaded to S3

    If you don't have these yet, this test will FAIL.

    To test without AWS:
    - Modify handler.py to use local files
    - Or deploy to AWS first and test there

    Press Ctrl+C to cancel, or Enter to continue...
    """)

    try:
        input()
    except KeyboardInterrupt:
        print("\n\nTest cancelled.")
        exit(0)

    test_small_extraction()
