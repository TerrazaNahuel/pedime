"""
Schemas Pydantic para serialización de la API pública del menú.

Define la estructura JSON que se sirve en /api/menu/{slug}.
"""

from pydantic import BaseModel, ConfigDict
from typing import List


class ProductOut(BaseModel):
    """Producto individual visible en el menú público (solo available=True)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    price: float  # Serializado desde Decimal de la DB
    available: bool
    image_url: str = ""
    category_id: int


class CategoryOut(BaseModel):
    """Categoría con sus productos visibles."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    products: List[ProductOut]


class MenuResponse(BaseModel):
    """Respuesta completa del menú público: datos del store + categorías + productos."""
    model_config = ConfigDict(from_attributes=True)

    store_name: str
    store_slug: str
    whatsapp: str
    delivery_available: bool
    delivery_price: float
    payment_transfer: bool
    payment_cash: bool
    primary_color: str = "#10b981"
    logo_url: str = ""
    opening_time: str = ""
    closing_time: str = ""
    categories: List[CategoryOut]
