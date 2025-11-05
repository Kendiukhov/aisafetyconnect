# Implementación Async con asyncio

## Resumen

Esta implementación utiliza **asyncio** en lugar de threads (`ThreadPoolExecutor`) para lograr máxima eficiencia en operaciones I/O-bound como las llamadas HTTP al Semantic Scholar API.

## Ventajas de asyncio vs threads

### 1. Menor overhead
- **Threads**: Cada thread consume ~8MB de memoria stack
- **Asyncio**: Coroutines son mucho más livianas (~1KB)
- Podemos manejar miles de coroutines vs cientos de threads

### 2. Mejor control de concurrencia
- **Threads**: Context switching manejado por el OS
- **Asyncio**: Context switching controlado explícitamente por el programa
- Más predecible y eficiente

### 3. Ideal para I/O-bound
- Nuestro bottleneck es esperar respuestas HTTP (I/O)
- asyncio permite "pausar" mientras esperamos sin bloquear
- Threads se quedan bloqueados esperando

### 4. Mismo rate limiting
- Seguimos respetando 1 request/segundo con el rate limiter global
- Pero la gestión de espera es más eficiente

## Arquitectura

```
async_rate_limiter.py          # Rate limiter con asyncio.Lock
    ↓
async_api_client.py            # HTTP client con aiohttp
    ↓
async_extractor.py             # Extractor con asyncio.gather
    ↓
run_async_extraction.py        # Script principal
```

## Componentes

### 1. AsyncGlobalRateLimiter

```python
class AsyncGlobalRateLimiter:
    def __init__(self, requests_per_second: float = 1.0):
        self.min_interval = 1.0 / requests_per_second
        self.lock = asyncio.Lock()  # async-safe lock

    async def wait(self):
        async with self.lock:
            # Calcular y esperar si es necesario
            await asyncio.sleep(sleep_time)
```

**Diferencias con versión threads:**
- Usa `asyncio.Lock` en vez de `threading.Lock`
- Usa `await asyncio.sleep()` en vez de `time.sleep()`
- Debe ser llamado con `await`

### 2. AsyncSemanticScholarAPI

```python
class AsyncSemanticScholarAPI:
    async def search(self, query: str, ...) -> Tuple[List[Dict], Optional[str]]:
        # Rate limiting
        await self.rate_limiter.wait()

        # HTTP request con aiohttp
        async with self.session.get(...) as response:
            data = await response.json()
            return papers, next_token
```

**Características:**
- Usa `aiohttp` en vez de `requests`
- Session pool para reutilizar conexiones HTTP
- Context manager async (`async with`)
- Todas las operaciones I/O son `await`

### 3. AsyncExtractor

```python
class AsyncExtractor:
    async def extract_area(self, area_name, queries, ...):
        async with AsyncSemanticScholarAPI(api_key) as api:
            for query in queries:
                papers = await self.extract_query(api, query, ...)
                all_papers.extend(papers)
        return results

    async def run(self, ...):
        # Crear tasks para cada área
        tasks = [
            asyncio.create_task(self.extract_area(...))
            for area_name, queries in queries_by_area.items()
        ]

        # Ejecutar con límite de concurrencia
        semaphore = asyncio.Semaphore(max_concurrent_areas)
        results = await asyncio.gather(*tasks)
```

**Estrategia de concurrencia:**
- Cada área es una coroutine independiente
- `asyncio.Semaphore` limita cuántas áreas se procesan simultáneamente
- `asyncio.gather()` ejecuta todas las tasks y espera resultados
- El rate limiter global coordina todas las requests

## Uso

### Test simple (2 áreas, 50 papers)

```bash
cd semantic_scholar
uv run run_async_extraction.py --test
```

### Extracción completa con API key

```bash
# Opción 1: Variable de entorno
export SEMANTIC_SCHOLAR_API_KEY="your_key"
uv run run_async_extraction.py

# Opción 2: Parámetro directo
uv run run_async_extraction.py --api-key your_key
```

### Extracción personalizada

```bash
uv run run_async_extraction.py \
    --api-key YOUR_KEY \
    --areas 5 \
    --papers 1000 \
    --workers 3 \
    --year 2015 \
    --citations 10
```

### Todos los parámetros

```
--api-key      API key de Semantic Scholar
--terms        Path a terms.json (default: ../terms.json)
--output       Directorio de salida (default: ../raw_data)
--areas        Número de áreas a procesar (default: todas)
--papers       Max papers por query (default: 500)
--workers      Áreas concurrentes (default: 3)
--year         Año inicial (default: 2015)
--citations    Mínimo de citas (default: 10)
--secondary    Incluir secondary fields
--test         Modo test rápido
```

## Test del rate limiter

```bash
uv run test_async.py
```

Output esperado:
```
Task 0: Request permitido en 1698765432.123
Task 1: Request permitido en 1698765433.125  # ~1s después
Task 2: Request permitido en 1698765434.127  # ~1s después

Gaps entre requests:
  Gap 1: 1.002s  ✅ OK (>= 1 segundo)
  Gap 2: 1.002s  ✅ OK (>= 1 segundo)
```

## Performance esperado

Con rate limit de 1 req/segundo:

- **1 área con 10 queries**: ~10-15 segundos
- **3 áreas con 10 queries c/u**: ~10-15 segundos (paralelo)
- **10 áreas con 5 queries c/u**: ~17-20 segundos (50 queries total)

La paralelización por área permite procesar múltiples áreas "al mismo tiempo", pero respetando el límite global de 1 request/segundo.

## Diferencias con versión threads

| Aspecto | Threads | Asyncio |
|---------|---------|---------|
| Concurrencia | ThreadPoolExecutor | asyncio.gather + Semaphore |
| HTTP | requests (sync) | aiohttp (async) |
| Lock | threading.Lock | asyncio.Lock |
| Sleep | time.sleep() | await asyncio.sleep() |
| Overhead | ~8MB por thread | ~1KB por coroutine |
| Max concurrencia | ~100 threads | Miles de coroutines |

## Troubleshooting

### Error: "RuntimeError: Event loop is closed"

**Causa**: Intentar reutilizar un event loop cerrado

**Solución**: Usar `asyncio.run()` que crea un nuevo loop cada vez

### Error: "aiohttp.ClientError: Cannot connect to host"

**Causa**: Problemas de red o timeout

**Solución**: Aumentar timeout en `ClientTimeout(total=30)`

### Error: HTTP 429 (Rate limit)

**Causa**: Requests demasiado rápidos

**Solución**: Verificar que el rate limiter está funcionando:
```bash
uv run test_async.py
```

## Dependencias

Agregar a `pyproject.toml`:

```toml
[project]
dependencies = [
    "aiohttp>=3.9.0",
    "requests>=2.31.0",
]
```

Instalar:
```bash
uv sync
```

## Próximos pasos

1. ✅ Implementar rate limiter async
2. ✅ Convertir API client a async
3. ✅ Crear extractor async
4. ✅ Scripts de test y ejecución
5. ⏳ Ejecutar test completo
6. ⏳ Benchmarking vs versión threads
7. ⏳ Optimizaciones adicionales si es necesario

## Referencias

- [asyncio docs](https://docs.python.org/3/library/asyncio.html)
- [aiohttp docs](https://docs.aiohttp.org/)
- [Real Python - Async IO](https://realpython.com/async-io-python/)
