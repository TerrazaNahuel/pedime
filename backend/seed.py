"""
Seed data inicial para el comercio demo (SinCulpa.ar).

Se ejecuta automáticamente al iniciar el servidor si no existe ningún store.
Crea un store de ejemplo con categorías y productos, y loguea la contraseña generada.
"""

from database import SessionLocal
from models import Store, Category, Product
from passlib.hash import bcrypt
from decimal import Decimal
import logging
import secrets
import string

logger = logging.getLogger("pedime.seed")


def seed_default_store():
    """Crea un store demo con categorías y productos si la DB está vacía."""
    db = SessionLocal()
    try:
        existing = db.query(Store).first()
        if existing:
            return
        # Genera contraseña aleatoria de 16 caracteres
        alphabet = string.ascii_letters + string.digits
        default_password = "".join(secrets.choice(alphabet) for _ in range(16))

        logger.info("=" * 50)
        logger.info("STORE SEMILLA CREADA")
        logger.info("Email: sinculpa@pedime.app")
        logger.info("Contraseña: %s", default_password)
        logger.info("¡CAMBIALA apenas puedas desde el panel de admin!")
        logger.info("=" * 50)

        # Store demo (superadmin + premium)
        store = Store(
            name="SinCulpa.ar",
            slug="sinculpa",
            email="sinculpa@pedime.app",
            whatsapp="5491134567890",
            password_hash=bcrypt.hash(default_password),
            delivery_available=True,
            delivery_price=Decimal("1000.00"),
            payment_transfer=True,
            payment_cash=True,
            is_superadmin=True,
            plan="premium",
        )
        db.add(store)
        db.flush()

        # Categorías
        categoria_pizzas = Category(name="Pizzas", store_id=store.id)
        categoria_bebidas = Category(name="Bebidas", store_id=store.id)
        categoria_promos = Category(name="Promos", store_id=store.id)
        db.add_all([categoria_pizzas, categoria_bebidas, categoria_promos])
        db.flush()

        # Productos de ejemplo
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
        logger.warning("Seed ya existe o falló (race condition)", exc_info=True)
    finally:
        db.close()
