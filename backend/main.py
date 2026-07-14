"""
Punto de entrada de la aplicación FastAPI.

Configura middlewares (sesión, seguridad), rutas, manejo de errores,
inicialización de DB y seed data. Sirve el landing page y monta archivos
estáticos del frontend.
"""

# ──────────────────────────────────────────────────
# Imports del sistema y librerías externas
# ──────────────────────────────────────────────────
import os
import sys

# Permite que los imports internos (routers, database, etc.) funcionen
# cuando se ejecuta desde la raíz del proyecto (Railway).
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import logging
import secrets
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from database import get_db
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session
from routers import admin, admin_super, auth, menu_public, payments, tracking
from routers.admin_base import NotAuthenticatedException, NotAuthorizedException, templates
from seed import seed_default_store
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

# ──────────────────────────────────────────────────

load_dotenv()

# ──────────────────────────────────────────────────
# Configuración de logging estructurado
# ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("pedime")

# ──────────────────────────────────────────────────
# Configuración de la aplicación
# ──────────────────────────────────────────────────

# SECRET_KEY: obligatoria en .env. Sin ella la app no arranca.
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    msg = "SECRET_KEY no configurada. Creala con: python -c \"import secrets; print(secrets.token_hex(64))\""
    logger.critical(msg)
    raise RuntimeError(msg)

# Directorios del proyecto
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# ──────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Evento lifespan: ejecuta migrations (Alembic) y seed data al arrancar."""
    import sys as _sys
    _sys.stdout.flush()
    _sys.stderr.flush()
    logger.info("=== LIFESPAN START ===")
    logger.info("DATABASE_URL set: %s", "yes" if os.getenv("DATABASE_URL") else "no")
    logger.info("PORT: %s", os.getenv("PORT", "not set"))
    try:
        alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "alembic.ini"))
        command.upgrade(alembic_cfg, "head")
        logger.info("Base de datos migrada (alembic upgrade head)")
    except Exception:
        logger.error("Error ejecutando migrations", exc_info=True)
        _sys.stdout.flush()
        _sys.stderr.flush()
        raise
    try:
        seed_default_store()
        logger.info("Seed data ejecutado")
    except Exception:
        logger.warning("Error en seed (no crítico)", exc_info=True)
    logger.info("=== LIFESPAN READY ===")
    _sys.stdout.flush()
    _sys.stderr.flush()
    yield
    logger.info("=== LIFESPAN SHUTDOWN ===")


# Creación de la aplicación FastAPI
app = FastAPI(title="Pedime", lifespan=lifespan)


class TrustProxyMiddleware(BaseHTTPMiddleware):
    """Confía en headers X-Forwarded-* de Render para esquema HTTPS."""
    async def dispatch(self, request: Request, call_next):
        proto = request.headers.get("X-Forwarded-Proto", "")
        if proto == "https":
            request.scope["scheme"] = "https"
        return await call_next(request)


app.add_middleware(TrustProxyMiddleware)

# ──────────────────────────────────────────────────
# Middleware de sesión: cookies firmadas con SECRET_KEY, 1 día de vida
# ──────────────────────────────────────────────────
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=86400,
    same_site="lax",
    https_only=os.getenv("ENVIRONMENT") == "production",
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Agrega headers de seguridad a todas las respuestas."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' https: data:; "
            "object-src 'none'"
        )
        return response


app.add_middleware(SecurityHeadersMiddleware)

# ──────────────────────────────────────────────────
# Archivos estáticos del frontend
# ──────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# ──────────────────────────────────────────────────
# Manejadores de errores
# ──────────────────────────────────────────────────
@app.exception_handler(NotAuthenticatedException)
async def not_authenticated_handler(request: Request, exc: NotAuthenticatedException):
    """Redirige a login si el usuario no está autenticado."""
    return RedirectResponse(url="/login", status_code=302)


@app.exception_handler(NotAuthorizedException)
async def not_authorized_handler(request: Request, exc: NotAuthorizedException):
    """Redirige al dashboard si el usuario no tiene permisos."""
    return RedirectResponse(url="/admin/dashboard", status_code=302)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    logger.warning("404 %s %s", request.method, request.url.path)
    return templates.TemplateResponse(request, "404.html", status_code=404)


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    logger.error("500 %s %s: %s", request.method, request.url.path, str(exc))
    return templates.TemplateResponse(request, "500.html", status_code=500)


# ──────────────────────────────────────────────────
# Rutas: routers de la aplicación
# ──────────────────────────────────────────────────
app.include_router(menu_public.router)
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(admin_super.router)
app.include_router(tracking.router)
app.include_router(payments.router)

# ──────────────────────────────────────────────────
# Endpoints directos
# ──────────────────────────────────────────────────

@app.get("/health")
def health(db: Session = Depends(get_db)):
    """Health check: verifica DB y estado general."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        logger.error("Health check falló: %s", exc)
        return {"status": "error", "database": "disconnected"}, 503


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    """Landing page principal."""
    logger.info("Serving landing page, base_url=%s", request.base_url)
    return templates.TemplateResponse(request, "landing.html")
