"""
Schemas Pydantic para serialización de la API pública del menú.

Define la estructura JSON que se sirve en /api/menu/{slug}.
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer


class ProductOut(BaseModel):
    """Producto individual visible en el menú público (solo available=True)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    price: Decimal
    available: bool
    stock: int = 0
    image_url: str = ""
    category_id: int
    variants: str = ""
    featured: bool = False

    @field_serializer("price")
    @classmethod
    def serialize_price(cls, v: Decimal) -> float:
        return round(float(v), 2)


class CategoryOut(BaseModel):
    """Categoría con sus productos visibles."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    image_url: str = ""
    products: list[ProductOut]


class MenuResponse(BaseModel):
    """Respuesta completa del menú público: datos del store + categorías + productos."""
    model_config = ConfigDict(from_attributes=True)

    store_name: str
    store_slug: str
    whatsapp: str
    delivery_available: bool
    delivery_price: Decimal
    payment_transfer: bool
    payment_cash: bool
    primary_color: str = "#10b981"
    logo_url: str = ""
    opening_time: str = ""
    closing_time: str = ""
    working_days: str = "1,2,3,4,5,6,7"
    categories: list[CategoryOut]

    @field_serializer("delivery_price")
    @classmethod
    def serialize_delivery_price(cls, v: Decimal) -> float:
        return round(float(v), 2)
