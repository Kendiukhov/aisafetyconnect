#!/usr/bin/env python3
"""
Test del Global Rate Limiter

Verifica que múltiples threads respeten el límite de 1 req/segundo
"""

import time
import threading
from api_client import SemanticScholarAPI

def test_rate_limiter():
    """
    Test: 3 threads intentan hacer requests simultáneos
    Esperado: Se ejecuten con 1 segundo de separación
    """
    print("="*60)
    print("TEST: Global Rate Limiter")
    print("="*60)
    print("\nCreando 3 threads que harán requests simultáneos...")
    print("Esperado: Se ejecuten con ~1 segundo de separación\n")

    # Crear API client (comparte el rate limiter global)
    api = SemanticScholarAPI(api_key="test_key")

    # Lista para guardar timestamps
    timestamps = []
    lock = threading.Lock()

    def make_request(thread_id):
        """Función que ejecuta cada thread"""
        print(f"[Thread {thread_id}] Intentando hacer request...")

        # Guardar timestamp ANTES de rate limiting
        with lock:
            timestamps.append(('before', thread_id, time.time()))

        # Este wait() coordinará con otros threads
        api.rate_limiter.wait()

        # Guardar timestamp DESPUÉS de rate limiting
        request_time = time.time()
        with lock:
            timestamps.append(('after', thread_id, request_time))

        print(f"[Thread {thread_id}] ✅ Request permitido @ {request_time:.3f}")

    # Lanzar 3 threads simultáneos
    threads = []
    start_time = time.time()

    for i in range(3):
        t = threading.Thread(target=make_request, args=(i,))
        t.start()
        threads.append(t)

    # Esperar que terminen todos
    for t in threads:
        t.join()

    # Analizar resultados
    print("\n" + "="*60)
    print("RESULTADOS")
    print("="*60)

    # Filtrar solo timestamps 'after' (cuando se hizo el request)
    request_times = [t[2] for t in timestamps if t[0] == 'after']
    request_times.sort()

    print(f"\nTiempo total: {request_times[-1] - request_times[0]:.2f} segundos")
    print(f"\nTimestamps de requests:")

    for i, t in enumerate(request_times):
        elapsed = t - start_time
        if i > 0:
            gap = t - request_times[i-1]
            print(f"  Request {i+1}: {elapsed:.3f}s (gap: {gap:.3f}s)")
        else:
            print(f"  Request {i+1}: {elapsed:.3f}s")

    # Verificar gaps
    print("\n" + "="*60)
    print("VALIDACIÓN")
    print("="*60)

    gaps = [request_times[i+1] - request_times[i] for i in range(len(request_times)-1)]

    all_valid = True
    for i, gap in enumerate(gaps):
        if gap >= 0.9:  # Tolerancia de 0.1s
            print(f"✅ Gap {i+1}: {gap:.3f}s (OK)")
        else:
            print(f"❌ Gap {i+1}: {gap:.3f}s (DEMASIADO RÁPIDO!)")
            all_valid = False

    print("\n" + "="*60)
    if all_valid:
        print("✅ TEST PASADO: Rate limiting funciona correctamente")
    else:
        print("❌ TEST FALLIDO: Requests demasiado rápidos")
    print("="*60)

if __name__ == "__main__":
    test_rate_limiter()
