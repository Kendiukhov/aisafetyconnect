# AI Safety Connect - Papers Extraction System

A comprehensive system for extracting and analyzing AI Safety research papers from Semantic Scholar API.

## Project Structure

```
├── src/                           # Source code
│   └── semantic_scholar.py        # Main extraction script
├── scripts/                       # Utility scripts
│   └── generate_top_papers_ranking.py  # Ranking generation
├── config/                        # Configuration files
│   ├── database_schema.dbml       # Database schema
│   ├── docker-compose.yml         # Docker configuration
│   ├── requirements.txt           # Python dependencies
│   └── scraper_terms.json         # Taxonomy definitions
├── data/                          # Data files
│   ├── ai_safety_papers_ultra_optimized.csv  # Main dataset (12,371 papers)
│   ├── top_papers_by_citations.csv           # Top 100 by citations
│   ├── top_papers_by_year.csv               # Top papers by year
│   ├── top_papers_by_venue.csv              # Top papers by venue
│   ├── s2_cache*.sqlite                     # HTTP cache files
│   └── downloaded_pdfs*/                    # PDF storage
├── docs/                          # Documentation
│   ├── ACTIVITIES_REPORT_SEP29.md
│   └── ACTIVITIES_REPORT_SEPTEMBER_30_2025.md
├── logs/                          # Log files
│   ├── semantic_scholar_extraction.log
│   ├── semantic_scholar_extraction_optimized.log
│   └── semantic_scholar_ultra_optimized.log
└── documentation/                 # Additional documentation
    ├── ai-safety-connect-pipeline.md
    ├── extraction-layer-architecture.md
    └── LESSWRONG_*.md
```

## Key Features

- **Exhaustive Taxonomy Coverage**: 397 queries covering all AI Safety research areas
- **Optimized Rate Limiting**: 0.30 RPS for unauthenticated users
- **Intelligent Deduplication**: 100% unique papers (12,371 total)
- **PostgreSQL Integration**: Docker-based database with proper schema
- **Comprehensive Rankings**: Top papers by citations, year, and venue
- **Robust Error Handling**: Exponential backoff and retry mechanisms

## Results Summary

- **Total Papers Extracted**: 12,371 unique papers
- **Coverage Period**: 2015-2025
- **Total Citations**: 215,675
- **Unique Venues**: 4,944
- **Success Rate**: 100% (397/397 queries completed)

## Quick Start

1. **Setup Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r config/requirements.txt
   ```

2. **Start Database**:
   ```bash
   docker-compose -f config/docker-compose.yml up -d
   ```

3. **Run Extraction**:
   ```bash
   python src/semantic_scholar.py
   ```

4. **Generate Rankings**:
   ```bash
   python scripts/generate_top_papers_ranking.py
   ```

## Database Schema

The system uses PostgreSQL with the following main tables:
- `papers`: Core paper information with JSONB fields
- `extraction_logs`: Detailed extraction tracking

See `config/database_schema.dbml` for complete schema.

## Performance Metrics

- **Extraction Rate**: ~3,093 papers/hour
- **Deduplication Efficiency**: 100%
- **Rate Limit Compliance**: 0.30 RPS maintained
- **Cache Hit Rate**: Optimized with SQLite caching

## Documentation

- [Activities Report - Sep 29](docs/ACTIVITIES_REPORT_SEP29.md)
- [Activities Report - Sep 30](docs/ACTIVITIES_REPORT_SEPTEMBER_30_2025.md)
- [Database Schema](config/database_schema.dbml)

## License

This project is part of the AI Safety Connect initiative.
