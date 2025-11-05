#!/usr/bin/env python3
"""
Script principal para ejecutar extracción async con Semantic Scholar

Usage:
    # Test pequeño (2 áreas, 50 papers por query)
    uv run run_async_extraction.py --test

    # Extracción completa (todas las áreas)
    uv run run_async_extraction.py --api-key YOUR_KEY

    # Extracción personalizada
    uv run run_async_extraction.py \
        --api-key YOUR_KEY \
        --areas 5 \
        --papers 1000 \
        --workers 3 \
        --year 2015 \
        --citations 10
"""

import asyncio
import logging
import argparse
import os
from pathlib import Path

from async_extractor import AsyncExtractor

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('async_extraction.log')
    ]
)

logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(
        description='Extracción async de papers de Semantic Scholar',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--api-key',
        type=str,
        default=os.environ.get('SEMANTIC_SCHOLAR_API_KEY'),
        help='API key de Semantic Scholar (o env SEMANTIC_SCHOLAR_API_KEY)'
    )

    parser.add_argument(
        '--terms',
        type=str,
        default='../terms.json',
        help='Path al archivo terms.json (default: ../terms.json)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='../raw_data',
        help='Directorio de salida (default: ../raw_data)'
    )

    parser.add_argument(
        '--areas',
        type=int,
        default=None,
        help='Número de áreas a procesar (default: todas)'
    )

    parser.add_argument(
        '--papers',
        type=int,
        default=500,
        help='Máximo papers por query (default: 500)'
    )

    parser.add_argument(
        '--workers',
        type=int,
        default=3,
        help='Número de áreas concurrentes (default: 3)'
    )

    parser.add_argument(
        '--year',
        type=int,
        default=2015,
        help='Año inicial para filtrar papers (default: 2015)'
    )

    parser.add_argument(
        '--citations',
        type=int,
        default=10,
        help='Mínimo de citas (default: 10)'
    )

    parser.add_argument(
        '--secondary',
        action='store_true',
        help='Incluir secondary fields en queries'
    )

    parser.add_argument(
        '--test',
        action='store_true',
        help='Modo test: 2 áreas, 50 papers, año 2020'
    )

    args = parser.parse_args()

    # Modo test
    if args.test:
        logger.info("🧪 MODO TEST activado")
        args.areas = 2
        args.papers = 50
        args.year = 2020
        args.workers = 2

    # Verificar que existe terms.json
    terms_path = Path(args.terms)
    if not terms_path.exists():
        logger.error(f"❌ No se encuentra el archivo: {terms_path}")
        return

    # Crear extractor
    extractor = AsyncExtractor(
        api_key=args.api_key,
        output_dir=args.output,
        max_concurrent_areas=args.workers
    )

    # Ejecutar extracción
    logger.info("\n" + "="*60)
    logger.info("🚀 INICIANDO EXTRACCIÓN ASYNC")
    logger.info("="*60)
    logger.info(f"Terms: {args.terms}")
    logger.info(f"Output: {args.output}")
    logger.info(f"Áreas: {'todas' if args.areas is None else args.areas}")
    logger.info(f"Papers por query: {args.papers}")
    logger.info(f"Workers concurrentes: {args.workers}")
    logger.info(f"Año desde: {args.year}")
    logger.info(f"Min citas: {args.citations}")
    logger.info(f"API key: {'Sí' if args.api_key else 'No'}")
    logger.info("="*60 + "\n")

    await extractor.run(
        terms_json_path=args.terms,
        limit_areas=args.areas,
        max_papers_per_query=args.papers,
        year_from=args.year,
        min_citations=args.citations,
        include_secondary=args.secondary
    )

    logger.info("\n✅ Extracción completada exitosamente")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⚠️  Extracción interrumpida por el usuario")
    except Exception as e:
        logger.error(f"\n❌ Error: {e}", exc_info=True)
