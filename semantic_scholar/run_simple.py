#!/usr/bin/env python3
"""
Script CLI para ejecutar el extractor simple (secuencial)
"""

import argparse
import logging
from simple_extractor import SimpleExtractor

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extraction_simple.log'),
        logging.StreamHandler()
    ]
)


def main():
    parser = argparse.ArgumentParser(
        description="Extractor Simple - Secuencial"
    )
    parser.add_argument(
        "--terms-json",
        default="../terms.json",
        help="Path a terms.json"
    )
    parser.add_argument(
        "--limit-areas",
        type=int,
        default=2,
        help="Número de áreas a procesar (default: 2)"
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
        help="API key de Semantic Scholar"
    )
    parser.add_argument(
        "--output-dir",
        default="../raw_data",
        help="Directorio de salida (default: ../raw_data)"
    )
    parser.add_argument(
        "--include-secondary",
        action="store_true",
        help="Incluir secondary fields"
    )

    args = parser.parse_args()

    # Crear extractor
    extractor = SimpleExtractor(
        api_key=args.api_key,
        output_dir=args.output_dir
    )

    # Ejecutar
    extractor.run(
        terms_json_path=args.terms_json,
        limit_areas=args.limit_areas,
        max_papers_per_query=args.max_papers,
        year_from=args.year_from,
        min_citations=args.min_citations,
        include_secondary=args.include_secondary
    )


if __name__ == "__main__":
    main()
