"""
Rate limiter con respaldo en base de datos para compartir estado entre workers.

En producción con PostgreSQL, todos los workers comparten la misma tabla,
por lo que los límites se aplican globalmente.
"""

import logging
from datetime import UTC, datetime, timedelta

from database import SessionLocal
from models import RateLimitEntry
from sqlalchemy import delete

logger = logging.getLogger("pedime.ratelimit")


class RateLimiter:
    """
    Rate limiter basado en base de datos, compartido entre workers via DB.

    En cada check(), inserta un registro y cuenta los registros activos
    en la ventana de tiempo. Los registros viejos se eliminan periódicamente
    para evitar que la tabla crezca indefinidamente.

    Nota: usa SessionLocal() directo porque es un helper standalone,
    no un endpoint de FastAPI que pueda usar Depends(get_db).
    """

    def __init__(self):
        # Contador para ejecutar limpieza de registros viejos cada 100 check()
        self._cleanup_counter = 0

    def check(self, key: str, max_attempts: int, window_seconds: int = 60) -> bool:
        """
        Verifica si la clave key puede ejecutar la acción.

        Cuenta los intentos registrados dentro de la ventana de tiempo.
        Si no supera el límite, registra un nuevo intento.

        Args:
            key: Identificador único (ej. "login:1.2.3.4").
            max_attempts: Máximo de intentos permitidos en la ventana.
            window_seconds: Duración de la ventana en segundos (default 60).

        Returns:
            True si la acción está permitida, False si se excedió el límite.
        """
        db = SessionLocal()
        try:
            # Límite inferior de la ventana de tiempo
            cutoff = datetime.now(UTC) - timedelta(seconds=window_seconds)

            # Cuenta los intentos registrados dentro de la ventana vigente
            count = db.query(RateLimitEntry).filter(
                RateLimitEntry.key == key,
                RateLimitEntry.attempted_at > cutoff,
            ).count()

            # Si alcanzó el límite, rechaza la acción
            if count >= max_attempts:
                return False

            # Registra el nuevo intento
            db.add(RateLimitEntry(key=key, attempted_at=datetime.now(UTC)))
            db.commit()

            # Limpieza periódica: cada 100 check() elimina registros expirados
            self._cleanup_counter += 1
            if self._cleanup_counter >= 100:
                self._cleanup_counter = 0
                self._remove_stale_keys(db, cutoff)

            return True
        finally:
            db.close()

    def _remove_stale_keys(self, db, cutoff):
        """Elimina registros anteriores al cutoff para mantener la tabla liviana."""
        try:
            db.execute(
                delete(RateLimitEntry).where(RateLimitEntry.attempted_at <= cutoff)
            )
            db.commit()
        except Exception as e:
            logger.warning("Error limpiando rate limit entries: %s", e)
            db.rollback()

    def clear(self):
        """Elimina todos los registros de rate limiting (reset completo)."""
        db = SessionLocal()
        try:
            db.execute(delete(RateLimitEntry))
            db.commit()
        finally:
            db.close()
