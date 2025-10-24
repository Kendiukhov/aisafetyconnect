#!/usr/bin/env python3
"""
Quick test - Una sola query para verificar que el API funciona
"""

import requests
import json
import sys
from datetime import datetime

# Configuración básica
BULK_API = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
QUERY = "AI safety"
OUTPUT_FILE = "../raw_data/quick_test.json"

# Obtener API key de argumentos si existe
api_key = None
if len(sys.argv) > 1:
    api_key = sys.argv[1]

print("="*60)
print("QUICK TEST - Semantic Scholar Bulk API")
print("="*60)
print(f"Query: {QUERY}")
print(f"API Key: {'Sí ✅' if api_key else 'No (sin autenticar)'}")
print(f"Haciendo request...")

# Parámetros del request
params = {
    "query": QUERY,
    "limit": 10,  # Solo 10 papers para test rápido
    "fields": "title,abstract,authors,year,citationCount,url",
    "year": "2020-",
    "sort": "citationCount:desc"
}

# Headers
headers = {
    "User-Agent": "AIResearchBot/QuickTest",
    "Accept": "application/json",
}

# Agregar API key si existe
if api_key:
    headers["x-api-key"] = api_key

try:
    # Hacer el request
    response = requests.get(BULK_API, params=params, headers=headers, timeout=30)

    print(f"Status code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        papers = data.get('data', [])
        total = data.get('total', 0)

        print(f"✅ SUCCESS!")
        print(f"Total disponibles: {total}")
        print(f"Recibidos: {len(papers)}")
        print()

        # Mostrar los primeros 3
        print("Top 3 papers:")
        for i, paper in enumerate(papers[:3], 1):
            print(f"\n{i}. {paper.get('title', 'Sin título')}")
            print(f"   Año: {paper.get('year', 'N/A')}")
            print(f"   Citas: {paper.get('citationCount', 0)}")
            print(f"   Autores: {len(paper.get('authors', []))}")

        # Guardar resultado completo
        output = {
            "timestamp": datetime.now().isoformat(),
            "query": QUERY,
            "total_found": total,
            "papers_retrieved": len(papers),
            "papers": papers
        }

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Guardado en: {OUTPUT_FILE}")

    elif response.status_code == 429:
        print("❌ Rate limit! Espera unos segundos e intenta de nuevo")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text[:500])

except Exception as e:
    print(f"❌ Exception: {e}")

print("\n" + "="*60)
