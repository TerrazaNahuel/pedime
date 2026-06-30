"""
Protección CSRF (Cross-Site Request Forgery) mediante Double Submit Cookie.

Genera un token único, lo guarda en cookie HttpOnly y lo inyecta en cada
formulario HTML. En cada POST valida que el token del formulario coincida
con el de la cookie.
"""

import os
import secrets

from fastapi import HTTPException, Request

# secure=True solo en producción (cuando ENVIRONMENT=production). En local HTTP sin HTTPS, secure=False.
_csrf_secure = os.getenv("ENVIRONMENT", "development") == "production"

COOKIE_CONFIG = {
    "httponly": True,
    "samesite": "lax",
    "max_age": 86400,
    "secure": _csrf_secure,
    "path": "/",
}


def csrf_token_response(response) -> str:
    """Genera un token CSRF, lo setea como cookie en la response y lo devuelve."""
    token = secrets.token_hex(32)
    response.set_cookie(key="csrf_token", value=token, **COOKIE_CONFIG)
    return token


def validate_csrf(request: Request, csrf_token: str):
    """Compara el token del formulario contra la cookie. Si no coinciden → 403."""
    cookie_token = request.cookies.get("csrf_token")
    if not cookie_token or not csrf_token or cookie_token != csrf_token:
        raise HTTPException(status_code=403, detail="CSRF token inválido")
