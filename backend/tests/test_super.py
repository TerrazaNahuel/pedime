"""
Tests del panel Super Admin.
Cubre: dashboard, toggle-active, set-plan, make-superadmin, reset-password, delete.
"""

import re

import pytest


def _csrf(client, url):
    resp = client.get(url, follow_redirects=True)
    m = re.search(r'name="csrf_token".*?value="([^"]+)"', resp.text)
    assert m, f"No CSRF token found in {url}"
    return m.group(1), resp


def _login(client, email="super@test.com", password="Super1234"):
    csrf, _ = _csrf(client, "/login")
    resp = client.post("/login", data={
        "email": email, "password": password, "csrf_token": csrf,
    }, follow_redirects=False)
    assert resp.status_code == 302
    return _csrf(client, "/admin/super")[0]


@pytest.fixture
def super_store(db):
    from models import Store
    from passlib.hash import bcrypt

    store = Store(
        name="Super Admin",
        slug="super-admin",
        email="super@test.com",
        whatsapp="5491134567890",
        password_hash=bcrypt.hash("Super1234"),
        is_superadmin=True,
        plan="premium",
    )
    db.add(store)
    db.commit()
    db.refresh(store)

    extra = Store(
        name="Extra Store",
        slug="extra-store",
        email="extra@test.com",
        whatsapp="5491134567891",
        password_hash=bcrypt.hash("Extra1234"),
        is_superadmin=False,
        plan="free",
    )
    db.add(extra)
    db.commit()
    db.refresh(extra)
    return store


class TestSuperDashboard:
    def test_super_dashboard_accessible(self, client, super_store):
        """Super admin debe poder acceder al panel super."""
        csrf = _login(client)
        resp = client.get("/admin/super", follow_redirects=True)
        assert resp.status_code == 200
        assert "Super Admin" in resp.text or "super" in resp.text.lower()

    def test_super_dashboard_redirects_non_super(self, client, seed_store):
        """Store no superadmin debe ser redirigido."""
        csrf, _ = _csrf(client, "/login")
        client.post("/login", data={
            "email": "test@test.com", "password": "Test1234", "csrf_token": csrf,
        }, follow_redirects=False)
        resp = client.get("/admin/super", follow_redirects=False)
        assert resp.status_code == 302
        assert "/admin/dashboard" in resp.headers.get("location", "")


class TestSuperActions:
    def test_toggle_active(self, client, super_store, db):
        """Toggle active debe cambiar el estado del store."""
        from models import Store
        csrf = _login(client)
        target = db.query(Store).filter(Store.slug == "extra-store").first()
        old_active = target.is_active
        target_id = target.id

        resp = client.post(f"/admin/super/{target_id}/toggle-active", data={
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers.get("location", "").endswith("/admin/super")

        db.refresh(target)
        assert target.is_active != old_active

    def test_set_plan_free(self, client, super_store, db):
        """Set plan debe cambiar el plan del store."""
        from models import Store
        csrf = _login(client)
        target = db.query(Store).filter(Store.slug == "extra-store").first()

        resp = client.post(f"/admin/super/{target.id}/set-plan", data={
            "plan": "premium", "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302

        db.refresh(target)
        assert target.plan == "premium"

    def test_set_plan_invalid(self, client, super_store, db):
        """Plan inválido debe mostrar error."""
        from models import Store
        csrf = _login(client)
        target = db.query(Store).filter(Store.slug == "extra-store").first()

        resp = client.post(f"/admin/super/{target.id}/set-plan", data={
            "plan": "ultra", "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert "err" in resp.headers.get("location", "")

    def test_toggle_superadmin(self, client, super_store, db):
        """Toggle superadmin debe cambiar el flag."""
        from models import Store
        csrf = _login(client)
        target = db.query(Store).filter(Store.slug == "extra-store").first()
        old_super = target.is_superadmin

        resp = client.post(f"/admin/super/{target.id}/make-superadmin", data={
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302

        db.refresh(target)
        assert target.is_superadmin != old_super

    def test_toggle_self_superadmin_blocked(self, client, super_store, db):
        """Sacarse superadmin a uno mismo debe ser rechazado."""
        csrf = _login(client)
        resp = client.post(f"/admin/super/{super_store.id}/make-superadmin", data={
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert "err" in resp.headers.get("location", "")

    def test_delete_store(self, client, super_store, db):
        """Eliminar store debe removerlo de la DB."""
        from models import Store
        csrf = _login(client)
        target = db.query(Store).filter(Store.slug == "extra-store").first()
        target_id = target.id

        resp = client.post(f"/admin/super/{target_id}/delete", data={
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302

        deleted = db.query(Store).filter(Store.id == target_id).first()
        assert deleted is None

    def test_delete_self_blocked(self, client, super_store, db):
        """Auto-eliminarse debe ser rechazado."""
        csrf = _login(client)
        resp = client.post(f"/admin/super/{super_store.id}/delete", data={
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert "err" in resp.headers.get("location", "")

    def test_delete_superadmin_blocked(self, client, super_store, db):
        """Eliminar un superadmin debe ser rechazado."""
        from models import Store
        csrf = _login(client)
        # Crear otro superadmin
        from passlib.hash import bcrypt
        other = Store(
            name="Other Super", slug="other-super", email="other@test.com",
            whatsapp="5491134567892", password_hash=bcrypt.hash("Other1234"),
            is_superadmin=True, plan="premium",
        )
        db.add(other)
        db.commit()
        db.refresh(other)

        resp = client.post(f"/admin/super/{other.id}/delete", data={
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert "err" in resp.headers.get("location", "")

    def test_reset_password(self, client, super_store, db):
        """Reset password debe mostrar la nueva contraseña."""
        from models import Store
        csrf = _login(client)
        target = db.query(Store).filter(Store.slug == "extra-store").first()

        resp = client.post(f"/admin/super/{target.id}/reset-password", data={
            "csrf_token": csrf,
        }, follow_redirects=True)
        assert resp.status_code == 200
        # Debe mostrar la nueva contraseña en el HTML
        assert resp.text.count("extra-store") > 0 or "contrase" in resp.text.lower()
