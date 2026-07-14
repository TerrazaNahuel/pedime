"""
Tests para endpoints de pago con Mercado Pago.
"""

import re


def _login(client):
    """Helper: login y devolver CSRF token del dashboard."""
    resp = client.get("/login")
    csrf = re.search(r'name="csrf_token".*?value="([^"]+)"', resp.text).group(1)
    client.post("/login", data={
        "email": "test@test.com", "password": "Test1234!", "csrf_token": csrf,
    }, follow_redirects=False)
    resp = client.get("/admin/dashboard")
    return re.search(r'name="csrf_token".*?value="([^"]+)"', resp.text).group(1)


class TestCreatePreference:
    def test_invalid_plan_rejected(self, client, seed_store):
        """Plan invalido debe devolver 400 (o 503 si MP no configurado)."""
        csrf = _login(client)
        resp = client.post("/api/payments/create-preference", json={
            "plan": "plan_falso", "csrf_token": csrf,
        })
        assert resp.status_code in (400, 503)
        assert resp.json()["ok"] is False

    def test_missing_csrf_rejected(self, client, seed_store):
        """Sin CSRF token debe devolver 403."""
        _login(client)
        resp = client.post("/api/payments/create-preference", json={
            "plan": "vip_basico", "csrf_token": "",
        })
        assert resp.status_code == 403

    def test_no_auth_redirects(self, client):
        """Sin sesion debe redirigir a login."""
        resp = client.post("/api/payments/create-preference", json={
            "plan": "vip_basico", "csrf_token": "fake",
        }, follow_redirects=False)
        assert resp.status_code in (302, 307)

    def test_valid_plan_accepted(self, client, seed_store):
        """Plan valido debe crear preferencia (o devolver 503 si MP no configurado)."""
        csrf = _login(client)
        resp = client.post("/api/payments/create-preference", json={
            "plan": "vip_basico", "csrf_token": csrf,
        })
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert "ok" in data


class TestPaymentWebhook:
    def test_missing_payment_id(self, client):
        """Webhook sin payment_id debe devolver 400."""
        resp = client.post("/api/payments/webhook", json={
            "data": {"id": ""},
        }, params={"topic": "payment"})
        assert resp.status_code == 400

    def test_webhook_no_topic_ok(self, client):
        """Webhook sin topic especifico debe responder OK."""
        resp = client.post("/api/payments/webhook", json={})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


class TestPaymentCallbacks:
    def test_success_redirects(self, client, seed_store):
        """Callback success debe redirigir al dashboard."""
        _login(client)
        resp = client.get("/api/payments/success?preference_id=test123&external_reference=1", follow_redirects=False)
        assert resp.status_code in (302, 307)
        assert "dashboard" in resp.headers.get("location", "")

    def test_failure_redirects(self, client, seed_store):
        """Callback failure debe redirigir a stats con error."""
        _login(client)
        resp = client.get("/api/payments/failure", follow_redirects=False)
        assert resp.status_code in (302, 307)
        assert "premium=error" in resp.headers.get("location", "")

    def test_pending_redirects(self, client, seed_store):
        """Callback pending debe redirigir a stats con pending."""
        _login(client)
        resp = client.get("/api/payments/pending", follow_redirects=False)
        assert resp.status_code in (302, 307)
        assert "premium=pending" in resp.headers.get("location", "")
