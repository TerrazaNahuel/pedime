"""
Tests para endpoints de tracking (visitas y WhatsApp clicks).
"""


from models import Store
from passlib.hash import bcrypt


def _seed_trackable_store(db):
    """Crea un store con slug conocido para tests de tracking."""
    store = Store(
        name="Track Store", slug="track-store",
        email="track@track.com", whatsapp="5491111111111",
        password_hash=bcrypt.hash("Test1234!"),
        delivery_available=True, delivery_price=300,
        payment_transfer=True, payment_cash=True,
    )
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


class TestTrackView:
    def test_track_view_valid_slug(self, client, db):
        """Visita a un store activo debe registrar el page view (200)."""
        _seed_trackable_store(db)
        resp = client.post("/api/track/view/track-store", headers={"Origin": "http://localhost"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_track_view_invalid_slug(self, client):
        """Visita a slug inexistente debe devolver 404."""
        resp = client.post("/api/track/view/no-existe", headers={"Origin": "http://localhost"})
        assert resp.status_code == 404

    def test_track_view_no_origin_rejected(self, client, db):
        """Sin header Origin/Referer debe ser rechazado (403)."""
        _seed_trackable_store(db)
        resp = client.post("/api/track/view/track-store")
        assert resp.status_code == 403

    def test_track_view_wrong_origin_rejected(self, client, db):
        """Origen externo debe ser rechazado (403)."""
        _seed_trackable_store(db)
        resp = client.post("/api/track/view/track-store", headers={"Origin": "https://evil.com"})
        assert resp.status_code == 403


class TestTrackWhatsAppClick:
    def test_whatsapp_click_valid(self, client, db):
        """Click de WhatsApp con payload valido debe registrar (200)."""
        _seed_trackable_store(db)
        resp = client.post(
            "/api/track/whatsapp-click/track-store",
            json={"cart_value": 1500.50, "item_count": 3, "payment_method": "transfer"},
            headers={"Origin": "http://localhost"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_whatsapp_click_invalid_slug(self, client):
        """Click en slug inexistente debe devolver 404."""
        resp = client.post(
            "/api/track/whatsapp-click/no-existe",
            json={"cart_value": 100, "item_count": 1, "payment_method": "cash"},
            headers={"Origin": "http://localhost"},
        )
        assert resp.status_code == 404

    def test_whatsapp_click_no_origin_rejected(self, client, db):
        """Sin Origin debe ser rechazado (403)."""
        _seed_trackable_store(db)
        resp = client.post(
            "/api/track/whatsapp-click/track-store",
            json={"cart_value": 100, "item_count": 1, "payment_method": "cash"},
        )
        assert resp.status_code == 403

    def test_whatsapp_click_excessive_values_clamped(self, client, db):
        """Valores fuera de rango deben ser clampeados (no crashean)."""
        _seed_trackable_store(db)
        resp = client.post(
            "/api/track/whatsapp-click/track-store",
            json={"cart_value": 9999999, "item_count": 9999, "payment_method": "bitcoin"},
            headers={"Origin": "http://localhost"},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_whatsapp_click_invalid_payment_defaults_to_other(self, client, db):
        """Metodo de pago desconocido debe mapearse a 'other'."""
        _seed_trackable_store(db)
        resp = client.post(
            "/api/track/whatsapp-click/track-store",
            json={"cart_value": 200, "item_count": 2, "payment_method": "cripto"},
            headers={"Origin": "http://localhost"},
        )
        assert resp.status_code == 200

    def test_whatsapp_click_negative_values_clamped(self, client, db):
        """Valores negativos deben ser clampeados a 0."""
        _seed_trackable_store(db)
        resp = client.post(
            "/api/track/whatsapp-click/track-store",
            json={"cart_value": -500, "item_count": -3, "payment_method": ""},
            headers={"Origin": "http://localhost"},
        )
        assert resp.status_code == 200
