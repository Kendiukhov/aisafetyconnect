# Scholarly Extractor - Documentación Completa

## Resumen Ejecutivo

El extractor de scholarly es una herramienta funcional para extraer papers académicos de Google Scholar, pero con limitaciones inherentes debido a la naturaleza no oficial de la API de Google Scholar.

## Estado Actual

### **Funcionalidades Implementadas**
- Extracción básica de papers de Google Scholar
- Almacenamiento en PostgreSQL
- Modo rápido y modo completo
- Rate limiting y manejo de errores
- Exportación a CSV
- Filtros por año (2005-2026)
- Deduplicación por hash de título

### **Limitaciones Identificadas**
- **Datos truncados**: Abstracts cortados a ~200 caracteres
- **Captchas frecuentes**: Google Scholar bloquea consultas automatizadas
- **Rate limiting estricto**: Delays largos necesarios entre consultas
- **Datos inconsistentes**: Estructura variable entre papers

### **Métricas de Rendimiento**
- **Papers en base de datos**: 54 papers extraídos
- **Modo rápido**: 2-5 segundos por paper (cuando funciona)
- **Modo completo**: 10-30 segundos por paper
- **Tasa de éxito**: ~70% (limitada por captchas)

## Archivos de Documentación

### 1. `SCHOLARLY_DOCUMENTATION.md`
Documentación técnica completa:
- Funcionalidades implementadas
- Estructura de datos
- Métodos principales
- Configuración
- Limitaciones de Google Scholar

### 2. `LIMITATIONS_AND_SOLUTIONS.md`
Análisis detallado de problemas y soluciones:
- Datos truncados y soluciones
- Rate limiting y captchas
- Inconsistencias en datos
- Comparación de modos
- Recomendaciones de uso

### 3. `example_usage.py`
Ejemplos prácticos de uso:
- Extracción básica
- Configuración personalizada
- Modo rápido vs completo
- Análisis de datos
- Manejo de errores

## Uso Recomendado

### Para Extracciones Rápidas
```python
from Scholarly.scholarly_extractor import ScholarlyExtractorPostgres

extractor = ScholarlyExtractorPostgres()
extractor.run_bootstrap_extraction(
    max_queries=10,
    fast_mode=True,  # Modo rápido
    year_from=2005,
    year_to=2026
)
```

### Para Papers de Alto Impacto
```python
extractor.run_bootstrap_extraction(
    max_queries=5,
    fast_mode=False,  # Modo completo
    year_from=2005,
    year_to=2026
)
```

### Para Exportar Datos
```python
df = extractor.export_to_csv("papers_export.csv")
print(f"Exportados {len(df)} papers")
```

## Configuración de Base de Datos

### Credenciales
- **Host**: localhost
- **Puerto**: 5434
- **Base de datos**: ai_safety
- **Usuario**: scholar_user
- **Contraseña**: scholar_pass_2024

### Tablas
- `paper`: Papers extraídos
- `area`: Áreas de investigación
- `field`: Campos de investigación
- `subfield`: Subcampos de investigación

## Comandos Útiles

### Probar Conexión
```bash
cd "/Users/janeth/Extractors Notebook" && source venv/bin/activate && python3 -c "
from Scholarly.scholarly_extractor import ScholarlyExtractorPostgres
extractor = ScholarlyExtractorPostgres()
print('Conexión exitosa' if extractor.test_connection() else 'Error de conexión')
"
```

### Extracción Rápida
```bash
cd "/Users/janeth/Extractors Notebook" && source venv/bin/activate && python3 -c "
from Scholarly.scholarly_extractor import ScholarlyExtractorPostgres
extractor = ScholarlyExtractorPostgres()
extractor.run_bootstrap_extraction(max_queries=1, fast_mode=True)
"
```

### Exportar CSV
```bash
cd "/Users/janeth/Extractors Notebook" && source venv/bin/activate && python3 -c "
from Scholarly.scholarly_extractor import ScholarlyExtractorPostgres
extractor = ScholarlyExtractorPostgres()
df = extractor.export_to_csv()
print(f'Exportados {len(df)} papers')
"
```

## Limitaciones y Consideraciones

### 1. **Google Scholar no es una API oficial**
- Cambios en la estructura pueden romper la extracción
- Rate limiting agresivo y captchas
- Datos limitados en resultados básicos

### 2. **Datos Truncados**
- Abstracts cortados a ~200 caracteres
- Títulos largos pueden truncarse
- Información incompleta sin `scholarly.fill()`

### 3. **Captchas Frecuentes**
- Google Scholar detecta consultas automatizadas
- Requiere delays largos entre consultas
- Puede fallar completamente durante períodos

## Recomendaciones

### Para Uso en Producción
1. **Usar modo rápido** para extracciones masivas
2. **Implementar delays largos** (10+ segundos)
3. **Monitorear logs** para detectar captchas
4. **Tener estrategias de fallback**
5. **Considerar múltiples fuentes** de datos

### Para Investigación
1. **Usar modo completo** para papers específicos importantes
2. **Validar datos** antes de usar en análisis
3. **Combinar con otras fuentes** cuando sea posible
4. **Documentar limitaciones** en publicaciones

## Conclusión

El extractor `scholarly` es funcional pero tiene limitaciones inherentes. Es adecuado para:
- Extracciones exploratorias
- Obtención de metadatos básicos
- Identificación de papers relevantes
- Análisis de tendencias generales

No es adecuado para:
- Extracciones masivas sin supervisión
- Obtención de abstracts completos
- Uso en producción sin fallbacks
- Análisis que requiera datos completos

Para uso serio en investigación, se recomienda combinar con otras fuentes como Semantic Scholar API, ArXiv API, o CrossRef API.
