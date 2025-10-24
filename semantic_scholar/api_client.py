"""
API Client - Maneja solo requests HTTP al Semantic Scholar Bulk API
"""

import time
import logging
import requests
from typing import Optional, Dict, List, Tuple

from rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


class SemanticScholarAPI:
    """Cliente HTTP simple para el Bulk API"""

    BULK_API_URL = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"

    # Campos que pedimos al API
    FIELDS = (
        "title,abstract,authors,year,venue,citationCount,"
        "openAccessPdf,externalIds,publicationTypes,publicationDate,"
        "fieldsOfStudy,s2FieldsOfStudy,url,referenceCount,"
        "influentialCitationCount,isOpenAccess,publicationVenue"
    )

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.headers = {
            "User-Agent": "AIResearchBot/v2.0",
            "Accept": "application/json",
        }
        if api_key:
            self.headers["x-api-key"] = api_key

        # Rate limiting GLOBAL (compartido entre todos los threads)
        # Con API key: 1 request/segundo para /paper/search/bulk
        # Sin API key: 5000 requests/5min compartido (conservador: 1 req/segundo)
        requests_per_second = 1.0 if api_key else 1.0
        self.rate_limiter = get_rate_limiter(requests_per_second)

    def search(
        self,
        query: str,
        limit: int = 1000,
        year_from: int = 2015,
        min_citations: int = 0,
        token: Optional[str] = None
    ) -> Tuple[List[Dict], Optional[str]]:
        """
        Hacer una búsqueda en el Bulk API

        Returns:
            (papers, next_token)
        """
        # Rate limiting GLOBAL (coordina con otros threads)
        self.rate_limiter.wait()

        # Construir parámetros
        params = {
            "query": query,
            "limit": min(limit, 1000),
            "fields": self.FIELDS,
            "year": f"{year_from}-",
            "sort": "citationCount:desc"
        }

        if token:
            params["token"] = token

        if min_citations > 0:
            params["minCitationCount"] = str(min_citations)

        # Hacer request
        try:
            response = requests.get(
                self.BULK_API_URL,
                params=params,
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                papers = data.get('data', [])
                next_token = data.get('token')
                return papers, next_token

            elif response.status_code == 429:
                logger.warning("Rate limit (429), esperando 10s...")
                time.sleep(10)
                return [], None

            else:
                logger.error(f"Error HTTP {response.status_code}")
                return [], None

        except Exception as e:
            logger.error(f"Exception en request: {e}")
            return [], None
