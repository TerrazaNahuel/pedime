"""
Validación y generación de contraseñas seguras.

Define la política de contraseñas (mín. 8 chars, mayúscula, minúscula,
número y carácter especial) y provee un generador criptográficamente seguro.
"""

import re
import secrets
import string


def validate_password(password: str, field_name: str = "Contraseña") -> str | None:
    """
    Valida una contraseña contra la política de seguridad.

    Comprueba:
      - Longitud mínima de 8 caracteres
      - Longitud máxima de 128 caracteres
      - Al menos una mayúscula, una minúscula, un dígito y un carácter especial

    Args:
        password: Contraseña a validar.
        field_name: Nombre del campo para el mensaje de error (default "Contraseña").

    Returns:
        str con el mensaje de error si la validación falla, o None si es válida.
    """
    if len(password) < 8:
        return f"{field_name} debe tener al menos 8 caracteres"
    if len(password) > 128:
        return f"{field_name} es demasiado larga (máx. 128 caracteres)"
    if not re.search(r"[A-Z]", password):
        return f"{field_name} debe tener al menos una mayúscula"
    if not re.search(r"[a-z]", password):
        return f"{field_name} debe tener al menos una minúscula"
    if not re.search(r"\d", password):
        return f"{field_name} debe tener al menos un número"
    # Verifica al menos un carácter especial del conjunto definido
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return f"{field_name} debe tener al menos un carácter especial (!@#$%^&* etc.)"
    return None


def generate_secure_password(length: int = 16) -> str:
    """
    Genera una contraseña criptográficamente segura.

    Usa secrets.choice() para garantizar aleatoriedad segura. Reintenta
    hasta que la contraseña generada pase la política de validación.

    Args:
        length: Longitud de la contraseña a generar (default 16).

    Returns:
        str con la contraseña segura generada.
    """
    # Conjunto de caracteres permitidos: letras (may/min), dígitos y especiales
    chars = string.ascii_letters + string.digits + "!@#$%^&*()"
    while True:
        pw = "".join(secrets.choice(chars) for _ in range(length))
        if validate_password(pw) is None:
            return pw
