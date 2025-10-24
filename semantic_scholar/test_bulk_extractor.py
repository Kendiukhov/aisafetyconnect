#!/usr/bin/env python3
"""
Script de prueba para extraer papers usando Semantic Scholar Bulk API
Guarda resultados en raw_data/
"""

import json
import time
import logging
import requests
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('semantic_scholar_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SemanticScholarBulkExtractor:
    """Extractor simplificado usando solo Bulk API"""

    BULK_SEARCH_API = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"

    # Campos que queremos obtener
    PAPER_FIELDS = "title,abstract,authors,year,venue,citationCount,openAccessPdf,externalIds,publicationTypes,publicationDate,fieldsOfStudy,s2FieldsOfStudy,url,referenceCount,influentialCitationCount,isOpenAccess,publicationVenue"

    def __init__(self, api_key: Optional[str] = None, output_dir: str = "../raw_data"):
        self.api_key = api_key
        self.headers = {
            "User-Agent": "AIResearchBot/Test (AI Safety Research)",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }
        if api_key:
            self.headers["x-api-key"] = api_key

        # Configuración de rate limiting
        self.has_api_key = bool(api_key)
        self.BATCH_SIZE = 1000 if self.has_api_key else 500
        self.MIN_DELAY = 1.0 if self.has_api_key else 3.0

        # Directorio de salida
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)

        # Set para evitar duplicados
        self.processed_paper_ids: Set[str] = set()

        logger.info(f"Inicializado - API Key: {'Sí' if self.has_api_key else 'No'}")
        logger.info(f"Output directory: {self.output_dir.absolute()}")

    def load_terms_from_json(self, json_path: str, limit_areas: Optional[int] = None) -> List[str]:
        """
        Cargar queries desde terms.json

        Args:
            json_path: Ruta al archivo terms.json
            limit_areas: Número de áreas a procesar (None = todas)

        Returns:
            Lista de queries (strings)
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)

        queries = []
        seen = set()
        mappings = schema.get("AI_Safety_Research_Mappings", {})

        # Limitar áreas si se especifica
        areas_to_process = list(mappings.items())
        if limit_areas:
            areas_to_process = areas_to_process[:limit_areas]

        for area_key, payload in areas_to_process:
            # Convertir "Mechanistic_Interpretability" → "Mechanistic Interpretability"
            area = area_key.replace("_", " ")

            # Nivel 1: Solo área
            if area not in seen:
                seen.add(area)
                queries.append(area)
                logger.info(f"Área agregada: {area}")

            # Nivel 2: Área + Field (solo Primary Fields para testing)
            for field_dict in payload.get("Primary_Fields", []):
                for field_name, subfields in field_dict.items():
                    query = f"{area} {field_name}"
                    if query not in seen:
                        seen.add(query)
                        queries.append(query)
                        logger.info(f"  Field agregado: {field_name}")

        logger.info(f"Total queries generadas: {len(queries)}")
        return queries

    def bulk_search(self, query: str, limit: int = 1000, year_from: int = 2005,
                    min_citations: int = 0, token: Optional[str] = None) -> tuple:
        """
        Hacer una búsqueda bulk

        Returns:
            (papers_list, next_token)
        """
        params = {
            "query": query,
            "limit": min(limit, self.BATCH_SIZE),
            "fields": self.PAPER_FIELDS,
            "year": f"{year_from}-",
            "sort": "citationCount:desc"
        }

        # Agregar token para paginación
        if token:
            params["token"] = token

        if min_citations > 0:
            params["minCitationCount"] = str(min_citations)

        try:
            # Rate limiting
            time.sleep(self.MIN_DELAY)

            # HTTP Request
            response = requests.get(
                self.BULK_SEARCH_API,
                params=params,
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                papers = data.get('data', [])
                total = data.get('total', 0)
                next_token = data.get('token')

                logger.info(f"  Recibidos {len(papers)}/{total} papers | Token: {'Sí' if next_token else 'No'}")
                return papers, next_token

            elif response.status_code == 429:
                logger.warning(f"Rate limit! Esperando 10 segundos...")
                time.sleep(10)
                return [], None

            else:
                logger.error(f"Error HTTP {response.status_code}: {response.text[:200]}")
                return [], None

        except Exception as e:
            logger.error(f"Error en request: {e}")
            return [], None

    def extract_and_save_query(self, query: str, max_results: int = 1000,
                               year_from: int = 2005, min_citations: int = 0) -> Dict:
        """
        Extraer papers para una query y guardar en archivo JSON

        Returns:
            Dict con estadísticas
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Query: '{query}'")
        logger.info(f"{'='*60}")

        all_papers = []
        papers_found = 0
        token = None
        page = 1

        start_time = time.time()

        # Paginar hasta obtener max_results
        while papers_found < max_results:
            logger.info(f"Página {page}...")

            papers, next_token = self.bulk_search(
                query,
                limit=min(self.BATCH_SIZE, max_results - papers_found),
                year_from=year_from,
                min_citations=min_citations,
                token=token
            )

            if not papers:
                logger.info("No más papers disponibles")
                break

            # Filtrar duplicados
            new_papers = []
            for paper in papers:
                paper_id = paper.get('paperId', '')
                if paper_id and paper_id not in self.processed_paper_ids:
                    new_papers.append(paper)
                    self.processed_paper_ids.add(paper_id)

            all_papers.extend(new_papers)
            papers_found += len(new_papers)

            logger.info(f"  Nuevos: {len(new_papers)} | Total acumulado: {papers_found}")

            # Verificar si hay más páginas
            if not next_token:
                logger.info("No hay más páginas")
                break

            token = next_token
            page += 1

            # Delay entre páginas
            time.sleep(2)

        duration = time.time() - start_time

        # Guardar resultados en archivo JSON
        if all_papers:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Crear nombre de archivo seguro (sin espacios ni caracteres especiales)
            safe_query = query.replace(" ", "_").replace("/", "_")[:50]
            filename = f"papers_{safe_query}_{timestamp}.json"
            filepath = self.output_dir / filename

            output_data = {
                "query": query,
                "timestamp": timestamp,
                "total_papers": len(all_papers),
                "duration_seconds": duration,
                "filters": {
                    "year_from": year_from,
                    "min_citations": min_citations
                },
                "papers": all_papers
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Guardado: {filepath}")

        return {
            'query': query,
            'papers_found': papers_found,
            'duration': duration,
            'success': True
        }

    def run_extraction(self, terms_json_path: str, limit_areas: Optional[int] = None,
                      max_papers_per_query: int = 1000, year_from: int = 2005,
                      min_citations: int = 0):
        """
        Ejecutar extracción completa

        Args:
            terms_json_path: Ruta a terms.json
            limit_areas: Número de áreas a procesar (None = todas)
            max_papers_per_query: Máximo de papers por query
            year_from: Año inicial (inclusive)
            min_citations: Mínimo de citas
        """
        logger.info("="*60)
        logger.info("INICIANDO EXTRACCIÓN")
        logger.info("="*60)

        # Generar queries
        queries = self.load_terms_from_json(terms_json_path, limit_areas=limit_areas)

        logger.info(f"\nSe procesarán {len(queries)} queries")
        logger.info(f"Max papers por query: {max_papers_per_query}")
        logger.info(f"Año desde: {year_from}")
        logger.info(f"Min citas: {min_citations}")

        # Procesar cada query
        results = []
        total_papers = 0

        for i, query in enumerate(queries, 1):
            logger.info(f"\n[{i}/{len(queries)}]")

            result = self.extract_and_save_query(
                query,
                max_results=max_papers_per_query,
                year_from=year_from,
                min_citations=min_citations
            )

            results.append(result)
            total_papers += result['papers_found']

            # Delay entre queries
            if i < len(queries):
                logger.info("Esperando 5 segundos antes de siguiente query...")
                time.sleep(5)

        # Resumen final
        logger.info("\n" + "="*60)
        logger.info("EXTRACCIÓN COMPLETADA")
        logger.info("="*60)
        logger.info(f"Queries procesadas: {len(queries)}")
        logger.info(f"Total papers únicos: {total_papers}")
        logger.info(f"Papers únicos globales: {len(self.processed_paper_ids)}")
        logger.info(f"Archivos guardados en: {self.output_dir.absolute()}")

        # Guardar resumen
        summary_file = self.output_dir / f"extraction_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_queries': len(queries),
                'total_papers': total_papers,
                'unique_papers': len(self.processed_paper_ids),
                'queries': results
            }, f, indent=2)

        logger.info(f"Resumen guardado: {summary_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Test script para Semantic Scholar Bulk API"
    )
    parser.add_argument(
        "--terms-json",
        default="../terms.json",
        help="Ruta al archivo terms.json (default: ../terms.json)"
    )
    parser.add_argument(
        "--limit-areas",
        type=int,
        default=2,
        help="Número de áreas a procesar (default: 2 para testing)"
    )
    parser.add_argument(
        "--max-papers",
        type=int,
        default=500,
        help="Máximo papers por query (default: 500)"
    )
    parser.add_argument(
        "--year-from",
        type=int,
        default=2015,
        help="Año inicial (default: 2015)"
    )
    parser.add_argument(
        "--min-citations",
        type=int,
        default=10,
        help="Mínimo de citas (default: 10)"
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key de Semantic Scholar (opcional)"
    )
    parser.add_argument(
        "--output-dir",
        default="../raw_data",
        help="Directorio de salida (default: ../raw_data)"
    )

    args = parser.parse_args()

    # Crear extractor
    extractor = SemanticScholarBulkExtractor(
        api_key=args.api_key,
        output_dir=args.output_dir
    )

    # Ejecutar extracción
    extractor.run_extraction(
        terms_json_path=args.terms_json,
        limit_areas=args.limit_areas,
        max_papers_per_query=args.max_papers,
        year_from=args.year_from,
        min_citations=args.min_citations
    )


if __name__ == "__main__":
    main()
