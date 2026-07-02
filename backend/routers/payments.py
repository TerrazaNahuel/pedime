"""
Endpoints de pago con Mercado Pago para suscripciones Premium.

Este módulo queda en espera hasta que el usuario configure las credenciales
de Mercado Pago en las variables de entorno MP_ACCESS_TOKEN y MP_PUBLIC_KEY.

Endpoints planeados:
  POST /api/payments/create-preference → crea una preferencia de pago en MP
  POST /api/payments/webhook ← webhook de MP para confirmar pagos
  GET /api/payments/success → callback de éxito después del pago
  GET /api/payments/failure → callback de fallo
  GET /api/payments/pending → callback de pago pendiente
"""

import logging
from datetime import UTC, date, datetime

from database import get_db
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from routers.admin_base import get_authenticated_store

from backend.settings import MP_ACCESS_TOKEN, PREMIUM_DURATION_DAYS, PREMIUM_PRICE_MONTHLY, PREMIUM_PRICE_YEARLY, SITE_URL

router = APIRouter()
logger = logging.getLogger("pedime.payments")


class CreatePreferencePayload(BaseModel):
    plan: str  # "monthly" o "yearly"


@router.post("/api/payments/create-preference")
def create_preference(payload: CreatePreferencePayload, request: Request, db: Session = Depends(get_db)):
    """Crea una preferencia de pago en Mercado Pago."""
    store = get_authenticated_store(request, db)

    if not MP_ACCESS_TOKEN:
        return JSONResponse({"ok": False, "error": "Mercado Pago no está configurado todavía."}, status_code=503)

    if payload.plan == "yearly":
        title = "Pedime Premium - Plan Anual"
        price = PREMIUM_PRICE_YEARLY
    else:
        title = "Pedime Premium - Plan Mensual"
        price = PREMIUM_PRICE_MONTHLY

    # TODO: implementar con SDK de mercadopago cuando estén las credenciales
    # import mercadopago
    # sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
    # preference_data = {
    #     "items": [{"title": title, "quantity": 1, "unit_price": float(price)}],
    #     "back_urls": {
    #         "success": f"{SITE_URL}/api/payments/success",
    #         "failure": f"{SITE_URL}/api/payments/failure",
    #         "pending": f"{SITE_URL}/api/payments/pending",
    #     },
    #     "notification_url": f"{SITE_URL}/api/payments/webhook",
    #     "external_reference": str(store.id),
    #     "auto_return": "approved",
    # }
    # result = sdk.preference().create(preference_data)
    # return {"ok": True, "init_point": result["response"]["init_point"]}

    return JSONResponse({"ok": False, "error": "Mercado Pago no está configurado todavía."}, status_code=503)


@router.post("/api/payments/webhook")
def payment_webhook(request: Request, db: Session = Depends(get_db)):
    """Webhook de Mercado Pago para recibir notificaciones de pago."""
    # TODO: implementar verificación de firma y actualización de plan
    return JSONResponse({"ok": True})


@router.get("/api/payments/success")
def payment_success(request: Request, db: Session = Depends(get_db)):
    """Callback cuando el pago se completa exitosamente."""
    # TODO: verificar payment_id y external_reference, activar premium
    return RedirectResponse(url="/admin/dashboard?premium=ok")


@router.get("/api/payments/failure")
def payment_failure(request: Request, db: Session = Depends(get_db)):
    """Callback cuando el pago falla."""
    return RedirectResponse(url="/admin/stats?premium=error")


@router.get("/api/payments/pending")
def payment_pending(request: Request, db: Session = Depends(get_db)):
    """Callback cuando el pago queda pendiente."""
    return RedirectResponse(url="/admin/stats?premium=pending")
