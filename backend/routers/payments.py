"""
Endpoints de pago con Mercado Pago para suscripciones Premium.

Usa el SDK oficial de Mercado Pago. Requiere MP_ACCESS_TOKEN en .env.
"""

import json
import logging
from datetime import UTC, datetime, timedelta

import mercadopago
from database import get_db
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from models import PaymentTransaction, Store
from pydantic import BaseModel
from routers.admin_base import get_authenticated_store, logger as admin_logger
from sqlalchemy.orm import Session

from backend.settings import MP_ACCESS_TOKEN, MP_WEBHOOK_SECRET, PREMIUM_DURATION_DAYS, PREMIUM_PRICE_MONTHLY, PREMIUM_PRICE_YEARLY, SITE_URL

router = APIRouter()
logger = logging.getLogger("pedime.payments")


class CreatePreferencePayload(BaseModel):
    plan: str  # "monthly" o "yearly"


@router.post("/api/payments/create-preference")
def create_preference(payload: CreatePreferencePayload, request: Request, db: Session = Depends(get_db)):
    """Crea una preferencia de pago en Mercado Pago y retorna el init_point."""
    store = get_authenticated_store(request, db)

    if not MP_ACCESS_TOKEN:
        return JSONResponse({"ok": False, "error": "Mercado Pago no está configurado."}, status_code=503)

    if payload.plan == "yearly":
        title = "Pedime Premium - Plan Anual"
        price = PREMIUM_PRICE_YEARLY
        duration_days = PREMIUM_DURATION_DAYS * 12
    else:
        title = "Pedime Premium - Plan Mensual"
        price = PREMIUM_PRICE_MONTHLY
        duration_days = PREMIUM_DURATION_DAYS

    sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
    # Crea la preferencia con URLs de retorno, webhook y referencia externa (store_id)
    preference_data = {
        "items": [{"title": title, "quantity": 1, "unit_price": float(price)}],
        "back_urls": {
            "success": f"{SITE_URL}/api/payments/success",
            "failure": f"{SITE_URL}/api/payments/failure",
            "pending": f"{SITE_URL}/api/payments/pending",
        },
        "notification_url": f"{SITE_URL}/api/payments/webhook",
        "external_reference": str(store.id),
        "auto_return": "approved",
    }
    result = sdk.preference().create(preference_data)

    if result["status"] not in (200, 201):
        logger.error("MP create_preference error: %s", result)
        return JSONResponse({"ok": False, "error": "Error al crear preferencia de pago."}, status_code=502)

    mp_preference_id = result["response"]["id"]
    init_point = result["response"]["init_point"]

    tx = PaymentTransaction(
        store_id=store.id,
        mp_preference_id=mp_preference_id,
        status="pending",
        amount=price,
        plan_type=payload.plan,
        expires_at=datetime.now(UTC) + timedelta(days=duration_days),
    )
    db.add(tx)
    db.commit()

    logger.info("Preferencia MP creada store_id=%s preference=%s", store.id, mp_preference_id)
    return {"ok": True, "init_point": init_point, "preference_id": mp_preference_id}


@router.post("/api/payments/webhook")
async def payment_webhook(request: Request, db: Session = Depends(get_db)):
    """Webhook de Mercado Pago para recibir notificaciones de pago."""
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    topic = request.query_params.get("topic") or request.query_params.get("type")

    logger.info("Webhook MP recibido: topic=%s body=%s", topic, body)

    if topic == "payment":
        # El ID puede venir en el body (topic=payment) o en query params (topic=merchant_order)
        payment_id = body.get("data", {}).get("id") or request.query_params.get("id")
        if not payment_id:
            return JSONResponse({"ok": False, "error": "Falta payment_id"}, status_code=400)

        sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
        payment_info = sdk.payment().get(payment_id)
        if payment_info["status"] != 200:
            logger.error("MP get_payment error: %s", payment_info)
            return JSONResponse({"ok": False}, status_code=502)

        payment_data = payment_info["response"]
        status = payment_data.get("status")
        external_ref = payment_data.get("external_reference", "")
        preference_id = payment_data.get("preference_id", "")

        if status != "approved":
            logger.info("Pago MP no aprobado: status=%s payment=%s", status, payment_id)
            return JSONResponse({"ok": True})

        store_id = int(external_ref) if external_ref.isdigit() else None
        if not store_id:
            logger.error("MP webhook: external_reference inválida: %s", external_ref)
            return JSONResponse({"ok": False}, status_code=400)

        tx = db.query(PaymentTransaction).filter(
            PaymentTransaction.mp_preference_id == preference_id,
            PaymentTransaction.store_id == store_id,
            PaymentTransaction.status == "pending",
        ).first()

        if not tx:
            logger.warning("MP webhook: transacción no encontrada preference=%s store=%s", preference_id, store_id)
            return JSONResponse({"ok": True})

        # Marca la transacción como aprobada y activa Premium en el store
        tx.status = "approved"
        tx.mp_payment_id = str(payment_id)
        tx.approved_at = datetime.now(UTC)
        db.commit()

        store = db.query(Store).filter(Store.id == store_id).first()
        if store:
            store.plan = "premium"
            store.plan_expires_at = tx.expires_at
            db.commit()
            admin_logger.info("Store %s activado Premium vía MP (payment=%s)", store_id, payment_id)

        logger.info("Pago MP aprobado: store=%s payment=%s", store_id, payment_id)

    return JSONResponse({"ok": True})


@router.get("/api/payments/success")
def payment_success(request: Request, db: Session = Depends(get_db)):
    """Callback cuando el pago se completa exitosamente."""
    payment_id = request.query_params.get("payment_id")
    preference_id = request.query_params.get("preference_id")
    external_ref = request.query_params.get("external_reference", "")

    if external_ref.isdigit():
        store_id = int(external_ref)
        store = db.query(Store).filter(Store.id == store_id).first()
        if store:
            tx = db.query(PaymentTransaction).filter(
                PaymentTransaction.mp_preference_id == preference_id,
                PaymentTransaction.store_id == store_id,
            ).first()
            if tx and tx.status == "pending":
                tx.status = "approved"
                tx.mp_payment_id = str(payment_id) if payment_id else tx.mp_payment_id
                tx.approved_at = datetime.now(UTC)
                store.plan = "premium"
                store.plan_expires_at = tx.expires_at
                db.commit()
                admin_logger.info("Store %s activado Premium vía success callback", store_id)

    return RedirectResponse(url="/admin/dashboard?msg=¡Bienvenido+a+Premium!")


@router.get("/api/payments/failure")
def payment_failure(request: Request, db: Session = Depends(get_db)):
    """Callback cuando el pago falla."""
    return RedirectResponse(url="/admin/stats?premium=error")


@router.get("/api/payments/pending")
def payment_pending(request: Request, db: Session = Depends(get_db)):
    """Callback cuando el pago queda pendiente."""
    return RedirectResponse(url="/admin/stats?premium=pending")
