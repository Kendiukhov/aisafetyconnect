"""
Semantic Scholar Extractor - Main extraction logic for Lambda
"""

import asyncio
import logging
from typing import Dict, List
from pathlib import Path

from .async_api_client import AsyncSemanticScholarAPI
from .query_builder import load_terms_json, build_queries_by_area

logger = logging.getLogger(__name__)


class SemanticScholarExtractor:
    """
    Extractor optimizado para Lambda con snapshots mensuales
    """

    def __init__(self, api_key: str, max_workers: int = 10):
        self.api_key = api_key
        self.max_workers = max_workers

    async def extract_all_areas(
        self,
        terms_json_path: str,
        year_from: int = 2005,
        papers_per_query: int = 10000,
        min_citations: int = 0,
        include_secondary: bool = True
    ) -> Dict[str, List[Dict]]:
        """
        Extraer papers de todas las áreas

        Returns:
            Dict mapping area_name -> list of papers
        """
        logger.info("="*60)
        logger.info("SEMANTIC SCHOLAR EXTRACTION - LAMBDA")
        logger.info("="*60)

        # Load terms and build queries
        terms_data = load_terms_json(terms_json_path)
        queries_by_area = build_queries_by_area(
            terms_data,
            include_secondary=include_secondary
        )

        logger.info(f"Areas to process: {len(queries_by_area)}")
        logger.info(f"Max workers: {self.max_workers}")
        logger.info(f"Papers per query: {papers_per_query}")
        logger.info(f"Year from: {year_from}")
        logger.info(f"Min citations: {min_citations}")

        # Create tasks for each area
        tasks = [
            asyncio.create_task(
                self.extract_area(
                    area_name,
                    queries,
                    year_from,
                    papers_per_query,
                    min_citations
                ),
                name=f"Area-{area_name}"
            )
            for area_name, queries in queries_by_area.items()
        ]

        # Execute with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_workers)

        async def run_with_semaphore(task):
            async with semaphore:
                return await task

        # Execute all tasks
        results = {}
        for coro in asyncio.as_completed([run_with_semaphore(task) for task in tasks]):
            try:
                result = await coro
                area_name = result['area']
                results[area_name] = result['papers']
                logger.info(f"✅ Area '{area_name}' completed: {len(result['papers'])} papers")
            except Exception as e:
                logger.error(f"❌ Error in area: {e}", exc_info=True)

        total_papers = sum(len(papers) for papers in results.values())
        logger.info(f"\n{'='*60}")
        logger.info(f"EXTRACTION COMPLETED")
        logger.info(f"{'='*60}")
        logger.info(f"Areas processed: {len(results)}")
        logger.info(f"Total papers (raw, no dedup): {total_papers}")

        return results

    async def extract_area(
        self,
        area_name: str,
        queries: List[str],
        year_from: int,
        papers_per_query: int,
        min_citations: int
    ) -> Dict:
        """
        Extract papers for one area
        """
        task_name = asyncio.current_task().get_name()
        logger.info(f"\n{'='*60}")
        logger.info(f"[{task_name}] AREA: {area_name}")
        logger.info(f"[{task_name}] Queries: {len(queries)}")
        logger.info(f"{'='*60}")

        all_papers = []

        # Create API client for this area
        async with AsyncSemanticScholarAPI(api_key=self.api_key) as api:
            for i, query in enumerate(queries, 1):
                logger.info(f"\n[{task_name}] [{i}/{len(queries)}] Query: '{query}'")

                papers = await self.extract_query(
                    api,
                    query,
                    year_from,
                    papers_per_query,
                    min_citations
                )

                all_papers.extend(papers)
                logger.info(f"[{task_name}] Papers from this query: {len(papers)} | Total area: {len(all_papers)}")

                # Delay between queries
                if i < len(queries):
                    await asyncio.sleep(5)

        logger.info(f"[{task_name}] ✅ Area '{area_name}' completed: {len(all_papers)} papers")

        return {
            'area': area_name,
            'queries_count': len(queries),
            'papers': all_papers
        }

    async def extract_query(
        self,
        api: AsyncSemanticScholarAPI,
        query: str,
        year_from: int,
        max_papers: int,
        min_citations: int
    ) -> List[Dict]:
        """
        Extract papers for a single query
        """
        all_papers = []
        token = None
        page = 1

        while len(all_papers) < max_papers:
            papers, next_token = await api.search(
                query=query,
                limit=min(1000, max_papers - len(all_papers)),
                year_from=year_from,
                min_citations=min_citations,
                token=token
            )

            if not papers:
                break

            all_papers.extend(papers)

            if not next_token:
                break

            token = next_token
            page += 1
            await asyncio.sleep(2)

        return all_papers
