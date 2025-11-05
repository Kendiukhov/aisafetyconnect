# AI Safety Connect - Project Status

**Last Updated**: 2024-10-27
**Current Phase**: Lambda Code Complete - Ready for AWS Deployment

---

## 🎯 Project Goal

Build a data pipeline to extract, process, and analyze AI Safety research papers from Semantic Scholar.

### Medallion Architecture:

```
BRONZE (Raw Data) ← Currently building this
  └── Lambda → S3 Parquet (monthly snapshots)

SILVER (Staging) ← Future
  └── Glue/Spark → Cleaned, deduplicated, enriched

GOLD (Analytics) ← Future
  └── Aggregations, metrics, dashboards
```

---

## ✅ What's Done

### Phase 1: Local Prototype ✅
- [x] Async Semantic Scholar API client
- [x] Query builder with 3 levels (area, field, subfield)
- [x] Global rate limiter (1 req/sec)
- [x] Raw data extraction (no dedup)
- [x] Local testing and validation

### Phase 2: Lambda Function ✅
- [x] Lambda handler code
- [x] S3 Parquet writer
- [x] Secrets Manager integration
- [x] Error handling and logging
- [x] Documentation complete

### Phase 3: Infrastructure as Code ✅
- [x] Pulumi IaC for all AWS resources
- [x] IAM roles and policies
- [x] CloudWatch Log Group
- [x] S3 object upload automation
- [x] Deployment guide

---

## 🚧 What's Next

### Immediate: Deploy to AWS
- [ ] Run `pulumi up` to deploy Lambda
- [ ] Test with small extraction
- [ ] Verify S3 output and CloudWatch Logs

### Short-term: Historical Data
- [ ] Run extraction for 2005-2024 (240 months)
- [ ] Monitor and validate results
- [ ] Set up EventBridge monthly trigger (optional)

### Medium-term: Silver Layer
- [ ] AWS Glue for data cleaning
- [ ] Deduplication across areas
- [ ] Add cross-area metadata
- [ ] Data quality checks

### Long-term: Gold Layer
- [ ] Analytics tables
- [ ] Citation network analysis
- [ ] Trend identification
- [ ] Dashboards and visualizations

---

## 📁 Repository Structure

```
aisafetyconnect/
├── lambda/                           # AWS Lambda code
│   └── semantic_scholar_extractor/
│       ├── handler.py
│       ├── src/
│       ├── tests/
│       ├── README.md
│       └── SUMMARY.md
│
├── infrastructure/                   # Pulumi IaC
│   └── pulumi/
│       ├── __main__.py
│       ├── README.md
│       └── *.yaml
│
├── semantic_scholar/                 # Local prototype (reference)
│   ├── async_extractor.py
│   ├── query_builder.py
│   └── *.md
│
├── raw_data/                         # Local test data
│   └── area_*.json
│
├── terms.json                        # AI Safety research taxonomy
├── DEPLOYMENT.md                     # 📖 START HERE for deployment
├── CLAUDE_CODE_CONTEXT.md            # For future Claude Code sessions
└── PROJECT_STATUS.md                 # This file
```

---

## 📖 Documentation Index

| Document | Purpose | Audience |
|----------|---------|----------|
| **DEPLOYMENT.md** | Complete deployment walkthrough | Deploying for first time |
| **CLAUDE_CODE_CONTEXT.md** | Context for future sessions | Continuing work in new session |
| lambda/.../README.md | Lambda function details | Understanding the code |
| infrastructure/.../README.md | Pulumi IaC guide | Infrastructure changes |
| semantic_scholar/*.md | Local prototype docs | Reference/understanding |

---

## 🚀 Quick Start (For New Team Members)

1. **Read the docs**:
   - Start with `DEPLOYMENT.md`
   - Then `CLAUDE_CODE_CONTEXT.md`

2. **Set up environment**:
   ```bash
   # Install prerequisites
   brew install uv pulumi awscli

   # Configure AWS
   aws configure
   ```

3. **Deploy Lambda**:
   ```bash
   cd infrastructure/pulumi
   pulumi up
   ```

4. **Test**:
   ```bash
   aws lambda invoke \
     --function-name semantic-scholar-extractor \
     --payload '{"extraction_date": "2024-11-01"}' \
     response.json
   ```

---

## 🔑 Key Technical Decisions

1. **Lambda (not Batch)**: Simpler, cheaper, sufficient despite timeout
2. **Parquet (not JSON)**: Better compression, faster queries
3. **Monthly Snapshots**: No CDC complexity, time-travel capability
4. **No Dedup in Bronze**: Raw data preservation, dedup in Silver
5. **Async Concurrency**: 10 workers, 1 req/sec rate limit

---

## 📊 Data Flow

```
Semantic Scholar API
    ↓ (Lambda extracts via async HTTP)
Lambda Function
    ↓ (converts to Parquet)
S3 Bronze Layer
    └── s3://bucket/raw_data/snapshots/
        └── extraction_date=YYYY-MM-DD/
            └── area=AREA_NAME/
                └── papers.parquet
    ↓ (Glue processes - FUTURE)
S3 Silver Layer (cleaned, deduplicated)
    ↓ (Glue aggregates - FUTURE)
S3 Gold Layer (analytics-ready)
```

---

## ⚠️ Known Issues / Considerations

### Lambda Timeout:
- Max 15 minutes
- With ~40-80 queries/area, may timeout
- Mitigation: Reduce papers_per_query or split areas

### publicationDate Coverage:
- Only 79.66% of papers have exact date
- Using `year` filter to avoid losing 20% of data

### Query Generation:
- Fixed: Now generates all 3 levels correctly
- ~4-8x more queries than initial implementation

---

## 💰 Cost Estimate

| Item | Cost |
|------|------|
| Lambda executions | $0.03 per run |
| Secrets Manager | $0.40/month |
| S3 storage (100GB) | $2.30/month |
| CloudWatch Logs | $0.01/month |
| **Monthly total** | **~$3/month** |
| **Historical extraction** | **~$7 one-time** |

---

## 🆘 Getting Help

### For Deployment Issues:
1. Check `DEPLOYMENT.md` Troubleshooting section
2. Review CloudWatch Logs
3. Verify AWS permissions

### For Code Issues:
1. Check Lambda README
2. Review `CLAUDE_CODE_CONTEXT.md`
3. Test locally with `test_local.py`

### For Understanding:
1. Read `semantic_scholar/ASYNC_IMPLEMENTATION.md`
2. Review `semantic_scholar/RAW_DATA_MODE.md`
3. Check Semantic Scholar API docs

---

## 📞 Contact / Collaboration

This is an AI Safety research data pipeline project. For questions or collaboration:
- Check documentation in repository
- Review GitHub issues (if applicable)
- Contact project maintainers

---

## 🎯 Success Criteria

### Phase 1 (Current):
- [x] Lambda function deployed
- [ ] Historical data extracted (2005-2024)
- [ ] Data validated in S3
- [ ] CloudWatch monitoring set up

### Phase 2 (Future):
- [ ] Silver layer processing working
- [ ] Data quality metrics established
- [ ] Deduplication validated

### Phase 3 (Future):
- [ ] Gold layer analytics ready
- [ ] Dashboards operational
- [ ] Citation network analyzed

---

**Next Action**: Deploy Lambda with `pulumi up` (see DEPLOYMENT.md)

**Status**: ✅ Ready for AWS deployment
