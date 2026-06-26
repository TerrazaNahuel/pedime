"""
Rutas de autenticación: login y registro de comercios.

Incluye rate limiting, validación de password policy, protección CSRF,
y redacción de emails en logs por privacidad.
"""

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database import get_db
from models import Store
from passlib.hash import bcrypt
from csrf import validate_csrf, COOKIE_CONFIG
from ratelimit import RateLimiter
from routers.admin_base import templates
import logging
import secrets
import re

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
    token = secrets.token_hex(32)
    resp = templates.TemplateResponse(request, "login.html", {
        "error": None, "csrf_token": token,
    })
    resp.set_cookie(key="csrf_token", value=token, **COOKIE_CONFIG)
    return resp


@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """
    Procesa el formulario de login.
    Rate limit: 5 intentos por minuto por IP.
    """
    validate_csrf(request, csrf_token)
    ip = request.client.host if request.client else "unknown"
    if not rate_limiter.check(f"login:{ip}", max_attempts=5, window_seconds=60):
        logger.warning("Rate limit excedido para login ip=%s", ip)
        raise HTTPException(status_code=429, detail="Demasiados intentos. Esperá un minuto.")
    store = db.query(Store).filter(Store.email == email).first()
    if not store or not bcrypt.verify(password, store.password_hash):
        logger.warning("Login fallido para email=%s desde %s", redact_email(email), request.client.host if request.client else "?")
        token = secrets.token_hex(32)
        resp = templates.TemplateResponse(request, "login.html", {
            "error": "Email o contraseña incorrectos", "csrf_token": token,
        })
        resp.set_cookie(key="csrf_token", value=token, **COOKIE_CONFIG)
        return resp
    logger.info("Login exitoso store_id=%s email=%s", store.id, redact_email(email))
    # Regenera la sesión para prevenir session fixation
    request.session.clear()
    request.session["authenticated"] = True
    request.session["store_id"] = store.id
    return RedirectResponse(url="/admin/dashboard", status_code=302)


@router.get("/register")
def register_page(request: Request):
    """Muestra el formulario de registro."""
    if request.session.get("authenticated"):
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    token = secrets.token_hex(32)
    resp = templates.TemplateResponse(request, "register.html", {
        "error": None, "csrf_token": token,
    })
    resp.set_cookie(key="csrf_token", value=token, **COOKIE_CONFIG)
    return resp


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
        """Helper que renderiza register.html con un mensaje de error y nuevo CSRF."""
        token = secrets.token_hex(32)
        resp = templates.TemplateResponse(request, "register.html", {
            "error": msg, "csrf_token": token,
        })
        resp.set_cookie(key="csrf_token", value=token, **COOKIE_CONFIG)
        return resp

    ip = request.client.host if request.client else "unknown"
    if not rate_limiter.check(f"register:{ip}", max_attempts=3, window_seconds=300):
        logger.warning("Rate limit excedido para register ip=%s", ip)
        return render_error("Demasiados registros. Esperá 5 minutos.")

    # Validaciones de contraseña
    if password != confirm_password:
        return render_error("Las contraseñas no coinciden")
    if len(password) < 8:
        return render_error("La contraseña debe tener al menos 8 caracteres")
    if not re.search(r"[A-Z]", password):
        return render_error("La contraseña debe tener al menos una mayúscula")
    if not re.search(r"[a-z]", password):
        return render_error("La contraseña debe tener al menos una minúscula")
    if not re.search(r"\d", password):
        return render_error("La contraseña debe tener al menos un número")
    if len(password) > 128:
        return render_error("La contraseña es demasiado larga (máx. 128 caracteres)")

    # Validaciones de datos del comercio
    if len(name) > 100:
        return render_error("El nombre es demasiado largo (máx. 100 caracteres)")
    if len(email) > 200:
        return render_error("El email es demasiado largo (máx. 200 caracteres)")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return render_error("El formato del email no es válido")
    if len(whatsapp) > 50:
        return render_error("El número de WhatsApp es demasiado largo")
    if not re.match(r"^\d{10,15}$", re.sub(r"\D", "", whatsapp)):
        return render_error("El número de WhatsApp debe tener entre 10 y 15 dígitos")
    if len(slug) > 100:
        return render_error("El slug es demasiado largo (máx. 100 caracteres)")
    if not re.match(r"^[a-z0-9-]+$", slugify(slug)):
        return render_error("El slug solo puede contener letras, números y guiones")

    final_slug = slugify(slug)
    if not final_slug:
        return render_error("El slug no puede estar vacío")

    # Verifica unicidad de email y slug (atómicos en la DB con unique constraints)
    if db.query(Store).filter(Store.email == email).first():
        return render_error("Ya existe una cuenta con ese email")
    if db.query(Store).filter(Store.slug == final_slug).first():
        return render_error("Ese slug ya está en uso. Elegí otro.")

    # Crea el store y lo autentica automáticamente
    store = Store(
        name=name,
        slug=final_slug,
        email=email,
        password_hash=bcrypt.hash(password),
        whatsapp=whatsapp,
    )
    db.add(store)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_email = db.query(Store).filter(Store.email == email).first()
        if existing_email:
            return render_error("Ya existe una cuenta con ese email")
        return render_error("Ese slug ya está en uso. Elegí otro.")

    logger.info("Registro exitoso store_id=%s slug=%s email=%s", store.id, final_slug, redact_email(email))
    # Regenera la sesión
    request.session.clear()
    request.session["authenticated"] = True
    request.session["store_id"] = store.id
    return RedirectResponse(url="/admin/dashboard", status_code=302)
