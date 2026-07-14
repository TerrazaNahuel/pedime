"""
Validadores compartidos para evitar duplicación entre routers.

Cada función retorna un mensaje de error (str) si la validación falla,
o None si el valor es válido.
"""

import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
WHATSAPP_RE = re.compile(r"^\d{10,15}$")
URL_RE = re.compile(r"^https?://\S+$")

MAX_NAME_LEN = 100
MAX_EMAIL_LEN = 200
MAX_WHATSAPP_LEN = 50
MAX_URL_LEN = 500


def validate_name(name: str, entity: str = "El nombre") -> str | None:
    """Valida que el nombre no esté vacío ni exceda los 100 caracteres."""
    if len(name) > MAX_NAME_LEN:
        return f"{entity} es demasiado largo (máx. {MAX_NAME_LEN} caracteres)"
    if not name.strip():
        return f"{entity} no puede estar vacío"
    return None


def validate_email(email: str) -> str | None:
    """Valida formato y longitud del email."""
    if len(email) > MAX_EMAIL_LEN:
        return f"El email es demasiado largo (máx. {MAX_EMAIL_LEN} caracteres)"
    if not EMAIL_RE.match(email):
        return "El formato del email no es válido"
    return None


def validate_whatsapp(whatsapp: str) -> str | None:
    """Valida formato y longitud del número de WhatsApp."""
    if len(whatsapp) > MAX_WHATSAPP_LEN:
        return "El número de WhatsApp es demasiado largo"
    digits = re.sub(r"\D", "", whatsapp)
    if not WHATSAPP_RE.match(digits):
        return "El número de WhatsApp debe tener entre 10 y 15 dígitos"
    return None


def validate_url(url: str, field_name: str = "La URL") -> str | None:
    """Valida que una URL sea HTTP(S) o esté vacía. Rechaza javascript:."""
    if not url:
        return None
    if len(url) > MAX_URL_LEN:
        return f"{field_name} es demasiado larga (máx. {MAX_URL_LEN} caracteres)"
    if not URL_RE.match(url):
        return f"{field_name} no es válida"
    return None


def validate_password_match(p1: str, p2: str) -> str | None:
    """Valida que dos contraseñas coincidan."""
    if p1 != p2:
        return "Las contraseñas no coinciden"
    return None


def validate_not_empty(value: str, field_name: str) -> str | None:
    """Valida que un campo no esté vacío."""
    if not value or not value.strip():
        return f"{field_name} no puede estar vacío"
    return None
