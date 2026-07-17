"""
CRUD de categorías del panel de administración.

Operaciones: crear, editar nombre y eliminar (con cascade a productos).
"""

from csrf import validate_csrf
from database import get_db
from fastapi import APIRouter, Depends, Form, Request
from models import Category
from routers.admin_base import (
    admin_error_response,
    check_plan_limit,
    get_authenticated_store,
    logger,
    respond_ok,
)
from sqlalchemy.orm import Session
from validators import validate_name, validate_url

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
    return respond_ok(request, store, db, "Categoría creada", tab="categorias")


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
    if image_url:
        url_err = validate_url(image_url, "La URL de la imagen")
        if url_err:
            return admin_error_response(request, store, db, url_err, tab="categorias")
    logger.info("Categoría editada store_id=%s id=%s", store.id, category_id)
    cat.name = name
    cat.image_url = image_url if image_url else ""
    db.commit()
    return respond_ok(request, store, db, "Categoría actualizada", tab="categorias")


@router.post("/admin/category/{category_id}/delete")
def delete_category(category_id: int, request: Request, csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """Elimina una categoría y todos sus productos (cascade)."""
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)

    cat = db.query(Category).filter(Category.id == category_id, Category.store_id == store.id).first()
    if not cat:
        return admin_error_response(request, store, db, "Categoría no encontrada", tab="categorias")
    logger.info("Categoría eliminada store_id=%s id=%s", store.id, category_id)
    db.delete(cat)
    db.commit()
    return respond_ok(request, store, db, "Categoría eliminada", tab="categorias")
