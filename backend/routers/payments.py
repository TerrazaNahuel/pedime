"""
Endpoints de pago con Mercado Pago para suscripciones Premium.

Usa el SDK oficial de Mercado Pago. Requiere MP_ACCESS_TOKEN en .env.
"""

import hashlib
import hmac
import logging
from datetime import UTC, datetime, timedelta

import mercadopago
from csrf import validate_csrf
from database import get_db
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from models import PaymentTransaction, Store
from pydantic import BaseModel
from routers.admin_base import get_authenticated_store
from routers.admin_base import logger as admin_logger
from sqlalchemy.orm import Session

from backend.settings import (
    MP_ACCESS_TOKEN,
    MP_WEBHOOK_SECRET,
    PREMIUM_DURATION_DAYS,
    SITE_URL,
    VIP_BASICO_PRICE,
    VIP_PREMIUM_PRICE,
)

router = APIRouter()
logger = logging.getLogger("pedime.payments")

PLAN_INFO = {
    "vip_basico": {"title": "Pedime VIP Básico", "price": VIP_BASICO_PRICE},
    "vip_premium": {"title": "Pedime VIP Premium", "price": VIP_PREMIUM_PRICE},
}


class CreatePreferencePayload(BaseModel):
    plan: str  # "vip_basico" | "vip_premium"
    csrf_token: str = ""


def _verify_mp_signature(request: Request, payment_id: str) -> bool:
    """Verifica la firma HMAC-SHA256 del webhook de Mercado Pago."""
    if not MP_WEBHOOK_SECRET:
        admin_logger.warning("MP_WEBHOOK_SECRET no configurado, webhook sin verificar")
        return True
    x_signature = request.headers.get("x-signature", "")
    x_request_id = request.headers.get("x-request-id", "")
    if not x_signature or not x_request_id:
        admin_logger.warning("MP webhook: headers x-signature/x-request-id faltantes")
        return False
    expected = hmac.new(
        MP_WEBHOOK_SECRET.encode(),
        f"id:{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, x_signature)


def _activate_premium(tx: PaymentTransaction, store: Store, payment_id: str, db: Session) -> None:
    """Activa el plan premium en el store y marca la transacción como aprobada."""
    tx.status = "approved"
    tx.mp_payment_id = str(payment_id) if payment_id else tx.mp_payment_id
    tx.approved_at = datetime.now(UTC)
    store.plan = tx.plan_type
    store.plan_expires_at = tx.expires_at
    db.commit()


@router.post("/api/payments/create-preference")
def create_preference(payload: CreatePreferencePayload, request: Request, db: Session = Depends(get_db)):
    """Crea una preferencia de pago en Mercado Pago y retorna el init_point."""
    store = get_authenticated_store(request, db)
    validate_csrf(request, payload.csrf_token)

    if not MP_ACCESS_TOKEN:
        return JSONResponse({"ok": False, "error": "Mercado Pago no está configurado."}, status_code=503)

    plan_info = PLAN_INFO.get(payload.plan)
    if not plan_info:
        return JSONResponse({"ok": False, "error": "Plan inválido."}, status_code=400)

    title = plan_info["title"]
    price = plan_info["price"]
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
    try:
        result = sdk.preference().create(preference_data)
    except Exception:
        logger.exception("MP create_preference network error")
        return JSONResponse({"ok": False, "error": "Error al conectar con Mercado Pago."}, status_code=502)

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

    if not _verify_mp_signature(request, body.get("data", {}).get("id", "")):
        admin_logger.warning("MP webhook: firma inválida o faltante")
        return JSONResponse({"ok": False, "error": "Firma inválida"}, status_code=403)

    if topic == "payment":
        # El ID puede venir en el body (topic=payment) o en query params (topic=merchant_order)
        payment_id = body.get("data", {}).get("id") or request.query_params.get("id")
        if not payment_id:
            return JSONResponse({"ok": False, "error": "Falta payment_id"}, status_code=400)

        sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
        try:
            payment_info = sdk.payment().get(payment_id)
        except Exception:
            logger.exception("MP get_payment network error")
            return JSONResponse({"ok": False, "error": "Error al consultar Mercado Pago."}, status_code=502)
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

        store = db.query(Store).filter(Store.id == store_id).first()
        if store:
            _activate_premium(tx, store, payment_id, db)
            admin_logger.info("Store %s activado %s vía MP (payment=%s)", store_id, tx.plan_type, payment_id)

        logger.info("Pago MP aprobado: store=%s payment=%s", store_id, payment_id)

    return JSONResponse({"ok": True})


@router.get("/api/payments/success")
def payment_success(request: Request, db: Session = Depends(get_db)):
    """Callback cuando el pago se completa exitosamente."""
    payment_id = request.query_params.get("payment_id")
    preference_id = request.query_params.get("preference_id")
    external_ref = request.query_params.get("external_reference", "")

    plan_nombre = "VIP"
    if external_ref.isdigit():
        store_id = int(external_ref)
        store = db.query(Store).filter(Store.id == store_id).first()
        if store:
            tx = db.query(PaymentTransaction).filter(
                PaymentTransaction.mp_preference_id == preference_id,
                PaymentTransaction.store_id == store_id,
            ).first()
            if tx and tx.status == "pending":
                _activate_premium(tx, store, payment_id or "", db)
                admin_logger.info("Store %s activado %s vía success callback", store_id, tx.plan_type)
            plan_nombre = {"vip_basico": "VIP Básico", "vip_premium": "VIP Premium"}.get(store.plan, "VIP")

    return RedirectResponse(url=f"/admin/dashboard?msg=¡Bienvenido+a+{plan_nombre}!")


@router.get("/api/payments/failure")
def payment_failure(request: Request, db: Session = Depends(get_db)):
    """Callback cuando el pago falla."""
    return RedirectResponse(url="/admin/stats?premium=error")


@router.get("/api/payments/pending")
def payment_pending(request: Request, db: Session = Depends(get_db)):
    """Callback cuando el pago queda pendiente."""
    return RedirectResponse(url="/admin/stats?premium=pending")
