"""
Configuración global de pytest para los tests de Pedime.

Fixtures disponibles:
  - setup_db: autouse, crea/borra tablas entre tests
  - db: sesión SQLAlchemy
  - client: TestClient de FastAPI con HTTPS
  - seed_store: store de prueba con categoría y datos básicos
  - client_with_csrf: cliente autenticado con token CSRF válido
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["SECRET_KEY"] = "test" + "x" * 60
os.environ["ENVIRONMENT"] = "test"
# Tests usan SQLite en memoria compartida — no toca la DB de desarrollo (backend/data/pedime.db)
os.environ["DATABASE_URL"] = "sqlite://"

import re

from database import Base, SessionLocal, engine
from main import app
from models import Category, Store
from passlib.hash import bcrypt


@pytest.fixture(autouse=True)
def setup_db():
    """Limpia rate limiter y recrea tablas antes de cada test."""
    from routers.auth import rate_limiter
    rate_limiter.clear()
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def extract_csrf(resp):
    """Extrae el token CSRF del HTML de una response."""
    match = re.search(r'name="csrf_token".*?value="([^"]+)"', resp.text)
    assert match, "No CSRF token found in response"
    return match.group(1)


@pytest.fixture
def db():
    """Provee una sesión de base de datos en memoria para tests."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    """Cliente HTTP de prueba con base_url HTTPS (requerido por Secure=True en cookies)."""
    return TestClient(app, base_url="https://testserver")


@pytest.fixture
def seed_store(db):
    """Crea un store de prueba con categoría 'General' y datos básicos."""
    store = Store(
        name="Test Store",
        slug="test-store",
        email="test@test.com",
        whatsapp="5491134567890",
        password_hash=bcrypt.hash("Test1234"),
        delivery_available=True,
        delivery_price=500,
        payment_transfer=True,
        payment_cash=True,
        opening_time="09:00",
        closing_time="22:00",
    )
    db.add(store)
    db.commit()
    db.refresh(store)

    cat = Category(name="General", store_id=store.id)
    db.add(cat)
    db.commit()

    return store


@pytest.fixture
def client_with_csrf(client, seed_store):
    """
    Cliente autenticado como seed_store.
    Devuelve el token CSRF del dashboard (cookies manejadas automáticamente).
    """
    resp = client.get("/login")
    csrf = extract_csrf(resp)

    resp = client.post("/login", data={
        "email": "test@test.com",
        "password": "Test1234",
        "csrf_token": csrf,
    }, follow_redirects=False)
    assert resp.status_code == 302, f"Expected 302, got {resp.status_code}: {resp.text[:200]}"

    resp = client.get("/admin/dashboard")
    return extract_csrf(resp)
