"""
Modelos SQLAlchemy para la base de datos del menú digital.

Tres tablas principales:
  - stores: cada comercio registrado
  - categories: categorías de productos por comercio
  - products: productos individuales dentro de una categoría
"""

from datetime import UTC, datetime

from database import Base
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship


class Store(Base):
    """Comercio registrado en la plataforma. Cada store tiene su propio slug y menú."""

    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)  # URL amigable única
    email = Column(String(200), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    whatsapp = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    delivery_available = Column(Boolean, default=True)  # Indica si ofrece delivery
    delivery_price = Column(Numeric(10, 2), default=0.0)  # Precio del delivery en ARS
    payment_transfer = Column(Boolean, default=True)  # Acepta transferencia bancaria
    payment_cash = Column(Boolean, default=True)  # Acepta pago en efectivo
    primary_color = Column(String(7), default="#10b981")  # Color primario del comercio (hex)
    logo_url = Column(String(500), default="")  # URL del logo del comercio
    opening_time = Column(String(5), default="")  # HH:MM — hora de apertura
    closing_time = Column(String(5), default="")  # HH:MM — hora de cierre
    working_days = Column(String(20), default="1,2,3,4,5,6,7")  # Días laborales: 1=Lunes … 7=Domingo
    plan = Column(String(20), default="free")  # Tipo de suscripción: "free" | "premium"
    plan_expires_at = Column(DateTime, nullable=True)  # Fecha de vencimiento del plan premium
    is_active = Column(Boolean, default=True)  # Comercio visible/publicado
    is_superadmin = Column(Boolean, default=False)  # Permisos de administración global

    categories = relationship("Category", back_populates="store", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="store", cascade="all, delete-orphan")


class Category(Base):
    """Agrupación de productos (ej: Pizzas, Bebidas, Promos)."""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)  # Relación M:1 con stores

    store = relationship("Store", back_populates="categories")
    products = relationship("Product", back_populates="category", cascade="all, delete-orphan")


class Product(Base):
    """Producto individual dentro de una categoría (ej: Muzzarella, Coca-Cola)."""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), default="")
    price = Column(Numeric(10, 2), nullable=False)  # Precio en ARS
    available = Column(Boolean, default=True)  # Visible/disponible para la venta
    stock = Column(Integer, default=0)  # Stock disponible (0 = sin límite)
    image_url = Column(String(500), default="")
    sort_order = Column(Integer, default=0)  # Orden personalizado por drag & drop
    variants = Column(Text, default="")  # JSON con variantes: [{"name":"Doble","price":150}]
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)  # Relación M:1 con categories
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)  # Relación M:1 con stores

    category = relationship("Category", back_populates="products")
    store = relationship("Store", back_populates="products")


class PageView(Base):
    """Visita a la página de menú de un comercio."""

    __tablename__ = "page_views"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    viewed_at = Column(DateTime, default=lambda: datetime.now(UTC))


class WhatsAppClick(Base):
    """Click en el botón de WhatsApp para enviar un pedido."""

    __tablename__ = "whatsapp_clicks"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    clicked_at = Column(DateTime, default=lambda: datetime.now(UTC))
    cart_value = Column(Numeric(10, 2), default=0)
    item_count = Column(Integer, default=0)
    payment_method = Column(String(20), default="")


class RateLimitEntry(Base):
    """Registro de intentos para rate limiting, compartido entre workers via DB."""

    __tablename__ = "rate_limit_entries"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(200), index=True, nullable=False)  # Clave única, ej: "login:1.2.3.4"
    attempted_at = Column(DateTime, default=lambda: datetime.now(UTC))  # Marca de tiempo del intento


class PaymentTransaction(Base):
    """Transacción de pago para upgrade a premium."""

    __tablename__ = "payment_transactions"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False, index=True)
    mp_preference_id = Column(String(100), unique=True, nullable=True)  # ID de preferencia de Mercado Pago
    mp_payment_id = Column(String(100), unique=True, nullable=True)  # ID del pago en Mercado Pago
    status = Column(String(20), default="pending")  # pending | approved | rejected | refunded
    amount = Column(Numeric(10, 2), nullable=False)  # Monto cobrado en ARS
    plan_type = Column(String(20), default="premium")  # Tipo de plan adquirido
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    approved_at = Column(DateTime, nullable=True)  # Fecha de aprobación del pago
    expires_at = Column(DateTime, nullable=True)  # Fecha de vencimiento del plan
    metadata_json = Column(Text, default="")  # Datos adicionales en formato JSON
