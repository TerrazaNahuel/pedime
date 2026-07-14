"""
CRUD de categorías del panel de administración.

Operaciones: crear, editar nombre y eliminar (con cascade a productos).
"""

from csrf import validate_csrf
from database import get_db
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from models import Category
from routers.admin_base import (
    admin_error_response,
    check_plan_limit,
    get_authenticated_store,
    logger,
    render_dashboard_html,
)
from sqlalchemy.orm import Session
from validators import validate_name

router = APIRouter()


def _validate_category_name(name: str, store, exclude_id: int | None, db: Session) -> str | None:
    """Valida nombre de categoría: longitud, no vacío, y no duplicado."""
    err = validate_name(name, "El nombre de la categoría")
    if err:
        return err
    q = db.query(Category).filter(Category.name == name, Category.store_id == store.id)
    if exclude_id is not None:
        q = q.filter(Category.id != exclude_id)
    if q.first():
        return "Ya existe una categoría con ese nombre"
    return None


@router.post("/admin/category")
def create_category(request: Request, name: str = Form(...), csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """Crea una nueva categoría. Valida el nombre y los límites del plan."""
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)

    limit_err = check_plan_limit(store, db)
    if limit_err:
        return admin_error_response(request, store, db, limit_err, tab="categorias")
    name_err = _validate_category_name(name, store, None, db)
    if name_err:
        return admin_error_response(request, store, db, name_err, tab="categorias")
    db.add(Category(name=name, store_id=store.id))
    db.commit()
    logger.info("Categoría creada store_id=%s name=%s", store.id, name)
    if request.headers.get("HX-Request"):
        return render_dashboard_html(request, store, db, msg="Categoría creada", tab="categorias")
    return RedirectResponse(url="/admin/dashboard?tab=categorias", status_code=302)


@router.post("/admin/category/{category_id}/edit")
def update_category(category_id: int, request: Request, name: str = Form(...), image_url: str = Form(""), csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """Edita el nombre e imagen de una categoría."""
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)

    name_err = _validate_category_name(name, store, category_id, db)
    if name_err:
        return admin_error_response(request, store, db, name_err, tab="categorias")
    cat = db.query(Category).filter(Category.id == category_id, Category.store_id == store.id).first()
    if not cat:
        return admin_error_response(request, store, db, "Categoría no encontrada", tab="categorias")
    logger.info("Categoría editada store_id=%s id=%s", store.id, category_id)
    cat.name = name
    cat.image_url = image_url if image_url else ""
    db.commit()
    if request.headers.get("HX-Request"):
        return render_dashboard_html(request, store, db, msg="Categoría actualizada", tab="categorias")
    return RedirectResponse(url="/admin/dashboard?tab=categorias", status_code=302)


@router.post("/admin/category/{category_id}/delete")
def delete_category(category_id: int, request: Request, csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """
    Elimina una categoría y todos sus productos (cascade).
    """
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)

    cat = db.query(Category).filter(Category.id == category_id, Category.store_id == store.id).first()
    if not cat:
        return admin_error_response(request, store, db, "Categoría no encontrada", tab="categorias")
    logger.info("Categoría eliminada store_id=%s id=%s", store.id, category_id)
    db.delete(cat)
    db.commit()
    if request.headers.get("HX-Request"):
        return render_dashboard_html(request, store, db, msg="Categoría eliminada", tab="categorias")
    return RedirectResponse(url="/admin/dashboard?tab=categorias", status_code=302)
