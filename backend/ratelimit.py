"""
Rate limiter en memoria para prevenir abuso de endpoints críticos (login, register).

Almacena timestamps por clave (ej: "login:192.168.1.1") y rechaza si se
supera el límite en la ventana de tiempo configurada.
"""

import threading
import time
from collections import defaultdict


class RateLimiter:
    """
    Rate limiter simple en memoria. No persiste entre reinicios del servidor.

    Advertencia: el estado vive solo en este proceso. Si la app se escala a
    múltiples workers (gunicorn, uvicorn --workers N), cada worker tiene su
    propio contador, por lo que el límite real podría ser hasta N veces mayor.
    Railway usa un solo worker por defecto, así que no es un problema en producción.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.attempts = defaultdict(list)
        self._cleanup_counter = 0

    def check(self, key: str, max_attempts: int, window_seconds: int = 60) -> bool:
        now = time.time()
        with self._lock:
            self.attempts[key] = [t for t in self.attempts[key] if now - t < window_seconds]
            if len(self.attempts[key]) >= max_attempts:
                return False
            self.attempts[key].append(now)
            self._cleanup_counter += 1
            if self._cleanup_counter >= 100:
                self._cleanup_counter = 0
                self._remove_stale_keys()
        return True

    def _remove_stale_keys(self):
        """Elimina keys sin intentos activos para evitar memory leak."""
        now = time.time()
        stale = [k for k, v in self.attempts.items() if not v]
        for k in stale:
            del self.attempts[k]

    def clear(self):
        """Resetea todos los intentos. Útil en tests."""
        with self._lock:
            self.attempts.clear()
