"""
Configuración del comercio desde el panel de administración.

Permite actualizar nombre, email, WhatsApp, contraseña, delivery,
métodos de pago, personalización visual y horarios.
"""

import re
from decimal import Decimal

from csrf import validate_csrf
from database import get_db
from fastapi import APIRouter, Depends, Form, Request
from models import Store
from passlib.hash import bcrypt
from ratelimit import RateLimiter
from routers.admin_base import get_authenticated_store, logger, render_dashboard_html
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from validators import validate_email, validate_name, validate_password_match, validate_url, validate_whatsapp

from backend.password import validate_password
from backend.settings import PASSWORD_CHANGE_MAX_ATTEMPTS, PASSWORD_CHANGE_WINDOW_SECONDS

router = APIRouter()

rate_limiter = RateLimiter()


@router.post("/admin/settings")
def     update_settings(
    request: Request,
    name: str = Form(...),
    whatsapp: str = Form(...),
    email: str = Form(...),
    current_password: str = Form(""),
    new_password: str = Form(""),
    confirm_new_password: str = Form(""),
    delivery_available: str = Form("0"),
    delivery_price: Decimal = Form(Decimal("0.00")),
    payment_transfer: str = Form("0"),
    payment_cash: str = Form("0"),
    primary_color: str = Form("#10b981"),
    logo_url: str = Form(""),
    opening_time: str = Form(""),
    closing_time: str = Form(""),
    working_days: list[str] = Form([]),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)

    def render_with(msg=None, err=None):
        return render_dashboard_html(request, store, db, msg=msg or "", err=err or "", tab="config")

    if delivery_price < 0:
        return render_with(err="El costo de envío no puede ser negativo")
    if delivery_price > 999_999.99:
        return render_with(err="El costo de envío es demasiado alto")
    err = _validate_basic_fields(name, whatsapp, email, db, store)
    if err:
        return render_with(err=err)
    err = _validate_settings_visuals(primary_color, logo_url, opening_time, closing_time, working_days)
    if err:
        return render_with(err=err)
    err = _handle_password_change(store, current_password, new_password, confirm_new_password)
    if err:
        return render_with(err=err)

    store.name = name
    store.whatsapp = re.sub(r"\D", "", whatsapp)
    store.email = email
    store.delivery_available = (delivery_available == "1")
    store.delivery_price = delivery_price
    store.payment_transfer = (payment_transfer == "1")
    store.payment_cash = (payment_cash == "1")
    store.primary_color = primary_color
    store.logo_url = logo_url
    store.opening_time = opening_time
    store.closing_time = closing_time
    store.working_days = ",".join(working_days) if working_days else "1,2,3,4,5,6,7"
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return render_with(err="Ese email ya está en uso por otro comercio")

    logger.info("Configuración actualizada store_id=%s", store.id)
    return render_with(msg="Configuración guardada")


def _validate_basic_fields(name: str, whatsapp: str, email: str, db: Session, store: Store) -> str | None:
    name_err = validate_name(name, "El nombre")
    if name_err:
        return name_err
    whatsapp_err = validate_whatsapp(whatsapp)
    if whatsapp_err:
        return whatsapp_err
    email_err = validate_email(email)
    if email_err:
        return email_err
    if db.query(Store).filter(Store.email == email, Store.id != store.id).first():
        return "Ese email ya está en uso por otro comercio"
    return None


def _validate_settings_visuals(primary_color: str, logo_url: str, opening_time: str, closing_time: str, working_days: list[str]) -> str | None:
    if not re.match(r"^#[0-9a-fA-F]{6}$", primary_color):
        return "El color primario debe ser un hex válido (ej: #10b981)"
    url_err = validate_url(logo_url, "La URL del logo")
    if url_err:
        return url_err
    time_re = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
    if opening_time and not time_re.match(opening_time):
        return "El horario de apertura debe tener formato HH:MM (ej: 09:00)"
    if closing_time and not time_re.match(closing_time):
        return "El horario de cierre debe tener formato HH:MM (ej: 18:00)"
    if (opening_time and not closing_time) or (closing_time and not opening_time):
        return "Si configurás horario, completá apertura y cierre"
    if opening_time and closing_time and opening_time == closing_time:
        return "El horario de apertura y cierre no pueden ser iguales"
    if working_days:
        if not all(p.isdigit() and 1 <= int(p) <= 7 for p in working_days):
            return "Los días laborales deben ser números del 1 al 7"
    return None


def _handle_password_change(store: Store, current_password: str, new_password: str, confirm_new_password: str) -> str | None:
    if not current_password and not new_password:
        return None
    rate_key = f"password_change:{store.id}"
    if not rate_limiter.check(rate_key, max_attempts=PASSWORD_CHANGE_MAX_ATTEMPTS, window_seconds=PASSWORD_CHANGE_WINDOW_SECONDS):
        return "Demasiados intentos de cambio de contraseña. Esperá un minuto."
    if not bcrypt.verify(current_password, store.password_hash):
        return "Contraseña actual incorrecta"
    pwd_err = validate_password_match(new_password, confirm_new_password)
    if pwd_err:
        return pwd_err
    pw_err = validate_password(new_password, "La nueva contraseña")
    if pw_err:
        return pw_err
    store.password_hash = bcrypt.hash(new_password)
    return None
