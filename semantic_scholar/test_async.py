#!/usr/bin/env python3
"""
Test script para verificar el funcionamiento del extractor async
"""

import asyncio
import logging
import time
from async_extractor import run_async_extraction

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_rate_limiter():
    """
    Test simple para verificar que el rate limiter funciona correctamente
    """
    from async_api_client import AsyncSemanticScholarAPI

    logger.info("="*60)
    logger.info("TEST: Rate Limiter Async")
    logger.info("="*60)

    timestamps = []

    async def make_request(task_id):
        """Simular un request marcando timestamp antes y después"""
        before = time.time()
        timestamps.append(('before', task_id, before))
        logger.info(f"Task {task_id}: Esperando rate limiter...")

        async with AsyncSemanticScholarAPI(api_key="test_key") as api:
            await api.rate_limiter.wait()

        after = time.time()
        timestamps.append(('after', task_id, after))
        logger.info(f"Task {task_id}: Request permitido en {after:.3f}")

    # Crear 3 tasks que intentarán hacer requests simultáneamente
    tasks = [
        asyncio.create_task(make_request(i), name=f"Task-{i}")
        for i in range(3)
    ]

    # Ejecutar todas las tasks
    await asyncio.gather(*tasks)

    # Analizar timestamps
    logger.info("\n" + "="*60)
    logger.info("ANÁLISIS DE TIMESTAMPS")
    logger.info("="*60)

    after_times = [t for t in timestamps if t[0] == 'after']
    after_times.sort(key=lambda x: x[2])

    for i, (_, task_id, timestamp) in enumerate(after_times):
        logger.info(f"Request {i+1} (Task {task_id}): {timestamp:.3f}")

    # Verificar gaps
    logger.info("\nGaps entre requests:")
    for i in range(1, len(after_times)):
        gap = after_times[i][2] - after_times[i-1][2]
        logger.info(f"  Gap {i}: {gap:.3f}s")

        if gap >= 0.95:  # ~1 segundo con margen
            logger.info(f"    ✅ OK (>= 1 segundo)")
        else:
            logger.warning(f"    ⚠️  Menor a 1 segundo!")

    logger.info("\n" + "="*60)


async def test_small_extraction():
    """
    Test de extracción pequeña con 2 áreas
    """
    logger.info("\n" + "="*60)
    logger.info("TEST: Extracción Pequeña (2 áreas)")
    logger.info("="*60 + "\n")

    start_time = time.time()

    run_async_extraction(
        terms_json_path="../terms.json",
        api_key=None,  # Sin API key para test
        limit_areas=2,
        max_papers_per_query=50,
        year_from=2020,
        min_citations=10,
        max_concurrent_areas=2
    )

    elapsed = time.time() - start_time
    logger.info(f"\n⏱️  Tiempo total: {elapsed:.2f}s")


async def main():
    """Main async"""
    logger.info("Iniciando tests async...\n")

    # Test 1: Rate limiter
    await test_rate_limiter()

    # Test 2: Extracción pequeña
    # await test_small_extraction()

    logger.info("\n✅ Tests completados")


if __name__ == "__main__":
    asyncio.run(main())
