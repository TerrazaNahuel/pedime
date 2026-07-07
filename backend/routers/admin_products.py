"""
CRUD de productos del panel de administración.

Operaciones: crear, editar, duplicar, eliminar, toggle visibilidad,
reordenar (drag & drop), exportar e importar CSV.
"""

import csv
import io
import json
import re
import urllib.parse
from decimal import Decimal

from csrf import validate_csrf
from database import get_db
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from models import Category, Product
from routers.admin_base import check_plan_limit, get_authenticated_store, logger, render_dashboard_html
from sqlalchemy import func as db_func
from sqlalchemy.orm import Session

from backend.settings import MAX_FILE_SIZE, MAX_REORDER_IDS, MAX_VARIANTS

router = APIRouter()

URL_PATTERN = re.compile(r"^https?://\S+$")


def validate_url(url: str) -> bool:
    """Valida que una URL sea HTTP(S) válida o esté vacía. Rechaza javascript:, data:, etc."""
    return not url or bool(URL_PATTERN.match(url))


def validate_variants_json(variants: str, store) -> str | None:
    """Valida el JSON de variantes. Retorna mensaje de error o None si es válido."""
    if not variants or variants == "[]":
        return None
    if store.plan != "premium":
        return "Las variantes son solo para plan Premium"
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
    available: str = Form("1"),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    """Crea o edita un producto segun si product_id está presente."""
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)

    def _err(msg):
        if request.headers.get("HX-Request"):
            return render_dashboard_html(request, store, db, err=msg, tab="productos")
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote(msg), status_code=302)

    variants_err = validate_variants_json(variants, store)
    if variants_err:
        return _err(variants_err)

    if product_id > 0:
        prod = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).first()
        if not prod:
            return _err("Producto no encontrado")
        limit_err = check_plan_limit(store, db, category_id=category_id)
        if limit_err:
            return _err(limit_err)
        if len(name) > 100:
            return _err("El nombre del producto es demasiado largo")
        if len(description) > 500:
            return _err("La descripción es demasiado larga")
        if price < 0:
            return _err("El precio no puede ser negativo")
        if stock < 0:
            return _err("El stock no puede ser negativo")
        if not validate_url(image_url):
            return _err("La URL de la imagen no es válida")
        if len(image_url) > 500:
            return _err("La URL de la imagen es demasiado larga")
        if available not in ("0", "1"):
            return _err("Valor de disponibilidad inválido")
        cat = db.query(Category).filter(Category.id == category_id, Category.store_id == store.id).first()
        if not cat:
            return _err("Categoría no encontrada")
        prod.name = name
        prod.description = description
        prod.price = price
        prod.category_id = category_id
        prod.available = (available == "1")
        prod.image_url = image_url
        prod.stock = stock
        prod.variants = variants
        db.commit()
        logger.info("Producto editado store_id=%s id=%s", store.id, product_id)
        if request.headers.get("HX-Request"):
            return render_dashboard_html(request, store, db, msg="Producto actualizado", tab="productos")
        return RedirectResponse(url="/admin/dashboard", status_code=302)

    limit_err = check_plan_limit(store, db, category_id=category_id)
    if limit_err:
        return _err(limit_err)
    if len(name) > 100:
        return _err("El nombre del producto es demasiado largo")
    if len(description) > 500:
        return _err("La descripción es demasiado larga")
    if price < 0:
        return _err("El precio no puede ser negativo")
    if stock < 0:
        return _err("El stock no puede ser negativo")
    if not validate_url(image_url):
        return _err("La URL de la imagen no es válida")
    if len(image_url) > 500:
        return _err("La URL de la imagen es demasiado larga")
    if available not in ("0", "1"):
        return _err("Valor de disponibilidad inválido")
    cat = db.query(Category).filter(Category.id == category_id, Category.store_id == store.id).first()
    if not cat:
        return _err("Categoría no encontrada")
    min_sort = db.query(db_func.min(Product.sort_order)).filter(Product.store_id == store.id).scalar() or 0
    db.add(Product(name=name, description=description, price=price,
                   image_url=image_url, category_id=category_id, store_id=store.id,
                   stock=stock, variants=variants, available=(available == "1"), sort_order=min_sort - 1))
    db.commit()
    logger.info("Producto creado store_id=%s category_id=%s", store.id, category_id)
    if request.headers.get("HX-Request"):
        return render_dashboard_html(request, store, db, msg="Producto creado", tab="productos")
    return RedirectResponse(url="/admin/dashboard", status_code=302)


@router.post("/admin/product/{product_id}/edit")
def update_product(
    product_id: int, request: Request,
    name: str = Form(...), description: str = Form(""),
    price: Decimal = Form(...), category_id: int = Form(...),
    available: str = Form("0"),
    image_url: str = Form(""),
    stock: int = Form(0),
    variants: str = Form(""),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    """Edita un producto existente. Verifica que pertenezca al store autenticado."""
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)

    def _err(msg):
        if request.headers.get("HX-Request"):
            return render_dashboard_html(request, store, db, err=msg, tab="productos")
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote(msg), status_code=302)

    variants_err = validate_variants_json(variants, store)
    if variants_err:
        return _err(variants_err)
    if len(name) > 100:
        return _err("El nombre del producto es demasiado largo")
    if len(description) > 500:
        return _err("La descripción es demasiado larga")
    if price < 0:
        return _err("El precio no puede ser negativo")
    if stock < 0:
        return _err("El stock no puede ser negativo")
    prod = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).first()
    if not prod:
        return _err("Producto no encontrado")
    if not validate_url(image_url):
        return _err("La URL de la imagen no es válida")
    if len(image_url) > 500:
        return _err("La URL de la imagen es demasiado larga")
    if available not in ("0", "1"):
        return _err("Valor de disponibilidad inválido")
    cat = db.query(Category).filter(Category.id == category_id, Category.store_id == store.id).first()
    if not cat:
        return _err("Categoría no encontrada")
    logger.info("Producto editado store_id=%s id=%s", store.id, product_id)
    prod.name = name
    prod.description = description
    prod.price = price
    prod.category_id = category_id
    prod.available = (available == "1")
    prod.image_url = image_url
    prod.stock = stock
    prod.variants = variants
    db.commit()
    if request.headers.get("HX-Request"):
        return render_dashboard_html(request, store, db, msg="Producto actualizado", tab="productos")
    return RedirectResponse(url="/admin/dashboard", status_code=302)


@router.post("/admin/product/{product_id}/duplicate")
def duplicate_product(product_id: int, request: Request, csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """Duplica un producto agregando '(copia)' al nombre."""
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)

    def _err(msg):
        if request.headers.get("HX-Request"):
            return render_dashboard_html(request, store, db, err=msg, tab="productos")
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote(msg), status_code=302)

    original = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).first()
    if not original:
        return _err("Producto no encontrado")
    limit_err = check_plan_limit(store, db, category_id=original.category_id)
    if limit_err:
        return _err(limit_err)
    dup_name = original.name[:92] + " (copia)"
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
    )
    db.add(dup)
    db.commit()
    logger.info("Producto duplicado store_id=%s from_id=%s new_id=%s", store.id, product_id, dup.id)
    if request.headers.get("HX-Request"):
        return render_dashboard_html(request, store, db, msg="Producto duplicado", tab="productos")
    return RedirectResponse(url="/admin/dashboard", status_code=302)


@router.post("/admin/product/{product_id}/delete")
def delete_product(product_id: int, request: Request, csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """Elimina un producto."""
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)

    def _err(msg):
        if request.headers.get("HX-Request"):
            return render_dashboard_html(request, store, db, err=msg, tab="productos")
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote(msg), status_code=302)

    prod = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).first()
    if not prod:
        return _err("Producto no encontrado")
    logger.info("Producto eliminado store_id=%s id=%s", store.id, product_id)
    db.delete(prod)
    db.commit()
    if request.headers.get("HX-Request"):
        return render_dashboard_html(request, store, db, msg="Producto eliminado", tab="productos")
    return RedirectResponse(url="/admin/dashboard", status_code=302)


@router.post("/admin/product/{product_id}/toggle")
def toggle_product(product_id: int, request: Request, csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """Alterna la visibilidad de un producto (available true/false)."""
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)

    def _err(msg):
        if request.headers.get("HX-Request"):
            return render_dashboard_html(request, store, db, err=msg, tab="productos")
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote(msg), status_code=302)

    prod = db.query(Product).filter(Product.id == product_id, Product.store_id == store.id).first()
    if not prod:
        return _err("Producto no encontrado")
    prod.available = not prod.available
    db.commit()
    logger.info("Producto toggle store_id=%s id=%s available=%s", store.id, product_id, prod.available)
    if request.headers.get("HX-Request"):
        return render_dashboard_html(request, store, db, msg="Visibilidad actualizada", tab="productos")
    return RedirectResponse(url="/admin/dashboard", status_code=302)


@router.post("/admin/products/reorder")
def reorder_products(request: Request, product_ids: str = Form(...), csrf_token: str = Form(...), db: Session = Depends(get_db)):
    """
    Reordena los productos según una lista de IDs (drag & drop).
    El orden se recibe como string separado por comas desde SortableJS.
    """
    validate_csrf(request, csrf_token)
    store = get_authenticated_store(request, db)

    def _err(msg):
        if request.headers.get("HX-Request"):
            return render_dashboard_html(request, store, db, err=msg, tab="productos")
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote(msg), status_code=302)

    try:
        ids = [int(x) for x in product_ids.split(",") if x.strip()]
    except ValueError:
        return _err("IDs de producto inválidos")
    if len(ids) > MAX_REORDER_IDS:
        return _err(f"Demasiados productos (máx {MAX_REORDER_IDS})")
    products_to_update = db.query(Product).filter(
        Product.id.in_(ids),
        Product.store_id == store.id,
    ).all()
    unique_ids = list(dict.fromkeys(ids))
    id_to_product = {p.id: p for p in products_to_update}
    for i, pid in enumerate(unique_ids):
        if pid in id_to_product:
            id_to_product[pid].sort_order = i
    db.commit()
    logger.info("Productos reordenados store_id=%s count=%s", store.id, len(ids))
    if request.headers.get("HX-Request"):
        return render_dashboard_html(request, store, db, msg="Orden guardado", tab="productos")
    return RedirectResponse(url="/admin/dashboard", status_code=302)


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

    def _err(msg):
        if request.headers.get("HX-Request"):
            return render_dashboard_html(request, store, db, err=msg, tab="productos")
        return RedirectResponse(url="/admin/dashboard?err=" + urllib.parse.quote(msg), status_code=302)

    if file.filename is None or not file.filename.endswith(".csv"):
        return _err("El archivo debe ser CSV")

    raw = file.file.read(MAX_FILE_SIZE + 1)
    if len(raw) > MAX_FILE_SIZE:
        return _err(f"El archivo es demasiado grande (máx {MAX_FILE_SIZE // (1024*1024)} MB)")

    content_type = file.content_type or ""
    if content_type not in ("text/csv", "text/plain", "application/octet-stream", ""):
        return _err("El archivo debe ser un CSV válido")

    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return _err("El archivo debe estar codificado en UTF-8")
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

        description = row.get("description", "").strip()[:500]
        image_url = row.get("image_url", "").strip()[:500]

        try:
            price = Decimal(row.get("price", "0"))
        except Exception:
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

    if request.headers.get("HX-Request"):
        return render_dashboard_html(request, store, db, msg=msg, tab="productos")
    return RedirectResponse(url=f"/admin/dashboard?msg={urllib.parse.quote(msg)}", status_code=302)
