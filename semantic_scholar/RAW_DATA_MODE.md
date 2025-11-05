# Raw Data Mode - Sin Deduplicación

## Cambio Implementado

Se **eliminó completamente** la deduplicación de papers. Ahora el extractor guarda **exactamente** lo que el API de Semantic Scholar devuelve, sin ningún filtrado.

## Comportamiento

### Antes (con deduplicación):
```
Query 1: "AI safety" → Encuentra 100 papers → Guarda 100 papers
Query 2: "AI alignment" → Encuentra 80 papers (20 duplicados) → Guarda solo 60 nuevos
Total guardado: 160 papers (sin duplicados)
```

### Ahora (raw data):
```
Query 1: "AI safety" → Encuentra 100 papers → Guarda 100 papers
Query 2: "AI alignment" → Encuentra 80 papers → Guarda 80 papers (aunque haya duplicados)
Total guardado: 180 papers (con duplicados)
```

## Estructura de Salida

### Archivos generados:

```
raw_data/
├── area_AI_Safety_20251027_143022.json
├── area_Adversarial_Robustness_20251027_143022.json
├── area_Interpretability_20251027_143022.json
└── extraction_summary_20251027_143022.json
```

### Formato de archivo de área:

```json
{
  "area": "AI Safety",
  "timestamp": "20251027_143022",
  "total_papers": 500,
  "queries_count": 5,
  "queries": [
    "AI Safety",
    "AI Safety Mechanism Design",
    "AI Safety Crowdsourcing",
    "AI Safety Game Theory",
    "AI Safety Formal Verification"
  ],
  "papers": [
    {
      "paperId": "abc123",
      "title": "Paper Title",
      "abstract": "...",
      "authors": [...],
      "year": 2023,
      "citationCount": 45,
      "venue": "NeurIPS",
      "url": "https://...",
      // ... todos los campos del API ...
      // NO hay campo _metadata
    },
    {
      "paperId": "abc123",  // MISMO paper puede aparecer múltiples veces
      "title": "Paper Title",
      // ... mismos datos ...
    }
  ]
}
```

**Nota:** Los papers **NO tienen** campo `_metadata` - son exactamente como vienen del API.

### Formato del summary:

```json
{
  "mode": "async_raw_data",
  "max_concurrent_areas": 3,
  "total_areas": 10,
  "total_papers_raw": 5000,
  "note": "Raw data without deduplication - papers may appear multiple times across areas",
  "areas": [
    {
      "area": "AI Safety",
      "queries": 5,
      "papers": 500
    },
    {
      "area": "Adversarial Robustness",
      "queries": 6,
      "papers": 450
    }
  ]
}
```

**Ya NO incluye:**
- ❌ `total_papers_unique`
- ❌ `cross_area_papers`
- ❌ `cross_area_analysis`
- ❌ `most_cross_cutting_papers`

## Ventajas

✅ **Raw data puro** - Exactamente lo que devuelve el API

✅ **Sin lógica compleja** - No hay tracking global ni locks

✅ **Más rápido** - Sin overhead de comparación de duplicados

✅ **Más simple** - Código más fácil de entender y mantener

✅ **Trazabilidad perfecta** - Cada archivo refleja exactamente las queries ejecutadas

## Desventajas

❌ **Duplicados entre archivos** - Un paper puede aparecer en múltiples archivos de área

❌ **Duplicados dentro de archivos** - Un paper puede aparecer múltiples veces en el mismo archivo si múltiples queries lo devuelven

❌ **Archivos más grandes** - Más redundancia = más espacio

❌ **Requiere post-procesamiento** - Para obtener papers únicos necesitas deduplicar después

## Post-procesamiento para obtener únicos

Si necesitas papers únicos después de la extracción:

```python
import json
from pathlib import Path

# Leer todos los archivos de área
all_papers = {}

for area_file in Path('raw_data').glob('area_*.json'):
    with open(area_file) as f:
        data = json.load(f)
        for paper in data['papers']:
            paper_id = paper['paperId']
            if paper_id not in all_papers:
                all_papers[paper_id] = paper

print(f"Papers únicos: {len(all_papers)}")

# Guardar papers únicos
with open('papers_unique.json', 'w') as f:
    json.dump(list(all_papers.values()), f, indent=2)
```

## Análisis de duplicados

Para ver cuánta duplicación hay:

```python
from collections import Counter

paper_counts = Counter()

for area_file in Path('raw_data').glob('area_*.json'):
    with open(area_file) as f:
        data = json.load(f)
        for paper in data['papers']:
            paper_counts[paper['paperId']] += 1

# Papers que aparecen múltiples veces
duplicates = {pid: count for pid, count in paper_counts.items() if count > 1}

print(f"Total papers (con duplicados): {sum(paper_counts.values())}")
print(f"Papers únicos: {len(paper_counts)}")
print(f"Papers duplicados: {len(duplicates)}")
print(f"Papers que aparecen 2+ veces: {len([c for c in paper_counts.values() if c >= 2])}")
print(f"Papers que aparecen 3+ veces: {len([c for c in paper_counts.values() if c >= 3])}")
```

## Cambios en el código

### Eliminado:

1. `self.paper_metadata` - Ya no se trackean papers globalmente
2. `self.metadata_lock` - Ya no hay lock para sincronización
3. `_add_metadata()` - Ya no se agrega metadata
4. `_calculate_cross_area_stats()` - Ya no se calculan estadísticas de cross-area

### Simplificado:

**`extract_query()`**:
```python
# Antes:
enriched_papers = await self._add_metadata(papers, area_name, query)
all_papers.extend(enriched_papers)

# Ahora:
all_papers.extend(papers)  # Raw data directo
```

**Summary**:
```python
# Antes:
summary = {
    'total_papers_raw': total_papers,
    'total_papers_unique': unique_papers,
    'cross_area_analysis': {...}
}

# Ahora:
summary = {
    'total_papers_raw': total_papers,
    'note': 'Raw data without deduplication'
}
```

## Uso

### Test rápido:
```bash
cd semantic_scholar
uv run run_async_extraction.py --test
```

### Extracción completa:
```bash
uv run run_async_extraction.py \
    --api-key YOUR_KEY \
    --papers 10000 \
    --workers 10 \
    --year 2000 \
    --citations 0 \
    --secondary
```

## Ejemplo de salida

```
EXTRACCIÓN COMPLETADA
============================================================
Áreas procesadas: 15
Papers totales (raw, sin deduplicación): 75,000
```

**Nota:** Este número incluye duplicados. Para obtener el count único, usa el script de post-procesamiento.

## Comparación de modos

| Aspecto | Raw Data (actual) | Con Deduplicación (anterior) |
|---------|-------------------|------------------------------|
| Papers guardados | Todos (con duplicados) | Solo únicos |
| Metadata en papers | ❌ No | ✅ Sí (`_metadata`) |
| Velocidad | Más rápido | Más lento (overhead de tracking) |
| Complejidad código | Simple | Complejo (locks, tracking) |
| Tamaño archivos | Mayor | Menor |
| Post-procesamiento | Necesario para únicos | Ya viene deduplicado |
| Use case | Raw data analysis | Processed data ready to use |

## Recomendaciones

**Usa Raw Data Mode cuando:**
- ✅ Quieres preservar exactamente lo que devuelve el API
- ✅ Vas a hacer tu propio análisis/procesamiento
- ✅ Necesitas trazabilidad completa de queries
- ✅ Prefieres simplicidad sobre eficiencia de espacio

**Usa Deduplication Mode cuando:**
- ❌ Quieres datos listos para usar
- ❌ El espacio en disco es limitado
- ❌ No quieres hacer post-procesamiento
- ❌ Necesitas identificar papers cross-area automáticamente

## Referencias

- [async_extractor.py](async_extractor.py) - Implementación actual (raw data)
- [ASYNC_IMPLEMENTATION.md](ASYNC_IMPLEMENTATION.md) - Detalles de asyncio
- [data_saver.py](data_saver.py) - Guardado de archivos
