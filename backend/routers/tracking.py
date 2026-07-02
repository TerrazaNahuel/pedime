"""
Endpoints de tracking para estadísticas del menú.

Registra visitas a la página y clics en WhatsApp sin afectar la experiencia del usuario.
Usa respuestas 204 (sin contenido) para ser lo más liviano posible.
"""

import logging
from datetime import UTC, datetime

from database import get_db
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from models import PageView, Store, WhatsAppClick
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter()
logger = logging.getLogger("pedime.tracking")


class TrackClickPayload(BaseModel):
    cart_value: float = 0
    item_count: int = 0
    payment_method: str = ""


@router.post("/api/track/view/{slug}")
def track_view(slug: str, request: Request, db: Session = Depends(get_db)):
    """Registra una visita al menú del comercio."""
    store = db.query(Store).filter(Store.slug == slug, Store.is_active == True).first()
    if not store:
        return JSONResponse({"ok": False}, status_code=404)
    db.add(PageView(store_id=store.id, viewed_at=datetime.now(UTC)))
    db.commit()
    return JSONResponse({"ok": True}, status_code=200)


@router.post("/api/track/whatsapp-click/{slug}")
def track_whatsapp_click(slug: str, payload: TrackClickPayload, request: Request, db: Session = Depends(get_db)):
    """Registra un clic en el botón de WhatsApp para enviar un pedido."""
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
