# Opción 3A: Raw Data con Metadata Cross-Area

## Resumen

Esta implementación guarda **raw data completo** - cada paper aparece en TODAS las áreas donde fue encontrado, enriquecido con metadata que indica en qué otras áreas también aparece.

## Concepto

### Problema que resuelve:

**Antes (con deduplicación global):**
```
Área "AI Safety" encuentra paper X → se guarda
Área "Adversarial Robustness" encuentra paper X → ❌ se DESCARTA (ya visto)
```

**Ahora (Opción 3A):**
```
Área "AI Safety" encuentra paper X → se guarda con metadata
Área "Adversarial Robustness" encuentra paper X → ✅ se GUARDA de nuevo con metadata actualizada
```

## Estructura de salida

### Archivos generados:

```
raw_data/
├── area_AI_Safety_20251027_143022.json
├── area_Adversarial_Robustness_20251027_143022.json
├── area_Interpretability_20251027_143022.json
└── extraction_summary_20251027_143022.json
```

### Formato de un archivo de área:

```json
{
  "area": "AI Safety",
  "timestamp": "20251027_143022",
  "total_papers": 150,
  "queries_count": 5,
  "queries": ["AI safety", "AI alignment", ...],
  "papers": [
    {
      "paperId": "abc123",
      "title": "Paper Title",
      "abstract": "...",
      "authors": [...],
      "year": 2023,
      "citationCount": 45,
      // ... todos los campos normales del API ...

      "_metadata": {
        "found_in_areas": ["AI Safety"],
        "primary_area": "AI Safety",
        "is_cross_area": false,
        "total_areas": 1,
        "discovery_info": {
          "first_discovered_in": "AI Safety",
          "first_query": "AI safety",
          "first_seen_timestamp": "2025-10-27T14:30:22"
        },
        "queries_per_area": {
          "AI Safety": ["AI safety", "AI alignment"]
        }
      }
    },
    {
      "paperId": "xyz789",
      "title": "Cross-Area Paper Title",
      // ... campos normales ...

      "_metadata": {
        "found_in_areas": ["AI Safety", "Adversarial Robustness"],
        "primary_area": "AI Safety",
        "is_cross_area": true,
        "total_areas": 2,
        "also_appears_in": ["Adversarial Robustness"],
        "discovery_info": {
          "first_discovered_in": "AI Safety",
          "first_query": "AI safety adversarial",
          "first_seen_timestamp": "2025-10-27T14:30:22"
        },
        "queries_per_area": {
          "AI Safety": ["AI safety adversarial"],
          "Adversarial Robustness": ["adversarial examples", "robust ML"]
        }
      }
    }
  ]
}
```

### Formato del summary:

```json
{
  "mode": "async",
  "timestamp": "2025-10-27T14:30:22",
  "max_concurrent_areas": 3,
  "total_areas": 10,
  "total_papers_raw": 5000,
  "total_papers_unique": 3500,
  "cross_area_papers": 1500,
  "areas": [
    {
      "area": "AI Safety",
      "queries": 5,
      "papers": 500
    },
    // ...
  ],
  "cross_area_analysis": {
    "total_cross_area": 1500,
    "papers_by_area_count": {
      "papers_in_1_areas": 2000,
      "papers_in_2_areas": 1200,
      "papers_in_3_areas": 250,
      "papers_in_4_areas": 50
    },
    "most_cross_cutting_papers": [
      {
        "paperId": "xyz789",
        "areas": ["AI Safety", "Adversarial Robustness", "Interpretability", "Alignment"],
        "total_areas": 4
      },
      // ... top 20
    ]
  }
}
```

## Campos de metadata

### `_metadata` (en cada paper):

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `found_in_areas` | `List[str]` | Lista de TODAS las áreas donde apareció este paper |
| `primary_area` | `str` | Área donde se descubrió PRIMERO |
| `is_cross_area` | `bool` | `true` si aparece en múltiples áreas |
| `total_areas` | `int` | Número total de áreas donde apareció |
| `also_appears_in` | `List[str]` | (Solo si cross-area) Otras áreas además de la actual |
| `discovery_info` | `Dict` | Info sobre el primer descubrimiento |
| `queries_per_area` | `Dict[str, List[str]]` | Qué queries trajeron este paper en cada área |

### `discovery_info`:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `first_discovered_in` | `str` | Área donde se vio primero |
| `first_query` | `str` | Query que lo encontró primero |
| `first_seen_timestamp` | `str` | Timestamp ISO del descubrimiento |

## Uso y análisis

### 1. Cargar papers de un área específica:

```python
import json

with open('area_AI_Safety.json') as f:
    data = json.load(f)
    papers = data['papers']

print(f"Total papers en AI Safety: {len(papers)}")
```

### 2. Filtrar papers únicos vs cross-area:

```python
# Solo papers únicos de esta área
unique_papers = [
    p for p in papers
    if not p['_metadata']['is_cross_area']
]

# Solo papers cross-area
cross_papers = [
    p for p in papers
    if p['_metadata']['is_cross_area']
]

print(f"Únicos: {len(unique_papers)}, Cross-area: {len(cross_papers)}")
```

### 3. Encontrar papers que aparecen en áreas específicas:

```python
# Papers que aparecen en AI Safety Y Adversarial Robustness
safety_and_robustness = [
    p for p in papers
    if 'Adversarial Robustness' in p['_metadata']['found_in_areas']
]

print(f"Papers en ambas áreas: {len(safety_and_robustness)}")
```

### 4. Contar papers únicos globalmente:

```python
from pathlib import Path

all_paper_ids = set()
for area_file in Path('raw_data').glob('area_*.json'):
    with open(area_file) as f:
        data = json.load(f)
        all_paper_ids.update([p['paperId'] for p in data['papers']])

print(f"Total papers únicos: {len(all_paper_ids)}")
```

### 5. Identificar papers más "centrales":

```python
# Cargar summary
with open('extraction_summary.json') as f:
    summary = json.load(f)

top_papers = summary['cross_area_analysis']['most_cross_cutting_papers']

print("Papers más cross-cutting:")
for paper in top_papers[:5]:
    print(f"- {paper['paperId']}: {paper['total_areas']} áreas")
    print(f"  Areas: {', '.join(paper['areas'])}")
```

## Ventajas

✅ **Raw data completo**: Cada área contiene TODOS sus papers

✅ **Trazabilidad**: Sabes exactamente dónde apareció cada paper

✅ **Análisis flexible**: Puedes filtrar por área, cross-area, etc.

✅ **Identificación de papers centrales**: Papers en múltiples áreas son probablemente más importantes

✅ **Queries exactas**: Sabes qué queries trajeron cada paper

✅ **Timestamp de descubrimiento**: Orden cronológico de descubrimiento

## Desventajas

❌ **Duplicación de datos**: Un paper en 5 áreas se guarda 5 veces completo

❌ **Archivos más grandes**: Mayor uso de disco

❌ **Requiere post-procesamiento**: Para contar únicos necesitas deduplicar después

## Comparación con otras opciones

| Aspecto | Opción 1 (dedupe por área) | Opción 3A (metadata) |
|---------|---------------------------|---------------------|
| Paper aparece en múltiples áreas | ✅ Sí, una vez por área | ✅ Sí, una vez por área |
| Metadata de cross-area | ❌ No | ✅ Sí |
| Tamaño de archivos | Normal | ~20-30% más grande |
| Análisis de overlaps | Difícil | Fácil |
| Identificar papers centrales | Difícil | Fácil |
| Raw data completo | ✅ Sí | ✅ Sí |

## Testing

```bash
# Test rápido (2 áreas, 20 papers)
cd semantic_scholar
uv run test_option3a.py

# Verificar metadata
ls ../raw_data_test/
cat ../raw_data_test/area_*.json | jq '.[0]._metadata'
```

## Ejecución

### Test pequeño:
```bash
uv run run_async_extraction.py --test
```

### Extracción completa:
```bash
uv run run_async_extraction.py \
    --api-key YOUR_KEY \
    --papers 10000 \
    --workers 5 \
    --year 2015 \
    --citations 0
```

## Implementación

La implementación se encuentra en:
- `async_extractor.py`: Lógica principal con `_add_metadata()` y `_calculate_cross_area_stats()`
- `data_saver.py`: Guardado sin cambios (metadata viene en los papers)
- `test_option3a.py`: Script de testing

### Flujo:

1. **Primera área encuentra paper X**:
   ```python
   paper_metadata[X] = {
       'first_area': 'AI Safety',
       'areas': ['AI Safety'],
       'queries_per_area': {'AI Safety': ['AI safety']}
   }
   ```

2. **Segunda área encuentra paper X**:
   ```python
   paper_metadata[X]['areas'].append('Adversarial Robustness')
   paper_metadata[X]['queries_per_area']['Adversarial Robustness'] = ['adversarial examples']
   ```

3. **Al guardar**:
   - Paper X se guarda en `area_AI_Safety.json` con metadata completa
   - Paper X se guarda en `area_Adversarial_Robustness.json` con metadata completa
   - Metadata indica `found_in_areas: ['AI Safety', 'Adversarial Robustness']`

## Referencias

- [async_extractor.py](async_extractor.py) - Implementación principal
- [ASYNC_IMPLEMENTATION.md](ASYNC_IMPLEMENTATION.md) - Detalles de asyncio
- [data_saver.py](data_saver.py) - Guardado de archivos
