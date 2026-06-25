"""
Configuración del comercio desde el panel de administración.

Permite actualizar nombre, email, WhatsApp, contraseña, delivery,
métodos de pago, personalización visual y horarios.
"""

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session
from database import get_db
from models import Store, Category, Product
from passlib.hash import bcrypt
from decimal import Decimal
from routers.admin_base import get_authenticated_store, templates, logger
from csrf import validate_csrf, COOKIE_CONFIG
from ratelimit import RateLimiter
import secrets
import re

router = APIRouter()

rate_limiter = RateLimiter()


@router.post("/admin/settings")
def update_settings(
    request: Request,
    name: str = Form(...),
    whatsapp: str = Form(...),
    email: str = Form(...),
    current_password: str = Form(""),
    new_password: str = Form(""),
    delivery_available: str = Form("0"),
    delivery_price: Decimal = Form(Decimal("0.00")),
    payment_transfer: str = Form("0"),
    payment_cash: str = Form("0"),
    primary_color: str = Form("#10b981"),
    logo_url: str = Form(""),
    opening_time: str = Form(""),
    closing_time: str = Form(""),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Actualiza la configuración del store autenticado.

    Validaciones incluidas:
      - Longitud de campos
      - Formato de email, WhatsApp, color hex, URL de logo
      - Password policy para cambio de contraseña
      - Coherencia de horarios (apertura/cierre)
    """
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)

    def render_with(msg=None, err=None):
        """Helper: renderiza el dashboard con mensaje flash y nuevo CSRF."""
        token = secrets.token_hex(32)
        resp = templates.TemplateResponse(request, "dashboard.html", {
            "store": store,
            "categories": db.query(Category).filter(Category.store_id == store.id).all(),
            "products": db.query(Product).filter(Product.store_id == store.id).order_by(Product.sort_order, Product.id).all(),
            "csrf_token": token, "success": msg, "error": err,
        })
        resp.set_cookie(key="csrf_token", value=token, **COOKIE_CONFIG)
        return resp

    # Validaciones de datos básicos
    if len(name) > 100:
        return render_with(err="El nombre es demasiado largo (máx. 100 caracteres)")
    if len(whatsapp) > 50:
        return render_with(err="El número de WhatsApp es demasiado largo")
    if not re.match(r"^\d{10,15}$", re.sub(r"\D", "", whatsapp)):
        return render_with(err="El número de WhatsApp debe tener entre 10 y 15 dígitos")
    if len(email) > 200:
        return render_with(err="El email es demasiado largo (máx. 200 caracteres)")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return render_with(err="El formato del email no es válido")
    if db.query(Store).filter(Store.email == email, Store.id != store.id).first():
        return render_with(err="Ese email ya está en uso por otro comercio")

    # Cambio de contraseña (opcional) — con rate limit
    if current_password and new_password:
        rate_key = f"password_change:{store.id}"
        if not rate_limiter.check(rate_key, max_attempts=5, window_seconds=60):
            return render_with(err="Demasiados intentos de cambio de contraseña. Esperá un minuto.")
        if not bcrypt.verify(current_password, store.password_hash):
            return render_with(err="Contraseña actual incorrecta")
        if len(new_password) < 8:
            return render_with(err="La nueva contraseña debe tener al menos 8 caracteres")
        if not re.search(r"[A-Z]", new_password):
            return render_with(err="La nueva contraseña debe tener al menos una mayúscula")
        if not re.search(r"[a-z]", new_password):
            return render_with(err="La nueva contraseña debe tener al menos una minúscula")
        if not re.search(r"\d", new_password):
            return render_with(err="La nueva contraseña debe tener al menos un número")
        if len(new_password) > 128:
            return render_with(err="La nueva contraseña es demasiado larga (máx. 128 caracteres)")
        store.password_hash = bcrypt.hash(new_password)

    # Validación de precio de envío
    if delivery_price < 0:
        return render_with(err="El costo de envío no puede ser negativo")

    # Validaciones visuales
    if not re.match(r"^#[0-9a-fA-F]{6}$", primary_color):
        return render_with(err="El color primario debe ser un hex válido (ej: #10b981)")
    if logo_url and not re.match(r"^https?://\S+$", logo_url):
        return render_with(err="La URL del logo no es válida")
    if len(logo_url) > 500:
        return render_with(err="La URL del logo es demasiado larga (máx. 500 caracteres)")

    # Validación de horario: formato HH:MM y coherencia
    TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
    if opening_time and not TIME_RE.match(opening_time):
        return render_with(err="El horario de apertura debe tener formato HH:MM (ej: 09:00)")
    if closing_time and not TIME_RE.match(closing_time):
        return render_with(err="El horario de cierre debe tener formato HH:MM (ej: 18:00)")
    if (opening_time and not closing_time) or (closing_time and not opening_time):
        return render_with(err="Si configurás horario, completá apertura y cierre")
    if opening_time and closing_time and opening_time == closing_time:
        return render_with(err="El horario de apertura y cierre no pueden ser iguales")

    # Aplica los cambios
    store.name = name
    store.whatsapp = whatsapp
    store.email = email
    store.delivery_available = (delivery_available == "1")
    store.delivery_price = delivery_price
    store.payment_transfer = (payment_transfer == "1")
    store.payment_cash = (payment_cash == "1")
    store.primary_color = primary_color
    store.logo_url = logo_url
    store.opening_time = opening_time
    store.closing_time = closing_time
    db.commit()

    logger.info("Configuración actualizada store_id=%s", store.id)
    return render_with(msg="Configuración guardada")
