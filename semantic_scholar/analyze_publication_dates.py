#!/usr/bin/env python3
"""
Script para analizar la cobertura de publicationDate en los archivos raw_data

Verifica:
1. Cuántos papers tienen publicationDate
2. Qué formato tiene (YYYY-MM-DD, YYYY-MM, YYYY, null, etc)
3. Distribución por área
4. Ejemplos de papers sin fecha
"""

import json
from pathlib import Path
from collections import Counter, defaultdict
import re


def analyze_publication_dates(raw_data_dir: str = "../raw_data"):
    """Analizar todos los archivos de área en raw_data"""

    raw_data_path = Path(raw_data_dir)
    area_files = list(raw_data_path.glob("area_*.json"))

    if not area_files:
        print(f"❌ No se encontraron archivos en {raw_data_dir}")
        return

    print("="*80)
    print(f"ANÁLISIS DE publicationDate EN RAW DATA")
    print("="*80)
    print(f"\nArchivos encontrados: {len(area_files)}\n")

    # Estadísticas globales
    total_papers = 0
    papers_with_date = 0
    papers_without_date = 0

    # Contadores de formatos
    date_formats = Counter()

    # Por área
    stats_by_area = defaultdict(lambda: {
        'total': 0,
        'with_date': 0,
        'without_date': 0,
        'formats': Counter()
    })

    # Ejemplos de papers sin fecha
    examples_without_date = []

    # Regex para detectar formatos
    format_yyyy_mm_dd = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    format_yyyy_mm = re.compile(r'^\d{4}-\d{2}$')
    format_yyyy = re.compile(r'^\d{4}$')

    # Procesar cada archivo
    for area_file in sorted(area_files):
        print(f"Procesando: {area_file.name}...")

        with open(area_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        area_name = data.get('area', 'Unknown')
        papers = data.get('papers', [])

        for paper in papers:
            total_papers += 1
            stats_by_area[area_name]['total'] += 1

            pub_date = paper.get('publicationDate')

            if pub_date:
                papers_with_date += 1
                stats_by_area[area_name]['with_date'] += 1

                # Detectar formato
                if format_yyyy_mm_dd.match(pub_date):
                    date_format = 'YYYY-MM-DD'
                elif format_yyyy_mm.match(pub_date):
                    date_format = 'YYYY-MM'
                elif format_yyyy.match(pub_date):
                    date_format = 'YYYY'
                else:
                    date_format = f'OTHER: {pub_date}'

                date_formats[date_format] += 1
                stats_by_area[area_name]['formats'][date_format] += 1
            else:
                papers_without_date += 1
                stats_by_area[area_name]['without_date'] += 1

                # Guardar ejemplos
                if len(examples_without_date) < 10:
                    examples_without_date.append({
                        'area': area_name,
                        'paperId': paper.get('paperId'),
                        'title': paper.get('title', 'N/A')[:80],
                        'year': paper.get('year'),
                        'publicationDate': pub_date
                    })

    # Resultados globales
    print("\n" + "="*80)
    print("RESULTADOS GLOBALES")
    print("="*80)
    print(f"\nTotal papers analizados: {total_papers:,}")
    print(f"Papers CON publicationDate: {papers_with_date:,} ({papers_with_date/total_papers*100:.2f}%)")
    print(f"Papers SIN publicationDate: {papers_without_date:,} ({papers_without_date/total_papers*100:.2f}%)")

    # Formatos de fecha
    print("\n" + "-"*80)
    print("DISTRIBUCIÓN DE FORMATOS")
    print("-"*80)
    for date_format, count in date_formats.most_common():
        percentage = count / papers_with_date * 100 if papers_with_date > 0 else 0
        print(f"  {date_format:20s}: {count:8,} papers ({percentage:6.2f}% de los que tienen fecha)")

    # Estadísticas por área
    print("\n" + "-"*80)
    print("ESTADÍSTICAS POR ÁREA")
    print("-"*80)
    print(f"{'Área':<40} {'Total':>10} {'Con fecha':>12} {'Sin fecha':>12} {'% con fecha':>12}")
    print("-"*80)

    for area_name in sorted(stats_by_area.keys()):
        stats = stats_by_area[area_name]
        pct_with_date = stats['with_date'] / stats['total'] * 100 if stats['total'] > 0 else 0
        print(f"{area_name:<40} {stats['total']:>10,} {stats['with_date']:>12,} "
              f"{stats['without_date']:>12,} {pct_with_date:>11.2f}%")

    # Ejemplos sin fecha
    if examples_without_date:
        print("\n" + "-"*80)
        print("EJEMPLOS DE PAPERS SIN publicationDate (primeros 10)")
        print("-"*80)
        for i, example in enumerate(examples_without_date, 1):
            print(f"\n{i}. Área: {example['area']}")
            print(f"   Paper ID: {example['paperId']}")
            print(f"   Title: {example['title']}")
            print(f"   Year: {example['year']}")
            print(f"   publicationDate: {example['publicationDate']}")

    # Recomendación
    print("\n" + "="*80)
    print("RECOMENDACIÓN")
    print("="*80)

    pct_yyyy_mm_dd = (date_formats.get('YYYY-MM-DD', 0) / papers_with_date * 100
                      if papers_with_date > 0 else 0)
    pct_with_date = papers_with_date / total_papers * 100

    print(f"\n1. Cobertura total: {pct_with_date:.2f}% de papers tienen publicationDate")
    print(f"2. De los que tienen fecha, {pct_yyyy_mm_dd:.2f}% están en formato YYYY-MM-DD")

    if pct_with_date >= 95 and pct_yyyy_mm_dd >= 90:
        print("\n✅ RECOMENDACIÓN: Es SEGURO usar publicationDateOrYear del API")
        print("   - Casi todos los papers tienen fecha")
        print("   - La mayoría están en formato completo YYYY-MM-DD")
    elif pct_with_date >= 80:
        print("\n⚠️  RECOMENDACIÓN: Usar publicationDateOrYear con CUIDADO")
        print("   - Mayoría de papers tienen fecha, pero algunos no")
        print("   - Considerar estrategia híbrida (fecha + year fallback)")
    else:
        print("\n❌ RECOMENDACIÓN: NO usar exclusivamente publicationDateOrYear")
        print("   - Muchos papers sin fecha exacta")
        print("   - Mejor usar filtro por 'year' y post-procesar")

    print("\n" + "="*80)


if __name__ == "__main__":
    analyze_publication_dates()
