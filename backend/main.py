"""
Punto de entrada de la aplicación FastAPI.

Configura middlewares (sesión, seguridad), rutas, manejo de errores,
inicialización de DB y seed data. Sirve el landing page y monta archivos
estáticos del frontend.
"""

import os
import sys
# Permite que los imports internos (routers, database, etc.) funcionen
# cuando se ejecuta desde la raíz del proyecto (Railway).
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
from alembic.config import Config
from alembic import command
from routers import menu_public, admin, auth, admin_super
from routers.admin_base import NotAuthenticatedException, templates
from dotenv import load_dotenv
from seed import seed_default_store
import logging
import secrets

load_dotenv()

# Configuración de logging estructurado
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("pedime")

# SECRET_KEY: primero intenta leer de .env, si no genera una temporal
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(64)
    logger.warning("SECRET_KEY no configurada en .env. Se generó una temporal.")

# Directorios del proyecto
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Evento lifespan: ejecuta migrations (Alembic) y seed data al arrancar."""
    try:
        alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "alembic.ini"))
        command.upgrade(alembic_cfg, "head")
        logger.info("Base de datos migrada (alembic upgrade head)")
    except Exception:
        logger.error("Error ejecutando migrations", exc_info=True)
        raise
    seed_default_store()
    yield


app = FastAPI(title="Pedime", lifespan=lifespan)

# Middleware de sesión: cookies firmadas con SECRET_KEY, 1 día de vida
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
            "script-src 'self' https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "img-src 'self' https: data:; "
            "object-src 'none'"
        )
        return response


app.add_middleware(SecurityHeadersMiddleware)

# Sirve archivos estáticos del frontend (HTML, JS, imágenes)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# Manejadores de errores
@app.exception_handler(NotAuthenticatedException)
async def not_authenticated_handler(request: Request, exc: NotAuthenticatedException):
    """Redirige a login si el usuario no está autenticado."""
    return RedirectResponse(url="/login", status_code=302)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    logger.warning("404 %s %s", request.method, request.url.path)
    return HTMLResponse(status_code=404, content="<h1>404 - Página no encontrada</h1>")


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    logger.error("500 %s %s: %s", request.method, request.url.path, str(exc))
    return HTMLResponse(status_code=500, content="<h1>500 - Error interno del servidor</h1>")


# Registro de routers
app.include_router(menu_public.router)
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(admin_super.router)


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    """Landing page principal."""
    return templates.TemplateResponse(request, "landing.html")
