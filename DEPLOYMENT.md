# Deployment Guide - Semantic Scholar Extractor Lambda

Complete guide for deploying and running the Semantic Scholar extraction Lambda function.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Deployment Steps](#deployment-steps)
4. [Testing the Lambda](#testing-the-lambda)
5. [Historical Data Extraction](#historical-data-extraction)
6. [Monitoring and Logs](#monitoring-and-logs)
7. [Troubleshooting](#troubleshooting)

---

## Overview

This deployment guide covers:
- Deploying Lambda function with Pulumi IaC
- Setting up AWS resources (Secrets Manager, IAM, S3, CloudWatch)
- Running historical extraction (2005-2024)
- Setting up monthly automatic extraction (optional)

### Architecture:

```
EventBridge (monthly trigger)
    ↓
Lambda Function (15 min max, 2GB RAM)
    ├─→ Reads: Secrets Manager (API key)
    ├─→ Reads: S3 (terms.json)
    └─→ Writes: S3 (Parquet files)
        └─→ s3://bucket/raw_data/snapshots/extraction_date=YYYY-MM-DD/
```

---

## Prerequisites

### 1. Software Requirements:

- **Python 3.13** - For Lambda runtime
- **Python 3.8+** - For Pulumi CLI
- **uv** - Python package manager ([install](https://github.com/astral-sh/uv))
- **Pulumi CLI** - [Install guide](https://www.pulumi.com/docs/get-started/install/)
- **AWS CLI** - [Install guide](https://aws.amazon.com/cli/)

### 2. AWS Requirements:

- AWS Account with admin access (or sufficient permissions)
- AWS CLI configured:
  ```bash
  aws configure
  # Or:
  export AWS_ACCESS_KEY_ID=xxx
  export AWS_SECRET_ACCESS_KEY=yyy
  export AWS_REGION=us-east-1
  ```

### 3. Semantic Scholar:

- API Key from [Semantic Scholar](https://www.semanticscholar.org/product/api)
- Rate limit: 1 request/second with API key

### 4. S3 Bucket:

- Create S3 bucket if it doesn't exist:
  ```bash
  aws s3 mb s3://aisafetyconnect-raw-dev --region us-east-1
  ```

---

## Deployment Steps

### Step 1: Clone and Setup

```bash
cd /path/to/aisafetyconnect
```

Verify structure:
```bash
tree -L 2
├── lambda/
│   └── semantic_scholar_extractor/
├── infrastructure/
│   └── pulumi/
├── terms.json
└── DEPLOYMENT.md (this file)
```

### Step 2: Install Pulumi Dependencies

```bash
cd infrastructure/pulumi

# Create virtual environment
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt
```

### Step 3: Initialize Pulumi Stack

```bash
# Login to Pulumi
pulumi login  # Cloud backend (free)
# OR
pulumi login --local  # Local file backend

# Initialize stack
pulumi stack init dev

# Verify
pulumi stack ls
```

### Step 4: Configure Stack

```bash
# AWS region
pulumi config set aws:region us-east-1

# S3 bucket (must already exist)
pulumi config set aisafetyconnect:s3-bucket aisafetyconnect-raw-dev

# Semantic Scholar API key (encrypted)
pulumi config set --secret aisafetyconnect:semantic-scholar-api-key YOUR_API_KEY_HERE
```

Verify configuration:
```bash
pulumi config
```

Output:
```
KEY                                              VALUE
aisafetyconnect:s3-bucket                        aisafetyconnect-raw-dev
aisafetyconnect:semantic-scholar-api-key         [secret]
aws:region                                       us-east-1
```

### Step 5: Preview Deployment

```bash
pulumi preview
```

Review resources to be created:
- 1 Secrets Manager Secret
- 1 IAM Role + 3 Policies
- 1 Lambda Function
- 1 CloudWatch Log Group
- 1 S3 Object (terms.json)

### Step 6: Deploy

```bash
pulumi up
# Review changes
# Type: yes
```

Wait for deployment (~2-3 minutes).

### Step 7: Verify Deployment

```bash
# Get outputs
pulumi stack output

# Verify Lambda exists
aws lambda get-function --function-name semantic-scholar-extractor

# Verify secret exists
aws secretsmanager describe-secret --secret-id semantic-scholar-api-key

# Verify terms.json uploaded
aws s3 ls s3://aisafetyconnect-raw-dev/config/
```

---

## Testing the Lambda

### Test 1: Manual Invocation (Small Test)

Create test event:
```bash
cat > test-event.json << 'EOF'
{
  "extraction_date": "2024-11-01",
  "year_from": 2020,
  "papers_per_query": 100,
  "min_citations": 10,
  "include_secondary": false,
  "max_workers": 2
}
EOF
```

Invoke Lambda:
```bash
aws lambda invoke \
  --function-name semantic-scholar-extractor \
  --payload file://test-event.json \
  --cli-binary-format raw-in-base64-out \
  response.json

# Check response
cat response.json
```

Expected output:
```json
{
  "statusCode": 200,
  "body": {
    "extraction_date": "2024-11-01",
    "total_areas": 15,
    "total_papers": 1500,
    "s3_prefix": "raw_data/snapshots/extraction_date=2024-11-01/",
    "timestamp": "2024-11-01T10:30:00"
  }
}
```

### Test 2: Check S3 Output

```bash
# List created files
aws s3 ls s3://aisafetyconnect-raw-dev/raw_data/snapshots/ --recursive

# Download a sample file
aws s3 cp s3://aisafetyconnect-raw-dev/raw_data/snapshots/extraction_date=2024-11-01/area=AI_Safety/papers.parquet ./test.parquet

# Read parquet file (with pandas)
python -c "import pandas as pd; df = pd.read_parquet('test.parquet'); print(df.head())"
```

### Test 3: Check CloudWatch Logs

```bash
# Tail logs
aws logs tail /aws/lambda/semantic-scholar-extractor --follow

# Get recent logs
aws logs tail /aws/lambda/semantic-scholar-extractor --since 1h
```

---

## Historical Data Extraction

To extract data from 2005 to present, you need to invoke the Lambda multiple times (once per month).

### Option A: Python Script (Recommended)

Create `scripts/run_historical_extraction.py`:

```python
#!/usr/bin/env python3
"""
Run historical extraction for all months from 2005 to present
"""

import boto3
import json
import time
from datetime import datetime, timedelta

lambda_client = boto3.client('lambda', region_name='us-east-1')

def generate_monthly_dates(start_year=2005):
    """Generate YYYY-MM-01 dates from start_year to now"""
    dates = []
    current = datetime(start_year, 1, 1)
    now = datetime.now()

    while current <= now:
        dates.append(current.strftime('%Y-%m-01'))
        # Next month
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)

    return dates

def invoke_extraction(extraction_date):
    """Invoke Lambda for one month"""
    payload = {
        "extraction_date": extraction_date,
        "year_from": 2005,
        "papers_per_query": 10000,
        "min_citations": 0,
        "include_secondary": True,
        "max_workers": 10
    }

    print(f"📅 Invoking extraction for {extraction_date}...")

    response = lambda_client.invoke(
        FunctionName='semantic-scholar-extractor',
        InvocationType='Event',  # Async invocation
        Payload=json.dumps(payload)
    )

    if response['StatusCode'] == 202:
        print(f"   ✅ Invoked successfully")
    else:
        print(f"   ❌ Error: {response}")

    return response['StatusCode'] == 202

def main():
    dates = generate_monthly_dates(2005)
    print(f"Total months to extract: {len(dates)}")
    print(f"From: {dates[0]} to {dates[-1]}\n")

    input("Press Enter to continue...")

    successful = 0
    failed = 0

    for i, date in enumerate(dates, 1):
        print(f"\n[{i}/{len(dates)}]")

        if invoke_extraction(date):
            successful += 1
        else:
            failed += 1

        # Rate limit: Don't invoke too many at once
        time.sleep(2)

    print(f"\n{'='*60}")
    print(f"EXTRACTION INVOCATIONS COMPLETED")
    print(f"{'='*60}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"\nNote: Lambdas are running asynchronously.")
    print(f"Check CloudWatch Logs for progress.")

if __name__ == "__main__":
    main()
```

Run it:
```bash
python scripts/run_historical_extraction.py
```

### Option B: Bash Script

```bash
#!/bin/bash
# scripts/run_historical_extraction.sh

FUNCTION_NAME="semantic-scholar-extractor"

for year in {2005..2024}; do
  for month in {1..12}; do
    # Skip future months
    if [ $year -eq 2024 ] && [ $month -gt 10 ]; then
      break
    fi

    extraction_date=$(printf "%04d-%02d-01" $year $month)

    echo "📅 Invoking extraction for $extraction_date..."

    aws lambda invoke \
      --function-name $FUNCTION_NAME \
      --invocation-type Event \
      --payload "{\"extraction_date\": \"$extraction_date\", \"year_from\": 2005, \"papers_per_query\": 10000, \"min_citations\": 0, \"include_secondary\": true}" \
      /dev/null

    sleep 2
  done
done

echo "✅ All invocations completed"
```

### Monitor Progress:

```bash
# Watch Lambda invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=semantic-scholar-extractor \
  --start-time 2024-11-01T00:00:00Z \
  --end-time 2024-11-01T23:59:59Z \
  --period 3600 \
  --statistics Sum

# Check S3 for completed months
aws s3 ls s3://aisafetyconnect-raw-dev/raw_data/snapshots/ | wc -l
```

---

## Monitoring and Logs

### CloudWatch Logs:

```bash
# Real-time logs
aws logs tail /aws/lambda/semantic-scholar-extractor --follow

# Logs from last hour
aws logs tail /aws/lambda/semantic-scholar-extractor --since 1h

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/semantic-scholar-extractor \
  --filter-pattern "ERROR"
```

### CloudWatch Metrics:

```bash
# Lambda duration
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=semantic-scholar-extractor \
  --start-time 2024-11-01T00:00:00Z \
  --end-time 2024-11-01T23:59:59Z \
  --period 3600 \
  --statistics Average,Maximum

# Lambda errors
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=semantic-scholar-extractor \
  --start-time 2024-11-01T00:00:00Z \
  --end-time 2024-11-01T23:59:59Z \
  --period 3600 \
  --statistics Sum
```

---

## Troubleshooting

### Issue: Lambda times out after 15 minutes

**Symptoms**: Execution stops at 900 seconds

**Solutions**:
1. Reduce `papers_per_query`: `--papers_per_query 5000`
2. Disable secondary fields: `--include_secondary false`
3. Reduce workers: `--max_workers 5`
4. Consider AWS Batch (no timeout limit)

### Issue: Rate limit errors (HTTP 429)

**Symptoms**: Logs show "Rate limit (429)"

**Solutions**:
1. Reduce `max_workers`
2. Check rate limiter is working
3. Verify API key is valid

### Issue: S3 Access Denied

**Symptoms**: "Access Denied" errors in logs

**Solutions**:
1. Check IAM role has S3 PutObject permission
2. Verify bucket name in config
3. Check bucket policy

### Issue: Secret not found

**Symptoms**: "Secret not found" error

**Solutions**:
1. Verify secret exists:
   ```bash
   aws secretsmanager describe-secret --secret-id semantic-scholar-api-key
   ```
2. Check `SECRET_ARN` environment variable
3. Verify IAM permissions

---

## Next Steps

After successful deployment:

1. ✅ Run test extraction
2. ✅ Verify S3 output
3. ✅ Run historical extraction
4. ⏳ Set up EventBridge monthly trigger (optional)
5. ⏳ Configure CloudWatch alarms
6. ⏳ Build Silver layer (Glue/Spark for data cleaning)
7. ⏳ Build Gold layer (analytics/aggregations)

---

## 📚 Related Documentation

- [lambda/semantic_scholar_extractor/README.md](lambda/semantic_scholar_extractor/README.md)
- [infrastructure/pulumi/README.md](infrastructure/pulumi/README.md)
- [semantic_scholar/ASYNC_IMPLEMENTATION.md](semantic_scholar/ASYNC_IMPLEMENTATION.md)
- [semantic_scholar/RAW_DATA_MODE.md](semantic_scholar/RAW_DATA_MODE.md)

---

## 🆘 Getting Help

If you encounter issues:

1. Check CloudWatch Logs first
2. Review this troubleshooting section
3. Check related documentation
4. Verify AWS permissions and quotas
