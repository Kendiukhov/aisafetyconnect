# Semantic Scholar Extractor - AWS Lambda

AWS Lambda function for extracting research papers from Semantic Scholar API and storing them in S3 as Parquet files.

## 📋 Overview

This Lambda function:
- Extracts papers from Semantic Scholar API (Bulk API endpoint)
- Processes all AI Safety research areas defined in `terms.json`
- Generates queries with 3 levels: Area, Area+Field, Area+Field+Subfield
- Stores results in S3 as Parquet files (partitioned by extraction_date and area)
- Implements rate limiting (1 request/second) with async concurrency
- Handles monthly snapshots for historical data tracking

## 🏗️ Architecture

```
Lambda Handler (handler.py)
    ↓
Extractor (src/extractor.py)
    ├─→ Query Builder (src/query_builder.py)
    ├─→ API Client (src/async_api_client.py)
    └─→ Rate Limiter (src/async_rate_limiter.py)
    ↓
S3 Parquet Writer (src/s3_writer.py)
    ↓
S3: s3://bucket/raw_data/snapshots/extraction_date=YYYY-MM-DD/area=AREA/papers.parquet
```

## 📁 Project Structure

```
lambda/semantic_scholar_extractor/
├── handler.py                      # Lambda entry point
├── pyproject.toml                  # uv dependencies
├── .python-version                 # Python 3.13
├── src/
│   ├── __init__.py
│   ├── extractor.py                # Main extraction logic
│   ├── s3_writer.py                # Parquet S3 uploader
│   ├── secrets.py                  # AWS Secrets Manager helper
│   ├── utils.py                    # Utility functions
│   ├── async_api_client.py         # Semantic Scholar API client
│   ├── async_rate_limiter.py       # Global rate limiter
│   └── query_builder.py            # Query generation from terms.json
├── tests/
│   └── test_handler.py
└── README.md                       # This file
```

## 🔧 Lambda Configuration

- **Runtime**: Python 3.13
- **Timeout**: 900 seconds (15 minutes - AWS Lambda maximum)
- **Memory**: 2048 MB (2 GB)
- **Ephemeral Storage**: 2048 MB (2 GB)
- **Concurrent Executions**: 10 areas at a time
- **Environment Variables**:
  - `SECRET_ARN`: ARN of Semantic Scholar API key in Secrets Manager
  - `S3_BUCKET`: Target S3 bucket (e.g., "aisafetyconnect-raw-dev")
  - `S3_PREFIX`: S3 prefix for snapshots (e.g., "raw_data/snapshots/")
  - `TERMS_JSON_S3_KEY`: S3 key for terms.json config file

## 📥 Input Event Schema

```json
{
  "extraction_date": "2024-11-01",
  "year_from": 2005,
  "papers_per_query": 10000,
  "min_citations": 0,
  "include_secondary": true,
  "max_workers": 10
}
```

### Parameters:

- **extraction_date**: Date string (YYYY-MM-DD) or "auto" (defaults to first day of current month)
- **year_from**: Minimum publication year (default: 2005)
- **papers_per_query**: Maximum papers per query (default: 10000)
- **min_citations**: Minimum citation count filter (default: 0)
- **include_secondary**: Include secondary fields in queries (default: true)
- **max_workers**: Number of concurrent area extractions (default: 10)

## 📤 Output

### S3 Structure:

```
s3://aisafetyconnect-raw-dev/
├── config/
│   └── terms.json                                    # Query configuration
└── raw_data/
    └── snapshots/
        ├── extraction_date=2024-11-01/
        │   ├── area=AI_Safety/
        │   │   └── papers.parquet
        │   ├── area=Adversarial_Robustness/
        │   │   └── papers.parquet
        │   └── ...
        └── extraction_date=2024-12-01/
            └── ...
```

### Lambda Response:

```json
{
  "statusCode": 200,
  "body": {
    "extraction_date": "2024-11-01",
    "total_areas": 15,
    "total_papers": 50000,
    "s3_prefix": "raw_data/snapshots/extraction_date=2024-11-01/",
    "timestamp": "2024-11-01T10:30:00"
  }
}
```

## 🚀 Local Development with uv

### Setup:

```bash
cd lambda/semantic_scholar_extractor

# Create virtual environment with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e .
```

### Run locally:

```python
# test_local.py
import asyncio
from handler import lambda_handler

event = {
    "extraction_date": "2024-11-01",
    "year_from": 2020,
    "papers_per_query": 100,
    "min_citations": 10,
    "include_secondary": False,
    "max_workers": 2
}

class MockContext:
    pass

result = lambda_handler(event, MockContext())
print(result)
```

### Run tests:

```bash
uv run pytest tests/
```

## 📦 Dependencies

Main dependencies (from `pyproject.toml`):

- `aiohttp>=3.9.0` - Async HTTP client
- `boto3>=1.34.0` - AWS SDK
- `pandas>=2.2.0` - Data manipulation
- `pyarrow>=15.0.0` - Parquet file format

## 🔐 AWS Permissions Required

Lambda execution role needs:

### CloudWatch Logs:
```json
{
  "Effect": "Allow",
  "Action": [
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents"
  ],
  "Resource": "arn:aws:logs:*:*:*"
}
```

### S3 Read (for terms.json):
```json
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "s3:ListBucket"
  ],
  "Resource": [
    "arn:aws:s3:::aisafetyconnect-raw-dev",
    "arn:aws:s3:::aisafetyconnect-raw-dev/config/*"
  ]
}
```

### S3 Write (for Parquet files):
```json
{
  "Effect": "Allow",
  "Action": [
    "s3:PutObject",
    "s3:PutObjectAcl"
  ],
  "Resource": "arn:aws:s3:::aisafetyconnect-raw-dev/raw_data/snapshots/*"
}
```

### Secrets Manager:
```json
{
  "Effect": "Allow",
  "Action": "secretsmanager:GetSecretValue",
  "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:semantic-scholar-api-key-*"
}
```

## ⏱️ Execution Time Considerations

### Timeout Limits:

- AWS Lambda maximum timeout: **15 minutes**
- With 10 workers and 1 req/second rate limit: ~900 queries max
- Each area can have 20-40 queries (Primary) or 40-80 queries (Primary + Secondary)

### If execution times out:

**Option 1**: Split into multiple invocations per area
**Option 2**: Use AWS Batch instead of Lambda (no timeout limit)
**Option 3**: Reduce `papers_per_query` or disable `include_secondary`

## 📊 Monitoring

### CloudWatch Logs:

```bash
aws logs tail /aws/lambda/semantic-scholar-extractor --follow
```

### CloudWatch Metrics:

- Duration
- Errors
- Invocations
- Throttles
- ConcurrentExecutions

### Custom Logs:

Lambda logs include:
- Extraction parameters
- Progress per area (X/Y queries)
- Papers extracted per query
- S3 upload confirmation
- Total papers and areas processed

## 🐛 Troubleshooting

### Error: "Task timed out after 900 seconds"

**Cause**: Lambda hit 15-minute timeout limit

**Solutions**:
1. Reduce `papers_per_query`
2. Set `include_secondary=false`
3. Split extraction into multiple Lambda invocations
4. Consider using AWS Batch instead

### Error: "Rate limit (429)"

**Cause**: Too many concurrent requests to Semantic Scholar API

**Check**: Rate limiter should prevent this, but if it happens:
- Reduce `max_workers`
- Increase delays between queries

### Error: "Secret not found"

**Cause**: Secrets Manager secret doesn't exist or Lambda doesn't have permission

**Solutions**:
1. Verify secret exists: `aws secretsmanager describe-secret --secret-id semantic-scholar-api-key`
2. Check IAM permissions
3. Verify `SECRET_ARN` environment variable

### Error: "S3 PutObject Access Denied"

**Cause**: Lambda role lacks S3 write permissions

**Solution**: Add S3 PutObject policy to Lambda execution role

## 🔄 Historical Extraction

To extract data for all months from 2005 to now, see the deployment guide for scripts to invoke the Lambda multiple times with different dates.

## 📚 Related Documentation

- [../infrastructure/pulumi/README.md](../../infrastructure/pulumi/README.md) - Pulumi IaC deployment guide
- [DEPLOYMENT.md](../../DEPLOYMENT.md) - Full deployment walkthrough
- [../../semantic_scholar/ASYNC_IMPLEMENTATION.md](../../semantic_scholar/ASYNC_IMPLEMENTATION.md) - Async implementation details
- [../../semantic_scholar/RAW_DATA_MODE.md](../../semantic_scholar/RAW_DATA_MODE.md) - Raw data strategy

## 🆘 Support

For issues or questions:
1. Check CloudWatch Logs for error details
2. Review this README and related documentation
3. Check [Semantic Scholar API docs](https://www.semanticscholar.org/product/api)
