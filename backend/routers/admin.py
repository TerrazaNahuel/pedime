"""
Router principal del panel de administración.

Incluye los sub-routers de productos, categorías y settings.
Provee el dashboard principal y el logout.
"""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import Store, Category, Product
from routers.admin_base import get_authenticated_store, templates, logger
from routers import admin_products, admin_categories, admin_settings
from csrf import validate_csrf, COOKIE_CONFIG
from ratelimit import RateLimiter
import secrets

router = APIRouter()
logout_limiter = RateLimiter()

# Sub-routers de funcionalidades del admin
router.include_router(admin_products.router)
router.include_router(admin_categories.router)
router.include_router(admin_settings.router)


@router.get("/admin")
def admin_root(request: Request):
    """Redirige al dashboard o al login según si hay sesión activa."""
    if request.session.get("authenticated") and request.session.get("store_id"):
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    return RedirectResponse(url="/login", status_code=302)


@router.get("/admin/dashboard")
def admin_dashboard(request: Request, msg: str = "", err: str = "", db: Session = Depends(get_db)):
    """
    Dashboard principal del admin.
    Muestra productos (ordenados), categorías y configuración.
    Los parámetros msg/err permiten mostrar mensajes flash desde otros endpoints.
    """
    store = get_authenticated_store(request, db)
    categories = db.query(Category).filter(Category.store_id == store.id).all()
    products = db.query(Product).filter(Product.store_id == store.id).order_by(Product.sort_order, Product.id).all()
    token = secrets.token_hex(32)
    base_url = str(request.base_url)
    resp = templates.TemplateResponse(request, "dashboard.html", {
        "store": store, "categories": categories, "products": products,
        "csrf_token": token, "success": msg or None, "error": err or None,
        "base_url": base_url,
    })
    resp.set_cookie(key="csrf_token", value=token, **COOKIE_CONFIG)
    return resp


@router.post("/admin/logout")
def admin_logout(request: Request, csrf_token: str = Form(...)):
    """Cierra la sesión del admin y redirige al inicio."""
    validate_csrf(request, csrf_token)
    if not logout_limiter.check(f"logout:{request.client.host}", 10, 60):
        return RedirectResponse(url="/admin/dashboard", status_code=429)
    store_id = request.session.get("store_id")
    logger.info("Logout store_id=%s", store_id)
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)
