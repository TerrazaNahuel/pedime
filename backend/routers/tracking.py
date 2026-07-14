"""
Endpoints de tracking para estadísticas del menú.

Registra visitas a la página y clics en WhatsApp sin afectar la experiencia del usuario.
Usa respuestas 204 (sin contenido) para ser lo más liviano posible.
"""

import logging
from datetime import UTC, datetime
from urllib.parse import urlparse

from database import get_db
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from models import PageView, Store, WhatsAppClick
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

router = APIRouter()
logger = logging.getLogger("pedime.tracking")

from backend.settings import SITE_URL

SITE_HOST = urlparse(SITE_URL).hostname or "localhost"
VALID_PAYMENT_METHODS = {"", "transfer", "cash", "mercadopago", "other"}


def _validate_origin(request: Request):
    """Valida que Origin/Referer sea el mismo sitio (protección CSRF para endpoints públicos)."""
    origin = request.headers.get("Origin") or request.headers.get("Referer") or ""
    if not origin:
        logger.warning("Tracking sin Origin/Referer: %s %s", request.method, request.url.path)
        raise HTTPException(status_code=403, detail="Origen requerido")
    try:
        req_host = urlparse(origin).hostname
    except Exception:
        logger.warning("Error parseando origin: %s", origin)
        req_host = None
    if not req_host:
        raise HTTPException(status_code=403, detail="Origen inválido")
    # Solo permite peticiones desde el mismo sitio, localhost o 127.0.0.1
    if req_host not in (SITE_HOST, "localhost", "127.0.0.1"):
        logger.warning("Origen rechazado para tracking: %s", origin)
        raise HTTPException(status_code=403, detail="Origen no permitido")


class TrackClickPayload(BaseModel):
    cart_value: float = 0
    item_count: int = 0
    payment_method: str = ""

    @field_validator("cart_value")
    @classmethod
    def _validate_cart_value(cls, v: float) -> float:
        if v < 0 or v > 1_000_000:
            return 0
        return v

    @field_validator("item_count")
    @classmethod
    def _validate_item_count(cls, v: int) -> int:
        if v < 0 or v > 999:
            return 0
        return v

    @field_validator("payment_method")
    @classmethod
    def _validate_payment_method(cls, v: str) -> str:
        return v if v in VALID_PAYMENT_METHODS else "other"


@router.post("/api/track/view/{slug}")
def track_view(slug: str, request: Request, db: Session = Depends(get_db)):
    """Registra una visita al menú del comercio."""
    _validate_origin(request)
    store = db.query(Store).filter(Store.slug == slug, Store.is_active == True).first()
    if not store:
        return JSONResponse({"ok": False}, status_code=404)
    db.add(PageView(store_id=store.id, viewed_at=datetime.now(UTC)))
    db.commit()
    return JSONResponse({"ok": True}, status_code=200)


@router.post("/api/track/whatsapp-click/{slug}")
def track_whatsapp_click(slug: str, payload: TrackClickPayload, request: Request, db: Session = Depends(get_db)):
    """Registra un clic en el botón de WhatsApp para enviar un pedido."""
    _validate_origin(request)
    store = db.query(Store).filter(Store.slug == slug, Store.is_active == True).first()
    if not store:
        return JSONResponse({"ok": False}, status_code=404)
    db.add(WhatsAppClick(
        store_id=store.id,
        clicked_at=datetime.now(UTC),
        cart_value=payload.cart_value,
        item_count=payload.item_count,
        payment_method=payload.payment_method,
    ))
    db.commit()
    return JSONResponse({"ok": True}, status_code=200)
