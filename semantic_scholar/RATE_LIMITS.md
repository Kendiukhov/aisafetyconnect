# Semantic Scholar API - Rate Limits Oficiales

## 📚 Fuentes Oficiales

- **API Product Page**: https://www.semanticscholar.org/product/api
- **API Release Notes**: https://github.com/allenai/s2-folks/blob/main/API_RELEASE_NOTES.md
- **Solicitar API Key**: https://www.semanticscholar.org/product/api#api-key-form

---

## 🔢 Rate Limits por Tipo de Usuario

### **Sin API Key (Unauthenticated)**

```
5,000 requests / 5 minutos
= ~16.6 requests/segundo (teórico)
```

**⚠️ IMPORTANTE**:
- Es un **pool compartido** entre TODOS los usuarios sin autenticar a nivel global
- En la práctica puede ser mucho menor si hay mucha carga
- Recomendación: Usar 1 request/segundo para ser conservador

**Endpoints afectados**:
- Todos los endpoints públicos

---

### **Con API Key (Authenticated)**

#### Para Bulk Search API (`/paper/search/bulk`):
```
1 request / segundo
```

**Endpoints específicos con este límite**:
- `/paper/batch`
- `/paper/search`
- `/paper/search/bulk` ← El que usamos

#### Para otros endpoints:
```
10 requests / segundo
```

**Endpoints con límite más alto**:
- `/paper/{paper_id}`
- `/author/{author_id}`
- Etc.

---

## 🎯 Nuestro Caso de Uso

Usamos **`/paper/search/bulk`**, por lo tanto:

| Configuración | Rate Limit Real | Rate Limit Usado en Código |
|---------------|-----------------|---------------------------|
| Sin API Key | 5000 req/5min (compartido) | 1 req/s (conservador) |
| Con API Key | 1 req/s | 1 req/s |

---

## ⏱️ Cálculos de Tiempo

### **Ejemplo: 100 queries**

**Sin API Key (conservador, 1 req/s)**:
```
100 queries × 1 segundo = 100 segundos = 1.67 minutos
```

**Con API Key (1 req/s)**:
```
100 queries × 1 segundo = 100 segundos = 1.67 minutos
```

**Con API Key Premium (hipotético, no documentado)**:
```
Algunos usuarios reportan límites más altos con cuentas premium
Pero no está oficialmente documentado
```

---

## 🚦 Manejo de Rate Limiting en el Código

### **HTTP 429 (Rate Limit Exceeded)**

Cuando excedes el límite, el API retorna:
```http
HTTP/1.1 429 Too Many Requests
```

**Nuestra estrategia**:
```python
if response.status_code == 429:
    logger.warning("Rate limit (429), esperando 10s...")
    time.sleep(10)
    return [], None  # Reintentar en siguiente llamada
```

### **Exponential Backoff (Requerido)**

Según la documentación oficial:
> "We now require the use of exponential backoff strategies for API calls"

**Implementación actual**:
- Delay fijo de 10 segundos en 429
- **TODO**: Implementar exponential backoff verdadero

**Exponential backoff correcto**:
```python
def exponential_backoff(attempt):
    wait_time = min(60, 2 ** attempt + random.uniform(0, 1))
    return wait_time

# Intento 1: 2^0 + random = ~1-2s
# Intento 2: 2^1 + random = ~2-3s
# Intento 3: 2^2 + random = ~4-5s
# Intento 4: 2^3 + random = ~8-9s
# ...
# Max: 60 segundos
```

---

## 📊 Rate Limit Headers (No documentados)

Algunos APIs incluyen headers como:
```http
X-RateLimit-Limit: 1
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1635724800
```

**Semantic Scholar**: No documentan estos headers públicamente.

---

## 🔑 Cómo Obtener API Key

1. Ir a: https://www.semanticscholar.org/product/api#api-key-form
2. Completar formulario:
   - Nombre
   - Email
   - Organización
   - Caso de uso
3. Esperar aprobación (usualmente 1-2 días)
4. Recibir API key por email

**Requisitos**:
- Caso de uso académico o de investigación
- No comercial (o contactar para uso comercial)

---

## 🧪 Testing de Rate Limits

### **Test sin API Key**:
```bash
# Hacer 10 requests rápidos
for i in {1..10}; do
  curl "https://api.semanticscholar.org/graph/v1/paper/search/bulk?query=AI&limit=10"
  echo "Request $i"
done
```

**Resultado esperado**:
- Primeros ~5 requests: OK (200)
- Siguientes: 429 (si el pool está lleno)

### **Test con API Key**:
```bash
# Hacer 2 requests en 1 segundo
curl -H "x-api-key: YOUR_KEY" "https://api.semanticscholar.org/graph/v1/paper/search/bulk?query=AI&limit=10" &
curl -H "x-api-key: YOUR_KEY" "https://api.semanticscholar.org/graph/v1/paper/search/bulk?query=AI&limit=10" &
wait
```

**Resultado esperado**:
- Primera request: OK (200)
- Segunda request: 429

---

## 📈 Optimizaciones para Rate Limits

### **1. Batch Endpoints (si disponibles)**

En vez de:
```
Query 1 → Request 1
Query 2 → Request 2
Query 3 → Request 3
```

Usar:
```
Queries [1,2,3] → Request 1 (batch)
```

**Nota**: El bulk search ya optimiza esto parcialmente.

### **2. Caching**

```python
# Guardar respuestas en cache
cache = {}
if query in cache:
    return cache[query]
else:
    response = api.search(query)
    cache[query] = response
    return response
```

### **3. Request Queueing**

```python
# Cola de requests con rate limiting
from queue import Queue
import time

request_queue = Queue()
last_request_time = 0

def rate_limited_request():
    global last_request_time
    elapsed = time.time() - last_request_time
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)

    response = make_request()
    last_request_time = time.time()
    return response
```

### **4. Paralelización Inteligente**

```python
# En vez de N workers paralelos constantes:
# Usar 1 worker por cada 1 req/s de rate limit

if api_key:
    max_workers = 1  # Solo 1 req/s permitido
else:
    max_workers = 1  # Conservador con pool compartido
```

---

## ⚠️ Errores Comunes

### **Error 1: Demasiados workers en paralelo**

```python
# ❌ MAL: 10 workers con 1 req/s limit
ThreadPoolExecutor(max_workers=10)

# ✅ BIEN: 1 worker (o 2-3 con delays)
ThreadPoolExecutor(max_workers=1)
```

### **Error 2: No usar delays entre requests**

```python
# ❌ MAL: Requests consecutivos sin delay
for query in queries:
    api.search(query)

# ✅ BIEN: Delay entre requests
for query in queries:
    api.search(query)
    time.sleep(1.0)
```

### **Error 3: No manejar 429**

```python
# ❌ MAL: Fallar en 429
if status == 429:
    raise Exception("Rate limited!")

# ✅ BIEN: Retry con backoff
if status == 429:
    time.sleep(10)
    retry()
```

---

## 📝 TODO: Mejoras Pendientes

- [ ] Implementar exponential backoff verdadero
- [ ] Agregar métricas de rate limiting (cuántos 429 recibimos)
- [ ] Cache de queries ya ejecutadas
- [ ] Auto-ajustar workers según rate limit observado
- [ ] Leer rate limit headers si se agregan en el futuro

---

## 🔗 Referencias

- **Semantic Scholar API Docs**: https://api.semanticscholar.org/api-docs/graph
- **GitHub Release Notes**: https://github.com/allenai/s2-folks/blob/main/API_RELEASE_NOTES.md
- **Observable Example**: https://observablehq.com/@mdeagen/throttled-semantic-scholar
- **R Package Documentation**: https://kth-library.github.io/semanticscholar/

---

**Última actualización**: 2025-10-23
**Versión de API**: v1 (Graph API)
