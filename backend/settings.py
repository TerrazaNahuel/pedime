"""
Configuración centralizada de Pedime.
Todas las variables de entorno se leen y proveen con defaults aquí.
"""

import os

# ── Límites de planes ──────────────────────────
MAX_PRODUCTS_PER_CATEGORY = int(os.getenv("MAX_PRODUCTS_PER_CATEGORY", "10"))  # Free: máx por categoría
MAX_CATEGORIES_FREE = int(os.getenv("MAX_CATEGORIES_FREE", "5"))  # Free: máx categorías
MAX_CATEGORIES_VIP = int(os.getenv("MAX_CATEGORIES_VIP", "15"))  # VIP Básico: máx categorías
MAX_REORDER_IDS = int(os.getenv("MAX_REORDER_IDS", "500"))
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", "10")) * 1024 * 1024
MAX_VARIANTS = int(os.getenv("MAX_VARIANTS", "10"))

# ── Rate limiting ──────────────────────────────────
# Login: ventana de 60s, máx 5 intentos
LOGIN_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_WINDOW_SECONDS = int(os.getenv("LOGIN_WINDOW_SECONDS", "60"))
# Registro: ventana de 5min, máx 3 intentos
REGISTER_MAX_ATTEMPTS = int(os.getenv("REGISTER_MAX_ATTEMPTS", "3"))
REGISTER_WINDOW_SECONDS = int(os.getenv("REGISTER_WINDOW_SECONDS", "300"))
# Cambio de contraseña: ventana de 60s, máx 5 intentos
PASSWORD_CHANGE_MAX_ATTEMPTS = int(os.getenv("PASSWORD_CHANGE_MAX_ATTEMPTS", "5"))
PASSWORD_CHANGE_WINDOW_SECONDS = int(os.getenv("PASSWORD_CHANGE_WINDOW_SECONDS", "60"))
# Reset de superadmin: ventana de 1h, máx 3 intentos
SUPER_RESET_MAX_ATTEMPTS = int(os.getenv("SUPER_RESET_MAX_ATTEMPTS", "3"))
SUPER_RESET_WINDOW_SECONDS = int(os.getenv("SUPER_RESET_WINDOW_SECONDS", "3600"))

# ── Mercado Pago ───────────────────────────────────
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")  # Token de acceso para API de MP

MP_WEBHOOK_SECRET = os.getenv("MP_WEBHOOK_SECRET", "")  # Secreto para validar webhooks de MP

# ── Precios de planes VIP (en ARS) ─────────────
VIP_BASICO_PRICE = int(os.getenv("VIP_BASICO_PRICE", "12999"))
VIP_PREMIUM_PRICE = int(os.getenv("VIP_PREMIUM_PRICE", "30000"))
PREMIUM_DURATION_DAYS = int(os.getenv("PREMIUM_DURATION_DAYS", "30"))
SITE_URL = os.getenv("SITE_URL", "http://localhost:8000")

# ── Contraseña del store demo ──────────────────────
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "Admin123!")
