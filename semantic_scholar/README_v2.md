## Semantic Scholar Extractor v2 - Refactorizado y Paralelizado

Versión simplificada, modular y con soporte para extracción paralela.

## 📁 Estructura

```
semantic_scholar/
├── api_client.py           # HTTP client (solo requests)
├── query_builder.py        # Genera queries desde terms.json
├── data_saver.py           # Guarda archivos JSON
├── simple_extractor.py     # Extractor secuencial
├── parallel_extractor.py   # Extractor paralelo (por área)
├── run_simple.py           # CLI para versión simple
├── run_parallel.py         # CLI para versión paralela
├── quick_test.py           # Test rápido
└── test_bulk_extractor.py  # Versión original (deprecated)
```

---

## 🚀 Uso

### 1. Test Rápido (1 query)

```bash
uv run quick_test.py
uv run quick_test.py "YOUR_API_KEY"
```

### 2. Extractor Simple (Secuencial)

Procesa áreas una por una:

```bash
# Básico
uv run run_simple.py

# Con parámetros
uv run run_simple.py \
  --limit-areas 3 \
  --max-papers 1000 \
  --year-from 2010 \
  --min-citations 20 \
  --api-key "YOUR_KEY"
```

**Ventajas**:
- ✅ Más simple de entender
- ✅ Menos uso de recursos
- ✅ Bueno para debugging
- ✅ Rate limiting más controlado

**Desventajas**:
- ❌ Más lento (procesa área por área)

### 3. Extractor Paralelo (Por Área) ⭐ Recomendado

Procesa múltiples áreas en paralelo:

```bash
# Básico (3 áreas, 3 workers)
uv run run_parallel.py

# Con parámetros
uv run run_parallel.py \
  --limit-areas 5 \
  --max-workers 3 \
  --max-papers 1000 \
  --year-from 2010 \
  --min-citations 20 \
  --api-key "YOUR_KEY"
```

**Ventajas**:
- ✅ Mucho más rápido (3x-5x)
- ✅ Usa tiempo de espera de rate limiting eficientemente
- ✅ Thread-safe (sin race conditions)

**Desventajas**:
- ⚠️ Más uso de recursos (CPU/memoria)
- ⚠️ Logs entrelazados (más difícil de leer)

---

## 📊 Comparación de Velocidad

### Ejemplo: 3 áreas, 5 queries por área, 500 papers por query

**Versión Simple (Secuencial)**:
```
Área 1 → 5 queries × 30s = 150s
Área 2 → 5 queries × 30s = 150s
Área 3 → 5 queries × 30s = 150s
-----------------------------------
TOTAL: ~450 segundos (7.5 minutos)
```

**Versión Paralela (3 workers)**:
```
Área 1 ──┐
Área 2 ──┼─→ En paralelo → 5 queries × 30s = 150s
Área 3 ──┘
-----------------------------------
TOTAL: ~150 segundos (2.5 minutos)
```

**Speedup: 3x más rápido** 🚀

---

## 🏗️ Arquitectura

### Separación de Responsabilidades

```
┌─────────────────────┐
│   API Client        │  ← Solo HTTP requests
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  Query Builder      │  ← Genera queries desde JSON
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│   Data Saver        │  ← Guarda archivos JSON
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│ Simple Extractor    │  ← Orquestador secuencial
│ Parallel Extractor  │  ← Orquestador paralelo
└─────────────────────┘
```

### Flujo de Extracción

```
1. Load terms.json
   ↓
2. Build queries by area
   ↓
3. For each area (secuencial o paralelo):
   ↓
   a. For each query:
      ↓
      - Paginar con tokens
      - Filtrar duplicados
      - Acumular papers
   ↓
   b. Guardar área en JSON
   ↓
4. Guardar resumen final
```

---

## 📦 Output

### Archivos generados:

```
raw_data/
├── area_Mechanistic_Interpretability_20251023_143022.json
├── area_Scalable_Oversight_20251023_143145.json
├── area_Adversarial_Robustness_20251023_143310.json
└── extraction_summary_20251023_143500.json
```

### Estructura de área:

```json
{
  "area": "Mechanistic_Interpretability",
  "timestamp": "20251023_143022",
  "total_papers": 2347,
  "queries_count": 5,
  "queries": [
    "Mechanistic Interpretability",
    "Mechanistic Interpretability Neuroscience",
    ...
  ],
  "papers": [...]
}
```

### Estructura de resumen:

```json
{
  "mode": "parallel",
  "max_workers": 3,
  "total_areas": 3,
  "total_papers": 6521,
  "unique_papers": 6234,
  "areas": [
    {
      "area": "Mechanistic_Interpretability",
      "queries": 5,
      "papers": 2347
    },
    ...
  ]
}
```

---

## 🔧 Parámetros

| Parámetro | Simple | Paralelo | Default | Descripción |
|-----------|--------|----------|---------|-------------|
| `--terms-json` | ✅ | ✅ | `../terms.json` | Path a terms.json |
| `--limit-areas` | ✅ | ✅ | 2 / 3 | Áreas a procesar |
| `--max-workers` | ❌ | ✅ | 3 | Workers paralelos |
| `--max-papers` | ✅ | ✅ | 500 | Papers por query |
| `--year-from` | ✅ | ✅ | 2015 | Año inicial |
| `--min-citations` | ✅ | ✅ | 10 | Mínimo de citas |
| `--api-key` | ✅ | ✅ | None | API key |
| `--output-dir` | ✅ | ✅ | `../raw_data` | Directorio salida |
| `--include-secondary` | ✅ | ✅ | False | Secondary fields |

---

## 🧪 Testing

### Test unitario rápido:

```bash
# Test del API client
python -c "
from api_client import SemanticScholarAPI
api = SemanticScholarAPI()
papers, token = api.search('AI safety', limit=10)
print(f'Papers: {len(papers)}, Token: {token is not None}')
"

# Test del query builder
python -c "
from query_builder import load_terms_json, build_queries_by_area
data = load_terms_json('../terms.json')
queries = build_queries_by_area(data, limit_areas=1)
print(f'Áreas: {len(queries)}')
print(f'Primera área: {list(queries.keys())[0]}')
print(f'Queries: {len(list(queries.values())[0])}')
"
```

### Test de extracción pequeña:

```bash
# Simple (1 área, 100 papers)
uv run run_simple.py --limit-areas 1 --max-papers 100

# Paralelo (2 áreas, 2 workers, 100 papers)
uv run run_parallel.py --limit-areas 2 --max-workers 2 --max-papers 100
```

---

## 🔍 Logs

### Simple:
```
extraction_simple.log
- Un solo thread
- Fácil de seguir
```

### Paralelo:
```
extraction_parallel.log
- Múltiples threads (Thread-1, Thread-2, etc)
- Logs entrelazados
- Buscar por thread name para seguir un área específica
```

---

## 💡 Cuándo Usar Cada Versión

### Usa **Simple** si:
- Estás debuggeando
- Tienes pocas áreas (~1-2)
- Quieres minimizar uso de recursos
- Prefieres logs más claros

### Usa **Paralelo** si:
- Tienes muchas áreas (3+)
- Quieres máxima velocidad
- Tienes API key (mejor rate limiting)
- No te importa usar más CPU/memoria

---

## 🚦 Rate Limiting

El extractor respeta los límites del API:

- **Sin API key**: 1 request cada 3 segundos
- **Con API key**: 1 request por segundo
- **Entre páginas**: 2 segundos
- **Entre queries**: 5 segundos
- **HTTP 429**: Espera 10 segundos automáticamente

En modo paralelo, cada thread tiene su propio rate limiter.

---

## 🐛 Troubleshooting

### Error: "No module named 'api_client'"
```bash
# Asegúrate de estar en la carpeta correcta
cd semantic_scholar
```

### Rate limit constante (429)
```bash
# Reducir workers en paralelo
uv run run_parallel.py --max-workers 2

# O usar versión simple
uv run run_simple.py
```

### Logs muy verbosos
```bash
# Editar el script y cambiar nivel de logging
logging.basicConfig(level=logging.WARNING)  # En vez de INFO
```

---

## 📚 Siguiente Paso

1. Probar con `quick_test.py`
2. Ejecutar versión simple con 1-2 áreas
3. Si funciona, ejecutar versión paralela
4. Revisar archivos en `raw_data/`
5. Ajustar parámetros según necesidad
