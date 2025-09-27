# Plan de Implementación ACTUALIZADO: AI Safety Connect - LessWrong Extractor MVP
**Versión 2.0 - Corregido con implementación real funcional**

## 📋 Contexto del Proyecto

### Objetivo
Extraer y mapear investigadores trabajando en AI Safety desde LessWrong para el proyecto AI Safety Connect, facilitando conexiones entre academia y la comunidad EA/LessWrong.

### Fase Actual
**MVP - Week 3 (Oct 15-21)** según cronograma del proyecto

### Estrategia MVP Implementada
- Usar **5 tags definitivos de AI Safety** para test inicial
- Buscar posts con estos tags para identificar usuarios activos
- Ordenar usuarios por karma total
- Extraer TODOS los posts y comentarios de los top usuarios
- Enriquecer posts con información de AI Safety tags y research agendas

## 🏗️ Arquitectura de Clases Implementada

### 1. Clase Base Abstracta: `base_extractor.py`

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import json
import logging
from datetime import datetime
from pathlib import Path

class BasePlatformExtractor(ABC):
    """
    Clase abstracta base para extractores de plataformas.
    Define la interfaz común para LessWrong, EA Forum, y futuras plataformas.
    """

    def __init__(self, base_output_dir: str = "raw-data"):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.base_output_dir = Path(base_output_dir)
        self.platform_name = self.get_platform_name()
        self.extraction_date = datetime.now().strftime("%Y-%m-%d")
        self.setup_directories()
        self.logger.info(f"Inicializado extractor para {self.platform_name}")

    @abstractmethod
    def get_platform_name(self) -> str:
        """Retorna el nombre de la plataforma"""
        pass

    @abstractmethod
    def extract_top_users(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Extrae los top N usuarios según criterios de AI Safety"""
        pass

    @abstractmethod
    def extract_user_posts(self, user_id: str) -> List[Dict[str, Any]]:
        """Extrae todos los posts históricos de un usuario"""
        pass

    @abstractmethod
    def extract_user_comments(self, user_id: str) -> List[Dict[str, Any]]:
        """Extrae todos los comentarios de un usuario"""
        pass

    def setup_directories(self):
        """Crea la estructura de carpetas necesaria"""
        self.output_dir = self.base_output_dir / self.platform_name / self.extraction_date
        self.posts_dir = self.output_dir / "posts"
        self.comments_dir = self.output_dir / "comments"

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.posts_dir.mkdir(exist_ok=True)
        self.comments_dir.mkdir(exist_ok=True)

    def save_to_json(self, data: Any, filepath: Path):
        """Guarda datos en formato JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def extract_and_save_all(self, limit: int = 100):
        """Pipeline completo de extracción"""
        # 1. Extraer top usuarios
        users = self.extract_top_users(limit)
        self.save_to_json(users, self.output_dir / f"users_top{limit}.json")

        # 2. Para cada usuario, extraer posts y comentarios
        for i, user in enumerate(users, 1):
            user_id = user['userId']
            username = user.get('username', user_id)

            self.logger.info(f"Procesando usuario {i}/{len(users)}: {username}")

            # Extraer posts y comentarios
            posts = self.extract_user_posts(user_id)
            comments = self.extract_user_comments(user_id)

            # Guardar
            self.save_to_json(posts, self.posts_dir / f"user_{user_id}_posts.json")
            self.save_to_json(comments, self.comments_dir / f"user_{user_id}_comments.json")

            # Actualizar conteos
            user['post_count'] = len(posts)
            user['comment_count'] = len(comments)
```

### 2. Implementación LessWrong: `lesswrong_extractor.py`

```python
import time
import requests
from typing import List, Dict, Any, Optional
from base_extractor import BasePlatformExtractor

class LessWrongExtractor(BasePlatformExtractor):
    """
    Extractor específico para LessWrong usando GraphQL API.
    """

    def __init__(self, base_output_dir: str = "raw-data"):
        super().__init__(base_output_dir)
        self.graphql_endpoint = "https://www.lesswrong.com/graphql"
        self.rate_limit_delay = 0.5  # segundos entre requests
        self.max_retries = 3
        self.post_source_tags = {}  # Para rastrear origen de posts
        self.setup_ai_safety_tags()

    def get_platform_name(self) -> str:
        return "lesswrong"

    def setup_ai_safety_tags(self):
        """Define los tags definitivos de AI Safety"""
        # Para test inicial, usar solo 5 tags principales
        self.DEFINITE_AI_SAFETY_TAGS = {
            "NrvXXL3iGjjxu5B7d": {"name": "MIRI", "posts": 166},
            "Dw5Z6wtTgk4Fikz9f": {"name": "Inner Alignment", "posts": 343},
            "BisjoDrd3oNatDu7X": {"name": "Outer Alignment", "posts": 335},
            "qHDus5MuMNqQxJbjD": {"name": "AI Governance", "posts": 794},
            "56yXXrcxRjrQs6z9R": {"name": "Interpretability (ML & AI)", "posts": 998}
        }

        # Tags adicionales para producción (todos los 53 tags)
        self.ALL_AI_SAFETY_TAGS = {
            # ... agregar resto de tags aquí
        }

    def make_graphql_request(self, query: str, variables: Dict = None) -> Optional[Dict]:
        """Realiza una request GraphQL con rate limiting y reintentos"""
        time.sleep(self.rate_limit_delay)

        for attempt in range(self.max_retries):
            try:
                payload = {'query': query, 'variables': variables or {}}
                response = requests.post(
                    self.graphql_endpoint,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
        return None

    def extract_top_users(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Extrae top usuarios basándose en posts con tags AI Safety.
        """
        all_users = {}
        self.post_source_tags.clear()

        # 1. Para cada tag definitivo, obtener usuarios
        for tag_id, tag_info in self.DEFINITE_AI_SAFETY_TAGS.items():
            # QUERY CORREGIDA
            query = """
            query GetPostsByTag($tagId: String!, $limit: Int!) {
                posts(input: {
                    terms: {
                        filterSettings: {
                            tags: [{tagId: $tagId, filterMode: "Required"}]
                        }
                        limit: $limit
                    }
                }) {
                    results {
                        _id
                        userId
                        user {
                            _id
                            username
                            displayName
                            karma
                            afKarma
                        }
                    }
                }
            }
            """

            result = self.make_graphql_request(query, {'tagId': tag_id, 'limit': 50})

            if result and 'data' in result:
                posts = result.get('data', {}).get('posts', {}).get('results', [])

                for post in posts:
                    if post.get('_id'):
                        # Rastrear origen del post
                        self.post_source_tags[post['_id']] = {
                            'tag_id': tag_id,
                            'tag_name': tag_info['name'],
                            'research_agenda': self.map_tag_to_research_agenda(tag_info['name'])
                        }

                    if post.get('user'):
                        user_id = post['userId']
                        if user_id not in all_users:
                            all_users[user_id] = {
                                'userId': user_id,
                                'username': post['user'].get('username'),
                                'displayName': post['user'].get('displayName'),
                                'karma': post['user'].get('karma', 0),
                                'afKarma': post['user'].get('afKarma', 0),
                                'ai_safety_tags': [],
                                'post_count_in_ai_safety': 0
                            }

                        all_users[user_id]['ai_safety_tags'].append(tag_info['name'])
                        all_users[user_id]['post_count_in_ai_safety'] += 1

        # 2. Enriquecer información de usuarios
        sorted_users = sorted(all_users.values(), key=lambda x: x.get('karma', 0), reverse=True)
        users_to_enrich = sorted_users[:min(limit, len(sorted_users))]

        for user_data in users_to_enrich:
            user_id = user_data['userId']
            user_full = self.get_user_full_info(user_id)
            if user_full:
                user_data.update(user_full)

        return users_to_enrich[:limit]

    def get_user_full_info(self, user_id: str) -> Optional[Dict]:
        """Obtiene información completa de un usuario"""
        # QUERY CORREGIDA - Sin wrapper input, con result
        query = f"""
        query GetUserFullInfo {{
            user(selector: {{_id: "{user_id}"}}) {{
                result {{
                    _id
                    username
                    displayName
                    slug
                    karma
                    afKarma
                    bio
                    jobTitle
                    organization
                    careerStage
                    website
                    linkedinProfileURL
                    githubProfileURL
                    twitterProfileURL  # CORRECTO: NO es twitterProfileUsername
                    postCount
                    commentCount
                    createdAt
                    profileTagIds
                }}
            }}
        }}
        """

        result = self.make_graphql_request(query, {})
        if result and 'data' in result and result['data']['user']:
            return result['data']['user']['result']
        return None

    def extract_user_posts(self, user_id: str) -> List[Dict[str, Any]]:
        """Extrae todos los posts de un usuario"""
        # QUERY CORREGIDA - userPosts selector
        query = f"""
        query GetUserPosts {{
            posts(selector: {{userPosts: {{userId: "{user_id}"}}}}, limit: 50) {{
                results {{
                    _id
                    title
                    slug
                    url
                    baseScore
                    voteCount
                    viewCount
                    commentCount
                    createdAt
                    postedAt
                    contents {{
                        markdown
                        plaintextDescription
                        wordCount
                    }}
                    tags {{
                        _id
                        name
                        slug
                    }}
                    af
                }}
            }}
        }}
        """

        result = self.make_graphql_request(query, {})
        if result and result.get('data', {}).get('posts', {}).get('results'):
            posts = result['data']['posts']['results']

            # Enriquecer cada post con información de AI Safety
            for post in posts:
                self.enrich_post_with_ai_safety_tags(post)

            return posts
        return []

    def extract_user_comments(self, user_id: str) -> List[Dict[str, Any]]:
        """Extrae todos los comentarios de un usuario"""
        # QUERY CORREGIDA - profileComments selector
        query = f"""
        query GetUserComments {{
            comments(selector: {{profileComments: {{userId: "{user_id}"}}}}, limit: 100) {{
                results {{
                    _id
                    postId
                    parentCommentId
                    topLevelCommentId
                    contents {{
                        markdown
                        plaintextDescription
                    }}
                    baseScore
                    voteCount
                    createdAt
                    user {{
                        username
                    }}
                    post {{
                        title
                        _id
                    }}
                }}
            }}
        }}
        """

        result = self.make_graphql_request(query, {})
        if result and result.get('data', {}).get('comments', {}).get('results'):
            return result['data']['comments']['results']
        return []

    def enrich_post_with_ai_safety_tags(self, post: Dict[str, Any]):
        """Agrega información sobre AI Safety tags y research agendas al post"""
        post_id = post.get('_id')

        # Inicializar campos
        post['ai_safety_tags'] = []
        post['research_agendas'] = []
        post['extraction_source'] = None

        # Combinar todos los tags de AI Safety
        all_ai_safety_tags = {**self.DEFINITE_AI_SAFETY_TAGS, **self.ALL_AI_SAFETY_TAGS}

        # Revisar los tags del post
        if post.get('tags'):
            for tag in post.get('tags', []):
                tag_id = tag.get('_id')
                if tag_id in all_ai_safety_tags:
                    tag_info = all_ai_safety_tags[tag_id]

                    # Agregar a ai_safety_tags
                    post['ai_safety_tags'].append({
                        'id': tag_id,
                        'name': tag_info['name'],
                        'source': 'post_tag'
                    })

                    # Mapear a research agenda
                    agenda = self.map_tag_to_research_agenda(tag_info['name'])
                    if agenda and agenda not in post['research_agendas']:
                        post['research_agendas'].append(agenda)

                    # Establecer extraction_source
                    if not post['extraction_source']:
                        post['extraction_source'] = {
                            'tag_id': tag_id,
                            'tag_name': tag_info['name'],
                            'research_agenda': agenda
                        }

        # Si tenemos información de post_source_tags, usarla
        if hasattr(self, 'post_source_tags') and post_id in self.post_source_tags:
            source_info = self.post_source_tags[post_id]
            post['extraction_source'] = {
                'tag_id': source_info['tag_id'],
                'tag_name': source_info['tag_name'],
                'research_agenda': source_info['research_agenda']
            }

    def map_tag_to_research_agenda(self, tag_name: str) -> str:
        """Mapea un tag a su research agenda correspondiente"""
        mapping = {
            'miri': 'Agent Foundations',
            'inner alignment': 'Alignment Theory',
            'outer alignment': 'Alignment Theory',
            'mesa-optimization': 'Alignment Theory',
            'ai governance': 'AI Governance & Policy',
            'interpretability': 'Mechanistic Interpretability',
            # ... más mapeos
        }

        tag_lower = tag_name.lower()
        for key, agenda in mapping.items():
            if key in tag_lower:
                return agenda
        return None
```

### 3. Script Principal: `main.py`

```python
import logging
import sys
from lesswrong_extractor import LessWrongExtractor

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG para más información
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extraction.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Script principal de extracción"""
    try:
        # Crear extractor
        extractor = LessWrongExtractor()

        # Test con 3 usuarios primero
        logger.info("=== TEST: Extrayendo 3 usuarios ===")
        extractor.extract_and_save_all(limit=3)

        # Si funciona, descomentar para ejecutar completo
        # logger.info("=== COMPLETO: Extrayendo 100 usuarios ===")
        # extractor.extract_and_save_all(limit=100)

    except Exception as e:
        logger.error(f"Error en ejecución principal: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## 📝 Dependencias: `pyproject.toml`

```toml
[project]
name = "aisafetyconnect"
version = "0.1.0"
description = "AI Safety Connect data extraction tools"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "requests>=2.32.3",
]
```

## 🚨 Errores Comunes y Soluciones

### 1. GraphQL Query Errors

**Error**: `Cannot query field twitterProfileUsername`
- **Causa**: El campo correcto es `twitterProfileURL`
- **Solución**: Usar `twitterProfileURL` en la query

**Error**: `400 Bad Request` en queries de usuario
- **Causa**: Estructura incorrecta de la query
- **Solución**: No usar wrapper `input`, usar `result` para acceder a datos

**Error**: `Cannot query field on type Query`
- **Causa**: Selector incorrecto para posts/comentarios
- **Solución**:
  - Posts: `selector: {userPosts: {userId: "..."}}`
  - Comentarios: `selector: {profileComments: {userId: "..."}}`

### 2. Tags Structure Errors

**Error**: Posts sin tags de AI Safety
- **Causa**: No todos los posts tienen tags de AI Safety
- **Comportamiento esperado**: Solo posts con tags relevantes se enriquecen

## 🗂️ Estructura de Salida

```
raw-data/
└── lesswrong/
    └── 2025-09-27/
        ├── users_top3.json         # Top 3 usuarios
        ├── posts/
        │   ├── user_XXX_posts.json # Posts de cada usuario
        │   └── ...
        ├── comments/
        │   ├── user_XXX_comments.json # Comentarios
        │   └── ...
        └── extraction_summary.json # Resumen final
```

## 🔄 Estrategia de Extracción

1. **Buscar por Tags**: Encontrar posts con tags de AI Safety
2. **Identificar Autores**: Extraer usuarios que escribieron esos posts
3. **Rankear por Karma**: Ordenar usuarios por karma total
4. **Extraer Todo**: Descargar TODOS los posts/comentarios de top usuarios
5. **Enriquecer**: Agregar metadata de AI Safety a posts relevantes

## 📊 Datos Extraídos por Usuario

- **Información básica**: username, karma, afKarma, bio
- **Profesional**: jobTitle, organization, careerStage
- **Enlaces**: website, LinkedIn, GitHub, Twitter
- **Métricas**: postCount, commentCount
- **AI Safety**: tags trabajados, research agendas
- **Contenido completo**: Todos sus posts y comentarios

## 🚀 Ejecución

```bash
# Instalar dependencias con uv
uv pip install -e .

# Ejecutar extracción de prueba (3 usuarios)
uv run python main.py

# Para extracción completa, modificar main.py y usar limit=100
```

## ✅ Validación

- Verificar que `raw-data/lesswrong/YYYY-MM-DD/` se crea
- Confirmar archivos JSON con datos de usuarios
- Revisar que posts con tags AI Safety tienen campos enriquecidos
- Comprobar logs en `extraction.log` para errores

## 🔮 Próximos Pasos

1. Expandir a los 53 tags definitivos
2. Implementar extractor para EA Forum (misma estructura)
3. Agregar procesamiento de research agendas
4. Implementar deduplicación cross-platform
5. Crear pipeline de actualización incremental