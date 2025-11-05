# Project Summary - Semantic Scholar Extractor Lambda

**Created**: 2024-10-27
**Status**: ✅ Code Complete - Ready for Deployment
**Next Step**: Deploy with Pulumi

---

## What Was Built

### 1. AWS Lambda Function (Python 3.13)
- Extracts research papers from Semantic Scholar API
- Processes 15+ AI Safety research areas
- Generates 3-level queries (area, field, subfield)
- Stores results in S3 as Parquet files
- Implements monthly snapshot strategy

### 2. Pulumi Infrastructure as Code
- Secrets Manager for API key
- IAM roles and policies
- Lambda function configuration
- CloudWatch Log Group
- S3 object upload (terms.json)

### 3. Complete Documentation
- Lambda README
- Pulumi README
- DEPLOYMENT.md (step-by-step guide)
- CLAUDE_CODE_CONTEXT.md (for future sessions)

---

## File Structure Created

```
aisafetyconnect/
├── lambda/
│   └── semantic_scholar_extractor/
│       ├── handler.py
│       ├── pyproject.toml
│       ├── src/
│       │   ├── extractor.py
│       │   ├── s3_writer.py
│       │   ├── secrets.py
│       │   ├── utils.py
│       │   ├── async_api_client.py  (copied)
│       │   ├── async_rate_limiter.py  (copied)
│       │   └── query_builder.py  (copied)
│       ├── README.md
│       └── SUMMARY.md  (this file)
│
├── infrastructure/
│   └── pulumi/
│       ├── __main__.py
│       ├── Pulumi.yaml
│       ├── Pulumi.dev.yaml
│       ├── requirements.txt
│       └── README.md
│
├── DEPLOYMENT.md
└── CLAUDE_CODE_CONTEXT.md
```

---

## Key Decisions

1. **Lambda over AWS Batch**: Simpler, cheaper, sufficient (despite 15min timeout)
2. **Parquet over JSON**: Better compression, faster queries
3. **Monthly Snapshots**: Simple CDC strategy, enables time-travel
4. **No Deduplication in Bronze**: Raw data preservation
5. **3-Level Queries**: Area + Field + Subfield for comprehensive coverage

---

## What to Do Next

### Deploy (First Time):

```bash
cd infrastructure/pulumi
pulumi stack init dev
pulumi config set aws:region us-east-1
pulumi config set aisafetyconnect:s3-bucket aisafetyconnect-raw-dev
pulumi config set --secret aisafetyconnect:semantic-scholar-api-key YOUR_KEY
pulumi up
```

### Test:

```bash
aws lambda invoke \
  --function-name semantic-scholar-extractor \
  --payload '{"extraction_date": "2024-11-01", "year_from": 2020, "papers_per_query": 100}' \
  response.json
```

### Run Historical Extraction:

See `DEPLOYMENT.md` Section: "Historical Data Extraction" for scripts

---

## Important Notes

### ⚠️ Timeout Risk:
Lambda has 15-minute max timeout. With ~40-80 queries per area, may need to:
- Reduce `papers_per_query`
- Disable `include_secondary`
- Split large areas

### ✅ Query Generation Fixed:
Modified `query_builder.py` to generate all 3 levels (area, field, subfield).
Now generates ~4-8x more queries than before.

### ✅ Semantic Scholar Verified:
- Searches title AND abstract (confirmed)
- publicationDate coverage: 79.66% (use `year` filter)
- Rate limit: 1 req/second with API key

---

## Documentation Guide

| File | Purpose |
|------|---------|
| `CLAUDE_CODE_CONTEXT.md` | Read this FIRST in new sessions |
| `DEPLOYMENT.md` | Step-by-step deployment guide |
| `lambda/.../README.md` | Lambda function documentation |
| `infrastructure/.../README.md` | Pulumi IaC documentation |

---

## Cost Estimate

- **Lambda**: $0.03 per execution
- **Secrets Manager**: $0.40/month
- **S3 Storage**: ~$2.30/month (100GB)
- **Total**: ~$3/month ongoing
- **Historical extraction**: ~$7 one-time (240 months)

---

## Status Checklist

- [x] Lambda code written
- [x] Pulumi IaC written
- [x] Documentation complete
- [ ] **Deployed to AWS** ← Next step
- [ ] Tested with small extraction
- [ ] Historical extraction run
- [ ] EventBridge trigger configured (optional)

---

**Ready to deploy? Start with `DEPLOYMENT.md`**
