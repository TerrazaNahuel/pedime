"""
Rutas públicas del menú digital.

Sirve la página HTML del menú y la API JSON con los datos del comercio
(productos disponibles, categorías, configuración).
"""

import logging
import os

from database import get_db
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from models import Category, Product, Store
from schemas import CategoryOut, MenuResponse, ProductOut
from sqlalchemy.orm import Session

router = APIRouter()
logger = logging.getLogger("pedime.menu")

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")

# Cachea el HTML estático del menú en memoria con invalidación por mtime
_menu_html_cache = None
_menu_html_mtime = 0


def get_menu_html():
    """Lee y cachea el archivo menu.html. Invalida si el archivo cambió en disco."""
    global _menu_html_cache, _menu_html_mtime
    menu_path = os.path.join(FRONTEND_DIR, "menu.html")
    if not os.path.exists(menu_path):
        raise HTTPException(status_code=404, detail="Página de menú no encontrada")
    # Compara el mtime para invalidar el caché si el archivo se modificó
    current_mtime = os.path.getmtime(menu_path)
    if _menu_html_cache is None or current_mtime > _menu_html_mtime:
        with open(menu_path, encoding="utf-8") as f:
            _menu_html_cache = f.read()
        _menu_html_mtime = current_mtime
        logger.info("menu.html cachead en memoria")
    return _menu_html_cache


@router.get("/menu/{slug}", response_class=HTMLResponse)
def serve_menu(slug: str, db: Session = Depends(get_db)):
    """Sirve la página HTML del menú para el slug dado. 404 si el slug no existe."""
    store = db.query(Store).filter(Store.slug == slug).first()
    if not store or not store.is_active:
        raise HTTPException(status_code=404, detail="Comercio no encontrado")
    return get_menu_html()


@router.get("/api/menu/{slug}", response_model=MenuResponse)
def get_menu(slug: str, db: Session = Depends(get_db)):
    """
    API JSON del menú público.

    Retorna datos del store, categorías y productos disponibles.
    Solo incluye productos con available=True.
    """
    store = db.query(Store).filter(Store.slug == slug).first()
    if not store or not store.is_active:
        raise HTTPException(status_code=404, detail="Comercio no encontrado")

    # Carga todas las categorías del store
    categories = {c.id: c for c in db.query(Category).filter(Category.store_id == store.id).all()}

    # Carga solo productos disponibles, ordenados: destacados primero, luego sort_order
    products = (
        db.query(Product)
        .filter(
            Product.store_id == store.id,
            Product.available,
        )
        .order_by(Product.featured.desc(), Product.sort_order, Product.id)
        .all()
    )

    # Agrupa productos por categoría
    products_by_category = {}
    for p in products:
        products_by_category.setdefault(p.category_id, []).append(
            ProductOut(
                id=p.id,
                name=p.name,
                description=p.description or "",
                price=p.price,
                available=p.available,
                stock=p.stock or 0,
                image_url=p.image_url or "",
                category_id=p.category_id,
                variants=p.variants or "",
                featured=p.featured or False,
            )
        )

    categories_out = [
        CategoryOut(id=cat.id, name=cat.name, image_url=cat.image_url or "", products=products_by_category.get(cat.id, []))
        for cat in categories.values()
    ]

    return MenuResponse(
        store_name=store.name,
        store_slug=store.slug,
        whatsapp=store.whatsapp,
        delivery_available=store.delivery_available,
        delivery_price=store.delivery_price,
        payment_transfer=store.payment_transfer,
        payment_cash=store.payment_cash,
        primary_color=store.primary_color or "#10b981",
        logo_url=store.logo_url or "",
        opening_time=store.opening_time or "",
        closing_time=store.closing_time or "",
        working_days=store.working_days or "1,2,3,4,5,6,7",
        categories=categories_out,
    )
