"""
Configuración centralizada de Pedime.
Todas las variables de entorno se leen y proveen con defaults aquí.
"""

import os

# Plan limits
MAX_PRODUCTS_PER_CATEGORY = int(os.getenv("MAX_PRODUCTS_PER_CATEGORY", "10"))
MAX_CATEGORIES = int(os.getenv("MAX_CATEGORIES", "5"))
MAX_REORDER_IDS = int(os.getenv("MAX_REORDER_IDS", "500"))
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", "10")) * 1024 * 1024

# Rate limits
LOGIN_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_WINDOW_SECONDS = int(os.getenv("LOGIN_WINDOW_SECONDS", "60"))
REGISTER_MAX_ATTEMPTS = int(os.getenv("REGISTER_MAX_ATTEMPTS", "3"))
REGISTER_WINDOW_SECONDS = int(os.getenv("REGISTER_WINDOW_SECONDS", "300"))
PASSWORD_CHANGE_MAX_ATTEMPTS = int(os.getenv("PASSWORD_CHANGE_MAX_ATTEMPTS", "5"))
PASSWORD_CHANGE_WINDOW_SECONDS = int(os.getenv("PASSWORD_CHANGE_WINDOW_SECONDS", "60"))
LOGOUT_MAX_ATTEMPTS = int(os.getenv("LOGOUT_MAX_ATTEMPTS", "10"))
LOGOUT_WINDOW_SECONDS = int(os.getenv("LOGOUT_WINDOW_SECONDS", "60"))
SUPER_RESET_MAX_ATTEMPTS = int(os.getenv("SUPER_RESET_MAX_ATTEMPTS", "3"))
SUPER_RESET_WINDOW_SECONDS = int(os.getenv("SUPER_RESET_WINDOW_SECONDS", "3600"))
