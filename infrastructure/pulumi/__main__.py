"""
Pulumi Infrastructure for AI Safety Connect - Semantic Scholar Extractor Lambda

Resources created:
- AWS Secrets Manager secret for Semantic Scholar API key
- IAM role and policies for Lambda
- Lambda function
- CloudWatch Log Group
- S3 bucket object (terms.json upload)
- Optional: EventBridge rule for monthly trigger

To deploy:
    cd infrastructure/pulumi
    pulumi stack init dev
    pulumi config set --secret aisafetyconnect:semantic-scholar-api-key YOUR_API_KEY
    pulumi up
"""

import json
import pulumi
import pulumi_aws as aws
from pathlib import Path

# Configuration
config = pulumi.Config("aisafetyconnect")
semantic_scholar_api_key = config.require_secret("semantic-scholar-api-key")
s3_bucket_name = config.require("s3-bucket")

# Project root paths
project_root = Path(__file__).parent.parent.parent
lambda_code_path = project_root / "lambda" / "semantic_scholar_extractor"
terms_json_path = project_root / "terms.json"

#############################################################################
# 1. AWS Secrets Manager - Store API Key
#############################################################################

semantic_scholar_secret = aws.secretsmanager.Secret(
    "semantic-scholar-api-key",
    name="semantic-scholar-api-key",
    description="API Key for Semantic Scholar API",
    recovery_window_in_days=0,  # Allow immediate deletion (dev only)
)

semantic_scholar_secret_version = aws.secretsmanager.SecretVersion(
    "semantic-scholar-api-key-version",
    secret_id=semantic_scholar_secret.id,
    secret_string=semantic_scholar_api_key,
)

#############################################################################
# 2. IAM Role for Lambda
#############################################################################

lambda_role = aws.iam.Role(
    "semantic-scholar-lambda-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }),
    tags={
        "Name": "semantic-scholar-lambda-role",
        "Project": "aisafetyconnect",
    }
)

# Attach AWS managed policy for basic Lambda execution (CloudWatch Logs)
lambda_basic_execution = aws.iam.RolePolicyAttachment(
    "lambda-basic-execution",
    role=lambda_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
)

# Custom policy for S3 access
s3_policy = aws.iam.RolePolicy(
    "lambda-s3-policy",
    role=lambda_role.id,
    policy=pulumi.Output.all(s3_bucket_name).apply(lambda args: json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                    f"arn:aws:s3:::{args[0]}",
                    f"arn:aws:s3:::{args[0]}/config/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject",
                    "s3:PutObjectAcl"
                ],
                "Resource": f"arn:aws:s3:::{args[0]}/raw_data/snapshots/*"
            }
        ]
    }))
)

# Custom policy for Secrets Manager access
secrets_policy = aws.iam.RolePolicy(
    "lambda-secrets-policy",
    role=lambda_role.id,
    policy=semantic_scholar_secret.arn.apply(lambda arn: json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": "secretsmanager:GetSecretValue",
            "Resource": arn
        }]
    }))
)

#############################################################################
# 3. CloudWatch Log Group
#############################################################################

log_group = aws.cloudwatch.LogGroup(
    "semantic-scholar-lambda-logs",
    name="/aws/lambda/semantic-scholar-extractor",
    retention_in_days=30,
    tags={
        "Project": "aisafetyconnect",
    }
)

#############################################################################
# 4. Lambda Function
#############################################################################

# Package Lambda code
# Note: In production, you'd want to build this properly with dependencies
# For now, we'll create a simple archive
lambda_function = aws.lambda_.Function(
    "semantic-scholar-extractor",
    name="semantic-scholar-extractor",
    role=lambda_role.arn,
    runtime="python3.13",
    handler="handler.lambda_handler",
    code=pulumi.AssetArchive({
        ".": pulumi.FileArchive(str(lambda_code_path))
    }),
    timeout=900,  # 15 minutes (maximum)
    memory_size=2048,  # 2GB
    ephemeral_storage=aws.lambda_.FunctionEphemeralStorageArgs(
        size=2048  # 2GB
    ),
    environment=aws.lambda_.FunctionEnvironmentArgs(
        variables={
            "SECRET_ARN": semantic_scholar_secret.arn,
            "S3_BUCKET": s3_bucket_name,
            "S3_PREFIX": "raw_data/snapshots/",
            "TERMS_JSON_S3_KEY": "config/terms.json",
        }
    ),
    tags={
        "Project": "aisafetyconnect",
        "Function": "semantic-scholar-extraction",
    },
    opts=pulumi.ResourceOptions(depends_on=[
        lambda_basic_execution,
        s3_policy,
        secrets_policy,
        log_group
    ])
)

#############################################################################
# 5. Upload terms.json to S3
#############################################################################

terms_json_upload = aws.s3.BucketObject(
    "terms-json-config",
    bucket=s3_bucket_name,
    key="config/terms.json",
    source=pulumi.FileAsset(str(terms_json_path)),
    content_type="application/json",
    tags={
        "Project": "aisafetyconnect",
    }
)

#############################################################################
# 6. OPTIONAL: EventBridge Rule for Monthly Trigger
#############################################################################

# Uncomment to enable automatic monthly trigger on 1st of each month at 00:00 UTC
"""
monthly_schedule = aws.cloudwatch.EventRule(
    "monthly-extraction-schedule",
    name="semantic-scholar-monthly-extraction",
    description="Trigger Semantic Scholar extraction on 1st of each month",
    schedule_expression="cron(0 0 1 * ? *)",  # Day 1 of each month at 00:00 UTC
    tags={
        "Project": "aisafetyconnect",
    }
)

monthly_target = aws.cloudwatch.EventTarget(
    "monthly-extraction-target",
    rule=monthly_schedule.name,
    arn=lambda_function.arn,
    input=json.dumps({
        "extraction_date": "auto",
        "year_from": 2005,
        "papers_per_query": 10000,
        "min_citations": 0,
        "include_secondary": True,
        "max_workers": 10
    })
)

lambda_eventbridge_permission = aws.lambda_.Permission(
    "allow-eventbridge-invoke",
    action="lambda:InvokeFunction",
    function=lambda_function.name,
    principal="events.amazonaws.com",
    source_arn=monthly_schedule.arn
)
"""

#############################################################################
# Exports
#############################################################################

pulumi.export("lambda_function_name", lambda_function.name)
pulumi.export("lambda_function_arn", lambda_function.arn)
pulumi.export("secret_arn", semantic_scholar_secret.arn)
pulumi.export("s3_bucket", s3_bucket_name)
pulumi.export("terms_json_s3_key", terms_json_upload.key)
pulumi.export("log_group_name", log_group.name)
