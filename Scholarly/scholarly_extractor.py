#!/usr/bin/env python3
"""
Scholarly Extractor for AI Safety Research
Extracts academic papers using Google Scholar API with taxonomy-based search terms
"""

import json
import sys
import time
import datetime
import hashlib
import logging
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

# Database imports
try:
    import psycopg2
    import psycopg2.extras
    import pandas as pd
except ImportError as e:
    print(f"Database dependencies not installed: {e}")
    print("Install with: pip install psycopg2-binary pandas")

# Scholarly imports
try:
    from scholarly import scholarly, ProxyGenerator
except ImportError as e:
    print(f"Scholarly not installed: {e}")
    print("Install with: pip install scholarly")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scholarly_extraction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration parameters"""
    host: str = "localhost"
    port: int = 5434
    database: str = "ai_safety"
    user: str = "scholar_user"
    password: str = "scholar_pass_2024"


@dataclass
class ExtractionConfig:
    """Extraction configuration parameters"""
    min_delay: int = 60  # 60 seconds between requests (ultra-conservative)
    max_papers_per_day: int = 20  # Very low daily limit
    max_papers_per_session: int = 5  # Very low session limit
    max_terms_per_query: int = 1  # Single term per query
    max_results_per_query: int = 1  # Single result per query


@dataclass
class PaperData:
    """Structured paper data"""
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


class ScholarlyExtractorPostgres:
    def __init__(self, 
                 db_config: Optional[DatabaseConfig] = None,
                 extraction_config: Optional[ExtractionConfig] = None):
        
        self.db_config = db_config or DatabaseConfig()
        self.extraction_config = extraction_config or ExtractionConfig()
        
        # Convert to dict for psycopg2 compatibility
        self.db_params = {
            'host': self.db_config.host,
            'port': self.db_config.port,
            'database': self.db_config.database,
            'user': self.db_config.user,
            'password': self.db_config.password
        }
        
        self.setup_scholarly()
        
        # Counters
        # Reset papers count for testing (don't count existing papers)
        self.papers_today = 0
        self.papers_this_session = 0
        self.last_request_time = 0
        
    @contextmanager
    def get_db_connection(self):
        """
        Context manager for database connections
        """
        conn = None
        try:
            conn = psycopg2.connect(**self.db_params)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result:
                    logger.info("PostgreSQL connection successful")
                    return True
        except Exception as e:
            logger.error(f"Error connecting to PostgreSQL: {e}")
            return False
    
    def setup_scholarly(self):
        """Configure scholarly with proxies"""
        try:
            pg = ProxyGenerator()
            pg.FreeProxies()
            scholarly.use_proxy(pg)
            logger.info("Free proxies configured successfully")
        except Exception as e:
            logger.warning(f"Error configuring proxies: {e}")
    
    def rotate_proxy_and_retry(self, max_retries=3):
        """Rotate proxy and retry with exponential backoff"""
        for attempt in range(max_retries):
            try:
                # Wait with exponential backoff
                wait_time = (2 ** attempt) * 30  # 30s, 60s, 120s
                logger.info(f"Waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                time.sleep(wait_time)
                
                # Try to reconfigure proxy
                pg = ProxyGenerator()
                pg.FreeProxies()
                scholarly.use_proxy(pg)
                logger.info(f"Proxy rotated for attempt {attempt + 1}")
                return True
                
            except Exception as e:
                logger.warning(f"Proxy rotation attempt {attempt + 1} failed: {e}")
                continue
        
        logger.error("All proxy rotation attempts failed")
        return False
    
    def get_papers_count_today(self) -> int:
        """Get number of papers extracted today"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                today = datetime.date.today()
                cursor.execute(
                    "SELECT COUNT(*) FROM paper WHERE DATE(created_at) = %s",
                    (today,)
                )
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting papers count: {e}")
            return 0
    
    def rate_limit_check(self) -> bool:
        """Check if we can make another request based on rate limits"""
        # Check daily limit
        if self.papers_today >= self.extraction_config.max_papers_per_day:
            logger.warning(f"Daily limit reached: {self.papers_today}/{self.extraction_config.max_papers_per_day}")
            return False
        
        # Check session limit
        if self.papers_this_session >= self.extraction_config.max_papers_per_session:
            logger.warning(f"Session limit reached: {self.papers_this_session}/{self.extraction_config.max_papers_per_session}")
            return False
        
        # Check time delay
        current_time = time.time()
        if self.last_request_time > 0:
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.extraction_config.min_delay:
                wait_time = self.extraction_config.min_delay - time_since_last
                logger.info(f"Rate limiting: waiting {wait_time:.1f}s")
                time.sleep(wait_time)
        
        return True
    
    def extract_paper_data(self, pub, fast_mode: bool = False) -> PaperData:
        """Extract paper data from scholarly publication with enhanced data retrieval"""
        bib = pub.get('bib', {})
        authors_field = bib.get('author', '')
        
        if isinstance(authors_field, list):
            authors_json = [{"name": author} for author in authors_field]
            authors_str = ', '.join(authors_field)
        else:
            authors_str = str(authors_field)
            authors_json = [{"name": authors_str}] if authors_str else []
        
        title = bib.get('title', '')
        title_hash = hashlib.md5(title.lower().encode()).hexdigest()
        
        if not fast_mode:
            try:
                if not pub.get('filled', False) and pub.get('num_citations', 0) > 10:
                    logger.info(f"  Filling complete data for high-impact paper: {title[:50]}...")
                    filled_pub = scholarly.fill(pub)
                    bib = filled_pub.get('bib', bib)
                    logger.info(f"  Data filled successfully")
                elif pub.get('num_citations', 0) <= 10:
                    logger.info(f"  Skipping fill for low-citation paper: {pub.get('num_citations', 0)} citations")
            except Exception as e:
                logger.warning(f"  Could not fill complete data: {e}")
                # Continue with original data
        else:
            logger.info(f"  Fast mode: skipping scholarly.fill()")
        
        # Use abstract from Google Scholar
        enhanced_abstract = bib.get('abstract', '')
        
        return PaperData(
            title=bib.get('title', title),
            authors=authors_str,  # Keep as string for display
            year=bib.get('pub_year'),
            abstract=enhanced_abstract,
            url=pub.get('pub_url', ''),
            pdf_url=pub.get('eprint_url', ''),
            scholar_url=pub.get('url_scholarbib', ''),
            venue=bib.get('venue', ''),
            keywords=', '.join(bib.get('keywords', [])),
            citations=pub.get('num_citations', 0),
            title_hash=title_hash
        )
    
    def save_paper(self, paper_data: PaperData) -> bool:
        """Save paper to database, return True if new paper"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check if paper already exists
                cursor.execute("SELECT paper_id FROM paper WHERE title_hash = %s", (paper_data.title_hash,))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing paper
                    cursor.execute('''
                        UPDATE paper SET
                            title = %s, authors = %s, year = %s, abstract = %s,
                            url = %s, pdf_url = %s, scholar_url = %s, venue = %s,
                            keywords = %s, citations = %s, updated_at = NOW()
                        WHERE title_hash = %s
                    ''', (
                        paper_data.title, paper_data.authors, paper_data.year,
                        paper_data.abstract, paper_data.url, paper_data.pdf_url,
                        paper_data.scholar_url, paper_data.venue, paper_data.keywords,
                        paper_data.citations, paper_data.title_hash
                    ))
                    conn.commit()
                    return False  # Not new
                else:
                    # Insert new paper
                    cursor.execute('''
                        INSERT INTO paper 
                        (paper_id, title, authors, year, abstract, url, pdf_url, 
                         scholar_url, venue, keywords, citations, title_hash)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        paper_data.title_hash, paper_data.title, paper_data.authors,
                        paper_data.year, paper_data.abstract, paper_data.url,
                        paper_data.pdf_url, paper_data.scholar_url, paper_data.venue,
                        paper_data.keywords, paper_data.citations, paper_data.title_hash
                    ))
                    conn.commit()
                    return True  # New paper
                    
        except Exception as e:
            logger.error(f"Error saving paper: {e}")
            return False
    
    def search_papers(self, query: str, max_results: Optional[int] = None, 
                     year_from: int = 2005, year_to: int = 2026, 
                     fast_mode: bool = False) -> Dict:
        """Search papers using scholarly library"""
        start_time = time.time()
        papers_found = 0
        papers_new = 0
        papers_updated = 0
        
        try:
            # Rate limiting check
            if not self.rate_limit_check():
                return {
                    'success': False,
                    'papers_found': 0,
                    'papers_new': 0,
                    'papers_updated': 0,
                    'error': 'Rate limit exceeded'
                }
            
            if max_results is None:
                max_results = self.extraction_config.max_results_per_query
            
            # Construct query with year filter
            year_query = f"{query} after:{year_from} before:{year_to}"
            logger.info(f"Searching: {year_query}")
            
            # Search using scholarly
            search_query = scholarly.search_pubs(year_query)
            
            for i, pub in enumerate(search_query):
                if i >= max_results:
                    break
                
                try:
                    # Extract paper data
                    paper_data = self.extract_paper_data(pub, fast_mode)
                    
                    # Filter by year range (additional check)
                    if paper_data.year is not None:
                        try:
                            year_int = int(paper_data.year) if isinstance(paper_data.year, str) else paper_data.year
                            if year_int < year_from or year_int > year_to:
                                logger.info(f"  Skipping paper from {year_int} (outside range {year_from}-{year_to})")
                                continue
                        except (ValueError, TypeError):
                            logger.info(f"  Skipping paper with invalid year: {paper_data.year}")
                            continue
                    
                    # Save paper
                    was_new = self.save_paper(paper_data)
                    if was_new:
                        papers_new += 1
                    else:
                        papers_updated += 1
                    
                    papers_found += 1
                    self.papers_this_session += 1
                    self.papers_today += 1
                    
                    year_info = f" ({paper_data.year})" if paper_data.year else " (no year)"
                    logger.info(f"  {papers_found}. {paper_data.title[:50]}...{year_info}")
                    logger.info(f"     {paper_data.url}")
                    logger.info(f"     {paper_data.citations} citations")
                    
                    # Rate limiting between papers
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"   Error processing paper: {e}")
                    continue
            
            self.last_request_time = time.time()
            
            # Log extraction
            duration = time.time() - start_time
            self.log_extraction(year_query, papers_found, papers_new, papers_updated, 
                              duration, True, None)
            
            return {
                'success': True,
                'papers_found': papers_found,
                'papers_new': papers_new,
                'papers_updated': papers_updated,
                'duration': duration
            }
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error in search: {e}")
            
            # Try proxy rotation and retry once
            if "captcha" in str(e).lower() or "blocked" in str(e).lower():
                logger.info("Attempting proxy rotation and retry...")
                if self.rotate_proxy_and_retry():
                    logger.info("Retrying search with new proxy...")
                    return self.search_papers(query, max_results, year_from, year_to, fast_mode)
            
            self.log_extraction(query, 0, 0, 0, duration, False, str(e))
            
            return {
                'success': False,
                'papers_found': 0,
                'papers_new': 0,
                'papers_updated': 0,
                'error': str(e)
            }
    
    def log_extraction(self, query: str, papers_found: int, papers_new: int, 
                      papers_updated: int, duration: float, success: bool, 
                      error_message: Optional[str]):
        """Log extraction results"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO extraction_logs 
                    (query, papers_found, papers_new, papers_updated, extraction_mode,
                     proxy_used, duration_seconds, success, error_message)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    query,
                    papers_found,
                    papers_new,
                    papers_updated,
                    'bootstrap' if self.papers_today < 9999999 else 'delta',
                    'free_proxy',
                    duration,
                    success,
                    error_message
                ))
                
                conn.commit()
        except Exception as e:
            logger.error(f"Error saving log: {e}")
    
    def load_terms_from_database(self, area_filter: Optional[str] = None) -> List[str]:
        """Load search terms from database tables"""
        terms = []
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Load from area table
                if area_filter:
                    cursor.execute("SELECT name FROM area WHERE name = %s", (area_filter,))
                else:
                    cursor.execute("SELECT name FROM area")
                
                areas = cursor.fetchall()
                terms.extend([area[0] for area in areas])
                
                # Load from field table
                if area_filter:
                    cursor.execute("""
                        SELECT f.name FROM field f 
                        JOIN area a ON f.area_id = a.id 
                        WHERE a.name = %s
                    """, (area_filter,))
                else:
                    cursor.execute("SELECT name FROM field")
                
                fields = cursor.fetchall()
                terms.extend([field[0] for field in fields])
                
                # Load from subfield table
                if area_filter:
                    cursor.execute("""
                        SELECT sf.name FROM subfield sf 
                        JOIN field f ON sf.field_id = f.id 
                        JOIN area a ON f.area_id = a.id 
                        WHERE a.name = %s
                    """, (area_filter,))
                else:
                    cursor.execute("SELECT name FROM subfield")
                
                subfields = cursor.fetchall()
                terms.extend([subfield[0] for subfield in subfields])
                
        except Exception as e:
            logger.error(f"Error loading terms from database: {e}")
        
        return list(set(terms))  # Remove duplicates
    
    def load_terms_from_json(self, json_path: str) -> List[str]:
        """Load search terms from JSON file (legacy method)"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            terms = []
            for area_name, area_data in data.items():
                terms.append(area_name)
                
                # Add primary fields
                for field_name in area_data.get('Primary_Fields', []):
                    terms.append(field_name)
                
                # Add secondary fields
                for field_name in area_data.get('Secondary_Fields', []):
                    terms.append(field_name)
            
            return terms
        except Exception as e:
            logger.error(f"Error loading terms from JSON: {e}")
            return []
    
    def build_queries(self, terms: List[str], base_topic: str = "") -> List[str]:
        """Build search queries from terms"""
        queries = []
        
        # Group terms into batches
        batch_size = self.extraction_config.max_terms_per_query
        for i in range(0, len(terms), batch_size):
            batch = terms[i:i + batch_size]
            query = f"{base_topic} {' '.join(batch)}".strip()
            queries.append(query)
        return queries
    
    def run_bootstrap_extraction(self, max_queries: int = 10, 
                               area_filter: Optional[str] = None,
                               use_database: bool = True,
                               year_from: int = 2005,
                               year_to: int = 2026,
                               fast_mode: bool = False):
        """Run bootstrap extraction (initial run)"""
        mode = "FAST" if fast_mode else "COMPLETE"
        logger.info(f"Starting BOOTSTRAP extraction ({mode} mode, years {year_from}-{year_to})")
        
        if not self.test_connection():
            logger.error("Cannot connect to database")
            return
        
        if use_database:
            terms = self.load_terms_from_database(area_filter=area_filter)
            logger.info(f"Loaded {len(terms)} terms from database")
        else:
            terms = self.load_terms_from_json("terms.json")
            logger.info(f"Loaded {len(terms)} terms from JSON")
        
        queries = self.build_queries(terms)
        queries = queries[:max_queries]
        
        total_papers = 0
        successful_queries = 0
        
        for i, query in enumerate(queries):
            logger.info(f"\nProgress: {i+1}/{len(queries)}")
            logger.info(f"Papers today: {self.papers_today}/{self.extraction_config.max_papers_per_day}")
            
            result = self.search_papers(query, year_from=year_from, year_to=year_to, fast_mode=fast_mode)
            
            if result['success']:
                successful_queries += 1
                total_papers += result['papers_found']
                logger.info(f"Success: {result['papers_new']} new, {result['papers_updated']} updated")
            else:
                logger.error(f"Failed: {result.get('error', 'Unknown error')}")
            
            if i < len(queries) - 1:
                logger.info("Waiting 10 seconds...")
                time.sleep(10)
        
        logger.info(f"\nBOOTSTRAP COMPLETED:")
        logger.info(f"Successful queries: {successful_queries}/{len(queries)}")
        logger.info(f"Total papers: {total_papers}")
        logger.info(f"Unique papers in DB: {self.get_total_papers_count()}")
    
    def get_total_papers_count(self) -> int:
        """Get total number of papers in database"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM paper")
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting total papers count: {e}")
            return 0
    
    def export_to_csv(self, output_path: str = "ai_safety_papers_export.csv"):
        """Export papers to CSV file"""
        try:
            with self.get_db_connection() as conn:
                df = pd.read_sql_query(
                    "SELECT * FROM paper ORDER BY created_at DESC",
                    conn
                )
                
                df.to_csv(output_path, index=False)
                logger.info(f"Data exported to: {output_path}")
                return df
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return None


if __name__ == "__main__":
    # Conservative but functional configuration
    extraction_config = ExtractionConfig(
        min_delay=30,  # 30 seconds between requests
        max_papers_per_day=100,  # Higher limit for testing
        max_papers_per_session=5,  # 5 papers per session
        max_terms_per_query=1,  # Single term
        max_results_per_query=2,  # 2 results per query
    )
    
    extractor = ScholarlyExtractorPostgres(extraction_config=extraction_config)
    
    try:
        # Run conservative extraction
        extractor.run_bootstrap_extraction(
            max_queries=1,  # Only 1 query
            use_database=True,
            year_from=2005,  # Full range as configured
            year_to=2026,
            fast_mode=True
        )
        
        # Export results
        df = extractor.export_to_csv()
        if df is not None:
            print(f"\nExtraction summary:")
            print(f"Total papers: {len(df)}")
            print(f"Papers with URLs: {len(df[df['url'].notna()])}")
            print(f"Papers with PDFs: {len(df[df['pdf_url'].notna()])}")
    
    except KeyboardInterrupt:
        print("\nExtraction interrupted by user")
    except Exception as e:
        print(f"Error during extraction: {e}")
    finally:
        print("Resources cleaned up")
