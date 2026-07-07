"""
Tests de operaciones CRUD del panel de administración.

Cubre productos (crear, editar, eliminar, duplicar, toggle, reordenar,
exportar/importar CSV), categorías (crear, editar, eliminar),
settings (actualizar, validaciones, password, logout).
"""

import io
import re
import urllib.parse

from models import Store


def _csrf(client, url):
    """Helper: GET a URL, sigue redirects, devuelve (token, response)."""
    resp = client.get(url, follow_redirects=True)
    m = re.search(r'name="csrf_token".*?value="([^"]+)"', resp.text)
    assert m, f"No CSRF token found in {url}"
    return m.group(1), resp


def _make_premium(db, store_id):
    """Actualiza el plan del store a premium para tests de variantes."""
    store = db.query(Store).filter(Store.id == store_id).first()
    if store:
        store.plan = "premium"
        db.commit()

def _login(client, email="test@test.com", password="Test1234"):
    """Helper: inicia sesión como seed_store y devuelve token CSRF del dashboard."""
    csrf, resp = _csrf(client, "/login")
    resp = client.post("/login", data={
        "email": email, "password": password, "csrf_token": csrf,
    }, follow_redirects=False)
    assert resp.status_code == 302
    return _csrf(client, "/admin/dashboard")[0]


class TestProducts:
    def test_create_product(self, client, seed_store):
        """Crear producto exitosamente debe redirigir al dashboard."""
        csrf = _login(client)
        resp = client.post("/admin/product", data={
            "name": "Test Pizza",
            "description": "Una pizza de prueba",
            "price": "1500.50",
            "category_id": "1",
            "image_url": "",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers.get("location", "").endswith("/admin/dashboard")

    def test_create_product_long_name_rejected(self, client, seed_store):
        """Nombre de producto > 100 caracteres debe ser rechazado."""
        csrf = _login(client)
        resp = client.post("/admin/product", data={
            "name": "A" * 101,
            "description": "",
            "price": "100",
            "category_id": "1",
            "image_url": "",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert "nombre" in resp.headers.get("location", "").lower()

    def test_create_product_negative_price_rejected(self, client, seed_store):
        """Precio negativo debe ser rechazado."""
        csrf = _login(client)
        resp = client.post("/admin/product", data={
            "name": "Pizza", "description": "",
            "price": "-10",
            "category_id": "1",
            "image_url": "",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert "precio" in resp.headers.get("location", "").lower()

    def test_edit_product(self, client, seed_store):
        """Editar producto debe persistir los cambios."""
        csrf = _login(client)
        client.post("/admin/product", data={
            "name": "Original", "description": "",
            "price": "100", "category_id": "1",
            "image_url": "", "csrf_token": csrf,
        }, follow_redirects=False)
        csrf = _csrf(client, "/admin/dashboard")[0]

        resp = client.post("/admin/product/1/edit", data={
            "name": "Edited", "description": "Nueva desc",
            "price": "200", "category_id": "1",
            "available": "1", "image_url": "",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302

        _, dash = _csrf(client, "/admin/dashboard")
        assert "Edited" in dash.text
        assert "Nueva desc" in dash.text

    def test_duplicate_product(self, client, seed_store):
        """Duplicar producto debe crear una copia con '(copia)' en el nombre."""
        csrf = _login(client)
        client.post("/admin/product", data={
            "name": "Original", "description": "",
            "price": "100", "category_id": "1",
            "image_url": "", "csrf_token": csrf,
        }, follow_redirects=False)
        csrf = _csrf(client, "/admin/dashboard")[0]

        resp = client.post("/admin/product/1/duplicate", data={
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302

        _, dash = _csrf(client, "/admin/dashboard")
        assert "(copia)" in dash.text

    def test_delete_product(self, client, seed_store):
        """Eliminar producto debe quitarlo del dashboard."""
        csrf = _login(client)
        client.post("/admin/product", data={
            "name": "ToDelete", "description": "",
            "price": "100", "category_id": "1",
            "image_url": "", "csrf_token": csrf,
        }, follow_redirects=False)
        csrf = _csrf(client, "/admin/dashboard")[0]

        resp = client.post("/admin/product/1/delete", data={
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302

        _, dash = _csrf(client, "/admin/dashboard")
        assert "ToDelete" not in dash.text

    def test_toggle_product(self, client, seed_store):
        """Toggle de producto debe mostrar 'Oculto' en el dashboard."""
        csrf = _login(client)
        client.post("/admin/product", data={
            "name": "ToggleMe", "description": "",
            "price": "100", "category_id": "1",
            "image_url": "", "csrf_token": csrf,
        }, follow_redirects=False)
        csrf = _csrf(client, "/admin/dashboard")[0]

        resp = client.post("/admin/product/1/toggle", data={
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302

        _, dash = _csrf(client, "/admin/dashboard")
        assert "Oculto" in dash.text

    def test_reorder_products(self, client, seed_store):
        """Reordenar productos debe responder 302."""
        csrf = _login(client)
        for i in range(3):
            client.post("/admin/product", data={
                "name": f"Prod{i}", "description": "",
                "price": "100", "category_id": "1",
                "image_url": "", "csrf_token": csrf,
            }, follow_redirects=False)
        csrf = _csrf(client, "/admin/dashboard")[0]

        resp = client.post("/admin/products/reorder", data={
            "product_ids": "3,2,1",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302

    def test_create_product_with_variants(self, client, seed_store, db):
        """Crear producto con variantes debe persistirlas."""
        _make_premium(db, seed_store.id)
        csrf = _login(client)
        resp = client.post("/admin/product", data={
            "name": "Hamburguesa",
            "description": "Con variantes",
            "price": "1000",
            "category_id": "1",
            "image_url": "",
            "variants": '[{"name":"Simple","price":800},{"name":"Doble","price":1200}]',
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302

        resp = client.get("/api/menu/test-store")
        assert resp.status_code == 200
        data = resp.json()
        prod = data["categories"][0]["products"][0]
        assert prod["variants"] == '[{"name":"Simple","price":800},{"name":"Doble","price":1200}]'

    def test_create_product_invalid_variants_json_rejected(self, client, seed_store):
        """JSON de variantes inválido debe ser rechazado."""
        csrf = _login(client)
        resp = client.post("/admin/product", data={
            "name": "Test", "description": "",
            "price": "100", "category_id": "1",
            "image_url": "",
            "variants": "not-json",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert "variante" in resp.headers.get("location", "").lower()

    def test_create_product_variant_empty_name_rejected(self, client, seed_store, db):
        """Variante con nombre vacío debe ser rechazada."""
        _make_premium(db, seed_store.id)
        csrf = _login(client)
        resp = client.post("/admin/product", data={
            "name": "Test", "description": "",
            "price": "100", "category_id": "1",
            "image_url": "",
            "variants": '[{"name":"","price":800}]',
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert "nombre" in resp.headers.get("location", "").lower()

    def test_create_product_variant_negative_price_rejected(self, client, seed_store, db):
        """Variante con precio negativo debe ser rechazada."""
        _make_premium(db, seed_store.id)
        csrf = _login(client)
        resp = client.post("/admin/product", data={
            "name": "Test", "description": "",
            "price": "100", "category_id": "1",
            "image_url": "",
            "variants": '[{"name":"Simple","price":-100}]',
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert "precio" in resp.headers.get("location", "").lower()

    def test_edit_product_variants(self, client, seed_store, db):
        """Editar producto debe actualizar variantes."""
        _make_premium(db, seed_store.id)
        csrf = _login(client)
        client.post("/admin/product", data={
            "name": "Original", "description": "",
            "price": "100", "category_id": "1",
            "image_url": "", "csrf_token": csrf,
        }, follow_redirects=False)
        csrf = _csrf(client, "/admin/dashboard")[0]

        resp = client.post("/admin/product/1/edit", data={
            "name": "Edited", "description": "",
            "price": "200", "category_id": "1",
            "available": "1", "image_url": "",
            "variants": '[{"name":"Triple","price":300}]',
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302

        resp = client.get("/api/menu/test-store")
        data = resp.json()
        prod = data["categories"][0]["products"][0]
        assert prod["variants"] == '[{"name":"Triple","price":300}]'

    def test_duplicate_product_with_variants(self, client, seed_store, db):
        """Duplicar producto debe copiar también las variantes."""
        _make_premium(db, seed_store.id)
        csrf = _login(client)
        client.post("/admin/product", data={
            "name": "Con Variantes", "description": "",
            "price": "100", "category_id": "1",
            "image_url": "",
            "variants": '[{"name":"S","price":50},{"name":"L","price":150}]',
            "csrf_token": csrf,
        }, follow_redirects=False)
        csrf = _csrf(client, "/admin/dashboard")[0]

        resp = client.post("/admin/product/1/duplicate", data={
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302

        resp = client.get("/api/menu/test-store")
        data = resp.json()
        assert len(data["categories"][0]["products"]) == 2
        assert data["categories"][0]["products"][1]["variants"] == data["categories"][0]["products"][0]["variants"]

    def test_export_csv(self, client, seed_store):
        """Exportar CSV debe incluir los productos creados."""
        csrf = _login(client)
        client.post("/admin/product", data={
            "name": "CSVProd", "description": "Desc",
            "price": "99.99", "category_id": "1",
            "image_url": "", "csrf_token": csrf,
        }, follow_redirects=False)

        resp = client.get("/admin/products/export")
        assert resp.status_code == 200
        assert "CSVProd" in resp.text
        assert "99.99" in resp.text

    def test_import_csv(self, client, seed_store):
        """Importar CSV debe crear los productos."""
        csrf = _login(client)
        content = "name,description,price,category_id,image_url,available\nImported,Test,500,1,,\n"
        resp = client.post("/admin/products/import", data={
            "csrf_token": csrf,
        }, files={
            "file": ("test.csv", io.BytesIO(content.encode("utf-8")), "text/csv"),
        }, follow_redirects=False)
        assert resp.status_code == 302

        _, dash = _csrf(client, "/admin/dashboard")
        assert "Imported" in dash.text


class TestCategories:
    def test_create_category(self, client, seed_store):
        """Crear categoría exitosamente debe mostrarla en el dashboard."""
        csrf = _login(client)
        resp = client.post("/admin/category", data={
            "name": "Test Cat",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302

        _, dash = _csrf(client, "/admin/dashboard")
        assert "Test Cat" in dash.text

    def test_create_category_empty_rejected(self, client, seed_store):
        """Nombre de categoría vacío debe ser rechazado."""
        csrf = _login(client)
        resp = client.post("/admin/category", data={
            "name": "",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302
        loc = urllib.parse.unquote(resp.headers.get("location", ""))
        assert "vacío" in loc

    def test_edit_category(self, client, seed_store):
        """Editar nombre de categoría debe persistir el cambio."""
        csrf = _login(client)
        client.post("/admin/category", data={
            "name": "Cat Original", "csrf_token": csrf,
        }, follow_redirects=False)
        csrf = _csrf(client, "/admin/dashboard")[0]

        resp = client.post("/admin/category/1/edit", data={
            "name": "Cat Editada", "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302

        _, dash = _csrf(client, "/admin/dashboard")
        assert "Cat Editada" in dash.text

    def test_delete_category(self, client, seed_store):
        """Eliminar categoría debe quitarla del dashboard."""
        csrf = _login(client)
        client.post("/admin/category", data={
            "name": "Cat To Delete", "csrf_token": csrf,
        }, follow_redirects=False)
        csrf = _csrf(client, "/admin/dashboard")[0]

        # seed_store crea General (id=1), entonces Cat To Delete es id=2
        resp = client.post("/admin/category/2/delete", data={
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302

        _, dash = _csrf(client, "/admin/dashboard")
        assert "Cat To Delete" not in dash.text

class TestSettings:
    def test_update_settings(self, client, seed_store):
        """Actualizar settings debe mostrar mensaje de confirmación."""
        csrf = _login(client)
        resp = client.post("/admin/settings", data={
            "name": "Updated Store", "email": "test@test.com",
            "whatsapp": "5491134567890",
            "delivery_available": "1", "delivery_price": "1500",
            "payment_transfer": "1", "payment_cash": "0",
            "primary_color": "#ff0000", "logo_url": "",
            "opening_time": "09:00", "closing_time": "22:00",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 200
        assert "Configuración guardada" in resp.text

    def test_update_settings_overnight_hours_accepted(self, client, seed_store):
        """Horario nocturno (cierre < apertura) debe ser aceptado."""
        csrf = _login(client)
        resp = client.post("/admin/settings", data={
            "name": "Store", "email": "test@test.com",
            "whatsapp": "5491134567890",
            "delivery_available": "1", "delivery_price": "0",
            "payment_transfer": "1", "payment_cash": "1",
            "primary_color": "#10b981", "logo_url": "",
            "opening_time": "22:00", "closing_time": "09:00",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 200
        assert "Configuración guardada" in resp.text

    def test_update_settings_equal_hours_rejected(self, client, seed_store):
        """Apertura = cierre debe ser rechazado."""
        csrf = _login(client)
        resp = client.post("/admin/settings", data={
            "name": "Store", "email": "test@test.com",
            "whatsapp": "5491134567890",
            "delivery_available": "1", "delivery_price": "0",
            "payment_transfer": "1", "payment_cash": "1",
            "primary_color": "#10b981", "logo_url": "",
            "opening_time": "09:00", "closing_time": "09:00",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 200
        assert "horario" in resp.text.lower()

    def test_update_settings_invalid_color_rejected(self, client, seed_store):
        """Color inválido en settings debe mostrar error."""
        csrf = _login(client)
        resp = client.post("/admin/settings", data={
            "name": "Store", "email": "test@test.com",
            "whatsapp": "5491134567890",
            "delivery_available": "1", "delivery_price": "0",
            "payment_transfer": "1", "payment_cash": "1",
            "primary_color": "red", "logo_url": "",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 200
        assert "color" in resp.text.lower()

    def test_change_password(self, client, seed_store):
        """Cambiar contraseña correctamente debe confirmar."""
        csrf = _login(client)
        resp = client.post("/admin/settings", data={
            "name": "Store", "email": "test@test.com",
            "whatsapp": "5491134567890",
            "delivery_available": "1", "delivery_price": "0",
            "payment_transfer": "1", "payment_cash": "1",
            "primary_color": "#10b981", "logo_url": "",
            "current_password": "Test1234", "new_password": "NewPass123",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 200
        assert "Configuración guardada" in resp.text

    def test_logout(self, client, seed_store):
        """Logout debe cerrar sesión y prevenir acceso al dashboard."""
        csrf = _login(client)
        resp = client.post("/admin/logout", data={
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302

        resp = client.get("/admin/dashboard", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers.get("location", "")
