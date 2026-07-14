"""
CRUD de productos del panel de administración.

Operaciones: crear, editar, duplicar, eliminar, toggle visibilidad,
reordenar (drag & drop), exportar e importar CSV.
"""

import csv
import io
import json
from decimal import Decimal

from csrf import validate_csrf
from database import get_db
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import Response
from models import Category, Product, Store
from routers.admin_base import (
    admin_error_response,
    check_plan_limit,
    get_authenticated_store,
    logger,
    respond_ok,
)
from sqlalchemy import func as db_func
from sqlalchemy.orm import Session
from validators import validate_url

from backend.settings import MAX_FILE_SIZE, MAX_REORDER_IDS, MAX_VARIANTS

router = APIRouter()


def _validate_product_fields(name: str, description: str, price: Decimal, stock: int, image_url: str, available: str, category_id: int, store, db) -> str | None:
    """Valida campos comunes de producto. Retorna mensaje de error o None."""
    if len(name) > 100:
        return "El nombre del producto es demasiado largo"
    if len(description) > 500:
        return "La descripción es demasiado larga"
    if price < 0:
        return "El precio no puede ser negativo"
    if stock < 0:
        return "El stock no puede ser negativo"
    url_err = validate_url(image_url, "La URL de la imagen")
    if url_err is not None:
        return url_err
    if available not in ("0", "1"):
        return "Valor de disponibilidad inválido"
    cat = db.query(Category).filter(Category.id == category_id, Category.store_id == store.id).first()
    if not cat:
        return "Categoría no encontrada"
    return None


def validate_variants_json(variants: str, store) -> str | None:
    """Valida el JSON de variantes. Retorna mensaje de error o None si es válido."""
    if not variants or variants == "[]":
        return None
    if store.plan == "free":
        return "Las variantes son solo para planes VIP"
    try:
        parsed = json.loads(variants)
    except json.JSONDecodeError:
        return "El formato de variantes no es válido"
    if not isinstance(parsed, list):
        return "Las variantes deben ser una lista"
    if len(parsed) > MAX_VARIANTS:
        return f"Máximo {MAX_VARIANTS} variantes por producto"
    for v in parsed:
        if not isinstance(v, dict) or "name" not in v or "price" not in v:
            return "Cada variante debe tener 'name' y 'price'"
        if not isinstance(v["name"], str) or not v["name"].strip():
            return "El nombre de la variante no puede estar vacío"
        if len(v["name"]) > 50:
            return "El nombre de la variante es demasiado largo (máx 50 caracteres)"
        try:
            price_val = float(v["price"])
        except (ValueError, TypeError):
            return "El precio de la variante debe ser un número"
        if price_val < 0:
            return "El precio de la variante no puede ser negativo"
    return None


@router.post("/admin/product")
def create_product(
    request: Request,
    name: str = Form(...), description: str = Form(""),
    price: Decimal = Form(...), category_id: int = Form(...),
    image_url: str = Form(""), product_id: int = Form(0),
    stock: int = Form(0), variants: str = Form(""),
    available: str = Form("1"), featured: str = Form("0"),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    """Crea un producto nuevo o redirige a update si product_id > 0."""
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)

    if product_id > 0:
        return update_product(request, name, description, price, category_id, image_url, product_id, stock, variants, available, featured, store, db)

    variants_err = validate_variants_json(variants, store)
    if variants_err:
        return admin_error_response(request, store, db, variants_err)
    limit_err = check_plan_limit(store, db, category_id=category_id)
    if limit_err:
        return admin_error_response(request, store, db, limit_err)
    field_err = _validate_product_fields(name, description, price, stock, image_url, available, category_id, store, db)
    if field_err:
        return admin_error_response(request, store, db, field_err)
    min_sort = db.query(db_func.min(Product.sort_order)).filter(Product.store_id == store.id).scalar() or 0
    db.add(Product(name=name, description=description, price=price,
                   image_url=image_url, category_id=category_id, store_id=store.id,
                   stock=stock, variants=variants, available=(available == "1"),
                   featured=(featured == "1"), sort_order=min_sort - 1))
    db.commit()
    logger.info("Producto creado store_id=%s category_id=%s", store.id, category_id)
    return respond_ok(request, store, db, "Producto creado")


def update_product(
    request: Request,
    name: str,
    description: str,
    price: Decimal,
    category_id: int,
    image_url: str,
    product_id: int,
    stock: int,
    variants: str,
    available: str,
    featured: str,
    store: Store,
    db: Session,
) -> Response:
    """Edita un producto existente."""
    variants_err = validate_variants_json(variants, store)
    if variants_err:
        return admin_error_response(request, store, db, variants_err)
    prod = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).first()
    if not prod:
        return admin_error_response(request, store, db, "Producto no encontrado")
    limit_err = check_plan_limit(store, db, category_id=category_id, exclude_product_id=product_id)
    if limit_err:
        return admin_error_response(request, store, db, limit_err)
    field_err = _validate_product_fields(name, description, price, stock, image_url, available, category_id, store, db)
    if field_err:
        return admin_error_response(request, store, db, field_err)
    prod.name = name
    prod.description = description
    prod.price = price
    prod.category_id = category_id
    prod.available = (available == "1")
    prod.image_url = image_url
    prod.stock = stock
    prod.variants = variants
    prod.featured = (featured == "1")
    db.commit()
    logger.info("Producto editado store_id=%s id=%s", store.id, product_id)
    return respond_ok(request, store, db, "Producto actualizado")


@router.post("/admin/product/{product_id}/duplicate")
def duplicate_product(product_id: int, request: Request, csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """Duplica un producto agregando '(copia)' al nombre."""
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)

    original = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).first()
    if not original:
        return admin_error_response(request, store, db, "Producto no encontrado")
    limit_err = check_plan_limit(store, db, category_id=original.category_id)
    if limit_err:
        return admin_error_response(request, store, db, limit_err)
    dup_name = original.name[:max(0, 100 - len(" (copia)"))] + " (copia)"
    min_sort = db.query(db_func.min(Product.sort_order)).filter(Product.store_id == store.id).scalar() or 0
    dup = Product(
        name=dup_name,
        description=original.description,
        price=original.price,
        stock=original.stock,
        image_url=original.image_url,
        available=original.available,
        category_id=original.category_id,
        store_id=store.id,
        sort_order=min_sort - 1,
        variants=original.variants,
        featured=original.featured,
    )
    db.add(dup)
    db.commit()
    logger.info("Producto duplicado store_id=%s from_id=%s new_id=%s", store.id, product_id, dup.id)
    return respond_ok(request, store, db, "Producto duplicado")


@router.post("/admin/product/{product_id}/delete")
def delete_product(product_id: int, request: Request, csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """Elimina un producto."""
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)

    prod = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).first()
    if not prod:
        return admin_error_response(request, store, db, "Producto no encontrado")
    logger.info("Producto eliminado store_id=%s id=%s", store.id, product_id)
    db.delete(prod)
    db.commit()
    logger.info("Producto eliminado store_id=%s id=%s", store.id, product_id)
    return respond_ok(request, store, db, "Producto eliminado")


@router.post("/admin/product/{product_id}/toggle")
def toggle_product(product_id: int, request: Request, csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """Alterna la visibilidad de un producto (available true/false)."""
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)

    prod = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).first()
    if not prod:
        return admin_error_response(request, store, db, "Producto no encontrado")
    prod.available = not prod.available
    db.commit()
    logger.info("Producto toggle store_id=%s id=%s available=%s", store.id, product_id, prod.available)
    return respond_ok(request, store, db, "Visibilidad actualizada")


@router.post("/admin/product/{product_id}/toggle-featured")
def toggle_featured(product_id: int, request: Request, csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """Alterna el estado destacado de un producto."""
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)

    prod = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).first()
    if not prod:
        return admin_error_response(request, store, db, "Producto no encontrado")
    prod.featured = not prod.featured
    db.commit()
    logger.info("Producto toggle featured store_id=%s id=%s featured=%s", store.id, product_id, prod.featured)
    return respond_ok(request, store, db, "Destacado actualizado")


@router.post("/admin/products/reorder")
def reorder_products(request: Request, product_ids: str = Form(...), csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """
    Reordena los productos según una lista de IDs (drag & drop).
    El orden se recibe como string separado por comas desde SortableJS.
    """
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)

    try:
        ids = [int(x) for x in product_ids.split(",") if x.strip()]
    except ValueError:
        return admin_error_response(request, store, db, "IDs de producto inválidos")
    if len(ids) > MAX_REORDER_IDS:
        return admin_error_response(request, store, db, f"Demasiados productos (máx {MAX_REORDER_IDS})")
    products_to_update = db.query(Product).filter(
        Product.id.in_(ids),
        Product.store_id == store.id,
    ).all()
    # Elimina duplicados preservando orden, asigna índice secuencial como sort_order
    unique_ids = list(dict.fromkeys(ids))
    id_to_product = {p.id: p for p in products_to_update}
    for i, pid in enumerate(unique_ids):
        if pid in id_to_product:
            id_to_product[pid].sort_order = i
    db.commit()
    logger.info("Productos reordenados store_id=%s count=%s", store.id, len(ids))
    return respond_ok(request, store, db, "Orden guardado")


@router.get("/admin/products/export")
def export_products_csv(request: Request, db: Session = Depends(get_db)):
    """Exporta todos los productos del store como archivo CSV."""
    store = get_authenticated_store(request, db)
    products = db.query(Product).filter(Product.store_id == store.id).order_by(Product.sort_order, Product.id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["name", "description", "price", "category_id", "image_url", "available", "stock", "variants"])
    for p in products:
        writer.writerow([p.name, p.description or "", str(p.price), p.category_id, p.image_url or "", "1" if p.available else "0", str(p.stock or 0), p.variants or ""])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=productos.csv"},
    )


@router.post("/admin/products/import")
def import_products_csv(
    request: Request,
    file: UploadFile = File(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Importa productos desde un archivo CSV.
    Validaciones: extensión .csv, tamaño máx 10MB, codificación UTF-8.
    Retorna resumen con cantidad importada y hasta 5 errores.
    """
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)

    if file.filename is None or not file.filename.endswith(".csv"):
        return admin_error_response(request, store, db, "El archivo debe ser CSV")

    raw = file.file.read(MAX_FILE_SIZE + 1)
    if len(raw) > MAX_FILE_SIZE:
        return admin_error_response(request, store, db, f"El archivo es demasiado grande (máx {MAX_FILE_SIZE // (1024*1024)} MB)")

    content_type = file.content_type or ""
    if content_type not in ("text/csv", "text/plain", "application/octet-stream", ""):
        return admin_error_response(request, store, db, "El archivo debe ser un CSV válido")

    # Intenta decodificar con utf-8-sig que maneja BOM automáticamente
    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return admin_error_response(request, store, db, "El archivo debe estar codificado en UTF-8")
    reader = csv.DictReader(io.StringIO(content))

    created = 0
    errors = []
    for row_num, row in enumerate(reader, start=2):
        name = row.get("name", "").strip()
        if not name:
            errors.append(f"Fila {row_num}: nombre requerido")
            continue
        if len(name) > 100:
            errors.append(f"Fila {row_num}: nombre demasiado largo")
            continue

        description = row.get("description", "").strip()
        if len(description) > 500:
            errors.append(f"Fila {row_num}: descripción demasiado larga")
            continue
        image_url = row.get("image_url", "").strip()[:500]

        try:
            price = Decimal(row.get("price", "0"))
        except (ValueError, TypeError, ArithmeticError):
            errors.append(f"Fila {row_num}: precio inválido")
            continue
        if price < 0:
            errors.append(f"Fila {row_num}: precio negativo")
            continue

        try:
            category_id = int(row.get("category_id", "0"))
        except (ValueError, TypeError):
            errors.append(f"Fila {row_num}: category_id inválido")
            continue

        cat = db.query(Category).filter(Category.id == category_id, Category.store_id == store.id).first()
        if not cat:
            errors.append(f"Fila {row_num}: categoría {category_id} no encontrada")
            continue

        limit_err = check_plan_limit(store, db, category_id=category_id)
        if limit_err:
            errors.append(f"Fila {row_num}: {limit_err}")
            continue

        available = row.get("available", "1").strip() in ("1", "true", "yes")

        try:
            stock = int(row.get("stock", "0").strip() or "0")
        except (ValueError, TypeError):
            stock = 0
        if stock < 0:
            stock = 0

        variants = row.get("variants", "").strip()
        variants_err = validate_variants_json(variants, store)
        if variants_err:
            errors.append(f"Fila {row_num}: {variants_err}")
            continue

        db.add(Product(
            name=name, description=description, price=price,
            stock=stock, image_url=image_url, category_id=category_id,
            store_id=store.id, available=available, variants=variants,
        ))
        created += 1

    db.commit()
    logger.info("Productos importados store_id=%s creados=%s errores=%s", store.id, created, len(errors))

    msg = f"Se importaron {created} productos."
    if errors:
        msg += " Errores: " + "; ".join(errors[:5])

    return respond_ok(request, store, db, msg)
