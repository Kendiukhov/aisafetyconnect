# Semantic Scholar Bulk Extractor - Script de Prueba

Script simplificado para extraer papers de Semantic Scholar usando solo el Bulk API.

## Características

- ✅ **Solo Bulk API**: Usa únicamente el endpoint `/paper/search/bulk`
- ✅ **Lee terms.json**: Carga queries desde el archivo `terms.json` en la raíz
- ✅ **Guarda en raw_data/**: Todos los resultados se guardan en formato JSON
- ✅ **Anti-duplicados**: Mantiene set de paper IDs para evitar duplicados
- ✅ **Paginación con token**: Implementa paginación correcta usando tokens
- ✅ **Rate limiting**: Respeta límites del API (1s con key, 3s sin key)
- ✅ **Modo testing**: Por default procesa solo 2 áreas para pruebas rápidas

## Instalación

```bash
cd semantic_scholar
pip install requests
```

## Uso Básico

### Prueba rápida (2 áreas, 500 papers por query)

```bash
python test_bulk_extractor.py
```

Esto procesará:
- Las primeras 2 áreas del `terms.json`
- Máximo 500 papers por query
- Papers desde 2015
- Mínimo 10 citas
- Guarda en `../raw_data/`

### Con API Key (recomendado)

```bash
python test_bulk_extractor.py --api-key "YOUR_API_KEY"
```

### Personalizar parámetros

```bash
python test_bulk_extractor.py \
  --limit-areas 5 \
  --max-papers 2000 \
  --year-from 2010 \
  --min-citations 50 \
  --api-key "YOUR_KEY"
```

## Parámetros

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `--terms-json` | `../terms.json` | Ruta al archivo terms.json |
| `--limit-areas` | `2` | Número de áreas a procesar (None = todas) |
| `--max-papers` | `500` | Máximo papers por query |
| `--year-from` | `2015` | Año inicial (inclusive) |
| `--min-citations` | `10` | Mínimo de citas |
| `--api-key` | `None` | API key de Semantic Scholar |
| `--output-dir` | `../raw_data` | Directorio de salida |

## Estructura de Salida

### Archivos generados en `raw_data/`:

```
raw_data/
├── papers_Mechanistic_Interpretability_20251023_143022.json
├── papers_Mechanistic_Interpretability_Neuroscience_20251023_143145.json
├── papers_Scalable_Oversight_20251023_143310.json
└── extraction_summary_20251023_143500.json
```

### Formato de archivo de papers:

```json
{
  "query": "Mechanistic Interpretability",
  "timestamp": "20251023_143022",
  "total_papers": 347,
  "duration_seconds": 45.2,
  "filters": {
    "year_from": 2015,
    "min_citations": 10
  },
  "papers": [
    {
      "paperId": "649def34f8be52c8b66281af98ae884c09aef38b",
      "title": "Paper Title",
      "abstract": "...",
      "authors": [...],
      "year": 2020,
      "citationCount": 156,
      ...
    }
  ]
}
```

### Formato de summary:

```json
{
  "timestamp": "2025-10-23T14:35:00",
  "total_queries": 5,
  "total_papers": 1523,
  "unique_papers": 1489,
  "queries": [
    {
      "query": "Mechanistic Interpretability",
      "papers_found": 347,
      "duration": 45.2,
      "success": true
    }
  ]
}
```

## Queries Generadas

El script genera queries en 2 niveles desde `terms.json`:

1. **Nivel 1 - Área**: `"Mechanistic Interpretability"`
2. **Nivel 2 - Área + Field**: `"Mechanistic Interpretability Neuroscience"`

Para testing, **solo procesa Primary Fields** (no Secondary Fields).

### Ejemplo con `--limit-areas 2`:

```
Queries generadas:
1. "Mechanistic Interpretability"
2. "Mechanistic Interpretability Neuroscience"
3. "Mechanistic Interpretability Signal Processing"
4. "Mechanistic Interpretability Applied Mathematics"
5. "Mechanistic Interpretability Statistical Physics"
6. "Scalable Oversight"
7. "Scalable Oversight Mechanism Design"
8. "Scalable Oversight Crowdsourcing/Human Computation"
9. "Scalable Oversight Game Theory"
10. "Scalable Oversight Formal Verification"
```

## Logs

El script genera dos tipos de logs:

1. **Console output**: Progreso en tiempo real
2. **semantic_scholar_test.log**: Log detallado guardado en archivo

## Rate Limiting

- **Con API key**: ~1 request/segundo
- **Sin API key**: ~1 request/3 segundos
- Delay entre páginas: 2 segundos
- Delay entre queries: 5 segundos

## Diferencias vs Script Original

| Característica | Script Original | Este Script |
|----------------|----------------|-------------|
| APIs usadas | 3 (search, bulk, match) | 1 (solo bulk) |
| Base de datos | PostgreSQL | No (solo archivos) |
| Output | PostgreSQL + CSV | JSON files |
| Configuración | Muchos parámetros | Simple y directo |
| Propósito | Producción | Testing |

## Siguiente Paso

Una vez que hayas testeado y verificado que funciona:

1. Revisar los archivos JSON en `raw_data/`
2. Verificar que los papers son relevantes
3. Ajustar parámetros según necesidad
4. Ejecutar con más áreas: `--limit-areas 5` o sin límite

## Troubleshooting

### Error: "No module named 'requests'"
```bash
pip install requests
```

### Error: "File not found: terms.json"
```bash
# Verificar que estás en la carpeta correcta
cd semantic_scholar
ls ../terms.json  # Debe existir
```

### Rate limit (HTTP 429)
```bash
# Agregar API key o aumentar delays
python test_bulk_extractor.py --api-key "YOUR_KEY"
```

### Sin papers encontrados
- Verificar que las queries son correctas
- Reducir `--min-citations` (probar con 0)
- Aumentar rango de años `--year-from 2000`
