"""
Dependencias compartidas por los routers de administración.

Provee el template engine, logger y la función de autenticación que
usan todos los endpoints del panel de admin.
"""

import logging
import os
import secrets
import urllib.parse
from datetime import UTC, datetime

from csrf import COOKIE_CONFIG
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from models import Category, Product, Store
from sqlalchemy.orm import Session

from backend.settings import MAX_CATEGORIES_FREE, MAX_CATEGORIES_VIP, MAX_PRODUCTS_PER_CATEGORY

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.globals["now"] = lambda: datetime.now(UTC)

logger = logging.getLogger("pedime.admin")


class NotAuthenticatedException(Exception):
    """Se lanza cuando un usuario no autenticado intenta acceder al admin."""
    pass


class NotAuthorizedException(Exception):
    """Se lanza cuando un usuario no tiene permisos suficientes."""
    pass


def get_client_ip(request: Request) -> str:
    """Obtiene la IP real del cliente. TrustProxyMiddleware ya resuelve X-Forwarded-For."""
    return request.client.host if request.client else "unknown"


def get_authenticated_store(request: Request, db: Session) -> Store:
    """
    Obtiene el store autenticado desde la sesión.
    Si no hay sesión válida, lanza NotAuthenticatedException.
    Verifica expiración del plan premium.
    """
    store_id = request.session.get("store_id")
    authenticated = request.session.get("authenticated")
    if not authenticated or not store_id:
        raise NotAuthenticatedException()
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store or store.is_active is False:
        raise NotAuthenticatedException()
    # Migrar plan legacy "premium" → "vip_basico"
    if store.plan == "premium":
        store.plan = "vip_basico"
        db.commit()
        logger.info("Plan migrado: store_id=%s premium -> vip_basico", store.id)
    # Verificar expiración de planes VIP
    if store.plan in ("vip_basico", "vip_premium") and store.plan_expires_at:
        if datetime.now(UTC).date() > store.plan_expires_at.date():
            store.plan = "free"
            store.plan_expires_at = None
            db.commit()
            logger.info("Plan expirado: store_id=%s vuelve a free", store.id)
    return store


def render_template_with_csrf(request: Request, template_name: str, context: dict) -> HTMLResponse:
    """Renderiza una plantilla Jinja2 con un nuevo token CSRF en cookie y contexto."""
    token = secrets.token_hex(32)
    context["csrf_token"] = token
    resp = templates.TemplateResponse(request, template_name, context)
    resp.set_cookie(key="csrf_token", value=token, **COOKIE_CONFIG)
    return resp


def render_dashboard_html(request: Request, store: Store, db: Session, msg: str = "", err: str = "", tab: str = "productos") -> HTMLResponse:
    """Renderiza el HTML completo del dashboard con nuevo CSRF token. Usado por HTMX."""
    categories = db.query(Category).filter(Category.store_id == store.id).all()
    products = db.query(Product).filter(Product.store_id == store.id).order_by(Product.sort_order, Product.id).all()
    category_products = {}
    for p in products:
        category_products.setdefault(p.category_id, []).append(p)
    base_url = str(request.base_url)
    return render_template_with_csrf(request, "dashboard.html", {
        "store": store, "categories": categories, "products": products,
        "category_products": category_products,
        "success": msg or None, "error": err or None,
        "base_url": base_url, "active_tab": tab,
    })


def admin_error_response(request: Request, store: Store, db: Session, msg: str, tab: str = "productos") -> HTMLResponse | RedirectResponse:
    """Helper compartido para responder con error en admin, compatible con HTMX y sin JS."""
    return _respond(request, store, db, msg=msg, tab=tab, is_error=True)


def respond_ok(request: Request, store: Store, db: Session, msg: str, tab: str = "productos") -> HTMLResponse | RedirectResponse:
    """Respuesta de éxito para operaciones admin: HTMX render o redirect con mensaje."""
    return _respond(request, store, db, msg=msg, tab=tab)


def _respond(request: Request, store: Store, db: Session, msg: str, tab: str = "productos", is_error: bool = False) -> HTMLResponse | RedirectResponse:
    """Respuesta unificada: HTMX render o redirect, usada por todos los endpoints admin."""
    if request.headers.get("HX-Request"):
        return render_dashboard_html(request, store, db, err=msg if is_error else "", msg="" if is_error else msg, tab=tab)
    tab_param = f"&tab={tab}" if tab != "productos" else ""
    key = "err" if is_error else "msg"
    return RedirectResponse(url=f"/admin/dashboard?{key}={urllib.parse.quote(msg)}{tab_param}", status_code=302)


def check_plan_limit(store: Store, db: Session, category_id: int | None = None, exclude_product_id: int | None = None) -> str | None:
    """
    Verifica los límites del plan (categorías o productos por categoría).
    Retorna un mensaje de error si se excede el límite, o None si está ok.
    Si category_id se pasa, verifica productos en esa categoría; si no, verifica categorías totales.
    exclude_product_id permite excluir un producto del conteo (útil al editar).
    """
    if store.plan == "vip_premium":
        return None  # Sin límites
    if category_id is not None:
        # Verificar límite de productos por categoría
        if store.plan == "free":
            q = db.query(Product).filter(
                Product.category_id == category_id,
                Product.store_id == store.id,
            )
            if exclude_product_id is not None:
                q = q.filter(Product.id != exclude_product_id)
            prod_count = q.count()
            if prod_count >= MAX_PRODUCTS_PER_CATEGORY:
                return f"Plan free: máximo {MAX_PRODUCTS_PER_CATEGORY} productos por categoría. Actualizá a un plan VIP."
        # VIP Básico y Premium: items sin límite por categoría
        return None
    else:
        # Verificar límite de categorías totales
        cat_count = db.query(Category).filter(Category.store_id == store.id).count()
        if store.plan == "free":
            if cat_count >= MAX_CATEGORIES_FREE:
                return f"Plan free: máximo {MAX_CATEGORIES_FREE} categorías. Actualizá a un plan VIP."
        elif store.plan == "vip_basico":
            if cat_count >= MAX_CATEGORIES_VIP:
                return f"Plan VIP Básico: máximo {MAX_CATEGORIES_VIP} categorías. Actualizá a VIP Premium."
    return None
