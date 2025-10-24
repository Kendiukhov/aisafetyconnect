import time
import requests
import logging
from typing import List, Dict, Any, Optional
from base_extractor import BasePlatformExtractor

logger = logging.getLogger(__name__)

class LessWrongExtractor(BasePlatformExtractor):
    """
    Extractor específico para LessWrong usando GraphQL API.
    MVP: Extrae usuarios basándose en 53 tags definitivos de AI Safety.
    """

    def __init__(self, base_output_dir: str = "raw-data"):
        super().__init__(base_output_dir)
        self.graphql_endpoint = "https://www.lesswrong.com/graphql"
        self.rate_limit_delay = 0.5  # segundos entre requests
        self.max_retries = 3
        self.post_source_tags = {}  # Inicializar para persistir entre llamadas
        self.setup_ai_safety_tags()

    def get_platform_name(self) -> str:
        return "lesswrong"

    def setup_ai_safety_tags(self):
        """Define los tags definitivos de AI Safety - 10 tags más relevantes"""
        # Top 10 tags de AI Safety por relevancia y número de posts
        self.DEFINITE_AI_SAFETY_TAGS = {
            # Core alignment tags
            "NrvXXL3iGjjxu5B7d": {"name": "MIRI", "posts": 166},
            "Dw5Z6wtTgk4Fikz9f": {"name": "Inner Alignment", "posts": 343},
            "BisjoDrd3oNatDu7X": {"name": "Outer Alignment", "posts": 335},
            "qHDus5MuMNqQxJbjD": {"name": "AI Governance", "posts": 794},
            "E9FmKBJvWBJd8FJuf": {"name": "Interpretability (ML & AI)", "posts": 351},

            # Additional important tags
            "NZ67PZ8CkeS6xn27h": {"name": "Mesa-Optimization", "posts": 140},
            "mZTuBntSdPeyLSrec": {"name": "Chain-of-Thought Alignment", "posts": 112},
            "qnYusX26j7YLYxHxR": {"name": "Agent Foundations", "posts": 167},
            "2KA9EDpAkGhNxrbLm": {"name": "AI Alignment (general)", "posts": 394},
            "nBqjqNWqDYfvMRYZ8": {"name": "Existential Risk", "posts": 536}
        }

        # Lista completa para cuando funcione el test
        self.ALL_AI_SAFETY_TAGS = {
            "mZTuBntSdPeyLSrec": {"name": "Chain-of-Thought Alignment", "posts": 112},
            "dHfxtPwAmrij4KEce": {"name": "Redwood Research", "posts": 54},
            "HrCcwuykKcn2SJgge": {"name": "Alignment Research Center", "posts": 34},
            "NrvXXL3iGjjxu5B7d": {"name": "MIRI", "posts": 166},
            "Dw5Z6wtTgk4Fikz9f": {"name": "Inner Alignment", "posts": 343},
            "BisjoDrd3oNatDu7X": {"name": "Outer Alignment", "posts": 335},
            "NZ67PZ8CkeS6xn27h": {"name": "Mesa-Optimization", "posts": 140},
            "qHDus5MuMNqQxJbjD": {"name": "AI Governance", "posts": 794},
            "5syXuDYRqWiXS5LSj": {"name": "Research Agendas", "posts": 133},
            "GvAa8JPCrFa25fcKN": {"name": "Optimizer's Curse", "posts": 32},
            "iCL9KruWg3gtJiHhM": {"name": "Critiques (AI Safety)", "posts": 173},
            "JJFphYfMsdFMuprBy": {"name": "Orthogonality", "posts": 153},
            "E9FmKBJvWBJd8FJuf": {"name": "Interpretability (ML & AI)", "posts": 351},
            "Gg3cv3otBRgzZiurT": {"name": "Embedded Agency", "posts": 137},
            "Nwgdq6kHke5LY692J": {"name": "Alignment Forum", "posts": 124},
            "wt6Kux4CTh9tpmk9X": {"name": "AI Risk", "posts": 124},
            "JDBKrvGH5s9r37MGZ": {"name": "Regulation and AI Risk", "posts": 121},
            "J3gFP8SN4pzdtn3mz": {"name": "AI Timelines", "posts": 284},
            "tbRbyWoKRpFhqRhXs": {"name": "Corrigibility", "posts": 109},
            "JqJZsxTLzxqH7KqgF": {"name": "Logical Decision Theory", "posts": 73},
            "hvGoYXi2kgnS3vxqb": {"name": "Selection Theorems", "posts": 64},
            "fZZxKRgtLwXYgaxMT": {"name": "Shard Theory", "posts": 78},
            "n7o5m4tftWpJvv3XB": {"name": "Timeless Decision Theory", "posts": 115},
            "4hLcbXaqudM9wSeor": {"name": "Risks from Learned Optimization (Sequence)", "posts": 35},
            "bBdfbWfWxHN9Chjcq": {"name": "Value Learning", "posts": 108},
            "GcJXbP5wBEaycxWoR": {"name": "AI", "posts": 2565},
            "cHLfxLCFq59dGLsNC": {"name": "Distillation & Pedagogy", "posts": 260},
            "qajKCSTmhguqSPgYW": {"name": "Myopia", "posts": 39},
            "BQJKuMahhgS4CEqYC": {"name": "Tool AI", "posts": 55},
            "6u9mYKSkHbSwPPJhs": {"name": "Treacherous Turn", "posts": 51},
            "8N4xbWdJYy5r39t4M": {"name": "Stuart Armstrong", "posts": 126},
            "nM3Sya3vNe7jg7nvK": {"name": "Updateless Decision Theory", "posts": 31},
            "k2HnvHHeQaX9nZnF3": {"name": "Approval-Directed Agents", "posts": 26},
            "2TfqgBkLBxqKHGAWz": {"name": "Functional Decision Theory", "posts": 63},
            "Kkv7myPBmcepqmhxz": {"name": "Effective Accelerationism", "posts": 30},
            "EfqSjCE7aRnhKPDqj": {"name": "AI Capabilities", "posts": 136},
            "FN9pAmjT3LJvEPtsY": {"name": "RLHF", "posts": 84},
            "YWftoGHBuSJGyvb5e": {"name": "Misalignment", "posts": 113},
            "4hCbeW5BEJv62uBZW": {"name": "Mechanistic Interpretability", "posts": 96},
            "6HrmHaxWnKDvnHqvB": {"name": "Eliciting Latent Knowledge", "posts": 48},
            "uP6wvbBHMvxBHqRGt": {"name": "Coherent Extrapolated Volition", "posts": 84},
            "tynrvBhCMGK8WkP9E": {"name": "Multi-Agent Dilemmas", "posts": 50},
            "47esLg2G3xZvH6WbW": {"name": "Gradient Hacking", "posts": 39},
            "vKy9EzoQfEFMzScnX": {"name": "Whole Brain Emulation", "posts": 66},
            "8hhLmPyTQTGsJ9L8c": {"name": "Paul Christiano", "posts": 57},
            "dCv7fWYBwTYXwiqsa": {"name": "Goodhart's Law", "posts": 89},
            "kq6rjLwqfLtD2J9px": {"name": "Infra-Bayesianism", "posts": 100},
            "DxkCGWmSL3FfBZ3yz": {"name": "Forecasting", "posts": 635},
            "Ej8uW9grqCHzZFFf5": {"name": "Goal-Directedness", "posts": 48},
            "uqBjdgkdEBBAHedfw": {"name": "AI Safety Camp", "posts": 26},
            "7vkLDezJDwqiAb6pc": {"name": "Reward Hacking", "posts": 47},
            "RdBTegsjrGjuqqGPL": {"name": "Deceptive Alignment", "posts": 31},
            "RCBb8cL5znBuNawyv": {"name": "Recursive Self-Improvement", "posts": 44}
        }
        self.logger.info(f"Configurados {len(self.DEFINITE_AI_SAFETY_TAGS)} tags AI Safety principales")

    def make_graphql_request(self, query: str, variables: Dict = None) -> Optional[Dict]:
        """Realiza una request GraphQL con rate limiting y reintentos"""
        time.sleep(self.rate_limit_delay)

        for attempt in range(self.max_retries):
            try:
                payload = {'query': query, 'variables': variables or {}}

                # Debug log para ver la query exacta
                if attempt == 0:
                    self.logger.debug(f"GraphQL Query: {query[:200]}...")

                response = requests.post(
                    self.graphql_endpoint,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )

                # Si hay error, log del response completo
                if response.status_code != 200:
                    self.logger.debug(f"Response status: {response.status_code}")
                    self.logger.debug(f"Response body: {response.text[:500]}")

                response.raise_for_status()

                data = response.json()
                if 'errors' in data:
                    self.logger.warning(f"GraphQL errors: {data['errors']}")

                return data

            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    self.logger.error(f"Max retries reached. Query failed.")
                    raise

        return None

    def extract_top_users(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        MVP: Extrae usuarios de tags definitivos, ordena por karma.
        Mantiene registro de qué posts vienen de qué tags.
        """
        self.logger.info("Extrayendo usuarios de tags AI Safety definitivos...")
        all_users = {}
        # Limpiar el diccionario de rastreo antes de empezar
        self.post_source_tags.clear()  # Ya inicializado en __init__

        # 1. Para cada tag definitivo, obtener usuarios
        for i, (tag_id, tag_info) in enumerate(self.DEFINITE_AI_SAFETY_TAGS.items(), 1):
            self.logger.info(f"  [{i}/{len(self.DEFINITE_AI_SAFETY_TAGS)}] Procesando tag: {tag_info['name']}")

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

            try:
                result = self.make_graphql_request(query, {'tagId': tag_id, 'limit': 50})

                if not result or 'data' not in result:
                    self.logger.warning(f"No data for tag {tag_info['name']}")
                    continue

                posts = result.get('data', {}).get('posts', {}).get('results', [])
                self.logger.debug(f"Tag {tag_info['name']}: {len(posts)} posts encontrados")

                # Mapear el tag a su research agenda
                research_agenda = self.map_tag_to_research_agenda(tag_info['name'])

                # Agregar usuarios únicos y rastrear posts
                for post in posts:
                    if post.get('_id'):
                        # Rastrear de qué tag vino este post
                        self.post_source_tags[post['_id']] = {
                            'tag_id': tag_id,
                            'tag_name': tag_info['name'],
                            'research_agenda': research_agenda
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

            except Exception as e:
                self.logger.error(f"Error procesando tag {tag_info['name']}: {e}")
                continue

        self.logger.info(f"Usuarios únicos encontrados: {len(all_users)}")

        # 2. Enriquecer con información completa del usuario (solo top users por karma)
        self.logger.info("Enriqueciendo información de usuarios...")

        # Ordenar por karma primero para procesar solo los mejores
        sorted_users_temp = sorted(
            all_users.values(),
            key=lambda x: x.get('karma', 0),
            reverse=True
        )

        # Solo procesar los top N para enriquecimiento
        users_to_enrich = sorted_users_temp[:min(limit, len(sorted_users_temp))]

        for i, user_data in enumerate(users_to_enrich, 1):
            if i % 5 == 0:
                self.logger.info(f"  Enriqueciendo usuario {i}/{len(users_to_enrich)}")

            try:
                user_id = user_data['userId']
                self.logger.debug(f"Enriqueciendo usuario {user_data.get('username')} con ID: {user_id}")
                user_full = self.get_user_full_info(user_id)
                if user_full:
                    # Actualizar directamente el objeto user_data que ya está en la lista
                    user_data.update(user_full)
                    self.logger.debug(f"Usuario {user_data.get('username')} enriquecido exitosamente")
            except Exception as e:
                self.logger.warning(f"Error obteniendo info completa de usuario {user_data.get('username', 'unknown')}: {e}")

        # 3. Ordenar por karma y retornar top N
        sorted_users = sorted(
            all_users.values(),
            key=lambda x: x.get('karma', 0),
            reverse=True
        )

        self.logger.info(f"Retornando top {limit} usuarios de {len(sorted_users)} totales")
        return sorted_users[:limit]

    def get_user_full_info(self, user_id: str) -> Dict[str, Any]:
        """Obtiene información completa de un usuario"""
        self.logger.debug(f"get_user_full_info llamado con user_id: {user_id}")

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
                    twitterProfileURL
                    postCount
                    commentCount
                    createdAt
                    profileTagIds
                }}
            }}
        }}
        """

        result = self.make_graphql_request(query, {})

        if result:
            self.logger.debug(f"Respuesta recibida para user_id {user_id}: {result.get('data', {}).get('user', {})}")
            if result.get('data', {}).get('user', {}).get('result'):
                return result['data']['user']['result']
        else:
            self.logger.debug(f"No se recibió respuesta para user_id {user_id}")

        return {}

    def extract_user_posts(self, user_id: str) -> List[Dict[str, Any]]:
        """Extrae todos los posts de un usuario"""
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

            # Enriquecer cada post con información de AI Safety tags
            for post in posts:
                self.enrich_post_with_ai_safety_tags(post)

            return posts
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

        # Revisar los tags del post para encontrar AI Safety tags
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

                    # Si es el primer tag de AI Safety encontrado, usarlo como extraction_source
                    if not post['extraction_source']:
                        post['extraction_source'] = {
                            'tag_id': tag_id,
                            'tag_name': tag_info['name'],
                            'research_agenda': agenda
                        }

        # Si tenemos información de post_source_tags (desde extract_top_users), agregarla
        if hasattr(self, 'post_source_tags') and post_id in self.post_source_tags:
            source_info = self.post_source_tags[post_id]

            # Actualizar extraction_source con la información original
            post['extraction_source'] = {
                'tag_id': source_info['tag_id'],
                'tag_name': source_info['tag_name'],
                'research_agenda': source_info['research_agenda']
            }

            # Asegurarse de que el tag de búsqueda esté en ai_safety_tags
            if not any(t['id'] == source_info['tag_id'] for t in post['ai_safety_tags']):
                post['ai_safety_tags'].insert(0, {
                    'id': source_info['tag_id'],
                    'name': source_info['tag_name'],
                    'source': 'search_tag'
                })

    def map_tag_to_research_agenda(self, tag_name: str) -> str:
        """Mapea un tag a su research agenda correspondiente"""
        tag_lower = tag_name.lower()

        # Mapeo basado en las research agendas del Backend Strategy Plan
        if any(term in tag_lower for term in ['inner alignment', 'outer alignment', 'mesa-optimization', 'alignment theory']):
            return 'Alignment Theory'
        elif any(term in tag_lower for term in ['governance', 'regulation', 'policy', 'scaling laws', 'compute governance']):
            return 'AI Governance & Policy'
        elif any(term in tag_lower for term in ['interpretability', 'mechanistic']):
            return 'Mechanistic Interpretability'
        elif any(term in tag_lower for term in ['agent foundations', 'embedded agency', 'logical', 'decision theory', 'functional decision', 'updateless']):
            return 'Agent Foundations'
        elif any(term in tag_lower for term in ['cooperative', 'game theory', 'coordination', 'commitment']):
            return 'Cooperative AI'
        elif any(term in tag_lower for term in ['scalable oversight', 'debate', 'amplification', 'mechanism design']):
            return 'Scalable Oversight'
        elif any(term in tag_lower for term in ['value learning', 'value alignment', 'coherent extrapolated', 'reward']):
            return 'Value Learning & Alignment'
        elif any(term in tag_lower for term in ['miri', 'redwood', 'alignment research center', 'anthropic', 'deepmind', 'openai']):
            return 'AI Safety Organizations'
        elif any(term in tag_lower for term in ['corrigibility', 'tool ai', 'myopia', 'treacherous turn']):
            return 'Safety Properties'
        elif any(term in tag_lower for term in ['forecasting', 'timelines', 'capabilities']):
            return 'AI Forecasting & Capabilities'

        return None

    def extract_user_comments(self, user_id: str) -> List[Dict[str, Any]]:
        """Extrae todos los comentarios de un usuario"""
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
                    postedAt
                    af
                }}
            }}
        }}
        """

        result = self.make_graphql_request(query, {})
        if result and result.get('data', {}).get('comments', {}).get('results'):
            return result['data']['comments']['results']
        return []