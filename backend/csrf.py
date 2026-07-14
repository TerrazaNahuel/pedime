"""
Protección CSRF (Cross-Site Request Forgery) mediante Double Submit Cookie.

Genera un token único, lo guarda en cookie HttpOnly y lo inyecta en cada
formulario HTML. En cada POST valida que el token del formulario coincida
con el de la cookie.
"""

import os
import secrets

from fastapi import HTTPException, Request

# secure=True solo en producción (cuando ENVIRONMENT=production).
# En local HTTP sin HTTPS, secure=False para evitar problemas de cookie.
_csrf_secure = os.getenv("ENVIRONMENT", "development") == "production"

# Configuración de la cookie CSRF: HttpOnly, SameSite=Lax, 24h de vida
COOKIE_CONFIG = {
    "httponly": True,      # No accesible desde JavaScript
    "samesite": "lax",     # Protege contra CSRF sin romper navegación normal
    "max_age": 86400,      # 24 horas en segundos
    "secure": _csrf_secure, # Solo enviar por HTTPS en producción
    "path": "/",           # Disponible en toda la aplicación
}


def csrf_token_response(response) -> str:
    """
    Genera un token CSRF, lo setea como cookie en la response y lo devuelve.

    Args:
        response: Objeto response de FastAPI/Starlette donde se setea la cookie.

    Returns:
        str con el token generado (para insertar en formularios HTML).
    """
    token = secrets.token_hex(32)  # 64 caracteres hex, criptográficamente seguro
    response.set_cookie(key="csrf_token", value=token, **COOKIE_CONFIG)
    return token


def validate_csrf(request: Request, csrf_token: str):
    """
    Valida el token CSRF comparando el token del formulario contra la cookie.

    Args:
        request: Objeto Request de FastAPI para leer cookies.
        csrf_token: Token enviado desde el formulario HTML.

    Raises:
        HTTPException 403 si el token no coincide o falta.
    """
    cookie_token = request.cookies.get("csrf_token")
    if not cookie_token or not csrf_token or cookie_token != csrf_token:
        raise HTTPException(status_code=403, detail="CSRF token inválido")
