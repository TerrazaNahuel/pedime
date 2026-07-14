"""
Router de superadministración.

Permite gestionar todos los comercios desde una cuenta superadmin:
activar/desactivar stores, cambiar planes, otorgar/quitar superadmin,
resetear contraseñas y eliminar comercios.
"""

from datetime import UTC, datetime, timedelta

from csrf import validate_csrf
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
    get_client_ip,
    logger,
    render_template_with_csrf,
)
from sqlalchemy.orm import Session

from backend.password import generate_secure_password
from backend.settings import PREMIUM_DURATION_DAYS, SUPER_RESET_MAX_ATTEMPTS, SUPER_RESET_WINDOW_SECONDS

router = APIRouter()
reset_limiter = RateLimiter()


def get_super_admin_store(request: Request, db: Session) -> Store:
    """Obtiene el store autenticado y verifica que sea superadmin. Lanza excepción si no."""
    store = get_authenticated_store(request, db)
    if not store.is_superadmin:
        raise NotAuthorizedException("No autorizado")
    return store


def _super_render(request, admin, db, **extra):
    """Renderiza el dashboard de superadmin con lista de stores y CSRF token."""
    stores = db.query(Store).order_by(Store.id).all()
    ctx = {"store": admin, "stores": stores}
    ctx.update(extra)
    resp = render_template_with_csrf(request, "super_dashboard.html", ctx)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp


def _guard_super(request, db):
    """Helper que envuelve get_super_admin_store para usar en endpoints POST."""
    return get_super_admin_store(request, db)


def _require_store(db: Session, store_id: int) -> Store | None:
    """Busca un store por ID o retorna None si no existe."""
    return db.query(Store).filter(Store.id == store_id).first()


@router.get("/admin/super")
def super_dashboard(request: Request, db: Session = Depends(get_db)):
    """Muestra el panel de superadministración con la lista de todos los comercios."""
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
    """Activa o desactiva un comercio. No permite auto-desactivarse."""
    validate_csrf(request, csrf_token)
    try:
        _guard_super(request, db)
    except (NotAuthenticatedException, NotAuthorizedException):
        return RedirectResponse(url="/admin/dashboard", status_code=302)

    target = _require_store(db, store_id)
    if not target:
        return RedirectResponse(url="/admin/super?err=Store+no+encontrado", status_code=302)
    if target.id == request.session.get("store_id"):
        return RedirectResponse(url="/admin/super?err=No+podes+desactivarte+a+vos+mismo", status_code=302)
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
    """Cambia el plan de un comercio (free/vip_basico/vip_premium). Si es VIP, establece fecha de expiración."""
    validate_csrf(request, csrf_token)
    try:
        _guard_super(request, db)
    except (NotAuthenticatedException, NotAuthorizedException):
        return RedirectResponse(url="/admin/dashboard", status_code=302)

    if plan not in ("free", "vip_basico", "vip_premium"):
        return RedirectResponse(url="/admin/super?err=Plan+invalido", status_code=302)

    target = _require_store(db, store_id)
    if not target:
        return RedirectResponse(url="/admin/super?err=Store+no+encontrado", status_code=302)
    target.plan = plan
    if plan in ("vip_basico", "vip_premium"):
        target.plan_expires_at = datetime.now(UTC) + timedelta(days=PREMIUM_DURATION_DAYS)
    else:
        target.plan_expires_at = None
    db.commit()
    logger.info("Super admin set plan store_id=%s plan=%s expires=%s", store_id, plan, target.plan_expires_at)
    return RedirectResponse(url="/admin/super", status_code=302)


@router.post("/admin/super/{store_id}/make-superadmin")
def toggle_superadmin(
    store_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Otorga o revoca permisos de superadmin a un comercio.
    No permite auto-sacarse el rol ni dejar cero superadmins.
    """
    validate_csrf(request, csrf_token)
    try:
        _guard_super(request, db)
    except (NotAuthenticatedException, NotAuthorizedException):
        return RedirectResponse(url="/admin/dashboard", status_code=302)

    target = _require_store(db, store_id)
    if not target:
        return RedirectResponse(url="/admin/super?err=Store+no+encontrado", status_code=302)
    if target.id == request.session.get("store_id"):
        return RedirectResponse(url="/admin/super?err=No+podes+sacarte+el+superadmin+a+vos+mismo", status_code=302)
    # Evita que se quede sin superadmins en el sistema
    if target.is_superadmin:
        superadmin_count = db.query(Store).filter(Store.is_superadmin).count()
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
    """Resetea la contraseña de un comercio a una segura generada aleatoriamente. Con rate limit por IP."""
    validate_csrf(request, csrf_token)
    try:
        admin = _guard_super(request, db)
    except (NotAuthenticatedException, NotAuthorizedException):
        return RedirectResponse(url="/admin/dashboard", status_code=302)

    admin_ip = get_client_ip(request)
    if not reset_limiter.check(f"reset_pw:{admin_ip}", SUPER_RESET_MAX_ATTEMPTS, SUPER_RESET_WINDOW_SECONDS):
        return RedirectResponse(url="/admin/super?err=Demasiados+reseteos+de+contraseña", status_code=429)

    target = _require_store(db, store_id)
    if not target:
        return RedirectResponse(url="/admin/super?err=Store+no+encontrado", status_code=302)

    new_password = generate_secure_password()
    target.password_hash = bcrypt.hash(new_password)
    db.commit()

    logger.info("Super admin reset password store_id=%s", store_id)

    # Muestra la nueva contraseña en el dashboard con flash_password
    return _super_render(request, admin, db, flash_password=new_password, flash_store_name=target.name)


@router.post("/admin/super/{store_id}/delete")
def delete_store(
    store_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    """Elimina un comercio del sistema. No permite auto-eliminarse ni borrar superadmins."""
    validate_csrf(request, csrf_token)
    try:
        _guard_super(request, db)
    except (NotAuthenticatedException, NotAuthorizedException):
        return RedirectResponse(url="/admin/dashboard", status_code=302)

    target = _require_store(db, store_id)
    if not target:
        return RedirectResponse(url="/admin/super?err=Store+no+encontrado", status_code=302)
    if target.id == request.session.get("store_id"):
        return RedirectResponse(url="/admin/super?err=No+podes+eliminarte+a+vos+mismo", status_code=302)
    if target.is_superadmin:
        superadmin_count = db.query(Store).filter(Store.is_superadmin).count()
        if superadmin_count <= 1:
            return RedirectResponse(url="/admin/super?err=Debe+haber+al+menos+un+superadmin", status_code=302)
    logger.info("Super admin deleted store_id=%s", store_id)
    db.delete(target)
    db.commit()
    return RedirectResponse(url="/admin/super", status_code=302)
