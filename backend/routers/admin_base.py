"""
Dependencias compartidas por los routers de administración.

Provee el template engine, logger y la función de autenticación que
usan todos los endpoints del panel de admin.
"""

import logging
import os
from datetime import UTC, datetime

from fastapi import Request
from fastapi.templating import Jinja2Templates
from models import Category, Product, Store
from sqlalchemy.orm import Session
from backend.settings import MAX_CATEGORIES, MAX_PRODUCTS_PER_CATEGORY

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
    """
    store_id = request.session.get("store_id")
    authenticated = request.session.get("authenticated")
    if not authenticated or not store_id:
        raise NotAuthenticatedException()
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store or store.is_active is False:
        raise NotAuthenticatedException()
    return store


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
