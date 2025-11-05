"""
Async Global Rate Limiter - Thread-safe rate limiting con asyncio
"""

import asyncio
import time
from typing import Optional


class AsyncGlobalRateLimiter:
    """
    Rate limiter async para coordinar múltiples coroutines

    Asegura que solo 1 request se haga por segundo globalmente,
    sin importar cuántas coroutines estén ejecutándose.
    """

    def __init__(self, requests_per_second: float = 1.0):
        """
        Args:
            requests_per_second: Número de requests permitidos por segundo
        """
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0
        self.lock = asyncio.Lock()

    async def wait(self):
        """
        Esperar el tiempo necesario antes de permitir el siguiente request

        Async-safe: Solo una coroutine puede hacer request a la vez
        """
        async with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_request_time

            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                await asyncio.sleep(sleep_time)

            self.last_request_time = time.time()

    def set_rate(self, requests_per_second: float):
        """Actualizar el rate limit dinámicamente"""
        self.min_interval = 1.0 / requests_per_second


# Instancia global (singleton)
_global_limiter: Optional[AsyncGlobalRateLimiter] = None


def get_async_rate_limiter(requests_per_second: float = 1.0) -> AsyncGlobalRateLimiter:
    """
    Obtener el rate limiter global async (singleton)

    Args:
        requests_per_second: Solo se usa en la primera llamada

    Returns:
        La instancia global del rate limiter async
    """
    global _global_limiter

    if _global_limiter is None:
        _global_limiter = AsyncGlobalRateLimiter(requests_per_second)

    return _global_limiter
