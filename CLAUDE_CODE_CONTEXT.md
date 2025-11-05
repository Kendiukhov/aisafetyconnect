# Claude Code - Session Context Document

**Project**: AI Safety Connect - Research Paper Data Pipeline
**Date Created**: 2024-10-27
**Last Updated**: 2024-10-27
**Status**: Lambda code complete, ready for deployment

---

## 🎯 Project Overview

Building a data pipeline to extract research papers from Semantic Scholar API related to AI Safety research topics.

### Architecture (Medallion):

```
Bronze (Raw Data)
    └── Lambda extracts from Semantic Scholar API
    └── Stores in S3 as Parquet (monthly snapshots)

Silver (Staging) - FUTURE
    └── Glue/Spark for cleaning, deduplication, enrichment

Gold (Analytics) - FUTURE
    └── Aggregations, metrics, analysis-ready tables
```

---

## 📁 Current State of the Project

### What's Complete:

✅ **Local Semantic Scholar Extractor** (`semantic_scholar/`)
- Async extraction with `aiohttp`
- Global rate limiter (1 req/second)
- Query generation with 3 levels (area, area+field, area+field+subfield)
- Raw data mode (no deduplication - for Bronze layer)
- Tested and working

✅ **Lambda Function Code** (`lambda/semantic_scholar_extractor/`)
- Handler for AWS Lambda invocation
- S3 Parquet writer
- Secrets Manager integration
- All source code ported from local version
- NOT YET DEPLOYED

✅ **Pulumi IaC** (`infrastructure/pulumi/`)
- Complete infrastructure definition
- Secrets Manager, IAM, Lambda, CloudWatch
- NOT YET DEPLOYED

✅ **Documentation**
- Lambda README
- Pulumi README
- DEPLOYMENT.md (complete deployment guide)
- This context document

### What's NOT Complete:

❌ Lambda NOT deployed to AWS yet
❌ Historical data extraction NOT run yet
❌ Silver/Gold layers NOT built yet
❌ EventBridge trigger NOT set up yet

---

## 🗂️ Project Structure

```
aisafetyconnect/
├── lambda/
│   └── semantic_scholar_extractor/
│       ├── handler.py                    # Lambda entry point
│       ├── pyproject.toml                # uv dependencies
│       ├── .python-version               # 3.13
│       ├── src/
│       │   ├── extractor.py              # Main extraction logic
│       │   ├── s3_writer.py              # Parquet S3 upload
│       │   ├── secrets.py                # Secrets Manager helper
│       │   ├── utils.py                  # S3 download helper
│       │   ├── async_api_client.py       # Semantic Scholar API
│       │   ├── async_rate_limiter.py     # Rate limiting
│       │   └── query_builder.py          # Query generation
│       └── README.md
│
├── infrastructure/
│   └── pulumi/
│       ├── __main__.py                   # Main Pulumi program
│       ├── Pulumi.yaml                   # Project config
│       ├── Pulumi.dev.yaml               # Stack config
│       ├── requirements.txt              # Pulumi dependencies
│       └── README.md
│
├── semantic_scholar/                     # Local version (used for testing)
│   ├── async_api_client.py
│   ├── async_rate_limiter.py
│   ├── async_extractor.py
│   ├── query_builder.py
│   ├── run_async_extraction.py
│   ├── analyze_publication_dates.py
│   └── *.md (documentation)
│
├── raw_data/                             # Local test extractions
│   └── area_*.json                       # Historical extractions (for reference)
│
├── terms.json                            # AI Safety research areas/fields/subfields
├── DEPLOYMENT.md                         # Complete deployment guide
└── CLAUDE_CODE_CONTEXT.md                # This file
```

---

## 🔑 Key Decisions Made

### 1. **Architecture: Lambda (not AWS Batch)**
- **Decision**: Use Lambda despite 15-minute timeout limit
- **Reason**: Simpler, cheaper, sufficient for current use case
- **Note**: May need to switch to Batch if timeouts become issue

### 2. **Storage Format: Parquet (not JSON)**
- **Decision**: Store in S3 as Parquet files
- **Reason**: 5-10x compression, faster Athena queries, columnar format
- **Structure**: `s3://bucket/raw_data/snapshots/extraction_date=YYYY-MM-DD/area=AREA/papers.parquet`

### 3. **Data Strategy: Monthly Snapshots (not CDC)**
- **Decision**: Full snapshot each month (no change data capture)
- **Reason**: Simplest approach, time-travel capability, no deduplication complexity
- **Trade-off**: More storage, but cheap (~$2/month)

### 4. **Deduplication: None in Bronze**
- **Decision**: NO deduplication in Bronze layer
- **Reason**: Raw data should be untouched, dedup happens in Silver
- **Impact**: Papers appear multiple times if in multiple areas (expected)

### 5. **Query Generation: 3 Levels with Subfields**
- **Decision**: Area, Area+Field, Area+Field+Subfield
- **Previous Bug**: Was NOT generating subfield queries
- **Fixed**: Modified `query_builder.py` to include all 3 levels
- **Impact**: ~4-8x more queries per area

### 6. **Semantic Scholar API: Searches Title + Abstract**
- **Verified**: `query` parameter searches both fields automatically
- **No changes needed**: Implementation already correct

### 7. **publicationDate Coverage: ~80%**
- **Fact**: Only 79.66% of papers have exact publication date
- **Decision**: Use `year` filter (not `publicationDateOrYear`)
- **Reason**: Don't lose 20% of papers that only have year

---

## ⚙️ Technical Details

### Lambda Configuration:

```python
Runtime: Python 3.13
Timeout: 900 seconds (15 minutes - AWS maximum)
Memory: 2048 MB
Ephemeral Storage: 2048 MB
Concurrent Workers: 10 areas at a time
```

### Environment Variables:

```bash
SECRET_ARN=arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:semantic-scholar-api-key-XXX
S3_BUCKET=aisafetyconnect-raw-dev
S3_PREFIX=raw_data/snapshots/
TERMS_JSON_S3_KEY=config/terms.json
```

### Invocation Event:

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

### S3 Output Structure:

```
s3://aisafetyconnect-raw-dev/
├── config/
│   └── terms.json
└── raw_data/
    └── snapshots/
        └── extraction_date=2024-11-01/
            ├── area=AI_Safety/papers.parquet
            ├── area=Adversarial_Robustness/papers.parquet
            └── ...
```

---

## 🚀 Next Steps (For Next Session)

### Immediate (Deploy Lambda):

1. **Deploy with Pulumi**:
   ```bash
   cd infrastructure/pulumi
   pulumi up
   ```

2. **Test Lambda**:
   ```bash
   aws lambda invoke \
     --function-name semantic-scholar-extractor \
     --payload '{"extraction_date": "2024-11-01", "year_from": 2020, "papers_per_query": 100}' \
     response.json
   ```

3. **Verify S3 Output**:
   ```bash
   aws s3 ls s3://aisafetyconnect-raw-dev/raw_data/snapshots/ --recursive
   ```

### Historical Extraction:

4. **Run Historical Script**:
   - Create script to invoke Lambda for all months 2005-2024
   - See DEPLOYMENT.md for examples
   - Monitor CloudWatch Logs

### Future (Silver/Gold Layers):

5. **Build Silver Layer**:
   - AWS Glue job for deduplication
   - Add cross-area metadata
   - Data quality checks

6. **Build Gold Layer**:
   - Aggregations by area, year, author
   - Citation analysis
   - Trend identification

---

## 🐛 Known Issues and Considerations

### 1. Lambda Timeout Risk:

**Issue**: With ~40-80 queries per area (with secondary), Lambda might timeout

**Mitigation Options**:
- Reduce `papers_per_query`
- Disable `include_secondary`
- Split large areas into multiple invocations
- Switch to AWS Batch if persistent

### 2. Query Generation:

**Verified**: Now generating all 3 levels correctly
- Before fix: ~5 queries/area
- After fix: ~20-40 queries/area (Primary only)
- With secondary: ~40-80 queries/area

### 3. Rate Limiting:

**Current**: 1 request/second (Semantic Scholar limit with API key)
**Implementation**: Global async rate limiter working correctly
**Max throughput**: ~900 requests in 15 minutes (Lambda timeout)

### 4. Semantic Scholar API:

**Search Fields**: Title + Abstract (verified working)
**publicationDate**: Only 79.66% have exact date, rest only have year
**Pagination**: Token-based, up to 10,000 results per query

---

## 📝 Important Notes for Future Sessions

### When Debugging Lambda Issues:

1. **Always check CloudWatch Logs first**:
   ```bash
   aws logs tail /aws/lambda/semantic-scholar-extractor --follow
   ```

2. **Check S3 output**:
   ```bash
   aws s3 ls s3://aisafetyconnect-raw-dev/raw_data/snapshots/ --recursive
   ```

3. **Verify Secrets Manager**:
   ```bash
   aws secretsmanager get-secret-value --secret-id semantic-scholar-api-key
   ```

### When Modifying Code:

1. **Local version** (`semantic_scholar/`) is for testing
2. **Lambda version** (`lambda/semantic_scholar_extractor/`) is production
3. Keep them in sync manually (no build system yet)
4. After changes: `pulumi up` to redeploy

### When Running Extractions:

1. **Test small first**: `papers_per_query=100`, `include_secondary=false`
2. **Then scale up**: Full parameters after testing
3. **Monitor costs**: Lambda is cheap (~$0.03/execution), S3 storage adds up

---

## 📚 Key Files to Reference

### For Understanding the System:

- `DEPLOYMENT.md` - Complete deployment walkthrough
- `lambda/semantic_scholar_extractor/README.md` - Lambda documentation
- `infrastructure/pulumi/README.md` - Pulumi IaC guide

### For Understanding Data:

- `semantic_scholar/ASYNC_IMPLEMENTATION.md` - Async architecture
- `semantic_scholar/RAW_DATA_MODE.md` - Raw data strategy
- `semantic_scholar/analyze_publication_dates.py` - Date coverage analysis

### For Running Extractions:

- `DEPLOYMENT.md` Section: "Historical Data Extraction"
- Example scripts for invoking Lambda multiple times

---

## 🔗 External Resources

- [Semantic Scholar API Docs](https://www.semanticscholar.org/product/api)
- [AWS Lambda Python Runtime](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)
- [Pulumi AWS Documentation](https://www.pulumi.com/docs/clouds/aws/)
- [Parquet Format](https://parquet.apache.org/docs/)

---

## ✅ Quick Commands Reference

```bash
# Deploy Lambda
cd infrastructure/pulumi && pulumi up

# Test Lambda
aws lambda invoke --function-name semantic-scholar-extractor \
  --payload '{"extraction_date": "2024-11-01"}' response.json

# Check Logs
aws logs tail /aws/lambda/semantic-scholar-extractor --follow

# List S3 files
aws s3 ls s3://aisafetyconnect-raw-dev/raw_data/snapshots/ --recursive

# Download Parquet file
aws s3 cp s3://aisafetyconnect-raw-dev/raw_data/snapshots/extraction_date=2024-11-01/area=AI_Safety/papers.parquet ./

# Read Parquet
python -c "import pandas as pd; df = pd.read_parquet('papers.parquet'); print(df.info())"
```

---

## 💡 Tips for Next Claude Code Session

1. **Start by reading this file** to understand current state
2. **Check DEPLOYMENT.md** for step-by-step deployment guide
3. **Run small test first** before full historical extraction
4. **Monitor CloudWatch Logs** during execution
5. **Verify S3 output** after each extraction

---

**End of Context Document**

Last updated: 2024-10-27
Project Status: Code complete, ready for AWS deployment
Next Action: Deploy with Pulumi (`pulumi up`)
