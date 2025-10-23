# AI Safety Research Data Extractors

This repository contains a comprehensive suite of data extractors for AI Safety research papers from multiple academic sources. The project implements optimized extraction strategies for Google Scholar, OpenAlex, and Semantic Scholar APIs.

##  Features

- **Multi-Source Extraction**: Support for Google Scholar, OpenAlex, and Semantic Scholar
- **Database-Driven Taxonomy**: Uses PostgreSQL with hierarchical taxonomy structure
- **Optimized Performance**: Ultra-optimized extraction with caching and rate limiting
- **Checkpointing System**: Resume interrupted extractions automatically
- **Comprehensive Logging**: Detailed extraction logs and progress tracking
- **CSV Export**: Automatic export of extracted data to CSV format

##  Project Structure

```
├── Scholarly/              # Google Scholar extractor
│   ├── scholarly_extractor.py
│   ├── README.md
│   └── LIMITATIONS_AND_SOLUTIONS.md
├── OpenAlex/               # OpenAlex API extractor
│   ├── Open Alex.py
│   ├── EXTRACTION_SUMMARY.md
│   ├── create_schema.sql
│   └── generate_top_papers_ranking.py
├── SemanticScholar/        # Semantic Scholar API extractor
│   ├── semantic_scholar.py
│   ├── create_schema.sql
│   ├── populate_taxonomy.py
│   └── swagger.json
├── schema.dbml            # Database schema definition
├── terms.json             # AI Safety taxonomy
└── Extractors.ipynb       # Jupyter notebook for analysis
```

##  Database Schema

The project uses PostgreSQL with the following key tables:
- `area`: Research areas (e.g., "Mechanistic Interpretability")
- `field`: Primary and secondary fields within each area
- `subfield`: Specific subfields and techniques
- `paper`: Extracted paper metadata
- `paper_taxonomy`: Mapping between papers and taxonomy
- `paper_concept`: Extracted concepts from papers

##  Setup

### Prerequisites
- Python 3.8+
- PostgreSQL
- Docker (for database containers)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Kendiukhov/aisafetyconnect.git
   cd aisafetyconnect
   ```

2. **Set up virtual environment**:
   ```bash
   # For each extractor
   cd Scholarly && python -m venv venv && source venv/bin/activate
   cd OpenAlex && python -m venv venv && source venv/bin/activate
   cd SemanticScholar && python -m venv venv && source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up database**:
   ```bash
   # Create PostgreSQL container
   docker run -d --name ai_safety_db \
     -e POSTGRES_DB=ai_safety \
     -e POSTGRES_USER=scholar_user \
     -e POSTGRES_PASSWORD=scholar_pass_2024 \
     -p 6543:5432 postgres:13
   
   # Create schema and populate taxonomy
   psql -h localhost -p 6543 -U scholar_user -d ai_safety -f create_schema.sql
   python populate_taxonomy.py
   ```

##  Usage

### Semantic Scholar Extractor (Recommended)
```bash
cd SemanticScholar
source venv/bin/activate
python semantic_scholar.py \
  --api-key "YOUR_API_KEY" \
  --use-database \
  --use-bulk \
  --year-from 2005 \
  --year-to 2026
```

### OpenAlex Extractor
```bash
cd OpenAlex
source venv/bin/activate
python "Open Alex.py" \
  --use-database \
  --use-hierarchical \
  --year-from 2005 \
  --year-to 2026
```

### Google Scholar Extractor
```bash
cd Scholarly
source venv/bin/activate
python scholarly_extractor.py \
  --use-database \
  --year-from 2005 \
  --year-to 2026
```

##  Results

The extractors have successfully extracted:
- **Semantic Scholar**: 23,070 papers (13 minutes, 48 seconds)
- **OpenAlex**: Comprehensive dataset with hierarchical queries
- **Google Scholar**: Limited due to anti-bot measures

##  AI Safety Taxonomy

The project uses a comprehensive taxonomy covering 11 research areas:
1. Mechanistic Interpretability
2. Scalable Oversight
3. Adversarial Robustness
4. Agent Foundations
5. Alignment Theory
6. Evaluations Dangerous Capabilities
7. Value Learning Alignment
8. Cooperative AI
9. AI Governance Policy
10. Compute Governance
11. Technical Governance

##  Performance

- **Semantic Scholar**: ~27 papers/second, 100% success rate
- **OpenAlex**: Optimized with caching and concurrent processing
- **Google Scholar**: Limited by rate limiting and captcha challenges

##  Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

##  License



##  Support

For questions or issues, please open an issue on GitHub or contact the maintainers.
