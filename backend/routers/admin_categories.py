"""
CRUD de categorías del panel de administración.

Operaciones: crear, editar nombre y eliminar (con cascade a productos).
"""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
from models import Category
from routers.admin_base import get_authenticated_store, check_plan_limit, logger
from csrf import validate_csrf
import urllib.parse

router = APIRouter()


@router.post("/admin/category")
def create_category(request: Request, name: str = Form(...), csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """Crea una nueva categoría. Valida el nombre y los límites del plan."""
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)
    limit_err = check_plan_limit(store, db)
    if limit_err:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote(limit_err), status_code=302)
    if len(name) > 100:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("El nombre de la categoría es demasiado largo"), status_code=302)
    if not name.strip():
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("El nombre de la categoría no puede estar vacío"), status_code=302)
    db.add(Category(name=name, store_id=store.id))
    db.commit()
    logger.info("Categoría creada store_id=%s name=%s", store.id, name)
    return RedirectResponse(url="/admin/dashboard", status_code=302)


@router.post("/admin/category/{category_id}/edit")
def update_category(category_id: int, request: Request, name: str = Form(...), csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """Edita el nombre de una categoría."""
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)
    if len(name) > 100:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("El nombre de la categoría es demasiado largo"), status_code=302)
    if not name.strip():
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("El nombre de la categoría no puede estar vacío"), status_code=302)
    cat = db.query(Category).filter(Category.id == category_id, Category.store_id == store.id).first()
    if not cat:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("Categoría no encontrada"), status_code=302)
    logger.info("Categoría editada store_id=%s id=%s", store.id, category_id)
    cat.name = name
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=302)


@router.post("/admin/category/{category_id}/delete")
def delete_category(category_id: int, request: Request, csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """
    Elimina una categoría y todos sus productos (cascade).
    """
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)
    cat = db.query(Category).filter(Category.id == category_id, Category.store_id == store.id).first()
    if not cat:
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote("Categoría no encontrada"), status_code=302)
    logger.info("Categoría eliminada store_id=%s id=%s", store.id, category_id)
    db.delete(cat)
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=302)
