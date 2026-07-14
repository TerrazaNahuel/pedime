"""
Rutas de autenticación: login y registro de comercios.

Incluye rate limiting, validación de password policy, protección CSRF,
y redacción de emails en logs por privacidad.
"""

import logging
import re

from csrf import csrf_token_response, validate_csrf
from database import get_db
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from models import Store
from passlib.hash import bcrypt
from ratelimit import RateLimiter
from routers.admin_base import get_client_ip, render_template_with_csrf
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from validators import validate_email, validate_name, validate_password_match, validate_whatsapp

from backend.password import validate_password
from backend.settings import (
    LOGIN_MAX_ATTEMPTS,
    LOGIN_WINDOW_SECONDS,
    REGISTER_MAX_ATTEMPTS,
    REGISTER_WINDOW_SECONDS,
)

router = APIRouter()
logger = logging.getLogger("pedime.auth")

rate_limiter = RateLimiter()


def redact_email(email: str) -> str:
    """Ofusca el email en logs por privacidad: a***l@ejemplo.com."""
    at = email.find("@")
    if at < 0:
        return "***"
    if at < 2:
        return "***@" + email[at + 1:]
    return email[0] + "***" + email[at - 1:]


def slugify(text: str) -> str:
    """Convierte un texto en un slug URL-friendly: solo letras, números y guiones."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


@router.get("/login")
def login_page(request: Request):
    """Muestra el formulario de login. Si ya está autenticado, redirige al dashboard."""
    if request.session.get("authenticated"):
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    return render_template_with_csrf(request, "login.html", {"error": None})


@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """Procesa el formulario de login. Rate limit: 5 intentos por minuto por IP."""
    validate_csrf(request, csrf_token)
    email = email.lower().strip()
    ip = get_client_ip(request)
    if not rate_limiter.check(f"login:{ip}", max_attempts=LOGIN_MAX_ATTEMPTS, window_seconds=LOGIN_WINDOW_SECONDS):
        logger.warning("Rate limit excedido para login ip=%s", ip)
        raise HTTPException(status_code=429, detail="Demasiados intentos. Esperá un minuto.")
    store = db.query(Store).filter(Store.email == email).first()
    if not store or not bcrypt.verify(password, store.password_hash):
        logger.warning("Login fallido para email=%s desde %s", redact_email(email), request.client.host if request.client else "?")
        return render_template_with_csrf(request, "login.html", {"error": "Email o contraseña incorrectos"})
    logger.info("Login exitoso store_id=%s email=%s", store.id, redact_email(email))
    request.session.clear()
    request.session["authenticated"] = True
    request.session["store_id"] = store.id
    resp = RedirectResponse(url="/admin/dashboard", status_code=302)
    csrf_token_response(resp)
    return resp


@router.get("/register")
def register_page(request: Request):
    """Muestra el formulario de registro."""
    if request.session.get("authenticated"):
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    return render_template_with_csrf(request, "register.html", {"error": None})


@router.post("/register")
def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    whatsapp: str = Form(...),
    slug: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Procesa el formulario de registro.
    Rate limit: 3 registros cada 5 minutos por IP.
    Validaciones: password policy, formato email, whatsapp, slug único.
    """
    validate_csrf(request, csrf_token)

    def render_error(msg):
        return render_template_with_csrf(request, "register.html", {"error": msg})

    ip = get_client_ip(request)
    if not rate_limiter.check(f"register:{ip}", max_attempts=REGISTER_MAX_ATTEMPTS, window_seconds=REGISTER_WINDOW_SECONDS):
        logger.warning("Rate limit excedido para register ip=%s", ip)
        return render_error("Demasiados registros. Esperá 5 minutos.")

    # Validaciones de contraseña
    pw_match_err = validate_password_match(password, confirm_password)
    if pw_match_err:
        return render_error(pw_match_err)
    pw_err = validate_password(password)
    if pw_err:
        return render_error(pw_err)

    email = email.lower().strip()

    # Validaciones de datos del comercio
    name_err = validate_name(name, "El nombre")
    if name_err:
        return render_error(name_err)
    email_err = validate_email(email)
    if email_err:
        return render_error(email_err)
    whatsapp_err = validate_whatsapp(whatsapp)
    if whatsapp_err:
        return render_error(whatsapp_err)
    if len(slug) > 100:
        return render_error("El slug es demasiado largo (máx. 100 caracteres)")
    if not re.match(r"^[a-z0-9-]+$", slugify(slug)):
        return render_error("El slug solo puede contener letras, números y guiones")

    final_slug = slugify(slug)
    if not final_slug:
        return render_error("El slug no puede estar vacío")

    # Crea el store y lo autentica automáticamente
    store = Store(
        name=name,
        slug=final_slug,
        email=email,
        password_hash=bcrypt.hash(password),
        whatsapp=re.sub(r"\D", "", whatsapp),
    )
    db.add(store)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return render_error("El email o slug ya está en uso")

    logger.info("Registro exitoso store_id=%s slug=%s email=%s", store.id, final_slug, redact_email(email))
    # Regenera la sesión
    request.session.clear()
    request.session["authenticated"] = True
    request.session["store_id"] = store.id
    return RedirectResponse(url="/admin/dashboard", status_code=302)
