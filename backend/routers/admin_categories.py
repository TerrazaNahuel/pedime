"""
CRUD de categorías del panel de administración.

Operaciones: crear, editar nombre y eliminar (con cascade a productos).
"""

from csrf import validate_csrf
from database import get_db
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from models import Category
from routers.admin_base import admin_error_response, check_plan_limit, get_authenticated_store, logger, render_dashboard_html
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/admin/category")
def create_category(request: Request, name: str = Form(...), csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """Crea una nueva categoría. Valida el nombre y los límites del plan."""
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)

    limit_err = check_plan_limit(store, db)
    if limit_err:
        return admin_error_response(request, store, db, limit_err, tab="categorias")
    if len(name) > 100:
        return admin_error_response(request, store, db, "El nombre de la categoría es demasiado largo", tab="categorias")
    if not name.strip():
        return admin_error_response(request, store, db, "El nombre de la categoría no puede estar vacío", tab="categorias")
    # Verifica que no exista otra categoría con el mismo nombre en este store
    if db.query(Category).filter(Category.name == name, Category.store_id == store.id).first():
        return admin_error_response(request, store, db, "Ya existe una categoría con ese nombre", tab="categorias")
    db.add(Category(name=name, store_id=store.id))
    db.commit()
    logger.info("Categoría creada store_id=%s name=%s", store.id, name)
    if request.headers.get("HX-Request"):
        return render_dashboard_html(request, store, db, msg="Categoría creada", tab="categorias")
    return RedirectResponse(url="/admin/dashboard?tab=categorias", status_code=302)


@router.post("/admin/category/{category_id}/edit")
def update_category(category_id: int, request: Request, name: str = Form(...), csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """Edita el nombre de una categoría."""
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)

    if len(name) > 100:
        return admin_error_response(request, store, db, "El nombre de la categoría es demasiado largo", tab="categorias")
    if not name.strip():
        return admin_error_response(request, store, db, "El nombre de la categoría no puede estar vacío", tab="categorias")
    cat = db.query(Category).filter(Category.id == category_id, Category.store_id == store.id).first()
    if not cat:
        return admin_error_response(request, store, db, "Categoría no encontrada", tab="categorias")
    if db.query(Category).filter(Category.name == name, Category.store_id == store.id, Category.id != category_id).first():
        return admin_error_response(request, store, db, "Ya existe una categoría con ese nombre", tab="categorias")
    logger.info("Categoría editada store_id=%s id=%s", store.id, category_id)
    cat.name = name
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
