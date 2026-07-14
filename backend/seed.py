"""
Seed data inicial para el comercio demo (SinCulpa.ar).

Se ejecuta automáticamente al iniciar el servidor si no existe ningún store.
Crea un store de ejemplo con categorías y productos, y loguea la contraseña generada.
"""

import logging
from decimal import Decimal

from database import SessionLocal
from models import Category, Product, Store
from passlib.hash import bcrypt
from settings import DEMO_PASSWORD

logger = logging.getLogger("pedime.seed")


def seed_default_store():
    """Crea un store demo con categorías y productos si la DB está vacía."""
    db = SessionLocal()
    try:
        existing = db.query(Store).first()
        if existing:
            return
        default_password = DEMO_PASSWORD

        # ── Log de credenciales del store demo ──
        logger.info("=" * 50)
        logger.info("STORE SEMILLA CREADA")
        logger.info("Email: demo@pedime.app")
        logger.info("Contraseña: %s...%s", default_password[0], default_password[-1])
        logger.info("¡CAMBIALA apenas puedas desde el panel de admin!")
        logger.info("=" * 50)

        # ── Store demo con permisos de superadmin y plan premium ──
        store = Store(
            name="ElAdmin",
            slug="eladmin",
            email="demo@pedime.app",
            whatsapp="542473419927",
            password_hash=bcrypt.hash(default_password),
            delivery_available=True,
            delivery_price=Decimal("1000.00"),
            payment_transfer=True,
            payment_cash=True,
            is_superadmin=True,
            plan="vip_premium",
        )
        db.add(store)
        db.flush()  # Forzar asignación de ID sin commit

        # ── Categorías del menú ──
        categoria_pizzas = Category(name="Pizzas", store_id=store.id)
        categoria_bebidas = Category(name="Bebidas", store_id=store.id)
        categoria_promos = Category(name="Promos", store_id=store.id)
        db.add_all([categoria_pizzas, categoria_bebidas, categoria_promos])
        db.flush()

        # ── Productos de ejemplo con precios ficticios ──
        productos = [
            Product(
                name="Muzzarella",
                description="Pizza clásica con muzzarella y salsa de tomate",
                price=Decimal("8000.00"),
                category_id=categoria_pizzas.id,
                store_id=store.id,
            ),
            Product(
                name="Pepperoni",
                description="Pizza con pepperoni, muzzarella y salsa",
                price=Decimal("9500.00"),
                category_id=categoria_pizzas.id,
                store_id=store.id,
            ),
            Product(
                name="Especial",
                description="Jamón, morrones, aceitunas y muzzarella",
                price=Decimal("11000.00"),
                category_id=categoria_pizzas.id,
                store_id=store.id,
            ),
            Product(
                name="Coca-Cola 500ml",
                price=Decimal("2500.00"),
                category_id=categoria_bebidas.id,
                store_id=store.id,
            ),
            Product(
                name="Agua mineral 500ml",
                price=Decimal("1500.00"),
                category_id=categoria_bebidas.id,
                store_id=store.id,
            ),
            Product(
                name="Promo 2 Muzzas + 2 Cocas",
                description="Dos pizzas muzzarella + dos Coca 500ml",
                price=Decimal("17000.00"),
                category_id=categoria_promos.id,
                store_id=store.id,
            ),
        ]
        db.add_all(productos)
        db.commit()
        logger.info("Store semilla creada: id=%s slug=%s", store.id, store.slug)
    except Exception:
        # Si el store ya existe o hay un error transitorio, se omite sin romper el arranque
        logger.debug("Seed no ejecutado (store ya existe o error transitorio)", exc_info=True)
    finally:
        db.close()
