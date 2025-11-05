# Pulumi Infrastructure - Semantic Scholar Extractor Lambda

Infrastructure as Code (IaC) for deploying the Semantic Scholar extraction Lambda to AWS.

## 📋 Resources Created

This Pulumi stack creates:

1. **AWS Secrets Manager Secret** - Stores Semantic Scholar API key
2. **IAM Role** - Lambda execution role with necessary permissions
3. **IAM Policies** - S3 access, Secrets Manager access, CloudWatch Logs
4. **Lambda Function** - Semantic Scholar extractor (Python 3.13, 2GB RAM, 15min timeout)
5. **CloudWatch Log Group** - Lambda logs (30 day retention)
6. **S3 Bucket Object** - Uploads `terms.json` to S3
7. **EventBridge Rule** (Optional) - Monthly automatic trigger

## 🚀 Quick Start

### Prerequisites:

- Python 3.8+ (for Pulumi, not the Lambda)
- [Pulumi CLI](https://www.pulumi.com/docs/get-started/install/) installed
- AWS CLI configured with credentials
- `uv` or `pip` for Python dependencies

### 1. Install Dependencies:

```bash
cd infrastructure/pulumi

# With uv (recommended)
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Or with pip
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Initialize Pulumi Stack:

```bash
# Login to Pulumi (choose backend)
pulumi login  # For Pulumi Cloud (free for individuals)
# OR
pulumi login --local  # For local state file

# Create/select stack
pulumi stack init dev
```

### 3. Configure Stack:

```bash
# Set AWS region
pulumi config set aws:region us-east-1

# Set S3 bucket name (must already exist)
pulumi config set aisafetyconnect:s3-bucket aisafetyconnect-raw-dev

# Set Semantic Scholar API key (encrypted)
pulumi config set --secret aisafetyconnect:semantic-scholar-api-key YOUR_API_KEY_HERE
```

### 4. Preview Changes:

```bash
pulumi preview
```

### 5. Deploy:

```bash
pulumi up
# Review changes
# Confirm: yes
```

## 📦 What Gets Deployed

### Secrets Manager:

```
Secret Name: semantic-scholar-api-key
ARN: arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:semantic-scholar-api-key-XXXXX
```

### Lambda Function:

```
Function Name: semantic-scholar-extractor
Runtime: python3.13
Timeout: 900s (15 minutes)
Memory: 2048 MB
Ephemeral Storage: 2048 MB
```

### S3 Structure:

```
s3://aisafetyconnect-raw-dev/
├── config/
│   └── terms.json  # Uploaded by Pulumi
└── raw_data/
    └── snapshots/  # Created by Lambda at runtime
```

### CloudWatch:

```
Log Group: /aws/lambda/semantic-scholar-extractor
Retention: 30 days
```

## 🔧 Configuration Options

### Required Config:

- `aisafetyconnect:s3-bucket` - S3 bucket name (string)
- `aisafetyconnect:semantic-scholar-api-key` - API key (secret)

### Optional Config:

```bash
# AWS region (default: us-east-1)
pulumi config set aws:region us-west-2

# AWS profile (if using multiple AWS accounts)
pulumi config set aws:profile my-profile
```

## 📤 Outputs

After deployment, Pulumi exports:

```bash
pulumi stack output lambda_function_name    # semantic-scholar-extractor
pulumi stack output lambda_function_arn     # arn:aws:lambda:...
pulumi stack output secret_arn              # arn:aws:secretsmanager:...
pulumi stack output s3_bucket               # aisafetyconnect-raw-dev
pulumi stack output terms_json_s3_key       # config/terms.json
pulumi stack output log_group_name          # /aws/lambda/semantic-scholar-extractor
```

## 🔄 Updates and Changes

### Update Lambda Code:

```bash
# Make changes to lambda/semantic_scholar_extractor/
# Then:
pulumi up
```

Pulumi will detect changes and redeploy the Lambda function.

### Update Configuration:

```bash
# Change API key
pulumi config set --secret aisafetyconnect:semantic-scholar-api-key NEW_KEY

# Update deployment
pulumi up
```

### Update terms.json:

```bash
# Edit ../../terms.json
# Then:
pulumi up
```

Pulumi will re-upload the file to S3.

## 🗑️ Destroy Infrastructure

⚠️ **Warning**: This will delete all resources including the secret!

```bash
pulumi destroy
# Confirm: yes
```

## 🎛️ EventBridge Automatic Trigger (Optional)

By default, the EventBridge rule is **commented out** in `__main__.py`.

To enable monthly automatic extraction:

1. Open `__main__.py`
2. Uncomment lines starting with `monthly_schedule`
3. Run `pulumi up`

This will create:
- EventBridge rule: Triggers on 1st of each month at 00:00 UTC
- Target: Invokes Lambda with default parameters
- Permission: Allows EventBridge to invoke Lambda

## 🐛 Troubleshooting

### Error: "No valid credential sources found"

**Cause**: AWS credentials not configured

**Solution**:
```bash
aws configure
# Or set environment variables:
export AWS_ACCESS_KEY_ID=xxx
export AWS_SECRET_ACCESS_KEY=yyy
export AWS_REGION=us-east-1
```

### Error: "Resource already exists"

**Cause**: Resource with same name exists from previous deployment

**Solutions**:
1. Delete existing resource manually
2. Change resource name in code
3. Use `pulumi import` to import existing resource

### Error: "Bucket does not exist"

**Cause**: S3 bucket specified in config doesn't exist

**Solution**:
```bash
# Create bucket first
aws s3 mb s3://aisafetyconnect-raw-dev --region us-east-1

# Or update config to existing bucket
pulumi config set aisafetyconnect:s3-bucket your-existing-bucket
```

### Error: "terms.json not found"

**Cause**: `terms.json` file doesn't exist in project root

**Solution**: Ensure `../../terms.json` exists relative to Pulumi directory

## 📊 Cost Estimation

Approximate monthly costs:

| Service | Usage | Cost |
|---------|-------|------|
| Lambda | 1 execution/month, 15 min, 2GB | $0.03 |
| Secrets Manager | 1 secret | $0.40 |
| S3 Storage | ~100GB | $2.30 |
| CloudWatch Logs | ~100MB/month | $0.01 |
| **Total** | | **~$2.75/month** |

Historical extraction (one-time):
- 240 months × $0.03 = ~$7.20

## 🔐 Security Best Practices

1. **API Key**: Always use `--secret` flag when setting API key
2. **IAM Policies**: Follow principle of least privilege
3. **S3 Bucket**: Enable versioning and encryption
4. **Secrets Rotation**: Consider rotating API key periodically
5. **VPC**: For production, deploy Lambda in VPC with NAT Gateway

## 📚 File Structure

```
infrastructure/pulumi/
├── __main__.py           # Main Pulumi program
├── Pulumi.yaml           # Project config
├── Pulumi.dev.yaml       # Stack config (dev)
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## 🔗 Related Documentation

- [../../lambda/semantic_scholar_extractor/README.md](../../lambda/semantic_scholar_extractor/README.md) - Lambda documentation
- [../../DEPLOYMENT.md](../../DEPLOYMENT.md) - Complete deployment guide
- [Pulumi AWS Documentation](https://www.pulumi.com/docs/clouds/aws/)
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)

## 🆘 Support

For Pulumi-specific issues:
- [Pulumi Community Slack](https://slack.pulumi.com/)
- [Pulumi GitHub](https://github.com/pulumi/pulumi)

For AWS issues:
- Check CloudWatch Logs
- Review IAM permissions
- Verify resource quotas
