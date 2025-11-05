"""
Async API Client - Maneja requests HTTP asíncronos al Semantic Scholar Bulk API
"""

import asyncio
import logging
import aiohttp
from typing import Optional, Dict, List, Tuple

from async_rate_limiter import get_async_rate_limiter

logger = logging.getLogger(__name__)


class AsyncSemanticScholarAPI:
    """Cliente HTTP async para el Bulk API"""

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

        # Rate limiting GLOBAL (compartido entre todas las coroutines)
        # Con API key: 1 request/segundo para /paper/search/bulk
        # Sin API key: 5000 requests/5min compartido (conservador: 1 req/segundo)
        requests_per_second = 1.0 if api_key else 1.0
        self.rate_limiter = get_async_rate_limiter(requests_per_second)

        # Session será creada al primer uso
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtener o crear la sesión HTTP"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self.headers)
        return self._session

    async def close(self):
        """Cerrar la sesión HTTP"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def search(
        self,
        query: str,
        limit: int = 1000,
        year_from: int = 2015,
        min_citations: int = 0,
        token: Optional[str] = None
    ) -> Tuple[List[Dict], Optional[str]]:
        """
        Hacer una búsqueda en el Bulk API de forma asíncrona

        Returns:
            (papers, next_token)
        """
        # Rate limiting GLOBAL (coordina con otras coroutines)
        await self.rate_limiter.wait()

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

        # Hacer request async
        try:
            session = await self._get_session()
            async with session.get(
                self.BULK_API_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    papers = data.get('data', [])
                    next_token = data.get('token')
                    return papers, next_token

                elif response.status == 429:
                    logger.warning("Rate limit (429), esperando 10s...")
                    await asyncio.sleep(10)
                    return [], None

                else:
                    logger.error(f"Error HTTP {response.status}")
                    return [], None

        except Exception as e:
            logger.error(f"Exception en request: {e}")
            return [], None

    async def __aenter__(self):
        """Soporte para context manager async"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cerrar sesión al salir del context manager"""
        await self.close()
