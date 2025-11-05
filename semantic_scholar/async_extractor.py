"""
Async Extractor - Versión con asyncio para máxima concurrencia
"""

import asyncio
import logging
from typing import List, Dict, Set
from pathlib import Path

from async_api_client import AsyncSemanticScholarAPI
from query_builder import load_terms_json, build_queries_by_area
from data_saver import DataSaver

logger = logging.getLogger(__name__)


class AsyncExtractor:
    """Extractor con asyncio para concurrencia eficiente"""

    def __init__(
        self,
        api_key: str = None,
        output_dir: str = "../raw_data",
        max_concurrent_areas: int = 3
    ):
        self.api_key = api_key
        self.saver = DataSaver(output_dir=output_dir)
        self.max_concurrent_areas = max_concurrent_areas

    async def extract_query(
        self,
        api: AsyncSemanticScholarAPI,
        area_name: str,
        query: str,
        max_papers: int = 500,
        year_from: int = 2015,
        min_citations: int = 10
    ) -> List[Dict]:
        """
        Extraer papers para una query (async)
        RAW DATA - Sin deduplicación, guarda exactamente lo que devuelve el API
        """
        logger.info(f"Query: '{query}'")

        all_papers = []
        token = None
        page = 1

        while len(all_papers) < max_papers:
            logger.info(f"  Página {page}...")

            papers, next_token = await api.search(
                query=query,
                limit=min(1000, max_papers - len(all_papers)),
                year_from=year_from,
                min_citations=min_citations,
                token=token
            )

            if not papers:
                logger.info("  No más papers")
                break

            # Raw data - Agregar papers directamente sin deduplicación
            all_papers.extend(papers)

            logger.info(f"  Obtenidos: {len(papers)} | Total query: {len(all_papers)}")

            if not next_token:
                break

            token = next_token
            page += 1
            await asyncio.sleep(2)

        return all_papers

    async def extract_area(
        self,
        area_name: str,
        queries: List[str],
        max_papers_per_query: int = 500,
        year_from: int = 2015,
        min_citations: int = 10
    ) -> Dict:
        """
        Extraer papers para un área completa (async)
        """
        task_name = asyncio.current_task().get_name()
        logger.info(f"\n{'='*60}")
        logger.info(f"[{task_name}] ÁREA: {area_name}")
        logger.info(f"[{task_name}] Queries: {len(queries)}")
        logger.info(f"{'='*60}")

        all_papers = []
        queries_processed = []

        # Crear API client para esta área
        async with AsyncSemanticScholarAPI(api_key=self.api_key) as api:
            for i, query in enumerate(queries, 1):
                logger.info(f"\n[{task_name}] [{i}/{len(queries)}]")

                papers = await self.extract_query(
                    api,
                    area_name,
                    query,
                    max_papers=max_papers_per_query,
                    year_from=year_from,
                    min_citations=min_citations
                )

                all_papers.extend(papers)
                queries_processed.append(query)

                # Delay entre queries
                if i < len(queries):
                    await asyncio.sleep(5)

        # Guardar resultados del área
        self.saver.save_area_results(area_name, all_papers, queries_processed)

        logger.info(f"[{task_name}] ✅ Área '{area_name}' completada: {len(all_papers)} papers")

        return {
            'area': area_name,
            'queries_processed': queries_processed,
            'total_papers': len(all_papers),
            'papers': all_papers
        }

    async def run(
        self,
        terms_json_path: str,
        limit_areas: int = None,
        max_papers_per_query: int = 500,
        year_from: int = 2015,
        min_citations: int = 10,
        include_secondary: bool = False
    ):
        """
        Ejecutar extracción async con concurrencia limitada

        Args:
            terms_json_path: Path a terms.json
            limit_areas: Número de áreas a procesar
            max_papers_per_query: Máximo papers por query
            year_from: Año inicial
            min_citations: Mínimo de citas
            include_secondary: Incluir secondary fields
        """
        logger.info("="*60)
        logger.info("EXTRACCIÓN ASYNC - CON ASYNCIO")
        logger.info("="*60)

        # Cargar queries por área
        terms_data = load_terms_json(terms_json_path)
        queries_by_area = build_queries_by_area(
            terms_data,
            limit_areas=limit_areas,
            include_secondary=include_secondary
        )

        logger.info(f"\nÁreas a procesar: {len(queries_by_area)}")
        logger.info(f"Concurrencia máxima: {self.max_concurrent_areas}")
        logger.info(f"Max papers por query: {max_papers_per_query}")
        logger.info(f"Año desde: {year_from}")
        logger.info(f"Min citas: {min_citations}\n")

        # Crear tasks para cada área
        tasks = [
            asyncio.create_task(
                self.extract_area(
                    area_name,
                    queries,
                    max_papers_per_query,
                    year_from,
                    min_citations
                ),
                name=f"Area-{area_name}"
            )
            for area_name, queries in queries_by_area.items()
        ]

        # Ejecutar con semáforo para limitar concurrencia
        semaphore = asyncio.Semaphore(self.max_concurrent_areas)

        async def run_with_semaphore(task):
            async with semaphore:
                return await task

        # Ejecutar todas las tasks con límite de concurrencia
        results = []
        total_papers = 0

        for coro in asyncio.as_completed([run_with_semaphore(task) for task in tasks]):
            try:
                result = await coro
                results.append(result)
                total_papers += result['total_papers']
                logger.info(f"✅ Área '{result['area']}' procesada exitosamente")
            except Exception as e:
                logger.error(f"❌ Error en área: {e}")

        # Guardar resumen (raw data - sin deduplicación)
        summary = {
            'mode': 'async_raw_data',
            'max_concurrent_areas': self.max_concurrent_areas,
            'total_areas': len(queries_by_area),
            'total_papers_raw': total_papers,
            'note': 'Raw data without deduplication - papers may appear multiple times across areas',
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
        logger.info(f"Papers totales (raw, sin deduplicación): {total_papers}")



def run_async_extraction(**kwargs):
    """
    Helper function para ejecutar extracción async desde código síncrono

    Usage:
        run_async_extraction(
            terms_json_path="../terms.json",
            api_key="YOUR_KEY",
            limit_areas=2,
            max_papers_per_query=100
        )
    """
    extractor = AsyncExtractor(
        api_key=kwargs.get('api_key'),
        output_dir=kwargs.get('output_dir', '../raw_data'),
        max_concurrent_areas=kwargs.get('max_concurrent_areas', 3)
    )

    asyncio.run(
        extractor.run(
            terms_json_path=kwargs['terms_json_path'],
            limit_areas=kwargs.get('limit_areas'),
            max_papers_per_query=kwargs.get('max_papers_per_query', 500),
            year_from=kwargs.get('year_from', 2015),
            min_citations=kwargs.get('min_citations', 10),
            include_secondary=kwargs.get('include_secondary', False)
        )
    )
