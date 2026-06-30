import secrets
import string

from csrf import COOKIE_CONFIG, validate_csrf
from database import get_db
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from models import Store
from passlib.hash import bcrypt
from ratelimit import RateLimiter
from routers.admin_base import (
    NotAuthenticatedException,
    NotAuthorizedException,
    get_authenticated_store,
    logger,
    templates,
)
from sqlalchemy.orm import Session

from backend.settings import SUPER_RESET_MAX_ATTEMPTS, SUPER_RESET_WINDOW_SECONDS

router = APIRouter()
reset_limiter = RateLimiter()


def get_super_admin_store(request: Request, db: Session) -> Store:
    store = get_authenticated_store(request, db)
    if not store.is_superadmin:
        raise NotAuthorizedException("No autorizado")
    return store


def _super_render(request, admin, db, **extra):
    stores = db.query(Store).order_by(Store.id).all()
    token = secrets.token_hex(32)
    ctx = {"store": admin, "stores": stores, "csrf_token": token}
    ctx.update(extra)
    resp = templates.TemplateResponse(request, "super_dashboard.html", ctx)
    resp.set_cookie(key="csrf_token", value=token, **COOKIE_CONFIG)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp


def _guard_super(request, db):
    try:
        return get_super_admin_store(request, db)
    except NotAuthenticatedException:
        raise
    except NotAuthorizedException:
        raise
    except Exception as exc:
        logger.error("Error inesperado en _guard_super", exc_info=True)
        raise NotAuthenticatedException() from exc


@router.get("/admin/super")
def super_dashboard(request: Request, db: Session = Depends(get_db)):
    try:
        admin = get_super_admin_store(request, db)
    except (NotAuthenticatedException, NotAuthorizedException):
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    return _super_render(request, admin, db)


@router.post("/admin/super/{store_id}/toggle-active")
def toggle_store_active(
    store_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    try:
        admin = _guard_super(request, db)
    except (NotAuthenticatedException, NotAuthorizedException):
        return RedirectResponse(url="/admin/dashboard", status_code=302)

    target = db.query(Store).filter(Store.id == store_id).first()
    if not target:
        return RedirectResponse(url="/admin/super?err=Store+no+encontrado", status_code=302)
    target.is_active = not target.is_active
    db.commit()
    logger.info("Super admin toggle active store_id=%s", store_id)
    return RedirectResponse(url="/admin/super", status_code=302)


@router.post("/admin/super/{store_id}/set-plan")
def set_store_plan(
    store_id: int,
    request: Request,
    plan: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    try:
        admin = _guard_super(request, db)
    except (NotAuthenticatedException, NotAuthorizedException):
        return RedirectResponse(url="/admin/dashboard", status_code=302)

    if plan not in ("free", "premium"):
        return RedirectResponse(url="/admin/super?err=Plan+invalido", status_code=302)

    target = db.query(Store).filter(Store.id == store_id).first()
    if not target:
        return RedirectResponse(url="/admin/super?err=Store+no+encontrado", status_code=302)
    target.plan = plan
    db.commit()
    logger.info("Super admin set plan store_id=%s", store_id)
    return RedirectResponse(url="/admin/super", status_code=302)


@router.post("/admin/super/{store_id}/make-superadmin")
def toggle_superadmin(
    store_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    try:
        admin = _guard_super(request, db)
    except (NotAuthenticatedException, NotAuthorizedException):
        return RedirectResponse(url="/admin/dashboard", status_code=302)

    target = db.query(Store).filter(Store.id == store_id).first()
    if not target:
        return RedirectResponse(url="/admin/super?err=Store+no+encontrado", status_code=302)
    if target.id == request.session.get("store_id"):
        return RedirectResponse(url="/admin/super?err=No+podes+sacarte+el+superadmin+a+vos+mismo", status_code=302)
    if target.is_superadmin:
        superadmin_count = db.query(Store).filter(Store.is_superadmin == True).count()
        if superadmin_count <= 1:
            return RedirectResponse(url="/admin/super?err=Debe+haber+al+menos+un+superadmin", status_code=302)
    target.is_superadmin = not target.is_superadmin
    db.commit()
    logger.info("Super admin toggle superadmin store_id=%s", store_id)
    return RedirectResponse(url="/admin/super", status_code=302)


@router.post("/admin/super/{store_id}/reset-password")
def reset_store_password(
    store_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    try:
        admin = _guard_super(request, db)
    except (NotAuthenticatedException, NotAuthorizedException):
        return RedirectResponse(url="/admin/dashboard", status_code=302)

    if not reset_limiter.check(f"reset_pw:{store_id}", SUPER_RESET_MAX_ATTEMPTS, SUPER_RESET_WINDOW_SECONDS):
        return RedirectResponse(url="/admin/super?err=Demasiados+reseteos+de+contraseña", status_code=429)

    target = db.query(Store).filter(Store.id == store_id).first()
    if not target:
        return RedirectResponse(url="/admin/super?err=Store+no+encontrado", status_code=302)

    alphabet = string.ascii_letters + string.digits
    new_password = "".join(secrets.choice(alphabet) for _ in range(12))
    target.password_hash = bcrypt.hash(new_password)
    db.commit()

    logger.info("Super admin reset password store_id=%s", store_id)

    return _super_render(request, admin, db, flash_password=new_password, flash_store_name=target.name)


@router.post("/admin/super/{store_id}/delete")
def delete_store(
    store_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    try:
        admin = _guard_super(request, db)
    except (NotAuthenticatedException, NotAuthorizedException):
        return RedirectResponse(url="/admin/dashboard", status_code=302)

    target = db.query(Store).filter(Store.id == store_id).first()
    if not target:
        return RedirectResponse(url="/admin/super?err=Store+no+encontrado", status_code=302)
    if target.id == request.session.get("store_id"):
        return RedirectResponse(url="/admin/super?err=No+podes+eliminarte+a+vos+mismo", status_code=302)
    if target.is_superadmin:
        return RedirectResponse(url="/admin/super?err=No+podes+eliminar+un+superadmin", status_code=302)
    logger.info("Super admin deleted store_id=%s", store_id)
    db.delete(target)
    db.commit()
    return RedirectResponse(url="/admin/super", status_code=302)
