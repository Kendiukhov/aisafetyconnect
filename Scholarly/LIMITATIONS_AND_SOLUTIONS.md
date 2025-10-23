# Scholarly Extractor Documentation

## Overview
The `ScholarlyExtractorPostgres` extracts academic papers from Google Scholar using the `scholarly` Python library, with PostgreSQL storage.

## Key Features

### Data Extraction
- **Title**: From `bib.title`
- **Authors**: From `bib.author` (converted to string)
- **Year**: From `bib.pub_year`
- **Abstract**: From `bib.abstract`
- **URL**: From `pub_url`
- **PDF URL**: From `eprint_url`
- **Venue**: From `bib.venue`
- **Citations**: From `num_citations`

### Operation Modes

#### Fast Mode (`fast_mode=True`)
- Uses basic search results only
- Skips `scholarly.fill()`
- Faster but limited data
- Recommended for bulk extractions

#### Complete Mode (`fast_mode=False`)
- Uses `scholarly.fill()` for papers with >10 citations
- More complete data
- Slower due to Google Scholar rate limiting
- Recommended for high-impact papers

## Main Limitations & Solutions

### 1. Truncated Data
**Problem**: Google Scholar provides truncated snippets in search results.
- Abstracts cut to ~200 characters
- Long titles may be truncated
- Incomplete information in basic results

**Solution**: 
```python
if not fast_mode and pub.get('num_citations', 0) > 10:
    filled_pub = scholarly.fill(pub)
    bib = filled_pub.get('bib', bib)
```

### 2. Rate Limiting & Captchas
**Problem**: Google Scholar detects automated queries and shows captchas.
```
INFO - Got a captcha request.
ERROR - Cannot Fetch from Google Scholar.
```

**Solutions**:
- Query delays (8+ seconds)
- Rotating proxies (with limitations)
- Fast mode to reduce load

### 3. Data Inconsistencies
**Problem**: Variable data structure between papers.
- `authors` can be list or string
- `year` can be string or int
- Optional fields may be missing

**Solution**: Data validation and normalization

## Data Structure

### PaperData Class
```python
@dataclass
class PaperData:
    title: str
    authors: str
    year: Optional[int]
    abstract: str
    url: str
    pdf_url: str
    scholar_url: str
    venue: str
    keywords: str
    citations: int
    title_hash: str
```

### Database Schema
```sql
CREATE TABLE paper (
    paper_id text PRIMARY KEY,
    title text NOT NULL,
    authors text,
    year int,
    abstract text,
    url text,
    pdf_url text,
    scholar_url text,
    venue text,
    keywords text,
    citations int DEFAULT 0,
    title_hash text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
```

## Configuration

### DatabaseConfig
```python
@dataclass
class DatabaseConfig:
    host: str = "localhost"
    port: int = 5434
    database: str = "ai_safety"
    user: str = "scholar_user"
    password: str = "scholar_pass_2024"
```

### ExtractionConfig
```python
@dataclass
class ExtractionConfig:
    min_delay: int = 8  # seconds between requests
    max_papers_per_day: int = 200
    max_papers_per_session: int = 50
    max_terms_per_query: int = 3
    max_results_per_query: int = 5
```

## Usage Examples

### Fast Extraction
```python
extractor = ScholarlyExtractorPostgres()
extractor.run_bootstrap_extraction(
    max_queries=10,
    fast_mode=True,
    year_from=2005,
    year_to=2026
)
```

### High-Impact Papers
```python
extractor.run_bootstrap_extraction(
    max_queries=5,
    fast_mode=False,
    year_from=2005,
    year_to=2026
)
```

## Performance Metrics

### Extraction Times
- **Fast Mode**: 2-5 seconds per paper
- **Complete Mode**: 10-30 seconds per paper
- **With Captcha**: 2-5 minutes per paper (fails)

### Success Rates
- **Fast Mode**: ~90% success
- **Complete Mode**: ~70% success (due to captchas)
- **With Proxies**: ~80% success

### Data Quality
- **Fast Mode**: Abstracts ~200 characters
- **Complete Mode**: Full abstracts for important papers
- **Basic Data**: Always available (title, authors, year, URL)

## Google Scholar Limitations

### 1. Incomplete Data
- Truncated abstracts in basic results
- Limited information without `scholarly.fill()`
- Data format inconsistencies

### 2. Rate Limiting
- Frequent captchas with intensive use
- Required delays between queries
- Temporary blocks

### 3. Structure Dependency
- Google Scholar changes can break extraction
- No official API guarantee
- Fragile HTML parsing

## Alternative Sources

### 1. Semantic Scholar API / OpenAlex
- Official and stable API
- More complete data
- More generous rate limits
- Requires additional implementation

### 2. ArXiv API
- Only for ArXiv papers
- Complete and structured data
- No strict rate limiting
- Limited to certain domains

## Recommendations

### For Production Use
1. Use fast mode for bulk extractions
2. Implement long delays (10+ seconds)
3. Use rotating proxies to avoid blocks
4. Monitor logs for captcha detection
5. Have fallbacks when Google Scholar fails

### For Complete Data
1. Combine multiple sources (Google Scholar + Semantic Scholar)
2. Use complete mode only for important papers
3. Implement caching to avoid re-extractions
4. Validate data before storing

## Conclusion

The `scholarly` extractor is functional but has inherent limitations due to:
- Unofficial nature of Google Scholar API
- Rate limiting and bot detection
- Truncated data in basic results

For production use, it's recommended to:
- Use fast mode for volume
- Implement multiple data sources
- Have fallback strategies
- Monitor and adjust rate limiting as needed