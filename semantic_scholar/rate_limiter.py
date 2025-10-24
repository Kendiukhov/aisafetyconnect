"""
Global Rate Limiter - Thread-safe rate limiting compartido
"""

import time
import threading
from typing import Optional


class GlobalRateLimiter:
    """
    Rate limiter thread-safe para coordinar múltiples workers

    Asegura que solo 1 request se haga por segundo globalmente,
    sin importar cuántos threads estén ejecutándose.
    """

    def __init__(self, requests_per_second: float = 1.0):
        """
        Args:
            requests_per_second: Número de requests permitidos por segundo
        """
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0
        self.lock = threading.Lock()

    def wait(self):
        """
        Esperar el tiempo necesario antes de permitir el siguiente request

        Thread-safe: Solo un thread puede hacer request a la vez
        """
        with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_request_time

            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                time.sleep(sleep_time)

            self.last_request_time = time.time()

    def set_rate(self, requests_per_second: float):
        """Actualizar el rate limit dinámicamente"""
        with self.lock:
            self.min_interval = 1.0 / requests_per_second


# Instancia global (singleton)
_global_limiter: Optional[GlobalRateLimiter] = None


def get_rate_limiter(requests_per_second: float = 1.0) -> GlobalRateLimiter:
    """
    Obtener el rate limiter global (singleton)

    Args:
        requests_per_second: Solo se usa en la primera llamada

    Returns:
        La instancia global del rate limiter
    """
    global _global_limiter

    if _global_limiter is None:
        _global_limiter = GlobalRateLimiter(requests_per_second)

    return _global_limiter
