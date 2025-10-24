"""
Simple Extractor - Versión simplificada y legible del extractor
"""

import time
import logging
from typing import List, Dict, Set
from pathlib import Path

from api_client import SemanticScholarAPI
from query_builder import load_terms_json, build_queries_by_area
from data_saver import DataSaver

logger = logging.getLogger(__name__)


class SimpleExtractor:
    """Extractor simple y legible"""

    def __init__(self, api_key: str = None, output_dir: str = "../raw_data"):
        self.api = SemanticScholarAPI(api_key=api_key)
        self.saver = DataSaver(output_dir=output_dir)
        self.seen_paper_ids: Set[str] = set()

    def extract_query(
        self,
        query: str,
        max_papers: int = 500,
        year_from: int = 2015,
        min_citations: int = 10
    ) -> List[Dict]:
        """
        Extraer papers para una query

        Returns:
            Lista de papers únicos
        """
        logger.info(f"Query: '{query}'")

        all_papers = []
        token = None
        page = 1

        # Paginar hasta obtener max_papers
        while len(all_papers) < max_papers:
            logger.info(f"  Página {page}...")

            papers, next_token = self.api.search(
                query=query,
                limit=min(1000, max_papers - len(all_papers)),
                year_from=year_from,
                min_citations=min_citations,
                token=token
            )

            if not papers:
                logger.info("  No más papers")
                break

            # Filtrar duplicados
            new_papers = self._filter_duplicates(papers)
            all_papers.extend(new_papers)

            logger.info(f"  Nuevos: {len(new_papers)} | Total: {len(all_papers)}")

            if not next_token:
                break

            token = next_token
            page += 1
            time.sleep(2)  # Delay entre páginas

        return all_papers

    def extract_area(
        self,
        area_name: str,
        queries: List[str],
        max_papers_per_query: int = 500,
        year_from: int = 2015,
        min_citations: int = 10
    ) -> Dict:
        """
        Extraer papers para todas las queries de un área

        Returns:
            {
                'area': area_name,
                'queries_processed': [...],
                'total_papers': N,
                'papers': [...]
            }
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"ÁREA: {area_name}")
        logger.info(f"Queries: {len(queries)}")
        logger.info(f"{'='*60}")

        all_papers = []
        queries_processed = []

        for i, query in enumerate(queries, 1):
            logger.info(f"\n[{i}/{len(queries)}]")

            papers = self.extract_query(
                query,
                max_papers=max_papers_per_query,
                year_from=year_from,
                min_citations=min_citations
            )

            all_papers.extend(papers)
            queries_processed.append(query)

            # Delay entre queries
            if i < len(queries):
                time.sleep(5)

        # Guardar resultados del área
        self.saver.save_area_results(area_name, all_papers, queries_processed)

        return {
            'area': area_name,
            'queries_processed': queries_processed,
            'total_papers': len(all_papers),
            'papers': all_papers
        }

    def run(
        self,
        terms_json_path: str,
        limit_areas: int = None,
        max_papers_per_query: int = 500,
        year_from: int = 2015,
        min_citations: int = 10,
        include_secondary: bool = False
    ):
        """
        Ejecutar extracción completa (secuencial)

        Args:
            terms_json_path: Path a terms.json
            limit_areas: Número de áreas a procesar (None = todas)
            max_papers_per_query: Máximo papers por query
            year_from: Año inicial
            min_citations: Mínimo de citas
            include_secondary: Incluir secondary fields
        """
        logger.info("="*60)
        logger.info("EXTRACCIÓN SIMPLE - MODO SECUENCIAL")
        logger.info("="*60)

        # Cargar queries por área
        terms_data = load_terms_json(terms_json_path)
        queries_by_area = build_queries_by_area(
            terms_data,
            limit_areas=limit_areas,
            include_secondary=include_secondary
        )

        logger.info(f"\nÁreas a procesar: {len(queries_by_area)}")
        logger.info(f"Max papers por query: {max_papers_per_query}")
        logger.info(f"Año desde: {year_from}")
        logger.info(f"Min citas: {min_citations}\n")

        # Procesar cada área secuencialmente
        results = []
        total_papers = 0

        for area_name, queries in queries_by_area.items():
            result = self.extract_area(
                area_name,
                queries,
                max_papers_per_query=max_papers_per_query,
                year_from=year_from,
                min_citations=min_citations
            )

            results.append(result)
            total_papers += result['total_papers']

        # Guardar resumen
        summary = {
            'mode': 'sequential',
            'total_areas': len(queries_by_area),
            'total_papers': total_papers,
            'unique_papers': len(self.seen_paper_ids),
            'areas': [
                {
                    'area': r['area'],
                    'queries': len(r['queries_processed']),
                    'papers': r['total_papers']
                }
                for r in results
            ]
        }
        self.saver.save_summary(summary)

        logger.info("\n" + "="*60)
        logger.info("EXTRACCIÓN COMPLETADA")
        logger.info("="*60)
        logger.info(f"Áreas procesadas: {len(queries_by_area)}")
        logger.info(f"Papers totales: {total_papers}")
        logger.info(f"Papers únicos: {len(self.seen_paper_ids)}")

    def _filter_duplicates(self, papers: List[Dict]) -> List[Dict]:
        """Filtrar papers duplicados"""
        new_papers = []
        for paper in papers:
            paper_id = paper.get('paperId')
            if paper_id and paper_id not in self.seen_paper_ids:
                new_papers.append(paper)
                self.seen_paper_ids.add(paper_id)
        return new_papers
