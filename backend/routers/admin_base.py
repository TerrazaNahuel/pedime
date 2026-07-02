"""
Dependencias compartidas por los routers de administración.

Provee el template engine, logger y la función de autenticación que
usan todos los endpoints del panel de admin.
"""

import logging
import os
from datetime import UTC, date, datetime

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from models import Category, Product, Store
from sqlalchemy.orm import Session
from backend.settings import MAX_CATEGORIES, MAX_PRODUCTS_PER_CATEGORY, PREMIUM_DURATION_DAYS
from csrf import COOKIE_CONFIG

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
    # Verificar expiración de premium
    if store.plan == "premium" and store.plan_expires_at:
        if date.today() > store.plan_expires_at.date():
            store.plan = "free"
            store.plan_expires_at = None
            db.commit()
    return store


def render_dashboard_html(request: Request, store: Store, db: Session, msg: str = "", err: str = "", tab: str = "productos") -> HTMLResponse:
    """Renderiza el HTML completo del dashboard con nuevo CSRF token. Usado por HTMX."""
    from models import Category, Product
    import secrets
    categories = db.query(Category).filter(Category.store_id == store.id).all()
    products = db.query(Product).filter(Product.store_id == store.id).order_by(Product.sort_order, Product.id).all()
    category_products = {}
    for cat in categories:
        category_products[cat.id] = [p for p in products if p.category_id == cat.id]
    token = secrets.token_hex(32)
    base_url = str(request.base_url)
    resp = templates.TemplateResponse(request, "dashboard.html", {
        "store": store, "categories": categories, "products": products,
        "category_products": category_products,
        "csrf_token": token, "success": msg or None, "error": err or None,
        "base_url": base_url, "active_tab": tab,
    })
    resp.set_cookie(key="csrf_token", value=token, **COOKIE_CONFIG)
    return resp


def check_plan_limit(store: Store, db: Session, category_id: int | None = None) -> str | None:
    if store.plan == "premium":
        return None
    if category_id is not None:
        prod_count = db.query(Product).filter(
            Product.category_id == category_id,
            Product.store_id == store.id,
        ).count()
        if prod_count >= MAX_PRODUCTS_PER_CATEGORY:
            return f"Plan free: máximo {MAX_PRODUCTS_PER_CATEGORY} productos por categoría. Actualizá a premium."
    else:
        cat_count = db.query(Category).filter(Category.store_id == store.id).count()
        if cat_count >= MAX_CATEGORIES:
            return f"Plan free: máximo {MAX_CATEGORIES} categorías. Actualizá a premium."
    return None
