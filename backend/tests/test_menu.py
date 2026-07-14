"""
Tests de rutas públicas del menú.

Verifica que:
  - Slugs inválidos devuelven 404
  - Slugs válidos devuelven 200 con contenido esperado
  - La API JSON funciona correctamente
  - Las páginas de login y register se renderizan
"""


def test_menu_404_on_invalid_slug(client):
    """Un slug inexistente debe devolver 404."""
    resp = client.get("/menu/nonexistent")
    assert resp.status_code == 404


def test_menu_200_on_valid_slug(client, seed_store):
    """Un slug existente debe devolver 200 con el HTML del menú."""
    resp = client.get(f"/menu/{seed_store.slug}")
    assert resp.status_code == 200
    assert "Cargando" in resp.text


def test_api_menu_404(client):
    """API con slug inválido debe devolver 404."""
    resp = client.get("/api/menu/invalid")
    assert resp.status_code == 404


def test_api_menu_200(client, seed_store):
    """API con slug válido debe devolver JSON con datos del store."""
    resp = client.get(f"/api/menu/{seed_store.slug}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["store_name"] == "Test Store"
    assert data["store_slug"] == "test-store"
    assert data["delivery_available"]


def test_login_returns_page(client):
    """GET /login debe devolver 200 con el formulario de login."""
    resp = client.get("/login")
    assert resp.status_code == 200
    assert "Login" in resp.text or "login" in resp.text or "Ingresar" in resp.text


def test_register_page(client):
    """GET /register debe devolver 200 con el formulario de registro."""
    resp = client.get("/register")
    assert resp.status_code == 200
