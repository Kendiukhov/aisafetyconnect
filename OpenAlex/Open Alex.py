#!/usr/bin/env python3
"""
Open Alex (compliant) No API key
Estrategias avanzadas para evitar cuellos de botella
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
from typing import List, Dict, Optional, Set
import pandas as pd
from contextlib import contextmanager
from pathlib import Path
import random
import argparse
import threading
import os
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
import math
from sqlalchemy import create_engine

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('openalex_ultra_optimized.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    import requests_cache
    requests_cache.install_cache("openalex_cache_ultra", backend="sqlite", expire_after=60*60*48)  # 48h cache
    logger.info("requests-cache habilitado (TTL 48h)")
except Exception as _:
    logger.info("requests-cache no disponible; continuando sin caché")

class UltraOptimizedOpenAlexExtractor:
    """
    Extractor ULTRA OPTIMIZADO con estrategias anti-cuello de botella para Open Alex
    """
    
    SEARCH_API = "https://api.openalex.org/works"
    # Open Alex no requiere especificar campos como Semantic Scholar
    # Los campos se especifican en el parámetro 'select' si se desea limitar
    
    def __init__(self, 
                 host: str = "localhost",
                 port: int = 6543,
                 database: str = "ai_safety",
                 user: str = "scholar_user",
                 password: str = "scholar_pass_2024",
                 email: Optional[str] = None):
        
        self.db_config = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }
        
        self.email = email
        self.headers = {
            "User-Agent": "AIResearchBot/3.0 (AI Safety Research - Open Alex Ultra Optimized)",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }
        
        # Open Alex permite 100,000 requests por día - OPTIMIZADO PARA MÁXIMA EXTRACCIÓN
        # Ritmo optimizado para extraer máximo número de papers
        self.RPS_TARGET = 1.0  # 1 request por segundo - más agresivo
        self.BATCH_SIZE = 200  # Open Alex permite hasta 200 por página

        # Delays optimizados para máxima velocidad
        self.BASE_DELAY = max(1.0, 1.0 / self.RPS_TARGET)  # 1 segundo base
        self.MIN_DELAY = 1.0  # Mínimo 1 segundo entre requests
        self.MAX_DELAY = 3.0  # Máximo 3 segundos
        self.MAX_BACKOFF_DELAY = 60.0  # Backoff más corto

        # Límites optimizados para máxima extracción
        self.MAX_PAPERS_PER_DAY = 999999  # Más agresivo para Open Alex
        self.MAX_PAPERS_PER_SESSION = 9999999  # Sesiones más largas
        self.MAX_REQUESTS_PER_HOUR = 999999  # Más requests por hora

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
        self.pdf_dir = Path("downloaded_pdfs_openalex")
        self.pdf_dir.mkdir(exist_ok=True)
        
        # Asegurar esquema
        try:
            self.ensure_schema()
        except Exception as e:
            logger.warning(f"No se pudo asegurar el esquema al iniciar: {e}")

    def get_sqlalchemy_engine(self):
        """Crear SQLAlchemy engine para exportes eficientes y evitar warnings de pandas."""
        user = self.db_config['user']
        password = self.db_config['password']
        host = self.db_config['host']
        port = self.db_config['port']
        database = self.db_config['database']
        uri = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
        return create_engine(uri, pool_pre_ping=True)
    
    def load_processed_papers(self):
        """Cargar IDs de papers ya procesados para evitar duplicados"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT paper_id FROM papers WHERE paper_id IS NOT NULL")
                rows = cursor.fetchall()
                self.processed_paper_ids = {row[0] for row in rows}
                logger.info(f"Cargados {len(self.processed_paper_ids)} papers ya procesados")
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
                    venue TEXT,
                    keywords TEXT,
                    citations INT DEFAULT 0,
                    title_hash TEXT,
                    doi TEXT,
                    arxiv_id TEXT,
                    s2_fields JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            
            # Solo índices de rendimiento, sin constraints únicos problemáticos
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_citations ON papers (citations DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_year ON papers (year);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_created_at ON papers (created_at);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_title ON papers (title);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers (doi);")
            
            # Agregar columna publication_date si no existe
            cursor.execute("""
                ALTER TABLE papers 
                ADD COLUMN IF NOT EXISTS publication_date DATE;
            """)
            
            # Crear índice para publication_date
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_publication_date ON papers (publication_date);")
            
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
            
            # Tabla de checkpointing para reanudación
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS extraction_checkpoints (
                    id SERIAL PRIMARY KEY,
                    query TEXT NOT NULL,
                    cursor TEXT,
                    papers_processed INTEGER DEFAULT 0,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(query, cursor)
                );
                """
            )
            
            conn.commit()
    
    def save_checkpoint(self, query: str, cursor: str, papers_processed: int):
        """Guardar checkpoint para reanudación"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO extraction_checkpoints (query, cursor, papers_processed)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (query, cursor) 
                        DO UPDATE SET papers_processed = %s, created_at = CURRENT_TIMESTAMP
                    """, (query, cursor, papers_processed, papers_processed))
                    conn.commit()
        except Exception as e:
            logger.warning(f"Error guardando checkpoint: {e}")
    
    def load_checkpoint(self, query: str) -> Optional[Dict]:
        """Cargar último checkpoint para una query"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT cursor, papers_processed 
                        FROM extraction_checkpoints 
                        WHERE query = %s 
                        ORDER BY created_at DESC 
                        LIMIT 1
                    """, (query,))
                    result = cur.fetchone()
                    if result:
                        return {"cursor": result[0], "papers_processed": result[1]}
        except Exception as e:
            logger.warning(f"Error cargando checkpoint: {e}")
        return None
    
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
    
    def search_papers_ultra_optimized(self, query: str, limit: int = 9999999, 
                                     cursor: str = "*", year_from: int = 2005, year_to: int = 2026) -> Dict[str, object]:
        """Búsqueda ultra optimizada con filtrado anti-duplicados para Open Alex.
        Devuelve un dict con 'papers' y 'next_cursor' real de OpenAlex.
        """
        # Campos específicos para reducir payload y mejorar performance
        # Solo campos válidos según la documentación de OpenAlex
        select_fields = [
            "id", "title", "publication_date", "authorships", 
            "biblio", "doi", "primary_location", 
            "open_access", "cited_by_count", "abstract_inverted_index"
        ]
        
        params = {
            "search": query,
            "per-page": min(limit, 200),  # Open Alex permite hasta 200 por página
            "cursor": cursor,
            "select": ",".join(select_fields)  # Reducir payload solicitando solo campos necesarios
        }
        
        # Solo agregar mailto si se proporciona un email válido
        if self.email and self.email != "research@example.com" and self.email != "test@example.com":
            params["mailto"] = self.email
        
        # Filtro por fecha granular usando publication_date
        if year_from and year_from > 0 and year_to and year_to > 0:
            params["filter"] = f"from_publication_date:{year_from}-01-01,to_publication_date:{year_to}-12-31"
        elif year_from and year_from > 0:
            params["filter"] = f"from_publication_date:{year_from}-01-01"
        
        response = self.ultra_safe_http_request(self.SEARCH_API, params=params)
        if not response:
            return {"papers": [], "next_cursor": None}
        
        try:
            data = response.json()
            papers = data.get('results', [])  # Open Alex usa 'results' en lugar de 'data'
            meta = data.get('meta', {})
            total = meta.get('count', 0)
            next_cursor = meta.get('next_cursor')
            
            # FILTRAR DUPLICADOS ANTES DE PROCESAR
            new_papers = []
            for paper in papers:
                paper_id = paper.get('id', '').split('/')[-1] if paper.get('id') else ''  # Extraer ID del Open Alex ID
                if paper_id and paper_id not in self.processed_paper_ids:
                    new_papers.append(paper)
                    self.processed_paper_ids.add(paper_id)
            
            logger.info(f"Query: '{query}' | Papers: {len(papers)}/{total} | Nuevos: {len(new_papers)} | Cursor: {cursor}")
            return {"papers": new_papers, "next_cursor": next_cursor}
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return {"papers": [], "next_cursor": None}
    
    @staticmethod
    def _quote(s: str) -> str:
        s = s.strip()
        # Para Open Alex, no usar comillas en las queries
        return s
    
    def optimize_query_for_max_results(self, query: str) -> List[str]:
        """Optimiza una query para obtener el máximo número de resultados relevantes"""
        optimized_queries = [query]
        
        # Agregar variaciones de la query para capturar más papers
        if "AI safety" in query.lower():
            optimized_queries.extend([
                query.replace("AI safety", "artificial intelligence safety"),
                query.replace("AI Alignment", "ai alignment"),
               
            ])
        

    

        
        # Remover duplicados y queries muy similares
        unique_queries = []
        for q in optimized_queries:
            if q not in unique_queries and len(q) > 3:
                unique_queries.append(q)
        
        return unique_queries[:3]  # Máximo 3 variaciones por query original
    
    
    @staticmethod
    def iter_queries_from_taxonomy_all(schema: Dict) -> List[str]:
        """Generate ALL queries from taxonomy using Theme + Topic approach consistently.
        - Primary_Fields: area+field, area+field+subtopic
        - Secondary_Fields: area+field, area+field+subtopic  
        - Technical_Governance: category, category+term
        - technicalAiGovernance: core+category, core+category+dimension, core+category+value
        - Preserves insertion order while deduplicating
        - All areas use Theme + Topic approach for optimal balance between specificity and coverage
        """
        def _norm(s: str) -> str:
            return ' '.join((s or '').strip().split())
        def _q(s: str) -> str:
            return UltraOptimizedOpenAlexExtractor._quote(_norm(s))

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

            # Primary Fields - Theme + Topic approach
            for field_dict in payload.get("Primary_Fields", []) or []:
                for field, subs in (field_dict or {}).items():
                    field_q = _q(field)
                    # Theme + Topic: "Mechanistic Interpretability Neuroscience"
                    add(f"{area} {field_q}")
                    for sub in (subs or []):
                        sub_q = _q(sub)
                        # Theme + Topic: "Mechanistic Interpretability Neuroscience Connectomics"
                        add(f"{area} {field_q} {sub_q}")

            # Secondary Fields - Theme + Topic approach
            for field_dict in payload.get("Secondary_Fields", []) or []:
                for field, subs in (field_dict or {}).items():
                    field_q = _q(field)
                    # Theme + Topic: "Adversarial Robustness Cryptography"
                    add(f"{area} {field_q}")
                    for sub in (subs or []):
                        sub_q = _q(sub)
                        # Theme + Topic: "Adversarial Robustness Computer Security Threat modeling"
                        add(f"{area} {field_q} {sub_q}")

            # Technical_Governance (nueva estructura - Tema + Tópico)
            for tech_gov_dict in payload.get("Technical_Governance", []) or []:
                for category, terms in (tech_gov_dict or {}).items():
                    category_q = _q(category)
                    # Solo agregar el tema (categoría) como query independiente
                    add(category_q)
                    for term in (terms or []):
                        term_q = _q(term)
                        # Enfoque Tema + Tópico: "Security Hardware security"
                        add(f"{category_q} {term_q}")

        # technicalAiGovernance - Theme + Topic approach
        tag = schema.get("technicalAiGovernance", {})
        if tag:
            core = _q("technical ai governance")
            if core not in seen:
                seen.add(core); queries.append(core)
            for category, dims in tag.items():
                cat_q = _q(str(category).replace("_", " "))
                # Theme + Topic: "technical ai governance category"
                add_q = f"{core} {cat_q}"
                if add_q not in seen:
                    seen.add(add_q); queries.append(add_q)
                for dim, val in (dims or {}).items():
                    dim_q = _q(str(dim).replace("_", " "))
                    # Theme + Topic: "technical ai governance category dimension"
                    add_q2 = f"{core} {cat_q} {dim_q}"
                    if add_q2 not in seen:
                        seen.add(add_q2); queries.append(add_q2)
                    if isinstance(val, str) and val.strip():
                        val_q = _q(val)
                        # Theme + Topic: "technical ai governance category value"
                        add_q3 = f"{core} {cat_q} {val_q}"
                        if add_q3 not in seen:
                            seen.add(add_q3); queries.append(add_q3)

        return queries
    
    def extract_paper_data(self, paper: Dict) -> Dict:
        """Extracción de datos optimizada para Open Alex"""
        if not isinstance(paper, dict):
            return {}
        title = paper.get('title') or ''
        
        # Procesar autores - Open Alex usa 'authorships'
        authors_list = paper.get('authorships') or []
        safe_authors = []
        for a in authors_list:
            if isinstance(a, dict):
                auth = a.get('author') or {}
                if isinstance(auth, dict):
                    name = auth.get('display_name') or ''
                    if name:
                        safe_authors.append(name)
        authors = ', '.join(safe_authors)
        
        # IDs y URLs - Open Alex estructura diferente
        openalex_id = paper.get('id') or ''
        paper_id = openalex_id.split('/')[-1] if openalex_id else ''
        
        # IDs externos
        external_ids = paper.get('ids') or {}
        if not isinstance(external_ids, dict):
            external_ids = {}
        arxiv_raw = external_ids.get('arxiv')
        arxiv_id = (arxiv_raw or '').replace('arxiv:', '') if arxiv_raw else ''
        doi_raw = external_ids.get('doi')
        doi = (doi_raw or '').replace('https://doi.org/', '') if doi_raw else ''
        
        # URLs
        url = paper.get('id') or ''  # Open Alex ID es la URL principal
        landing_page_url = paper.get('landing_page_url') or ''
        if landing_page_url:
            url = landing_page_url
        
        # PDF URL - Open Alex tiene open_access
        pdf_url = ''
        open_access = paper.get('open_access') or {}
        if isinstance(open_access, dict) and open_access.get('is_oa') and open_access.get('oa_url'):
            pdf_url = open_access['oa_url']
        elif arxiv_id:
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        
        # Venue/Journal (con respaldo a host_venue.display_name)
        venue = ''
        primary_location = paper.get('primary_location') or {}
        if isinstance(primary_location, dict) and primary_location:
            source = primary_location.get('source') or {}
            if isinstance(source, dict):
                venue = source.get('display_name') or ''
        if not venue:
            host_venue = paper.get('host_venue') or {}
            if isinstance(host_venue, dict):
                venue = host_venue.get('display_name') or venue
        
        # Keywords/Concepts - Open Alex usa 'concepts'
        concepts = paper.get('concepts') or []
        safe_concepts = []
        for c in concepts[:10]:
            if isinstance(c, dict):
                dn = c.get('display_name') or ''
                if dn:
                    safe_concepts.append(dn)
        keywords = ', '.join(safe_concepts)  # Top 10 concepts
        
        # Procesar abstract - Open Alex usa formato invertido (optimizado)
        abstract_text = ''
        abstract_inverted = paper.get('abstract_inverted_index')
        if abstract_inverted and isinstance(abstract_inverted, dict):
            # Convertir índice invertido a texto plano (optimizado)
            try:
                words = []
                for word, positions in abstract_inverted.items():
                    if isinstance(positions, list):
                        for pos in positions:
                            words.append((pos, word))
                words.sort(key=lambda x: x[0])
                abstract_text = ' '.join([word for pos, word in words])
                
                # Limpiar y optimizar el abstract
                abstract_text = abstract_text.strip()
                if len(abstract_text) > 5000:  # Limitar longitud para eficiencia
                    abstract_text = abstract_text[:5000] + "..."
                    
            except Exception as e:
                logger.warning(f"Error procesando abstract invertido: {e}")
                abstract_text = ''
        
        # Hash del título
        title_hash = hashlib.md5(title.lower().encode()).hexdigest() if title else None
        
        # Año derivado desde publication_date si existe
        pub_date = paper.get('publication_date') or ''
        try:
            derived_year = int((pub_date or '')[:4]) if pub_date else paper.get('publication_year')
        except Exception:
            derived_year = paper.get('publication_year')

        return {
            'title': title,
            'authors': authors,
            'year': derived_year,
            'publication_date': pub_date,  # Campo granular de fecha
            'abstract': abstract_text,
            'url': url,
            'pdf_url': pdf_url,
            'venue': venue,
            'keywords': keywords,
            'citations': paper.get('cited_by_count', 0),
            'title_hash': title_hash,
            'paper_id': paper_id,
            'arxiv_id': arxiv_id,
            'doi': doi,
            's2_fields': concepts  # Usar concepts como campos
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
                        (paper_id, title, authors, year, abstract, url, pdf_url, 
                         venue, keywords, citations, title_hash, doi, arxiv_id, s2_fields, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, CURRENT_TIMESTAMP)
                        ON CONFLICT (paper_id) DO UPDATE SET
                            title = EXCLUDED.title,
                            authors = EXCLUDED.authors,
                            year = EXCLUDED.year,
                            abstract = EXCLUDED.abstract,
                            url = EXCLUDED.url,
                            pdf_url = EXCLUDED.pdf_url,
                            venue = EXCLUDED.venue,
                            keywords = EXCLUDED.keywords,
                            citations = EXCLUDED.citations,
                            title_hash = EXCLUDED.title_hash,
                            doi = EXCLUDED.doi,
                            arxiv_id = EXCLUDED.arxiv_id,
                            s2_fields = EXCLUDED.s2_fields,
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
                        paper_data.get('venue'),
                        paper_data.get('keywords'),
                        paper_data.get('citations'),
                        paper_data.get('title_hash'),
                        paper_data.get('doi'),
                        paper_data.get('arxiv_id'),
                        json.dumps(paper_data.get('s2_fields') or [])
                    ))
                    
                    new_count += 1
                
                conn.commit()
                return new_count, updated_count
                
        except Exception as e:
            logger.error(f"Error guardando lote de papers: {e}")
            return 0, 0
    
    def search_and_save_ultra_optimized(self, query: str, max_results: int = 200, 
                                       year_from: int = 2005, year_to: int = 2026) -> Dict:
        """Búsqueda y guardado ultra optimizado para Open Alex con checkpointing"""
        start_time = time.time()
        papers_found = 0
        papers_new = 0
        papers_updated = 0
        
        try:
            logger.info(f"Buscando: {query}")
            
            # Cargar checkpoint si existe
            checkpoint = self.load_checkpoint(query)
            cursor = checkpoint.get('cursor', '*') if checkpoint else "*"
            papers_found = checkpoint.get('papers_processed', 0) if checkpoint else 0
            
            if checkpoint:
                logger.info(f"Reanudando desde checkpoint: cursor={cursor}, papers_processed={papers_found}")
            
            batch_size = self.BATCH_SIZE
            consecutive_empty_batches = 0
            max_empty_batches = 3  # Más permisivo para extraer más papers
            checkpoint_interval = 5  # Guardar checkpoint cada 5 lotes
            batch_count = 0
            
            while papers_found < max_results and consecutive_empty_batches < max_empty_batches:
                current_batch_size = min(batch_size, max_results - papers_found)
                result_page = self.search_papers_ultra_optimized(
                    query, limit=current_batch_size, cursor=cursor, year_from=year_from, year_to=year_to
                )
                papers = result_page.get('papers', [])
                next_cursor = result_page.get('next_cursor')
                
                if not papers:
                    consecutive_empty_batches += 1
                    logger.info(f"Batch vacío {consecutive_empty_batches}/{max_empty_batches}")
                    time.sleep(1)  # Delay más corto para ser más eficiente
                    continue
                
                consecutive_empty_batches = 0
                
                # Procesar papers en paralelo para mayor eficiencia (solo parseo, no HTTP)
                papers_data = []
                max_workers = min(8, max(2, os.cpu_count() or 2))
                def _safe_extract(p):
                    try:
                        d = self.extract_paper_data(p)
                        return d if d and d.get('title') else None
                    except Exception as ex:
                        logger.error(f"Error procesando paper: {ex}")
                        return None
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    for d in executor.map(_safe_extract, papers):
                        if d:
                            papers_data.append(d)
                
                # Guardar en lote
                if papers_data:
                    new, updated = self.batch_save_papers_ultra(papers_data)
                    papers_new += new
                    papers_updated += updated
                    papers_found += len(papers_data)
                    
                    self.papers_this_session += len(papers_data)
                    self.papers_today += len(papers_data)
                    
                    logger.info(f"  Procesados: {len(papers_data)} | Total: {papers_found} | Nuevos: {new}")
                
                # Actualizar cursor usando el real de OpenAlex; si no hay, fin de paginación
                cursor = next_cursor
                batch_count += 1
                
                # Guardar checkpoint cada N lotes
                if batch_count % checkpoint_interval == 0:
                    self.save_checkpoint(query, cursor, papers_found)
                    logger.info(f"Checkpoint guardado: {papers_found} papers procesados")
                
                # Si obtuvimos menos de lo solicitado, no hay más
                if not cursor:
                    break
                
                # Delay entre batches optimizado
                time.sleep(1)  # Delay más corto para máxima eficiencia
            
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
                    'openalex_ultra_optimized', 'none', duration, success, error_message
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error guardando log: {e}")
    
    def load_schema_from_json(self, json_path: str) -> Dict:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_terms_from_database(self, area_filter: Optional[str] = None) -> List[str]:
        """Cargar términos de búsqueda desde la base de datos"""
        terms = []
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Cargar desde tabla area
                if area_filter:
                    cursor.execute("SELECT name FROM area WHERE id = %s", (area_filter,))
                else:
                    cursor.execute("SELECT name FROM area")
                
                areas = cursor.fetchall()
                terms.extend([area[0] for area in areas])
                
                # Cargar desde tabla field
                if area_filter:
                    cursor.execute("""
                        SELECT f.name FROM field f 
                        JOIN area a ON f.area_id = a.id 
                        WHERE a.id = %s
                    """, (area_filter,))
                else:
                    cursor.execute("SELECT name FROM field")
                
                fields = cursor.fetchall()
                terms.extend([field[0] for field in fields])
                
                # Cargar desde tabla subfield
                if area_filter:
                    cursor.execute("""
                        SELECT sf.alias FROM subfield sf 
                        JOIN field f ON sf.field_id = f.id 
                        JOIN area a ON f.area_id = a.id 
                        WHERE a.id = %s
                    """, (area_filter,))
                else:
                    cursor.execute("SELECT alias FROM subfield")
                
                subfields = cursor.fetchall()
                terms.extend([subfield[0] for subfield in subfields])
                
        except Exception as e:
            logger.error(f"Error cargando términos desde base de datos: {e}")
        
        return list(set(terms))  # Eliminar duplicados

    def build_queries_from_database(self, max_terms_per_query: int = 3) -> List[str]:
        """Construir queries desde la base de datos"""
        terms = self.load_terms_from_database()
        queries = []
        
        # Agrupar términos en lotes
        for i in range(0, len(terms), max_terms_per_query):
            batch = terms[i:i + max_terms_per_query]
            query = ' '.join(batch)
            queries.append(query)
        
        return queries

    def run_ultra_optimized_extraction(self, use_database: bool = True, json_path: str = None, 
                                      max_queries: int = 15, year_from: int = 2005, year_to: int = 2026,
                                      max_papers_per_query: int = 200):
        """Ejecutar extracción ultra optimizada"""
        logger.info(" Iniciando extracción ULTRA OPTIMIZADA con Open Alex API")
        
        if not self.test_connection():
            logger.error("No se puede conectar a la base de datos")
            return
        
        # Generar queries desde base de datos o JSON
        if use_database:
            logger.info("Cargando términos desde base de datos...")
            base_queries = self.build_queries_from_database()
            logger.info(f"Cargados {len(base_queries)} queries desde base de datos")
        else:
            logger.info("Cargando términos desde JSON...")
            schema = self.load_schema_from_json(json_path)
            base_queries = list(self.iter_queries_from_taxonomy_all(schema))

        # Optimizar queries para obtener más resultados
        optimized_queries = []
        for query in base_queries[:max_queries]:
            optimized_queries.extend(self.optimize_query_for_max_results(query))

        # Normalización y deduplicación fuerte de queries (lower, trim, colapsa espacios)
        def _normalize_query(q: str) -> str:
            return ' '.join((q or '').strip().lower().split())

        seen = set()
        normalized_queries = []
        for q in optimized_queries:
            nq = _normalize_query(q)
            if nq and nq not in seen:
                seen.add(nq)
                normalized_queries.append(q)  # preservamos la forma original pero deduplicada por normalización

        removed_dups = len(optimized_queries) - len(normalized_queries)

        # Limitar el total de queries tras deduplicación
        queries = normalized_queries[:max_queries * 2]

        logger.info(f"Queries base generadas: {len(base_queries)}")
        logger.info(f"Queries optimizadas antes de deduplicar: {len(optimized_queries)}")
        logger.info(f"Queries eliminadas por duplicadas (normalización): {removed_dups}")
        logger.info(f"Queries finales a ejecutar: {len(queries)}")
        
        total_papers = 0
        successful_queries = 0
        consecutive_zero_new = 0
        zero_new_threshold = 100
        
        logger.info(f"Ejecutando {len(queries)} queries DIVERSAS")
        
        for i, query in enumerate(queries):
            logger.info(f"\n Progreso: {i+1}/{len(queries)}")
            logger.info(f" Papers hoy: {self.papers_today}/{self.MAX_PAPERS_PER_DAY}")
            logger.info(f" Query: {query}")
            
            result = self.search_and_save_ultra_optimized(
                query, max_results=max_papers_per_query, year_from=year_from, year_to=year_to
            )
            
            if result['success']:
                successful_queries += 1
                total_papers += result['papers_found']
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
            
            # Delay entre queries optimizado
            if i < len(queries) - 1:
                time.sleep(2)  # Delay más corto para máxima eficiencia
        
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
    
    def export_to_csv(self, output_path: str = "ai_safety_papers_openalex_optimized.csv"):
        """Exportar datos a CSV"""
        try:
            engine = self.get_sqlalchemy_engine()
            sql = "SELECT * FROM papers ORDER BY citations DESC, created_at DESC"
            # Export en chunks para no cargar todo a memoria
            header_written = False
            rows_total = 0
            with open(output_path, "w", encoding="utf-8", newline="") as f:
                for chunk in pd.read_sql_query(sql, engine, chunksize=50000):
                    chunk.to_csv(f, index=False, header=not header_written)
                    header_written = True
                    rows_total += len(chunk)
            logger.info(f"Datos exportados a: {output_path} (filas: {rows_total})")
            return None
        except Exception as e:
            logger.error(f"Error exportando datos: {e}")
            return None


if __name__ == "__main__":
    # CLI ultra optimizado
    parser = argparse.ArgumentParser(description="Open Alex extractor ULTRA OPTIMIZADO (AI Safety)")
    parser.add_argument("--json-path", default="scraper_terms.json", help="Ruta al JSON de taxonomía/términos")
    parser.add_argument("--max-queries", type=int, default=200, help="Máximo de queries a ejecutar")
    parser.add_argument("--year-from", type=int, default=2005, help="Filtrar por año inicial (inclusive)")
    parser.add_argument("--year-to", type=int, default=2026, help="Filtrar por año final (inclusive)")
    parser.add_argument("--max-papers-per-query", type=int, default=5000, help="Máximo papers por query")
    parser.add_argument("--email", default=None, help="Email para Open Alex (recomendado)")
    # DB flags
    parser.add_argument("--db-host", default="localhost", help="Host de PostgreSQL")
    parser.add_argument("--db-port", type=int, default=6543, help="Puerto de PostgreSQL")
    parser.add_argument("--db-name", default="ai_safety", help="Nombre de la base de datos")
    parser.add_argument("--db-user", default="scholar_user", help="Usuario de la base de datos")
    parser.add_argument("--db-password", default="scholar_pass_2024", help="Password de la base de datos")
    args = parser.parse_args()
    
    # Configuración
    EMAIL = args.email
    
    extractor = UltraOptimizedOpenAlexExtractor(
        host=args.db_host,
        port=args.db_port,
        database=args.db_name,
        user=args.db_user,
        password=args.db_password,
        email=EMAIL
    )
    
    # Ejecutar extracción optimizada usando base de datos
    extractor.run_ultra_optimized_extraction(
        use_database=True,  # Usar base de datos en lugar de JSON
        json_path=args.json_path,  # Fallback si se necesita
        max_queries=args.max_queries,
        year_from=args.year_from,
        year_to=args.year_to,
        max_papers_per_query=args.max_papers_per_query
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
