"""
Tests de seguridad y validaciones.

Cubre: password policy, CSRF, rate limiting, SQL injection, XSS,
validación de colores/URLs, CSV malformed, sesión, headers de seguridad.
"""

import re


def _csrf(client, url="/register"):
    """Helper: hace GET a una página para setear la cookie CSRF y devuelve el token."""
    resp = client.get(url)
    match = re.search(r'name="csrf_token".*?value="([^"]+)"', resp.text)
    assert match, f"No CSRF token in {url}"
    return match.group(1)


class TestAuthSecurity:
    def test_password_policy_too_short(self, client):
        """Password de menos de 8 caracteres debe ser rechazado."""
        csrf = _csrf(client, "/register")
        resp = client.post("/register", data={
            "name": "Test", "email": "test@test.com",
            "password": "Ab1", "confirm_password": "Ab1",
            "whatsapp": "5491134567890", "slug": "test-store",
            "csrf_token": csrf,
        })
        assert "8 caracteres" in resp.text

    def test_password_policy_no_uppercase(self, client):
        """Password sin mayúscula debe ser rechazado."""
        csrf = _csrf(client, "/register")
        resp = client.post("/register", data={
            "name": "Test", "email": "test@test.com",
            "password": "abcdef12", "confirm_password": "abcdef12",
            "whatsapp": "5491134567890", "slug": "test-store",
            "csrf_token": csrf,
        })
        assert "mayúscula" in resp.text

    def test_password_policy_no_lowercase(self, client):
        """Password sin minúscula debe ser rechazado."""
        csrf = _csrf(client, "/register")
        resp = client.post("/register", data={
            "name": "Test", "email": "test@test.com",
            "password": "ABCDEF12", "confirm_password": "ABCDEF12",
            "whatsapp": "5491134567890", "slug": "test-store",
            "csrf_token": csrf,
        })
        assert "minúscula" in resp.text

    def test_password_policy_no_digit(self, client):
        """Password sin número debe ser rechazado."""
        csrf = _csrf(client, "/register")
        resp = client.post("/register", data={
            "name": "Test", "email": "test@test.com",
            "password": "Abcdefgh", "confirm_password": "Abcdefgh",
            "whatsapp": "5491134567890", "slug": "test-store",
            "csrf_token": csrf,
        })
        assert "número" in resp.text

    def test_csrf_missing_returns_422(self, client):
        """POST sin csrf_token debe devolver 422 (validation error de FastAPI)."""
        resp = client.post("/login", data={
            "email": "test@test.com", "password": "Test1234!",
        })
        assert resp.status_code == 422

    def test_csrf_wrong_returns_403(self, client):
        """POST con csrf_token incorrecto debe devolver 403."""
        resp = client.post("/login", data={
            "email": "test@test.com", "password": "Test1234!",
            "csrf_token": "x" * 64,
        })
        assert resp.status_code == 403

    def test_rate_limit_login(self, client):
        """6 intentos de login en 60s deben disparar rate limit (429)."""
        csrf = _csrf(client, "/login")
        for i in range(6):
            resp = client.post("/login", data={
                "email": f"nobody{i}@test.com",
                "password": "WrongPass1",
                "csrf_token": csrf,
            })
            # Cada login fallido rota el token CSRF; extraer para el próximo intento
            m = re.search(r'name="csrf_token".*?value="([^"]+)"', resp.text)
            if m:
                csrf = m.group(1)
        assert resp.status_code == 429


class TestSQLInjection:
    def test_sqli_slug(self, client):
        """Slug con SQL injection debe devolver 404 (no ejecutar el SQL)."""
        payloads = [
            "'; DROP TABLE stores; --",
            "' OR '1'='1",
            "'; SELECT * FROM stores; --",
            "../../etc/passwd",
        ]
        for payload in payloads:
            resp = client.get(f"/menu/{payload}")
            assert resp.status_code == 404

    def test_sqli_api_slug(self, client):
        """Slug con SQL injection en API debe devolver 404."""
        resp = client.get("/api/menu/'; DROP TABLE stores; --")
        assert resp.status_code == 404

    def test_sqli_login_email(self, client):
        """Email con SQL injection en login no debe autenticar."""
        csrf = _csrf(client, "/login")
        resp = client.post("/login", data={
            "email": "' OR '1'='1",
            "password": "Test1234!",
            "csrf_token": csrf,
        })
        assert resp.status_code == 200
        assert "Email o contraseña incorrectos" in resp.text


class TestXSS:
    def test_xss_in_slug(self, client):
        """Slug con script tags debe devolver 404 (no ejecutarse)."""
        resp = client.get("/menu/<script>alert(1)</script>")
        assert resp.status_code == 404


class TestColorValidation:
    def test_invalid_color_rejected(self, client, client_with_csrf):
        """Color inválido en settings debe mostrar error."""
        csrf = client_with_csrf
        resp = client.post("/admin/settings", data={
            "name": "Test Store", "whatsapp": "5491134567890",
            "email": "test@test.com", "current_password": "",
            "new_password": "", "delivery_available": "1",
            "delivery_price": "500", "payment_transfer": "1",
            "payment_cash": "1", "primary_color": "not-a-color",
            "logo_url": "", "opening_time": "", "closing_time": "",
            "csrf_token": csrf,
        })
        assert "color" in resp.text.lower()


class TestURLValidation:
    def test_invalid_image_url_rejected(self, client, client_with_csrf):
        """URL maliciosa (javascript:) debe ser rechazada al crear producto."""
        csrf = client_with_csrf
        resp = client.post("/admin/product", data={
            "name": "Test", "description": "",
            "price": "100", "category_id": "1",
            "image_url": "javascript:alert(1)",
            "csrf_token": csrf,
        })
        assert "URL" in resp.text


class TestCSVImport:
    def test_csv_non_utf8_rejected(self, client, client_with_csrf):
        """CSV con codificación no UTF-8 debe ser rechazado."""
        csrf = client_with_csrf
        bad_bytes = b"\xff\xfe\x00\x00name,price\n"
        resp = client.post("/admin/products/import", data={
            "csrf_token": csrf,
        }, files={
            "file": ("test.csv", bad_bytes, "text/csv"),
        })
        assert "UTF" in resp.text or "utf" in resp.text.lower()


class TestSessionSecurity:
    def test_authenticated_session_required(self, client):
        """Acceso a /admin/dashboard sin sesión debe redirigir a /login."""
        resp = client.get("/admin/dashboard", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers.get("location", "")


class TestRateLimiting:
    def test_rate_limit_register(self, client):
        """4 registros en 5 minutos debe mostrar mensaje de rate limit."""
        for i in range(4):
            resp = client.get("/register", follow_redirects=False)
            if resp.status_code == 302:
                client.cookies.clear()
                resp = client.get("/register")
            csrf = re.search(r'name="csrf_token".*?value="([^"]+)"', resp.text)
            assert csrf, "No CSRF token"
            resp = client.post("/register", data={
                "name": f"Test{i}", "email": f"test{i}@test.com",
                "password": "Test1234!", "confirm_password": "Test1234!",
                "whatsapp": "5491134567890", "slug": f"test-store-{i}",
                "csrf_token": csrf.group(1),
            }, follow_redirects=False)
        assert "Demasiados registros" in resp.text


class TestCSRFCookieFlags:
    def test_csrf_cookie_has_httponly(self, client):
        """La cookie csrf_token debe tener flag HttpOnly."""
        resp = client.get("/login")
        set_cookie = resp.headers.get("set-cookie", "")
        assert "csrf_token=" in set_cookie
        assert "httponly" in set_cookie.lower()


class TestSecurityHeaders:
    def test_x_frame_options(self, client):
        """Toda respuesta debe incluir X-Frame-Options: DENY."""
        resp = client.get("/")
        assert resp.headers.get("x-frame-options") == "DENY"

    def test_x_content_type_options(self, client):
        """Toda respuesta debe incluir X-Content-Type-Options: nosniff."""
        resp = client.get("/")
        assert resp.headers.get("x-content-type-options") == "nosniff"
