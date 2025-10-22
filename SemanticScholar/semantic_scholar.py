#!/usr/bin/env python3
"""
Semantic Scholar API key
"""

import psycopg2
import psycopg2.extras
import json
import sys
import time
import datetime
import hashlib
import logging
import requests
import os
from typing import List, Dict, Optional, Set
import pandas as pd
from contextlib import contextmanager
from pathlib import Path
import random
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import math

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('semantic_scholar_ultra_optimized.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    import requests_cache
    requests_cache.install_cache("s2_cache_ultra", backend="sqlite", expire_after=60*60*48)  # 48h cache
    logger.info("requests-cache habilitado (TTL 48h)")
except Exception as _:
    logger.info("requests-cache no disponible; continuando sin caché")

class UltraOptimizedSemanticScholarExtractor:
    """
    Extractor ULTRA OPTIMIZADO con estrategias anti-cuello de botella
    """
    
    SEARCH_API = "https://api.semanticscholar.org/graph/v1/paper/search"
    BULK_SEARCH_API = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
    BATCH_API = "https://api.semanticscholar.org/graph/v1/paper/batch"
    MATCH_API = "https://api.semanticscholar.org/graph/v1/paper/search/match"
    SNIPPET_API = "https://api.semanticscholar.org/graph/v1/snippet/search"
    
    PAPER_FIELDS = "title,abstract,authors,year,venue,citationCount,openAccessPdf,externalIds,publicationTypes,publicationDate,fieldsOfStudy,s2FieldsOfStudy,url"
    ENHANCED_PAPER_FIELDS = "title,abstract,authors,year,venue,citationCount,openAccessPdf,externalIds,publicationTypes,publicationDate,fieldsOfStudy,s2FieldsOfStudy,url,referenceCount,influentialCitationCount,isOpenAccess,publicationVenue"
    
    def __init__(self, 
                 host: str = "localhost",
                 port: int = 6543,
                 database: str = "ai_safety",
                 user: str = "scholar_user",
                 password: str = "scholar_pass_2024",
                 api_key: Optional[str] = None):
        
        self.db_config = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }
        
        self.api_key = api_key
        self.headers = {
            "User-Agent": "AIResearchBot/3.0 (AI Safety Research - Ultra Optimized)",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }
        if api_key:
            self.headers["x-api-key"] = api_key
        
        # Ritmo por política para usuarios sin API key
        self.has_api_key = bool(self.api_key)
        self.RPS_TARGET = 0.95 if self.has_api_key else 0.30
        self.BATCH_SIZE = 50 if self.has_api_key else 35
        self.BULK_BATCH_SIZE = 1000 if self.has_api_key else 500  # Para bulk search

        # Delays derivados + jitter corto (cumplimiento)
        self.BASE_DELAY = max(1.05, 1.0 / self.RPS_TARGET)
        self.MIN_DELAY = 1.0 if self.has_api_key else 3.0
        self.MAX_DELAY = 2.0 if self.has_api_key else 4.0
        self.MAX_BACKOFF_DELAY = 120.0

        # Límites adicionales (conservadores)
        self.MAX_PAPERS_PER_DAY = 999999
        self.MAX_PAPERS_PER_SESSION = 9999999
        self.MAX_REQUESTS_PER_HOUR = 600  # Más conservador: 100 req/10min
        
        # Sistema de checkpointing
        self.checkpoint_file = "extraction_checkpoint.json"
        self.checkpoint_interval = 5  # Guardar checkpoint cada N queries

        # Control de estado
        self.papers_today = self.get_papers_count_today()
        self.papers_this_session = 0
        self.requests_this_hour = 0
        self.last_request_time = 0
        self.hour_start_time = time.time()
        
        # ANTI-DUPLICACIÓN: Set de papers ya procesados
        self.processed_paper_ids: Set[str] = set()
        self.load_processed_papers()
        
        # Control de concurrencia
        self.request_lock = threading.Lock()
        
        # Directorio para PDFs
        self.pdf_dir = Path("downloaded_pdfs_ultra")
        self.pdf_dir.mkdir(exist_ok=True)
        
        # Asegurar esquema
        try:
            self.ensure_schema()
        except Exception as e:
            logger.warning(f"No se pudo asegurar el esquema al iniciar: {e}")
    
    def load_processed_papers(self):
        """Cargar IDs de papers ya procesados para evitar duplicados"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT paper_id FROM papers WHERE paper_id IS NOT NULL")
                rows = cursor.fetchall()
                self.processed_paper_ids = {row[0] for row in rows}
                logger.info(f" Cargados {len(self.processed_paper_ids)} papers ya procesados")
        except Exception as e:
            logger.error(f"Error cargando papers procesados: {e}")
            self.processed_paper_ids = set()
    
    @contextmanager
    def get_db_connection(self):
        """Context manager para conexiones a la base de datos"""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error de conexión a DB: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def ensure_schema(self):
        """Crear tablas optimizadas"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Tabla papers sin constraints problemáticos
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS papers (
                    paper_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    authors TEXT,
                    year INT,
                    abstract TEXT,
                    url TEXT,
                    pdf_url TEXT,
                    scholar_url TEXT,
                    venue TEXT,
                    keywords TEXT,
                    citations INT DEFAULT 0,
                    title_hash TEXT,
                    doi TEXT,
                    arxiv_id TEXT,
                    s2_fields JSONB,
                    source TEXT DEFAULT 'semantic_scholar',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            
            # Solo índices de rendimiento, sin constraints únicos problemáticos
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_citations ON papers (citations DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_year ON papers (year);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_created_at ON papers (created_at);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_source ON papers (source);")
            
            # Tabla de logs
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS extraction_logs (
                    id SERIAL PRIMARY KEY,
                    query TEXT,
                    papers_found INT,
                    papers_new INT,
                    papers_updated INT,
                    extraction_mode TEXT,
                    proxy_used TEXT,
                    duration_seconds DOUBLE PRECISION,
                    success BOOLEAN,
                    error_message TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            
            conn.commit()
    
    def test_connection(self) -> bool:
        """Probar conexión a la base de datos"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                logger.info("Conexión a PostgreSQL exitosa")
                return True
        except Exception as e:
            logger.error(f"Error conectando a PostgreSQL: {e}")
            return False
    
    def get_papers_count_today(self) -> int:
        """Obtener número de papers extraídos hoy"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                today = datetime.date.today()
                cursor.execute(
                    "SELECT COUNT(*) FROM papers WHERE DATE(created_at) = %s", 
                    (today,)
                )
                count = cursor.fetchone()[0]
                return count
        except Exception as e:
            logger.error(f"Error obteniendo conteo de papers: {e}")
            return 0
    
    def ultra_conservative_rate_limit(self) -> bool:
        """Rate limiting ultra conservador para evitar bloqueos"""
        with self.request_lock:
            current_time = time.time()
            
            # Reset contador por hora
            if current_time - self.hour_start_time >= 3600:
                self.requests_this_hour = 0
                self.hour_start_time = current_time
            
            # Verificar límites
            if self.papers_today >= self.MAX_PAPERS_PER_DAY:
                logger.warning(f"Límite diario alcanzado: {self.papers_today}/{self.MAX_PAPERS_PER_DAY}")
                return False
            
            if self.papers_this_session >= self.MAX_PAPERS_PER_SESSION:
                logger.warning(f"Límite de sesión alcanzado: {self.papers_this_session}/{self.MAX_PAPERS_PER_SESSION}")
                return False
            
            if self.requests_this_hour >= self.MAX_REQUESTS_PER_HOUR:
                wait_time = 3600 - (current_time - self.hour_start_time)
                logger.warning(f"Límite horario alcanzado. Esperando {wait_time:.1f}s")
                time.sleep(wait_time)
                self.requests_this_hour = 0
                self.hour_start_time = time.time()
            
            # Delay ultra conservador
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.MIN_DELAY:
                sleep_time = self.MIN_DELAY - time_since_last
                time.sleep(sleep_time)
            
            return True
    
    def ultra_safe_http_request(self, url: str, params: Optional[Dict] = None, 
                               headers: Optional[Dict] = None, timeout: int = 30, 
                               max_retries: int = 2) -> Optional[requests.Response]:
        """HTTP request ultra seguro con backoff muy conservador"""
        attempt = 0
        headers = headers or self.headers
        
        while attempt < max_retries:
            if not self.ultra_conservative_rate_limit():
                return None
            
            try:
                with self.request_lock:
                    self.requests_this_hour += 1
                    self.last_request_time = time.time()
                
                response = requests.get(url, params=params, headers=headers, timeout=timeout)
                
                if response.status_code == 200:
                    return response
                
                elif response.status_code == 429:
                    # Rate limit - backoff muy conservador
                    wait_s = min(self.MAX_BACKOFF_DELAY, self.BASE_DELAY * (3 ** attempt) + random.uniform(0.25, 0.75))
                    logger.warning(f"Rate limit (429). Esperando {wait_s:.1f}s (intento {attempt+1}/{max_retries})")
                    time.sleep(wait_s)
                    attempt += 1
                    continue
                
                elif response.status_code in (500, 502, 503, 504):
                    # Server errors - backoff muy conservador
                    wait_s = min(self.MAX_BACKOFF_DELAY, self.BASE_DELAY * (3 ** attempt) + random.uniform(0.5, 1.0))
                    logger.warning(f"Server error {response.status_code}. Esperando {wait_s:.1f}s")
                    time.sleep(wait_s)
                    attempt += 1
                    continue
                
                else:
                    logger.error(f"Error HTTP {response.status_code}: {response.text[:200]}")
                    return None
                    
            except Exception as e:
                wait_s = min(self.MAX_BACKOFF_DELAY, self.BASE_DELAY * (3 ** attempt) + random.uniform(0.25, 0.75))
                logger.warning(f"Excepción en request: {e}. Esperando {wait_s:.1f}s")
                time.sleep(wait_s)
                attempt += 1
        
        logger.error(f"Max reintentos alcanzado para {url}")
        return None
    
    def search_papers_bulk_optimized(self, query: str, limit: int = 1000, 
                                   year_from: int = 2005, min_citations: int = 0,
                                   fields_of_study: str = None) -> List[Dict]:
        """Búsqueda masiva optimizada usando /paper/search/bulk"""
        params = {
            "query": query,
            "limit": min(limit, self.BULK_BATCH_SIZE),
            "fields": self.ENHANCED_PAPER_FIELDS,
            "year": f"{year_from}-",
            "sort": "citationCount:desc"
        }
        
        if min_citations > 0:
            params["minCitationCount"] = str(min_citations)
        
        if fields_of_study:
            params["fieldsOfStudy"] = fields_of_study
        
        response = self.ultra_safe_http_request(self.BULK_SEARCH_API, params=params)
        if not response:
            return []
        
        try:
            data = response.json()
            papers = data.get('data', [])
            total = data.get('total', 0)
            token = data.get('token')  # Para paginación
            
            # FILTRAR DUPLICADOS ANTES DE PROCESAR
            new_papers = []
            for paper in papers:
                paper_id = paper.get('paperId', '')
                if paper_id and paper_id not in self.processed_paper_ids:
                    new_papers.append(paper)
                    self.processed_paper_ids.add(paper_id)
            
            logger.info(f"Bulk Query: '{query}' | Papers: {len(papers)}/{total} | Nuevos: {len(new_papers)} | Token: {token[:20] if token else 'None'}...")
            return new_papers, token
        except Exception as e:
            logger.error(f"Error parsing bulk response: {e}")
            return [], None

    def search_paper_by_title(self, title: str) -> Optional[Dict]:
        """Búsqueda de paper por título exacto usando /paper/search/match"""
        params = {
            "query": title,
            "fields": self.ENHANCED_PAPER_FIELDS
        }
        
        response = self.ultra_safe_http_request(self.MATCH_API, params=params)
        if not response:
            return None
        
        try:
            data = response.json()
            papers = data.get('data', [])
            if papers:
                paper = papers[0]  # Mejor coincidencia
                match_score = paper.get('matchScore', 0)
                logger.info(f"Title match: '{title[:50]}...' | Score: {match_score}")
                return paper
            return None
        except Exception as e:
            logger.error(f"Error parsing title match response: {e}")
            return None

    def search_papers_ultra_optimized(self, query: str, limit: int = 100, 
                                     offset: int = 0, year_from: int = 2005) -> List[Dict]:
        """Búsqueda ultra optimizada con filtrado anti-duplicados"""
        params = {
            "query": query,
            "limit": min(limit, 100),
            "offset": offset,
            "fields": self.PAPER_FIELDS,
            "year": f"{year_from}-"
        }
        
        response = self.ultra_safe_http_request(self.SEARCH_API, params=params)
        if not response:
            return []
        
        try:
            data = response.json()
            papers = data.get('data', [])
            total = data.get('total', 0)
            
            # FILTRAR DUPLICADOS ANTES DE PROCESAR
            new_papers = []
            for paper in papers:
                paper_id = paper.get('paperId', '')
                if paper_id and paper_id not in self.processed_paper_ids:
                    new_papers.append(paper)
                    self.processed_paper_ids.add(paper_id)
            
            logger.info(f"Query: '{query}' | Papers: {len(papers)}/{total} | Nuevos: {len(new_papers)} | Offset: {offset}")
            return new_papers
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return []
    
    @staticmethod
    def _quote(s: str) -> str:
        s = s.strip()
        return f'"{s}"' if (" " in s and not (len(s) >= 2 and s[0] == s[-1] == '"')) else s
    
    
    @staticmethod
    def iter_queries_from_taxonomy_all(schema: Dict) -> List[str]:
        """Generate ALL queries from taxonomy (areas → fields → subtopics) without caps.
        - Includes Primary_Fields and Secondary_Fields fully
        - Adds tiers: area, area+field, area+field+subtopic
        - Preserves insertion order while deduplicating
        """
        def _norm(s: str) -> str:
            return ' '.join((s or '').strip().split())
        def _q(s: str) -> str:
            return UltraOptimizedSemanticScholarExtractor._quote(_norm(s))

        queries: List[str] = []
        seen = set()
        mappings = schema.get("AI_Safety_Research_Mappings", {})

        for area_key, payload in (mappings or {}).items():
            area = _q(area_key.replace("_", " "))
            if area not in seen:
                seen.add(area); queries.append(area)

            def add(q: str):
                if q not in seen:
                    seen.add(q); queries.append(q)

            # Primary Fields
            for field_dict in payload.get("Primary_Fields", []) or []:
                for field, subs in (field_dict or {}).items():
                    field_q = _q(field)
                    add(f"{area} {field_q}")
                    for sub in (subs or []):
                        sub_q = _q(sub)
                        add(f"{area} {field_q} {sub_q}")

            # Secondary Fields
            for field_dict in payload.get("Secondary_Fields", []) or []:
                for field, subs in (field_dict or {}).items():
                    field_q = _q(field)
                    add(f"{area} {field_q}")
                    for sub in (subs or []):
                        sub_q = _q(sub)
                        add(f"{area} {field_q} {sub_q}")

        # technicalAiGovernance
        tag = schema.get("technicalAiGovernance", {})
        if tag:
            core = _q("technical ai governance")
            if core not in seen:
                seen.add(core); queries.append(core)
            for category, dims in tag.items():
                cat_q = _q(str(category).replace("_", " "))
                add_q = f"{core} {cat_q}"
                if add_q not in seen:
                    seen.add(add_q); queries.append(add_q)
                for dim, val in (dims or {}).items():
                    dim_q = _q(str(dim).replace("_", " "))
                    add_q2 = f"{core} {cat_q} {dim_q}"
                    if add_q2 not in seen:
                        seen.add(add_q2); queries.append(add_q2)
                    if isinstance(val, str) and val.strip():
                        val_q = _q(val)
                        add_q3 = f"{core} {cat_q} {val_q}"
                        if add_q3 not in seen:
                            seen.add(add_q3); queries.append(add_q3)

        return queries
    
    def extract_paper_data(self, paper: Dict) -> Dict:
        """Extracción de datos optimizada"""
        title = paper.get('title', '')
        
        # Procesar autores
        authors_list = paper.get('authors', [])
        authors = ', '.join([a.get('name', '') for a in authors_list if a.get('name')])
        
        # URLs / IDs
        external_ids = paper.get('externalIds', {})
        arxiv_id = external_ids.get('ArXiv', '')
        doi = external_ids.get('DOI', '')
        paper_id = paper.get('paperId', '')
        
        # URLs
        direct_url = paper.get('url') or ''
        url = direct_url or (f"https://www.semanticscholar.org/paper/{paper_id}" if paper_id else '')
        
        # PDF URL
        pdf_url = ''
        open_access = paper.get('openAccessPdf')
        if open_access and open_access.get('url'):
            pdf_url = open_access['url']
        elif arxiv_id:
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        
        # Keywords/Fields
        fields = paper.get('s2FieldsOfStudy', [])
        keywords = ', '.join([f.get('category', '') for f in fields if f.get('category')])
        
        # Hash del título
        title_hash = hashlib.md5(title.lower().encode()).hexdigest() if title else None
        
        return {
            'title': title,
            'authors': authors,
            'year': paper.get('year'),
            'abstract': paper.get('abstract', ''),
            'url': url,
            'pdf_url': pdf_url,
            'scholar_url': url,
            'venue': paper.get('venue', ''),
            'keywords': keywords,
            'citations': paper.get('citationCount', 0),
            'title_hash': title_hash,
            'paper_id': paper_id,
            'arxiv_id': arxiv_id,
            'doi': doi,
            's2_fields': fields
        }
    
    def batch_save_papers_ultra(self, papers_data: List[Dict]) -> tuple:
        """Guardar papers en lotes ultra optimizado"""
        new_count = 0
        updated_count = 0
        
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                for paper_data in papers_data:
                    if not paper_data.get('title'):
                        continue
                    
                    paper_id = paper_data.get('paper_id')
                    if not paper_id:
                        paper_id = paper_data.get('title_hash') or hashlib.md5(
                            (paper_data.get('title') or '').lower().encode()
                        ).hexdigest()
                    
                    # UPSERT simple sin constraints problemáticos
                    insert_query = '''
                        INSERT INTO papers 
                        (paper_id, title, authors, year, abstract, url, pdf_url, scholar_url, 
                         venue, keywords, citations, title_hash, doi, arxiv_id, s2_fields, source, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (paper_id) DO UPDATE SET
                            title = EXCLUDED.title,
                            authors = EXCLUDED.authors,
                            year = EXCLUDED.year,
                            abstract = EXCLUDED.abstract,
                            url = EXCLUDED.url,
                            pdf_url = EXCLUDED.pdf_url,
                            scholar_url = EXCLUDED.scholar_url,
                            venue = EXCLUDED.venue,
                            keywords = EXCLUDED.keywords,
                            citations = EXCLUDED.citations,
                            title_hash = EXCLUDED.title_hash,
                            doi = EXCLUDED.doi,
                            arxiv_id = EXCLUDED.arxiv_id,
                            s2_fields = EXCLUDED.s2_fields,
                            source = EXCLUDED.source,
                            updated_at = CURRENT_TIMESTAMP
                    '''
                    
                    cursor.execute(insert_query, (
                        paper_id,
                        paper_data.get('title'),
                        paper_data.get('authors'),
                        paper_data.get('year'),
                        paper_data.get('abstract'),
                        paper_data.get('url'),
                        paper_data.get('pdf_url'),
                        paper_data.get('scholar_url'),
                        paper_data.get('venue'),
                        paper_data.get('keywords'),
                        paper_data.get('citations'),
                        paper_data.get('title_hash'),
                        paper_data.get('doi'),
                        paper_data.get('arxiv_id'),
                        json.dumps(paper_data.get('s2_fields') or []),
                        'semantic_scholar'
                    ))
                    
                    new_count += 1
                
                conn.commit()
                return new_count, updated_count
                
        except Exception as e:
            logger.error(f"Error guardando lote de papers: {e}")
            return 0, 0
    
    def search_and_save_bulk_optimized(self, query: str, max_results: int = 2000, 
                                     year_from: int = 2005, min_citations: int = 0,
                                     fields_of_study: str = None) -> Dict:
        """Búsqueda y guardado masivo optimizado usando bulk API"""
        start_time = time.time()
        papers_found = 0
        papers_new = 0
        papers_updated = 0
        token = None
        
        try:
            logger.info(f"Búsqueda masiva: {query}")
            
            while papers_found < max_results:
                # Usar token si está disponible para paginación
                if token:
                    papers, next_token = self.search_papers_bulk_optimized(
                        query, limit=min(self.BULK_BATCH_SIZE, max_results - papers_found),
                        year_from=year_from, min_citations=min_citations,
                        fields_of_study=fields_of_study
                    )
                else:
                    papers, next_token = self.search_papers_bulk_optimized(
                        query, limit=min(self.BULK_BATCH_SIZE, max_results - papers_found),
                        year_from=year_from, min_citations=min_citations,
                        fields_of_study=fields_of_study
                    )
                
                if not papers:
                    logger.info("No más papers encontrados")
                    break
                
                # Procesar papers
                papers_data = []
                for paper in papers:
                    try:
                        paper_data = self.extract_paper_data(paper)
                        if paper_data['title']:
                            papers_data.append(paper_data)
                    except Exception as e:
                        logger.error(f"Error procesando paper: {e}")
                        continue
                
                # Guardar en lote
                if papers_data:
                    new, updated = self.batch_save_papers_ultra(papers_data)
                    papers_new += new
                    papers_updated += updated
                    papers_found += len(papers_data)
                    
                    self.papers_this_session += len(papers_data)
                    self.papers_today += len(papers_data)
                    
                    logger.info(f"  Procesados: {len(papers_data)} | Total: {papers_found} | Nuevos: {new}")
                
                # Verificar si hay más páginas
                if not next_token:
                    logger.info("No hay más páginas disponibles")
                    break
                
                token = next_token
                
                # Delay entre páginas
                time.sleep(2)
            
            duration = time.time() - start_time
            self.log_extraction(query, papers_found, papers_new, papers_updated, 
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
            logger.error(f"Error en búsqueda masiva: {e}")
            self.log_extraction(query, 0, 0, 0, duration, False, str(e))
            
            return {
                'success': False,
                'papers_found': 0,
                'papers_new': 0,
                'papers_updated': 0,
                'error': str(e)
            }

    def search_and_save_ultra_optimized(self, query: str, max_results: int = 200, 
                                       year_from: int = 2005) -> Dict:
        """Búsqueda y guardado ultra optimizado"""
        start_time = time.time()
        papers_found = 0
        papers_new = 0
        papers_updated = 0
        
        try:
            logger.info(f"Buscando: {query}")
            
            # Paginación conservadora
            offset = 0
            batch_size = self.BATCH_SIZE
            consecutive_empty_batches = 0
            max_empty_batches = 2  # Más estricto
            
            while papers_found < max_results and consecutive_empty_batches < max_empty_batches:
                current_batch_size = min(batch_size, max_results - papers_found)
                papers = self.search_papers_ultra_optimized(
                    query, limit=current_batch_size, offset=offset, year_from=year_from
                )
                
                if not papers:
                    consecutive_empty_batches += 1
                    logger.info(f"Batch vacío {consecutive_empty_batches}/{max_empty_batches}")
                    time.sleep(2)  # Delay más largo
                    continue
                
                consecutive_empty_batches = 0
                
                # Procesar papers
                papers_data = []
                for paper in papers:
                    try:
                        paper_data = self.extract_paper_data(paper)
                        if paper_data['title']:
                            papers_data.append(paper_data)
                    except Exception as e:
                        logger.error(f"Error procesando paper: {e}")
                        continue
                
                # Guardar en lote
                if papers_data:
                    new, updated = self.batch_save_papers_ultra(papers_data)
                    papers_new += new
                    papers_updated += updated
                    papers_found += len(papers_data)
                    
                    self.papers_this_session += len(papers_data)
                    self.papers_today += len(papers_data)
                    
                    logger.info(f"  Procesados: {len(papers_data)} | Total: {papers_found} | Nuevos: {new}")
                
                offset += len(papers)
                
                # Si obtuvimos menos de lo solicitado, no hay más
                if len(papers) < current_batch_size:
                    break
                
                # Delay entre batches
                time.sleep(3)  # Más conservador
            
            duration = time.time() - start_time
            self.log_extraction(query, papers_found, papers_new, papers_updated, 
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
            logger.error(f"Error en búsqueda ultra optimizada: {e}")
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
        """Registrar log de extracción"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO extraction_logs 
                    (query, papers_found, papers_new, papers_updated, extraction_mode,
                     proxy_used, duration_seconds, success, error_message)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    query, papers_found, papers_new, papers_updated,
                    'semantic_scholar_ultra_optimized', 'none', duration, success, error_message
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error guardando log: {e}")
    
    def load_schema_from_json(self, json_path: str) -> Dict:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_terms_from_database(self, area_filter: Optional[str] = None) -> List[Dict]:
        """Cargar términos desde la base de datos (área, field, subfield)"""
        terms = []
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                if area_filter:
                    cursor.execute("""
                        SELECT 
                            a.id as area_id,
                            a.name as area_name,
                            f.id as field_id,
                            f.name as field_name,
                            f.is_primary,
                            sf.id as subfield_id,
                            sf.alias as subfield_name
                        FROM area a
                        LEFT JOIN field f ON a.id = f.area_id
                        LEFT JOIN subfield sf ON f.id = sf.field_id
                        WHERE a.id = %s
                        ORDER BY a.name, f.name, sf.alias
                    """, (area_filter,))
                else:
                    cursor.execute("""
                        SELECT 
                            a.id as area_id,
                            a.name as area_name,
                            f.id as field_id,
                            f.name as field_name,
                            f.is_primary,
                            sf.id as subfield_id,
                            sf.alias as subfield_name
                        FROM area a
                        LEFT JOIN field f ON a.id = f.area_id
                        LEFT JOIN subfield sf ON f.id = sf.field_id
                        ORDER BY a.name, f.name, sf.alias
                    """)
                
                rows = cursor.fetchall()
                
                # Agrupar por área y field
                current_area = None
                current_field = None
                area_data = {}
                
                for row in rows:
                    area_id, area_name, field_id, field_name, is_primary, subfield_id, subfield_name = row
                    
                    if area_id != current_area:
                        if current_area is not None:
                            terms.append(area_data)
                        current_area = area_id
                        area_data = {
                            'area_id': area_id,
                            'area_name': area_name,
                            'fields': {}
                        }
                    
                    if field_id and field_id != current_field:
                        current_field = field_id
                        area_data['fields'][field_id] = {
                            'field_id': field_id,
                            'field_name': field_name,
                            'is_primary': is_primary,
                            'subfields': []
                        }
                    
                    if subfield_id and subfield_name:
                        area_data['fields'][field_id]['subfields'].append({
                            'subfield_id': subfield_id,
                            'subfield_name': subfield_name
                        })
                
                # Agregar la última área
                if current_area is not None:
                    terms.append(area_data)
                
        except Exception as e:
            logger.error(f"Error cargando términos desde base de datos: {e}")
        
        return terms

    def build_queries_from_database(self, include_primary_only: bool = False) -> List[str]:
        """Construir queries desde la base de datos (modo plano)"""
        terms = self.load_terms_from_database()
        queries = []
        
        for area_data in terms:
            area_name = area_data['area_name']
            
            # Query solo con área
            queries.append(area_name)
            
            for field_id, field_data in area_data['fields'].items():
                field_name = field_data['field_name']
                is_primary = field_data['is_primary']
                
                # Filtrar por primary fields si se especifica
                if include_primary_only and not is_primary:
                    continue
                
                # Query área + field
                area_field_query = f"{area_name} {field_name}"
                queries.append(area_field_query)
                
                # Queries área + field + subfield
                for subfield_data in field_data['subfields']:
                    subfield_name = subfield_data['subfield_name']
                    area_field_subfield_query = f"{area_name} {field_name} {subfield_name}"
                    queries.append(area_field_subfield_query)
        
        # Eliminar duplicados manteniendo orden
        seen = set()
        unique_queries = []
        for query in queries:
            if query not in seen:
                seen.add(query)
                unique_queries.append(query)
        
        return unique_queries

    def save_checkpoint(self, query_index: int, total_queries: int, successful_queries: int, 
                       total_papers: int, queries_completed: List[str], start_time: float):
        """Guardar checkpoint del progreso de extracción"""
        try:
            checkpoint_data = {
                "timestamp": time.time(),
                "query_index": query_index,
                "total_queries": total_queries,
                "successful_queries": successful_queries,
                "total_papers": total_papers,
                "queries_completed": queries_completed,
                "start_time": start_time,
                "papers_today": self.papers_today,
                "papers_this_session": self.papers_this_session
            }
            
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2)
            
            logger.info(f"Checkpoint guardado: Query {query_index}/{total_queries}")
            
        except Exception as e:
            logger.error(f"Error guardando checkpoint: {e}")

    def load_checkpoint(self) -> Optional[Dict]:
        """Cargar checkpoint del progreso de extracción"""
        try:
            if not os.path.exists(self.checkpoint_file):
                return None
            
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            
            logger.info(f"Checkpoint cargado: Query {checkpoint_data['query_index']}/{checkpoint_data['total_queries']}")
            return checkpoint_data
            
        except Exception as e:
            logger.error(f"Error cargando checkpoint: {e}")
            return None

    def clear_checkpoint(self):
        """Limpiar checkpoint al completar extracción"""
        try:
            if os.path.exists(self.checkpoint_file):
                os.remove(self.checkpoint_file)
                logger.info("Checkpoint limpiado - extracción completada")
        except Exception as e:
            logger.error(f"Error limpiando checkpoint: {e}")

    def resume_extraction(self, queries: List[str], checkpoint_data: Dict, 
                         use_bulk: bool, max_papers_per_query: int, year_from: int,
                         min_citations: int, fields_of_study: str) -> Dict:
        """Reanudar extracción desde checkpoint"""
        query_index = checkpoint_data['query_index']
        successful_queries = checkpoint_data['successful_queries']
        total_papers = checkpoint_data['total_papers']
        queries_completed = set(checkpoint_data['queries_completed'])
        start_time = checkpoint_data['start_time']
        
        logger.info(f"Reanudando extracción desde query {query_index + 1}")
        logger.info(f"Queries completadas: {len(queries_completed)}")
        logger.info(f"Papers extraídos hasta ahora: {total_papers}")
        
        # Continuar desde donde se quedó
        for i in range(query_index + 1, len(queries)):
            query = queries[i]
            
            # Saltar queries ya completadas
            if query in queries_completed:
                logger.info(f"Saltando query ya completada: {query}")
                continue
            
            logger.info(f"\n Progreso: {i+1}/{len(queries)} (REANUDADO)")
            logger.info(f" Papers hoy: {self.papers_today}/{self.MAX_PAPERS_PER_DAY}")
            logger.info(f" Query: {query}")
            
            if use_bulk:
                result = self.search_and_save_bulk_optimized(
                    query, max_results=max_papers_per_query, year_from=year_from, 
                    min_citations=min_citations, fields_of_study=fields_of_study
                )
            else:
                result = self.search_and_save_ultra_optimized(
                    query, max_results=max_papers_per_query, year_from=year_from
                )
            
            if result['success']:
                successful_queries += 1
                total_papers += result['papers_found']
                queries_completed.add(query)
                logger.info(f" Éxito: {result['papers_new']} nuevos, {result['papers_updated']} actualizados")
            else:
                logger.error(f" Error: {result.get('error', 'Error desconocido')}")
            
            # Guardar checkpoint cada N queries
            if (i + 1) % self.checkpoint_interval == 0:
                self.save_checkpoint(i, len(queries), successful_queries, total_papers, 
                                   list(queries_completed), start_time)
            
            # Delay entre queries
            time.sleep(2)
        
        return {
            'successful_queries': successful_queries,
            'total_papers': total_papers,
            'duration': time.time() - start_time
        }
    
    def run_ultra_optimized_extraction(self, json_path: str = None, max_queries: int = 15, 
                                     year_from: int = 2005, max_papers_per_query: int = 200,
                                     use_bulk: bool = False, min_citations: int = 0, 
                                     fields_of_study: str = None, use_database: bool = True,
                                     include_primary_only: bool = False, resume: bool = True):
        """Ejecutar extracción ultra optimizada"""
        logger.info(" Iniciando extracción ULTRA OPTIMIZADA con Semantic Scholar API")
        
        if not self.test_connection():
            logger.error("No se puede conectar a la base de datos")
            return
        
        # Generar queries desde base de datos o JSON
        if use_database:
            logger.info("Cargando términos desde base de datos...")
            queries = self.build_queries_from_database(include_primary_only=include_primary_only)
            logger.info(f"Cargados {len(queries)} queries desde base de datos")
        else:
            logger.info("Cargando términos desde JSON...")
            schema = self.load_schema_from_json(json_path)
            queries = list(self.iter_queries_from_taxonomy_all(schema))
            logger.info(f"Cargados {len(queries)} queries desde JSON")
        
        # Verificar si hay checkpoint para reanudar
        checkpoint_data = None
        if resume:
            checkpoint_data = self.load_checkpoint()
        
        if checkpoint_data:
            # Reanudar desde checkpoint
            result = self.resume_extraction(queries, checkpoint_data, use_bulk, 
                                          max_papers_per_query, year_from, min_citations, fields_of_study)
            successful_queries = result['successful_queries']
            total_papers = result['total_papers']
            duration = result['duration']
            
            # Limpiar checkpoint al completar
            self.clear_checkpoint()
            
            logger.info(f"\n EXTRACCIÓN REANUDADA Y COMPLETADA:")
            logger.info(f" Queries exitosas: {successful_queries}/{len(queries)}")
            logger.info(f" Total papers: {total_papers}")
            logger.info(f" Papers únicos en DB: {self.get_total_papers_count()}")
            return
        
        # Iniciar extracción nueva
        total_papers = 0
        successful_queries = 0
        consecutive_zero_new = 0
        zero_new_threshold = 50  # Aumentar umbral para no detener prematuramente
        start_time = time.time()
        queries_completed = []
        
        logger.info(f"Ejecutando {len(queries)} queries DIVERSAS")
        
        for i, query in enumerate(queries):
            logger.info(f"\n Progreso: {i+1}/{len(queries)}")
            logger.info(f" Papers hoy: {self.papers_today}/{self.MAX_PAPERS_PER_DAY}")
            logger.info(f" Query: {query}")
            
            if use_bulk:
                result = self.search_and_save_bulk_optimized(
                    query, max_results=max_papers_per_query, year_from=year_from, 
                    min_citations=min_citations, fields_of_study=fields_of_study
                )
            else:
                result = self.search_and_save_ultra_optimized(
                    query, max_results=max_papers_per_query, year_from=year_from
                )
            
            if result['success']:
                successful_queries += 1
                total_papers += result['papers_found']
                queries_completed.append(query)
                logger.info(f" Éxito: {result['papers_new']} nuevos, {result['papers_updated']} actualizados")
                # actualizar contador de racha sin nuevos
                if result.get('papers_new', 0) > 0:
                    consecutive_zero_new = 0
                else:
                    consecutive_zero_new += 1
                    logger.info(f"Racha sin nuevos: {consecutive_zero_new}/{zero_new_threshold}")
                    if consecutive_zero_new >= zero_new_threshold:
                        logger.warning("Umbral de racha sin nuevos alcanzado. Deteniendo la corrida para evitar llamadas inútiles.")
                        break
            else:
                logger.error(f" Falló: {result.get('error', 'Unknown error')}")
                # Las fallas también cuentan para la racha sin nuevos
                consecutive_zero_new += 1
                logger.info(f"Racha sin nuevos: {consecutive_zero_new}/{zero_new_threshold}")
                if consecutive_zero_new >= zero_new_threshold:
                    logger.warning("Umbral de racha sin nuevos alcanzado tras fallos. Deteniendo la corrida.")
                    break
            
            # Guardar checkpoint cada N queries
            if (i + 1) % self.checkpoint_interval == 0:
                self.save_checkpoint(i, len(queries), successful_queries, total_papers, 
                                   queries_completed, start_time)
            
            # Delay entre queries
            if i < len(queries) - 1:
                time.sleep(5)  # Delay más largo entre queries
        
        # Limpiar checkpoint al completar
        self.clear_checkpoint()
        
        logger.info(f"\n EXTRACCIÓN ULTRA OPTIMIZADA COMPLETADA:")
        logger.info(f" Queries exitosas: {successful_queries}/{len(queries)}")
        logger.info(f" Total papers: {total_papers}")
        logger.info(f" Papers únicos en DB: {self.get_total_papers_count()}")
    
    def get_total_papers_count(self) -> int:
        """Obtener total de papers en la base de datos"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM papers")
                count = cursor.fetchone()[0]
                return count
        except Exception as e:
            logger.error(f"Error obteniendo conteo total: {e}")
            return 0
    
    def export_to_csv(self, output_path: str = "ai_safety_papers_ultra_optimized.csv"):
        """Exportar datos a CSV"""
        try:
            with self.get_db_connection() as conn:
                df = pd.read_sql_query(
                    "SELECT * FROM papers ORDER BY citations DESC, created_at DESC", 
                    conn
                )
                df.to_csv(output_path, index=False)
                logger.info(f"Datos exportados a: {output_path}")
                return df
        except Exception as e:
            logger.error(f"Error exportando datos: {e}")
            return None


if __name__ == "__main__":
    # CLI ultra optimizado
    parser = argparse.ArgumentParser(description="Semantic Scholar extractor ULTRA OPTIMIZADO (AI Safety)")
    parser.add_argument("--json-path", default="scraper_terms.json", help="Ruta al JSON de taxonomía/términos")
    parser.add_argument("--max-queries", type=int, default=15, help="Máximo de queries a ejecutar")
    parser.add_argument("--year-from", type=int, default=2005, help="Filtrar por año inicial (inclusive)")
    parser.add_argument("--max-papers-per-query", type=int, default=200, help="Máximo papers por query")
    parser.add_argument("--api-key", default=None, help="API key de Semantic Scholar (opcional)")
    parser.add_argument("--use-bulk", action="store_true", help="Usar API bulk para búsquedas masivas")
    parser.add_argument("--min-citations", type=int, default=0, help="Mínimo número de citas")
    parser.add_argument("--fields-of-study", type=str, default=None, help="Campos de estudio (comma-separated, opcional)")
    parser.add_argument("--search-by-title", type=str, help="Buscar paper específico por título")
    parser.add_argument("--use-database", action="store_true", default=True, help="Usar base de datos para cargar términos (default: True)")
    parser.add_argument("--use-json", action="store_true", help="Usar archivo JSON en lugar de base de datos")
    parser.add_argument("--primary-only", action="store_true", help="Solo incluir primary fields en queries")
    parser.add_argument("--no-resume", action="store_true", help="No reanudar desde checkpoint (iniciar desde cero)")
    parser.add_argument("--checkpoint-interval", type=int, default=5, help="Intervalo para guardar checkpoints (default: 5)")
    # DB flags
    parser.add_argument("--db-host", default="localhost", help="Host de PostgreSQL")
    parser.add_argument("--db-port", type=int, default=6543, help="Puerto de PostgreSQL")
    parser.add_argument("--db-name", default="ai_safety", help="Nombre de la base de datos")
    parser.add_argument("--db-user", default="scholar_user", help="Usuario de la base de datos")
    parser.add_argument("--db-password", default="scholar_pass_2024", help="Password de la base de datos")
    args = parser.parse_args()
    
    # Configuración
    API_KEY = args.api_key
    
    extractor = UltraOptimizedSemanticScholarExtractor(
        host=args.db_host,
        port=args.db_port,
        database=args.db_name,
        user=args.db_user,
        password=args.db_password,
        api_key=API_KEY
    )
    
    # Ejecutar extracción  optimizada
    # Ejecutar extracción ultra optimizada
    if args.search_by_title:
        # Búsqueda por título específico
        logger.info(f"Buscando paper por título: {args.search_by_title}")
        paper = extractor.search_paper_by_title(args.search_by_title)
        if paper:
            paper_data = extractor.extract_paper_data(paper)
            new, updated = extractor.batch_save_papers_ultra([paper_data])
            logger.info(f"Paper encontrado: {paper_data['title']} | Nuevo: {new} | Actualizado: {updated}")
        else:
            logger.info("Paper no encontrado")
    else:
        # Extracción normal
        use_database = args.use_database and not args.use_json
        extractor.checkpoint_interval = args.checkpoint_interval
        extractor.run_ultra_optimized_extraction(
            json_path=args.json_path,
            max_queries=args.max_queries,
            year_from=args.year_from,
            max_papers_per_query=args.max_papers_per_query,
            use_bulk=args.use_bulk,
            min_citations=args.min_citations,
            fields_of_study=args.fields_of_study,
            use_database=use_database,
            include_primary_only=args.primary_only,
            resume=not args.no_resume
        )
    
    # Exportar resultados
    df = extractor.export_to_csv()
    
    if df is not None:
        print(f"\n Resumen de extracción optimizada:")
        print(f"Total papers: {len(df)}")
        print(f"Papers con URLs: {len(df[df['url'].notna()])}")
        print(f"Papers con PDFs: {len(df[df['pdf_url'].notna()])}")
        print(f"Rango de años: {df['year'].min()} - {df['year'].max()}")
        print(f"Total de citas: {df['citations'].sum()}")
