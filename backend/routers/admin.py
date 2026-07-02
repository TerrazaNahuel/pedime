"""
Router principal del panel de administración.

Incluye los sub-routers de productos, categorías y settings.
Provee el dashboard principal y el logout.
"""

import secrets
from datetime import UTC, datetime, timedelta

from csrf import COOKIE_CONFIG, validate_csrf
from database import get_db
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from models import Category, PageView, Product, WhatsAppClick
from ratelimit import RateLimiter
from routers import admin_categories, admin_products, admin_settings
from routers.admin_base import get_authenticated_store, logger, templates
from sqlalchemy import func as db_func
from sqlalchemy.orm import Session

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


@router.get("/admin/stats")
def admin_stats(request: Request, db: Session = Depends(get_db)):
    """Panel de estadísticas del comercio autenticado."""
    store = get_authenticated_store(request, db)
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)

    # Page views
    views_total = db.query(db_func.count(PageView.id)).filter(PageView.store_id == store.id).scalar() or 0
    views_today = db.query(db_func.count(PageView.id)).filter(PageView.store_id == store.id, PageView.viewed_at >= today_start).scalar() or 0
    views_week = db.query(db_func.count(PageView.id)).filter(PageView.store_id == store.id, PageView.viewed_at >= week_start).scalar() or 0
    views_month = db.query(db_func.count(PageView.id)).filter(PageView.store_id == store.id, PageView.viewed_at >= month_start).scalar() or 0

    # WhatsApp clicks
    clicks_total = db.query(db_func.count(WhatsAppClick.id)).filter(WhatsAppClick.store_id == store.id).scalar() or 0
    clicks_today = db.query(db_func.count(WhatsAppClick.id)).filter(WhatsAppClick.store_id == store.id, WhatsAppClick.clicked_at >= today_start).scalar() or 0
    clicks_week = db.query(db_func.count(WhatsAppClick.id)).filter(WhatsAppClick.store_id == store.id, WhatsAppClick.clicked_at >= week_start).scalar() or 0
    clicks_month = db.query(db_func.count(WhatsAppClick.id)).filter(WhatsAppClick.store_id == store.id, WhatsAppClick.clicked_at >= month_start).scalar() or 0

    conversion = (clicks_total / views_total * 100) if views_total > 0 else 0

    token = secrets.token_hex(32)
    resp = templates.TemplateResponse(request, "stats.html", {
        "store": store, "csrf_token": token, "active_tab": "estadisticas",
        "views_total": views_total, "views_today": views_today,
        "views_week": views_week, "views_month": views_month,
        "clicks_total": clicks_total, "clicks_today": clicks_today,
        "clicks_week": clicks_week, "clicks_month": clicks_month,
        "conversion": conversion,
    })
    resp.set_cookie(key="csrf_token", value=token, **COOKIE_CONFIG)
    return resp


@router.get("/admin/dashboard")
def admin_dashboard(request: Request, msg: str = "", err: str = "", tab: str = "productos", db: Session = Depends(get_db)):
    """
    Dashboard principal del admin.
    Muestra productos (ordenados), categorías y configuración.
    Los parámetros msg/err permiten mostrar mensajes flash desde otros endpoints.
    tab: determina qué tab mostrar activa al cargar (productos, categorias, config).
    """
    store = get_authenticated_store(request, db)
    categories = db.query(Category).filter(Category.store_id == store.id).all()
    products = db.query(Product).filter(Product.store_id == store.id).order_by(Product.sort_order, Product.id).all()

    # Agrupa productos por categoría para vista colapsable
    category_products = {}
    for cat in categories:
        category_products[cat.id] = [p for p in products if p.category_id == cat.id]

    token = secrets.token_hex(32)
    base_url = str(request.base_url)
    if tab not in ("productos", "categorias", "config"):
        tab = "productos"
    resp = templates.TemplateResponse(request, "dashboard.html", {
        "store": store, "categories": categories, "products": products,
        "category_products": category_products,
        "csrf_token": token, "success": msg or None, "error": err or None,
        "base_url": base_url, "active_tab": tab,
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
