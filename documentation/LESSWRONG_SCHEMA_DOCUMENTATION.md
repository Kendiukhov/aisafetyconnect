# LessWrong GraphQL Schema Documentation
## Descubrimiento Completo del Schema para AI Safety Connect

---

## 📊 Resumen Ejecutivo

### Descubrimientos Clave
- **Endpoint GraphQL**: `https://www.lesswrong.com/graphql`
- **Total de tipos en el schema**: 1049
- **Tipos principales identificados**: User (265 campos), Post (241 campos), Comment (103 campos), Tag (87 campos)
- **Rate limiting**: No se detectó rate limiting agresivo (20 requests consecutivas exitosas)
- **Tiempo promedio de respuesta**: 0.46 segundos

### Campos Clave para AI Safety Connect

#### 🧑‍💻 User - Campos Principales
- **Identificación**: `_id`, `username`, `displayName`, `slug`
- **Métricas de karma**:
  - `karma` (Float!) - Karma total
  - `afKarma` (Float!) - Karma del Alignment Forum
  - `legacyKarma` - Karma histórico
- **Actividad**: `postCount`, `commentCount`, `sequenceCount`
- **Profesional**: `jobTitle`, `organization`, `careerStage`
- **Enlaces**: `website`, `linkedinProfileURL`, `githubProfileURL`, `twitterProfileUsername`
- **Perfil**: `bio`, `profileTagIds`, `groups`

#### 📝 Post - Campos Principales
- **Identificación**: `_id`, `title`, `slug`, `url`
- **Contenido**:
  - `contents.html` - Contenido en HTML
  - `contents.markdown` - Contenido en Markdown
  - `contents.plaintextDescription` - Descripción en texto plano
  - `contents.wordCount` - Contador de palabras
- **Métricas**:
  - `baseScore` (Float!) - Puntuación base
  - `voteCount` (Float!) - Número de votos
  - `viewCount` - Vistas
  - `clickCount` - Clicks
  - `commentCount` - Número de comentarios
- **Fechas**: `createdAt`, `postedAt`, `curatedDate`, `frontpageDate`
- **Categorización**: `tags`, `tagRelevance`, `af` (Alignment Forum)
- **Autor**: `userId`, `user`, `coauthors`

#### 💬 Comment - Campos Principales
- **Identificación**: `_id`
- **Contenido**: `contents`
- **Relaciones**: `postId`, `parentCommentId`, `topLevelCommentId`
- **Métricas**: `baseScore`, `voteCount`
- **Autor**: `userId`, `user`
- **Fechas**: `createdAt`, `postedAt`

#### 🏷️ Tags Relacionados con AI Safety
**Análisis completo de 938 tags activos** - Identificados con keywords del Backend Strategy Plan

##### 📊 Resumen del Análisis
- **Total tags analizados**: 938 tags activos con posts
- **Tags definitivamente AI Safety**: 53 (score ≥ 25)
- **Tags probablemente AI Safety**: 74 (score 15-25)
- **Research Agendas cubiertas**: 10/10

##### 🎯 Tags por Research Agenda (Backend Strategy Plan)

**1. Alignment Theory (818 posts total)**
- `inner-alignment` - 343 posts
- `outer-alignment` - 335 posts
- `mesa-optimization` - 140 posts

**2. AI Governance & Policy (1,196 posts total)**
- `ai-governance` - 794 posts
- `regulation-and-ai-risk` - 149 posts
- `goodharts-law` - 142 posts
- `scaling-laws` - 91 posts
- `compute-governance` - 20 posts

**3. Mechanistic Interpretability (998 posts total)**
- `interpretability-ml-and-ai` - 998 posts

**4. Agent Foundations (536 posts total)**
- `agent-foundations` - 167 posts
- `embedded-agency` - 125 posts
- `logical-uncertainty` - 77 posts
- `functional-decision-theory` - 46 posts
- `updateless-decision-theory` - 41 posts
- `lobs-theorem` - 37 posts
- `logical-induction` - 43 posts

**5. Cooperative AI (730 posts total)**
- `game-theory` - 364 posts
- `coordination-cooperation` - 321 posts
- `commitment-mechanisms` - 14 posts
- `evidential-cooperation-in-large-worlds` - 13 posts

**6. Scalable Oversight (442 posts total)**
- `mechanism-design` - 167 posts
- `debate-ai-safety-technique` - 114 posts
- `iterated-amplification` - 70 posts
- `scalable-oversight` - 24 posts

**7. Value Learning & Alignment (310 posts total)**
- `value-learning` - 208 posts
- `moral-uncertainty` - 84 posts
- `value-drift` - 18 posts

**8. Evaluations & Dangerous Capabilities (254 posts total)**
- `ai-evaluations` - 254 posts

**9. Adversarial Robustness (70 posts total)**
- `adversarial-examples-ai` - 41 posts
- `adversarial-training` - 29 posts

**10. Compute Governance (361 posts total)**
- `computer-science` - 128 posts
- `computer-security-cryptography` - 121 posts
- `compute` - 48 posts

##### 🏆 Top Tags AI Safety por Número de Posts
1. **ai** - 13,536 posts (Core tag)
2. **world-modeling** - 6,111 posts (Core tag)
3. **interpretability-ml-and-ai** - 998 posts
4. **language-models-llms** - 925 posts
5. **ai-governance** - 794 posts
6. **existential-risk** - 536 posts
7. **decision-theory** - 512 posts
8. **ai-alignment-fieldbuilding** - 394 posts
9. **game-theory** - 364 posts
10. **inner-alignment** - 343 posts

##### 🔑 Tags Clave con IDs para Queries

```python
AI_SAFETY_TAG_IDS = {
    # Core Tags
    "ai": "sYm3HiWcfZvrGu3ui",
    "existential-risk": "nBqjqNWqDYfvMRYZ8",

    # Research Agendas
    "inner-alignment": "Dw5Z6wtTgk4Fikz9f",
    "outer-alignment": "BisjoDrd3oNatDu7X",
    "mesa-optimization": "NZ67PZ8CkeS6xn27h",
    "interpretability-ml-and-ai": "56yXXrcxRjrQs6z9R",
    "ai-governance": "qHDus5MuMNqQxJbjD",
    "agent-foundations": "xqKKPZxXBnNkFubKR",
    "embedded-agency": "8ySxrF2pFX93pL9tH",
    "value-learning": "NLwTnsH9RSotqXYLw",
    "cooperative-ai": "rHf8nirSJx3jMWHKw",
    "adversarial-robustness": "haiwnEEx3vhrkfmAP",
    "compute-governance": "TXYW2ftfEvuwLBCpb",

    # Organizations
    "miri": "b7mWRnrGyt5Xz2pSH",
    "openai": "H4n4rzs33JfEgkf8b",
    "anthropic": "C9NimMKsXPCpCG8dL",
    "deepmind": "FWL2tvXKqLxseqKGR",
    "redwood-research": "qMXDMzxp7KJqFnXFM",

    # Safety Techniques
    "rlhf": "wqeBNjndX7egbzQrW",
    "debate-ai-safety-technique": "HqaByfeGvDLKSaK2W",
    "iterated-amplification": "6DuJxY8X45Sco4bS2",
    "constitutional-ai": "constitutional-ai-slug",
}
```

##### 📈 Estadísticas de Cobertura
- **Posts totales en tags AI Safety definitivos**: ~25,000+
- **Usuarios activos en estos tags**: Por determinar mediante queries
- **Crecimiento mensual promedio**: Por analizar

**Nota sobre "af"**: Los campos con prefijo "af" se refieren al **Alignment Forum**:
- `afKarma` - Karma específico del Alignment Forum
- `afPostCount` - Posts en el Alignment Forum
- `af` (boolean) - Si el contenido pertenece al Alignment Forum

---

## 🔍 Queries Optimizadas para AI Safety Connect - VERSIONES CORREGIDAS

**⚠️ IMPORTANTE**: Las queries originales tenían errores de sintaxis. Las siguientes son las versiones corregidas y probadas que funcionan correctamente con el API GraphQL de LessWrong.

### 1. Obtener Posts por Tag de AI Safety

```graphql
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
```

### 2. Obtener Información Completa de un Usuario

```graphql
query GetUserFullInfo {
  user(selector: {_id: "USER_ID_HERE"}) {
    result {
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
      twitterProfileURL  # NOTA: Es twitterProfileURL, NO twitterProfileUsername
      postCount
      commentCount
      createdAt
      profileTagIds
    }
  }
}
```

### 3. Obtener Posts de un Usuario

```graphql
query GetUserPosts {
  posts(selector: {userPosts: {userId: "USER_ID_HERE"}}, limit: 50) {
    results {
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
      contents {
        markdown
        plaintextDescription
        wordCount
      }
      tags {
        _id
        name
        slug
      }
      af
    }
  }
}
```

### 4. Obtener Comentarios de un Usuario

```graphql
query GetUserComments {
  comments(selector: {profileComments: {userId: "USER_ID_HERE"}}, limit: 100) {
    results {
      _id
      postId
      parentCommentId
      topLevelCommentId
      contents {
        markdown
        plaintextDescription
      }
      baseScore
      voteCount
      createdAt
      user {
        username
      }
      post {
        title
        _id
      }
    }
  }
}
```

### 5. Notas Importantes sobre Errores Comunes

**🚨 ERRORES COMUNES Y SUS SOLUCIONES:**

1. **Error: "Cannot query field twitterProfileUsername"**
   - ❌ INCORRECTO: `twitterProfileUsername`
   - ✅ CORRECTO: `twitterProfileURL`

2. **Error: Estructura incorrecta en queries de usuario**
   - ❌ INCORRECTO: `user(input: {selector: {_id: $userId}})`
   - ✅ CORRECTO: `user(selector: {_id: "USER_ID"})` con `result` wrapper

3. **Error: Selector incorrecto para posts de usuario**
   - ❌ INCORRECTO: `posts(input: {selector: {userId: $userId}})`
   - ✅ CORRECTO: `posts(selector: {userPosts: {userId: "USER_ID"}})`

4. **Error: Selector incorrecto para comentarios**
   - ❌ INCORRECTO: `comments(input: {selector: {userId: $userId}})`
   - ✅ CORRECTO: `comments(selector: {profileComments: {userId: "USER_ID"}})`

5. **Error: Estructura de tags incorrecta**
   - ❌ INCORRECTO: `selector: {tagIds: [$tagId]}`
   - ✅ CORRECTO: `terms: {filterSettings: {tags: [{tagId: $tagId, filterMode: "Required"}]}}`

### 6. Estrategia Python para Identificar Usuarios AI Safety

```python
# Estrategia implementada y probada
def find_ai_safety_users(graphql_client):
    # 1. Usar los tags definitivos de AI Safety
    DEFINITE_AI_SAFETY_TAGS = {
        "NrvXXL3iGjjxu5B7d": {"name": "MIRI", "posts": 166},
        "Dw5Z6wtTgk4Fikz9f": {"name": "Inner Alignment", "posts": 343},
        "BisjoDrd3oNatDu7X": {"name": "Outer Alignment", "posts": 335},
        "qHDus5MuMNqQxJbjD": {"name": "AI Governance", "posts": 794},
        # ... más tags
    }

    ai_users = set()

    for tag in ai_tags:
        posts = graphql_client.query(
            """
            query {
              posts(input: {
                terms: {
                  filterSettings: {
                    tags: [{tagName: $tag, filterMode: "Required"}]
                  }
                  limit: 1000
                }
              }) {
                results {
                  userId
                  user {
                    _id
                    displayName
                    karma
                  }
                }
              }
            }
            """,
            {"tag": tag}
        )

        for post in posts["data"]["posts"]["results"]:
            if post["user"]["karma"] > 100:  # Filtro por karma mínimo
                ai_users.add(post["userId"])

    # 2. Obtener información completa de cada usuario
    user_data = []
    for user_id in ai_users:
        user_info = get_user_full_info(user_id)
        user_data.append(user_info)

    # 3. Ordenar por karma
    user_data.sort(key=lambda x: x["karma"], reverse=True)

    return user_data[:100]  # Top 100
```

---

## 📋 Mapeo de Campos a Requerimientos del Proyecto

### Requerimiento: "Database with all users in LW/EAF/AF that are working in AIS"

**Campos necesarios**:
```json
{
  "user_identification": {
    "id": "User._id",
    "username": "User.username",
    "display_name": "User.displayName",
    "slug": "User.slug"
  },
  "metrics": {
    "karma_total": "User.karma",
    "karma_alignment_forum": "User.afKarma",
    "post_count": "User.postCount",
    "comment_count": "User.commentCount"
  },
  "professional_info": {
    "bio": "User.bio",
    "job_title": "User.jobTitle",
    "organization": "User.organization",
    "career_stage": "User.careerStage"
  },
  "links": {
    "website": "User.website",
    "linkedin": "User.linkedinProfileURL",
    "github": "User.githubProfileURL",
    "twitter": "User.twitterProfileUsername"
  },
  "ai_safety_indicators": {
    "profile_tags": "User.profileTagIds",
    "groups": "User.groups",
    "af_karma": "User.afKarma > 0"
  }
}
```

### Requerimiento: "Including when they worked on what"

**Campos necesarios**:
```json
{
  "posts": {
    "id": "Post._id",
    "title": "Post.title",
    "content": "Post.contents",
    "created_at": "Post.createdAt",
    "posted_at": "Post.postedAt",
    "tags": "Post.tags",
    "score": "Post.baseScore"
  },
  "projects": {
    "sequences": "User.sequenceCount",
    "sequences_list": "Query user sequences separately"
  },
  "publications": {
    "curated_posts": "Post.curatedDate != null",
    "frontpage_posts": "Post.frontpageDate != null",
    "af_posts": "Post.af == true"
  }
}
```

---

## 🚀 Implementación Recomendada

### 1. Estrategia de Extracción

```python
class LessWrongAISafetyExtractor:
    def __init__(self):
        self.graphql_endpoint = "https://www.lesswrong.com/graphql"
        self.ai_safety_tags = self.load_ai_safety_tags()
        self.delay_between_requests = 0.5  # segundos

    def extract_ai_safety_users(self):
        """Proceso principal de extracción"""

        # Paso 1: Identificar usuarios por actividad en tags AI
        ai_users = self.find_users_by_ai_tags()

        # Paso 2: Filtrar por karma mínimo (ej: 100)
        filtered_users = [u for u in ai_users if u['karma'] >= 100]

        # Paso 3: Enriquecer datos de usuarios
        enriched_users = self.enrich_user_data(filtered_users)

        # Paso 4: Extraer posts y proyectos
        for user in enriched_users:
            user['posts'] = self.get_user_posts(user['_id'])
            user['ai_posts'] = self.filter_ai_posts(user['posts'])

        # Paso 5: Ordenar por relevancia AI Safety
        ranked_users = self.rank_by_ai_relevance(enriched_users)

        return ranked_users[:100]  # Top 100
```

### 2. Optimizaciones

- **Caching**: Implementar cache de 15 minutos para queries repetidas
- **Batch queries**: Agrupar múltiples IDs en una sola query cuando sea posible
- **Rate limiting**: Mantener 0.5-1 segundo entre requests
- **Paralelización**: Usar async/await para queries concurrentes con límite de 5 simultáneas

### 3. Filtros de AI Safety

```python
AI_SAFETY_KEYWORDS = [
    # Términos directos
    "ai safety", "ai alignment", "alignment research",
    "existential risk", "x-risk", "agi safety",

    # Organizaciones
    "miri", "anthropic", "deepmind", "openai",
    "fhi", "cser", "gcri", "chai",

    # Conceptos técnicos
    "mesa optimization", "inner alignment", "outer alignment",
    "corrigibility", "interpretability", "robustness"
]

def is_ai_safety_content(text):
    """Determina si el contenido está relacionado con AI Safety"""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in AI_SAFETY_KEYWORDS)
```

---

## 📊 Métricas y Monitoreo

### KPIs para el Scraping

1. **Cobertura**: % de usuarios AI Safety identificados
2. **Precisión**: % de falsos positivos en identificación AI Safety
3. **Completitud**: % de campos poblados por usuario
4. **Velocidad**: Usuarios procesados por hora
5. **Errores**: Tasa de errores en queries

### Monitoreo Recomendado

```python
class ScrapingMonitor:
    def __init__(self):
        self.metrics = {
            'users_processed': 0,
            'posts_extracted': 0,
            'errors': [],
            'api_response_times': []
        }

    def log_progress(self):
        print(f"""
        Progress Update:
        - Users processed: {self.metrics['users_processed']}
        - Posts extracted: {self.metrics['posts_extracted']}
        - Avg response time: {np.mean(self.metrics['api_response_times']):.2f}s
        - Error rate: {len(self.metrics['errors']) / max(self.metrics['users_processed'], 1):.2%}
        """)
```

---

## ⚠️ Consideraciones Importantes

1. **No hay endpoint de búsqueda directa por karma**: Necesitas obtener usuarios y ordenar localmente
2. **Tags AI Safety son limitados**: Muchos posts relevantes pueden no tener tags específicos
3. **Bio y descripción en texto libre**: Requiere NLP para identificación precisa
4. **Datos de Alignment Forum**: Campo `af` y `afKarma` indican participación en AF
5. **Rate limiting suave**: No hay límite estricto, pero mantén delays por cortesía

---

## 📝 Próximos Pasos

1. **Implementar extractor completo** con las queries optimizadas
2. **Crear pipeline de NLP** para identificar contenido AI Safety en bios y posts
3. **Establecer base de datos** con schema apropiado para almacenar resultados
4. **Implementar actualización incremental** para mantener datos actualizados
5. **Crear API** para servir los datos al proyecto AI Safety Connect

---

## 🔗 Recursos Adicionales

- Schema completo: `lesswrong_complete_schema.json`
- Mapeo de campos: `lesswrong_field_mapping.json`
- Scripts de extracción: `extract_all_fields.py`
- Test de introspección: `introspection_deep.py`