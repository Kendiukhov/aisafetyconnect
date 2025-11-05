#!/usr/bin/env python3
"""
Test script para verificar la Opción 3A: metadata de cross-area papers
"""

import asyncio
import logging
import json
from pathlib import Path
from async_extractor import AsyncExtractor

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_option3a():
    """
    Test pequeño para verificar que:
    1. Papers aparecen en múltiples áreas
    2. Metadata se agrega correctamente
    3. Stats de cross-area se calculan bien
    """
    logger.info("="*60)
    logger.info("TEST: Opción 3A - Metadata Cross-Area")
    logger.info("="*60)

    # Crear extractor
    extractor = AsyncExtractor(
        api_key=None,  # Sin API key para test
        output_dir="../raw_data_test",
        max_concurrent_areas=2
    )

    # Ejecutar extracción pequeña (2 áreas, 20 papers por query)
    await extractor.run(
        terms_json_path="../terms.json",
        limit_areas=2,
        max_papers_per_query=20,
        year_from=2020,
        min_citations=10,
        include_secondary=False
    )

    logger.info("\n" + "="*60)
    logger.info("VERIFICANDO RESULTADOS")
    logger.info("="*60)

    # Leer archivos generados
    output_dir = Path("../raw_data_test")
    area_files = list(output_dir.glob("area_*.json"))

    logger.info(f"\nArchivos generados: {len(area_files)}")

    # Analizar cada archivo
    all_paper_ids = []
    for area_file in area_files:
        with open(area_file) as f:
            data = json.load(f)

        area_name = data['area']
        papers = data['papers']

        logger.info(f"\n📁 {area_name}")
        logger.info(f"   Total papers: {len(papers)}")

        # Contar cross-area papers
        cross_area_papers = [p for p in papers if p.get('_metadata', {}).get('is_cross_area', False)]
        unique_papers = [p for p in papers if not p.get('_metadata', {}).get('is_cross_area', False)]

        logger.info(f"   Papers únicos de esta área: {len(unique_papers)}")
        logger.info(f"   Papers cross-area: {len(cross_area_papers)}")

        # Mostrar un ejemplo de cross-area paper
        if cross_area_papers:
            example = cross_area_papers[0]
            logger.info(f"\n   Ejemplo de cross-area paper:")
            logger.info(f"   - Title: {example['title'][:60]}...")
            logger.info(f"   - Found in areas: {example['_metadata']['found_in_areas']}")
            logger.info(f"   - Primary area: {example['_metadata']['primary_area']}")
            logger.info(f"   - Also appears in: {example['_metadata'].get('also_appears_in', [])}")

        # Trackear paper IDs
        all_paper_ids.extend([p['paperId'] for p in papers])

    # Verificar duplicados globales
    unique_global = set(all_paper_ids)
    total_raw = len(all_paper_ids)

    logger.info("\n" + "="*60)
    logger.info("RESUMEN GLOBAL")
    logger.info("="*60)
    logger.info(f"Papers totales (raw, con duplicados): {total_raw}")
    logger.info(f"Papers únicos globalmente: {len(unique_global)}")
    logger.info(f"Papers que aparecen múltiples veces: {total_raw - len(unique_global)}")

    # Leer summary
    summary_files = list(output_dir.glob("extraction_summary_*.json"))
    if summary_files:
        with open(summary_files[0]) as f:
            summary = json.load(f)

        logger.info("\n📊 Summary de extracción:")
        logger.info(f"   Total areas: {summary['total_areas']}")
        logger.info(f"   Papers raw: {summary['total_papers_raw']}")
        logger.info(f"   Papers únicos: {summary['total_papers_unique']}")
        logger.info(f"   Papers cross-area: {summary['cross_area_papers']}")

        if 'cross_area_analysis' in summary:
            analysis = summary['cross_area_analysis']
            logger.info(f"\n   Análisis cross-area:")
            for key, value in analysis['papers_by_area_count'].items():
                logger.info(f"   - {key}: {value}")

            if analysis['most_cross_cutting_papers']:
                logger.info(f"\n   Top 5 papers más cross-cutting:")
                for i, paper in enumerate(analysis['most_cross_cutting_papers'][:5], 1):
                    logger.info(f"   {i}. {paper['paperId'][:20]}... - {paper['total_areas']} áreas")
                    logger.info(f"      Areas: {paper['areas']}")

    logger.info("\n" + "="*60)
    logger.info("✅ TEST COMPLETADO")
    logger.info("="*60)


if __name__ == "__main__":
    asyncio.run(test_option3a())
