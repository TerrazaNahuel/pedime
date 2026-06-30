"""
Configuración de SQLAlchemy y conexión a base de datos.

Soporta dos modos:
  - PostgreSQL: si DATABASE_URL está configurada (Railway)
  - SQLite: fallback local (desarrollo)
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Usa DATABASE_URL de Railway si existe, sino SQLite local
DATABASE_URL = os.getenv("DATABASE_URL", "")

if DATABASE_URL:
    # PostgreSQL en Railway o SQLite en tests
    from sqlalchemy.pool import StaticPool
    engine_kwargs = {}
    if DATABASE_URL.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        if DATABASE_URL == "sqlite://":
            engine_kwargs["poolclass"] = StaticPool
    engine = create_engine(DATABASE_URL, **engine_kwargs)
else:
    # SQLite local (desarrollo)
    DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(DATA_DIR, exist_ok=True)
    SQLITE_URL = "sqlite:///" + os.path.join(DATA_DIR, "pedime.db")
    engine = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False},
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base declarativa para los modelos SQLAlchemy
Base = declarative_base()


def get_db():
    """Dependencia de FastAPI que provee una sesión de DB por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Crea todas las tablas definidas en models.py si no existen."""
    Base.metadata.create_all(bind=engine)
